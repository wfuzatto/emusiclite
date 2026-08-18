#!/usr/bin/env bash
set -Eeuo pipefail

BASE="/var/lib/musiclite/studio-hq"
APP="/opt/musiclite/studio-hq"
SAMPLES="$BASE/samples/hiphop"
PIANO="$SAMPLES/piano"
BRASS="$SAMPLES/brass"
STRINGS="$SAMPLES/strings"
FUNK="$BASE/samples/funk"
CACHE="${MUSICLITE_HIPHOP_CACHE:-$HOME/.cache/musiclite-hiphop-hq}"
SERVICE_USER="${MUSICLITE_HQ_USER:-musiclite}"
SERVICE_GROUP="${MUSICLITE_HQ_GROUP:-musiclite}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$CACHE"
echo "== MusicLite American Hip-Hop HQ 0.6 =="
echo "Base eletrônica: MusicLite kick/hats/808. Piano/brass/strings: VSCO 2 CE CC0."

echo "== Dependências =="
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y curl rsync ffmpeg sox python3

if [ ! -s "$FUNK/kit/funk_carioca_kit.sfz" ] || [ ! -s "$FUNK/808/funk_808_sub.sfz" ]; then
  echo "== Instalando base eletrônica MusicLite =="
  bash "$SCRIPT_DIR/install_funk_hq.sh"
fi

sudo mkdir -p "$PIANO" "$BRASS" "$STRINGS"
sudo chown -R "$SERVICE_USER":"$SERVICE_GROUP" "$SAMPLES"

fetch () {
  url="$1"; dst="$2"
  cache_name="$(printf '%s' "$url" | sha256sum | cut -c1-16)-$(basename "$dst")"
  tmp="$CACHE/$cache_name"
  if [ ! -s "$tmp" ]; then
    echo "Baixando $(basename "$dst")"
    curl -fL --retry 8 --retry-delay 2 --connect-timeout 20 --max-time 300 "$url" -o "$tmp"
  fi
  sudo install -o "$SERVICE_USER" -g "$SERVICE_GROUP" -m 0640 "$tmp" "$dst"
}

RAW="https://raw.githubusercontent.com/sgossner/VSCO-2-CE/master"
fetch "$RAW/LICENSE" "$SAMPLES/VSCO2CE-LICENSE.txt"
fetch "$RAW/README.md" "$SAMPLES/VSCO2CE-README.md"

echo "== Upright piano real: duas dinâmicas =="
for idx in 014 016 018 020 022 024 026; do
  for dyn in 1 3; do
    fetch "$RAW/Keys/Upright%20Piano/Player_dyn${dyn}_rr1_${idx}.wav" "$PIANO/Player_dyn${dyn}_rr1_${idx}.wav"
  done
done

echo "== Trumpet staccato real =="
fetch "$RAW/Brass/Trumpet/stac/Sum_SHTrumpet_stac_F2_v2_rr1.wav" "$BRASS/trumpet_F2.wav"
fetch "$RAW/Brass/Trumpet/stac/Sum_SHTrumpet_stac_A2_v2_rr1.wav" "$BRASS/trumpet_A2.wav"
fetch "$RAW/Brass/Trumpet/stac/Sum_SHTrumpet_stac_C3_v2_rr1.wav" "$BRASS/trumpet_C3.wav"
fetch "$RAW/Brass/Trumpet/stac/Sum_SHTrumpet_stac_D%233_v2_rr1.wav" "$BRASS/trumpet_Ds3.wav"
fetch "$RAW/Brass/Trumpet/stac/Sum_SHTrumpet_stac_F3_v2_rr1.wav" "$BRASS/trumpet_F3.wav"
fetch "$RAW/Brass/Trumpet/stac/Sum_SHTrumpet_stac_G3_v2_rr1.wav" "$BRASS/trumpet_G3.wav"
fetch "$RAW/Brass/Trumpet/stac/Sum_SHTrumpet_stac_A%233_v2_rr1.wav" "$BRASS/trumpet_As3.wav"
fetch "$RAW/Brass/Trumpet/stac/Sum_SHTrumpet_stac_D4_v2_rr1.wav" "$BRASS/trumpet_D4.wav"
fetch "$RAW/Brass/Trumpet/stac/Sum_SHTrumpet_stac_F4_v2_rr1.wav" "$BRASS/trumpet_F4.wav"
fetch "$RAW/Brass/Trumpet/stac/Sum_SHTrumpet_stac_A4_v2_rr1.wav" "$BRASS/trumpet_A4.wav"
fetch "$RAW/Brass/Trumpet/stac/Sum_SHTrumpet_stac_C5_v2_rr1.wav" "$BRASS/trumpet_C5.wav"

