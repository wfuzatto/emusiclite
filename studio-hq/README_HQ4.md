# MusicLite Neural Studio 0.4

O HQ3 continua sendo o diretor musical determinístico. A versão 0.4 acrescenta uma segunda etapa neural para evitar que o áudio final soe como reprodução de samples.

## Pipeline

1. HQ3 gera uma performance de referência com forma musical, MIDI humanizado e instrumentos reais.
2. A referência é enviada ao ACE-Step 1.5 no modo `cover`.
3. O ACE-Step ressintetiza a música como áudio contínuo, preservando estrutura em graus diferentes.
4. São gerados vários takes sequencialmente para caber no perfil de GPU de 6 GB.
5. Um critic técnico mede clipping, silêncio, dinâmica, espectro e correlação de envelope com a referência.
6. Todos os takes são preservados; o melhor ranking técnico é copiado para `studio-hq/output`.

O critic **não é um detector de IA** e não afirma qual take é artisticamente melhor. Ele evita escolher automaticamente um take tecnicamente degradado.

## Por que Cover/Remix

ACE-Step 1.5 suporta oficialmente Cover/Remix no modelo Turbo. `audio_cover_strength` alto preserva mais a estrutura; valores menores permitem que o modelo recrie mais a execução/timbre.

O Neural Studio usa, por padrão:
- take controlado
- take balanceado
- take criativo
- um take livre `text2music` para explorar uma interpretação menos presa à referência

O ACE-Step Turbo usa `shift=3.0`, conforme a recomendação do projeto upstream.

## Instalação

```bash
cd ~/emusiclite
git pull origin main
cd studio-hq
chmod +x upgrade_hq4.sh
./upgrade_hq4.sh
```

O script preserva HQ3, atualiza o adaptador ACE-Step e instala um `/etc/musiclite/neural.env` dedicado contendo somente o token local, URL e timeout necessários ao HQ; as demais credenciais do worker não são carregadas no processo HQ.

## Render máximo

Para liberar VRAM, pare temporariamente o ComfyUI se ele estiver ocupando a GPU:

```bash
sudo systemctl stop comfyui.service
```

Depois:

```bash
curl -sS -X POST http://127.0.0.1:8094/render/neural \
  -H 'Content-Type: application/json' \
  -d '{
    "seconds":90,
    "bpm":132,
    "genre":"rock",
    "prompt":"rock brasileiro gravado em estúdio profissional, músicos humanos, refrão memorável, guitarras orgânicas, bateria acústica natural",
    "candidates":4,
    "cover_strength":0.55,
    "exploration":true,
    "instrumental":true
  }' | python3 -m json.tool
```

O WAV escolhido termina em `-neural04.wav`.

## Limite atual de voz

No perfil legado da GTX 1060 6 GB, a instalação atual usa quantização `w8a8_dynamic`. O serviço continua rejeitando geração vocal neural nesse perfil para evitar OOM conhecido. Instrumentais usam o Neural Studio normalmente.

## Controles principais

- `candidates`: 1–8; default recomendado no servidor atual: 4.
- `cover_strength`: 0.10–0.95; default 0.55.
- `exploration=true`: inclui um candidato livre além dos covers.
- `MUSIC_AI_NEURAL_STEPS`: default 12.
- `MUSIC_AI_NEURAL_MAX_CANDIDATES`: default 4.
