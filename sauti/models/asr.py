"""Speech to text: Whisper small (faster-whisper, CTranslate2 int8), Swahili, offline."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np

SAMPLE_RATE = 16_000
# Vocabulary only, no numbers: a prompt with numbers could leak into the transcript.
_VOCABULARY = "Shamba la kahawa, ziara, wageni, bei, shilingi, maelekezo, Jumatatu, asubuhi, jioni."


class SwahiliASR:
    def __init__(self, model_dir: Path) -> None:
        from faster_whisper import WhisperModel

        self._model = WhisperModel(str(model_dir), device="cpu", compute_type="int8", cpu_threads=os.cpu_count() or 4)

    def transcribe(self, audio: np.ndarray) -> str:
        """audio: mono float32 at 16 kHz. Returns '' when no confident speech."""
        segments, _ = self._model.transcribe(
            audio.astype(np.float32),
            language="sw",
            beam_size=5,
            vad_filter=True,
            condition_on_previous_text=False,
            initial_prompt=_VOCABULARY,
        )
        # Drop segments Whisper itself doubts: hallucinated text on noise is worse than silence.
        texts = [s.text.strip() for s in segments if s.no_speech_prob < 0.6 and s.avg_logprob > -1.0]
        return " ".join(t for t in texts if t)
