from pathlib import Path
from .midi_tools import write_midi, make_tempo_map
from .genres import normalize_genre
from .song_form import make_form
from .drumgizmo import note_map
from .musicians import hq3, funk, hiphop, chillstep

def create_test_midis(work: Path, seconds=60, bpm=126, genre="sertanejo"):
    genre=normalize_genre(genre)
    bars=max(4, round(seconds / ((60/bpm)*4)))
    form=make_form(bars,genre)
    # Electronic chillstep should stay locked to the grid. Human feel is added
    # at note level, not by drifting the global tempo.
    tempo=[(0,bpm)] if genre=="chillstep" else make_tempo_map(bpm,bars,form=form)

    if genre=="chillstep":
        drums={}
        specs={
            "drums": chillstep.chillstep_drums,
            "sub": chillstep.chillstep_sub,
            "pad": chillstep.chillstep_pad,
            "pluck": chillstep.chillstep_pluck,
            "lead": chillstep.chillstep_lead,
        }
    elif genre=="hiphop":
        drums={}
        specs={
            "drums": hiphop.hiphop_drums,
            "sub": hiphop.hiphop_sub,
            "piano": hiphop.hiphop_piano,
            "brass": hiphop.hiphop_brass,
            "strings": hiphop.hiphop_strings,
        }
    elif genre=="funk":
        drums={}
        specs={
            "drums": funk.funk_drums,
            "sub": funk.funk_sub,
        }
    elif genre=="rock":
        drums=note_map(genre)
        specs={
            "drums": hq3.rock_drums,
            "bass": hq3.rock_bass,
            "guitar_l": hq3.rock_guitar_left,
            "guitar_r": hq3.rock_guitar_right,
        }
    else:
        drums=note_map(genre)
        specs={
            "drums": hq3.sertanejo_drums,
            "bass": hq3.sertanejo_bass,
            "guitar": hq3.sertanejo_guitar,
            "piano": hq3.sertanejo_piano,
            "accordion": hq3.sertanejo_accordion,
        }

    out={}
    for i,(name,fn) in enumerate(specs.items()):
        ev=[]
        fn(ev,bars,bpm,seed=11000+i*311,form=form,notes=drums)
        p=work/f"{name}.mid"
        write_midi(p,ev,bpm,bars,tempo_map=tempo)
        out[name]=p
    return out,bars,form
