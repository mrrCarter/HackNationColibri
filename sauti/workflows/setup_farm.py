"""W1. Set up the farm, as one phone-call style conversation.

1. Noor describes her tour freely (free dictation).
2. The extractor (Qwen) copies, word for word, the span of the transcript that
   holds each fact. Spans that were not actually said are dropped.
3. Code parses every span (numbers, Swahili clock times, weekdays).
4. Missing facts are asked one by one.
5. Every value is read back and kept only after an explicit "ndiyo".
6. The full sheet is read back and saved only after a final "ndiyo".

Unclear answers are never treated as yes. A value Noor cannot confirm is left
empty rather than guessed.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from sauti.farm_sheet import FarmSheet, OpeningHours
from sauti.lang import swahili as sw

MAX_FIELD_ATTEMPTS = 3
MAX_CONFIRM_ATTEMPTS = 3


class Channel(Protocol):
    """How the agent talks with Noor: simulated call (voice) or text console."""

    def say(self, text: str) -> None: ...

    def listen(self, *, long: bool = False) -> str:
        """What Noor said, or '' on silence. long=True for free dictation."""
        ...


class Extractor(Protocol):
    def extract(self, transcript: str) -> dict[str, Any]:
        """Raw spans copied from the transcript, keyed by field name, None when absent."""
        ...


# ---------------------------------------------------------------- what the agent says

GREETING = (
    "Habari Noor, karibu. Mimi ni Sauti, msaidizi wako. "
    "Tutaandaa taarifa za ziara za shamba lako. "
    "Niambie kwa maneno yako: bei kwa kila mgeni, idadi ya wageni unaoweza kupokea, "
    "siku na saa za ziara, maelekezo ya kufika shambani, na kinachojumuishwa kwenye ziara. "
    "Ukimaliza, nyamaza kidogo."
)
NO_SPEECH = "Sijakusikia. Tafadhali ongea sasa."
HANG_UP_SILENT = "Sijakusikia. Tafadhali piga tena baadaye. Kwaheri."
THINKING = "Asante. Ngoja kidogo, ninasoma ulichosema."
NOT_UNDERSTOOD = "Samahani, sikuelewa vizuri."
IS_IT_RIGHT = "Ni sawa?"
YES_NO_HINT = "Sema ndiyo au hapana. Unaweza pia kusema moja kwa ndiyo, au mbili kwa hapana."
SUMMARY_INTRO = "Hizi ndizo taarifa nilizonazo."
SAVE_QUESTION = "Nihifadhi taarifa hizi?"
SAVED = "Nimehifadhi. Asante Noor. Kwaheri."
NOT_SAVED = "Sawa, sijahifadhi chochote. Kwaheri."
NOTHING_TO_SAVE = "Sina taarifa yoyote iliyothibitishwa, kwa hiyo sijahifadhi chochote. Kwaheri."


def _skip_message(label: str) -> str:
    return f"Sina uhakika kuhusu {label}, kwa hiyo sitaiandika. Unaweza kuiongeza baadaye."


# ---------------------------------------------------------------- fields


def _parse_hours(text: str) -> OpeningHours | None:
    hours = sw.parse_hours(text)
    return OpeningHours(start=hours[0], end=hours[1]) if hours else None


def _parse_free_text(text: str) -> str | None:
    cleaned = " ".join(text.split()).strip(" .,;")
    return cleaned if len(cleaned.split()) >= 3 else None


def _parse_list(text: str) -> list[str] | None:
    items = [item.strip(" .") for item in re.split(r",|;|\bpamoja na\b|\bna\b", text)]
    items = [item for item in items if len(item) > 1]
    return items or None


def _amount_in_range(low: int, high: int) -> Callable[[str], int | None]:
    def parse(text: str) -> int | None:
        value = sw.parse_amount(text)
        return value if value is not None and low <= value <= high else None

    return parse


@dataclass(frozen=True)
class FieldSpec:
    name: str  # FarmSheet attribute
    span_key: str  # key in the extractor output
    label: str  # Swahili name, used when skipping
    question: str
    parse: Callable[[str], Any]
    readback: Callable[[Any], str]


FIELDS: tuple[FieldSpec, ...] = (
    FieldSpec(
        "price_per_person_kes", "price", "bei",
        "Bei ya ziara ni shilingi ngapi kwa kila mgeni?",
        _amount_in_range(1, 1_000_000),
        lambda v: f"Bei ni shilingi {sw.number_to_words(v)} kwa kila mgeni.",
    ),
    FieldSpec(
        "capacity_per_tour", "capacity", "idadi ya wageni",
        "Unaweza kupokea wageni wangapi kwa ziara moja?",
        _amount_in_range(1, 200),
        lambda v: "Unapokea mgeni mmoja kwa ziara moja." if v == 1
        else f"Unapokea wageni {sw.people_to_words(v)} kwa ziara moja.",
    ),
    FieldSpec(
        "days", "days", "siku za ziara",
        "Unapokea wageni siku gani za wiki?",
        sw.parse_days,
        lambda v: f"Siku za ziara ni {sw.days_to_words(v)}.",
    ),
    FieldSpec(
        "hours", "hours", "saa za ziara",
        "Ziara zinaanza saa ngapi, na zinamalizika saa ngapi?",
        _parse_hours,
        lambda v: f"Ziara ni kuanzia {sw.time_to_words(v.start)} hadi {sw.time_to_words(v.end)}.",
    ),
    FieldSpec(
        "directions_sw", "directions", "maelekezo",
        "Wageni wanafikaje shambani kwako? Nieleze maelekezo.",
        _parse_free_text,
        lambda v: f"Maelekezo ni: {v}.",
    ),
    FieldSpec(
        "inclusions_sw", "inclusions", "kinachojumuishwa",
        "Ziara inajumuisha nini? Kwa mfano kahawa au chakula.",
        _parse_list,
        lambda v: f"Ziara inajumuisha: {', '.join(v)}.",
    ),
)
FIELDS_BY_KEY = {spec.span_key: spec for spec in FIELDS}


# ---------------------------------------------------------------- extraction
# Cue word stems, matched inside words because Swahili glues prefixes (tunawapa, analipa).
# A span from the LLM is kept only if it carries a cue of its field; otherwise code
# looks for a sentence with that cue itself.

_PRICE_CUES = ("shilingi", "bei", "ksh", "kes", "pesa", "lipa", "gharama")
_PEOPLE_CUES = ("geni", "watu", "mtu", "pokea")
_DIRECTION_CUES = (
    "fika", "fuata", "panda", "shuka", "barabara", "kutoka", "kilomita", "matatu", "kona",
    "kushoto", "kulia", "njia", "soko", "pita", "geuka", "boda", "stage", "kanisa", "shule",
)
_INCLUSION_VERBS = ("wapa", "pata", "jumuisha", "onja", "kunywa", "pewa")


def _has_cue(text: str, stems: tuple[str, ...]) -> bool:
    # Day names are skipped: 'matatu' (minibus) hides inside 'Jumatatu' (Monday).
    words = [tok for tok in sw.tokens(text) if sw.parse_days(tok) is None]
    return any(stem in tok for tok in words for stem in stems)


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"[.?!;\n]+", text) if s.strip()]


def _strip_inclusion_verb(item: str) -> str:
    """'Wageni wanapata kahawa' -> 'kahawa'."""
    words = item.split()
    for i, word in enumerate(words[:-1]):
        if any(stem in word.lower() for stem in _INCLUSION_VERBS):
            return " ".join(words[i + 1:])
    return item


def _span_fits(key: str, span: str) -> bool:
    if key == "price":
        return _has_cue(span, _PRICE_CUES)
    if key == "capacity":
        return _has_cue(span, _PEOPLE_CUES) and not _has_cue(span, _PRICE_CUES)
    if key == "directions":
        return _has_cue(span, _DIRECTION_CUES) and not _has_cue(span, _PRICE_CUES)
    if key == "inclusions":
        return not (_has_cue(span, _DIRECTION_CUES) or _has_cue(span, _PRICE_CUES) or sw.find_numbers(span))
    return True


def _from_sentences(key: str, transcript: str) -> Any:
    """Code-only fallback: the first sentence carrying the field's cue."""
    for sentence in _sentences(transcript):
        if key == "price" and _span_fits("price", sentence):
            value = FIELDS_BY_KEY["price"].parse(sentence)
        elif key == "capacity" and _span_fits("capacity", sentence):
            value = FIELDS_BY_KEY["capacity"].parse(sentence)
        elif key == "directions" and _span_fits("directions", sentence):
            value = _parse_free_text(sentence)
        elif key == "inclusions" and _has_cue(sentence, _INCLUSION_VERBS) and _span_fits("inclusions", sentence):
            value = _parse_list(_strip_inclusion_verb(sentence))
        else:
            continue
        if value is not None:
            return value
    return None


