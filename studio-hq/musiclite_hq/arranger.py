from pathlib import Path
from .midi_tools import write_midi
from .genres import normalize_genre
from .musicians import (
    drummer, bassist, guitarist, pianist, accordionist,
    rock_drummer, rock_bassist, rock_guitarist,
)

def create_test_midis(work: Path, seconds=60, bpm=126, genre="sertanejo"):
    genre = normalize_genre(genre)
    bars = max(4, round(seconds / ((60/bpm)*4)))

    if genre == "rock":
        specs = {
            "drums": rock_drummer.perform,
            "bass": rock_bassist.perform,
            "guitar_l": rock_guitarist.perform_left,
            "guitar_r": rock_guitarist.perform_right,
        }
    else:
        specs = {
            "drums": drummer.perform,
            "bass": bassist.perform,
            "guitar": guitarist.perform,
            "piano": pianist.perform,
            "accordion": accordionist.perform,
        }

    out = {}
    for i, (name, fn) in enumerate(specs.items()):
        ev = []
        fn(ev, bars, bpm, seed=10000 + i * 101)
        p = work / f"{name}.mid"
        write_midi(p, ev, bpm, bars)
        out[name] = p
    return out, bars
