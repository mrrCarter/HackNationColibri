"""Simulated phone call with the agent: microphone in, Swahili voice out, fully offline.

    python -m sauti.interfaces.noor_voice
    python -m sauti.interfaces.noor_voice --no-llm

The text of the conversation is also printed, as subtitles for the demo.
"""

from __future__ import annotations

import argparse
import sys

from sauti import config
from sauti.interfaces.session import load_extractor, run_setup_call, setup_logging


class VoiceChannel:
    def __init__(self) -> None:
        from sauti.models.asr import SwahiliASR
        from sauti.models.tts import SwahiliTTS

        self._asr = SwahiliASR(config.WHISPER_DIR)
        self._tts = SwahiliTTS(config.TTS_DIR)

    def say(self, text: str) -> None:
        from sauti.interfaces.audio_io import play

        print(f"\nSauti > {text}")
        play(self._tts.synthesize(text), self._tts.sample_rate)

    def listen(self, *, long: bool = False) -> str:
        from sauti.interfaces.audio_io import record_utterance

        print("        (inasikiliza...)", flush=True)
        if long:
            audio = record_utterance(start_timeout_s=10, end_silence_s=2.5, max_s=120)
        else:
            audio = record_utterance(start_timeout_s=8, end_silence_s=1.2, max_s=30)
        text = self._asr.transcribe(audio) if audio is not None else ""
        print(f"Noor  > {text or '(kimya)'}")
        return text


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Sauti Host, W1 farm setup (simulated voice call).")
    parser.add_argument("--no-llm", action="store_true", help="do not load Qwen, ask every field one by one")
    args = parser.parse_args(argv)

    config.force_offline()
    setup_logging()
    missing = [p for p in (config.WHISPER_DIR, config.TTS_DIR) if not p.exists()]
    if missing:
        sys.exit(f"Models missing: {', '.join(map(str, missing))}. Run scripts/download_models.sh first.")

    print("Loading local models (offline)...")
    channel = VoiceChannel()
    extractor = None if args.no_llm else load_extractor()
    print("\n=== Simu inaingia: Noor anampigia Sauti ===")
    run_setup_call(channel, extractor, source="w1_voice")
    print("=== Simu imekatika ===")


if __name__ == "__main__":
    main()
