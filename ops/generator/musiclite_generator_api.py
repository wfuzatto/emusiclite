#!/opt/musiclite/venv/bin/python
"""Authenticated synchronous HTTP adapter for the isolated ACE-Step backend."""

from __future__ import annotations

import gc
import hmac
import logging
import os
import subprocess
import threading
import uuid
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse

from musiclite_generation_spec import GENERATION_MODELS, build_ace_spec

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger("musiclite-generator")
TOKEN = os.environ.get("MUSIC_AI_GENERATOR_TOKEN", "")
OUTPUT_ROOT = Path(os.environ.get("MUSIC_AI_GENERATOR_OUTPUT_PATH", "/var/lib/musiclite/generator-output")).resolve()
PUBLIC_URL = os.environ.get("MUSIC_AI_GENERATOR_URL", "http://127.0.0.1:8091").rstrip("/")
CHECKPOINTS = os.environ.get("MUSIC_AI_GENERATOR_CHECKPOINTS_DIR", "/var/lib/musiclite/models")
MAX_DURATION = int(os.environ.get("MUSIC_AI_GENERATOR_MAX_DURATION", "180"))
MIN_FREE_VRAM_MB = int(os.environ.get("MUSIC_AI_MIN_FREE_VRAM_MB", "5200"))
INFERENCE_STEPS = int(os.environ.get("MUSIC_AI_GENERATOR_STEPS", "8"))
QUANTIZATION = os.environ.get("MUSIC_AI_GENERATOR_QUANTIZATION", "auto").strip().lower()
DCW_MODE = os.environ.get("MUSIC_AI_GENERATOR_DCW_ENABLED", "auto").strip().lower()
VELOCITY_NORM = os.environ.get("MUSIC_AI_GENERATOR_VELOCITY_NORM_THRESHOLD", "auto").strip().lower()

if len(TOKEN) < 32:
    raise RuntimeError("MUSIC_AI_GENERATOR_TOKEN deve possuir ao menos 32 caracteres.")

os.environ["ACESTEP_CHECKPOINTS_DIR"] = CHECKPOINTS
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="MusicLite Generator", docs_url=None, redoc_url=None, openapi_url=None)
_generation_lock = threading.Lock()
_handler_lock = threading.Lock()
_dit_handler = None
_dit_model_name: str | None = None


def _select_quantization() -> str | None:
    if QUANTIZATION in {"none", "off", "false", "0"}:
        return None
    if QUANTIZATION != "auto":
        if QUANTIZATION not in {"int8_weight_only", "w8a8_dynamic"}:
            raise RuntimeError("MUSIC_AI_GENERATOR_QUANTIZATION possui valor inválido.")
        return QUANTIZATION
    try:
        import torch
        if torch.cuda.is_available():
            major, _ = torch.cuda.get_device_capability(0)
            if major < 7:
                return "w8a8_dynamic"
    except Exception:
        LOGGER.warning("Could not inspect CUDA capability; using weight-only INT8", exc_info=True)
    return "int8_weight_only"


def _dcw_enabled() -> bool:
    if DCW_MODE in {"true", "1", "yes", "on"}: return True
    if DCW_MODE in {"false", "0", "no", "off"}: return False
    if DCW_MODE != "auto": raise RuntimeError("MUSIC_AI_GENERATOR_DCW_ENABLED possui valor inválido.")
    return _select_quantization() != "w8a8_dynamic"


def _velocity_norm_threshold() -> float:
    if VELOCITY_NORM == "auto": return 2.0 if _select_quantization() == "w8a8_dynamic" else 0.0
    try: threshold = float(VELOCITY_NORM)
    except ValueError as exc: raise RuntimeError("MUSIC_AI_GENERATOR_VELOCITY_NORM_THRESHOLD é inválido.") from exc
    if threshold < 0 or threshold > 100: raise RuntimeError("MUSIC_AI_GENERATOR_VELOCITY_NORM_THRESHOLD está fora do limite.")
    return threshold


def _authorize(authorization: str | None) -> None:
    expected = f"Bearer {TOKEN}"
    if not authorization or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Não autorizado.")


def _free_vram_mb() -> int | None:
    try:
        result = subprocess.run(["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"], capture_output=True, check=True, text=True, timeout=8)
        values = [int(line.strip()) for line in result.stdout.splitlines() if line.strip()]
        return min(values) if values else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def _model_installed(model_name: str) -> bool:
    return (Path(CHECKPOINTS) / model_name).is_dir()


def _dispose_handler(handler) -> None:
    if handler is not None:
        del handler
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
    except Exception:
        LOGGER.warning("Could not clear MusicLite CUDA cache", exc_info=True)


