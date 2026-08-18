from pathlib import Path
import subprocess
import shutil
from .genres import normalize_genre

def _run(cmd):
    subprocess.run(cmd, check=True)

def _ffmpeg_prepare(src: Path, dst: Path, filters: str):
    _run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-af", filters, str(dst)])

def prepare_stem(src: Path, dst: Path, kind: str, genre: str):
    genre = normalize_genre(genre)

    if genre == "rock" and kind in ("guitar_l", "guitar_r"):
        amp = dst.with_name(dst.stem + "_amp.wav")
        if shutil.which("sox"):
            _run([
                "sox", str(src), str(amp),
                "gain", "-7",
                "highpass", "75",
                "overdrive", "18", "18",
                "lowpass", "9200",
            ])
            source = amp
        else:
            source = src

        pan = (
            "pan=stereo|c0=0.98*c0|c1=0.22*c1"
            if kind == "guitar_l"
            else "pan=stereo|c0=0.22*c0|c1=0.98*c1"
        )
        filters = (
            "highpass=f=82,lowpass=f=9800,"
            "equalizer=f=240:t=q:w=0.8:g=-2.0,"
            "equalizer=f=3200:t=q:w=0.9:g=1.4,"
            "equalizer=f=7200:t=q:w=1.1:g=-1.7,"
            "acompressor=threshold=0.20:ratio=2.1:attack=8:release=95:makeup=1.08,"
            + pan
        )
        _ffmpeg_prepare(source, dst, filters)
        if amp.exists():
            amp.unlink()
        return

    base_filters = {
        "drums": (
            "highpass=f=28,lowpass=f=19000,equalizer=f=260:t=q:w=0.8:g=-1.2,"
            "acompressor=threshold=0.18:ratio=1.55:attack=18:release=160:makeup=1.1"
        ),
        "bass": (
            "highpass=f=32,lowpass=f=9000,equalizer=f=220:t=q:w=1.0:g=-1.5,"
            "acompressor=threshold=0.16:ratio=2.0:attack=22:release=180:makeup=1.15"
        ),
        "guitar": (
            "highpass=f=72,lowpass=f=15500,equalizer=f=270:t=q:w=0.8:g=-1.0,"
            "equalizer=f=3600:t=q:w=1:g=-0.8,"
            "acompressor=threshold=0.23:ratio=1.35:attack=18:release=140:makeup=1.04"
        ),
        "piano": (
            "highpass=f=45,lowpass=f=17500,equalizer=f=250:t=q:w=0.9:g=-0.8,"
            "acompressor=threshold=0.24:ratio=1.35:attack=25:release=190:makeup=1.03"
        ),
        "accordion": (
            "highpass=f=95,lowpass=f=14500,equalizer=f=1800:t=q:w=1.0:g=-0.8,"
            "acompressor=threshold=0.24:ratio=1.30:attack=20:release=170:makeup=1.03"
        ),
    }

    filters = base_filters[kind]
    if genre == "rock" and kind == "drums":
        filters = (
            "highpass=f=28,lowpass=f=19000,equalizer=f=230:t=q:w=0.8:g=-1.0,"
            "equalizer=f=4200:t=q:w=1.0:g=1.0,"
            "acompressor=threshold=0.16:ratio=1.8:attack=12:release=125:makeup=1.12"
        )
    elif genre == "rock" and kind == "bass":
        filters = (
            "highpass=f=34,lowpass=f=7500,equalizer=f=150:t=q:w=0.8:g=1.0,"
            "equalizer=f=850:t=q:w=1.0:g=0.8,"
            "acompressor=threshold=0.14:ratio=2.4:attack=18:release=145:makeup=1.15"
        )

    _ffmpeg_prepare(src, dst, filters)

def _make_mix(prepared, order, volumes, dst):
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for name in order:
        cmd += ["-i", str(prepared[name])]

    parts = []
    labels = []
    for i, name in enumerate(order):
        label = f"s{i}"
        parts.append(f"[{i}:a]volume={volumes.get(name, 0.8)}[{label}]")
        labels.append(f"[{label}]")
    parts.append(
        "".join(labels) +
        f"amix=inputs={len(order)}:normalize=0,alimiter=limit=0.90[mix]"
    )
    _run(cmd + ["-filter_complex", ";".join(parts), "-map", "[mix]", str(dst)])

def _make_room(prepared, names, dst, genre):
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for name in names:
        cmd += ["-i", str(prepared[name])]

    labels = []
    parts = []
    for i, name in enumerate(names):
        amount = 0.30
        if "guitar" in name:
            amount = 0.44 if genre == "sertanejo" else 0.34
        elif name == "piano":
            amount = 0.25
        elif name == "accordion":
            amount = 0.34
        label = f"r{i}"
        parts.append(f"[{i}:a]volume={amount}[{label}]")
        labels.append(f"[{label}]")
    parts.append("".join(labels) + f"amix=inputs={len(names)}:normalize=0[roomsrc]")
    room_src = dst.with_name(dst.stem + "_src.wav")
    _run(cmd + ["-filter_complex", ";".join(parts), "-map", "[roomsrc]", str(room_src)])

    if shutil.which("sox"):
        if genre == "rock":
            reverb = ["12", "46", "48", "78", "0", "0"]
        else:
            reverb = ["16", "47", "54", "84", "0", "0"]
        _run(["sox", str(room_src), str(dst), "reverb", *reverb])
    else:
        _run([
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(room_src),
            "-af", "aecho=0.7:0.38:31|47|71:0.16|0.11|0.07", str(dst)
        ])
    room_src.unlink(missing_ok=True)

def mix_master(stems, out: Path, work: Path, genre="sertanejo"):
    genre = normalize_genre(genre)
    order = tuple(stems.keys())
    prepared = {}

    for kind in order:
        dst = work / f"{kind}_prep.wav"
        prepare_stem(stems[kind], dst, kind, genre)
        prepared[kind] = dst

    if genre == "rock":
        volumes = {
            "drums": 0.94,
            "bass": 0.88,
            "guitar_l": 0.70,
            "guitar_r": 0.70,
        }
        room_names = [n for n in ("drums", "guitar_l", "guitar_r") if n in prepared]
        room_amount = 0.12
        target_lufs = "-13"
        lra = "9"
    else:
        volumes = {
            "drums": 0.88,
            "bass": 0.86,
            "guitar": 0.82,
            "piano": 0.48,
            "accordion": 0.56,
        }
        room_names = [n for n in ("drums", "guitar", "piano", "accordion") if n in prepared]
        room_amount = 0.16
        target_lufs = "-14"
        lra = "10"

    dry = work / "dry_mix.wav"
    _make_mix(prepared, order, volumes, dry)

    room = work / "room.wav"
    _make_room(prepared, room_names, room, genre)

    premaster = work / "premaster.wav"
    _run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(dry), "-i", str(room),
        "-filter_complex",
        f"[1:a]volume={room_amount}[r];[0:a][r]amix=inputs=2:normalize=0,alimiter=limit=.92[m]",
        "-map", "[m]", str(premaster)
    ])

    _run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(premaster),
        "-af",
        f"highpass=f=24,acompressor=threshold=.30:ratio=1.22:attack=32:release=230,"
        f"loudnorm=I={target_lufs}:TP=-1.0:LRA={lra}",
        "-ar", "48000", "-c:a", "pcm_s24le", str(out)
    ])
    return out
