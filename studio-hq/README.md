MUSICLITE STUDIO HQ — TESTE DE QUALIDADE MÁXIMA

Objetivo:
- não substituir o Studio atual
- subir um renderer CPU-only em 127.0.0.1:8094
- baixar bibliotecas SFZ multisample reais (bateria, baixo, violão aço, acordeon, piano e guitarra elétrica extra)
- gerar MIDI com "músicos" diferentes por instrumento
- renderizar stems offline em 48 kHz
- usar um único room bus e master conservador

INSTALAÇÃO
1) copie/extraia esta pasta no Ubuntu
2) entre nela
3) rode:
   chmod +x install_hq.sh diagnose.sh
   ./install_hq.sh

TESTE
curl -sS -X POST http://127.0.0.1:8094/render/test \
  -H 'Content-Type: application/json' \
  -d '{"seconds":60,"bpm":126}' | python3 -m json.tool

O WAV final fica em:
  /var/lib/musiclite/studio-hq/output/

DIAGNÓSTICO
  ./diagnose.sh

IMPORTANTE
O teste deliberadamente usa um arranjo determinístico sertanejo/pop simples G-D-Em-C, com violão aço e acordeon.
Isso é proposital: primeiro julgamos SOM, dinâmica, groove e sensação humana
sem misturar o problema de composição da IA.
Depois de aprovado, o mesmo renderer deve ser ligado ao planner/arranger do MusicLite.

Não apaga nem altera:
  musiclite-generator.service
  musiclite-studio.service
  musiclite-worker.service
  ollama.service
  comfyui.service
