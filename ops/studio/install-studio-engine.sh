#!/usr/bin/env bash
set -euo pipefail

# Instala SOMENTE o motor Studio Real do MusicLite em caminhos isolados.
# Execute após revisar ops/ubuntu-inventory.sh.

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  echo "Execute com sudo: sudo bash ops/studio/install-studio-engine.sh" >&2
  exit 1
fi

if ! id musiclite >/dev/null 2>&1; then
  echo "Usuário musiclite não existe. Faça a implantação base antes." >&2
  exit 1
fi

ROOT=/var/lib/musiclite/studio-samples
DOWNLOADS="$ROOT/downloads"
BUILD=/opt/musiclite/studio-build
VENV=/opt/musiclite/studio-venv
STUDIO=/opt/musiclite/studio
MANIFEST=/etc/musiclite/studio-instruments.json

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  fluidsynth ffmpeg curl ca-certificates git cmake g++ make \
  libsndfile1-dev p7zip-full xz-utils python3-venv

install -d -o musiclite -g musiclite -m 0750 "$ROOT" "$DOWNLOADS" "$BUILD" "$STUDIO" /var/lib/musiclite/studio-output
python3 -m venv "$VENV"
"$VENV/bin/pip" install --upgrade pip wheel
"$VENV/bin/pip" install 'fastapi>=0.115,<1' 'uvicorn>=0.30,<1' 'mido>=1.3,<2'

# sfizz_render é necessário apenas para bancos SFZ, como o acordeão.
if ! command -v sfizz_render >/dev/null 2>&1; then
  rm -rf "$BUILD/sfizz"
  git clone --recursive --depth 1 https://github.com/sfztools/sfizz.git "$BUILD/sfizz"
  cmake -S "$BUILD/sfizz" -B "$BUILD/sfizz/build" \
    -DCMAKE_BUILD_TYPE=Release \
    -DSFIZZ_RENDER=ON \
    -DSFIZZ_JACK=OFF \
    -DSFIZZ_LV2=OFF \
    -DSFIZZ_VST=OFF \
    -DSFIZZ_TESTS=OFF
  cmake --build "$BUILD/sfizz/build" --target sfizz_render -j"$(nproc)"
  SFIZZ_BIN=$(find "$BUILD/sfizz/build" -type f -name sfizz_render -perm -111 | head -n1 || true)
  if [[ -z "$SFIZZ_BIN" ]]; then
    echo "Não foi possível localizar sfizz_render após compilação." >&2
    exit 1
  fi
  install -m 0755 "$SFIZZ_BIN" /usr/local/bin/sfizz_render
fi

