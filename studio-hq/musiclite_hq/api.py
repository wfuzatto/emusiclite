from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
import uuid, json, traceback

from .config import OUTPUT, WORK, NEURAL_GENERATOR_TOKEN, NEURAL_GENERATOR_URL
from .arranger import create_test_midis
from .library import instruments, all_instruments, fallback_instrument
from .render import render_sfz
from .mix import mix_master
from .genres import normalize_genre, genre_info
from .song_form import serialize_form
from .drumgizmo import render_multimic, available as drumgizmo_available
from .drum_mix import mix_multimic
from .neural import neuralize_reference, publish_best

app = FastAPI(title="MusicLite Studio HQ + Neural", version="0.6.0")

class TestReq(BaseModel):
    seconds: int = Field(60, ge=15, le=300)
    bpm: float = Field(126, ge=60, le=190)
    genre: Optional[str] = Field(default=None, max_length=80)
    prompt: Optional[str] = Field(default=None, max_length=1000)

class NeuralReq(TestReq):
    candidates: int = Field(4, ge=1, le=8)
    cover_strength: float = Field(0.55, ge=0.10, le=0.95)
    exploration: bool = True
    instrumental: bool = True
    lyrics: Optional[str] = Field(default=None, max_length=12000)

@app.get("/health")
def health():
    libs = all_instruments()
    return {
        "ok": True,
        "version": "0.6.0",
        "hq_reference_engine": "0.6",
        "neural_engine": "ace-step-1.5-cover",
        "neural_configured": len(NEURAL_GENERATOR_TOKEN) >= 32,
        "neural_generator_url": NEURAL_GENERATOR_URL,
        "supported_genres": list(genre_info().keys()),
        "drumgizmo_multimic": drumgizmo_available(),
        "funk_engine_ready": bool(libs.get("funk_kit") and libs.get("funk_808")),
        "hiphop_engine_ready": bool(libs.get("funk_kit") and libs.get("funk_808") and libs.get("hiphop_piano") and libs.get("hiphop_brass") and libs.get("hiphop_strings")),
        "libraries": {k: (str(v) if v else None) for k, v in libs.items()},
    }

@app.get("/genres")
def genres(): return genre_info()

