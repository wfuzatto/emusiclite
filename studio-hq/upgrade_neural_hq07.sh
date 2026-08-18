#!/usr/bin/env bash
set -Eeuo pipefail

APP="/opt/musiclite/studio-hq"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_USER="${MUSICLITE_HQ_USER:-musiclite}"
SERVICE_GROUP="${MUSICLITE_HQ_GROUP:-musiclite}"

echo "== MusicLite Neural HQ 0.7 =="

test -f "$SCRIPT_DIR/musiclite_hq/neural.py"
test -f "$SCRIPT_DIR/musiclite_hq/api.py"
sudo test -d "$APP"

if ! sudo systemctl cat musiclite-studio-hq.service >/dev/null 2>&1; then
  echo "ERRO: musiclite-studio-hq.service não está instalado."
  exit 20
fi

if ! sudo test -f /etc/musiclite/neural.env; then
  echo "ERRO: /etc/musiclite/neural.env não existe. Rode studio-hq/upgrade_hq4.sh primeiro."
  exit 21
fi

echo "== Validando Python =="
python3 -m py_compile "$SCRIPT_DIR/musiclite_hq/neural.py" "$SCRIPT_DIR/musiclite_hq/api.py"

echo "== Deploy orchestrator HQ 0.7 =="
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
assert h.get('neural_engine') == 'ace-step-1.5-cover-hq07', h
assert h.get('neural_configured') is True, h
assert h.get('funk_engine_ready') is True, h
print('NEURAL HQ 0.7: READY')
PY

echo
echo "Upgrade neural concluído. Samples e bibliotecas existentes não foram reinstalados."
