#!/bin/sh
# SOMENTE LEITURA. Execute e revise a saída antes de instalar qualquer componente MusicLite.
set -u
echo '=== IDENTIDADE E SISTEMA ==='
id
uname -a
cat /etc/os-release 2>/dev/null || true
echo '=== PORTAS TCP ==='
ss -ltnp
echo '=== SERVICES ==='
systemctl list-units --type=service --all --no-pager
echo '=== UNIT FILES E TIMERS ==='
systemctl list-unit-files --type=service --no-pager
systemctl list-timers --all --no-pager
echo '=== GPU ==='
nvidia-smi || true
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv 2>/dev/null || true
echo '=== PROCESSOS RELEVANTES ==='
ps -eo user,pid,ppid,etime,%cpu,%mem,command | grep -Ei 'ebooklite|ollama|comfy|python|torch|cuda' | grep -v grep || true
echo '=== RECURSOS EBOOKLITE PRESERVADOS ==='
systemctl status ebooklite-worker.service --no-pager 2>/dev/null || true
systemctl status ollama.service --no-pager 2>/dev/null || true
systemctl status comfyui.service --no-pager 2>/dev/null || true
ls -ld /opt/ebooklite /var/lib/ebooklite /etc/ebooklite /etc/ebooklite/worker.env 2>/dev/null || true
echo '=== AMBIENTES PYTHON ==='
find /opt /srv /var/lib -maxdepth 5 -type f \( -name pyvenv.cfg -o -name activate \) -print 2>/dev/null
echo '=== MODELOS E DIRETORIOS ==='
find /opt /srv /var/lib -maxdepth 6 \( -type d -o -type f \) \( -iname '*model*' -o -iname '*checkpoint*' -o -iname '*comfy*' -o -iname '*ollama*' -o -iname '*ebooklite*' \) -print 2>/dev/null
du -sh /opt/ebooklite /var/lib/ebooklite /usr/share/ollama /var/lib/ollama 2>/dev/null || true
df -h
echo '=== PYTHON/CUDA (SOMENTE CONSULTA) ==='
command -v python3 || true
python3 --version 2>/dev/null || true
command -v nvcc >/dev/null 2>&1 && nvcc --version || true
