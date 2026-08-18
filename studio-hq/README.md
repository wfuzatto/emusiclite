MUSICLITE STUDIO HQ — TESTE DE QUALIDADE MÁXIMA

Objetivo:
- não substituir o Studio atual
- subir um renderer CPU-only em 127.0.0.1:8094
- baixar bibliotecas SFZ multisample reais
- gerar MIDI com "músicos" diferentes por instrumento
- renderizar stems offline em 48 kHz/24-bit
- usar room bus compartilhado e master conservador
- aceitar perfis de gênero musical

GÊNEROS ATUAIS
- sertanejo: bateria, baixo, violão aço, piano e acordeon
- rock: bateria rock, baixo pulsante e guitarra elétrica em duas execuções L/R

INSTALAÇÃO
1) entre na pasta studio-hq
2) rode:
   chmod +x install_hq.sh diagnose.sh
   ./install_hq.sh

HEALTHCHECK
curl -sS http://127.0.0.1:8094/health | python3 -m json.tool

LISTAR GÊNEROS
curl -sS http://127.0.0.1:8094/genres | python3 -m json.tool

TESTE SERTANEJO
curl -sS -X POST http://127.0.0.1:8094/render/test \
  -H 'Content-Type: application/json' \
  -d '{"seconds":60,"bpm":126,"genre":"sertanejo"}' | python3 -m json.tool

TESTE ROCK
curl -sS -X POST http://127.0.0.1:8094/render/test \
  -H 'Content-Type: application/json' \
  -d '{"seconds":60,"bpm":132,"genre":"rock"}' | python3 -m json.tool

TESTE POR PROMPT
Se "genre" for omitido, o Studio HQ tenta identificar o gênero pelo prompt:

curl -sS -X POST http://127.0.0.1:8094/render/test \
  -H 'Content-Type: application/json' \
  -d '{"seconds":60,"bpm":135,"prompt":"rock brasileiro energético, guitarras distorcidas, bateria acústica forte e baixo presente"}' \
  | python3 -m json.tool

Neste estágio, o prompt seleciona o perfil de gênero. Ele ainda não é um compositor LLM livre.
A próxima integração deverá usar o planner/Ollama para transformar prompt em estrutura,
acordes, seções, riffs, dinâmica e instrumentação.

ROCK
- usa Emily Guitar gravada DI
- duas performances MIDI independentes para guitarra esquerda/direita
- estágio offline de drive/amp-like via SoX
- EQ de caixa/amplificador
- bateria e baixo recebem performances e mix próprios
- acordeon e violão acústico não entram no perfil rock

SAÍDA
/var/lib/musiclite/studio-hq/output/

DIAGNÓSTICO
./diagnose.sh

Não apaga nem altera:
  musiclite-generator.service
  musiclite-studio.service
  musiclite-worker.service
  ollama.service
  comfyui.service
