from datetime import time

import pytest

from sauti.lang import swahili as sw


@pytest.mark.parametrize(
    "text, expected",
    [
        ("shilingi elfu mbili", 2000),
        ("elfu mbili na mia tano", 2500),
        ("elfu mbili mia tano", 2500),
        ("kumi na tano", 15),
        ("elfu kumi na tano", 15000),
        ("elfu mia moja", 100_000),
        ("laki moja na elfu hamsini", 150_000),
        ("Ksh 2,000", 2000),
        ("2000/= kwa mtu mmoja", 2000),
        ("watu watano", 5),
    ],
)
def test_parse_amount(text: str, expected: int) -> None:
    assert sw.parse_amount(text) == expected


def test_clock_hours_are_not_amounts() -> None:
    assert sw.parse_amount("saa tatu asubuhi") is None


def _ambiguous_in_swahili(n: int) -> bool:
    # 20 001 and 21 000 are both said "elfu ishirini na moja"; we read the latter.
    thousands = n // 1000 % 1000
    return thousands >= 10 and thousands % 10 == 0 and 1 <= n % 1000 <= 9


def test_number_words_round_trip() -> None:
    for n in list(range(1, 3000)) + list(range(3000, 2_000_000, 997)) + [1001, 2005, 100_001]:
        if not _ambiguous_in_swahili(n):
            assert sw.parse_amount(sw.number_to_words(n)) == n, n


def test_people_agreement() -> None:
    assert sw.people_to_words(5) == "watano"
    assert sw.people_to_words(12) == "kumi na wawili"
    assert sw.people_to_words(10) == "kumi"


@pytest.mark.parametrize(
    "text, expected",
    [
        ("saa tatu asubuhi", time(9, 0)),
        ("saa tisa mchana", time(15, 0)),
        ("saa kumi na moja jioni", time(17, 0)),
        ("saa moja jioni", time(19, 0)),
        ("saa mbili na nusu", time(8, 30)),
        ("saa nne kasorobo", time(9, 45)),
        ("saa 2 asubuhi", time(8, 0)),
        ("14:00", time(14, 0)),
        ("8 am", time(8, 0)),
    ],
)
def test_find_times(text: str, expected: time) -> None:
    assert sw.find_times(text) == [expected]


def test_time_words_round_trip() -> None:
    for hour in range(24):
        for minute in (0, 10, 15, 30, 45, 59):
            t = time(hour, minute)
            assert sw.find_times(sw.time_to_words(t)) == [t], sw.time_to_words(t)


def test_parse_hours() -> None:
    assert sw.parse_hours("kuanzia saa tatu asubuhi mpaka saa tisa mchana") == (time(9), time(15))
    assert sw.parse_hours("saa tatu asubuhi tu") is None


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Jumatatu hadi Ijumaa", ["mon", "tue", "wed", "thu", "fri"]),
        ("kila siku isipokuwa Jumapili", ["mon", "tue", "wed", "thu", "fri", "sat"]),
        ("Jumamosi na Jumapili", ["sat", "sun"]),
        ("juma tano tu", ["wed"]),
        ("hakuna siku", None),
    ],
)
def test_parse_days(text: str, expected: list[str] | None) -> None:
    assert sw.parse_days(text) == expected


def test_days_to_words() -> None:
    assert sw.days_to_words(["mon", "tue", "wed", "thu", "fri", "sat"]) == "Jumatatu hadi Jumamosi"
    assert sw.days_to_words(["sat", "sun"]) == "Jumamosi na Jumapili"


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Ndiyo", "yes"),
        ("sawa kabisa", "yes"),
        ("hapana, si sawa", "no"),
        ("1", "yes"),
        ("mbili", "no"),
        ("rudia tafadhali", "repeat"),
        ("ndiyo, saa tatu", "yes"),  # a keypad word inside a sentence is not a keypress
        ("mmm", None),
        ("", None),
    ],
)
def test_parse_confirmation(text: str, expected: str | None) -> None:
    assert sw.parse_confirmation(text) == expected


def test_grounding_rejects_invented_spans() -> None:
    transcript = "Bei ni shilingi elfu mbili kwa mtu"
    assert sw.is_grounded("shilingi elfu mbili", transcript)
    assert not sw.is_grounded("shilingi elfu tano", transcript)
