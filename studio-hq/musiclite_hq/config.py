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

# Neural Studio 0.4 talks only to the loopback ACE-Step adapter. The bearer
# token is loaded into the HQ service via /etc/musiclite/worker.env.
NEURAL_GENERATOR_URL = os.getenv(
    "MUSICLITE_NEURAL_GENERATOR_URL",
    os.getenv("MUSIC_AI_GENERATOR_URL", "http://127.0.0.1:8091"),
).rstrip("/")
NEURAL_GENERATOR_TOKEN = os.getenv("MUSIC_AI_GENERATOR_TOKEN", "")
NEURAL_TIMEOUT = int(os.getenv("MUSICLITE_NEURAL_TIMEOUT", os.getenv("MUSIC_AI_GENERATOR_TIMEOUT", "3600")))

for p in (BASE, SAMPLES, DRUMKITS, IRS, OUTPUT, WORK):
    p.mkdir(parents=True, exist_ok=True)
