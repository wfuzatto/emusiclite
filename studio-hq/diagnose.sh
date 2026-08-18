#!/usr/bin/env bash
set -u
echo "=== DISCO ==="
df -h / /var/lib/musiclite 2>/dev/null
echo
echo "=== RAM ==="
free -h
echo
echo "=== CPU ==="
nproc
lscpu | egrep 'Model name|Socket|Core|Thread|CPU\(s\)' | head -20
echo
echo "=== SERVICO ==="
systemctl status musiclite-studio-hq.service --no-pager || true
echo
echo "=== HEALTH ==="
curl -sS http://127.0.0.1:8094/health || true
echo
echo "=== SFIZZ ==="
command -v sfizz_render || true
sfizz_render --help 2>&1 | head -30 || true
echo
echo "=== SAMPLES ==="
du -sh /var/lib/musiclite/studio-hq/samples/*/* 2>/dev/null || true
echo
echo "=== ULTIMO LOG ==="
journalctl -u musiclite-studio-hq.service -n 80 --no-pager || true
