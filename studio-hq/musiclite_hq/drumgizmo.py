from pathlib import Path
import subprocess
import shutil
import xml.etree.ElementTree as ET
from .config import DRUMKITS, DRUMGIZMO, SAMPLE_RATE

GM={"kick":36,"snare":38,"sidestick":37,"hh_closed":42,"hh_pedal":44,"hh_open":46,"crash":49,"ride":51,"ride_bell":53,"tom_high":48,"tom_mid":47,"tom_low":45,"tom_floor":41}

def _root_tag(path):
    try: return ET.parse(path).getroot().tag.lower()
    except Exception: return ""

def resolve_kit(genre):
    preferred="CrocellKit" if genre=="rock" else "DRSKit"
    roots=[DRUMKITS/preferred]+[p for p in DRUMKITS.glob("*") if p.is_dir() and p.name!=preferred]
    for root in roots:
        if not root.exists(): continue
        kits=[p for p in root.rglob("*.xml") if _root_tag(p).endswith("drumkit")]
        maps=[p for p in root.rglob("*.xml") if _root_tag(p).endswith("midimap")]
        if kits and maps:
            kit=sorted(kits,key=lambda p:("full" not in p.name.lower(),len(str(p))))[0]
            midimap=sorted(maps,key=lambda p:("full" not in p.name.lower(),len(str(p))))[0]
            return {"name":preferred,"root":root,"kit":kit,"midimap":midimap}
    return None

def _parse_midimap(path):
    result=[]
    try:
        root=ET.parse(path).getroot()
        for m in root.iter():
            if m.tag.lower().endswith("map") and "note" in m.attrib and "instr" in m.attrib:
                result.append((int(m.attrib["note"]),m.attrib["instr"]))
    except Exception: pass
    return result

def _choose(items,keywords,fallback):
    lowered=[(note,name,name.lower()) for note,name in items]
    for kwset in keywords:
        for note,name,low in lowered:
            if all(k in low for k in kwset): return note
    return fallback

def note_map(genre):
    spec=resolve_kit(genre)
    if not spec: return dict(GM)
    items=_parse_midimap(spec["midimap"])
    return {
        "kick":_choose(items,[("kdrum",),("kick",)],GM["kick"]),
        "snare":_choose(items,[("snare",)],GM["snare"]),
        "sidestick":_choose(items,[("snare","rest"),("side",)],GM["sidestick"]),
        "hh_closed":_choose(items,[("hihat","closed"),("hh","closed")],GM["hh_closed"]),
        "hh_pedal":_choose(items,[("hihat","pedal"),("hh","pedal")],GM["hh_pedal"]),
        "hh_open":_choose(items,[("hihat","open"),("hh","open")],GM["hh_open"]),
        "crash":_choose(items,[("crash",),("china",)],GM["crash"]),
        "ride":_choose(items,[("ride","r"),("ride",)],GM["ride"]),
        "ride_bell":_choose(items,[("ride","bell"),("bell",)],GM["ride_bell"]),
        "tom_high":_choose(items,[("tom1",),("tom","1")],GM["tom_high"]),
        "tom_mid":_choose(items,[("tom2",),("tom","2")],GM["tom_mid"]),
        "tom_low":_choose(items,[("tom3",),("tom","3")],GM["tom_low"]),
        "tom_floor":_choose(items,[("ftom",),("tom4",),("floor",)],GM["tom_floor"]),
    }

def available():
    return bool(shutil.which(DRUMGIZMO) and resolve_kit("rock") and resolve_kit("sertanejo"))

def render_multimic(midi:Path,work:Path,genre:str):
    exe=shutil.which(DRUMGIZMO); spec=resolve_kit(genre)
    if not exe or not spec: return None
    outdir=work/"drumgizmo"; outdir.mkdir(parents=True,exist_ok=True)
    prefix=outdir/"mic_"
    cmd=[exe,"-i","midifile","-I",f"file={midi},midimap={spec['midimap']}","-o","wavfile","-O",f"file={prefix},srate={SAMPLE_RATE}","-s",str(spec["kit"])]
    subprocess.run(cmd,check=True,cwd=spec["root"])
    wavs=sorted(outdir.glob("mic_*.wav"))
    if not wavs: raise RuntimeError("DrumGizmo terminou sem produzir canais WAV.")
    return {"engine":"drumgizmo","kit":str(spec["kit"]),"midimap":str(spec["midimap"]),"channels":wavs}
