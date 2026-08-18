#!/usr/bin/env bash
set -Eeuo pipefail

BASE="/var/lib/musiclite/studio-hq"
APP="/opt/musiclite/studio-hq"
SAMPLES="$BASE/samples/chillstep"
KIT="$SAMPLES/kit"
SUB="$SAMPLES/sub"
PAD="$SAMPLES/pad"
PLUCK="$SAMPLES/pluck"
LEAD="$SAMPLES/lead"
CACHE="${MUSICLITE_CHILLSTEP_CACHE:-$HOME/.cache/musiclite-chillstep-hq8}"
BUILD="$CACHE/build"
SERVICE_USER="${MUSICLITE_HQ_USER:-musiclite}"
SERVICE_GROUP="${MUSICLITE_HQ_GROUP:-musiclite}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$BUILD/kit" "$BUILD/sub" "$BUILD/pad" "$BUILD/pluck" "$BUILD/lead"

echo "== MusicLite Chillstep HQ 0.8 =="
echo "140 BPM half-time, sub, stereo pad, pluck e lead sintetizados localmente."

echo "== Dependências =="
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y rsync ffmpeg python3

echo "== Síntese local HQ8 =="
PY="$CACHE/chillstep_synth.py"
cat > "$PY" <<'PY'
import math, random, struct, wave
from pathlib import Path

SR=48000
ROOT=Path(__import__('sys').argv[1])
random.seed(808140)


def env_ar(t,dur,attack,release):
    a=min(1.0,t/max(1e-6,attack))
    r=min(1.0,max(0.0,dur-t)/max(1e-6,release))
    return max(0.0,min(a,r))


