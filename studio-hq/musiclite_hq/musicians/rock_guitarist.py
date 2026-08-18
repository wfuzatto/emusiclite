from ..humanize import Humanizer, PPQ
from ..midi_tools import add_note

ROOTS = [43, 50, 40, 48]  # G2 D3 E2 C3

def _perform(events, bars, bpm, seed, side):
    h = Humanizer(seed, bpm)
    beat = PPQ
    eighth = beat // 2
    side_offset = -3.0 if side == "left" else 4.0

    for bar in range(bars):
        base = bar * 4 * beat
        root = ROOTS[bar % 4]
        chord = [root, root + 7, root + 12]
        chorus = (bar // 8) % 2 == 1
        phrase = bar % 8

        if chorus:
            for b in (0.0, 1.0, 2.0, 3.0):
                t0 = base + round(b * beat) + h.ticks(center_ms=side_offset, spread_ms=2.0)
                spread = max(1, abs(h.ticks(center_ms=11.0, spread_ms=1.2)))
                for i, note in enumerate(chord):
                    add_note(events, t0 + i * spread,
                             h.duration(round(beat * .76) - i * spread, .035),
                             note, h.velocity(104 - i * 3, 3), 0)
        else:
            for i in range(8):
                t0 = base + i * eighth + h.ticks(center_ms=side_offset, spread_ms=2.2)
                spread = max(1, abs(h.ticks(center_ms=5.5, spread_ms=.8)))
                chord_notes = chord[:2] if i not in (0, 4) else chord
                for j, note in enumerate(chord_notes):
                    add_note(events, t0 + j * spread,
                             h.duration(round(eighth * .46) - j * spread, .04),
                             note, h.velocity(91 + (8 if i in (0,4) else 0) - j * 2, 3), 0)

        if phrase == 7:
            lick = [root + 12, root + 14, root + 15, root + 14]
            for i, note in enumerate(lick):
                t = base + round((3.0 + i * .22) * beat) + h.ticks(center_ms=side_offset, spread_ms=1.8)
                add_note(events, t, h.duration(round(beat * .16), .04),
                         note, h.velocity(87 + i * 2, 3), 0)

def perform_left(events, bars, bpm, seed=6303):
    _perform(events, bars, bpm, seed, "left")

def perform_right(events, bars, bpm, seed=6404):
    _perform(events, bars, bpm, seed, "right")
