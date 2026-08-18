"""Client/orchestrator for the local ACE-Step Neural Studio backend.

HQ 0.7 keeps the deterministic reference as the musical director, then uses
ACE-Step Cover for texture/timbre realism. Electronic genres get their own
caption, candidate preference, and final mastering instead of inheriting the
acoustic-band wording used by rock/sertanejo.
"""
from __future__ import annotations

import json
import shutil
import subprocess
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
    profiles = {
        "rock": (
            "professional modern rock studio production, human band performance, realistic acoustic drums, "
            "organic electric guitars and bass, coherent room depth, expressive microtiming, natural attacks and releases"
        ),
        "sertanejo": (
            "contemporary Brazilian sertanejo universitario studio production, real steel-string acoustic guitar, "
            "natural acoustic drums and electric bass, tasteful accordion and piano, human phrasing, believable room acoustics"
        ),
        "funk": (
            "authentic modern Brazilian funk carioca baile production, preserve the exact tamborzao swing and syncopation, "
            "tight dry kick, deep controlled mono sub 808, crisp clap, shuffled hats, organic agogo and percussion, "
            "powerful club low end, sparse verses and explosive drops, electronic production rather than an acoustic band, "
            "no rock drums, no sertanejo, no EDM festival drop, no cheap sampler feel, no obvious MIDI feel"
        ),
        "hiphop": (
            "luxury southern American hip-hop production, slow confident half-time pocket, massive controlled 808, "
            "hard dry kick and snare, tasteful hat rolls, dark piano, cinematic brass and strings, expensive spacious mix, "
            "no rock drums, no EDM, no cartoon synth brass, no obvious MIDI feel"
        ),
    }
    core = profiles.get(genre, profiles["sertanejo"])
    if user:
        core = f"{user}. Production direction: {core}"
    return core[:1100]


def _genre_preference(genre: str, candidate: dict[str, Any], target_strength: float) -> float:
    critic = candidate.get("critic") or {}
    technical = float(critic.get("technical_rank_score") or 0.0)
    corr = critic.get("reference_envelope_correlation")
    corr = float(corr) if corr is not None else 0.0
    strength = candidate.get("cover_strength")
    if strength is None:
        # Free text-to-music can be interesting for acoustic genres, but for
        # electronic groove references it is much more likely to lose the beat.
        strength_bonus = -12.0 if genre in {"funk", "hiphop"} else -1.0
    else:
        distance = abs(float(strength) - float(target_strength))
        strength_bonus = max(-8.0, 7.0 - distance * 30.0)
    structure_bonus = max(-4.0, min(8.0, corr * 8.0))
    if genre in {"funk", "hiphop"}:
        structure_bonus *= 1.35
    return technical + strength_bonus + structure_bonus


def _rerank_for_genre(result: dict[str, Any], genre: str, target_strength: float) -> dict[str, Any]:
    candidates = list(result.get("candidates") or [])
    if not candidates:
        return result
    for candidate in candidates:
        candidate["musiclite_quality_score"] = round(
            _genre_preference(genre, candidate, target_strength), 4
        )
    candidates.sort(key=lambda row: row.get("musiclite_quality_score", -999.0), reverse=True)
    best = candidates[0]
    result["candidates"] = candidates
    result["best"] = best
    result["best_path"] = best.get("path")
    result["best_audio_url"] = best.get("audio_url")
    result["musiclite_selection"] = {
        "profile": "hq07-genre-aware",
        "genre": genre,
        "target_cover_strength": target_strength,
        "criterion": "technical quality + reference structure + genre cover preference",
    }
    return result


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
    # For electronic genres a free text2music candidate usually destroys the
    # deterministic groove. Keep all takes in Cover mode unless explicitly
    # using the backend directly.
    effective_exploration = bool(exploration) and genre not in {"funk", "hiphop"}
    payload = {
        "source_audio": str(reference),
        "caption": build_production_caption(genre, prompt),
        "instrumental": instrumental,
        "lyrics": lyrics or "",
        "bpm": round(float(bpm)),
        "duration": measured_duration,
        "candidate_count": int(candidates),
        "cover_strength": float(cover_strength),
        "exploration": effective_exploration,
    }
    result = _post_json("/neuralize", payload)
    return _rerank_for_genre(result, genre, float(cover_strength))


def _master_filter(genre: str) -> str | None:
    if genre == "funk":
        return (
            "highpass=f=20,"
            "equalizer=f=46:t=q:w=.75:g=1.0,"
            "equalizer=f=240:t=q:w=1.0:g=-0.7,"
            "equalizer=f=5200:t=q:w=.9:g=.5,"
            "acompressor=threshold=.30:ratio=1.22:attack=24:release=145:makeup=1.02,"
            "alimiter=limit=.95,"
            "loudnorm=I=-10.5:TP=-0.8:LRA=6"
        )
    if genre == "hiphop":
        return (
            "highpass=f=20,"
            "equalizer=f=48:t=q:w=.75:g=.8,"
            "equalizer=f=280:t=q:w=1.0:g=-.5,"
            "acompressor=threshold=.31:ratio=1.20:attack=28:release=160:makeup=1.02,"
            "alimiter=limit=.95,"
            "loudnorm=I=-11:TP=-0.8:LRA=7"
        )
    return None


def publish_best(neural_result: dict[str, Any], target: str | Path, genre: str | None = None) -> Path:
    best = Path(str(neural_result.get("best_path") or "")).resolve()
    if not best.is_file():
        raise RuntimeError("O backend neural não retornou best_path válido.")
    target = Path(target).resolve()
    if OUTPUT.resolve() not in target.parents:
        raise RuntimeError("Destino neural precisa ficar dentro do OUTPUT do Studio HQ.")
    target.parent.mkdir(parents=True, exist_ok=True)
    filt = _master_filter(str(genre or ""))
    if not filt:
        shutil.copy2(best, target)
        return target
    # Keep the ACE take untouched in the generator output and publish a final
    # club/mastering pass as the Studio HQ result. Fall back to raw copy if the
    # local ffmpeg build rejects a filter.
    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error", "-i", str(best),
                "-af", filt, "-ar", "48000", "-c:a", "pcm_s24le", str(target),
            ],
            check=True,
            timeout=900,
        )
    except (OSError, subprocess.SubprocessError):
        shutil.copy2(best, target)
    return target
