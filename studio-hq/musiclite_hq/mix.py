from pathlib import Path
import subprocess, shutil

def _run(cmd):
    subprocess.run(cmd, check=True)

def prepare_stem(src: Path, dst: Path, kind: str):
    filters = {
        "drums": "highpass=f=28,lowpass=f=19000,equalizer=f=260:t=q:w=0.8:g=-1.2,acompressor=threshold=0.18:ratio=1.55:attack=18:release=160:makeup=1.1",
        "bass": "highpass=f=32,lowpass=f=9000,equalizer=f=220:t=q:w=1.0:g=-1.5,acompressor=threshold=0.16:ratio=2.0:attack=22:release=180:makeup=1.15",
        "guitar": "highpass=f=72,lowpass=f=15500,equalizer=f=270:t=q:w=0.8:g=-1.0,equalizer=f=3600:t=q:w=1:g=-0.8,acompressor=threshold=0.23:ratio=1.35:attack=18:release=140:makeup=1.04",
        "piano": "highpass=f=45,lowpass=f=17500,equalizer=f=250:t=q:w=0.9:g=-0.8,acompressor=threshold=0.24:ratio=1.35:attack=25:release=190:makeup=1.03",
        "accordion": "highpass=f=95,lowpass=f=14500,equalizer=f=1800:t=q:w=1.0:g=-0.8,acompressor=threshold=0.24:ratio=1.30:attack=20:release=170:makeup=1.03",
    }[kind]
    _run(["ffmpeg","-y","-loglevel","error","-i",str(src),"-af",filters,str(dst)])

def mix_master(stems, out: Path, work: Path):
    order=("drums","bass","guitar","piano","accordion")
    prepared={}
    for k in order:
        d=work/f"{k}_prep.wav"
        prepare_stem(stems[k],d,k)
        prepared[k]=d

    dry = work/"dry_mix.wav"
    cmd=["ffmpeg","-y","-loglevel","error"]
    for k in order:
        cmd += ["-i",str(prepared[k])]
    filt=(
        "[0:a]volume=0.88[d];"
        "[1:a]volume=0.86[b];"
        "[2:a]volume=0.82[g];"
        "[3:a]volume=0.48[p];"
        "[4:a]volume=0.56[a];"
        "[d][b][g][p][a]amix=inputs=5:normalize=0,alimiter=limit=0.90[dry]"
    )
    cmd += ["-filter_complex",filt,"-map","[dry]",str(dry)]
    _run(cmd)

    roomsrc=work/"room_src.wav"
    _run(["ffmpeg","-y","-loglevel","error",
          "-i",str(prepared["drums"]),"-i",str(prepared["guitar"]),
          "-i",str(prepared["piano"]),"-i",str(prepared["accordion"]),
          "-filter_complex",
          "[0:a]volume=.30[a];[1:a]volume=.48[b];[2:a]volume=.28[c];[3:a]volume=.38[d];"
          "[a][b][c][d]amix=inputs=4:normalize=0[r]",
          "-map","[r]",str(roomsrc)])
    room=work/"room.wav"
    if shutil.which("sox"):
        _run(["sox",str(roomsrc),str(room),"reverb","16","47","54","84","0","0"])
    else:
        _run(["ffmpeg","-y","-loglevel","error","-i",str(roomsrc),"-af",
              "aecho=0.7:0.38:31|47|71:0.16|0.11|0.07",str(room)])

    premaster=work/"premaster.wav"
    _run(["ffmpeg","-y","-loglevel","error","-i",str(dry),"-i",str(room),
          "-filter_complex","[1:a]volume=.16[r];[0:a][r]amix=inputs=2:normalize=0,alimiter=limit=.92[m]",
          "-map","[m]",str(premaster)])

    _run(["ffmpeg","-y","-loglevel","error","-i",str(premaster),
          "-af","highpass=f=24,acompressor=threshold=.30:ratio=1.22:attack=32:release=230,loudnorm=I=-14:TP=-1.0:LRA=10",
          "-ar","48000","-c:a","pcm_s24le",str(out)])
    return out
