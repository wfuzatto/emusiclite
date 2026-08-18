#!/usr/bin/env bash
set -Eeuo pipefail

BASE="/var/lib/musiclite/studio-hq"
APP="/opt/musiclite/studio-hq"
SAMPLES="$BASE/samples"
DRUMKITS="$BASE/drumkits"
IRS="$BASE/irs"
SERVICE_USER="${MUSICLITE_HQ_USER:-musiclite}"
SERVICE_GROUP="${MUSICLITE_HQ_GROUP:-musiclite}"
MIN_FREE_GB="${MUSICLITE_HQ3_MIN_FREE_GB:-18}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAGE="$(mktemp -d /tmp/musiclite-hq3.XXXXXX)"
trap 'rm -rf "$STAGE"' EXIT

echo "== MusicLite Studio HQ 0.3 / REALISM UPGRADE =="
FREE_GB=$(df -Pk /var/lib/musiclite 2>/dev/null | awk 'NR==2 {printf "%.0f",$4/1024/1024}')
if [ -z "${FREE_GB:-}" ]; then FREE_GB=$(df -Pk / | awk 'NR==2 {printf "%.0f",$4/1024/1024}'); fi
echo "Espaço livre: ${FREE_GB} GB"
if [ "$FREE_GB" -lt "$MIN_FREE_GB" ]; then
  echo "ERRO: HQ3 completo exige pelo menos ${MIN_FREE_GB} GB livres durante a atualização."
  echo "Nada foi apagado. Libere espaço e execute novamente."
  exit 20
fi

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  git curl wget unzip p7zip-full unar file rsync ffmpeg sox \
  python3 python3-venv python3-dev build-essential pkg-config \
  autoconf automake libtool libsndfile1-dev libsmf-dev libasound2-dev \
  libjack-jackd2-dev libzita-resampler-dev libexpat1-dev libx11-dev

echo "== DrumGizmo CLI =="
if ! command -v drumgizmo >/dev/null 2>&1; then
  if sudo apt-get install -y drumgizmo; then true; else
    git clone --recursive http://git.drumgizmo.org/drumgizmo.git "$STAGE/drumgizmo"
    (cd "$STAGE/drumgizmo" && ./autogen.sh && ./configure --prefix=/usr/local --enable-cli --disable-editor && make -j"$(nproc)" && sudo make install)
  fi
fi
drumgizmo --version || drumgizmo -v

TOOLS_VENV="$STAGE/tools-venv"
python3 -m venv "$TOOLS_VENV"
"$TOOLS_VENV/bin/pip" -q install --upgrade pip gdown

extract_auto () {
  arc="$1"; dst="$2"; mkdir -p "$dst"; mime=$(file -b --mime-type "$arc" || true)
  case "$mime" in
    application/zip) unzip -q -o "$arc" -d "$dst" ;;
    application/x-rar|application/vnd.rar) unar -f -q -o "$dst" "$arc" ;;
    application/x-7z-compressed) 7z x -y "$arc" -o"$dst" >/dev/null ;;
    application/x-xz|application/x-tar|application/gzip) tar -xf "$arc" -C "$dst" ;;
    *) if ! 7z x -y "$arc" -o"$dst" >/dev/null 2>&1; then unar -f -q -o "$dst" "$arc"; fi ;;
  esac
}

target_has () { target="$1"; pattern="$2"; sudo -u "$SERVICE_USER" find "$target" -type f -name "$pattern" -print -quit 2>/dev/null | grep -q .; }
install_tree () {
  source_dir="$1"; target_dir="$2"; sudo mkdir -p "$target_dir"; sudo rsync -a "$source_dir"/ "$target_dir"/; sudo chown -R "$SERVICE_USER":"$SERVICE_GROUP" "$target_dir"; sudo chmod -R u+rwX,go-rwx "$target_dir"
}
gdrive_pack () {
  id="$1"; target="$2"; marker="$3"; label="$4"
  if target_has "$target" "$marker"; then echo "Já instalado: $target"; return; fi
  pack="$STAGE/${label}.pack"; extracted="$STAGE/${label}"
  "$TOOLS_VENV/bin/gdown" --fuzzy "https://drive.google.com/uc?id=$id" -O "$pack"
  extract_auto "$pack" "$extracted"; install_tree "$extracted" "$target"
}

echo "== Guitar/Bass HQ libraries =="
gdrive_pack "1FurY3_x_tog_56irX1VDNyRCUt5JD7bO" "$SAMPLES/guitar/MetalGTX" "*.sfz" "metal-gtx"
gdrive_pack "1uoV7icZV1_IjiOGKM7Wm5_K5UkF41Fm3" "$SAMPLES/guitar/StandardGuitar" "*.sfz" "standard-guitar"
gdrive_pack "1Xp4p4l3qIkQM2kAZf6al0Lpo3NQpcRwk" "$SAMPLES/bass/StandardBass" "*.sfz" "standard-bass"

