from ..humanize import Humanizer, PPQ
from ..midi_tools import add_note

# General MIDI notes used by the GM preset of Naked Drums.
KICK, SNARE, SIDE, CHH, PHH, OHH, CRASH, RIDE, LTOM, MTOM, HTOM = 36, 38, 37, 42, 44, 46, 49, 51, 45, 47, 50

def perform(events, bars, bpm, seed=1001):
    h = Humanizer(seed, bpm)
    beat = PPQ
    eighth = PPQ//2
    sixteenth = PPQ//4
    for bar in range(bars):
        base = bar*4*beat
        section_pos = bar % 8
        # Hats: alternating hand/strength. Avoid identical machine-gun velocities.
        for i in range(8):
            t = base + i*eighth + h.ticks(center_ms=1 if i%2 else -1, spread_ms=2.2)
            accent = 78 if i in (0,4) else (66 if i%2==0 else 58)
            note = OHH if (section_pos == 7 and i == 7) else CHH
            add_note(events, t, h.duration(sixteenth, .05), note, h.velocity(accent, 4), 9)
        # Backbeat has a slightly late, human pocket.
        for b in (1,3):
            t = base + b*beat + h.ticks(center_ms=7.0, spread_ms=2.8)
            add_note(events, t, h.duration(sixteenth, .04), SNARE, h.velocity(104 if b==1 else 108,4), 9)
            # tasteful ghost before some backbeats
            if (bar+b)%3 == 0:
                gt = t - sixteenth + h.ticks(center_ms=-3, spread_ms=2)
                add_note(events, gt, h.duration(sixteenth//2,.08), SNARE, h.velocity(37,4), 9)
        # Sertanejo/pop pocket: kick on 1, plus syncopation.
        kick_positions = [0, 2*eighth, 4*eighth, 5*eighth]
        if section_pos in (3,7):
            kick_positions += [7*eighth]
        for j, pos in enumerate(kick_positions):
            t = base + pos + h.ticks(center_ms=1.5, spread_ms=2.0)
            add_note(events, t, h.duration(sixteenth,.04), KICK, h.velocity(108 if j in (0,2) else 94,4), 9)
        if section_pos == 0:
            add_note(events, base+h.ticks(0,1), beat, CRASH, h.velocity(104,3), 9)
        # Short tom fill only at phrase boundaries.
        if section_pos == 7:
            for k, note in enumerate((HTOM, MTOM, LTOM, SNARE)):
                t = base + 3*beat + k*sixteenth + h.ticks(0,2.2)
                add_note(events, t, h.duration(sixteenth*.75,.05), note, h.velocity(84+k*6,4), 9)