def extract_candidates(transcript: str, extractor: Extractor | None) -> dict[str, Any]:
    """Parsed values from the free dictation. Only grounded, plausible spans survive."""
    raw: dict[str, Any] = {}
    if extractor is not None:
        try:
            raw = extractor.extract(transcript) or {}
        except Exception:  # a broken model must never block the call: we just ask more questions
            raw = {}

    candidates: dict[str, Any] = {}
    # Days and clock times are unambiguous in Swahili: code reads them on the whole transcript.
    if days := sw.parse_days(transcript):
        candidates["days"] = days
    if hours := _parse_hours(transcript):
        candidates["hours"] = hours

    for spec in FIELDS:
        if spec.name in candidates:
            continue
        span = raw.get(spec.span_key)
        value = None
        if spec.span_key == "inclusions":
            items = [
                _strip_inclusion_verb(" ".join(i.split()).strip(" ."))
                for i in (span or [])
                if isinstance(i, str) and sw.is_grounded(i, transcript) and _span_fits("inclusions", i)
            ]
            value = [i for i in items if i] or None
        elif isinstance(span, str) and sw.is_grounded(span, transcript) and _span_fits(spec.span_key, span):
            value = spec.parse(span)
        if value is None:
            value = _from_sentences(spec.span_key, transcript)
        if value is not None:
            candidates[spec.name] = value
    return candidates


