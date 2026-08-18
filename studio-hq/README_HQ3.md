# MusicLite Studio HQ 0.3 — Realism Engine

Objetivo: sair do "MIDI com timbre bom" e se aproximar de uma sessão de estúdio.

## Mudanças principais

- DrumGizmo multi-mic:
  - Rock: CrocellKit (15 canais)
  - Sertanejo/pop: DRSKit (13 canais)
- Guitarra rock: Metal GTX preferencial; Standard Guitar como segunda opção.
- Baixo: Standard Bass preferencial.
- Guitar amp/cab offline: saturação + convolution cabinet IR.
- L/R guitarists são performances independentes; não é cópia com delay.
- Bateria tem close mics, overheads e room reais, com parallel compression.
- Forma musical por seções: intro, verse, pre, chorus, bridge, final chorus, outro.
- Tempo drift correlacionado, section push/pull, timing por músico.
- Master conservador para preservar transientes.
- Fallbacks são registrados em `manifest.json`; nunca são escondidos.

## Upgrade

```bash
cd ~/emusiclite
git pull origin main
cd studio-hq
chmod +x upgrade_hq3.sh
./upgrade_hq3.sh
```

## Teste rock

```bash
curl -sS -X POST http://127.0.0.1:8094/render/test \
  -H 'Content-Type: application/json' \
  -d '{"seconds":90,"bpm":132,"genre":"rock","prompt":"rock brasileiro de estúdio, bateria acústica real, guitarras grandes e humanas"}' \
  | python3 -m json.tool
```

O JSON deve indicar `version: 0.3.0`. O alvo principal é `drums_engine: drumgizmo_multimic`; qualquer fallback de instrumento aparece em `library_fallbacks` para diagnóstico.
