"""Text version of Noor's call: the agent writes, Noor types. Same conversation as by voice.

    python -m sauti.interfaces.noor_cli            # with Qwen extraction
    python -m sauti.interfaces.noor_cli --no-llm   # code only, asks every field
"""

from __future__ import annotations

import argparse

from sauti import config
from sauti.interfaces.session import load_extractor, run_setup_call, setup_logging


class TextChannel:
    def say(self, text: str) -> None:
        print(f"\nSauti > {text}")

    def listen(self, *, long: bool = False) -> str:
        try:
            return input("Noor  > ")
        except EOFError:
            return ""


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Sauti Host, W1 farm setup (text call).")
    parser.add_argument("--no-llm", action="store_true", help="do not load Qwen, ask every field one by one")
    args = parser.parse_args(argv)

    config.force_offline()
    setup_logging()
    extractor = None if args.no_llm else load_extractor()
    run_setup_call(TextChannel(), extractor, source="w1_text")


if __name__ == "__main__":
    main()
