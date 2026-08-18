from pathlib import Path
import subprocess, shutil
from .config import SFIZZ_RENDER, SAMPLE_RATE, RENDER_QUALITY, POLYPHONY

def render_sfz(sfz: Path, midi: Path, wav: Path):
    if not sfz or not sfz.exists():
        raise FileNotFoundError(f"SFZ não encontrado: {sfz}")
    exe = shutil.which(SFIZZ_RENDER) or (SFIZZ_RENDER if Path(SFIZZ_RENDER).exists() else None)
    if not exe:
        raise RuntimeError("sfizz_render não encontrado")
    cmd = [
        str(exe),
        "--sfz", str(sfz),
        "--midi", str(midi),
        "--wav", str(wav),
        "--samplerate", str(SAMPLE_RATE),
        "--quality", str(RENDER_QUALITY),
        "--polyphony", str(POLYPHONY),
        "--use-eot",
    ]
    subprocess.run(cmd, check=True)
    return wav