# ---------------------------------------------------------------- conversation


@dataclass
class SetupResult:
    saved_version: int | None
    sheet: FarmSheet | None
    transcript: list[str] = field(default_factory=list)


class _Conversation:
    def __init__(self, channel: Channel) -> None:
        self.channel = channel
        self.heard: list[str] = []

    def ask(self, text: str, *, long: bool = False) -> str:
        self.channel.say(text)
        answer = self.channel.listen(long=long).strip()
        if answer:
            self.heard.append(answer)
        return answer

    def confirm(self, statement: str, question: str = IS_IT_RIGHT) -> bool:
        """Read a statement back and wait for an explicit yes."""
        full = f"{statement} {question}".strip()
        prompt = full
        for _ in range(MAX_CONFIRM_ATTEMPTS):
            answer = sw.parse_confirmation(self.ask(prompt))
            if answer == "yes":
                return True
            if answer == "no":
                return False
            prompt = full if answer == "repeat" else f"{NOT_UNDERSTOOD} {YES_NO_HINT} {full}"
        return False  # never assume a yes

    def settle_field(self, spec: FieldSpec, value: Any) -> Any:
        """Return a value Noor confirmed, or None if she could not."""
        attempts = 0
        while True:
            if value is None:
                if attempts >= MAX_FIELD_ATTEMPTS:
                    self.channel.say(_skip_message(spec.label))
                    return None
                attempts += 1
                answer = self.ask(spec.question)
                if sw.is_skip(answer):
                    self.channel.say(_skip_message(spec.label))
                    return None
                value = spec.parse(answer) if answer else None
                if value is None:
                    self.channel.say(NOT_UNDERSTOOD)
                    continue
            if self.confirm(spec.readback(value)):
                return value
            value = None


def run_setup(
    channel: Channel,
    extractor: Extractor | None,
    save: Callable[[FarmSheet, str], int],
) -> SetupResult:
    """Run W1 end to end. `save(sheet, transcript)` is only called after Noor's final yes."""
    talk = _Conversation(channel)

    dictation = talk.ask(GREETING, long=True)
    if not dictation:
        dictation = talk.ask(NO_SPEECH, long=True)
    if not dictation:
        channel.say(HANG_UP_SILENT)
        return SetupResult(None, None, talk.heard)

    channel.say(THINKING)
    candidates = extract_candidates(dictation, extractor)

    confirmed = {spec.name: talk.settle_field(spec, candidates.get(spec.name)) for spec in FIELDS}
    sheet = FarmSheet(**confirmed)
    present = [spec for spec in FIELDS if confirmed[spec.name] is not None]
    if not present:
        channel.say(NOTHING_TO_SAVE)
        return SetupResult(None, None, talk.heard)

    summary = " ".join([SUMMARY_INTRO, *(spec.readback(confirmed[spec.name]) for spec in present)])
    missing = [spec.label for spec in FIELDS if confirmed[spec.name] is None]
    if missing:
        summary += f" Bado sina: {', '.join(missing)}."
    channel.say(summary)

    if not talk.confirm(SAVE_QUESTION, question=""):
        channel.say(NOT_SAVED)
        return SetupResult(None, sheet, talk.heard)

    version = save(sheet, "\n".join(talk.heard))
    channel.say(SAVED)
    return SetupResult(version, sheet, talk.heard)
