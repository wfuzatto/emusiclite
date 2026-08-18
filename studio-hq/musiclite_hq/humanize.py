import random
from dataclasses import dataclass

PPQ = 960

def ms_to_ticks(ms: float, bpm: float, ppq: int = PPQ) -> int:
    return round((ms / 1000.0) * (bpm / 60.0) * ppq)

@dataclass
class Humanizer:
    seed: int
    bpm: float

    def __post_init__(self):
        self.rng = random.Random(self.seed)

    def ticks(self, center_ms=0.0, spread_ms=4.0):
        return ms_to_ticks(center_ms + self.rng.gauss(0.0, spread_ms), self.bpm)

    def velocity(self, base: int, spread: int = 5, lo: int = 1, hi: int = 127):
        return max(lo, min(hi, round(base + self.rng.gauss(0, spread))))

    def duration(self, base_ticks: int, spread_pct: float = 0.035):
        return max(1, round(base_ticks * (1.0 + self.rng.gauss(0, spread_pct))))