echo "== Violin ensemble sustain real: duas dinâmicas =="
fetch "$RAW/Strings/Violin%20Section/susVib/VlnEns_susVib_G2_v1.wav" "$STRINGS/strings_G2_v1.wav"
fetch "$RAW/Strings/Violin%20Section/susVib/VlnEns_susVib_G2_v2.wav" "$STRINGS/strings_G2_v2.wav"
fetch "$RAW/Strings/Violin%20Section/susVib/VlnEns_susVib_A2_v1.wav" "$STRINGS/strings_A2_v1.wav"
fetch "$RAW/Strings/Violin%20Section/susVib/VlnEns_susVib_A2_v2.wav" "$STRINGS/strings_A2_v2.wav"
fetch "$RAW/Strings/Violin%20Section/susVib/VlnEns_susVib_B2_v1.wav" "$STRINGS/strings_B2_v1.wav"
fetch "$RAW/Strings/Violin%20Section/susVib/VlnEns_susVib_B2_v2.wav" "$STRINGS/strings_B2_v2.wav"
fetch "$RAW/Strings/Violin%20Section/susVib/VlnEns_susVib_D3_v1.wav" "$STRINGS/strings_D3_v1.wav"
fetch "$RAW/Strings/Violin%20Section/susVib/VlnEns_susVib_D3_v2.wav" "$STRINGS/strings_D3_v2.wav"
fetch "$RAW/Strings/Violin%20Section/susVib/VlnEns_susVib_F%233_v1.wav" "$STRINGS/strings_Fs3_v1.wav"
fetch "$RAW/Strings/Violin%20Section/susVib/VlnEns_susVib_F%233_v2.wav" "$STRINGS/strings_Fs3_v2.wav"
fetch "$RAW/Strings/Violin%20Section/susVib/VlnEns_susVib_A3_v1.wav" "$STRINGS/strings_A3_v1.wav"
fetch "$RAW/Strings/Violin%20Section/susVib/VlnEns_susVib_A3_v2.wav" "$STRINGS/strings_A3_v2.wav"
fetch "$RAW/Strings/Violin%20Section/susVib/VlnEns_susVib_C4_v1.wav" "$STRINGS/strings_C4_v1.wav"
fetch "$RAW/Strings/Violin%20Section/susVib/VlnEns_susVib_C4_v2.wav" "$STRINGS/strings_C4_v2.wav"
fetch "$RAW/Strings/Violin%20Section/susVib/VlnEns_susVib_E4_v1.wav" "$STRINGS/strings_E4_v1.wav"
fetch "$RAW/Strings/Violin%20Section/susVib/VlnEns_susVib_E4_v2.wav" "$STRINGS/strings_E4_v2.wav"
fetch "$RAW/Strings/Violin%20Section/susVib/VlnEns_susVib_G4_v1.wav" "$STRINGS/strings_G4_v1.wav"
fetch "$RAW/Strings/Violin%20Section/susVib/VlnEns_susVib_G4_v2.wav" "$STRINGS/strings_G4_v2.wav"
fetch "$RAW/Strings/Violin%20Section/susVib/VlnEns_susVib_B4_v1.wav" "$STRINGS/strings_B4_v1.wav"
fetch "$RAW/Strings/Violin%20Section/susVib/VlnEns_susVib_B4_v2.wav" "$STRINGS/strings_B4_v2.wav"

