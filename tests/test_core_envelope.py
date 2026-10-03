"""Contract r1.0: schemas, fixtures and digest vectors agree with each other.

These tests pin the cross-language truth. If a fixture's digest changes, either the
schema changed on purpose (regenerate with contracts/tools/make_fixtures.py and bump
the revision) or someone edited an envelope by hand, which is exactly what an
approval must detect.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from sauti.core import canon

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"
FIX = CONTRACTS / "fixtures"

ENVELOPE = Draft202012Validator(json.loads((CONTRACTS / "action-envelope.schema.json").read_text(encoding="utf-8")))
APPROVAL = Draft202012Validator(json.loads((CONTRACTS / "approval-record.schema.json").read_text(encoding="utf-8")))


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def good_envelopes() -> list[Path]:
    return [p for p in sorted((FIX / "good").glob("*.json")) if load(p).get("schema") == "sauti.action_envelope"]


@pytest.mark.parametrize("path", good_envelopes(), ids=lambda p: p.stem)
def test_good_envelope_validates_and_digest_matches(path: Path) -> None:
    env = load(path)
    assert not list(ENVELOPE.iter_errors(env))
    assert _window_valid(env)
    body = {k: v for k, v in env.items() if k != "digest"}
    assert canon.digest(canon.ENVELOPE_DOMAIN, body) == env["digest"]


def test_integral_float_hashes_like_the_integer() -> None:
    # "1.0" parses as float in Python and as 1 in JS; both must hash identically (codex review, 22:22Z).
    assert canon.canonical_bytes({"fact_revision": 1.0}) == canon.canonical_bytes({"fact_revision": 1})
    with pytest.raises(canon.CanonError):
        canon.canonical_bytes({"fact_revision": 1.5})
    with pytest.raises(canon.CanonError):
        canon.canonical_bytes({"fact_revision": 2**53})


def test_good_approval_binds_to_its_envelope() -> None:
    approval = load(FIX / "good" / "approval_send_message.json")
    env = load(FIX / "good" / "send_message_simulated.json")
    assert not list(APPROVAL.iter_errors(approval))
    assert approval["action_id"] == env["action_id"]
    assert approval["digest"] == env["digest"]
    assert approval["fact_revision"] == env["fact_revision"]


@pytest.mark.parametrize("path", sorted((FIX / "bad").glob("*.json")), ids=lambda p: p.stem)
def test_bad_fixture_is_rejected(path: Path) -> None:
    case = load(path)
    data = case["input"]
    if data.get("schema") == "sauti.approval_record":
        assert list(APPROVAL.iter_errors(data)), case["reason"]
        return
    schema_errors = list(ENVELOPE.iter_errors(data))
    if schema_errors:
        return  # rejected at the schema gate
    # Schema-valid bad inputs must fail a later code check: calendar, window, digest or evidence.
    body = {k: v for k, v in data.items() if k != "digest"}
    window_ok = _window_valid(data)
    digest_ok = canon.digest(canon.ENVELOPE_DOMAIN, body) == data.get("digest")
    evidence_ok = all(_evidence_item_valid(item) for item in data.get("evidence", []))
    assert not (window_ok and digest_ok and evidence_ok), case["reason"]


def _parse_ts(text: str) -> datetime | None:
    try:
        return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _window_valid(env: dict) -> bool:
    """Code gate every implementation must apply after the schema: real dates and a non-empty window."""
    created, until = _parse_ts(env["created_at"]), _parse_ts(env["valid_until"])
    return created is not None and until is not None and until > created


def _evidence_item_valid(item: dict) -> bool:
    source = load(FIX / "sources" / f"{item['source_id']}.json")
    raw = source["text"].encode("utf-8")
    if canon.source_text_hash(source["text"]) != item["content_hash"]:
        return False
    start, end = item["span"]["start"], item["span"]["end"]
    if not (0 <= start < end <= len(raw)):
        return False
    try:
        return raw[start:end].decode("utf-8") == item["quote"]
    except UnicodeDecodeError:
        return False


def test_digest_vectors_reproduce() -> None:
    vectors = load(FIX / "digest-vectors.json")["vectors"]
    assert vectors, "no vectors generated"
    for v in vectors:
        canonical = bytes.fromhex(v["canonical_utf8_hex"])
        assert canon.canonical_bytes(v["envelope_without_digest"]) == canonical
        expected = hashlib.sha256(v["domain"].encode() + b"\x00" + canonical).hexdigest()
        assert expected == v["digest"]
        assert canon.digest(canon.ENVELOPE_DOMAIN, v["envelope_without_digest"]) == v["digest"]


def test_canon_rejects_floats_and_non_finite() -> None:
    with pytest.raises(canon.CanonError):
        canon.canonical_bytes({"amount": 1.5})
    with pytest.raises(canon.CanonError):
        canon.canonical_bytes({"amount": float("inf")})
    with pytest.raises(canon.CanonError):
        canon.digest(b"", {"a": 1})


def test_canon_key_order_does_not_matter_but_values_do() -> None:
    a = {"b": 1, "a": {"y": [1, 2], "x": "é"}}
    b = {"a": {"x": "é", "y": [1, 2]}, "b": 1}
    assert canon.canonical_bytes(a) == canon.canonical_bytes(b)
    assert canon.digest(canon.ENVELOPE_DOMAIN, a) != canon.digest(canon.ENVELOPE_DOMAIN, {**a, "b": 2})
    assert canon.digest(canon.ENVELOPE_DOMAIN, a) != canon.digest(canon.APPROVAL_DOMAIN, a)
