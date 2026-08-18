from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from pathlib import Path
from datetime import datetime
import uuid, json, traceback

from .config import OUTPUT, WORK
from .arranger import create_test_midis
from .library import instruments
from .render import render_sfz
from .mix import mix_master

app=FastAPI(title="MusicLite Studio HQ", version="0.1.0")

class TestReq(BaseModel):
    seconds:int=Field(60, ge=15, le=240)
    bpm:float=Field(126, ge=60, le=190)

@app.get("/health")
def health():
    libs=instruments()
    return {"ok":True,"instruments":{k:(str(v) if v else None) for k,v in libs.items()}}

@app.post("/render/test")
def render_test(req:TestReq):
    job=datetime.now().strftime("%Y%m%d-%H%M%S")+"-"+uuid.uuid4().hex[:6]
    work=WORK/job
    work.mkdir(parents=True,exist_ok=True)
    try:
        libs=instruments()
        missing=[k for k,v in libs.items() if not v]
        if missing:
            raise RuntimeError("Bibliotecas ausentes: "+", ".join(missing))
        midis,bars=create_test_midis(work, req.seconds, req.bpm)
        stems={}
        for name,midi in midis.items():
            wav=work/f"{name}_raw.wav"
            render_sfz(libs[name],midi,wav)
            stems[name]=wav
        final=OUTPUT/f"{job}-hq-test.wav"
        mix_master(stems,final,work)
        manifest={
            "job":job,"bpm":req.bpm,"bars":bars,
            "final":str(final),
            "instruments":{k:str(v) for k,v in libs.items()},
            "stems":{k:str(v) for k,v in stems.items()},
        }
        (work/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
        return manifest
    except Exception as e:
        (work/"ERROR.txt").write_text(traceback.format_exc(),encoding="utf-8")
        raise HTTPException(status_code=500,detail=str(e))
