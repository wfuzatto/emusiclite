from ..humanize import Humanizer, PPQ
from ..midi_tools import add_note

# Playable mid-register voicings, intentionally not piano-style block chords.
VOICINGS = [
    [55,59,62,67],  # G
    [54,57,62,66],  # D/F#
    [52,55,59,64],  # Em
    [52,55,60,64],  # C/E
]

def _strum(events, notes, tick, dur, vel, down, h):
    spread_ms = h.rng.uniform(16, 34)
    total_ticks = max(3, h.ticks(center_ms=spread_ms, spread_ms=2.0))
    order = notes if down else list(reversed(notes))
    step = max(1, total_ticks//max(1,len(order)-1))
    for i,n in enumerate(order):
        # Upper/lower strings do not all receive exactly the same velocity.
        vv = h.velocity(vel - i*2 + (3 if down else 0), 3)
        add_note(events, tick+i*step, h.duration(dur-i*step,.035), n, vv, 0)

def perform(events, bars, bpm, seed=3003):
    h = Humanizer(seed, bpm)
    beat = PPQ
    eighth = beat//2
    for bar in range(bars):
        chord = VOICINGS[bar%4]
        base = bar*4*beat
        # Brazilian pop/sertanejo strum: down/up motion with deliberate gaps.
        pattern = [
            (0.00, True,  88, .43),
            (0.50, False, 60, .28),
            (1.00, True,  78, .42),
            (1.50, False, 64, .27),
            (2.00, True,  91, .43),
            (2.75, False, 62, .22),
            (3.00, True,  79, .40),
            (3.50, False, 66, .26),
        ]
        for b,down,v,d in pattern:
            t = base + round(b*beat) + h.ticks(center_ms=(-2 if down else 4), spread_ms=3.0)
            _strum(events, chord, t, round(d*beat), v, down, h)