fetch_extract() {
  local name="$1" url="$2" archive="$3"
  local out="$ROOT/$name"
  install -d -o musiclite -g musiclite -m 0750 "$out"
  if [[ ! -f "$DOWNLOADS/$archive" ]]; then
    echo "Baixando $name..."
    curl -fL --retry 4 --retry-delay 3 -o "$DOWNLOADS/$archive" "$url"
  fi
  rm -rf "$out"/*
  case "$archive" in
    *.7z) 7z x -y -o"$out" "$DOWNLOADS/$archive" >/dev/null ;;
    *.tar.xz) tar -xJf "$DOWNLOADS/$archive" -C "$out" ;;
    *) echo "Formato de arquivo não suportado: $archive" >&2; exit 1 ;;
  esac
}

# Bancos FreePats. Os arquivos abaixo são gravações/sample banks com licenças livres.
fetch_extract steel-guitar \
  'https://freepats.zenvoid.org/Guitar/FSS-SteelStringGuitar/FSS-SteelStringGuitar-SF2-20200521.tar.xz' \
  'FSS-SteelStringGuitar-SF2-20200521.tar.xz'
fetch_extract finger-bass \
  'https://github.com/freepats/electric-bass-YR/releases/download/2019-09-30/FingerBassYR-SF2-20190930.7z' \
  'FingerBassYR-SF2-20190930.7z'
fetch_extract acoustic-drums \
  'https://github.com/freepats/muldjordkit/releases/download/2020-10-18/MuldjordKit-SF2-20201018.7z' \
  'MuldjordKit-SF2-20201018.7z'
fetch_extract clean-electric-guitar \
  'https://github.com/freepats/electric-guitar-FSBS-clean/releases/download/2026-08-07/EGuitarFSBS-clean-SF2-20260807.7z' \
  'EGuitarFSBS-clean-SF2-20260807.7z'
fetch_extract upright-piano \
  'https://freepats.zenvoid.org/Piano/UprightPianoKW/UprightPianoKW-SF2-20220221.7z' \
  'UprightPianoKW-SF2-20220221.7z'
fetch_extract accordion \
  'https://github.com/freepats/button-accordion-HN/releases/download/2024-03-29/ButtonAccordionHN-SFZ%2BFLAC-20240329.7z' \
  'ButtonAccordionHN-SFZ+FLAC-20240329.7z'

link_first() {
  local search_dir="$1" pattern="$2" target="$3"
  local source
  source=$(find "$search_dir" -type f -iname "$pattern" | head -n1 || true)
  if [[ -z "$source" ]]; then
    echo "Arquivo $pattern não encontrado em $search_dir" >&2
    exit 1
  fi
  ln -sfn "$source" "$ROOT/$target"
}

link_first "$ROOT/steel-guitar" '*.sf2' steel-guitar.sf2
link_first "$ROOT/finger-bass" '*.sf2' finger-bass.sf2
link_first "$ROOT/acoustic-drums" '*.sf2' acoustic-drums.sf2
link_first "$ROOT/clean-electric-guitar" '*.sf2' clean-electric-guitar.sf2
link_first "$ROOT/upright-piano" '*.sf2' upright-piano.sf2
link_first "$ROOT/accordion" '*.sfz' accordion.sfz

cat > "$MANIFEST" <<'JSON'
{
  "sample_root": "/var/lib/musiclite/studio-samples",
  "instruments": {
    "steel_guitar": {"engine":"fluidsynth","file":"steel-guitar.sf2","gain":0.78,"role":"acoustic_guitar"},
    "clean_guitar": {"engine":"fluidsynth","file":"clean-electric-guitar.sf2","gain":0.62,"role":"clean_guitar"},
    "electric_bass": {"engine":"fluidsynth","file":"finger-bass.sf2","gain":0.82,"role":"bass"},
    "acoustic_drums": {"engine":"fluidsynth","file":"acoustic-drums.sf2","gain":0.90,"role":"drums","midi_channel":9},
    "accordion": {"engine":"sfizz","file":"accordion.sfz","gain":0.58,"role":"accordion"},
    "upright_piano": {"engine":"fluidsynth","file":"upright-piano.sf2","gain":0.58,"role":"piano"}
  }
}
JSON

chown root:musiclite "$MANIFEST"
chmod 0640 "$MANIFEST"
chown -R musiclite:musiclite "$ROOT" /var/lib/musiclite/studio-output "$STUDIO" "$VENV"

cat <<'EOF'

Studio Real: dependências e bancos instalados.

Próximos passos do deploy do código:
  sudo install -o musiclite -g musiclite -m 0640 ops/studio/musiclite_arranger.py /opt/musiclite/studio/
  sudo install -o musiclite -g musiclite -m 0640 ops/studio/grooves.json /opt/musiclite/studio/
  sudo install -o musiclite -g musiclite -m 0750 ops/generator/musiclite_studio_api.py /opt/musiclite/api/
  sudo install -m 0644 ops/systemd/musiclite-studio.service /etc/systemd/system/
  sudo systemctl daemon-reload
  sudo systemctl enable --now musiclite-studio.service

Teste:
  systemctl status musiclite-studio.service --no-pager
  journalctl -u musiclite-studio.service -n 100 --no-pager
EOF
