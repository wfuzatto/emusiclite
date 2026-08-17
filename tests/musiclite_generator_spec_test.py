import unittest

from ops.generator.musiclite_generation_spec import build_ace_spec


class MusicLiteGeneratorSpecTest(unittest.TestCase):
    def test_maps_registered_instrumental_track(self):
        spec = build_ace_spec(
            {
                "prompt": "Energetic original electronic track",
                "lyrics": None,
                "instrumental": True,
                "duration_seconds": 60,
                "genre": "eletrohits",
                "mood": "elétrico",
                "language": "Português",
                "bpm": 140,
                "key": "D Minor",
                "instruments": ["sintetizador"],
            }
        )
        self.assertEqual("[Instrumental]", spec["lyrics"])
        self.assertEqual("pt", spec["vocal_language"])
        self.assertEqual(60.0, spec["duration"])
        self.assertEqual(140, spec["bpm"])
        self.assertIn("genre: eletrohits", spec["caption"])

    def test_rejects_vocal_without_lyrics(self):
        with self.assertRaisesRegex(ValueError, "letra"):
            build_ace_spec({"prompt": "original pop", "instrumental": False})

    def test_rejects_duration_above_server_limit(self):
        with self.assertRaisesRegex(ValueError, "duração"):
            build_ace_spec({"prompt": "original ambient", "instrumental": True, "duration_seconds": 181})

    def test_rejects_invalid_bpm(self):
        with self.assertRaisesRegex(ValueError, "BPM"):
            build_ace_spec({"prompt": "original ambient", "instrumental": True, "bpm": 500})


if __name__ == "__main__":
    unittest.main()

