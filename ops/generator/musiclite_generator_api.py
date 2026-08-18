#!/opt/musiclite/venv/bin/python
"""Authenticated synchronous HTTP adapter for the isolated ACE-Step backend.

MusicLite Neural Studio 0.4 adds a controlled audio-to-audio path:
HQ3 creates the musical reference, ACE-Step Cover re-synthesizes it as
continuous audio, multiple takes are generated sequentially, and a lightweight
technical critic ranks them. The API remains loopback/authenticated.
"""

from __future__ import annotations

import gc
import hmac
import logging
import os
import random
import subprocess
import threading
import uuid
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse

from musiclite_audio_critic import rank_candidates
from musiclite_generation_spec import build_ace_spec


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger("musiclite-generator")
TOKEN = os.environ.get("MUSIC_AI_GENERATOR_TOKEN", "")
OUTPUT_ROOT = Path(os.environ.get("MUSIC_AI_GENERATOR_OUTPUT_PATH", "/var/lib/musiclite/generator-output")).resolve()
PUBLIC_URL = os.environ.get("MUSIC_AI_GENERATOR_URL", "http://127.0.0.1:8091").rstrip("/")
CHECKPOINTS = os.environ.get("MUSIC_AI_GENERATOR_CHECKPOINTS_DIR", "/var/lib/musiclite/models")
MAX_DURATION = int(os.environ.get("MUSIC_AI_GENERATOR_MAX_DURATION", "180"))
MIN_FREE_VRAM_MB = int(os.environ.get("MUSIC_AI_MIN_FREE_VRAM_MB", "5200"))
INFERENCE_STEPS = int(os.environ.get("MUSIC_AI_GENERATOR_STEPS", "8"))
NEURAL_STEPS = int(os.environ.get("MUSIC_AI_NEURAL_STEPS", "12"))
MAX_NEURAL_CANDIDATES = int(os.environ.get("MUSIC_AI_NEURAL_MAX_CANDIDATES", "4"))
NEURAL_SOURCE_ROOTS = [
    Path(p).resolve()
    for p in os.environ.get(
        "MUSIC_AI_NEURAL_SOURCE_ROOTS",
        "/var/lib/musiclite/studio-hq/output:/var/lib/musiclite/neural-studio",
    ).split(":")
    if p.strip()
]
QUANTIZATION = os.environ.get("MUSIC_AI_GENERATOR_QUANTIZATION", "auto").strip().lower()
DCW_MODE = os.environ.get("MUSIC_AI_GENERATOR_DCW_ENABLED", "auto").strip().lower()
VELOCITY_NORM = os.environ.get("MUSIC_AI_GENERATOR_VELOCITY_NORM_THRESHOLD", "auto").strip().lower()

if len(TOKEN) < 32:
    raise RuntimeError("MUSIC_AI_GENERATOR_TOKEN deve possuir ao menos 32 caracteres.")
if not 1 <= MAX_NEURAL_CANDIDATES <= 8:
    raise RuntimeError("MUSIC_AI_NEURAL_MAX_CANDIDATES deve ficar entre 1 e 8.")

os.environ["ACESTEP_CHECKPOINTS_DIR"] = CHECKPOINTS
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="MusicLite Generator", docs_url=None, redoc_url=None, openapi_url=None)
_generation_lock = threading.Lock()
_handler_lock = threading.Lock()
_dit_handler = None


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
    if DCW_MODE in {"true", "1", "yes", "on"}:
        return True
    if DCW_MODE in {"false", "0", "no", "off"}:
        return False
    if DCW_MODE != "auto":
        raise RuntimeError("MUSIC_AI_GENERATOR_DCW_ENABLED possui valor inválido.")
    return _select_quantization() != "w8a8_dynamic"


def _velocity_norm_threshold() -> float:
    if VELOCITY_NORM == "auto":
        return 2.0 if _select_quantization() == "w8a8_dynamic" else 0.0
    try:
        threshold = float(VELOCITY_NORM)
    except ValueError as exc:
        raise RuntimeError("MUSIC_AI_GENERATOR_VELOCITY_NORM_THRESHOLD é inválido.") from exc
    if threshold < 0 or threshold > 100:
        raise RuntimeError("MUSIC_AI_GENERATOR_VELOCITY_NORM_THRESHOLD está fora do limite.")
    return threshold


