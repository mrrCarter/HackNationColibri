from datetime import time
from typing import Any

from sauti.farm_sheet import FarmSheet
from sauti.storage import db
from sauti.workflows.setup_farm import extract_candidates, run_setup

DICTATION = (
    "Bei ni shilingi elfu mbili kwa mtu. Napokea wageni kumi. Ziara ni Jumatatu hadi Jumamosi "
    "kuanzia saa tatu asubuhi mpaka saa tisa mchana. Kutoka soko la Othaya fuata barabara "
    "ya kanisa kilomita mbili. Wageni wanapata kahawa na chakula cha mchana."
)
GOOD_SPANS = {
    "price": "shilingi elfu mbili kwa mtu",
    "capacity": "wageni kumi",
    "days": "Jumatatu hadi Jumamosi",
    "hours": "kuanzia saa tatu asubuhi mpaka saa tisa mchana",
    "directions": "Kutoka soko la Othaya fuata barabara ya kanisa kilomita mbili",
    "inclusions": ["kahawa", "chakula cha mchana"],
}


class ScriptedNoor:
    """Plays Noor's answers in order and records everything the agent said."""

    def __init__(self, answers: list[str]) -> None:
        self.answers = list(answers)
        self.said: list[str] = []

    def say(self, text: str) -> None:
        self.said.append(text)

    def listen(self, *, long: bool = False) -> str:
        return self.answers.pop(0) if self.answers else ""


class FakeExtractor:
    def __init__(self, spans: dict[str, Any]) -> None:
        self.spans = spans

    def extract(self, transcript: str) -> dict[str, Any]:
        return self.spans


class Recorder:
    def __init__(self) -> None:
        self.saved: list[FarmSheet] = []

    def __call__(self, sheet: FarmSheet, transcript: str) -> int:
        self.saved.append(sheet)
        return len(self.saved)


def test_happy_path_saves_confirmed_sheet() -> None:
    noor = ScriptedNoor([DICTATION] + ["ndiyo"] * 6 + ["ndiyo"])
    save = Recorder()
    result = run_setup(noor, FakeExtractor(GOOD_SPANS), save)

    assert result.saved_version == 1
    sheet = save.saved[0]
    assert sheet.price_per_person_kes == 2000
    assert sheet.capacity_per_tour == 10
    assert sheet.days == ["mon", "tue", "wed", "thu", "fri", "sat"]
    assert (sheet.hours.start, sheet.hours.end) == (time(9), time(15))
    assert sheet.inclusions_sw == ["kahawa", "chakula cha mchana"]
    assert sheet.missing_fields() == []
    # the agent reads numbers as words, never digits
    assert any("shilingi elfu mbili" in line for line in noor.said)


def test_final_no_saves_nothing() -> None:
    noor = ScriptedNoor([DICTATION] + ["ndiyo"] * 6 + ["hapana"])
    save = Recorder()
    result = run_setup(noor, FakeExtractor(GOOD_SPANS), save)
    assert result.saved_version is None
    assert save.saved == []


def test_unclear_answer_is_never_a_yes() -> None:
    noor = ScriptedNoor([DICTATION] + ["ndiyo"] * 6 + ["mmm", "eeh", "sijui"])
    save = Recorder()
    run_setup(noor, FakeExtractor(GOOD_SPANS), save)
    assert save.saved == []


def test_invented_span_is_dropped() -> None:
    spans = {**GOOD_SPANS, "price": "shilingi elfu tano"}  # never said
    noor = ScriptedNoor([DICTATION] + ["ndiyo"] * 6 + ["ndiyo"])
    save = Recorder()
    run_setup(noor, FakeExtractor(spans), save)
    assert save.saved[0].price_per_person_kes == 2000
    assert not any("elfu tano" in line for line in noor.said)


def test_missing_price_is_asked() -> None:
    dictation = "Napokea wageni kumi."
    noor = ScriptedNoor([dictation, "elfu mbili", "ndiyo"] + ["ndiyo"] + ["sijui"] * 4 + ["ndiyo"])
    save = Recorder()
    run_setup(noor, None, save)
    assert any("shilingi ngapi" in line for line in noor.said)
    assert save.saved[0].price_per_person_kes == 2000


def test_no_on_a_field_asks_again_and_uses_new_value() -> None:
    noor = ScriptedNoor([DICTATION, "hapana", "elfu mbili na mia tano", "ndiyo"] + ["ndiyo"] * 5 + ["ndiyo"])
    save = Recorder()
    run_setup(noor, FakeExtractor(GOOD_SPANS), save)
    assert save.saved[0].price_per_person_kes == 2500