def _get_handler(model_name: str):
    global _dit_handler, _dit_model_name
    if _dit_handler is not None and _dit_model_name == model_name:
        return _dit_handler
    with _handler_lock:
        if _dit_handler is not None and _dit_model_name == model_name:
            return _dit_handler
        if not _model_installed(model_name):
            raise HTTPException(status_code=422, detail=f"O modelo {model_name} ainda não está instalado no servidor.")
        old_handler = _dit_handler
        _dit_handler = None
        _dit_model_name = None
        _dispose_handler(old_handler)

        from acestep.handler import AceStepHandler
        handler = AceStepHandler()
        quantization = _select_quantization()
        LOGGER.info("Initializing ACE-Step model=%s quantization=%s", model_name, quantization or "none")
        status, ready = handler.initialize_service(
            project_root="/opt/musiclite/generator",
            config_path=model_name,
            device="cuda",
            use_flash_attention=False,
            compile_model=True,
            offload_to_cpu=True,
            offload_dit_to_cpu=True,
            quantization=quantization,
            use_mlx_dit=False,
        )
        if not ready:
            LOGGER.error("ACE-Step initialization failed for %s: %s", model_name, status)
            _dispose_handler(handler)
            raise RuntimeError("O gerador não pôde inicializar o modelo selecionado.")
        _dit_handler = handler
        _dit_model_name = model_name
        return handler


def _release_own_handler() -> None:
    global _dit_handler, _dit_model_name
    with _handler_lock:
        handler = _dit_handler
        _dit_handler = None
        _dit_model_name = None
    _dispose_handler(handler)


@app.get("/health")
def health(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _authorize(authorization)
    free_vram = _free_vram_mb()
    return {"online": True, "backend": "ace-step-1.5", "model_ready": _dit_handler is not None, "current_model": _dit_model_name, "busy": _generation_lock.locked(), "free_vram_mb": free_vram, "resources_ready": free_vram is not None and free_vram >= MIN_FREE_VRAM_MB}


@app.get("/models")
def models(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _authorize(authorization)
    return {"models": [{"key": key, "name": name, "installed": _model_installed(name)} for key, name in GENERATION_MODELS.items()], "current_model": _dit_model_name}


@app.post("/generate")
def generate(payload: dict[str, Any], authorization: str | None = Header(default=None)) -> dict[str, str]:
    _authorize(authorization)
    try:
        spec = build_ace_spec(payload, max_duration=MAX_DURATION)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if not spec["instrumental"] and _select_quantization() == "w8a8_dynamic":
        LOGGER.warning("Vocal generation rejected: legacy GPU capacity is insufficient.")
        raise HTTPException(status_code=422, detail="Configuração de GPU insuficiente para geração vocal.")

    if not _generation_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Já existe uma geração em andamento.")
    try:
        free_vram = _free_vram_mb()
        if free_vram is None or free_vram < MIN_FREE_VRAM_MB:
            raise HTTPException(status_code=503, detail="Recursos temporariamente indisponíveis.")

        from acestep.inference import GenerationConfig, GenerationParams, generate_music
        from acestep.llm_inference import LLMHandler

        job_id = str(uuid.uuid4())
        job_dir = OUTPUT_ROOT / job_id
        job_dir.mkdir(mode=0o750)
        params = GenerationParams(task_type="text2music", caption=spec["caption"], lyrics=spec["lyrics"], instrumental=spec["instrumental"], vocal_language=spec["vocal_language"], bpm=spec["bpm"], keyscale=spec["keyscale"], timesignature=spec["timesignature"], duration=spec["duration"], inference_steps=INFERENCE_STEPS, thinking=False, use_cot_metas=False, use_cot_caption=False, use_cot_lyrics=False, use_cot_language=False, dcw_enabled=_dcw_enabled(), velocity_norm_threshold=_velocity_norm_threshold())
        config = GenerationConfig(batch_size=1, use_random_seed=True, audio_format="wav")
        result = generate_music(_get_handler(spec["model"]), LLMHandler(), params, config, save_dir=str(job_dir))
        if not result.success or not result.audios:
            LOGGER.error("ACE-Step generation failed for job %s: %s", job_id, result.error)
            raise HTTPException(status_code=503, detail="A geração de áudio falhou temporariamente.")
        generated = Path(str(result.audios[0].get("path", ""))).resolve()
        if not generated.is_file() or job_dir not in generated.parents or generated.stat().st_size < 1024:
            raise HTTPException(status_code=503, detail="O gerador não produziu um arquivo válido.")
        return {"job_id": job_id, "audio_url": f"{PUBLIC_URL}/files/{job_id}/{generated.name}", "model": spec["model"]}
    except HTTPException as exc:
        if exc.status_code >= 500: _release_own_handler()
        raise
    except Exception:
        LOGGER.exception("Unexpected generation failure")
        _release_own_handler()
        raise HTTPException(status_code=503, detail="A geração de áudio falhou temporariamente.")
    finally:
        _generation_lock.release()


@app.get("/files/{job_id}/{filename}")
def download(job_id: str, filename: str, authorization: str | None = Header(default=None)):
    _authorize(authorization)
    try: uuid.UUID(job_id)
    except ValueError as exc: raise HTTPException(status_code=404, detail="Arquivo não encontrado.") from exc
    if Path(filename).name != filename: raise HTTPException(status_code=404, detail="Arquivo não encontrado.")
    path = (OUTPUT_ROOT / job_id / filename).resolve()
    if OUTPUT_ROOT not in path.parents or not path.is_file(): raise HTTPException(status_code=404, detail="Arquivo não encontrado.")
    return FileResponse(path, media_type="audio/wav", filename="musiclite-generated.wav")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("MUSIC_AI_GENERATOR_PORT", "8091")), workers=1)
