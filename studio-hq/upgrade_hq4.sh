#!/usr/bin/env bash
set -Eeuo pipefail

BASE="/var/lib/musiclite/studio-hq"
APP="/opt/musiclite/studio-hq"
GEN_API="/opt/musiclite/api"
GEN_APP="/opt/musiclite/generator"
ENV_FILE="/etc/musiclite/worker.env"
SERVICE_USER="${MUSICLITE_HQ_USER:-musiclite}"
SERVICE_GROUP="${MUSICLITE_HQ_GROUP:-musiclite}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "== MusicLite Neural Studio 0.4 =="

test -f "$REPO_ROOT/ops/generator/musiclite_generator_api.py"
test -f "$REPO_ROOT/ops/generator/musiclite_audio_critic.py"
test -f "$SCRIPT_DIR/musiclite_hq/neural.py"

if ! sudo test -f "$ENV_FILE"; then
  echo "ERRO: $ENV_FILE não existe. O token do gerador é obrigatório."
  exit 20
fi

TOKEN_LEN=$(sudo awk -F= '$1=="MUSIC_AI_GENERATOR_TOKEN"{sub(/^MUSIC_AI_GENERATOR_TOKEN=/,""); print length($0); exit}' "$ENV_FILE")
if [ "${TOKEN_LEN:-0}" -lt 32 ]; then
  echo "ERRO: MUSIC_AI_GENERATOR_TOKEN precisa ter ao menos 32 caracteres."
  exit 21
fi

ensure_env () {
  key="$1"; value="$2"
  if ! sudo grep -q "^${key}=" "$ENV_FILE"; then
    printf '%s=%s\n' "$key" "$value" | sudo tee -a "$ENV_FILE" >/dev/null
    echo "Adicionado em worker.env: $key"
  fi
}

ensure_env MUSIC_AI_NEURAL_STEPS 12
ensure_env MUSIC_AI_NEURAL_MAX_CANDIDATES 4
ensure_env MUSIC_AI_NEURAL_SOURCE_ROOTS "/var/lib/musiclite/studio-hq/output:/var/lib/musiclite/neural-studio"
ensure_env MUSICLITE_NEURAL_GENERATOR_URL "http://127.0.0.1:8091"
ensure_env MUSICLITE_NEURAL_TIMEOUT 5400

sudo install -d -o "$SERVICE_USER" -g "$SERVICE_GROUP" -m 0750 \
  /var/lib/musiclite/neural-studio "$BASE/output" "$BASE/work"
sudo install -d -o root -g root -m 0755 "$GEN_API" "$GEN_APP" "$APP"

echo "== Generator Python dependencies =="
if ! /opt/musiclite/venv/bin/python -c 'import numpy, soundfile' >/dev/null 2>&1; then
  sudo /opt/musiclite/venv/bin/pip install -q numpy soundfile
fi

echo "== Deploy generator neural adapter =="
sudo install -o root -g root -m 0644 \
  "$REPO_ROOT/ops/generator/musiclite_generator_api.py" \
  "$GEN_API/musiclite_generator_api.py"
sudo install -o root -g root -m 0644 \
  "$REPO_ROOT/ops/generator/musiclite_audio_critic.py" \
  "$GEN_APP/musiclite_audio_critic.py"

echo "== Deploy HQ 0.4 orchestrator =="
sudo rsync -a --delete "$SCRIPT_DIR/musiclite_hq/" "$APP/musiclite_hq/"
sudo cp "$SCRIPT_DIR/requirements.txt" "$APP/requirements.txt"
sudo chmod -R a+rX "$APP"

sudo chown -R "$SERVICE_USER":"$SERVICE_GROUP" "$BASE" /var/lib/musiclite/neural-studio
sudo chmod -R u+rwX,go-rwx "$BASE" /var/lib/musiclite/neural-studio

if [ -x "$APP/venv/bin/pip" ]; then
  sudo "$APP/venv/bin/pip" install -q -r "$APP/requirements.txt"
fi

echo "== systemd: expose only the existing worker.env to HQ =="
sudo install -d -m 0755 /etc/systemd/system/musiclite-studio-hq.service.d
sudo tee /etc/systemd/system/musiclite-studio-hq.service.d/neural-studio.conf >/dev/null <<'EOF'
[Service]
EnvironmentFile=-/etc/musiclite/worker.env
Environment=MUSICLITE_NEURAL_GENERATOR_URL=http://127.0.0.1:8091
Environment=MUSICLITE_NEURAL_TIMEOUT=5400
EOF

sudo systemctl daemon-reload
sudo systemctl restart musiclite-generator.service
sudo systemctl restart musiclite-studio-hq.service
sleep 3

echo "== HQ health =="
curl -fsS http://127.0.0.1:8094/health | python3 -m json.tool

echo "== Generator health =="
sudo bash -c '
  set -a
  source /etc/musiclite/worker.env
  set +a
  curl -fsS -H "Authorization: Bearer $MUSIC_AI_GENERATOR_TOKEN" \
    http://127.0.0.1:8091/health
' | python3 -m json.tool

if [ "${MUSICLITE_HQ4_SKIP_SMOKE:-0}" != "1" ]; then
  echo "== Neural smoke test: 20s / 1 take =="
  COMFY_WAS_ACTIVE=0
  if sudo systemctl is-active --quiet comfyui.service; then
    COMFY_WAS_ACTIVE=1
    sudo systemctl stop comfyui.service
  fi
  restore_comfy () {
    if [ "$COMFY_WAS_ACTIVE" = "1" ]; then
      sudo systemctl start comfyui.service || true
    fi
  }
  trap restore_comfy EXIT

  curl -fsS -X POST http://127.0.0.1:8094/render/neural \
    -H 'Content-Type: application/json' \
    -d '{
      "seconds":20,
      "bpm":132,
      "genre":"rock",
      "prompt":"rock de estúdio com músicos humanos, dinâmica natural, guitarras orgânicas e bateria acústica real",
      "candidates":1,
      "cover_strength":0.55,
      "exploration":false,
      "instrumental":true
    }' | python3 -m json.tool

  restore_comfy
  trap - EXIT
fi

echo
echo "NEURAL STUDIO 0.4 instalado."
echo "Para máxima qualidade, gere 4 takes:"
echo "curl -sS -X POST http://127.0.0.1:8094/render/neural -H 'Content-Type: application/json' -d '{\"seconds\":90,\"bpm\":132,\"genre\":\"rock\",\"prompt\":\"rock brasileiro gravado em estúdio profissional, músicos humanos, refrão memorável, guitarras orgânicas, bateria acústica natural\",\"candidates\":4,\"cover_strength\":0.55,\"exploration\":true,\"instrumental\":true}' | python3 -m json.tool"
