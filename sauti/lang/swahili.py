"""Swahili parsing and rendering, done by code and never by the LLM.

Prices, head counts, clock times and weekdays are read from transcripts here,
and rendered back to words here, so that the facts in the farm sheet never
depend on model output and the TTS never has to read digits.
"""

from __future__ import annotations

import re
from datetime import time

UNITS = {"moja": 1, "mbili": 2, "tatu": 3, "nne": 4, "tano": 5, "sita": 6, "saba": 7, "nane": 8, "tisa": 9}
# Agreement forms used when counting people: mtu mmoja, watu wawili, ...
PEOPLE_UNITS = {"mmoja": 1, "wawili": 2, "watatu": 3, "wanne": 4, "watano": 5, "wanane": 8}
TENS = {
    "kumi": 10, "ishirini": 20, "thelathini": 30, "arobaini": 40, "hamsini": 50,
    "sitini": 60, "sabini": 70, "themanini": 80, "tisini": 90,
}
MULTIPLIERS = {"mia": 100, "elfu": 1000, "laki": 100_000, "milioni": 1_000_000}

_SMALL = {**UNITS, **PEOPLE_UNITS, **TENS}
_UNIT_WORDS = {v: k for k, v in UNITS.items()}
_TENS_WORDS = {v: k for k, v in TENS.items()}
_PEOPLE_WORDS = {v: k for k, v in PEOPLE_UNITS.items()}

WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
_DAY_WORDS = {
    "jumatatu": "mon", "jumanne": "tue", "jumatano": "wed", "alhamisi": "thu",
    "ijumaa": "fri", "jumamosi": "sat", "jumapili": "sun",
    "monday": "mon", "tuesday": "tue", "wednesday": "wed", "thursday": "thu",
    "friday": "fri", "saturday": "sat", "sunday": "sun",
}
_SW_DAY_NAMES = {
    "mon": "Jumatatu", "tue": "Jumanne", "wed": "Jumatano", "thu": "Alhamisi",
    "fri": "Ijumaa", "sat": "Jumamosi", "sun": "Jumapili",
}
_RANGE_WORDS = {"hadi", "mpaka", "to", "until", "till"}
_EXCEPT_WORDS = {"isipokuwa", "ila", "bila", "except"}
_PERIODS = {"alfajiri", "asubuhi", "mchana", "jioni", "usiku"}

_YES = {"ndiyo", "ndio", "sawa", "sawasawa", "naam", "kweli", "yes", "yeah", "ok", "okay"}
_NO = {"hapana", "la", "siyo", "sio", "si", "no", "badilisha", "kosa"}
_REPEAT = {"rudia", "tena", "sijasikia", "sikusikia", "sijaelewa", "nini", "repeat"}
# Keypad fallback, also accepted spoken: 1 yes, 2 no, 3 repeat. Only as a whole answer.
_KEYPAD = {"1": "yes", "moja": "yes", "2": "no", "mbili": "no", "3": "repeat", "tatu": "repeat"}


def tokens(text: str) -> list[str]:
    """Lowercase word tokens; digits kept whole, clock times kept as 'h:mm'."""
    text = text.lower()
    text = re.sub(r"(?<=\d)[,.](?=\d{3}(?!\d))", "", text)  # 2,000 or 2.000 -> 2000
    text = re.sub(r"\b(\d{1,2})\.(\d{2})\b", r"\1:\2", text)  # 8.30 -> 8:30
    text = re.sub(r"\bjuma (tatu|nne|tano|mosi|pili)\b", r"juma\1", text)
    return re.findall(r"\d{1,2}:\d{2}|\d+|[a-z']+", text)


# ---------------------------------------------------------------- ASR repair
# Whisper often glues or misspells number words ("efumbili" for "elfu mbili").
# We only repair towards number, day and clock words, and only on close matches,
# so a repair can at worst produce a value that Noor then rejects on readback.

_REPAIRABLE = (
    set(UNITS) | set(PEOPLE_UNITS) | set(TENS) | set(MULTIPLIERS) | set(_DAY_WORDS) | _PERIODS
    | {"kasorobo", "hapana", "ndiyo"}
)
_SPLIT_HEADS = set(MULTIPLIERS) | set(TENS)


def _within_one_edit(a: str, b: str) -> bool:
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) <= 1
    short, long_ = (a, b) if len(a) < len(b) else (b, a)
    return any(long_[:i] + long_[i + 1:] == short for i in range(len(long_)))


def _repair_word(tok: str, min_len: int) -> str | None:
    if tok in _REPAIRABLE:
        return tok
    if len(tok) < min_len:
        return None
    matches = [w for w in _REPAIRABLE if len(w) >= min_len - 1 and _within_one_edit(tok, w)]
    return matches[0] if len(matches) == 1 else None


