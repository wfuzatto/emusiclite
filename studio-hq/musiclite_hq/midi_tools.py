from dataclasses import dataclass
from typing import List
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
    events.append(Ev(start, "on", note, vel, channel))
    events.append(Ev(start + dur, "off", note, 0, channel))

def add_cc(events: List[Ev], tick: int, cc: int, value: int, channel: int = 0):
    events.append(Ev(max(0, int(tick)), "cc", channel=channel, value=max(0,min(127,value)), control=cc))

def write_midi(path, events: List[Ev], bpm: float, bars: int, numerator=4, denominator=4):
    mf = mido.MidiFile(type=1, ticks_per_beat=PPQ)
    tr = mido.MidiTrack()
    mf.tracks.append(tr)
    tr.append(mido.MetaMessage("track_name", name="MusicLite HQ", time=0))
    tr.append(mido.MetaMessage("time_signature", numerator=numerator, denominator=denominator, time=0))
    tr.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(bpm), time=0))

    # Gentle global tempo drift. Musicians remain locked together because every stem gets the same map.
    tempo_events = []
    for bar in range(1, bars):
        phase = (bar % 8) / 8.0
        drift = (phase - 0.5) * 0.26
        tempo_events.append((bar * numerator * PPQ, mido.MetaMessage(
            "set_tempo", tempo=mido.bpm2tempo(bpm + drift), time=0)))

    merged = []
    for e in events:
        if e.kind == "on":
            msg = mido.Message("note_on", note=e.note, velocity=e.velocity, channel=e.channel, time=0)
        elif e.kind == "off":
            msg = mido.Message("note_off", note=e.note, velocity=0, channel=e.channel, time=0)
        else:
            msg = mido.Message("control_change", control=e.control, value=e.value, channel=e.channel, time=0)
        merged.append((e.tick, 2 if e.kind == "off" else 1, msg))
    for t, msg in tempo_events:
        merged.append((t, 0, msg))
    merged.sort(key=lambda x:(x[0], x[1]))

    last = 0
    for tick, _, msg in merged:
        msg.time = max(0, tick-last)
        tr.append(msg)
        last = tick
    end_tick = bars * numerator * PPQ
    tr.append(mido.MetaMessage("end_of_track", time=max(1, end_tick-last)))
    mf.save(path)
