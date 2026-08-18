from pathlib import Path
import subprocess
import re

def _run(cmd): subprocess.run(cmd,check=True)
def _classify(name):
    n=name.lower()
    if "amb" in n or "room" in n:return "room"
    if "oh" in n or "overhead" in n:return "oh"
    if "kick" in n or "kdrum" in n:return "kick"
    if "snaretop" in n or ("snare" in n and "top" in n):return "snare_top"
    if "snarebottom" in n or ("snare" in n and "bottom" in n):return "snare_bottom"
    if "hihat" in n or "hat" in n:return "hat"
    if "ride" in n:return "ride"
    if "tom" in n:return "tom"
    return "other"
def _pan_for(name,kind):
    n=name.lower()
    if "left" in n or n.endswith("l") or "_l" in n:return (.96,.12)
    if "right" in n or n.endswith("r") or "_r" in n:return (.12,.96)
    if kind=="hat":return (.82,.38)
    if kind=="ride":return (.34,.86)
    if kind=="tom":
        digits=[int(x) for x in re.findall(r"\d+",n)]; d=digits[-1] if digits else 2
        return {1:(.82,.38),2:(.64,.55),3:(.45,.72),4:(.28,.88)}.get(d,(.55,.55))
    return (.70,.70)

def mix_multimic(channels,dst:Path,genre:str):
    cmd=["ffmpeg","-y","-loglevel","error"]
    for p in channels:cmd += ["-i",str(p)]
    chains=[];labels=[]
    for i,p in enumerate(channels):
        kind=_classify(p.stem);l,r=_pan_for(p.stem,kind)
        if kind=="kick":f="highpass=f=28,lowpass=f=9000,equalizer=f=62:t=q:w=.7:g=2.2,equalizer=f=330:t=q:w=1:g=-2.2,equalizer=f=3300:t=q:w=1:g=1.5,acompressor=threshold=.16:ratio=2.7:attack=15:release=110";vol=.76
        elif kind=="snare_top":f="highpass=f=75,lowpass=f=16000,equalizer=f=190:t=q:w=.8:g=1.2,equalizer=f=5200:t=q:w=1:g=1.5,acompressor=threshold=.18:ratio=2.0:attack=13:release=120";vol=.83
        elif kind=="snare_bottom":f="highpass=f=160,lowpass=f=14500,equalizer=f=6500:t=q:w=1:g=1.2";vol=.30
        elif kind=="oh":f="highpass=f=115,lowpass=f=17500,equalizer=f=6500:t=q:w=.8:g=.6";vol=.52
        elif kind=="room":f="highpass=f=100,lowpass=f=15000,acompressor=threshold=.22:ratio=1.35:attack=28:release=220";vol=.30 if genre=="rock" else .25
        elif kind=="hat":f="highpass=f=240,lowpass=f=17000,equalizer=f=8500:t=q:w=1:g=-.6";vol=.36
        elif kind=="ride":f="highpass=f=180,lowpass=f=17000";vol=.38
        elif kind=="tom":f="highpass=f=52,lowpass=f=12000,equalizer=f=420:t=q:w=.8:g=-1.0,acompressor=threshold=.20:ratio=1.6:attack=16:release=130";vol=.55
        else:f="highpass=f=35,lowpass=f=18000";vol=.30
        label=f"x{i}"
        chains.append(f"[{i}:a]{f},volume={vol},aformat=channel_layouts=mono,pan=stereo|c0={l}*c0|c1={r}*c0[{label}]");labels.append(f"[{label}]")
    chains.append("".join(labels)+f"amix=inputs={len(labels)}:normalize=0,alimiter=limit=.89[dry]")
    dry=dst.with_name(dst.stem+"_dry.wav")
    _run(cmd+["-filter_complex",";".join(chains),"-map","[dry]",str(dry)])
    parallel=dst.with_name(dst.stem+"_parallel.wav")
    _run(["ffmpeg","-y","-loglevel","error","-i",str(dry),"-af","acompressor=threshold=.10:ratio=4.5:attack=8:release=105:makeup=1.15",str(parallel)])
    blend=.16 if genre=="rock" else .10
    _run(["ffmpeg","-y","-loglevel","error","-i",str(dry),"-i",str(parallel),"-filter_complex",f"[1:a]volume={blend}[p];[0:a][p]amix=2:normalize=0,alimiter=limit=.90[m]","-map","[m]","-c:a","pcm_s24le",str(dst)])
    dry.unlink(missing_ok=True);parallel.unlink(missing_ok=True)
