from ..humanize import Humanizer, PPQ
from ..midi_tools import add_note

ROOTS = [43, 38, 40, 36]  # G2 D2 E2 C2

def perform(events, bars, bpm, seed=6202):
    h = Humanizer(seed, bpm)
    beat = PPQ
    eighth = beat // 2

    for bar in range(bars):
        base = bar * 4 * beat
        root = ROOTS[bar % 4]
        chorus = (bar // 8) % 2 == 1

        for i in range(8):
            note = root
            if chorus and i in (3, 7):
                note = root + 7
            if i == 7 and bar % 4 == 3:
                note = ROOTS[(bar + 1) % 4] + 2

            t = base + i * eighth + h.ticks(center_ms=4.0, spread_ms=2.1)
            dur = round(eighth * (0.74 if chorus else 0.62))
            vel = 98 + (8 if i in (0, 4) else 0) + (4 if chorus else 0)
            add_note(events, t, h.duration(dur, .035), note, h.velocity(vel, 3), 0)
