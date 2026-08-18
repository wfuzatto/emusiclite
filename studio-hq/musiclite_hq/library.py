from pathlib import Path
from .config import SAMPLES
from .genres import normalize_genre

def _find(root: Path, predicates):
    candidates = list(root.rglob("*.sfz"))
    for pred in predicates:
        hits = [p for p in candidates if pred(p.name.lower(), str(p).lower())]
        if hits:
            return sorted(hits, key=lambda p: len(str(p)))[0]
    return candidates[0] if candidates else None

def all_instruments():
    drums = _find(SAMPLES/"drums"/"NakedDrums", [
        lambda n,p: "gm" in n,
        lambda n,p: "basic" in n,
        lambda n,p: True,
    ])
    bass = _find(SAMPLES/"bass"/"BlackAndBlue", [
        lambda n,p: "normal" in n and "keysw" not in n,
        lambda n,p: "dark" in n and "normal" in n,
        lambda n,p: True,
    ])
    guitar_acoustic = _find(SAMPLES/"guitar"/"SteelAcoustic", [
        lambda n,p: "steel" in n,
        lambda n,p: "guitar" in n,
        lambda n,p: True,
    ])
    guitar_electric = _find(SAMPLES/"guitar"/"Emilyguitar", [
        lambda n,p: n == "emily_basic.sfz",
        lambda n,p: "basic" in n,
        lambda n,p: "clean" in n,
        lambda n,p: True,
    ])
    piano = _find(SAMPLES/"piano"/"Salamander", [
        lambda n,p: "salamander grand piano v3" in n,
        lambda n,p: "salaman" in n,
        lambda n,p: True,
    ])
    accordion = _find(SAMPLES/"accordion"/"ButtonAccordionHN", [
        lambda n,p: "accordion" in n,
        lambda n,p: True,
    ])
    return {
        "drums": drums,
        "bass": bass,
        "guitar_acoustic": guitar_acoustic,
        "guitar_electric": guitar_electric,
        "piano": piano,
        "accordion": accordion,
    }

def instruments(genre="sertanejo"):
    genre = normalize_genre(genre)
    lib = all_instruments()
    if genre == "rock":
        return {
            "drums": lib["drums"],
            "bass": lib["bass"],
            "guitar_l": lib["guitar_electric"],
            "guitar_r": lib["guitar_electric"],
        }
    return {
        "drums": lib["drums"],
        "bass": lib["bass"],
        "guitar": lib["guitar_acoustic"],
        "piano": lib["piano"],
        "accordion": lib["accordion"],
    }
