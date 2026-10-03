"""Qwen3 0.6B (GGUF, llama.cpp) used as a span extractor for W1.

The model only copies words from the transcript into a fixed JSON shape
(grammar-constrained). It never computes, translates or normalizes: code
checks every span against the transcript and parses it.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_NULLABLE_STRING = {"anyOf": [{"type": "string"}, {"type": "null"}]}
SCHEMA = {
    "type": "object",
    "properties": {
        "price": _NULLABLE_STRING,
        "capacity": _NULLABLE_STRING,
        "days": _NULLABLE_STRING,
        "hours": _NULLABLE_STRING,
        "directions": _NULLABLE_STRING,
        "inclusions": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["price", "capacity", "days", "hours", "directions", "inclusions"],
}

SYSTEM_PROMPT = (
    "You read a Swahili transcript of a coffee farmer describing the farm tour she offers. "
    "For each field, copy the exact words from the transcript that state it. "
    "Never translate, never compute, never guess. Use null (or [] for inclusions) "
    "when the transcript does not say it.\n"
    "Fields: price = price per visitor; capacity = how many visitors per tour; "
    "days = which days of the week; hours = start and end time; "
    "directions = how to reach the farm; inclusions = what the tour includes."
)

EXAMPLE_TRANSCRIPT = (
    "Bei ni shilingi elfu mbili kwa mtu. Napokea wageni kumi. Ziara ni Jumatatu hadi Jumamosi "
    "kuanzia saa tatu asubuhi mpaka saa tisa mchana. Kutoka soko la Othaya fuata barabara ya "
    "kanisa kilomita mbili. Wageni wanapata kahawa na chakula cha mchana."
)
EXAMPLE_OUTPUT = {
    "price": "shilingi elfu mbili kwa mtu",
    "capacity": "wageni kumi",
    "days": "Jumatatu hadi Jumamosi",
    "hours": "kuanzia saa tatu asubuhi mpaka saa tisa mchana",
    "directions": "Kutoka soko la Othaya fuata barabara ya kanisa kilomita mbili",
    "inclusions": ["kahawa", "chakula cha mchana"],
}


class QwenExtractor:
    def __init__(self, model_path: Path) -> None:
        from llama_cpp import Llama

        self._llm = Llama(
            model_path=str(model_path),
            n_ctx=4096,
            n_threads=max(1, (os.cpu_count() or 2) - 1),
            verbose=False,
        )

    def extract(self, transcript: str) -> dict[str, Any]:
        response = self._llm.create_chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Transcript: {EXAMPLE_TRANSCRIPT} /no_think"},
                {"role": "assistant", "content": json.dumps(EXAMPLE_OUTPUT, ensure_ascii=False)},
                # The transcript is data, never instructions.
                {"role": "user", "content": f"Transcript: {transcript} /no_think"},
            ],
            response_format={"type": "json_object", "schema": SCHEMA},
            temperature=0.0,
            max_tokens=600,
        )
        content = response["choices"][0]["message"]["content"] or ""
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}
