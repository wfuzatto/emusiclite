from ..humanize import Humanizer, PPQ
from ..midi_tools import add_note

CHORDS = [
    [55,59,62],  # G
    [54,57,62],  # D
    [52,55,59],  # Em
    [52,55,60],  # C
]

def perform(events, bars, bpm, seed=5005):
    h = Humanizer(seed, bpm)
    beat = PPQ
    # Deliberately sparse: human accordionists breathe and leave space.
    for bar in range(bars):
        base = bar*4*beat
        chord = CHORDS[bar%4]
        # soft held support on selected bars
        if bar % 4 in (1,3):
            t = base + h.ticks(center_ms=12, spread_ms=4)
            for i,n in enumerate(chord):
                add_note(events, t+i*h.ticks(center_ms=5, spread_ms=1),
                         h.duration(round(1.55*beat), .04), n+12,
                         h.velocity(55+i*2,4), 0)
        # phrase-end answer lick; monophonic, not a robotic full-time melody
        if bar % 8 == 7:
            notes = [67,69,71,74,71,69,67]
            pos   = [2.00,2.35,2.70,3.00,3.25,3.52,3.78]
            for i,(n,b) in enumerate(zip(notes,pos)):
                t=base+round(b*beat)+h.ticks(center_ms=6,spread_ms=2.5)
                add_note(events,t,h.duration(round(.22*beat),.06),n,
                         h.velocity(72+(5 if i in (0,3) else 0),4),0)
