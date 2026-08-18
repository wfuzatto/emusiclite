from pathlib import Path
import os

BASE = Path(os.getenv("MUSICLITE_HQ_BASE", "/var/lib/musiclite/studio-hq"))
SAMPLES = Path(os.getenv("MUSICLITE_HQ_SAMPLES", str(BASE / "samples")))
DRUMKITS = Path(os.getenv("MUSICLITE_HQ_DRUMKITS", str(BASE / "drumkits")))
IRS = Path(os.getenv("MUSICLITE_HQ_IRS", str(BASE / "irs")))
OUTPUT = Path(os.getenv("MUSICLITE_HQ_OUTPUT", str(BASE / "output")))
WORK = Path(os.getenv("MUSICLITE_HQ_WORK", str(BASE / "work")))
SFIZZ_RENDER = os.getenv("SFIZZ_RENDER", "/usr/local/bin/sfizz_render")
DRUMGIZMO = os.getenv("DRUMGIZMO", "drumgizmo")
SAMPLE_RATE = int(os.getenv("MUSICLITE_HQ_SAMPLE_RATE", "48000"))
RENDER_QUALITY = int(os.getenv("MUSICLITE_HQ_RENDER_QUALITY", "10"))
POLYPHONY = int(os.getenv("MUSICLITE_HQ_POLYPHONY", "768"))

for p in (BASE, SAMPLES, DRUMKITS, IRS, OUTPUT, WORK):
    p.mkdir(parents=True, exist_ok=True)
