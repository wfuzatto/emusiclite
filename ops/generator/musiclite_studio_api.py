#!/opt/musiclite/studio-venv/bin/python
"""CPU-only sampled MIDI studio backend for MusicLite.

It creates a symbolic multitrack arrangement, renders each MIDI stem through a
recorded sample library (SoundFont/SFZ), and mixes/master the resulting stems.
"""

from __future__ import annotations

import hmac
import json
import logging
import os
import shutil
import subprocess
import threading
import uuid
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse

import sys

STUDIO_CODE = Path(os.environ.get("MUSIC_AI_STUDIO_CODE_PATH", "/opt/musiclite/studio")).resolve()
if str(STUDIO_CODE) not in sys.path:
    sys.path.insert(0, str(STUDIO_CODE))

from musiclite_arranger import arrange  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger("musiclite-studio")

TOKEN = os.environ.get("MUSIC_AI_STUDIO_TOKEN", os.environ.get("MUSIC_AI_GENERATOR_TOKEN", ""))
PORT = int(os.environ.get("MUSIC_AI_STUDIO_PORT", "8093"))
PUBLIC_URL = os.environ.get("MUSIC_AI_STUDIO_URL", f"http://127.0.0.1:{PORT}").rstrip("/")
OUTPUT_ROOT = Path(os.environ.get("MUSIC_AI_STUDIO_OUTPUT_PATH", "/var/lib/musiclite/studio-output")).resolve()
MANIFEST_PATH = Path(os.environ.get("MUSIC_AI_STUDIO_MANIFEST", "/etc/musiclite/studio-instruments.json")).resolve()
GROOVES_PATH = Path(os.environ.get("MUSIC_AI_STUDIO_GROOVES", "/opt/musiclite/studio/grooves.json")).resolve()
MAX_DURATION = min(180, max(30, int(os.environ.get("MUSIC_AI_STUDIO_MAX_DURATION", "180"))))
FLUIDSYNTH_BIN = os.environ.get("MUSIC_AI_FLUIDSYNTH_BIN", shutil.which("fluidsynth") or "/usr/bin/fluidsynth")
SFIZZ_RENDER_BIN = os.environ.get("MUSIC_AI_SFIZZ_RENDER_BIN", shutil.which("sfizz_render") or "/usr/local/bin/sfizz_render")
FFMPEG_BIN = os.environ.get("MUSIC_AI_FFMPEG_BIN", shutil.which("ffmpeg") or "/usr/bin/ffmpeg")

if len(TOKEN) < 32:
    raise RuntimeError("MUSIC_AI_STUDIO_TOKEN deve possuir ao menos 32 caracteres.")

OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
app = FastAPI(title="MusicLite Studio Renderer", docs_url=None, redoc_url=None, openapi_url=None)
_generation_lock = threading.Lock()


def _authorize(authorization: str | None) -> None:
    expected = f"Bearer {TOKEN}"
    if not authorization or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Não autorizado.")


def _load_manifest() -> dict[str, Any]:
    if not MANIFEST_PATH.is_file():
        raise HTTPException(status_code=503, detail="Manifesto de instrumentos do Studio Real não foi instalado.")
    try:
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Manifesto de instrumentos do Studio Real é inválido.") from exc
    if not isinstance(data, dict) or not isinstance(data.get("instruments"), dict):
        raise HTTPException(status_code=503, detail="Manifesto de instrumentos do Studio Real está incompleto.")
    return data


def _instrument_path(manifest: dict[str, Any], instrument: str) -> tuple[dict[str, Any], Path]:
    config = manifest["instruments"].get(instrument)
    if not isinstance(config, dict):
        raise HTTPException(status_code=503, detail=f"Instrumento {instrument} não está configurado no Studio Real.")
    root = Path(str(manifest.get("sample_root") or "/var/lib/musiclite/studio-samples")).resolve()
    file_value = str(config.get("file") or "")
    path = Path(file_value)
    if not path.is_absolute():
        path = (root / path).resolve()
    if not path.is_file():
        raise HTTPException(status_code=503, detail=f"Banco de samples ausente para {instrument}: {path.name}.")
    return config, path


