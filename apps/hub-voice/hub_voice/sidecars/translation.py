"""Translation sidecar: a labeled reading aid for the operator screen, never counted.

Calls the local OpenAI-compatible LLM (Gemma 4 E4B on the hub) only when a base
URL is configured; otherwise returns no advice. The number guard refuses a
translation that introduces a number the source did not say. The output is
displayed next to the original, labeled as machine translation; it never enters
facts, counts, approvals or anything the speaker sends.
"""

from __future__ import annotations

import re

from .base import Advice, SidecarContext, Turn

try:
    import httpx
except Exception:  # pragma: no cover
    httpx = None  # type: ignore[assignment]

NUMBERS = re.compile(r"\d+")
TARGET = {"sw": "en", "en": "sw"}


def number_guard(source: str, translation: str) -> bool:
    """True if every digit sequence in the translation also appears in the source."""
    return set(NUMBERS.findall(translation)) <= set(NUMBERS.findall(source))


class TranslationSidecar:
    name = "translation"

    def __init__(self, timeout_s: float = 1.2) -> None:
        self._timeout = timeout_s

    async def run(self, turn: Turn, ctx: SidecarContext) -> Advice | None:
        base = ctx.settings.llm_base_url
        if not base or httpx is None:
            return None
        src_lang = turn.language_hint or "sw"
        tgt = TARGET.get(src_lang)
        if tgt is None:
            return None
        prompt = (
            f"Translate the following {src_lang} text to {tgt} for a human operator reading along. "
            "Output only the translation. Keep every number exactly as written; do not add numbers, names or facts.\n\n" + turn.text
        )
        body = {"model": ctx.settings.llm_model, "messages": [{"role": "user", "content": prompt}], "temperature": 0, "max_tokens": 200}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            r = await client.post(base.rstrip("/") + "/chat/completions", json=body)
        if r.status_code != 200:
            return None
        text = str(r.json()["choices"][0]["message"]["content"]).strip()
        if not text:
            return None
        if not number_guard(turn.text, text):
            return Advice(self.name, "machine translation withheld: it introduced a number the caller did not say", {"withheld": True, "reason": "number_guard"})
        return Advice(self.name, f"[machine translation, reading aid, never counted] {text}", {"translation": text, "to": tgt, "label": "machine_translation_unreviewed"})
