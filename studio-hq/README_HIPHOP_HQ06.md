# MusicLite American Hip-Hop HQ 0.6

Dedicated American southern/luxury hip-hop renderer. The profile targets the general production traits of cinematic, bass-heavy southern rap without reproducing any specific artist or song.

## Engine

- 84 BPM default with a slow half-time pocket.
- Syncopated hard kick, dry snare/clap and restrained hi-hat triplet/16th rolls.
- MusicLite pitched 808/sub engine.
- Dark minor-key upright piano with two velocity layers.
- Real trumpet staccato samples for cinematic brass stabs.
- Real violin-section sustain samples with two dynamics.
- Dedicated intro/verse/hook/verse2/hook2/breakdown/final-hook arrangement.
- Dedicated hip-hop stem EQ, compression, ambience and -11 LUFS reference master.
- Optional ACE-Step neural refinement remains available through `/render/neural`.

Piano, trumpet and violin source samples come from VSCO 2 CE under CC0 1.0. The installer retains the upstream README and LICENSE beside the installed assets.

## Install

```bash
cd ~/emusiclite
git pull --ff-only origin main
cd studio-hq
bash ./install_hiphop_hq.sh
```

The installer automatically installs the lightweight MusicLite electronic base if the Funk HQ kit/808 is not already present.

## Verify

```bash
curl -sS http://127.0.0.1:8094/health | python3 -m json.tool
```

Expected:

```json
{
  "version": "0.6.0",
  "hiphop_engine_ready": true,
  "supported_genres": ["sertanejo", "rock", "funk", "hiphop"]
}
```

## 90-second reference render

```bash
time curl -sS -X POST http://127.0.0.1:8094/render/test \
-H 'Content-Type: application/json' \
-d '{
  "seconds":90,
  "bpm":84,
  "genre":"hiphop",
  "prompt":"luxury southern American hip-hop, cinematic dark minor piano, huge clean 808 sub bass, hard dry kick, deep half-time snare and clap, crisp hi-hats with restrained triplet rolls, dramatic brass stabs, lush orchestral strings, spacious expensive studio production, confident slow groove, large hook sections, humanized timing, no EDM, no rock drums, no cartoon synth brass, no obvious MIDI feel"
}' | tee ~/hiphop-hq06.json | python3 -m json.tool
```

Expected markers:

- `drums_engine: hiphop_hq06_halftime_hybrid`
- `sub_engine: musiclite_808_sfz`
- `piano_engine: vsco2ce_upright_multisample`
- `brass_engine: vsco2ce_trumpet_staccato`
- `strings_engine: vsco2ce_violin_section_sustain`
- `groove_engine: american_southern_luxury_hiphop_humanized`
- output suffix `-hiphop-hq6-reference.wav`