def _run(command: list[str], timeout: int, label: str) -> None:
    LOGGER.info("%s: %s", label, " ".join(command))
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=503, detail=f"Tempo limite ao executar {label}.") from exc
    if result.returncode != 0:
        LOGGER.error("%s failed rc=%s stdout=%s stderr=%s", label, result.returncode, result.stdout[-2000:], result.stderr[-4000:])
        raise HTTPException(status_code=503, detail=f"Falha ao executar {label}.")


def _render_stem(manifest: dict[str, Any], stem: dict[str, Any], job_dir: Path) -> Path:
    instrument = str(stem["instrument"])
    config, bank = _instrument_path(manifest, instrument)
    engine = str(config.get("engine") or "fluidsynth").lower()
    midi_path = Path(str(stem["midi_path"])).resolve()
    wav_path = job_dir / f"{stem['name']}.wav"
    gain = float(config.get("gain", 0.75))

    if engine == "fluidsynth":
        if not Path(FLUIDSYNTH_BIN).is_file() and shutil.which(FLUIDSYNTH_BIN) is None:
            raise HTTPException(status_code=503, detail="FluidSynth não está instalado no servidor.")
        command = [
            FLUIDSYNTH_BIN, "-ni", "-q", "-R", "0", "-C", "0",
            "-r", "48000", "-g", f"{gain:.3f}", "-F", str(wav_path),
            str(bank), str(midi_path),
        ]
        _run(command, 600, f"FluidSynth/{instrument}")
    elif engine == "sfizz":
        if not Path(SFIZZ_RENDER_BIN).is_file() and shutil.which(SFIZZ_RENDER_BIN) is None:
            raise HTTPException(status_code=503, detail="sfizz_render não está instalado no servidor.")
        command = [
            SFIZZ_RENDER_BIN, "--sfz", str(bank), "--midi", str(midi_path),
            "--wav", str(wav_path), "--samplerate", "48000", "--use-eot",
        ]
        _run(command, 600, f"sfizz/{instrument}")
    else:
        raise HTTPException(status_code=503, detail=f"Engine de sample inválido para {instrument}.")

    if not wav_path.is_file() or wav_path.stat().st_size < 2048:
        raise HTTPException(status_code=503, detail=f"O instrumento {instrument} não produziu áudio válido.")
    stem["gain"] = gain
    stem["sample_bank"] = bank.name
    return wav_path


def _mix(stems: list[tuple[dict[str, Any], Path]], output: Path) -> None:
    if not stems:
        raise HTTPException(status_code=503, detail="Nenhuma pista foi renderizada.")
    command = [FFMPEG_BIN, "-hide_banner", "-loglevel", "error", "-y"]
    for _, wav in stems:
        command.extend(["-i", str(wav)])

    filters: list[str] = []
    labels: list[str] = []
    for index, (stem, _) in enumerate(stems):
        name = str(stem.get("name", ""))
        gain = float(stem.get("gain", 0.75))
        # Each group gets a small tonal correction before the final bus.
        chain = f"[{index}:a]volume={gain:.3f}"
        if "bass" in name:
            chain += ",highpass=f=28,lowpass=f=6500"
        elif "drum" in name:
            chain += ",highpass=f=32"
        elif "guitar" in name:
            chain += ",highpass=f=70,lowpass=f=14500"
        elif "accordion" in name:
            chain += ",highpass=f=95,lowpass=f=13000"
        elif "piano" in name:
            chain += ",highpass=f=55,lowpass=f=15000"
        label = f"s{index}"
        filters.append(chain + f"[{label}]")
        labels.append(f"[{label}]")

    mix = "".join(labels) + f"amix=inputs={len(labels)}:duration=longest:dropout_transition=0:normalize=0"
    mix += ",acompressor=threshold=0.12:ratio=2.4:attack=18:release=220:makeup=1.15"
    mix += ",alimiter=limit=0.96:attack=5:release=80,aresample=48000[out]"
    filters.append(mix)
    command.extend(["-filter_complex", ";".join(filters), "-map", "[out]", "-ac", "2", "-ar", "48000", "-c:a", "pcm_s24le", str(output)])
    _run(command, 900, "mix/master Studio Real")
    if not output.is_file() or output.stat().st_size < 4096:
        raise HTTPException(status_code=503, detail="O mix final do Studio Real não foi produzido.")


