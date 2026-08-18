from pathlib import Path
from .config import SAMPLES

def _find(root: Path, predicates):
    candidates = list(root.rglob("*.sfz"))
    for pred in predicates:
        hits = [p for p in candidates if pred(p.name.lower(), str(p).lower())]
        if hits:
            return sorted(hits, key=lambda p: len(str(p)))[0]
    return candidates[0] if candidates else None

def instruments():
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
    # Steel-string acoustic is the primary rhythm guitar for the HQ sertanejo test.
    guitar = _find(SAMPLES/"guitar"/"SteelAcoustic", [
        lambda n,p: "steel" in n,
        lambda n,p: "guitar" in n,
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
    return {"drums":drums, "bass":bass, "guitar":guitar, "piano":piano, "accordion":accordion}
