from __future__ import annotations

from . import __name__ as _pkg_name  # keep package import explicit for deployment checks
from ..humanize import Humanizer
from ..midi_tools import PPQ, add_note
from ..song_form import section_for_bar

# D minor / Bb / F / C: a familiar emotional chillstep cycle, voiced wide.
ROOTS = [38, 34, 41, 36]
PAD_CHORDS = [
    [62, 65, 69, 72],   # Dm7
    [58, 62, 65, 69],   # Bbmaj7
    [65, 69, 72, 76],   # Fmaj7
    [60, 64, 67, 74],   # Cadd9
]
PLUCK_TONES = [
    [74, 77, 81, 84],
    [70, 74, 77, 81],
    [77, 81, 84, 88],
    [72, 76, 79, 86],
]
LEAD_PATTERNS = [
    [(0.0, 81, 1.0), (1.0, 84, .5), (1.5, 86, .5), (2.0, 84, 1.0), (3.0, 81, 1.0)],
    [(0.0, 77, 1.5), (1.5, 81, .5), (2.0, 79, 1.0), (3.0, 77, 1.0)],
    [(0.0, 84, 1.0), (1.0, 81, 1.0), (2.0, 79, .5), (2.5, 81, .5), (3.0, 84, 1.0)],
    [(0.0, 79, 1.0), (1.0, 76, 1.0), (2.0, 74, 1.0), (3.0, 76, 1.0)],
]


def _name(form, bar: int) -> str:
    return section_for_bar(form, bar).name


def _active(name: str) -> bool:
    return name not in {"intro", "breakdown", "outro"}


def chillstep_drums(events, bars, bpm, seed=15001, form=None, notes=None):
    h = Humanizer(seed, bpm)
    kick, snare, hat, open_hat, crash = 36, 38, 42, 46, 49
    for bar in range(bars):
        section = section_for_bar(form, bar)
        name = section.name
        base = bar * 4 * PPQ
        if name == "intro":
            if bar >= max(1, section.end - 2):
                for beat in (0.0, 2.0):
                    add_note(events, base + int(beat * PPQ), int(.10 * PPQ), hat, h.velocity(42, 3))
            continue
        if name == "outro":
            if bar == section.start:
                add_note(events, base, int(.25 * PPQ), crash, h.velocity(70, 3))
            add_note(events, base, int(.12 * PPQ), kick, h.velocity(72, 3))
            continue
        if name == "breakdown":
            # Sparse heartbeat and air; leave room for pad/lead.
            if bar % 2 == 0:
                add_note(events, base, int(.14 * PPQ), kick, h.velocity(64, 4))
            for beat in (1.5, 3.5):
                add_note(events, base + int(beat * PPQ), int(.09 * PPQ), hat, h.velocity(38, 4))
            continue

        # Half-time chillstep backbone: snare on beat 3.
        kick_pattern = (0.0, 1.75, 3.25) if "drop" in name else (0.0, 2.75)
        for beat in kick_pattern:
            start = base + int(beat * PPQ) + h.ticks(0, 1.2)
            add_note(events, start, int(.12 * PPQ), kick, h.velocity(94 if "drop" in name else 82, 4))
        add_note(events, base + 2 * PPQ + h.ticks(0, 1.0), int(.14 * PPQ), snare, h.velocity(102 if "drop" in name else 88, 4))

        # Smooth 1/8 hats, with restrained 1/16 lift near section endings.
        for step in range(8):
            beat = step * .5
            vel = 52 + (8 if step % 2 == 0 else 0)
            add_note(events, base + int(beat * PPQ) + h.ticks(0, 1.0), int(.07 * PPQ), hat, h.velocity(vel, 4))
        if "drop" in name and (bar - section.start) % 4 == 3:
            for beat in (3.0, 3.25, 3.5, 3.75):
                add_note(events, base + int(beat * PPQ), int(.055 * PPQ), hat, h.velocity(60, 4))
        if bar == section.start and name in {"drop", "final_drop"}:
            add_note(events, base, int(.35 * PPQ), crash, h.velocity(86, 3))
        elif name == "build" and bar == section.end - 1:
            add_note(events, base + int(3.5 * PPQ), int(.22 * PPQ), open_hat, h.velocity(68, 3))


def chillstep_sub(events, bars, bpm, seed=15002, form=None, notes=None):
    h = Humanizer(seed, bpm)
    for bar in range(bars):
        section = section_for_bar(form, bar)
        if section.name in {"intro", "outro"}:
            continue
        root = ROOTS[bar % 4]
        base = bar * 4 * PPQ
        if section.name == "breakdown":
            if bar % 2:
                continue
            add_note(events, base, h.duration(4 * PPQ, .01), root, h.velocity(62, 2))
        elif "drop" in section.name:
            # Two long pulses create breathing room while retaining low-end weight.
            add_note(events, base, h.duration(int(1.85 * PPQ), .012), root, h.velocity(94, 2))
            add_note(events, base + 2 * PPQ, h.duration(int(1.78 * PPQ), .012), root, h.velocity(88, 2))
        else:
            add_note(events, base, h.duration(int(3.8 * PPQ), .012), root, h.velocity(72, 2))


def chillstep_pad(events, bars, bpm, seed=15003, form=None, notes=None):
    h = Humanizer(seed, bpm)
    for bar in range(bars):
        section = section_for_bar(form, bar)
        chord = PAD_CHORDS[bar % 4]
        base = bar * 4 * PPQ
        velocity = 50 if section.name == "intro" else (72 if "drop" in section.name else 61)
        if section.name == "outro":
            velocity = 46
        for idx, note in enumerate(chord):
            # Tiny onset spread across voices prevents a block-chord MIDI stamp.
            start = base + h.ticks(idx * 1.5, .7)
            add_note(events, start, h.duration(int(3.92 * PPQ), .008), note, h.velocity(velocity - idx * 2, 2))


def chillstep_pluck(events, bars, bpm, seed=15004, form=None, notes=None):
    h = Humanizer(seed, bpm)
    for bar in range(bars):
        section = section_for_bar(form, bar)
        name = section.name
        if name in {"intro", "breakdown", "outro"}:
            continue
        tones = PLUCK_TONES[bar % 4]
        base = bar * 4 * PPQ
        step = .5 if "drop" in name else 1.0
        count = int(4 / step)
        for i in range(count):
            note = tones[(i + (bar % 2)) % len(tones)]
            if "drop" in name and i in {3, 7}:
                note += 12
            start = base + int(i * step * PPQ) + h.ticks(0, 1.3)
            dur = int((.34 if step == .5 else .52) * PPQ)
            add_note(events, start, h.duration(dur, .025), note, h.velocity(64 if "drop" in name else 52, 4))


def chillstep_lead(events, bars, bpm, seed=15005, form=None, notes=None):
    h = Humanizer(seed, bpm)
    for bar in range(bars):
        section = section_for_bar(form, bar)
        name = section.name
        if "drop" not in name and name != "breakdown":
            continue
        if name == "breakdown" and (bar - section.start) % 2:
            continue
        base = bar * 4 * PPQ
        pattern = LEAD_PATTERNS[bar % 4]
        for beat, note, dur_beats in pattern:
            velocity = 76 if "drop" in name else 58
            add_note(
                events,
                base + int(beat * PPQ) + h.ticks(0, 2.0),
                h.duration(int(dur_beats * .90 * PPQ), .02),
                note,
                h.velocity(velocity, 4),
            )
