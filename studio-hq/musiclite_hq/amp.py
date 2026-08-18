from pathlib import Path
import shutil
import subprocess
from .config import IRS, SAMPLE_RATE

def _run(cmd): subprocess.run(cmd,check=True)
def _find_ir(tokens):
    candidates=[p for p in IRS.rglob("*") if p.is_file() and p.suffix.lower()==".wav"]
    for token_group in tokens:
        for p in candidates:
            low=p.name.lower()
            if all(t in low for t in token_group):return p
    return None

def cabinet_ir(side="left"):
    if side=="left":return _find_ir([("direct","cabinet","n3"),("cabinet","n3"),("direct","cabinet")])
    return _find_ir([("direct","cabinet","n4"),("cabinet","n4"),("direct","cabinet")])
def room_ir():return _find_ir([("nice","drum","room"),("small","drum","room"),("ruby","room")])

def _convolve(src:Path,ir:Path,dst:Path):
    ir48=dst.with_name(dst.stem+"_ir48.wav")
    _run(["ffmpeg","-y","-loglevel","error","-i",str(ir),"-ac","1","-ar",str(SAMPLE_RATE),"-c:a","pcm_s24le",str(ir48)])
    _run(["ffmpeg","-y","-loglevel","error","-i",str(src),"-i",str(ir48),"-filter_complex","[0:a][1:a]afir=dry=0:wet=1[a]","-map","[a]","-ar",str(SAMPLE_RATE),"-c:a","pcm_s24le",str(dst)])
    ir48.unlink(missing_ok=True)

def process_rock_guitar(src:Path,dst:Path,side:str):
    pre=dst.with_name(dst.stem+"_pre.wav");driven=dst.with_name(dst.stem+"_drive.wav")
    _run(["ffmpeg","-y","-loglevel","error","-i",str(src),"-af","highpass=f=72,lowpass=f=12500,volume=0.62","-ar",str(SAMPLE_RATE),"-c:a","pcm_s24le",str(pre)])
    if shutil.which("sox"):
        drive="13" if side=="left" else "15";tone="9" if side=="left" else "7"
        _run(["sox",str(pre),str(driven),"overdrive",drive,tone])
    else:
        _run(["ffmpeg","-y","-loglevel","error","-i",str(pre),"-af","acompressor=threshold=.12:ratio=3.2:attack=3:release=70",str(driven)])
    cab=cabinet_ir(side);convolved=dst.with_name(dst.stem+"_cab.wav")
    if cab:_convolve(driven,cab,convolved);source=convolved
    else:source=driven
    pan=("pan=stereo|c0=0.99*c0|c1=0.12*c1" if side=="left" else "pan=stereo|c0=0.12*c0|c1=0.99*c1")
    post="highpass=f=78,lowpass=f=10500,equalizer=f=240:t=q:w=.8:g=-1.8,equalizer=f=1650:t=q:w=.9:g=-.7,equalizer=f=3600:t=q:w=.9:g=1.1,acompressor=threshold=.19:ratio=1.65:attack=11:release=105:makeup=1.05,"+pan
    _run(["ffmpeg","-y","-loglevel","error","-i",str(source),"-af",post,"-ar",str(SAMPLE_RATE),"-c:a","pcm_s24le",str(dst)])
    for p in (pre,driven,convolved):p.unlink(missing_ok=True)

def process_rock_bass(src:Path,dst:Path):
    clean=dst.with_name(dst.stem+"_clean.wav");grit=dst.with_name(dst.stem+"_grit.wav")
    _run(["ffmpeg","-y","-loglevel","error","-i",str(src),"-af","highpass=f=31,lowpass=f=4300,equalizer=f=85:t=q:w=.7:g=1.2,acompressor=threshold=.15:ratio=2.6:attack=24:release=150:makeup=1.1",str(clean)])
    if shutil.which("sox"):_run(["sox",str(src),str(grit),"gain","-8","highpass","180","overdrive","7","6","lowpass","5200"])
    else:_run(["ffmpeg","-y","-loglevel","error","-i",str(src),"-af","highpass=f=180,acompressor=threshold=.1:ratio=4",str(grit)])
    _run(["ffmpeg","-y","-loglevel","error","-i",str(clean),"-i",str(grit),"-filter_complex","[0:a]volume=.88[c];[1:a]volume=.24[g];[c][g]amix=2:normalize=0,alimiter=limit=.91[a]","-map","[a]","-c:a","pcm_s24le",str(dst)])
    clean.unlink(missing_ok=True);grit.unlink(missing_ok=True)

def convolve_room(src:Path,dst:Path):
    ir=room_ir()
    if ir:_convolve(src,ir,dst)
    else:_run(["ffmpeg","-y","-loglevel","error","-i",str(src),"-af","aecho=.7:.35:29|43|67:.13|.09|.06",str(dst)])
