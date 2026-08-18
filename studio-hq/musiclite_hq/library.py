from pathlib import Path
from .config import SAMPLES
from .genres import normalize_genre

def _find(root: Path, include=(), exclude=()):
    if not root.exists():
        return None
    candidates = list(root.rglob("*.sfz"))
    candidates = [p for p in candidates if not any(x in p.name.lower() for x in exclude)]
    if include:
        hits = [p for p in candidates if any(x in p.name.lower() for x in include)]
        if hits:
            candidates = hits
    if not candidates:
        return None
    return max(candidates, key=lambda p: (-(len(p.relative_to(root).parts)), p.stat().st_size))

def all_instruments():
    return {
        "drums_fallback": _find(SAMPLES/"drums"/"NakedDrums", ("gm","basic")),
        "bass_hq": _find(SAMPLES/"bass"/"StandardBass", ("bass","standard"), ("slap",)),
        "bass_fallback": _find(SAMPLES/"bass"/"BlackAndBlue", ("normal","dark")),
        "guitar_metal_hq": _find(SAMPLES/"guitar"/"MetalGTX", ("metal","gtx","guitar")),
        "guitar_standard_hq": _find(SAMPLES/"guitar"/"StandardGuitar", ("standard","guitar")),
        "guitar_electric_fallback": _find(SAMPLES/"guitar"/"Emilyguitar", ("basic","clean")),
        "guitar_acoustic": _find(SAMPLES/"guitar"/"SteelAcoustic", ("steel","guitar")),
        "piano": _find(SAMPLES/"piano"/"Salamander", ("salamander",)),
        "accordion": _find(SAMPLES/"accordion"/"ButtonAccordionHN", ("accordion",)),
        "funk_kit": _find(SAMPLES/"funk"/"kit", ("funk","kit")),
        "funk_808": _find(SAMPLES/"funk"/"808", ("808","sub")),
        "hiphop_piano": _find(SAMPLES/"hiphop"/"piano", ("hiphop","upright","piano")),
        "hiphop_brass": _find(SAMPLES/"hiphop"/"brass", ("hiphop","brass","trumpet")),
        "hiphop_strings": _find(SAMPLES/"hiphop"/"strings", ("hiphop","strings","violin")),
    }

def instruments(genre="sertanejo"):
    genre = normalize_genre(genre)
    lib = all_instruments()
    if genre == "hiphop":
        return {
            "drums": lib["funk_kit"],
            "sub": lib["funk_808"],
            "piano": lib["hiphop_piano"],
            "brass": lib["hiphop_brass"],
            "strings": lib["hiphop_strings"],
        }
    if genre == "funk":
        return {"drums": lib["funk_kit"], "sub": lib["funk_808"]}
    bass = lib["bass_hq"] or lib["bass_fallback"]
    if genre == "rock":
        guitar = lib["guitar_metal_hq"] or lib["guitar_standard_hq"] or lib["guitar_electric_fallback"]
        return {"bass": bass, "guitar_l": guitar, "guitar_r": guitar}
    return {
        "bass": bass,
        "guitar": lib["guitar_acoustic"],
        "piano": lib["piano"],
        "accordion": lib["accordion"],
    }

def fallback_instrument(name: str, genre="sertanejo"):
    genre = normalize_genre(genre)
    lib = all_instruments()
    if genre in ("funk","hiphop"):
        return lib["piano"] if genre=="hiphop" and name=="piano" else None
    if name == "bass":
        return lib["bass_fallback"]
    if name.startswith("guitar_") and genre == "rock":
        return lib["guitar_electric_fallback"]
    if name == "guitar":
        return lib["guitar_acoustic"]
    if name == "piano":
        return lib["piano"]
    if name == "accordion":
        return lib["accordion"]
    return None