def _render_reference(req: TestReq) -> dict:
    try:
        genre = normalize_genre(req.genre, req.prompt)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    job = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    work = WORK / job;work.mkdir(parents=True, exist_ok=True)
    try:
        libs = instruments(genre)
        missing = [k for k, v in libs.items() if not v]
        if missing:
            if genre == "funk":hint = " Rode studio-hq/install_funk_hq.sh."
            elif genre == "hiphop":hint = " Rode studio-hq/install_hiphop_hq.sh."
            else:hint = ""
            raise RuntimeError(f"Bibliotecas ausentes para {genre}: " + ", ".join(missing) + hint)

        midis, bars, form = create_test_midis(work, req.seconds, req.bpm, genre)
        stems = {};render_info = {"drums_engine": "sfz_fallback", "library_fallbacks": {}}

        if genre in ("funk","hiphop"):
            for name,midi in midis.items():
                wav=work/f"{name}_raw.wav";render_sfz(libs[name],midi,wav);stems[name]=wav
            if genre == "funk":
                render_info.update({
                    "drums_engine":"funk_hq05_vcsl_hybrid",
                    "sub_engine":"musiclite_808_sfz",
                    "groove_engine":"funk_carioca_humanized_16th",
                })
            else:
                render_info.update({
                    "drums_engine":"hiphop_hq06_halftime_hybrid",
                    "sub_engine":"musiclite_808_sfz",
                    "piano_engine":"vsco2ce_upright_multisample",
                    "brass_engine":"vsco2ce_trumpet_staccato",
                    "strings_engine":"vsco2ce_violin_section_sustain",
                    "groove_engine":"american_southern_luxury_hiphop_humanized",
                })
        else:
            try:dg = render_multimic(midis["drums"], work, genre)
            except Exception as exc:
                dg = None;render_info["drumgizmo_error"] = str(exc)
            if dg:
                drums = work / "drums_multimic.wav";mix_multimic(dg["channels"], drums, genre);stems["drums"] = drums
                render_info.update({"drums_engine":"drumgizmo_multimic","drumkit":dg["kit"],"drum_channels":[str(x) for x in dg["channels"]]})
            else:
                fallback = all_instruments()["drums_fallback"]
                if not fallback:raise RuntimeError("Nem DrumGizmo nem bateria SFZ fallback estão disponíveis.")
                wav = work / "drums_raw.wav";render_sfz(fallback, midis["drums"], wav);stems["drums"] = wav
            for name, midi in midis.items():
                if name == "drums":continue
                wav = work / f"{name}_raw.wav";selected = libs[name]
                try:render_sfz(selected, midi, wav)
                except Exception as exc:
                    fallback = fallback_instrument(name, genre)
                    if not fallback or fallback == selected:raise
                    render_info["library_fallbacks"][name] = {"requested":str(selected),"fallback":str(fallback),"reason":str(exc)}
                    render_sfz(fallback, midi, wav);libs[name] = fallback
                stems[name] = wav

        if genre=="funk":engine_suffix="hq5-reference";render_mode="hq5_funk_reference"
        elif genre=="hiphop":engine_suffix="hiphop-hq6-reference";render_mode="hq6_american_hiphop_reference"
        else:engine_suffix="hq3-reference";render_mode="hq3_reference"
        final = OUTPUT / f"{job}-{genre}-{engine_suffix}.wav";mix_master(stems, final, work, genre)
        credits = []
        if render_info["drums_engine"] == "drumgizmo_multimic":credits.append("Drum samples rendered from DrumGizmo.org kit; see upstream kit license/attribution.")
        if genre == "funk":credits.append("Organic percussion layers from VCSL (CC0); electronic kick/tamborzao/hats/808 generated locally by MusicLite.")
        if genre == "hiphop":credits.append("Piano, brass and string source samples from VSCO 2 CE (CC0); electronic drums/808 use the MusicLite local electronic base.")
        manifest = {
            "job":job,"version":"0.6.0","render_mode":render_mode,"genre":genre,"prompt":req.prompt,"bpm":req.bpm,"bars":bars,
            "form":serialize_form(form),"final":str(final),"instruments":{k:str(v) for k,v in libs.items()},"stems":{k:str(v) for k,v in stems.items()},"credits":credits,**render_info,
        }
        (work / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        return manifest
    except HTTPException:raise
    except Exception as exc:
        (work / "ERROR.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@app.post("/render/test")
def render_test(req: TestReq): return _render_reference(req)

@app.post("/render/neural")
def render_neural(req: NeuralReq):
    reference = _render_reference(TestReq(seconds=req.seconds, bpm=req.bpm, genre=req.genre, prompt=req.prompt))
    genre = reference["genre"];work = WORK / reference["job"]
    try:
        result = neuralize_reference(reference["final"],genre=genre,prompt=req.prompt,bpm=req.bpm,seconds=req.seconds,candidates=req.candidates,cover_strength=req.cover_strength,exploration=req.exploration,instrumental=req.instrumental,lyrics=req.lyrics)
        target = OUTPUT / f"{reference['job']}-{genre}-neural04.wav";publish_best(result, target)
        manifest = {"job":reference["job"],"version":"0.6.0","render_mode":"neural_hybrid","genre":genre,"prompt":req.prompt,"bpm":req.bpm,"reference_audio":reference["final"],"final":str(target),"neural_backend":result.get("backend"),"best":result.get("best"),"candidates":result.get("candidates", []),"candidate_failures":result.get("failures", []),"reference":reference}
        (work / "neural-manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8");return manifest
    except Exception as exc:
        (work / "NEURAL_ERROR.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