def _repair_glued(tok: str) -> list[str] | None:
    """'elfumbili' / 'efumbili' -> ['elfu', 'mbili']; 'miatano' -> ['mia', 'tano']."""
    for cut in range(2, len(tok) - 2):
        head, tail = tok[:cut], tok[cut:]
        fixed_head = head if head in _SPLIT_HEADS else next(
            (h for h in _SPLIT_HEADS if len(head) >= 3 and _within_one_edit(head, h)), None
        )
        if fixed_head is None:
            continue
        fixed_tail = _repair_word(tail, min_len=4)
        if fixed_tail is not None and (fixed_tail in UNITS or fixed_tail in TENS or fixed_tail in PEOPLE_UNITS):
            return [fixed_head, fixed_tail]
    return None


def repaired_tokens(text: str) -> list[str]:
    """tokens() with likely ASR slips on number, day and clock words fixed."""
    toks = tokens(text)
    out: list[str] = []
    i = 0
    while i < len(toks):
        tok = toks[i]
        if tok in _REPAIRABLE or tok.isdigit() or ":" in tok:
            out.append(tok)
            i += 1
            continue
        # Whisper sometimes splits a glued word: "e fumbili"
        if i + 1 < len(toks) and toks[i + 1] not in _REPAIRABLE and (glued := _repair_glued(tok + toks[i + 1])):
            out.extend(glued)
            i += 2
            continue
        out.extend(_repair_glued(tok) or [_repair_word(tok, min_len=5) or tok])
        i += 1
    return out


# ---------------------------------------------------------------- numbers


def _is_number_token(tok: str) -> bool:
    return tok.isdigit() or tok in _SMALL or tok in MULTIPLIERS


def _value(tok: str) -> int:
    return int(tok) if tok.isdigit() else _SMALL[tok]


def _parse_run(toks: list[str]) -> int:
    """Value of a run of number tokens, 'na' connectors included."""
    total = 0
    i = 0
    while i < len(toks):
        tok = toks[i]
        if tok == "na":
            i += 1
        elif tok == "mia":
            # mia takes a single digit after it: mia tano = 500, mia alone = 100
            nxt = toks[i + 1] if i + 1 < len(toks) else None
            if nxt is not None and (nxt in UNITS or (nxt.isdigit() and 1 <= int(nxt) <= 9)):
                total += 100 * _value(nxt)
                i += 2
            else:
                total += 100
                i += 1
        elif tok in MULTIPLIERS:
            # elfu mbili mia tano: the count of elfu stops at the next multiplier,
            # except a smaller one in first position (elfu mia moja = 100 000).
            # It stops at 'na' too (elfu moja na moja = 1001), except inside a
            # tens-and-units count (elfu kumi na tano = 15 000, the usual reading).
            j = i + 1
            if j < len(toks) and toks[j] in MULTIPLIERS and MULTIPLIERS[toks[j]] < MULTIPLIERS[tok]:
                j += 1
            while j < len(toks) and toks[j] not in MULTIPLIERS:
                if toks[j] == "na" and not (
                    toks[j - 1] in TENS and j + 1 < len(toks) and (toks[j + 1] in UNITS or toks[j + 1] in PEOPLE_UNITS)
                ):
                    break
                j += 1
            count = _parse_run(toks[i + 1:j]) if j > i + 1 else 1
            total += MULTIPLIERS[tok] * count
            i = j
        else:
            total += _value(tok)
            i += 1
    return total


def find_numbers(text: str) -> list[int]:
    """Every number said in the text, in order. Clock hours ('saa tatu') are skipped."""
    toks = repaired_tokens(text)
    runs: list[list[str]] = []
    current: list[str] = []
    after_saa = False
    for i, tok in enumerate(toks):
        if _is_number_token(tok):
            # a bare digit right after another number starts a new number ("2000 10")
            if current and tok.isdigit() and current[-1] not in MULTIPLIERS:
                runs.append(current)
                current = []
            if not current and i > 0 and toks[i - 1] == "saa":
                after_saa = True
            current.append(tok)
        elif tok == "na" and current and i + 1 < len(toks) and _is_number_token(toks[i + 1]):
            current.append(tok)
        else:
            if current and not after_saa:
                runs.append(current)
            current, after_saa = [], False
    if current and not after_saa:
        runs.append(current)
    return [_parse_run(run) for run in runs]


def parse_amount(text: str) -> int | None:
    """The largest number said, e.g. 'elfu mbili kwa mtu mmoja' -> 2000."""
    numbers = [n for n in find_numbers(text) if n > 0]
    return max(numbers) if numbers else None


