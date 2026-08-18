#!/usr/bin/env bash
set -Eeuo pipefail

BASE="/var/lib/musiclite/studio-hq"
APP="/opt/musiclite/studio-hq"
SAMPLES="$BASE/samples"
MIN_FREE_GB="${MIN_FREE_GB:-12}"

echo "== MusicLite Studio HQ installer =="
echo "CPU-only offline renderer; existing musiclite-studio.service is not replaced."

FREE_GB=$(df -Pk /var/lib/musiclite 2>/dev/null | awk 'NR==2 {printf "%.0f", $4/1024/1024}' || echo 0)
echo "Espaço livre estimado em /var/lib/musiclite: ${FREE_GB} GB"
if [ "$FREE_GB" -lt "$MIN_FREE_GB" ]; then
  echo "ERRO: menos de ${MIN_FREE_GB} GB livres. Não vou baixar vários GB de samples."
  echo "Libere espaço ou monte outro disco em /var/lib/musiclite/studio-hq e rode novamente."
  exit 20
fi

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  git git-lfs build-essential cmake ninja-build pkg-config \
  libsndfile1-dev libsamplerate0-dev libfftw3-dev \
  ffmpeg sox rsync p7zip-full python3-venv python3-dev curl ca-certificates

git lfs install

sudo mkdir -p "$APP" "$SAMPLES"/{drums,bass,guitar,piano,accordion} "$BASE"/{output,work}
sudo chown -R "$USER":"$USER" "$APP" "$BASE"

echo "== Instalando sfizz_render =="
if ! command -v sfizz_render >/dev/null 2>&1; then
  TMP=$(mktemp -d)
  git clone --recursive https://github.com/sfztools/sfizz.git "$TMP/sfizz"
  cmake -S "$TMP/sfizz" -B "$TMP/sfizz/build" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DSFIZZ_JACK=OFF \
    -DSFIZZ_SHARED=ON \
    -DSFIZZ_RENDER=ON \
    -DPLUGIN_LV2=OFF \
    -DPLUGIN_LV2_UI=OFF \
    -DPLUGIN_VST3=OFF \
    -DSFIZZ_TESTS=OFF \
    -DSFIZZ_BENCHMARKS=OFF \
    -DSFIZZ_DEMOS=OFF \
    -DSFIZZ_USE_SNDFILE=ON
  cmake --build "$TMP/sfizz/build" --target sfizz_render -j"$(nproc)"
  BIN=$(find "$TMP/sfizz/build" -type f -name sfizz_render -perm -111 | head -1)
  test -n "$BIN"
  sudo install -m 0755 "$BIN" /usr/local/bin/sfizz_render
  rm -rf "$TMP"
fi
sfizz_render --help | head -30 || true

clone_lfs () {
  repo="$1"; dst="$2"
  if [ ! -d "$dst/.git" ]; then
    git clone --depth=1 "$repo" "$dst" || git clone "$repo" "$dst"
  fi
  (cd "$dst" && git lfs pull)
}

echo "== Baixando bibliotecas reais =="
# Bateria: multi-mic, 10 round-robins, até 5 velocity layers.
clone_lfs https://github.com/sfzinstruments/WilkinsonAudio.NakedDrums.git "$SAMPLES/drums/NakedDrums"

# Baixo: dois baixos de 5 cordas, CC0.
clone_lfs https://github.com/sfzinstruments/karoryfer.black-and-blue-basses.git "$SAMPLES/bass/BlackAndBlue"

# Guitarra elétrica extra: 4 velocity layers, 3 RR, releases/noises e acordes.
clone_lfs https://github.com/sfzinstruments/karoryfer.emilyguitar.git "$SAMPLES/guitar/Emilyguitar"

# Violão aço real (FreePats/FlameStudios), SFZ+WAV "best quality".
if ! find "$SAMPLES/guitar/SteelAcoustic" -name '*.sfz' -print -quit 2>/dev/null | grep -q .; then
  mkdir -p "$SAMPLES/guitar/SteelAcoustic"
  curl -fL --retry 3     https://freepats.zenvoid.org/Guitar/FSS-SteelStringGuitar/FSS-SteelStringGuitar-SFZ-20200521.tar.xz     -o /tmp/musiclite-steel-guitar.tar.xz
  tar -xJf /tmp/musiclite-steel-guitar.tar.xz -C "$SAMPLES/guitar/SteelAcoustic" --strip-components=1 ||     tar -xJf /tmp/musiclite-steel-guitar.tar.xz -C "$SAMPLES/guitar/SteelAcoustic"
  rm -f /tmp/musiclite-steel-guitar.tar.xz
fi

# Acordeon Hohner real, CC0, SFZ+WAV.
if ! find "$SAMPLES/accordion/ButtonAccordionHN" -name '*.sfz' -print -quit 2>/dev/null | grep -q .; then
  mkdir -p "$SAMPLES/accordion/ButtonAccordionHN"
  curl -fL --retry 3     'https://github.com/freepats/button-accordion-HN/releases/download/2024-03-29/ButtonAccordionHN-SFZ%2BWAV-20240329.7z'     -o /tmp/musiclite-accordion.7z
  7z x -y /tmp/musiclite-accordion.7z -o"$SAMPLES/accordion/ButtonAccordionHN" >/dev/null
  rm -f /tmp/musiclite-accordion.7z
fi

# Piano: Yamaha C5, 48kHz/24-bit, 16 velocity layers.
clone_lfs https://github.com/sfzinstruments/SalamanderGrandPiano.git "$SAMPLES/piano/Salamander"

echo "== Instalando API HQ =="
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
rsync -a --delete "$SCRIPT_DIR/musiclite_hq/" "$APP/musiclite_hq/"
cp "$SCRIPT_DIR/requirements.txt" "$APP/requirements.txt"

python3 -m venv "$APP/venv"
"$APP/venv/bin/pip" install --upgrade pip wheel
"$APP/venv/bin/pip" install -r "$APP/requirements.txt"

sudo tee /etc/systemd/system/musiclite-studio-hq.service >/dev/null <<EOF
[Unit]
Description=MusicLite Studio HQ - CPU multisample renderer
After=network.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$APP
Environment=MUSICLITE_HQ_BASE=$BASE
Environment=OMP_NUM_THREADS=$(nproc)
Environment=OPENBLAS_NUM_THREADS=$(nproc)
Environment=MKL_NUM_THREADS=$(nproc)
ExecStart=$APP/venv/bin/uvicorn musiclite_hq.api:app --host 127.0.0.1 --port 8094 --workers 1
Restart=on-failure
RestartSec=3
Nice=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now musiclite-studio-hq.service
sleep 2

echo
echo "== Verificação =="
curl -fsS http://127.0.0.1:8094/health | python3 -m json.tool || {
  sudo journalctl -u musiclite-studio-hq.service -n 100 --no-pager
  exit 30
}

echo
echo "INSTALADO."
echo "Teste de 60s:"
echo "curl -sS -X POST http://127.0.0.1:8094/render/test -H 'Content-Type: application/json' -d '{\"seconds\":60,\"bpm\":126}' | python3 -m json.tool"
echo
echo "Saída final: $BASE/output/"
