#!/opt/musiclite/stable-audio-venv/bin/python
"""Experimental Stable Audio Open backend for short CPU quality samples."""

from __future__ import annotations

import gc
import hmac
import logging
import os
import threading
import uuid
from pathlib import Path
from typing import Any

import torch
import torchaudio
import uvicorn
from einops import rearrange
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from stable_audio_tools import get_pretrained_model
from stable_audio_tools.inference.generation import generate_diffusion_cond

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger("musiclite-stable-audio")
TOKEN = os.environ.get("MUSIC_AI_STABLE_AUDIO_TOKEN", os.environ.get("MUSIC_AI_GENERATOR_TOKEN", ""))
MODEL_NAME = os.environ.get("MUSIC_AI_STABLE_AUDIO_MODEL", "stabilityai/stable-audio-open-1.0")
DEVICE = os.environ.get("MUSIC_AI_STABLE_AUDIO_DEVICE", "cpu").strip().lower()
PORT = int(os.environ.get("MUSIC_AI_STABLE_AUDIO_PORT", "8092"))
STEPS = max(10, int(os.environ.get("MUSIC_AI_STABLE_AUDIO_STEPS", "50")))
CFG_SCALE = float(os.environ.get("MUSIC_AI_STABLE_AUDIO_CFG", "7.0"))
MAX_DURATION = min(30, max(5, int(os.environ.get("MUSIC_AI_STABLE_AUDIO_MAX_DURATION", "30"))))
OUTPUT_ROOT = Path(os.environ.get("MUSIC_AI_STABLE_AUDIO_OUTPUT_PATH", "/var/lib/musiclite/stable-audio-output")).resolve()
PUBLIC_URL = os.environ.get("MUSIC_AI_STABLE_AUDIO_URL", f"http://127.0.0.1:{PORT}").rstrip("/")

if len(TOKEN) < 32:
    raise RuntimeError("MUSIC_AI_STABLE_AUDIO_TOKEN deve possuir ao menos 32 caracteres.")
if DEVICE not in {"cpu", "cuda"}:
    raise RuntimeError("MUSIC_AI_STABLE_AUDIO_DEVICE deve ser cpu ou cuda.")

OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
app = FastAPI(title="MusicLite Stable Audio", docs_url=None, redoc_url=None, openapi_url=None)
_generation_lock = threading.Lock()
_model_lock = threading.Lock()
_model = None
_model_config: dict[str, Any] | None = None


def _authorize(authorization: str | None) -> None:
    expected = f"Bearer {TOKEN}"
    if not authorization or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Não autorizado.")


def _get_model():
    global _model, _model_config
    if _model is not None and _model_config is not None:
        return _model, _model_config
    with _model_lock:
        if _model is not None and _model_config is not None:
            return _model, _model_config
        LOGGER.info("Loading Stable Audio model=%s device=%s", MODEL_NAME, DEVICE)
        try:
            model, config = get_pretrained_model(MODEL_NAME)
            model = model.to(DEVICE)
            model.eval()
        except Exception as exc:
            LOGGER.exception("Could not load Stable Audio Open")
            raise HTTPException(status_code=503, detail="Stable Audio Open não pôde ser carregado; verifique memória, dependências e acesso ao modelo no Hugging Face.") from exc
        _model, _model_config = model, config
        return _model, _model_config


def _release_model() -> None:
    global _model, _model_config
    with _model_lock:
        model = _model
        _model = None
        _model_config = None
    if model is not None:
        del model
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def _prompt(payload: dict[str, Any]) -> str:
    parts = [str(payload.get("prompt") or "").strip()]
    for key in ("genre", "subgenre", "mood", "theme", "instruments", "descriptive_references"):
        value = payload.get(key)
        if isinstance(value, list):
            value = ", ".join(str(item) for item in value)
        if value:
            parts.append(f"{key}: {str(value).strip()}")
    text = ". ".join(part for part in parts if part)
    if not text:
        raise HTTPException(status_code=422, detail="O prompt musical é obrigatório.")
    return text[:7000]


@app.get("/health")
def health(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _authorize(authorization)
    return {"online": True, "backend": "stable-audio-open-1.0", "device": DEVICE, "model_loaded": _model is not None, "busy": _generation_lock.locked(), "max_duration": MAX_DURATION}


@app.post("/generate")
def generate(payload: dict[str, Any], authorization: str | None = Header(default=None)) -> dict[str, str]:
    _authorize(authorization)
    if not bool(payload.get("instrumental", False)):
        raise HTTPException(status_code=422, detail="Stable Audio Open experimental está disponível apenas para instrumental.")
    try:
        duration = int(payload.get("duration_seconds") or 30)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="A duração é inválida.") from exc
    if duration < 5 or duration > MAX_DURATION:
        raise HTTPException(status_code=422, detail=f"Stable Audio Open está limitado a {MAX_DURATION} segundos neste teste.")
    if not _generation_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Já existe uma geração Stable Audio em andamento.")
    try:
        model, config = _get_model()
        sample_rate = int(config["sample_rate"])
        configured_sample_size = int(config["sample_size"])
        requested_sample_size = int(sample_rate * duration)
        sample_size = min(configured_sample_size, requested_sample_size)
        conditioning = [{"prompt": _prompt(payload), "seconds_start": 0, "seconds_total": duration}]
        LOGGER.info("Generating Stable Audio sample duration=%ss steps=%s sample_size=%s", duration, STEPS, sample_size)
        with torch.inference_mode():
            output = generate_diffusion_cond(
                model,
                steps=STEPS,
                cfg_scale=CFG_SCALE,
                conditioning=conditioning,
                sample_size=sample_size,
                sample_rate=sample_rate,
                device=DEVICE,
            )
        output = rearrange(output, "b d n -> d (b n)")
        peak = torch.max(torch.abs(output)).clamp_min(1e-8)
        output = output.to(torch.float32).div(peak).clamp(-1, 1).cpu()
        job_id = str(uuid.uuid4())
        job_dir = OUTPUT_ROOT / job_id
        job_dir.mkdir(mode=0o750)
        destination = job_dir / "stable-audio-sample.wav"
        torchaudio.save(str(destination), output, sample_rate)
        if not destination.is_file() or destination.stat().st_size < 1024:
            raise HTTPException(status_code=503, detail="Stable Audio não produziu um arquivo válido.")
        return {"job_id": job_id, "audio_url": f"{PUBLIC_URL}/files/{job_id}/{destination.name}", "model": MODEL_NAME}
    except HTTPException:
        raise
    except RuntimeError as exc:
        LOGGER.exception("Stable Audio runtime failure")
        _release_model()
        message = str(exc).lower()
        if "out of memory" in message or "cannot allocate memory" in message:
            raise HTTPException(status_code=503, detail="Memória insuficiente para Stable Audio Open neste host.") from exc
        raise HTTPException(status_code=503, detail="Stable Audio Open falhou durante a geração.") from exc
    except Exception as exc:
        LOGGER.exception("Stable Audio unexpected failure")
        _release_model()
        raise HTTPException(status_code=503, detail="Stable Audio Open falhou durante a geração.") from exc
    finally:
        _generation_lock.release()


@app.get("/files/{job_id}/{filename}")
def download(job_id: str, filename: str, authorization: str | None = Header(default=None)):
    _authorize(authorization)
    try:
        uuid.UUID(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.") from exc
    if Path(filename).name != filename:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")
    path = (OUTPUT_ROOT / job_id / filename).resolve()
    if OUTPUT_ROOT not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")
    return FileResponse(path, media_type="audio/wav", filename="stable-audio-sample.wav")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=PORT, workers=1)
