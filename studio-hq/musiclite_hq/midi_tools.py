from dataclasses import dataclass
from typing import List, Optional
import random
import mido

PPQ = 960

@dataclass
class Ev:
    tick: int
    kind: str
    note: int = 0
    velocity: int = 0
    channel: int = 0
    value: int = 0
    control: int = 0

def add_note(events: List[Ev], start: int, dur: int, note: int, vel: int, channel: int = 0):
    start = max(0, int(start))
    dur = max(1, int(dur))
    events.append(Ev(start, "on", int(note), max(1,min(127,int(vel))), channel))
    events.append(Ev(start + dur, "off", int(note), 0, channel))

def add_cc(events: List[Ev], tick: int, cc: int, value: int, channel: int = 0):
    events.append(Ev(max(0, int(tick)), "cc", channel=channel,
                     value=max(0,min(127,int(value))), control=int(cc)))

def make_tempo_map(bpm: float, bars: int, form=None, seed: int = 7717, numerator: int = 4):
    rng = random.Random(seed)
    drift = 0.0
    result = [(0, bpm)]
    for bar in range(1, bars):
        # Correlated random-walk timing; not independent random BPM per bar.
        drift = max(-0.38, min(0.38, drift * .78 + rng.gauss(0, .075)))
        section_push = 0.0
        if form:
            for s in form:
                if s.start <= bar < s.end:
                    if "chorus" in s.name:
                        section_push = 0.16
                    elif "verse" in s.name:
                        section_push = -0.05
                    elif s.name == "outro":
                        section_push = -0.18
                    if bar == s.start:
                        section_push += 0.08
                    break
        result.append((bar * numerator * PPQ, bpm + drift + section_push))
    return result

def write_midi(path, events: List[Ev], bpm: float, bars: int, numerator=4, denominator=4,
               tempo_map: Optional[list] = None):
    mf = mido.MidiFile(type=1, ticks_per_beat=PPQ)
    tr = mido.MidiTrack()
    mf.tracks.append(tr)
    tr.append(mido.MetaMessage("track_name", name="MusicLite HQ 0.3", time=0))
    tr.append(mido.MetaMessage("time_signature", numerator=numerator, denominator=denominator, time=0))

    if tempo_map is None:
        tempo_map = [(0, bpm)]

    merged = []
    for tick, value in tempo_map:
        merged.append((int(tick), 0, mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(value), time=0)))

    for e in events:
        if e.kind == "on":
            msg = mido.Message("note_on", note=e.note, velocity=e.velocity, channel=e.channel, time=0)
        elif e.kind == "off":
            msg = mido.Message("note_off", note=e.note, velocity=0, channel=e.channel, time=0)
        else:
            msg = mido.Message("control_change", control=e.control, value=e.value, channel=e.channel, time=0)
        merged.append((e.tick, 2 if e.kind == "off" else 1, msg))

    merged.sort(key=lambda x: (x[0], x[1]))
    last = 0
    for tick, _, msg in merged:
        msg.time = max(0, tick - last)
        tr.append(msg)
        last = tick

    end_tick = bars * numerator * PPQ
    tr.append(mido.MetaMessage("end_of_track", time=max(1, end_tick - last)))
    mf.save(path)
