"""Validation and mapping for MusicLite -> ACE-Step generation requests."""

from __future__ import annotations

from typing import Any


LANGUAGE_CODES = {
    "portugues": "pt",
    "português": "pt",
    "english": "en",
    "ingles": "en",
    "inglês": "en",
    "spanish": "es",
    "espanhol": "es",
}


def _text(value: Any, limit: int) -> str:
    return " ".join(str(value or "").strip().split())[:limit]


def build_ace_spec(payload: dict[str, Any], *, max_duration: int = 180) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("A especificação deve ser um objeto JSON.")

    prompt = _text(payload.get("prompt"), 6000)
    if not prompt:
        raise ValueError("O prompt musical é obrigatório.")

    instrumental = bool(payload.get("instrumental", False))
    lyrics = _text(payload.get("lyrics"), 12000)
    if instrumental:
        lyrics = "[Instrumental]"
    elif not lyrics:
        raise ValueError("A letra é obrigatória para música vocal.")

    try:
        duration = int(payload.get("duration_seconds") or 30)
    except (TypeError, ValueError) as exc:
        raise ValueError("A duração é inválida.") from exc
    if duration < 10 or duration > max_duration:
        raise ValueError(f"A duração deve ficar entre 10 e {max_duration} segundos.")

    bpm_raw = payload.get("bpm")
    bpm = None
    if bpm_raw not in (None, ""):
        try:
            bpm = int(bpm_raw)
        except (TypeError, ValueError) as exc:
            raise ValueError("O BPM é inválido.") from exc
        if bpm < 30 or bpm > 300:
            raise ValueError("O BPM deve ficar entre 30 e 300.")

    details = []
    for label, key in (
        ("genre", "genre"),
        ("subgenre", "subgenre"),
        ("mood", "mood"),
        ("theme", "theme"),
        ("instruments", "instruments"),
        ("voice", "voice_type"),
        ("structure", "structure"),
        ("descriptive references", "descriptive_references"),
    ):
        value = payload.get(key)
        if isinstance(value, list):
            value = ", ".join(_text(item, 200) for item in value if _text(item, 200))
        value = _text(value, 1000)
        if value:
            details.append(f"{label}: {value}")
    caption = prompt if not details else f"{prompt}. " + "; ".join(details)

    language = _text(payload.get("language"), 40).lower()
    language_code = LANGUAGE_CODES.get(language, language[:8] or "unknown")

    return {
        "caption": caption,
        "lyrics": lyrics,
        "instrumental": instrumental,
        "duration": float(duration),
        "bpm": bpm,
        "keyscale": _text(payload.get("key"), 40),
        "timesignature": "4",
        "vocal_language": language_code,
    }

