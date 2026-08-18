from pathlib import Path
import subprocess
from .genres import normalize_genre
from .amp import process_rock_guitar,process_rock_bass,convolve_room

def _run(cmd):subprocess.run(cmd,check=True)
def _prep(src,dst,kind,genre):
    if genre=="rock" and kind in ("guitar_l","guitar_r"):
        process_rock_guitar(src,dst,"left" if kind.endswith("_l") else "right");return
    if genre=="rock" and kind=="bass":process_rock_bass(src,dst);return
    if genre=="funk" and kind=="drums":
        filt="highpass=f=25,lowpass=f=19500,equalizer=f=95:t=q:w=1.0:g=1.2,equalizer=f=320:t=q:w=1.1:g=-1.0,equalizer=f=5200:t=q:w=.8:g=.8,acompressor=threshold=.20:ratio=2.2:attack=8:release=90:makeup=1.12"
    elif genre=="funk" and kind=="sub":
        filt="highpass=f=21,lowpass=f=230,equalizer=f=52:t=q:w=.75:g=1.6,equalizer=f=115:t=q:w=.9:g=-.7,acompressor=threshold=.18:ratio=2.4:attack=16:release=130:makeup=1.08"
    else:
        filt={
            "drums":"highpass=f=26,lowpass=f=19000",
            "bass":"highpass=f=31,lowpass=f=7500,equalizer=f=160:t=q:w=.8:g=.8,acompressor=threshold=.16:ratio=2.0:attack=22:release=170:makeup=1.08",
            "guitar":"highpass=f=72,lowpass=f=15500,equalizer=f=300:t=q:w=.8:g=-.8,acompressor=threshold=.24:ratio=1.25:attack=20:release=150",
            "piano":"highpass=f=48,lowpass=f=17500,equalizer=f=260:t=q:w=.9:g=-.7,acompressor=threshold=.25:ratio=1.25:attack=28:release=200",
            "accordion":"highpass=f=95,lowpass=f=14500,equalizer=f=1900:t=q:w=1:g=-.6,acompressor=threshold=.25:ratio=1.22:attack=22:release=180",
        }[kind]
    _run(["ffmpeg","-y","-loglevel","error","-i",str(src),"-af",filt,"-c:a","pcm_s24le",str(dst)])
def _mix_inputs(prepared,volumes,dst,limit=.91):
    order=list(prepared);cmd=["ffmpeg","-y","-loglevel","error"]
    for n in order:cmd += ["-i",str(prepared[n])]
    chains=[];labels=[]
    for i,n in enumerate(order):
        lab=f"m{i}";chains.append(f"[{i}:a]volume={volumes.get(n,.7)}[{lab}]");labels.append(f"[{lab}]")
    chains.append("".join(labels)+f"amix=inputs={len(labels)}:normalize=0,alimiter=limit={limit}[m]")
    _run(cmd+["-filter_complex",";".join(chains),"-map","[m]",str(dst)])
def mix_master(stems,out:Path,work:Path,genre="sertanejo"):
    genre=normalize_genre(genre);prepared={}
    for kind,src in stems.items():
        dst=work/f"{kind}_prep.wav";_prep(src,dst,kind,genre);prepared[kind]=dst
    if genre=="rock":
        volumes={"drums":.92,"bass":.82,"guitar_l":.72,"guitar_r":.72};room_names=[n for n in ("guitar_l","guitar_r") if n in prepared];room_amount=.075;target="-13.5";lra="9";limit=.91
    elif genre=="funk":
        # Club-oriented but still leaves true-peak headroom. Keep sub mono from source SFZ.
        volumes={"drums":.96,"sub":.92};room_names=[];room_amount=0;target="-11.5";lra="7";limit=.94
    else:
        volumes={"drums":.88,"bass":.82,"guitar":.84,"piano":.42,"accordion":.48};room_names=[n for n in ("guitar","piano","accordion") if n in prepared];room_amount=.105;target="-14";lra="10";limit=.91
    dry=work/"dry_mix.wav";_mix_inputs(prepared,volumes,dry,limit=limit)
    if room_names:
        room_src=work/"room_send.wav";_mix_inputs({n:prepared[n] for n in room_names},{n:.45 for n in room_names},room_src)
        room=work/"room.wav";convolve_room(room_src,room);pre=work/"premaster.wav"
        _run(["ffmpeg","-y","-loglevel","error","-i",str(dry),"-i",str(room),"-filter_complex",f"[1:a]volume={room_amount}[r];[0:a][r]amix=2:normalize=0,alimiter=limit=.93[p]","-map","[p]",str(pre)])
    else:pre=dry
    if genre=="funk":
        master=f"highpass=f=20,equalizer=f=42:t=q:w=.8:g=.7,acompressor=threshold=.30:ratio=1.22:attack=24:release=150,alimiter=limit=.95,loudnorm=I={target}:TP=-0.8:LRA={lra}"
    else:
        master=f"highpass=f=23,acompressor=threshold=.34:ratio=1.16:attack=38:release=250,loudnorm=I={target}:TP=-1.0:LRA={lra}"
    _run(["ffmpeg","-y","-loglevel","error","-i",str(pre),"-af",master,"-ar","48000","-c:a","pcm_s24le",str(out)])
    return out
