"""Text to speech: MMS-TTS Swahili (VITS), offline.

The model reads letters only, so every number must already be written in words
(see sauti.lang.swahili.number_to_words).
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np


class SwahiliTTS:
    def __init__(self, model_dir: Path) -> None:
        import torch
        from transformers import AutoTokenizer, VitsModel

        self._torch = torch
        self._model = VitsModel.from_pretrained(model_dir)
        self._tokenizer = AutoTokenizer.from_pretrained(model_dir)
        self.sample_rate: int = self._model.config.sampling_rate

    def synthesize(self, text: str) -> np.ndarray:
        pause = np.zeros(int(0.25 * self.sample_rate), dtype=np.float32)
        pieces: list[np.ndarray] = []
        for sentence in re.split(r"(?<=[.?!:])\s+", text.strip()):
            inputs = self._tokenizer(sentence.lower(), return_tensors="pt")
            if inputs["input_ids"].shape[-1] == 0:
                continue
            self._torch.manual_seed(0)  # same voice every time
            with self._torch.no_grad():
                wave = self._model(**inputs).waveform[0].numpy().astype(np.float32)
            pieces.extend([wave, pause])
        return np.concatenate(pieces) if pieces else pause