echo "== SFZ: hip-hop upright =="
sudo -u "$SERVICE_USER" tee "$PIANO/hiphop_upright_piano.sfz" >/dev/null <<'SFZ'
<control> default_path=./
<global> amp_veltrack=78 ampeg_release=0.38
<group> lovel=1 hivel=72
<region> sample=Player_dyn1_rr1_014.wav lokey=47 hikey=51 pitch_keycenter=49
<region> sample=Player_dyn1_rr1_016.wav lokey=52 hikey=55 pitch_keycenter=53
<region> sample=Player_dyn1_rr1_018.wav lokey=56 hikey=59 pitch_keycenter=57
<region> sample=Player_dyn1_rr1_020.wav lokey=60 hikey=63 pitch_keycenter=61
<region> sample=Player_dyn1_rr1_022.wav lokey=64 hikey=67 pitch_keycenter=65
<region> sample=Player_dyn1_rr1_024.wav lokey=68 hikey=71 pitch_keycenter=69
<region> sample=Player_dyn1_rr1_026.wav lokey=72 hikey=76 pitch_keycenter=73
<group> lovel=73 hivel=127
<region> sample=Player_dyn3_rr1_014.wav lokey=47 hikey=51 pitch_keycenter=49
<region> sample=Player_dyn3_rr1_016.wav lokey=52 hikey=55 pitch_keycenter=53
<region> sample=Player_dyn3_rr1_018.wav lokey=56 hikey=59 pitch_keycenter=57
<region> sample=Player_dyn3_rr1_020.wav lokey=60 hikey=63 pitch_keycenter=61
<region> sample=Player_dyn3_rr1_022.wav lokey=64 hikey=67 pitch_keycenter=65
<region> sample=Player_dyn3_rr1_024.wav lokey=68 hikey=71 pitch_keycenter=69
<region> sample=Player_dyn3_rr1_026.wav lokey=72 hikey=76 pitch_keycenter=73
SFZ

echo "== SFZ: cinematic brass =="
sudo -u "$SERVICE_USER" tee "$BRASS/hiphop_cinematic_brass.sfz" >/dev/null <<'SFZ'
<control> default_path=./
<global> loop_mode=one_shot amp_veltrack=72 ampeg_release=0.12
<region> sample=trumpet_F2.wav lokey=36 hikey=43 pitch_keycenter=41
<region> sample=trumpet_A2.wav lokey=44 hikey=46 pitch_keycenter=45
<region> sample=trumpet_C3.wav lokey=47 hikey=49 pitch_keycenter=48
<region> sample=trumpet_Ds3.wav lokey=50 hikey=52 pitch_keycenter=51
<region> sample=trumpet_F3.wav lokey=53 hikey=54 pitch_keycenter=53
<region> sample=trumpet_G3.wav lokey=55 hikey=56 pitch_keycenter=55
<region> sample=trumpet_As3.wav lokey=57 hikey=60 pitch_keycenter=58
<region> sample=trumpet_D4.wav lokey=61 hikey=63 pitch_keycenter=62
<region> sample=trumpet_F4.wav lokey=64 hikey=67 pitch_keycenter=65
<region> sample=trumpet_A4.wav lokey=68 hikey=70 pitch_keycenter=69
<region> sample=trumpet_C5.wav lokey=71 hikey=76 pitch_keycenter=72
SFZ

