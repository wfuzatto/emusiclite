#!/usr/bin/env bash
set -Eeuo pipefail

BASE="/var/lib/musiclite/studio-hq"
APP="/opt/musiclite/studio-hq"
SAMPLES="$BASE/samples/funk"
KIT="$SAMPLES/kit"
SUB="$SAMPLES/808"
CACHE="${MUSICLITE_FUNK_CACHE:-$HOME/.cache/musiclite-funk-hq}"
SERVICE_USER="${MUSICLITE_HQ_USER:-musiclite}"
SERVICE_GROUP="${MUSICLITE_HQ_GROUP:-musiclite}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$CACHE"

echo "== MusicLite Funk Carioca HQ 0.5 =="
echo "Assets orgânicos: VCSL CC0. Kick/tamborzao/hats/808: síntese local 48 kHz."

echo "== Dependências =="
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y curl rsync ffmpeg sox python3

sudo mkdir -p "$KIT" "$SUB"
sudo chown -R "$SERVICE_USER":"$SERVICE_GROUP" "$SAMPLES"

fetch () {
  url="$1"; dst="$2"
  tmp="$CACHE/$(basename "$dst")"
  if [ ! -s "$tmp" ]; then
    echo "Baixando $(basename "$dst")"
    curl -fL --retry 8 --retry-delay 2 --connect-timeout 20 --max-time 180 \
      "$url" -o "$tmp"
  fi
  sudo install -o "$SERVICE_USER" -g "$SERVICE_GROUP" -m 0640 "$tmp" "$dst"
}

RAW="https://raw.githubusercontent.com/sgossner/VCSL/master/Idiophones/Struck%20Idiophones"

echo "== VCSL CC0: claps round-robin =="
for n in 1 2 3 4 5 6; do
  fetch "$RAW/Claps/Clap_rr${n}.wav" "$KIT/Clap_rr${n}.wav"
done

echo "== VCSL CC0: agogô =="
for n in 1 2 3; do
  fetch "$RAW/Agogo%20Bells/Agogo_High_v${n}_rr1_Mid.wav" "$KIT/Agogo_High_v${n}_rr1_Mid.wav"
done
for n in 1 2; do
  fetch "$RAW/Agogo%20Bells/Agogo_Low_v${n}_rr1_Mid.wav" "$KIT/Agogo_Low_v${n}_rr1_Mid.wav"
done

echo "== VCSL CC0: cabasa =="
for n in 1 2; do
  fetch "$RAW/Cabasa/Cabasa1_Hit_rr${n}_Mid.wav" "$KIT/Cabasa1_Hit_rr${n}_Mid.wav"
done

fetch "https://raw.githubusercontent.com/sgossner/VCSL/master/LICENSE" "$SAMPLES/VCSL-LICENSE.txt"
fetch "https://raw.githubusercontent.com/sgossner/VCSL/master/README.md" "$SAMPLES/VCSL-README.md"

echo "== Síntese local: tamborzão, kick, hats e sub 808 =="
TMPPY="$(mktemp /tmp/musiclite-funk-synth.XXXXXX.py)"
cat > "$TMPPY" <<'PY'
import math, random, struct, sys, wave
from pathlib import Path

SR=48000
random.seed(5052026)
kit=Path(sys.argv[1]); sub=Path(sys.argv[2])
kit.mkdir(parents=True,exist_ok=True); sub.mkdir(parents=True,exist_ok=True)

