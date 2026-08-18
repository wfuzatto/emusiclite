from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
import uuid, json, traceback

from .config import OUTPUT, WORK
from .arranger import create_test_midis
from .library import instruments, all_instruments, fallback_instrument
from .render import render_sfz
from .mix import mix_master
from .genres import normalize_genre, genre_info
from .song_form import serialize_form
from .drumgizmo import render_multimic, available as drumgizmo_available
from .drum_mix import mix_multimic

app=FastAPI(title="MusicLite Studio HQ",version="0.3.0")

class TestReq(BaseModel):
    seconds:int=Field(60,ge=15,le=300)
    bpm:float=Field(126,ge=60,le=190)
    genre:Optional[str]=Field(default=None,max_length=80)
    prompt:Optional[str]=Field(default=None,max_length=1000)

@app.get("/health")
def health():
    libs=all_instruments()
    return {"ok":True,"version":"0.3.0","supported_genres":list(genre_info().keys()),"drumgizmo_multimic":drumgizmo_available(),"libraries":{k:(str(v) if v else None) for k,v in libs.items()}}

@app.get("/genres")
def genres():return genre_info()

@app.post("/render/test")
def render_test(req:TestReq):
    try:genre=normalize_genre(req.genre,req.prompt)
    except ValueError as e:raise HTTPException(status_code=422,detail=str(e))
    job=datetime.now().strftime("%Y%m%d-%H%M%S")+"-"+uuid.uuid4().hex[:6];work=WORK/job;work.mkdir(parents=True,exist_ok=True)
    try:
        libs=instruments(genre);missing=[k for k,v in libs.items() if not v]
        if missing:raise RuntimeError(f"Bibliotecas ausentes para {genre}: "+", ".join(missing))
        midis,bars,form=create_test_midis(work,req.seconds,req.bpm,genre);stems={};render_info={"drums_engine":"sfz_fallback","library_fallbacks":{}}
        try:dg=render_multimic(midis["drums"],work,genre)
        except Exception as e:dg=None;render_info["drumgizmo_error"]=str(e)
        if dg:
            drums=work/"drums_multimic.wav";mix_multimic(dg["channels"],drums,genre);stems["drums"]=drums
            render_info.update({"drums_engine":"drumgizmo_multimic","drumkit":dg["kit"],"drum_channels":[str(x) for x in dg["channels"]]})
        else:
            fallback=all_instruments()["drums_fallback"]
            if not fallback:raise RuntimeError("Nem DrumGizmo nem bateria SFZ fallback estão disponíveis.")
            wav=work/"drums_raw.wav";render_sfz(fallback,midis["drums"],wav);stems["drums"]=wav
        for name,midi in midis.items():
            if name=="drums":continue
            wav=work/f"{name}_raw.wav";selected=libs[name]
            try:render_sfz(selected,midi,wav)
            except Exception as e:
                fallback=fallback_instrument(name,genre)
                if not fallback or fallback==selected:raise
                render_info["library_fallbacks"][name]={"requested":str(selected),"fallback":str(fallback),"reason":str(e)}
                render_sfz(fallback,midi,wav);libs[name]=fallback
            stems[name]=wav
        final=OUTPUT/f"{job}-{genre}-hq3.wav";mix_master(stems,final,work,genre)
        credits=[]
        if render_info["drums_engine"]=="drumgizmo_multimic":credits.append("Drum samples rendered from DrumGizmo.org kit; see upstream kit license/attribution.")
        manifest={"job":job,"version":"0.3.0","genre":genre,"prompt":req.prompt,"bpm":req.bpm,"bars":bars,"form":serialize_form(form),"final":str(final),"instruments":{k:str(v) for k,v in libs.items()},"stems":{k:str(v) for k,v in stems.items()},"credits":credits,**render_info}
        (work/"manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding="utf-8")
        return manifest
    except Exception as e:
        (work/"ERROR.txt").write_text(traceback.format_exc(),encoding="utf-8")
        raise HTTPException(status_code=500,detail=str(e))