echo "== SFZ: cinematic strings =="
sudo -u "$SERVICE_USER" tee "$STRINGS/hiphop_cinematic_strings.sfz" >/dev/null <<'SFZ'
<control> default_path=./
<global> amp_veltrack=62 ampeg_attack=0.045 ampeg_release=0.48
<group> lovel=1 hivel=74
<region> sample=strings_G2_v1.wav lokey=41 hikey=44 pitch_keycenter=43
<region> sample=strings_A2_v1.wav lokey=45 hikey=46 pitch_keycenter=45
<region> sample=strings_B2_v1.wav lokey=47 hikey=48 pitch_keycenter=47
<region> sample=strings_D3_v1.wav lokey=49 hikey=52 pitch_keycenter=50
<region> sample=strings_Fs3_v1.wav lokey=53 hikey=55 pitch_keycenter=54
<region> sample=strings_A3_v1.wav lokey=56 hikey=58 pitch_keycenter=57
<region> sample=strings_C4_v1.wav lokey=59 hikey=62 pitch_keycenter=60
<region> sample=strings_E4_v1.wav lokey=63 hikey=65 pitch_keycenter=64
<region> sample=strings_G4_v1.wav lokey=66 hikey=68 pitch_keycenter=67
<region> sample=strings_B4_v1.wav lokey=69 hikey=76 pitch_keycenter=71
<group> lovel=75 hivel=127
<region> sample=strings_G2_v2.wav lokey=41 hikey=44 pitch_keycenter=43
<region> sample=strings_A2_v2.wav lokey=45 hikey=46 pitch_keycenter=45
<region> sample=strings_B2_v2.wav lokey=47 hikey=48 pitch_keycenter=47
<region> sample=strings_D3_v2.wav lokey=49 hikey=52 pitch_keycenter=50
<region> sample=strings_Fs3_v2.wav lokey=53 hikey=55 pitch_keycenter=54
<region> sample=strings_A3_v2.wav lokey=56 hikey=58 pitch_keycenter=57
<region> sample=strings_C4_v2.wav lokey=59 hikey=62 pitch_keycenter=60
<region> sample=strings_E4_v2.wav lokey=63 hikey=65 pitch_keycenter=64
<region> sample=strings_G4_v2.wav lokey=66 hikey=68 pitch_keycenter=67
<region> sample=strings_B4_v2.wav lokey=69 hikey=76 pitch_keycenter=71
SFZ

sudo chown -R "$SERVICE_USER":"$SERVICE_GROUP" "$SAMPLES"
sudo chmod -R u+rwX,go-rwx "$SAMPLES"

echo "== Validação de áudio e SFZ =="
for sfz in "$PIANO/hiphop_upright_piano.sfz" "$BRASS/hiphop_cinematic_brass.sfz" "$STRINGS/hiphop_cinematic_strings.sfz"; do
  test -s "$sfz" || { echo "ERRO: SFZ ausente: $sfz"; exit 61; }
done
COUNT=$(sudo -u "$SERVICE_USER" find "$SAMPLES" -type f -name '*.wav' | wc -l)
if [ "$COUNT" -lt 45 ]; then
  echo "ERRO: assets incompletos; esperados >=45 WAVs, encontrados $COUNT";exit 62
fi
while IFS= read -r wav; do
  ffprobe -v error -show_entries stream=codec_type -of default=nw=1:nk=1 "$wav" | grep -q audio || { echo "ERRO: WAV inválido: $wav";exit 63; }
done < <(sudo -u "$SERVICE_USER" find "$SAMPLES" -type f -name '*.wav' | sort)

echo "== Deploy MusicLite Studio HQ 0.6 =="
sudo rsync -a --delete "$SCRIPT_DIR/musiclite_hq/" "$APP/musiclite_hq/"
sudo cp "$SCRIPT_DIR/requirements.txt" "$APP/requirements.txt"
sudo chmod -R a+rX "$APP"
sudo chown -R "$SERVICE_USER":"$SERVICE_GROUP" "$BASE"
sudo chmod -R u+rwX,go-rwx "$BASE"
sudo systemctl restart musiclite-studio-hq.service
sleep 3

echo "== Health =="
HEALTH=$(curl -fsS http://127.0.0.1:8094/health)
printf '%s\n' "$HEALTH" | python3 -m json.tool
python3 - "$HEALTH" <<'PY'
import json,sys
h=json.loads(sys.argv[1])
assert h.get('version')=='0.6.0', h
assert h.get('hiphop_engine_ready') is True, h
assert 'hiphop' in h.get('supported_genres',[]), h
print('HIP-HOP HQ 0.6: READY')
PY

echo
echo "Assets instalados:"
sudo du -sh "$PIANO" "$BRASS" "$STRINGS" 2>/dev/null || true
echo
echo "American Hip-Hop HQ 0.6 pronto."