echo "== DrumGizmo real multi-mic kits =="
if ! target_has "$DRUMKITS/CrocellKit" "*.xml"; then
  zip="$STAGE/CrocellKit1_1.zip"; curl -fL --retry 4 https://drumgizmo.org/kits/CrocellKit/CrocellKit1_1.zip -o "$zip"
  echo "fa2be0f847bcd8ddef3830c1523690d3  $zip" | md5sum -c -
  mkdir -p "$STAGE/CrocellKit"; unzip -q -o "$zip" -d "$STAGE/CrocellKit"; install_tree "$STAGE/CrocellKit" "$DRUMKITS/CrocellKit"
fi
if ! target_has "$DRUMKITS/DRSKit" "*.xml"; then
  zip="$STAGE/DRSKit2_1.zip"; curl -fL --retry 4 https://drumgizmo.org/kits/DRSKit/DRSKit2_1.zip -o "$zip"
  echo "8c4d4b61ad9d354b3b845edd5da9c133  $zip" | md5sum -c -
  mkdir -p "$STAGE/DRSKit"; unzip -q -o "$zip" -d "$STAGE/DRSKit"; install_tree "$STAGE/DRSKit" "$DRUMKITS/DRSKit"
fi

echo "== Cabinet + room impulse responses =="
if ! sudo -u "$SERVICE_USER" find "$IRS/Voxengo" -type f -iname '*Direct*Cabinet*.wav' -print -quit 2>/dev/null | grep -q .; then
  zip="$STAGE/IMreverbs.zip"; curl -fL --retry 4 https://www.voxengo.com/files/impulses/IMreverbs.zip -o "$zip"
  mkdir -p "$STAGE/Voxengo"; unzip -q -o "$zip" -d "$STAGE/Voxengo"; install_tree "$STAGE/Voxengo" "$IRS/Voxengo"
fi

echo "== Deploy HQ3 code =="
sudo rsync -a --delete "$SCRIPT_DIR/musiclite_hq/" "$APP/musiclite_hq/"
sudo cp "$SCRIPT_DIR/requirements.txt" "$APP/requirements.txt"
sudo chmod -R a+rX "$APP"
sudo chown -R "$SERVICE_USER":"$SERVICE_GROUP" "$BASE"
sudo chmod -R u+rwX,go-rwx "$BASE"
sudo systemctl restart musiclite-studio-hq.service
sleep 3

echo "== Health =="
curl -fsS http://127.0.0.1:8094/health | python3 -m json.tool

echo "== Library inventory =="
sudo -u "$SERVICE_USER" find "$SAMPLES/guitar/MetalGTX" "$SAMPLES/guitar/StandardGuitar" "$SAMPLES/bass/StandardBass" -name '*.sfz' -type f 2>/dev/null | head -30
sudo du -sh "$SAMPLES/guitar/MetalGTX" "$SAMPLES/guitar/StandardGuitar" "$SAMPLES/bass/StandardBass" "$DRUMKITS/CrocellKit" "$DRUMKITS/DRSKit" "$IRS/Voxengo" 2>/dev/null || true

if [ "${MUSICLITE_HQ3_SKIP_SMOKE:-0}" != "1" ]; then
  echo "== Smoke test HQ3: rock 20s =="
  SMOKE_JSON="$STAGE/hq3-smoke.json"
  curl -fsS -X POST http://127.0.0.1:8094/render/test -H 'Content-Type: application/json' -d '{"seconds":20,"bpm":132,"genre":"rock","prompt":"rock de estúdio, bateria acústica real, guitarras humanas"}' > "$SMOKE_JSON"
  python3 - "$SMOKE_JSON" <<'PY'
import json,sys
d=json.load(open(sys.argv[1],encoding="utf-8"))
print(json.dumps({"version":d.get("version"),"drums_engine":d.get("drums_engine"),"library_fallbacks":d.get("library_fallbacks"),"drumgizmo_error":d.get("drumgizmo_error"),"final":d.get("final")},indent=2,ensure_ascii=False))
if d.get("version")!="0.3.0":raise SystemExit("HQ3 smoke falhou: versão inesperada")
if not d.get("final"):raise SystemExit("HQ3 smoke falhou: WAV final ausente")
PY
fi

echo
echo "HQ3 instalado."
echo "Teste rock máximo:"
echo "curl -sS -X POST http://127.0.0.1:8094/render/test -H 'Content-Type: application/json' -d '{\"seconds\":90,\"bpm\":132,\"genre\":\"rock\",\"prompt\":\"rock brasileiro de estúdio, bateria acústica real, guitarras grandes e humanas\"}' | python3 -m json.tool"
