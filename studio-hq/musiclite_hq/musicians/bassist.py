from ..humanize import Humanizer, PPQ
from ..midi_tools import add_note

# chord roots for a pop/sertanejo I-V-vi-IV test in G
ROOTS = [43, 38, 40, 36]  # G2 D2 E2 C2

def perform(events, bars, bpm, seed=2002):
    h = Humanizer(seed, bpm)
    beat = PPQ
    for bar in range(bars):
        root = ROOTS[bar % 4]
        base = bar*4*beat
        # Finger-bass line follows kick but sits a few ms behind it.
        seq = [
            (0.00, root,   .86, 96),
            (1.00, root+7, .72, 82),
            (2.00, root,   .82, 92),
            (2.75, root+12,.42, 72),
            (3.50, root+7, .38, 76),
        ]
        # Lead into next chord with a diatonic-ish approach tone.
        nxt = ROOTS[(bar+1)%4]
        approach = nxt-1 if nxt > root else nxt+2
        seq.append((3.82, approach, .16, 64))
        for idx,(b,n,d,v) in enumerate(seq):
            t = base + round(b*beat) + h.ticks(center_ms=7.5, spread_ms=3.0)
            dur = h.duration(round(d*beat), .045)
            # Alternating fingers expressed as tiny timbral/velocity difference.
            vel = h.velocity(v + (2 if idx%2==0 else -2), 3)
            add_note(events, t, dur, n, vel, 0)