def number_to_words(n: int) -> str:
    if n < 0:
        raise ValueError("negative numbers are not supported")
    if n == 0:
        return "sifuri"
    parts: list[str] = []
    for word, size in (("milioni", 1_000_000), ("laki", 100_000), ("elfu", 1000)):
        if n >= size:
            parts.append(f"{word} {number_to_words(n // size)}")
            n %= size
    if n >= 100:
        parts.append(f"mia {_UNIT_WORDS[n // 100]}")
        n %= 100
    if n >= 10:
        parts.append(_TENS_WORDS[n // 10 * 10])
        n %= 10
    if n:
        parts.append(_UNIT_WORDS[n])
    return " na ".join(parts)


def people_to_words(n: int) -> str:
    """Number agreeing with people nouns: wageni watano, mgeni mmoja."""
    words = number_to_words(n).split()
    last = words[-1]
    if last in UNITS and UNITS[last] in _PEOPLE_WORDS and (len(words) == 1 or words[-2] not in MULTIPLIERS):
        words[-1] = _PEOPLE_WORDS[UNITS[last]]
    return " ".join(words)


# ---------------------------------------------------------------- clock times
# Swahili time counts from 6 o'clock: saa moja asubuhi = 07:00, saa tisa mchana = 15:00.


def _swahili_to_24h(hour_sw: int, period: str | None) -> int:
    base = hour_sw + 6  # 7..18, daytime reading
    if period == "usiku":
        return (base + 12) % 24
    if period == "alfajiri":
        return base % 12
    if period == "asubuhi":
        return base - 12 if base > 12 else base
    if period == "jioni":
        return base if base >= 12 else base + 12
    return base


def _period_of(hour24: int) -> str:
    if 4 <= hour24 < 7:
        return "alfajiri"
    if 7 <= hour24 < 12:
        return "asubuhi"
    if 12 <= hour24 < 16:
        return "mchana"
    if 16 <= hour24 < 19:
        return "jioni"
    return "usiku"


def _read_small_run(toks: list[str], j: int) -> tuple[int | None, int]:
    """Read a number made of units and tens (kumi na moja), as for hours or minutes."""
    found: list[str] = []
    while j < len(toks):
        tok = toks[j]
        if tok in UNITS or tok in TENS or tok.isdigit():
            found.append(tok)
            j += 1
        elif tok == "na" and found and j + 1 < len(toks) and toks[j + 1] in UNITS:
            j += 1
        else:
            break
    return (_parse_run(found) if found else None), j


def _parse_swahili_clock(toks: list[str], j: int) -> tuple[time | None, int]:
    """Parse what follows 'saa': hour, optional minutes, optional period."""
    if j < len(toks) and ":" in toks[j]:
        hour_sw, minute = (int(x) for x in toks[j].split(":"))
        j += 1
    else:
        hour_sw, j = _read_small_run(toks, j)
        if hour_sw is None:
            return None, j
        minute = 0
        if j + 1 < len(toks) and toks[j] == "na" and toks[j + 1] in ("nusu", "robo"):
            minute = 30 if toks[j + 1] == "nusu" else 15
            j += 2
        elif j + 1 < len(toks) and toks[j] == "na" and toks[j + 1] == "dakika":
            mins, j = _read_small_run(toks, j + 2)
            minute = mins or 0
        elif j < len(toks) and toks[j] == "kasorobo":
            hour_sw, minute = hour_sw - 1, 45
            j += 1
        elif j + 1 < len(toks) and toks[j] == "kasoro" and toks[j + 1] == "robo":
            hour_sw, minute = hour_sw - 1, 45
            j += 2
    if hour_sw == 0:
        hour_sw = 12
    if j < len(toks) and toks[j] in ("za", "ya") and j + 1 < len(toks) and toks[j + 1] in _PERIODS:
        j += 1
    period = None
    if j < len(toks) and toks[j] in _PERIODS:
        period = toks[j]
        j += 1
    if not (1 <= hour_sw <= 12 and 0 <= minute < 60):
        return None, j
    return time(_swahili_to_24h(hour_sw, period), minute), j


def _parse_western_clock(toks: list[str], j: int) -> tuple[time | None, int]:
    """Parse '14:00', '8:30 am', '8 pm' (only when not introduced by 'saa')."""
    tok = toks[j]
    if ":" in tok:
        hour, minute = (int(x) for x in tok.split(":"))
    else:
        hour, minute = int(tok), 0
    j += 1
    if j < len(toks) and toks[j] in ("am", "pm"):
        if toks[j] == "pm" and hour < 12:
            hour += 12
        elif toks[j] == "am" and hour == 12:
            hour = 0
        j += 1
    elif ":" not in tok:
        return None, j  # a bare number is not a time
    if not (0 <= hour < 24 and 0 <= minute < 60):
        return None, j
    return time(hour, minute), j


def find_times(text: str) -> list[time]:
    toks = repaired_tokens(text)
    found: list[time] = []
    j = 0
    while j < len(toks):
        if toks[j] == "saa":
            parsed, j = _parse_swahili_clock(toks, j + 1)
        elif ":" in toks[j] or (toks[j].isdigit() and j + 1 < len(toks) and toks[j + 1] in ("am", "pm")):
            parsed, j = _parse_western_clock(toks, j)
        else:
            parsed, j = None, j + 1
        if parsed is not None:
            found.append(parsed)
    return found


def parse_hours(text: str) -> tuple[time, time] | None:
    """Opening hours as (start, end): the first two times said, end after start."""
    times = find_times(text)
    if len(times) < 2 or times[1] <= times[0]:
        return None
    return times[0], times[1]


def time_to_words(t: time) -> str:
    period = _period_of(t.hour)
    hour_ref, suffix = t.hour, ""
    if t.minute == 45:
        hour_ref, suffix = (t.hour + 1) % 24, " kasorobo"
    elif t.minute == 30:
        suffix = " na nusu"
    elif t.minute == 15:
        suffix = " na robo"
    elif t.minute:
        suffix = f" na dakika {number_to_words(t.minute)}"
    hour_sw = (hour_ref - 6) % 12 or 12
    return f"saa {number_to_words(hour_sw)}{suffix} {period}"


# ---------------------------------------------------------------- weekdays


def parse_days(text: str) -> list[str] | None:
    """Weekday codes in week order. Understands 'kila siku', ranges and exceptions."""
    toks = repaired_tokens(text)
    joined = f" {' '.join(toks)} "
    days: set[str] = set()
    if " kila siku " in joined:
        days.update(WEEKDAYS)
    if " wikendi " in joined or " mwisho wa wiki " in joined:
        days.update(("sat", "sun"))
    excluding = False
    j = 0
    while j < len(toks):
        tok = toks[j]
        if tok in _EXCEPT_WORDS:
            excluding = True
        elif tok in _DAY_WORDS:
            selected = [_DAY_WORDS[tok]]
            if j + 2 < len(toks) and toks[j + 1] in _RANGE_WORDS and toks[j + 2] in _DAY_WORDS:
                start, end = WEEKDAYS.index(selected[0]), WEEKDAYS.index(_DAY_WORDS[toks[j + 2]])
                span = (end - start) % 7
                selected = [WEEKDAYS[(start + k) % 7] for k in range(span + 1)]
                j += 2
            if excluding:
                days.difference_update(selected)
            else:
                days.update(selected)
        j += 1
    return [d for d in WEEKDAYS if d in days] or None


def days_to_words(days: list[str]) -> str:
    ordered = [d for d in WEEKDAYS if d in days]
    if len(ordered) == 7:
        return "kila siku"
    idx = [WEEKDAYS.index(d) for d in ordered]
    if len(idx) >= 3 and idx == list(range(idx[0], idx[-1] + 1)):
        return f"{_SW_DAY_NAMES[ordered[0]]} hadi {_SW_DAY_NAMES[ordered[-1]]}"
    names = [_SW_DAY_NAMES[d] for d in ordered]
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} na {names[-1]}"


# ---------------------------------------------------------------- yes / no


def parse_confirmation(text: str) -> str | None:
    """'yes', 'no', 'repeat' or None when unclear. Unclear is never a yes."""
    toks = repaired_tokens(text)
    if not toks:
        return None
    if len(toks) == 1 and toks[0] in _KEYPAD:
        return _KEYPAD[toks[0]]
    words = set(toks)
    if words & _REPEAT:
        return "repeat"
    if words & _NO:
        return "no"
    if words & _YES:
        return "yes"
    return None


_SKIP = {"sijui", "ruka", "baadaye", "skip"}


def is_skip(text: str) -> bool:
    """Noor says she does not know or wants to give this later."""
    return bool(set(tokens(text)) & _SKIP)


# ---------------------------------------------------------------- grounding


def is_grounded(span: str, transcript: str, min_coverage: float = 0.8) -> bool:
    """True when the span was actually said: the LLM may only copy, never invent."""
    span_toks = tokens(span)
    source = tokens(transcript)
    if not span_toks:
        return False
    if f" {' '.join(span_toks)} " in f" {' '.join(source)} ":
        return True
    vocabulary = set(source)
    return sum(tok in vocabulary for tok in span_toks) / len(span_toks) >= min_coverage
