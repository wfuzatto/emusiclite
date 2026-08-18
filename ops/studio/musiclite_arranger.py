"""Deterministic, humanized symbolic arranger used by the MusicLite studio renderer.

The module creates separate MIDI stems from a musical plan.  It deliberately
keeps the composition symbolic: timbre is provided later by recorded sample
libraries, not by a generative audio model.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import mido

TICKS_PER_BEAT = 480
BEATS_PER_BAR = 4.0

NOTE_BASE = {
    "c": 0, "c#": 1, "db": 1, "d": 2, "d#": 3, "eb": 3,
    "e": 4, "f": 5, "f#": 6, "gb": 6, "g": 7, "g#": 8,
    "ab": 8, "a": 9, "a#": 10, "bb": 10, "b": 11,
}

MAJOR_SCALE = [0, 2, 4, 5, 7, 9, 11]
MINOR_SCALE = [0, 2, 3, 5, 7, 8, 10]


@dataclass
class MidiEvent:
    beat: float
    note: int
    velocity: int
    duration: float


@dataclass
class Stem:
    name: str
    instrument: str
    midi_path: Path
    events: list[MidiEvent]
    channel: int = 0


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _seed_for(payload: dict[str, Any]) -> int:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:16], 16)


def _genre_key(payload: dict[str, Any]) -> str:
    value = f"{payload.get('genre', '')} {payload.get('subgenre', '')}".lower()
    if "sertanej" in value or "country" in value:
        return "sertanejo"
    if "funk" in value:
        return "funk"
    if "mpb" in value or "bossa" in value or "samba" in value:
        return "mpb"
    if "rock" in value:
        return "rock"
    return "pop"


def _parse_key(value: Any) -> tuple[int, bool, str]:
    text = " ".join(str(value or "C Major").strip().lower().split())
    parts = text.replace("minor", " minor").replace("major", " major").split()
    tonic = parts[0] if parts else "c"
    tonic = tonic.replace("♯", "#").replace("♭", "b")
    root = NOTE_BASE.get(tonic, 0)
    minor = "minor" in text or "menor" in text or text.endswith("m")
    return root, minor, tonic


def _degree_chord(root_pc: int, minor_key: bool, degree: int, octave: int = 4) -> list[int]:
    scale = MINOR_SCALE if minor_key else MAJOR_SCALE
    degree %= 7
    root = 12 * (octave + 1) + root_pc + scale[degree]
    third_degree = (degree + 2) % 7
    fifth_degree = (degree + 4) % 7
    third = 12 * (octave + 1) + root_pc + scale[third_degree]
    fifth = 12 * (octave + 1) + root_pc + scale[fifth_degree]
    while third <= root:
        third += 12
    while fifth <= third:
        fifth += 12
    return [root, third, fifth]


def _progression_for(genre: str, minor_key: bool) -> list[int]:
    if genre == "sertanejo":
        return [0, 4, 5, 3] if not minor_key else [0, 5, 2, 6]
    if genre == "mpb":
        return [0, 5, 1, 4, 3, 5, 1, 4]
    if genre == "rock":
        return [0, 3, 5, 4]
    if genre == "funk":
        return [0, 0, 5, 0]
    return [0, 4, 5, 3]


def _section_intensity(structure: Any, beat: float, bpm: int, total_beats: float) -> float:
    if isinstance(structure, list):
        seconds = beat * 60.0 / bpm
        for section in structure:
            if not isinstance(section, dict):
                continue
            try:
                start = float(section.get("start_seconds", 0))
                end = float(section.get("end_seconds", 0))
            except (TypeError, ValueError):
                continue
            if start <= seconds < end:
                name = str(section.get("name", "")).lower()
                if any(word in name for word in ("refr", "chorus", "climax", "drop")):
                    return 1.0
                if any(word in name for word in ("intro", "outro", "final")):
                    return 0.66
                if any(word in name for word in ("ponte", "bridge", "pre")):
                    return 0.82
                return 0.76
    ratio = beat / max(total_beats, 1.0)
    if ratio < 0.12:
        return 0.64
    if ratio > 0.88:
        return 0.7
    if 0.45 < ratio < 0.72:
        return 1.0
    return 0.78


def _humanize_beat(beat: float, bpm: int, milliseconds: int, rng: random.Random) -> float:
    max_beats = (milliseconds / 1000.0) * bpm / 60.0
    return max(0.0, beat + rng.uniform(-max_beats, max_beats))


def _velocity(base: int, intensity: float, jitter: int, rng: random.Random) -> int:
    value = base * intensity + rng.randint(-jitter, jitter)
    return int(_clamp(value, 18, 126))


def _load_groove(path: Path, genre: str) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get(genre) or data["pop"]


def _strum_events(chord: list[int], beat: float, velocity: int, duration: float, down: bool, rng: random.Random) -> list[MidiEvent]:
    notes = chord + [chord[0] + 12]
    if not down:
        notes = list(reversed(notes))
    result: list[MidiEvent] = []
    spread = 0.018 + rng.uniform(-0.004, 0.006)
    for index, note in enumerate(notes):
        result.append(MidiEvent(beat + spread * index, note, max(20, velocity - index * 2), duration))
    return result


def _make_guitar(payload: dict[str, Any], genre: str, groove: dict[str, Any], bars: int, root_pc: int, minor: bool, bpm: int, rng: random.Random) -> list[MidiEvent]:
    progression = _progression_for(genre, minor)
    events: list[MidiEvent] = []
    total_beats = bars * BEATS_PER_BAR
    strums = groove["guitar_strums"]
    accents = groove["guitar_accents"]
    for bar in range(bars):
        chord = _degree_chord(root_pc, minor, progression[bar % len(progression)], octave=3)
        intensity = _section_intensity(payload.get("structure"), bar * 4, bpm, total_beats)
        for index, offset in enumerate(strums):
            beat = bar * 4 + float(offset)
            human = _humanize_beat(beat, bpm, int(groove["humanize_ms"]), rng)
            base = int(88 * float(accents[index % len(accents)]))
            vel = _velocity(base, intensity, int(groove["velocity_jitter"]), rng)
            duration = 0.42 if float(offset) % 1 else 0.62
            events.extend(_strum_events(chord, human, vel, duration, index % 2 == 0, rng))
    return events


def _make_clean_guitar(payload: dict[str, Any], genre: str, bars: int, root_pc: int, minor: bool, bpm: int, rng: random.Random) -> list[MidiEvent]:
    progression = _progression_for(genre, minor)
    events: list[MidiEvent] = []
    total_beats = bars * 4
    pattern = [0, 2, 1, 3, 2, 1]
    for bar in range(bars):
        if bar < 2:
            continue
        chord = _degree_chord(root_pc, minor, progression[bar % len(progression)], octave=4)
        expanded = [chord[0], chord[1], chord[2], chord[0] + 12]
        intensity = _section_intensity(payload.get("structure"), bar * 4, bpm, total_beats)
        for i in range(8):
            beat = bar * 4 + i * 0.5
            note = expanded[pattern[i % len(pattern)] % len(expanded)]
            events.append(MidiEvent(_humanize_beat(beat, bpm, 11, rng), note, _velocity(66, intensity, 7, rng), 0.36))
    return events


def _make_bass(payload: dict[str, Any], genre: str, groove: dict[str, Any], bars: int, root_pc: int, minor: bool, bpm: int, rng: random.Random) -> list[MidiEvent]:
    progression = _progression_for(genre, minor)
    events: list[MidiEvent] = []
    total_beats = bars * 4
    for bar in range(bars):
        degree = progression[bar % len(progression)]
        chord = _degree_chord(root_pc, minor, degree, octave=2)
        root = chord[0]
        fifth = chord[2]
        intensity = _section_intensity(payload.get("structure"), bar * 4, bpm, total_beats)
        beats = [float(x) for x in groove["bass_beats"]]
        for index, offset in enumerate(beats):
            note = root if index % 2 == 0 else (fifth - 12 if fifth > root + 7 else fifth)
            if index == len(beats) - 1 and rng.random() < 0.45:
                note = root + (2 if rng.random() < 0.5 else -1)
            beat = _humanize_beat(bar * 4 + offset, bpm, int(groove["humanize_ms"] * 0.7), rng)
            events.append(MidiEvent(beat, note, _velocity(92, intensity, 7, rng), 0.42 if len(beats) > 3 else 0.7))
    return events


def _make_drums(payload: dict[str, Any], genre: str, groove: dict[str, Any], bars: int, bpm: int, rng: random.Random) -> list[MidiEvent]:
    events: list[MidiEvent] = []
    total_beats = bars * 4
    fill_every = int(groove.get("fill_every_bars", 8))
    for bar in range(bars):
        intensity = _section_intensity(payload.get("structure"), bar * 4, bpm, total_beats)
        is_fill = fill_every > 0 and (bar + 1) % fill_every == 0
        if bar == 0:
            events.append(MidiEvent(0.0, 49, _velocity(105, intensity, 4, rng), 0.2))
        for offset in groove["kick"]:
            events.append(MidiEvent(_humanize_beat(bar * 4 + float(offset), bpm, int(groove["humanize_ms"]), rng), 36, _velocity(108, intensity, 8, rng), 0.12))
        for offset in groove["snare"]:
            events.append(MidiEvent(_humanize_beat(bar * 4 + float(offset), bpm, int(groove["humanize_ms"]), rng), 38, _velocity(104, intensity, 9, rng), 0.12))
        for index, offset in enumerate(groove["hihat"]):
            note = 46 if index == len(groove["hihat"]) - 1 and intensity > 0.95 else 42
            base = 70 if index % 2 == 0 else 57
            events.append(MidiEvent(_humanize_beat(bar * 4 + float(offset), bpm, int(groove["humanize_ms"]), rng), note, _velocity(base, intensity, 10, rng), 0.08))
        if is_fill:
            for i, note in enumerate([45, 47, 48, 50]):
                events.append(MidiEvent(_humanize_beat(bar * 4 + 3.0 + i * 0.25, bpm, 8, rng), note, _velocity(92 + i * 3, intensity, 8, rng), 0.1))
    return events


def _make_accordion(payload: dict[str, Any], genre: str, bars: int, root_pc: int, minor: bool, bpm: int, rng: random.Random) -> list[MidiEvent]:
    if genre not in {"sertanejo", "mpb"}:
        return []
    progression = _progression_for(genre, minor)
    scale = MINOR_SCALE if minor else MAJOR_SCALE
    events: list[MidiEvent] = []
    total_beats = bars * 4
    for bar in range(bars):
        intensity = _section_intensity(payload.get("structure"), bar * 4, bpm, total_beats)
        if intensity < 0.75 and bar % 4 not in {1, 3}:
            continue
        degree = progression[bar % len(progression)]
        base_pc = (root_pc + scale[degree % 7]) % 12
        base = 60 + base_pc
        motif = [0, 4, 7, 9, 7, 4] if not minor else [0, 3, 7, 10, 7, 3]
        start = bar * 4 + (2.0 if bar % 2 == 0 else 0.0)
        for i, interval in enumerate(motif):
            beat = start + i * 0.32
            if beat >= (bar + 1) * 4:
                break
            events.append(MidiEvent(_humanize_beat(beat, bpm, 18, rng), base + interval, _velocity(70 if intensity < 0.95 else 84, intensity, 8, rng), 0.27))
    return events


def _make_piano(payload: dict[str, Any], genre: str, bars: int, root_pc: int, minor: bool, bpm: int, rng: random.Random) -> list[MidiEvent]:
    if genre == "sertanejo":
        return []
    progression = _progression_for(genre, minor)
    events: list[MidiEvent] = []
    total_beats = bars * 4
    for bar in range(bars):
        chord = _degree_chord(root_pc, minor, progression[bar % len(progression)], octave=4)
        intensity = _section_intensity(payload.get("structure"), bar * 4, bpm, total_beats)
        for offset in (0.0, 2.0):
            for note in chord:
                events.append(MidiEvent(_humanize_beat(bar * 4 + offset, bpm, 12, rng), note, _velocity(62, intensity, 7, rng), 1.55))
    return events


def write_midi(path: Path, events: Iterable[MidiEvent], bpm: int, channel: int = 0) -> None:
    midi = mido.MidiFile(type=1, ticks_per_beat=TICKS_PER_BEAT)
    track = mido.MidiTrack()
    midi.tracks.append(track)
    track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(bpm), time=0))
    track.append(mido.Message("program_change", program=0, channel=channel, time=0))
    absolute: list[tuple[int, int, mido.Message]] = []
    for event in events:
        start = max(0, round(event.beat * TICKS_PER_BEAT))
        end = max(start + 1, round((event.beat + event.duration) * TICKS_PER_BEAT))
        note = int(_clamp(event.note, 0, 127))
        velocity = int(_clamp(event.velocity, 1, 127))
        absolute.append((start, 1, mido.Message("note_on", note=note, velocity=velocity, channel=channel, time=0)))
        absolute.append((end, 0, mido.Message("note_off", note=note, velocity=0, channel=channel, time=0)))
    absolute.sort(key=lambda item: (item[0], item[1]))
    previous = 0
    for tick, _, message in absolute:
        message.time = max(0, tick - previous)
        track.append(message)
        previous = tick
    track.append(mido.MetaMessage("end_of_track", time=TICKS_PER_BEAT))
    midi.save(path)


def arrange(payload: dict[str, Any], output_dir: Path, grooves_path: Path) -> dict[str, Any]:
    bpm = int(payload.get("bpm") or 112)
    bpm = max(55, min(190, bpm))
    duration = int(payload.get("duration_seconds") or 60)
    duration = max(30, min(180, duration))
    total_beats = duration * bpm / 60.0
    bars = max(4, math.ceil(total_beats / BEATS_PER_BAR))
    root_pc, minor, tonic = _parse_key(payload.get("key"))
    genre = _genre_key(payload)
    groove = _load_groove(grooves_path, genre)
    rng = random.Random(_seed_for(payload))

    builders = [
        ("steel_guitar", "steel_guitar", _make_guitar(payload, genre, groove, bars, root_pc, minor, bpm, rng), 0),
        ("clean_guitar", "clean_guitar", _make_clean_guitar(payload, genre, bars, root_pc, minor, bpm, rng), 0),
        ("electric_bass", "electric_bass", _make_bass(payload, genre, groove, bars, root_pc, minor, bpm, rng), 0),
        ("acoustic_drums", "acoustic_drums", _make_drums(payload, genre, groove, bars, bpm, rng), 9),
        ("accordion", "accordion", _make_accordion(payload, genre, bars, root_pc, minor, bpm, rng), 0),
        ("upright_piano", "upright_piano", _make_piano(payload, genre, bars, root_pc, minor, bpm, rng), 0),
    ]

    stems: list[dict[str, Any]] = []
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, instrument, events, channel in builders:
        if not events:
            continue
        midi_path = output_dir / f"{name}.mid"
        write_midi(midi_path, events, bpm, channel)
        stems.append({"name": name, "instrument": instrument, "midi_path": str(midi_path), "events": len(events), "channel": channel})

    arrangement = {
        "engine": "studio-midi-sampled",
        "genre_profile": genre,
        "bpm": bpm,
        "duration_seconds": duration,
        "bars": bars,
        "key": tonic,
        "minor": minor,
        "stems": stems,
    }
    (output_dir / "arrangement.json").write_text(json.dumps(arrangement, ensure_ascii=False, indent=2), encoding="utf-8")
    return arrangement