def write_mono(path, data):
    peak=max(1e-9,max(abs(x) for x in data))
    g=min(.94/peak,1.0)
    path.parent.mkdir(parents=True,exist_ok=True)
    with wave.open(str(path),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(SR)
        frames=bytearray()
        for x in data:
            frames += struct.pack('<h', int(max(-1,min(1,x*g))*32767))
        w.writeframes(frames)


def write_stereo(path, left, right):
    peak=max(1e-9,max(max(abs(x) for x in left),max(abs(x) for x in right)))
    g=min(.92/peak,1.0)
    path.parent.mkdir(parents=True,exist_ok=True)
    with wave.open(str(path),'wb') as w:
        w.setnchannels(2);w.setsampwidth(2);w.setframerate(SR)
        frames=bytearray()
        for l,r in zip(left,right):
            frames += struct.pack('<hh',int(max(-1,min(1,l*g))*32767),int(max(-1,min(1,r*g))*32767))
        w.writeframes(frames)


def kick(seed):
    rng=random.Random(seed);dur=.72;phase=0.0;out=[]
    for i in range(int(dur*SR)):
        t=i/SR
        f=46+112*math.exp(-t/.035)
        phase += 2*math.pi*f/SR
        body=math.sin(phase)*math.exp(-t*7.1)
        click=(rng.random()*2-1)*math.exp(-t*125)*.10
        sub=.18*math.sin(phase*.5)*math.exp(-t*5.2)
        out.append(math.tanh((body+sub+click)*1.18)*.86)
    return out


def snare(seed):
    rng=random.Random(seed);dur=.52;out=[];p1=p2=0.0
    for i in range(int(dur*SR)):
        t=i/SR
        p1+=2*math.pi*186/SR;p2+=2*math.pi*331/SR
        noise=(rng.random()*2-1)*math.exp(-t*11.5)
        tone=(math.sin(p1)*.34+math.sin(p2)*.15)*math.exp(-t*15)
        air=(rng.random()*2-1)*math.exp(-t*28)*.18
        out.append(math.tanh((noise*.62+tone+air)*1.15)*.70)
    return out


def hat(seed,dur,decay):
    rng=random.Random(seed);out=[];ph=[0.0]*6;freqs=[5140,6390,7430,8920,10550,12600]
    for i in range(int(dur*SR)):
        t=i/SR;metal=0.0
        for j,f in enumerate(freqs):
            ph[j]+=2*math.pi*f/SR;metal+=math.sin(ph[j])
        noise=(rng.random()*2-1)
        env=math.exp(-t*decay)
        out.append(math.tanh((noise*.42+metal*.055)*env*1.4)*.54)
    return out


def crash(seed):
    rng=random.Random(seed);dur=2.8;out=[]
    smooth=0.0
    for i in range(int(dur*SR)):
        t=i/SR;noise=rng.random()*2-1
        smooth=.93*smooth+.07*noise
        hp=noise-smooth
        env=(1-math.exp(-t*80))*math.exp(-t*1.8)
        shimmer=math.sin(2*math.pi*9321*t)*.05+math.sin(2*math.pi*11731*t)*.035
        out.append(math.tanh((hp*.68+shimmer)*env*1.1)*.42)
    return out


def sub_c2():
    dur=4.0;f=65.406;phase=0.0;out=[]
    for i in range(int(dur*SR)):
        t=i/SR;phase+=2*math.pi*f/SR
        env=env_ar(t,dur,.012,.30)*math.exp(-t*.10)
        tone=math.sin(phase)+.16*math.sin(2*phase)+.035*math.sin(3*phase)
        out.append(math.tanh(tone*1.18)*env*.78)
    return out


def pad_c4():
    dur=8.0;f=261.626;left=[];right=[]
    phases_l=[0.0]*5;phases_r=[0.0]*5
    cents_l=[-13,-6,0,7,14];cents_r=[-11,-4,2,9,16]
    for i in range(int(dur*SR)):
        t=i/SR;env=env_ar(t,dur,.42,.85)
        l=r=0.0
        for j,c in enumerate(cents_l):
            ff=f*(2**(c/1200));phases_l[j]+=2*math.pi*ff/SR
            l += math.sin(phases_l[j])*.13 + math.sin(2*phases_l[j])*.025
        for j,c in enumerate(cents_r):
            ff=f*(2**(c/1200));phases_r[j]+=2*math.pi*ff/SR
            r += math.sin(phases_r[j])*.13 + math.sin(2*phases_r[j])*.025
        slow=.88+.12*math.sin(2*math.pi*.17*t)
        left.append(math.tanh(l*.95)*env*slow)
        right.append(math.tanh(r*.95)*env*(1.0-.05*math.sin(2*math.pi*.13*t)))
    return left,right


def pluck_c5():
    dur=1.6;f=523.251;out=[];p=0.0
    for i in range(int(dur*SR)):
        t=i/SR;p+=2*math.pi*f/SR
        env=(1-math.exp(-t*120))*math.exp(-t*4.7)
        x=math.sin(p)*.72+math.sin(2*p)*.22+math.sin(3*p)*.09+math.sin(5*p)*.035
        out.append(math.tanh(x*1.05)*env*.66)
    return out


def lead_c5():
    dur=2.6;f=523.251;left=[];right=[];pl=pr=0.0
    fl=f*(2**(-5/1200));fr=f*(2**(5/1200))
    for i in range(int(dur*SR)):
        t=i/SR;pl+=2*math.pi*fl/SR;pr+=2*math.pi*fr/SR
        env=env_ar(t,dur,.025,.35)*math.exp(-t*.18)
        vibr=1+.0022*math.sin(2*math.pi*5.2*t)
        l=(math.sin(pl*vibr)*.62+math.sin(2*pl)*.18+math.sin(3*pl)*.07)
        r=(math.sin(pr*vibr)*.62+math.sin(2*pr)*.18+math.sin(3*pr)*.07)
        left.append(math.tanh(l*1.08)*env*.62)
        right.append(math.tanh(r*1.08)*env*.62)
    return left,right

for n in range(1,4):write_mono(ROOT/'kit'/f'kick{n}.wav',kick(100+n))
for n in range(1,4):write_mono(ROOT/'kit'/f'snare{n}.wav',snare(200+n))
for n in range(1,3):write_mono(ROOT/'kit'/f'hat_closed{n}.wav',hat(300+n,.16,38))
write_mono(ROOT/'kit'/'hat_open.wav',hat(350,.72,6.3))
write_mono(ROOT/'kit'/'crash.wav',crash(400))
write_mono(ROOT/'sub'/'sub_C2.wav',sub_c2())
l,r=pad_c4();write_stereo(ROOT/'pad'/'pad_C4.wav',l,r)
write_mono(ROOT/'pluck'/'pluck_C5.wav',pluck_c5())
l,r=lead_c5();write_stereo(ROOT/'lead'/'lead_C5.wav',l,r)
PY

python3 "$PY" "$BUILD"

echo "== SFZ HQ8 =="
cat > "$BUILD/kit/chillstep_kit.sfz" <<'SFZ'
<control> default_path=./
<group> key=36 loop_mode=one_shot seq_length=3
<region> sample=kick1.wav seq_position=1
<region> sample=kick2.wav seq_position=2
<region> sample=kick3.wav seq_position=3
<group> key=38 loop_mode=one_shot seq_length=3
<region> sample=snare1.wav seq_position=1
<region> sample=snare2.wav seq_position=2
<region> sample=snare3.wav seq_position=3
<group> key=42 loop_mode=one_shot seq_length=2 group=1 off_by=1
<region> sample=hat_closed1.wav seq_position=1
<region> sample=hat_closed2.wav seq_position=2
<group> key=46 loop_mode=one_shot group=1 off_by=1
<region> sample=hat_open.wav
<group> key=49 loop_mode=one_shot
<region> sample=crash.wav
SFZ

cat > "$BUILD/sub/chillstep_sub.sfz" <<'SFZ'
<control> default_path=./
<group> ampeg_attack=.004 ampeg_release=.24 volume=-1.0
<region> sample=sub_C2.wav lokey=29 hikey=48 pitch_keycenter=36 pitch_keytrack=100
SFZ

cat > "$BUILD/pad/chillstep_pad.sfz" <<'SFZ'
<control> default_path=./
<global> ampeg_attack=.16 ampeg_release=.65 amp_veltrack=36
<region> sample=pad_C4.wav lokey=48 hikey=84 pitch_keycenter=60 pitch_keytrack=100
SFZ

cat > "$BUILD/pluck/chillstep_pluck.sfz" <<'SFZ'
<control> default_path=./
<global> ampeg_attack=.002 ampeg_release=.18 amp_veltrack=64
<region> sample=pluck_C5.wav lokey=60 hikey=100 pitch_keycenter=72 pitch_keytrack=100
SFZ

cat > "$BUILD/lead/chillstep_lead.sfz" <<'SFZ'
<control> default_path=./
<global> ampeg_attack=.012 ampeg_release=.30 amp_veltrack=54
<region> sample=lead_C5.wav lokey=60 hikey=92 pitch_keycenter=72 pitch_keytrack=100
SFZ

echo "== Validação local =="
COUNT=$(find "$BUILD" -type f -name '*.wav' | wc -l)
if [ "$COUNT" -lt 14 ]; then
  echo "ERRO: esperados >=14 WAVs, encontrados $COUNT";exit 51
fi
while IFS= read -r wav; do
  ffprobe -v error -show_entries stream=codec_type -of default=nw=1:nk=1 "$wav" | grep -q audio || { echo "ERRO: WAV inválido: $wav";exit 52; }
done < <(find "$BUILD" -type f -name '*.wav' | sort)

for sfz in "$BUILD/kit/chillstep_kit.sfz" "$BUILD/sub/chillstep_sub.sfz" "$BUILD/pad/chillstep_pad.sfz" "$BUILD/pluck/chillstep_pluck.sfz" "$BUILD/lead/chillstep_lead.sfz"; do
  test -s "$sfz" || { echo "ERRO: SFZ ausente: $sfz";exit 53; }
done

echo "== Instalação dos assets =="
sudo install -d -o "$SERVICE_USER" -g "$SERVICE_GROUP" -m 0750 "$KIT" "$SUB" "$PAD" "$PLUCK" "$LEAD"
for d in kit sub pad pluck lead; do
  sudo rsync -a --delete "$BUILD/$d/" "$SAMPLES/$d/"
done
sudo chown -R "$SERVICE_USER":"$SERVICE_GROUP" "$SAMPLES"
sudo chmod -R u+rwX,go-rwx "$SAMPLES"

echo "== Deploy MusicLite HQ 0.8 =="
python3 -m py_compile \
  "$SCRIPT_DIR/musiclite_hq/genres.py" \
  "$SCRIPT_DIR/musiclite_hq/song_form.py" \
  "$SCRIPT_DIR/musiclite_hq/arranger.py" \
  "$SCRIPT_DIR/musiclite_hq/library.py" \
  "$SCRIPT_DIR/musiclite_hq/mix.py" \
  "$SCRIPT_DIR/musiclite_hq/api.py" \
  "$SCRIPT_DIR/musiclite_hq/musicians/chillstep.py"

sudo rsync -a --delete "$SCRIPT_DIR/musiclite_hq/" "$APP/musiclite_hq/"
sudo cp "$SCRIPT_DIR/requirements.txt" "$APP/requirements.txt"
sudo chmod -R a+rX "$APP"
sudo systemctl restart musiclite-studio-hq.service
sleep 3

echo "== Health =="
HEALTH=$(curl -fsS http://127.0.0.1:8094/health)
printf '%s\n' "$HEALTH" | python3 -m json.tool
python3 - "$HEALTH" <<'PY'
import json,sys
h=json.loads(sys.argv[1])
assert h.get('version') == '0.8.0', h
assert h.get('chillstep_engine_ready') is True, h
assert 'chillstep' in h.get('supported_genres',[]), h
print('CHILLSTEP HQ 0.8: READY')
PY

echo
echo "Assets Chillstep:"
sudo du -sh "$SAMPLES" 2>/dev/null || true
echo "CHILLSTEP HQ 0.8 pronto."