def _dependencies() -> dict[str, Any]:
    manifest_ok = MANIFEST_PATH.is_file()
    grooves_ok = GROOVES_PATH.is_file()
    fluidsynth_ok = bool(shutil.which(FLUIDSYNTH_BIN) or Path(FLUIDSYNTH_BIN).is_file())
    sfizz_ok = bool(shutil.which(SFIZZ_RENDER_BIN) or Path(SFIZZ_RENDER_BIN).is_file())
    ffmpeg_ok = bool(shutil.which(FFMPEG_BIN) or Path(FFMPEG_BIN).is_file())
    samples: dict[str, bool] = {}
    if manifest_ok:
        try:
            manifest = _load_manifest()
            for name in manifest["instruments"]:
                try:
                    _, path = _instrument_path(manifest, name)
                    samples[name] = path.is_file()
                except HTTPException:
                    samples[name] = False
        except HTTPException:
            pass
    return {
        "manifest": manifest_ok,
        "grooves": grooves_ok,
        "fluidsynth": fluidsynth_ok,
        "sfizz_render": sfizz_ok,
        "ffmpeg": ffmpeg_ok,
        "samples": samples,
    }


@app.get("/health")
def health(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _authorize(authorization)
    deps = _dependencies()
    sample_values = list(deps["samples"].values())
    ready = deps["manifest"] and deps["grooves"] and deps["fluidsynth"] and deps["ffmpeg"] and bool(sample_values) and all(sample_values)
    return {"online": True, "backend": "studio-midi-sampled", "ready": ready, "busy": _generation_lock.locked(), "dependencies": deps}


@app.post("/generate")
def generate(payload: dict[str, Any], authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _authorize(authorization)
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="Especificação inválida.")
    if not bool(payload.get("instrumental", False)):
        raise HTTPException(status_code=422, detail="Studio Real atualmente renderiza somente instrumentais; use-o para a base instrumental.")
    try:
        duration = int(payload.get("duration_seconds") or 60)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Duração inválida.") from exc
    if duration < 30 or duration > MAX_DURATION:
        raise HTTPException(status_code=422, detail=f"Studio Real suporta duração entre 30 e {MAX_DURATION} segundos.")
    if not _generation_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Já existe uma renderização Studio Real em andamento.")
    try:
        manifest = _load_manifest()
        if not GROOVES_PATH.is_file():
            raise HTTPException(status_code=503, detail="Templates de groove do Studio Real não foram instalados.")
        job_id = str(uuid.uuid4())
        job_dir = OUTPUT_ROOT / job_id
        midi_dir = job_dir / "midi"
        job_dir.mkdir(mode=0o750, parents=True)
        midi_dir.mkdir(mode=0o750)
        arrangement = arrange(payload, midi_dir, GROOVES_PATH)
        rendered: list[tuple[dict[str, Any], Path]] = []
        for stem in arrangement["stems"]:
            rendered.append((stem, _render_stem(manifest, stem, job_dir)))
        final_path = job_dir / "musiclite-studio.wav"
        _mix(rendered, final_path)
        metadata = {
            "job_id": job_id,
            "model": "studio-midi-sampled",
            "arrangement": arrangement,
            "rendered_stems": [
                {"name": stem["name"], "sample_bank": stem.get("sample_bank"), "gain": stem.get("gain")}
                for stem, _ in rendered
            ],
        }
        (job_dir / "render.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        return {
            "job_id": job_id,
            "audio_url": f"{PUBLIC_URL}/files/{job_id}/{final_path.name}",
            "model": "studio-midi-sampled",
            "stems": metadata["rendered_stems"],
        }
    except HTTPException:
        raise
    except Exception as exc:
        LOGGER.exception("Unexpected Studio Real generation failure")
        raise HTTPException(status_code=503, detail=f"Falha temporária no Studio Real: {type(exc).__name__}.") from exc
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
    return FileResponse(path, media_type="audio/wav", filename="musiclite-studio.wav")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=PORT, workers=1)