def _authorize(authorization: str | None) -> None:
    expected = f"Bearer {TOKEN}"
    if not authorization or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Não autorizado.")


def _free_vram_mb() -> int | None:
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
            capture_output=True, check=True, text=True, timeout=8,
        )
        values = [int(line.strip()) for line in result.stdout.splitlines() if line.strip()]
        return min(values) if values else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def _get_handler():
    global _dit_handler
    if _dit_handler is not None:
        return _dit_handler
    with _handler_lock:
        if _dit_handler is not None:
            return _dit_handler
        from acestep.handler import AceStepHandler
        handler = AceStepHandler()
        quantization = _select_quantization()
        LOGGER.info("Initializing ACE-Step with quantization=%s", quantization or "none")
        status, ready = handler.initialize_service(
            project_root="/opt/musiclite/generator",
            config_path="acestep-v15-turbo",
            device="cuda",
            use_flash_attention=False,
            compile_model=True,
            offload_to_cpu=True,
            offload_dit_to_cpu=True,
            quantization=quantization,
            use_mlx_dit=False,
        )
        if not ready:
            LOGGER.error("ACE-Step initialization failed: %s", status)
            raise RuntimeError("O gerador não pôde ser inicializado.")
        _dit_handler = handler
        return handler


def _release_own_handler() -> None:
    global _dit_handler
    with _handler_lock:
        handler = _dit_handler
        _dit_handler = None
    if handler is not None:
        del handler
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
    except Exception:
        LOGGER.warning("Could not clear MusicLite CUDA cache after failure", exc_info=True)


def _check_resources() -> None:
    free_vram = _free_vram_mb()
    if free_vram is None or free_vram < MIN_FREE_VRAM_MB:
        raise HTTPException(status_code=503, detail="Recursos temporariamente indisponíveis.")


def _safe_source_audio(raw: Any) -> Path:
    value = str(raw or "").strip()
    if not value:
        raise HTTPException(status_code=422, detail="source_audio é obrigatório.")
    path = Path(value).resolve()
    if not path.is_file() or path.suffix.lower() not in {".wav", ".flac", ".mp3", ".ogg"}:
        raise HTTPException(status_code=422, detail="source_audio não é um arquivo de áudio válido.")
    if not any(path == root or root in path.parents for root in NEURAL_SOURCE_ROOTS):
        raise HTTPException(status_code=403, detail="source_audio está fora das áreas permitidas.")
    return path


def _bounded_float(value: Any, default: float, low: float, high: float, label: str) -> float:
    try:
        parsed = float(default if value in (None, "") else value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"{label} inválido.") from exc
    if not low <= parsed <= high:
        raise HTTPException(status_code=422, detail=f"{label} deve ficar entre {low} e {high}.")
    return parsed


def _bounded_int(value: Any, default: int, low: int, high: int, label: str) -> int:
    try:
        parsed = int(default if value in (None, "") else value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"{label} inválido.") from exc
    if not low <= parsed <= high:
        raise HTTPException(status_code=422, detail=f"{label} deve ficar entre {low} e {high}.")
    return parsed


def _neural_caption(raw: Any) -> str:
    text = " ".join(str(raw or "").split()).strip()
    if not text:
        raise HTTPException(status_code=422, detail="caption é obrigatório.")
    text = text[:900]
    direction = (
        "professional human studio performance, continuous natural acoustic detail, "
        "coherent musician interaction, expressive microtiming, realistic attacks and releases, "
        "natural room depth, convincing instrument resonance, no MIDI feel, no cheap sampler feel, "
        "no synthetic demo sound"
    )
    return f"{text}. Production direction: {direction}"[:1200]


def _candidate_strengths(base: float, count: int, exploration: bool) -> list[tuple[str, float | None]]:
    strengths = [
        ("cover-controlled", min(0.90, base + 0.17)),
        ("cover-balanced", base),
        ("cover-creative", max(0.20, base - 0.17)),
    ]
    if exploration:
        strengths.append(("free-neural", None))
    while len(strengths) < count:
        delta = 0.08 if len(strengths) % 2 == 0 else -0.08
        strengths.append(("cover-alt", max(0.20, min(0.90, base + delta))))
    return strengths[:count]


