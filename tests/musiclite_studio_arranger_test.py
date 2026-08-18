import sys
import tempfile
import unittest
from pathlib import Path

import mido

ROOT = Path(__file__).resolve().parents[1]
STUDIO = ROOT / "ops" / "studio"
if str(STUDIO) not in sys.path:
    sys.path.insert(0, str(STUDIO))

from musiclite_arranger import arrange


class StudioArrangerTest(unittest.TestCase):
    def test_sertanejo_builds_real_instrument_stems(self):
        payload = {
            "genre": "Sertanejo",
            "subgenre": "Sertanejo universitário brasileiro",
            "bpm": 126,
            "key": "G Major",
            "duration_seconds": 60,
            "structure": [
                {"name": "intro", "start_seconds": 0, "end_seconds": 8},
                {"name": "verso", "start_seconds": 8, "end_seconds": 28},
                {"name": "refrão", "start_seconds": 28, "end_seconds": 48},
                {"name": "final", "start_seconds": 48, "end_seconds": 60},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            result = arrange(payload, Path(tmp), STUDIO / "grooves.json")
            names = {stem["name"] for stem in result["stems"]}
            self.assertIn("steel_guitar", names)
            self.assertIn("electric_bass", names)
            self.assertIn("acoustic_drums", names)
            self.assertIn("accordion", names)
            self.assertGreaterEqual(result["bars"], 20)
            for stem in result["stems"]:
                path = Path(stem["midi_path"])
                self.assertTrue(path.is_file())
                midi = mido.MidiFile(path)
                note_ons = [
                    message
                    for track in midi.tracks
                    for message in track
                    if message.type == "note_on" and message.velocity > 0
                ]
                self.assertGreater(len(note_ons), 0)


if __name__ == "__main__":
    unittest.main()
