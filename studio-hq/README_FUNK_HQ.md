# MusicLite Funk Carioca HQ 0.5

Dedicated Funk Carioca renderer for Studio HQ. It does not reuse the rock/sertanejo DrumGizmo arrangements.

## Sound engine

- 150 BPM default profile with section-aware intro/build/drop/break/final-drop form.
- Dedicated tamborzao/kick and 16th-note swing/microtiming.
- VCSL real claps, agogo and cabasa layers with velocity/round-robin SFZ mapping.
- Locally synthesized 48 kHz kick, low/high tambor, closed/open hats and long 808/sub source.
- Pitched 808 SFZ following an F-minor-oriented progression.
- Funk-specific EQ, compression, low-end management and -11.5 LUFS target master.
- CPU sample rendering through sfizz; other project GPU/neural stages remain optional and can still be used when desired.

## License

VCSL states that its collection is CC0/public domain and may be used in commercial software and media without royalties or attribution requirements. `install_funk_hq.sh` stores the upstream README and LICENSE beside the installed assets for provenance.

The synthesized kick/tamborzao/hats/808 are generated locally by MusicLite and do not depend on third-party samples.

## Install

```bash
cd ~/emusiclite

git pull --ff-only origin main

cd studio-hq
bash ./install_funk_hq.sh
```

Verify:

```bash
curl -sS http://127.0.0.1:8094/health | python3 -m json.tool
```

Expected fields:

```json
{
  "version": "0.5.0",
  "funk_engine_ready": true,
  "supported_genres": ["sertanejo", "rock", "funk"]
}
```

## Test render

```bash
time curl -sS -X POST http://127.0.0.1:8094/render/test \
-H 'Content-Type: application/json' \
-d '{
  "seconds":90,
  "bpm":150,
  "genre":"funk",
  "prompt":"funk carioca profissional de baile, tamborzao forte, sub 808 profundo e controlado, claps secos, hats com swing, agogo e percussao organica, drops marcantes, variacoes humanas, sem sensacao MIDI"
}' | tee ~/funk-carioca-hq.json | python3 -m json.tool
```

Expected render markers:

- `drums_engine: funk_hq05_vcsl_hybrid`
- `sub_engine: musiclite_808_sfz`
- `groove_engine: funk_carioca_humanized_16th`
- output suffix `-funk-hq5-reference.wav`
