from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
import uuid
import json
import traceback

from .config import OUTPUT, WORK
from .arranger import create_test_midis
from .library import instruments, all_instruments
from .render import render_sfz
from .mix import mix_master
from .genres import normalize_genre, genre_info

app = FastAPI(title="MusicLite Studio HQ", version="0.2.0")

class TestReq(BaseModel):
    seconds: int = Field(60, ge=15, le=240)
    bpm: float = Field(126, ge=60, le=190)
    genre: Optional[str] = Field(default=None, max_length=80)
    prompt: Optional[str] = Field(default=None, max_length=1000)

@app.get("/health")
def health():
    libs = all_instruments()
    return {
        "ok": True,
        "version": "0.2.0",
        "supported_genres": list(genre_info().keys()),
        "libraries": {k: (str(v) if v else None) for k, v in libs.items()},
    }

@app.get("/genres")
def genres():
    return genre_info()

@app.post("/render/test")
def render_test(req: TestReq):
    try:
        genre = normalize_genre(req.genre, req.prompt)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    job = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    work = WORK / job
    work.mkdir(parents=True, exist_ok=True)

    try:
        libs = instruments(genre)
        missing = [k for k, v in libs.items() if not v]
        if missing:
            raise RuntimeError(
                f"Bibliotecas ausentes para {genre}: " + ", ".join(missing)
            )

        midis, bars = create_test_midis(work, req.seconds, req.bpm, genre)
        stems = {}
        for name, midi in midis.items():
            wav = work / f"{name}_raw.wav"
            render_sfz(libs[name], midi, wav)
            stems[name] = wav

        final = OUTPUT / f"{job}-{genre}-hq-test.wav"
        mix_master(stems, final, work, genre)

        manifest = {
            "job": job,
            "genre": genre,
            "prompt": req.prompt,
            "bpm": req.bpm,
            "bars": bars,
            "final": str(final),
            "instruments": {k: str(v) for k, v in libs.items()},
            "stems": {k: str(v) for k, v in stems.items()},
        }
        (work / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return manifest
    except Exception as e:
        (work / "ERROR.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise HTTPException(status_code=500, detail=str(e))
