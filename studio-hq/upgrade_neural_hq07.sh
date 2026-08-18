#!/usr/bin/env bash
set -Eeuo pipefail

APP="/opt/musiclite/studio-hq"
GEN_API="/opt/musiclite/api/musiclite_generator_api.py"
GEN_PY="/opt/musiclite/venv/bin/python"
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

if ! sudo systemctl cat musiclite-generator.service >/dev/null 2>&1; then
  echo "ERRO: musiclite-generator.service não está instalado."
  exit 22
fi

if ! sudo test -f /etc/musiclite/neural.env; then
  echo "ERRO: /etc/musiclite/neural.env não existe. Rode studio-hq/upgrade_hq4.sh primeiro."
  exit 21
fi

if ! sudo test -f "$GEN_API"; then
  echo "ERRO: adapter neural não encontrado em $GEN_API."
  exit 23
fi

echo "== Validando Python =="
python3 -m py_compile "$SCRIPT_DIR/musiclite_hq/neural.py" "$SCRIPT_DIR/musiclite_hq/api.py"

echo "== Corrigindo readiness de VRAM com ACE-Step já carregado =="
sudo python3 - "$GEN_API" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
old_check = '''def _check_resources() -> None:\n    free_vram = _free_vram_mb()\n    if free_vram is None or free_vram < MIN_FREE_VRAM_MB:\n        raise HTTPException(status_code=503, detail="Recursos temporariamente indisponíveis.")\n'''
new_check = '''def _check_resources() -> None:\n    # Quando o ACE-Step já está carregado, a VRAM ocupada pertence ao próprio\n    # gerador. Exigir MIN_FREE_VRAM_MB novamente causava um falso 503 na\n    # geração seguinte. O limite alto só é necessário antes do cold start.\n    if _dit_handler is not None:\n        return\n    free_vram = _free_vram_mb()\n    if free_vram is None or free_vram < MIN_FREE_VRAM_MB:\n        raise HTTPException(status_code=503, detail="Recursos temporariamente indisponíveis.")\n'''
old_health = '"resources_ready": free_vram is not None and free_vram >= MIN_FREE_VRAM_MB,'
new_health = '"resources_ready": _dit_handler is not None or (free_vram is not None and free_vram >= MIN_FREE_VRAM_MB),'

changed = False
if old_check in text:
    text = text.replace(old_check, new_check, 1)
    changed = True
elif 'if _dit_handler is not None:\n        return\n    free_vram = _free_vram_mb()' not in text:
    raise SystemExit("ERRO: bloco _check_resources desconhecido; patch abortado.")

if old_health in text:
    text = text.replace(old_health, new_health, 1)
    changed = True
elif new_health not in text:
    raise SystemExit("ERRO: campo resources_ready desconhecido; patch abortado.")

if changed:
    path.write_text(text, encoding="utf-8")
    print("VRAM warm-handler patch aplicado.")
else:
    print("VRAM warm-handler patch já estava aplicado.")
PY

if sudo test -x "$GEN_PY"; then
  sudo "$GEN_PY" -m py_compile "$GEN_API"
else
  sudo python3 -m py_compile "$GEN_API"
fi

echo "== Deploy orchestrator HQ 0.7 =="
sudo rsync -a --delete "$SCRIPT_DIR/musiclite_hq/" "$APP/musiclite_hq/"
sudo cp "$SCRIPT_DIR/requirements.txt" "$APP/requirements.txt"
sudo chmod -R a+rX "$APP"

sudo systemctl restart musiclite-generator.service
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
