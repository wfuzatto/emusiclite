#!/usr/bin/env bash
set -Eeuo pipefail

BASE="/var/lib/musiclite/studio-hq"
APP="/opt/musiclite/studio-hq"
SAMPLES="$BASE/samples"
DRUMKITS="$BASE/drumkits"
IRS="$BASE/irs"
CACHE="${MUSICLITE_HQ3_CACHE:-$HOME/.cache/musiclite-hq3}"
SERVICE_USER="${MUSICLITE_HQ_USER:-musiclite}"
SERVICE_GROUP="${MUSICLITE_HQ_GROUP:-musiclite}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAGE="$(mktemp -d /tmp/musiclite-hq3-rock.XXXXXX)"
trap 'rm -rf "$STAGE"' EXIT

mkdir -p "$CACHE"

echo "== MusicLite HQ rock fast-path =="
echo "Ignorando DRSKit por enquanto; ele é usado para sertanejo/pop."

echo "== Dependências =="
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y aria2 unzip rsync curl ffmpeg sox

target_has () {
  target="$1"; pattern="$2"
  sudo -u "$SERVICE_USER" find "$target" -type f -name "$pattern" -print -quit 2>/dev/null | grep -q .
}

install_tree () {
  source_dir="$1"; target_dir="$2"
  sudo mkdir -p "$target_dir"
  sudo rsync -a "$source_dir"/ "$target_dir"/
  sudo chown -R "$SERVICE_USER":"$SERVICE_GROUP" "$target_dir"
  sudo chmod -R u+rwX,go-rwx "$target_dir"
}

download_verified () {
  url="$1"; dst="$2"; md5="$3"
  mkdir -p "$(dirname "$dst")"
  if [ -s "$dst" ] && echo "$md5  $dst" | md5sum -c - >/dev/null 2>&1; then
    echo "Cache válido: $dst"
    return
  fi
  echo "Download retomável/paralelo: $url"
  aria2c \
    --continue=true \
    --max-connection-per-server=8 \
    --split=8 \
    --min-split-size=5M \
    --retry-wait=5 \
    --max-tries=20 \
    --timeout=30 \
    --connect-timeout=20 \
    --file-allocation=none \
    --dir="$(dirname "$dst")" \
    --out="$(basename "$dst")" \
    "$url"
  if ! echo "$md5  $dst" | md5sum -c -; then
    echo "ERRO: MD5 inválido em $dst"
    echo "Remova o arquivo de cache e execute novamente: rm -f '$dst'"
    exit 31
  fi
}

for p in \
  "$SAMPLES/guitar/MetalGTX" \
  "$SAMPLES/guitar/StandardGuitar" \
  "$SAMPLES/bass/StandardBass"; do
  if ! target_has "$p" '*.sfz'; then
    echo "ERRO: biblioteca HQ ausente: $p"
    echo "Execute upgrade_hq3.sh novamente para instalar guitarra/baixo HQ."
    exit 32
  fi
done

echo "== CrocellKit rock =="
if target_has "$DRUMKITS/CrocellKit" '*.xml'; then
  echo "CrocellKit já instalado."
else
  ZIP="$CACHE/CrocellKit1_1.zip"
  download_verified \
    "https://drumgizmo.org/kits/CrocellKit/CrocellKit1_1.zip" \
    "$ZIP" \
    "fa2be0f847bcd8ddef3830c1523690d3"
  mkdir -p "$STAGE/CrocellKit"
  unzip -q -o "$ZIP" -d "$STAGE/CrocellKit"
  install_tree "$STAGE/CrocellKit" "$DRUMKITS/CrocellKit"
fi

echo "== Cabinet/room IR =="
if sudo -u "$SERVICE_USER" find "$IRS/Voxengo" -type f -iname '*Direct*Cabinet*.wav' -print -quit 2>/dev/null | grep -q .; then
  echo "IRs Voxengo já instalados."
else
  ZIP="$CACHE/IMreverbs.zip"
  aria2c --continue=true --max-connection-per-server=4 --split=4 --file-allocation=none \
    --dir="$CACHE" --out="IMreverbs.zip" \
    "https://www.voxengo.com/files/impulses/IMreverbs.zip"
  mkdir -p "$STAGE/Voxengo"
  unzip -q -o "$ZIP" -d "$STAGE/Voxengo"
  install_tree "$STAGE/Voxengo" "$IRS/Voxengo"
fi

echo "== Deploy código atual =="
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
sudo du -sh \
  "$SAMPLES/guitar/MetalGTX" \
  "$SAMPLES/guitar/StandardGuitar" \
  "$SAMPLES/bass/StandardBass" \
  "$DRUMKITS/CrocellKit" \
  "$IRS/Voxengo" 2>/dev/null || true

echo
echo "ROCK HQ pronto. DRSKit foi deixado para depois."
