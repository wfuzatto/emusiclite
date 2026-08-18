# Studio Real — MIDI + samples de instrumentos reais

Este backend existe para reduzir o caráter sintético dos geradores text-to-audio quando a música exige instrumentos acústicos convincentes.

## Arquitetura

1. O Ollama continua criando o planejamento musical (BPM, tonalidade, estrutura e instrumentos).
2. `musiclite_arranger.py` transforma o planejamento em pistas MIDI separadas.
3. As pistas recebem humanização de tempo, velocity, acentos, palhetada, dinâmica por seção e viradas.
4. Cada pista MIDI é renderizada por um banco de samples gravado de instrumento real.
5. As pistas viram WAV separados e são mixadas/masterizadas com FFmpeg.
6. O arquivo final segue o mesmo pipeline de validação, ingestão e capa do eMusicLite.

O modo atual é instrumental. A voz deve continuar em outro backend até existir um pipeline vocal separado.

## Instrumentos instalados pelo script

O instalador `install-studio-engine.sh` baixa bancos do projeto FreePats. Os samples não são copiados para este repositório.

- Violão de aço: FSS Steel-String Acoustic Guitar — FreePats GPLv3+ com exceção para samples.
- Baixo elétrico: Bass Guitar YR (finger) — CC0 1.0.
- Bateria acústica: MuldjordKit — CC BY 4.0, com velocity layers e sons randomizados.
- Guitarra elétrica limpa: FSBS Electric Guitar Clean — CC0 1.0.
- Piano vertical Kawai: Upright Piano KW — CC0 1.0.
- Acordeão Hohner: Button Accordion HN — CC0 1.0.

Consulte sempre as páginas originais do FreePats e preserve atribuições exigidas pelos bancos usados.

## Dependências

- Python 3 + venv isolado `/opt/musiclite/studio-venv`
- `mido` para escrita MIDI
- FluidSynth para SoundFont/SF2
- `sfizz_render` para SFZ
- FFmpeg para mix/master

O FluidSynth é um sintetizador baseado em SoundFont e consegue renderizar arquivos MIDI para áudio. `sfizz_render` renderiza um MIDI através de um instrumento SFZ para WAV.

## Instalação

Primeiro revise o inventário do host, conforme `ops/DEPLOYMENT.md`.

```bash
sudo bash ops/studio/install-studio-engine.sh
```

Depois copie o código:

```bash
sudo install -d -o musiclite -g musiclite -m 0750 /opt/musiclite/studio /opt/musiclite/api
sudo install -o musiclite -g musiclite -m 0640 ops/studio/musiclite_arranger.py /opt/musiclite/studio/
sudo install -o musiclite -g musiclite -m 0640 ops/studio/grooves.json /opt/musiclite/studio/
sudo install -o musiclite -g musiclite -m 0750 ops/generator/musiclite_studio_api.py /opt/musiclite/api/
sudo install -m 0644 ops/systemd/musiclite-studio.service /etc/systemd/system/
```

Adicione/ajuste no `/etc/musiclite/worker.env`:

```text
MUSIC_AI_STUDIO_URL=http://127.0.0.1:8093
MUSIC_AI_STUDIO_PORT=8093
MUSIC_AI_STUDIO_TOKEN=<segredo com pelo menos 32 caracteres>
MUSIC_AI_STUDIO_TIMEOUT=1800
MUSIC_AI_STUDIO_MAX_DURATION=180
MUSIC_AI_STUDIO_OUTPUT_PATH=/var/lib/musiclite/studio-output
MUSIC_AI_STUDIO_MANIFEST=/etc/musiclite/studio-instruments.json
MUSIC_AI_STUDIO_CODE_PATH=/opt/musiclite/studio
MUSIC_AI_STUDIO_GROOVES=/opt/musiclite/studio/grooves.json
```

Então:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now musiclite-studio.service
sudo systemctl restart musiclite-worker.service
systemctl status musiclite-studio.service --no-pager
journalctl -u musiclite-studio.service -n 100 --no-pager
```

## O que melhora e o que não melhora

A principal melhoria é de **timbre**: o som vem de gravações reais, em vez de o modelo tentar sintetizar um violão, baixo ou sanfona. A composição e a execução ainda são produzidas por regras/IA e, portanto, não equivalem automaticamente a uma banda humana. A qualidade final cresce muito quando bancos com múltiplas velocities, round-robin e articulações são usados.

O manifest `/etc/musiclite/studio-instruments.json` foi feito para permitir substituir qualquer banco FreePats por uma biblioteca SF2/SFZ melhor, desde que você tenha direito de uso. Assim, o motor pode evoluir sem alterar o restante da aplicação.
