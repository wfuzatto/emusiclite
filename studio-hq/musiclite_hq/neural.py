"""Client/orchestrator for the local ACE-Step Neural Studio backend."""
from __future__ import annotations

import json
import shutil
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import soundfile as sf

from .config import NEURAL_GENERATOR_TOKEN, NEURAL_GENERATOR_URL, NEURAL_TIMEOUT, OUTPUT


def _post_json(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    if len(NEURAL_GENERATOR_TOKEN) < 32:
        raise RuntimeError(
            "MUSIC_AI_GENERATOR_TOKEN não está disponível no serviço HQ. "
            "Execute o upgrade_hq4.sh para instalar o drop-in do systemd."
        )
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"{NEURAL_GENERATOR_URL}{path}",
        data=data,
        headers={
            "Authorization": f"Bearer {NEURAL_GENERATOR_TOKEN}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=NEURAL_TIMEOUT) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Neural backend HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Neural backend indisponível: {exc}") from exc
    result = json.loads(body)
    if not isinstance(result, dict):
        raise RuntimeError("Neural backend retornou resposta inválida.")
    return result


def build_production_caption(genre: str, prompt: str | None) -> str:
    user = " ".join((prompt or "").split()).strip()
    genre_text = "rock" if genre == "rock" else "sertanejo brasileiro contemporâneo"
    core = (
        f"{genre_text}, professional commercial studio recording, "
        "human musicians playing together, memorable natural musical phrasing, "
        "organic dynamics, realistic instruments, coherent room acoustics, "
        "convincing transitions between intro verse chorus bridge and outro"
    )
    if user:
        core = f"{user}. {core}"
    return core[:900]


def neuralize_reference(
    reference: str | Path,
    *,
    genre: str,
    prompt: str | None,
    bpm: float,
    seconds: int,
    candidates: int = 4,
    cover_strength: float = 0.55,
    exploration: bool = True,
    instrumental: bool = True,
    lyrics: str | None = None,
) -> dict[str, Any]:
    reference = Path(reference).resolve()
    info = sf.info(str(reference))
    measured_duration = round(float(info.frames) / float(info.samplerate), 3)
    payload = {
        "source_audio": str(reference),
        "caption": build_production_caption(genre, prompt),
        "instrumental": instrumental,
        "lyrics": lyrics or "",
        "bpm": round(float(bpm)),
        "duration": measured_duration,
        "candidate_count": int(candidates),
        "cover_strength": float(cover_strength),
        "exploration": bool(exploration),
    }
    return _post_json("/neuralize", payload)


def publish_best(neural_result: dict[str, Any], target: str | Path) -> Path:
    best = Path(str(neural_result.get("best_path") or "")).resolve()
    if not best.is_file():
        raise RuntimeError("O backend neural não retornou best_path válido.")
    target = Path(target).resolve()
    if OUTPUT.resolve() not in target.parents:
        raise RuntimeError("Destino neural precisa ficar dentro do OUTPUT do Studio HQ.")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(best, target)
    return target