def test_without_llm_code_alone_reads_the_dictation() -> None:
    noor = ScriptedNoor([DICTATION] + ["ndiyo"] * 6 + ["ndiyo"])
    save = Recorder()
    run_setup(noor, None, save)
    sheet = save.saved[0]
    assert sheet.price_per_person_kes == 2000
    assert sheet.capacity_per_tour == 10
    assert sheet.days == ["mon", "tue", "wed", "thu", "fri", "sat"]
    assert sheet.hours.start == time(9)
    assert sheet.directions_sw.startswith("Kutoka soko la Othaya")
    assert sheet.inclusions_sw == ["kahawa", "chakula cha mchana"]


OTHER_DICTATION = (
    "Habari. Mimi naitwa Noor. Tunapokea wageni kila siku isipokuwa Jumapili, kuanzia saa mbili "
    "asubuhi hadi saa kumi jioni. Kila mgeni analipa shilingi elfu moja na mia tano. Naweza kupokea "
    "watu wanane kwa wakati mmoja. Ukifika Karatina, panda matatu ya Kagochi, shuka kwenye duka la "
    "Mama Wanjiku. Tunawapa kahawa yetu na ndizi."
)
# What Qwen 0.6B really returned on OTHER_DICTATION: every field shifted.
CONFUSED_SPANS = {
    "price": "Habari",
    "capacity": "Mimi naitwa Noor",
    "days": "Jumapili",
    "hours": "kuanzia saa mbili asubuhi hadi saa kumi jioni",
    "directions": "Kila mgeni analipa shilingi elfu moja na mia tano",
    "inclusions": ["Kuratina", "panda matatu", "shuka kwenye duka la Mama Wanjiku"],
}


def test_code_overrules_a_confused_llm() -> None:
    candidates = extract_candidates(OTHER_DICTATION, FakeExtractor(CONFUSED_SPANS))
    assert candidates["price_per_person_kes"] == 1500
    assert candidates["capacity_per_tour"] == 8
    assert candidates["days"] == ["mon", "tue", "wed", "thu", "fri", "sat"]
    assert candidates["hours"].start == time(8) and candidates["hours"].end == time(16)
    assert candidates["directions_sw"].startswith("Ukifika Karatina")
    assert candidates["inclusions_sw"] == ["kahawa yetu", "ndizi"]


def test_whisper_slips_on_numbers_are_repaired() -> None:
    candidates = extract_candidates("Bei ni shilingi e fumbili kwa kila mgeni.", None)
    assert candidates["price_per_person_kes"] == 2000


def test_field_left_empty_after_repeated_failures() -> None:
    spans = {**GOOD_SPANS, "directions": None}
    dictation = DICTATION.replace("Kutoka soko la Othaya fuata barabara ya kanisa kilomita mbili.", "")
    answers = [dictation] + ["ndiyo"] * 4 + ["mmm", "eeh", "aah"] + ["ndiyo", "ndiyo"]
    noor = ScriptedNoor(answers)
    save = Recorder()
    run_setup(noor, FakeExtractor(spans), save)
    assert save.saved[0].directions_sw is None
    assert any("Sina uhakika kuhusu maelekezo" in line for line in noor.said)


def test_silence_hangs_up_without_saving() -> None:
    save = Recorder()
    result = run_setup(ScriptedNoor([]), FakeExtractor(GOOD_SPANS), save)
    assert result.saved_version is None and save.saved == []


def test_broken_extractor_does_not_crash_the_call() -> None:
    class Broken:
        def extract(self, transcript: str) -> dict[str, Any]:
            raise RuntimeError("model crashed")

    noor = ScriptedNoor([DICTATION])
    run_setup(noor, Broken(), Recorder())  # must not raise


def test_db_versions() -> None:
    conn = db.connect(":memory:")
    assert db.get_current_farm_sheet(conn) is None
    db.save_farm_sheet(conn, FarmSheet(price_per_person_kes=2000), "test", "bei elfu mbili")
    v2 = db.save_farm_sheet(conn, FarmSheet(price_per_person_kes=2500), "test", None)
    version, sheet = db.get_current_farm_sheet(conn)
    assert version == v2 == 2
    assert sheet.price_per_person_kes == 2500
