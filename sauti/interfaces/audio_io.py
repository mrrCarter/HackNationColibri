"""Microphone and speaker for the simulated call (laptop or phone, offline)."""

from __future__ import annotations

import collections
import queue

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16_000
_FRAME = 480  # 30 ms
_MIN_THRESHOLD = 0.008


def _rms(block: np.ndarray) -> float:
    return float(np.sqrt(np.mean(block * block)))


def play(wave: np.ndarray, sample_rate: int) -> None:
    sd.play(wave, sample_rate)
    sd.wait()


def record_utterance(start_timeout_s: float, end_silence_s: float, max_s: float) -> np.ndarray | None:
    """Record from the first sound until `end_silence_s` of silence. None if nobody spoke."""
    blocks: queue.Queue[np.ndarray] = queue.Queue()

    def on_audio(indata: np.ndarray, frames: int, t: object, status: object) -> None:
        blocks.put(indata[:, 0].copy())

    pre_roll: collections.deque[np.ndarray] = collections.deque(maxlen=10)
    recorded: list[np.ndarray] = []
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", blocksize=_FRAME, callback=on_audio):
        noise = [_rms(blocks.get()) for _ in range(10)]  # 0.3 s of room noise
        threshold = max(float(np.median(noise)) * 3, _MIN_THRESHOLD)
        waited = spoken = silence = 0.0
        started = False
        while True:
            block = blocks.get()
            duration = len(block) / SAMPLE_RATE
            loud = _rms(block) > threshold
            if not started:
                pre_roll.append(block)
                waited += duration
                if loud:
                    started = True
                    recorded.extend(pre_roll)
                elif waited >= start_timeout_s:
                    return None
                continue
            recorded.append(block)
            spoken += duration
            silence = 0.0 if loud else silence + duration
            if silence >= end_silence_s or spoken >= max_s:
                break
    return np.concatenate(recorded)