def _validate_generated(path: Path, job_dir: Path) -> Path:
    generated = path.resolve()
    if not generated.is_file() or job_dir not in generated.parents or generated.stat().st_size < 1024:
        raise RuntimeError("O gerador não produziu um arquivo válido.")
    return generated


def _generate_one(params, job_dir: Path, seed: int):
    from acestep.inference import GenerationConfig, generate_music
    from acestep.llm_inference import LLMHandler
    config = GenerationConfig(batch_size=1, use_random_seed=False, seeds=[seed], audio_format="wav")
    result = generate_music(_get_handler(), LLMHandler(), params, config, save_dir=str(job_dir))
    if not result.success or not result.audios:
        raise RuntimeError(result.error or "ACE-Step retornou resultado vazio.")
    generated = _validate_generated(Path(str(result.audios[0].get("path", ""))), job_dir)
    return generated, result.audios[0].get("params") or {}


@app.get("/health")
def health(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _authorize(authorization)
    free_vram = _free_vram_mb()
    return {
        "online": True,
        "backend": "ace-step-1.5",
        "neural_studio": "0.4.0",
        "model_ready": _dit_handler is not None,
        "busy": _generation_lock.locked(),
        "free_vram_mb": free_vram,
        "resources_ready": free_vram is not None and free_vram >= MIN_FREE_VRAM_MB,
        "neural_steps": NEURAL_STEPS,
        "max_neural_candidates": MAX_NEURAL_CANDIDATES,
    }


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
        _check_resources()
        from acestep.inference import GenerationParams
        job_id = str(uuid.uuid4())
        job_dir = OUTPUT_ROOT / job_id
        job_dir.mkdir(mode=0o750)
        params = GenerationParams(
            task_type="text2music", caption=spec["caption"], lyrics=spec["lyrics"],
            instrumental=spec["instrumental"], vocal_language=spec["vocal_language"],
            bpm=spec["bpm"], keyscale=spec["keyscale"], timesignature=spec["timesignature"],
            duration=spec["duration"], inference_steps=INFERENCE_STEPS,
            shift=3.0, infer_method="ode", thinking=False,
            use_cot_metas=False, use_cot_caption=False, use_cot_lyrics=False, use_cot_language=False,
            dcw_enabled=_dcw_enabled(), velocity_norm_threshold=_velocity_norm_threshold(),
        )
        generated, _ = _generate_one(params, job_dir, random.SystemRandom().randint(1, 2_147_483_000))
        return {"job_id": job_id, "audio_url": f"{PUBLIC_URL}/files/{job_id}/{generated.name}"}
    except HTTPException as exc:
        if exc.status_code >= 500:
            _release_own_handler()
        raise
    except Exception:
        LOGGER.exception("Unexpected generation failure")
        _release_own_handler()
        raise HTTPException(status_code=503, detail="A geração de áudio falhou temporariamente.")
    finally:
        _generation_lock.release()


@app.post("/neuralize")
def neuralize(payload: dict[str, Any], authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _authorize(authorization)
    source = _safe_source_audio(payload.get("source_audio"))
    caption = _neural_caption(payload.get("caption"))
    candidate_count = _bounded_int(payload.get("candidate_count"), min(4, MAX_NEURAL_CANDIDATES), 1, MAX_NEURAL_CANDIDATES, "candidate_count")
    base_strength = _bounded_float(payload.get("cover_strength"), 0.55, 0.10, 0.95, "cover_strength")
    exploration = bool(payload.get("exploration", True))
    instrumental = bool(payload.get("instrumental", True))
    lyrics = str(payload.get("lyrics") or "").strip()
    if instrumental:
        lyrics = "[Instrumental]"
    elif not lyrics:
        raise HTTPException(status_code=422, detail="lyrics é obrigatório quando instrumental=false.")
    if not instrumental and _select_quantization() == "w8a8_dynamic":
        raise HTTPException(status_code=422, detail="A GPU atual não comporta com segurança a geração vocal neural; use instrumental=true.")
    bpm = payload.get("bpm")
    if bpm not in (None, ""):
        bpm = _bounded_int(bpm, 120, 30, 300, "bpm")
    keyscale = " ".join(str(payload.get("keyscale") or "").split())[:40]
    try:
        duration = float(payload.get("duration") or -1)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="duration inválido.") from exc
    if duration > MAX_DURATION:
        raise HTTPException(status_code=422, detail=f"duration não pode ultrapassar {MAX_DURATION}s.")
    if not _generation_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Já existe uma geração em andamento.")
    try:
        _check_resources()
        from acestep.inference import GenerationParams
        job_id = str(uuid.uuid4())
        job_dir = OUTPUT_ROOT / job_id
        job_dir.mkdir(mode=0o750)
        plan = _candidate_strengths(base_strength, candidate_count, exploration)
        candidates: list[dict[str, Any]] = []
        failures: list[dict[str, str]] = []
        for index, (mode, strength) in enumerate(plan, start=1):
            seed = random.SystemRandom().randint(1, 2_147_483_000)
            take_dir = job_dir / f"take-{index:02d}"
            take_dir.mkdir(mode=0o750)
            common = dict(
                caption=caption, lyrics=lyrics, instrumental=instrumental, bpm=bpm, keyscale=keyscale,
                timesignature="4", duration=duration, inference_steps=NEURAL_STEPS, shift=3.0,
                infer_method="ode", thinking=False, use_cot_metas=False, use_cot_caption=False,
                use_cot_lyrics=False, use_cot_language=False, dcw_enabled=_dcw_enabled(),
                velocity_norm_threshold=_velocity_norm_threshold(),
            )
            if strength is None:
                params = GenerationParams(task_type="text2music", **common)
            else:
                params = GenerationParams(task_type="cover", src_audio=str(source), audio_cover_strength=float(strength), **common)
            try:
                generated, ace_params = _generate_one(params, take_dir, seed)
                candidates.append({
                    "mode": mode, "cover_strength": strength,
                    "seed": int(ace_params.get("seed", seed)), "path": str(generated),
                    "audio_url": f"{PUBLIC_URL}/files/{job_id}/{take_dir.name}/{generated.name}",
                })
            except Exception as exc:
                LOGGER.warning("Neural take %s failed: %s", index, exc, exc_info=True)
                failures.append({"mode": mode, "error": str(exc)})
        if not candidates:
            raise RuntimeError("Nenhum take neural foi produzido.")
        ranking = rank_candidates([c["path"] for c in candidates], reference=source)
        by_path = {row["path"]: row for row in ranking}
        for candidate in candidates:
            candidate["critic"] = by_path.get(candidate["path"], {})
        candidates.sort(key=lambda row: row.get("critic", {}).get("technical_rank_score", 0.0), reverse=True)
        best = candidates[0]
        return {
            "job_id": job_id, "backend": "ace-step-1.5-cover", "neural_studio": "0.4.0",
            "source_audio": str(source), "caption": caption,
            "candidate_count_requested": candidate_count, "candidate_count_generated": len(candidates),
            "failures": failures, "best_path": best["path"], "best_audio_url": best["audio_url"],
            "best": best, "candidates": candidates,
        }
    except HTTPException as exc:
        if exc.status_code >= 500:
            _release_own_handler()
        raise
    except Exception:
        LOGGER.exception("Neural Studio generation failed")
        _release_own_handler()
        raise HTTPException(status_code=503, detail="A ressíntese neural falhou temporariamente.")
    finally:
        _generation_lock.release()


@app.get("/files/{job_id}/{filename:path}")
def download(job_id: str, filename: str, authorization: str | None = Header(default=None)):
    _authorize(authorization)
    try:
        uuid.UUID(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.") from exc
    relative = Path(filename)
    if relative.is_absolute() or ".." in relative.parts:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")
    path = (OUTPUT_ROOT / job_id / relative).resolve()
    job_root = (OUTPUT_ROOT / job_id).resolve()
    if job_root not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")
    return FileResponse(path, media_type="audio/wav", filename=path.name)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("MUSIC_AI_GENERATOR_PORT", "8091")), workers=1)
