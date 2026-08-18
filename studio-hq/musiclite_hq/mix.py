from pathlib import Path
import subprocess
from .genres import normalize_genre
from .amp import process_rock_guitar,process_rock_bass,convolve_room

def _run(cmd):subprocess.run(cmd,check=True)
def _prep(src,dst,kind,genre):
    if genre=="rock" and kind in ("guitar_l","guitar_r"):
        process_rock_guitar(src,dst,"left" if kind.endswith("_l") else "right");return
    if genre=="rock" and kind=="bass":process_rock_bass(src,dst);return
    filt={
        "drums":"highpass=f=26,lowpass=f=19000",
        "bass":"highpass=f=31,lowpass=f=7500,equalizer=f=160:t=q:w=.8:g=.8,acompressor=threshold=.16:ratio=2.0:attack=22:release=170:makeup=1.08",
        "guitar":"highpass=f=72,lowpass=f=15500,equalizer=f=300:t=q:w=.8:g=-.8,acompressor=threshold=.24:ratio=1.25:attack=20:release=150",
        "piano":"highpass=f=48,lowpass=f=17500,equalizer=f=260:t=q:w=.9:g=-.7,acompressor=threshold=.25:ratio=1.25:attack=28:release=200",
        "accordion":"highpass=f=95,lowpass=f=14500,equalizer=f=1900:t=q:w=1:g=-.6,acompressor=threshold=.25:ratio=1.22:attack=22:release=180",
    }[kind]
    _run(["ffmpeg","-y","-loglevel","error","-i",str(src),"-af",filt,"-c:a","pcm_s24le",str(dst)])
def _mix_inputs(prepared,volumes,dst):
    order=list(prepared);cmd=["ffmpeg","-y","-loglevel","error"]
    for n in order:cmd += ["-i",str(prepared[n])]
    chains=[];labels=[]
    for i,n in enumerate(order):
        lab=f"m{i}";chains.append(f"[{i}:a]volume={volumes.get(n,.7)}[{lab}]");labels.append(f"[{lab}]")
    chains.append("".join(labels)+f"amix=inputs={len(labels)}:normalize=0,alimiter=limit=.91[m]")
    _run(cmd+["-filter_complex",";".join(chains),"-map","[m]",str(dst)])
def mix_master(stems,out:Path,work:Path,genre="sertanejo"):
    genre=normalize_genre(genre);prepared={}
    for kind,src in stems.items():
        dst=work/f"{kind}_prep.wav";_prep(src,dst,kind,genre);prepared[kind]=dst
    if genre=="rock":
        volumes={"drums":.92,"bass":.82,"guitar_l":.72,"guitar_r":.72};room_names=[n for n in ("guitar_l","guitar_r") if n in prepared];room_amount=.075;target="-13.5";lra="9"
    else:
        volumes={"drums":.88,"bass":.82,"guitar":.84,"piano":.42,"accordion":.48};room_names=[n for n in ("guitar","piano","accordion") if n in prepared];room_amount=.105;target="-14";lra="10"
    dry=work/"dry_mix.wav";_mix_inputs(prepared,volumes,dry)
    if room_names:
        room_src=work/"room_send.wav";_mix_inputs({n:prepared[n] for n in room_names},{n:.45 for n in room_names},room_src)
        room=work/"room.wav";convolve_room(room_src,room);pre=work/"premaster.wav"
        _run(["ffmpeg","-y","-loglevel","error","-i",str(dry),"-i",str(room),"-filter_complex",f"[1:a]volume={room_amount}[r];[0:a][r]amix=2:normalize=0,alimiter=limit=.93[p]","-map","[p]",str(pre)])
    else:pre=dry
    _run(["ffmpeg","-y","-loglevel","error","-i",str(pre),"-af",f"highpass=f=23,acompressor=threshold=.34:ratio=1.16:attack=38:release=250,loudnorm=I={target}:TP=-1.0:LRA={lra}","-ar","48000","-c:a","pcm_s24le",str(out)])
    return out
