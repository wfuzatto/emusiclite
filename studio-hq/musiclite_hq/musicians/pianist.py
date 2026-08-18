from ..humanize import Humanizer, PPQ
from ..midi_tools import add_note, add_cc

CHORDS = [
    [55,59,62,67],
    [54,57,62,66],
    [52,55,59,64],
    [52,55,60,64],
]

def perform(events, bars, bpm, seed=4004):
    h = Humanizer(seed, bpm)
    beat = PPQ
    add_cc(events, 0, 64, 0)
    for bar in range(bars):
        base = bar*4*beat
        chord = CHORDS[bar%4]
        # sparse supporting piano - keeps the sample library audible but not "MIDI piano".
        for b in (0,2):
            t0 = base+b*beat+h.ticks(center_ms=4, spread_ms=3.2)
            for i,n in enumerate(chord):
                add_note(events, t0+i*h.ticks(center_ms=5.0, spread_ms=.8),
                         h.duration(round(1.55*beat),.03), n+12, h.velocity(58+i*2,4), 0)
