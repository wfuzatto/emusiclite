"""Lightweight objective audio ranking for MusicLite Neural Studio.

This is deliberately not called an "AI realism detector". It ranks generated
takes using measurable engineering properties plus structural correlation to
the HQ3 reference. All candidates remain available to the user.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf


def _mono(path: Path) -> tuple[np.ndarray, int]:
    audio, sr = sf.read(str(path), always_2d=True, dtype="float32")
    if audio.size == 0:
        raise ValueError(f"Áudio vazio: {path}")
    mono = np.mean(audio, axis=1, dtype=np.float32)
    mono = np.nan_to_num(mono, nan=0.0, posinf=0.0, neginf=0.0)
    return mono, int(sr)


def _frame_rms(x: np.ndarray, sr: int, frame_seconds: float = 0.20) -> np.ndarray:
    size = max(256, int(sr * frame_seconds))
    n = len(x) // size
    if n < 1:
        return np.array([float(np.sqrt(np.mean(x * x) + 1e-12))], dtype=np.float32)
    y = x[: n * size].reshape(n, size)
    return np.sqrt(np.mean(y * y, axis=1) + 1e-12)


def _resample_vector(values: np.ndarray, n: int = 256) -> np.ndarray:
    if len(values) == n:
        return values.astype(np.float64)
    if len(values) <= 1:
        return np.full(n, float(values[0]) if len(values) else 0.0, dtype=np.float64)
    xp = np.linspace(0.0, 1.0, len(values))
    xq = np.linspace(0.0, 1.0, n)
    return np.interp(xq, xp, values).astype(np.float64)


def _envelope_correlation(candidate: np.ndarray, csr: int, reference: np.ndarray, rsr: int) -> float:
    a = np.log10(_frame_rms(candidate, csr) + 1e-5)
    b = np.log10(_frame_rms(reference, rsr) + 1e-5)
    a = _resample_vector(a)
    b = _resample_vector(b)
    if np.std(a) < 1e-7 or np.std(b) < 1e-7:
        return 0.0
    corr = float(np.corrcoef(a, b)[0, 1])
    if not math.isfinite(corr):
        return 0.0
    return max(-1.0, min(1.0, corr))


def _spectral_stats(x: np.ndarray, sr: int) -> tuple[float, float]:
    win = min(8192, max(2048, 1 << int(math.log2(max(2048, sr // 6)))))
    if len(x) < win:
        padded = np.pad(x, (0, win - len(x)))
        chunks = [padded]
    else:
        count = min(24, max(1, len(x) // (sr * 2)))
        starts = np.linspace(0, len(x) - win, count).astype(int)
        chunks = [x[s : s + win] for s in starts]
    freqs = np.fft.rfftfreq(win, d=1.0 / sr)
    centroids = []
    flatnesses = []
    window = np.hanning(win)
    for chunk in chunks:
        mag = np.abs(np.fft.rfft(chunk * window)) + 1e-9
        centroids.append(float(np.sum(freqs * mag) / np.sum(mag)))
        flatnesses.append(float(np.exp(np.mean(np.log(mag))) / np.mean(mag)))
    return float(np.mean(centroids)), float(np.mean(flatnesses))


def analyze_audio(path: str | Path, reference: str | Path | None = None) -> dict[str, Any]:
    path = Path(path)
    x, sr = _mono(path)
    peak = float(np.max(np.abs(x)))
    rms = float(np.sqrt(np.mean(x * x) + 1e-12))
    rms_db = 20.0 * math.log10(max(rms, 1e-9))
    crest_db = 20.0 * math.log10(max(peak, 1e-9) / max(rms, 1e-9))
    clipping_ratio = float(np.mean(np.abs(x) >= 0.999))
    frames = _frame_rms(x, sr)
    silence_ratio = float(np.mean(frames < 0.004))
    fdb = 20.0 * np.log10(frames + 1e-9)
    dynamic_spread_db = float(np.percentile(fdb, 90) - np.percentile(fdb, 10))
    centroid_hz, flatness = _spectral_stats(x, sr)

    corr = None
    if reference:
        r, rsr = _mono(Path(reference))
        corr = _envelope_correlation(x, sr, r, rsr)

    score = 100.0
    score -= min(38.0, clipping_ratio * 150000.0)
    if peak < 0.35:
        score -= min(15.0, (0.35 - peak) * 35.0)
    if rms_db < -30:
        score -= min(15.0, (-30.0 - rms_db) * 0.8)
    if rms_db > -7:
        score -= min(18.0, (rms_db + 7.0) * 2.5)
    score -= min(25.0, silence_ratio * 45.0)
    if crest_db < 5.5:
        score -= (5.5 - crest_db) * 3.0
    elif crest_db > 20:
        score -= min(8.0, (crest_db - 20.0) * 0.7)
    if dynamic_spread_db < 5:
        score -= (5.0 - dynamic_spread_db) * 2.2
    if not 550 <= centroid_hz <= 6200:
        score -= 6.0
    if flatness > 0.32:
        score -= min(8.0, (flatness - 0.32) * 25.0)
    if corr is not None:
        score += 12.0 * max(-0.3, corr)

    return {
        "path": str(path),
        "sample_rate": sr,
        "duration_seconds": round(len(x) / sr, 3),
        "peak": round(peak, 6),
        "rms_db": round(rms_db, 3),
        "crest_db": round(crest_db, 3),
        "clipping_ratio": round(clipping_ratio, 8),
        "silence_ratio": round(silence_ratio, 5),
        "dynamic_spread_db": round(dynamic_spread_db, 3),
        "spectral_centroid_hz": round(centroid_hz, 2),
        "spectral_flatness": round(flatness, 5),
        "reference_envelope_correlation": None if corr is None else round(corr, 5),
        "technical_rank_score": round(max(0.0, min(100.0, score)), 3),
    }


def rank_candidates(paths: list[str | Path], reference: str | Path | None = None) -> list[dict[str, Any]]:
    scored = [analyze_audio(path, reference=reference) for path in paths]
    scored.sort(key=lambda row: row["technical_rank_score"], reverse=True)
    for index, row in enumerate(scored, start=1):
        row["rank"] = index
    return scored