def save(path,data):
    peak=max(1e-9,max(abs(x) for x in data))
    gain=min(.96/peak,1.0)
    with wave.open(str(path),'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(b''.join(struct.pack('<h',int(max(-1,min(1,x*gain))*32767)) for x in data))

def kick():
    out=[]; phase=0.0
    for i in range(int(.72*SR)):
        t=i/SR
        f=48.0+118.0*math.exp(-t/0.032)
        phase += 2*math.pi*f/SR
        env=math.exp(-t*7.2)
        click=(random.random()*2-1)*math.exp(-t*150)*.19
        body=math.sin(phase)*env + .16*math.sin(phase*2.02)*math.exp(-t*13)
        out.append(math.tanh((body+click)*1.35)*.88)
    return out

def tambor(freq,dur=.40):
    out=[]; phase=0.0
    for i in range(int(dur*SR)):
        t=i/SR; phase += 2*math.pi*(freq+26*math.exp(-t/.025))/SR
        env=math.exp(-t*10.0)
        noise=(random.random()*2-1)*math.exp(-t*42)*.10
        x=(math.sin(phase)+.24*math.sin(phase*1.49)+.10*math.sin(phase*2.04))*env+noise
        out.append(math.tanh(x*1.2)*.78)
    return out

def hat(dur,decay):
    out=[]; prev=0.0
    phases=[0.0]*5; freqs=[4370,5920,7130,8870,10340]
    for i in range(int(dur*SR)):
        t=i/SR; noise=random.random()*2-1
        hp=noise-prev*.96; prev=noise
        metal=0.0
        for j,f in enumerate(freqs):
            phases[j]+=2*math.pi*f/SR
            metal+=math.sin(phases[j])
        env=math.exp(-t*decay)
        out.append(math.tanh((hp*.72+metal*.055)*env*1.6)*.62)
    return out

def eightoh():
    out=[]; phase=0.0; f0=32.7032
    for i in range(int(3.8*SR)):
        t=i/SR
        f=f0+48.0*math.exp(-t/.038)
        phase+=2*math.pi*f/SR
        env=(1-math.exp(-t*90))*math.exp(-t*.78)
        tone=math.sin(phase)+.20*math.sin(2*phase)+.055*math.sin(3*phase)
        x=math.tanh(tone*1.65)*env
        out.append(x*.86)
    return out

save(kit/'electronic_kick.wav',kick())
save(kit/'tambor_low.wav',tambor(88,.46))
save(kit/'tambor_high.wav',tambor(137,.34))
save(kit/'hat_closed.wav',hat(.14,34))
save(kit/'hat_open.wav',hat(.62,8.5))
save(sub/'808_C1.wav',eightoh())
PY
chmod 0644 "$TMPPY"
sudo -u "$SERVICE_USER" python3 "$TMPPY" "$KIT" "$SUB"

echo "== SFZ dedicado =="
TMPKIT="$(mktemp /tmp/musiclite-funk-kit.XXXXXX.sfz)"
TMPSUB="$(mktemp /tmp/musiclite-funk-sub.XXXXXX.sfz)"
trap 'rm -f "$TMPPY" "$TMPKIT" "$TMPSUB"' EXIT

cat > "$TMPKIT" <<'SFZ'
<control> default_path=./

<group> loop_mode=one_shot
<region> key=36 sample=electronic_kick.wav volume=0
<region> key=45 sample=tambor_low.wav volume=-1
<region> key=47 sample=tambor_high.wav volume=-1

<group> loop_mode=one_shot key=38 seq_length=6
<region> sample=Clap_rr1.wav seq_position=1
<region> sample=Clap_rr2.wav seq_position=2
<region> sample=Clap_rr3.wav seq_position=3
<region> sample=Clap_rr4.wav seq_position=4
<region> sample=Clap_rr5.wav seq_position=5
<region> sample=Clap_rr6.wav seq_position=6

<group> loop_mode=one_shot group=1 off_by=1
<region> key=42 sample=hat_closed.wav
<region> key=46 sample=hat_open.wav

<group> loop_mode=one_shot key=68
<region> sample=Agogo_High_v1_rr1_Mid.wav lovel=1 hivel=45
<region> sample=Agogo_High_v2_rr1_Mid.wav lovel=46 hivel=90
<region> sample=Agogo_High_v3_rr1_Mid.wav lovel=91 hivel=127

<group> loop_mode=one_shot key=67
<region> sample=Agogo_Low_v1_rr1_Mid.wav lovel=1 hivel=64
<region> sample=Agogo_Low_v2_rr1_Mid.wav lovel=65 hivel=127

<group> loop_mode=one_shot key=69 seq_length=2
<region> sample=Cabasa1_Hit_rr1_Mid.wav seq_position=1
<region> sample=Cabasa1_Hit_rr2_Mid.wav seq_position=2
SFZ

cat > "$TMPSUB" <<'SFZ'
<control> default_path=./
<group> ampeg_attack=0.002 ampeg_release=0.20 volume=-1.0
<region> sample=808_C1.wav lokey=24 hikey=52 pitch_keycenter=24 pitch_keytrack=100
SFZ

if [ ! -s "$TMPKIT" ] || [ ! -s "$TMPSUB" ]; then
  echo "ERRO: geração temporária dos SFZ falhou"; exit 40
fi
sudo install -o "$SERVICE_USER" -g "$SERVICE_GROUP" -m 0640 "$TMPKIT" "$KIT/funk_carioca_kit.sfz"
sudo install -o "$SERVICE_USER" -g "$SERVICE_GROUP" -m 0640 "$TMPSUB" "$SUB/funk_808_sub.sfz"

sudo chown -R "$SERVICE_USER":"$SERVICE_GROUP" "$SAMPLES"
sudo chmod -R u+rwX,go-rwx "$SAMPLES"

echo "== Validação dos assets =="
for f in \
  "$KIT/funk_carioca_kit.sfz" \
  "$SUB/funk_808_sub.sfz" \
  "$KIT/electronic_kick.wav" \
  "$KIT/tambor_low.wav" \
  "$KIT/tambor_high.wav" \
  "$SUB/808_C1.wav"; do
  if ! sudo -u "$SERVICE_USER" test -s "$f"; then
    echo "ERRO: asset ausente ou ilegível para $SERVICE_USER: $f"
    sudo -u "$SERVICE_USER" ls -l "$f" 2>/dev/null || true
    exit 41
  fi
done

COUNT=$(sudo -u "$SERVICE_USER" find "$KIT" -maxdepth 1 -type f -name '*.wav' | wc -l)
if [ "$COUNT" -lt 18 ]; then
  echo "ERRO: kit incompleto; esperados >=18 WAVs, encontrados $COUNT"; exit 42
fi

echo "== Deploy MusicLite HQ 0.5 =="
sudo rsync -a --delete "$SCRIPT_DIR/musiclite_hq/" "$APP/musiclite_hq/"
sudo cp "$SCRIPT_DIR/requirements.txt" "$APP/requirements.txt"
sudo chmod -R a+rX "$APP"
sudo chown -R "$SERVICE_USER":"$SERVICE_GROUP" "$BASE"
sudo chmod -R u+rwX,go-rwx "$BASE"
sudo systemctl restart musiclite-studio-hq.service
sleep 3

echo "== Health =="
curl -fsS http://127.0.0.1:8094/health | python3 -m json.tool

echo
sudo du -sh "$SAMPLES" 2>/dev/null || true
echo "FUNK CARIOCA HQ 0.5 pronto."
