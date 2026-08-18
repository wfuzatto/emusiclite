from ..humanize import Humanizer, PPQ
from ..midi_tools import add_note

KICK, SNARE, CHH, OHH, CRASH, RIDE, LTOM, MTOM, HTOM = 36, 38, 42, 46, 49, 51, 45, 47, 50

def perform(events, bars, bpm, seed=6101):
    h = Humanizer(seed, bpm)
    beat = PPQ
    eighth = beat // 2
    sixteenth = beat // 4

    for bar in range(bars):
        base = bar * 4 * beat
        phrase = bar % 8
        chorus = (bar // 8) % 2 == 1

        cymbal = RIDE if chorus else CHH
        for i in range(8):
            note = OHH if (not chorus and i == 7 and phrase in (3, 7)) else cymbal
            accent = 86 if i in (0, 4) else (76 if i % 2 == 0 else 69)
            t = base + i * eighth + h.ticks(center_ms=(-1.0 if i % 2 == 0 else 1.5), spread_ms=1.8)
            add_note(events, t, h.duration(round(eighth * 0.42), .04), note,
                     h.velocity(accent + (5 if chorus else 0), 3), 9)

        for b in (1, 3):
            t = base + b * beat + h.ticks(center_ms=5.5, spread_ms=2.2)
            add_note(events, t, h.duration(round(sixteenth * 0.9), .035),
                     SNARE, h.velocity(113 if chorus else 106, 3), 9)

        kick_beats = [0.0, 2.0]
        if chorus:
            kick_beats += [1.5, 2.75, 3.5]
        else:
            kick_beats += [0.75, 2.75]
        if phrase in (3, 7):
            kick_beats.append(3.25)
        for i, b in enumerate(kick_beats):
            t = base + round(b * beat) + h.ticks(center_ms=0.0, spread_ms=1.7)
            add_note(events, t, h.duration(round(sixteenth * .8), .035),
                     KICK, h.velocity(112 if i in (0, 1) else 101, 3), 9)

        if phrase == 0:
            add_note(events, base + h.ticks(0, 1.0), beat, CRASH,
                     h.velocity(116 if chorus else 108, 2), 9)

        if phrase == 7:
            fill = (HTOM, HTOM, MTOM, MTOM, LTOM, SNARE)
            start = base + round(2.5 * beat)
            for i, note in enumerate(fill):
                t = start + i * sixteenth + h.ticks(center_ms=0.0, spread_ms=1.8)
                add_note(events, t, h.duration(round(sixteenth * .72), .04),
                         note, h.velocity(88 + i * 5, 3), 9)
