"""Generate contract fixtures and digest vectors from the Python reference canonicalizer.

    .venv/Scripts/python contracts/tools/make_fixtures.py

Every file it writes is synthetic and says so. Re-run after any schema change; the
test suite fails if a fixture's digest no longer matches.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from sauti.core.canon import ENVELOPE_DOMAIN, canonical_bytes, digest, source_text_hash  # noqa: E402

FIX = ROOT / "contracts" / "fixtures"
TENANT = "demo-owner-001"
NOTE = "Synthetic fixture. Not a real customer, not native-reviewed Swahili, not a send receipt."


def write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def with_digest(envelope: dict) -> dict:
    body = {k: v for k, v in envelope.items() if k != "digest"}
    return {**body, "digest": digest(ENVELOPE_DOMAIN, body)}


def main() -> None:
    # Immutable synthetic source text, Swahili with a multi-byte character so byte offsets are exercised.
    source_text = "Kahawa ilikuwa nzuri sana, lakini maelekezo ya kufika yalikuwa magumu — tulipotea njia."
    source = {
        "synthetic": True,
        "note": NOTE,
        "source_id": "synthetic-review-001",
        "source_type": "direct_review",
        "language": "sw",
        "text": source_text,
        "content_hash": source_text_hash(source_text),
    }
    write(FIX / "sources" / "synthetic-review-001.json", source)

    raw = source_text.encode("utf-8")
    quote = "maelekezo ya kufika yalikuwa magumu"
    start = raw.index(quote.encode("utf-8"))
    end = start + len(quote.encode("utf-8"))

    send_message = with_digest({
        "schema": "sauti.action_envelope",
        "schema_version": "1.0.0",
        "action_id": "42424242-1234-4abc-8123-abcdefabcdef",
        "tenant_id": TENANT,
        "kind": "send_message",
        "created_at": "2026-10-03T20:00:00Z",
        "valid_until": "2026-10-04T20:00:00Z",
        "fact_revision": 1,
        "recipient": {"channel": "simulated", "address": "SIMULATED:guest-001", "language": "sw"},
        "payload": {
            "type": "message",
            "body": "Asante kwa kututembelea. Ni sehemu gani ya maelekezo iliyokuwa ngumu?",
            "body_language": "sw",
            "in_reply_to": "synthetic-review-001",
            "template_id": "ask_which_direction_step",
        },
        "evidence": [{
            "source_id": "synthetic-review-001",
            "content_hash": source["content_hash"],
            "span": {"start": start, "end": end},
            "quote": quote,
        }],
        "preview": {
            "text": "SIMULATED tu. Tuma ujumbe huu kwa mgeni 001: Asante kwa kututembelea. Ni sehemu gani ya maelekezo iliyokuwa ngumu? (Haujakaguliwa na mzungumzaji wa Kiswahili.)",
            "render_locale": "sw-KE",
        },
        "authority": {"level": "owner", "owner_context_required": True},
    })
    write(FIX / "good" / "send_message_simulated.json", send_message)

    record_payment = with_digest({
        "schema": "sauti.action_envelope",
        "schema_version": "1.0.0",
        "action_id": "7a7a7a7a-5678-4def-9abc-0123456789ab",
        "tenant_id": TENANT,
        "kind": "record_payment",
        "created_at": "2026-10-03T20:05:00Z",
        "valid_until": "2026-10-03T21:05:00Z",
        "fact_revision": 1,
        "recipient": {"channel": "local", "address": "owner", "language": "sw"},
        "payload": {
            "type": "record_payment",
            "booking_id": "synthetic-booking-001",
            "money": {"amount_minor": 200000, "currency": "KES", "exponent": 2},
            "method": "mpesa",
            "reported_by": "owner",
        },
        "evidence": [],
        "preview": {
            "text": "Thomas, ziara Jumamosi tarehe nne Oktoba, watu wawili. Niandike malipo ya shilingi elfu mbili? (Later phase fixture.)",
            "render_locale": "sw-KE",
        },
        "authority": {"level": "owner", "owner_context_required": True},
    })
    write(FIX / "good" / "record_payment_owner_record.json", record_payment)

    approval = {
        "schema": "sauti.approval_record",
        "schema_version": "1.0.0",
        "approval_id": "11111111-2222-4333-8444-555555555555",
        "action_id": send_message["action_id"],
        "digest": send_message["digest"],
        "fact_revision": 1,
        "decision": "approved",
        "decided_at": "2026-10-03T20:10:00Z",
        "owner_context": {
            "owner_id": TENANT,
            "device_id": "demo-android-001",
            "unlock": "pin",
            "session_id": "local-session-0001",
        },
    }
    write(FIX / "good" / "approval_send_message.json", approval)

    # Bad fixtures: each must be rejected for the stated reason.
    bad = []
    tampered = dict(send_message)
    tampered["payload"] = {**send_message["payload"], "body": send_message["payload"]["body"] + " Bure!"}
    bad.append(("digest_mismatch_after_edit", tampered, "digest no longer matches the content: edited after approval"))
    float_money = json.loads(json.dumps(record_payment))
    float_money["payload"]["money"] = {"amount_minor": 2000.5, "currency": "KES", "exponent": 2}
    bad.append(("float_money", float_money, "money must be an integer in minor units"))
    unknown = dict(send_message)
    unknown["priority"] = "high"
    bad.append(("unknown_field", unknown, "unknown members are rejected before hashing"))
    ts = dict(send_message)
    ts["created_at"] = "2026-10-03T20:00:00+00:00"
    bad.append(("timestamp_not_utc_z", ts, "timestamps are RFC 3339 UTC with a literal Z"))
    quote_altered = json.loads(json.dumps(send_message))
    quote_altered["evidence"][0]["quote"] = "maelekezo ya kufika yalikuwa rahisi"
    quote_altered = with_digest(quote_altered)
    bad.append(("evidence_quote_altered", quote_altered, "schema-valid but the quote is not the exact UTF-8 slice: evidence validation must reject it"))
    no_owner_ctx = dict(approval)
    del no_owner_ctx["owner_context"]
    bad.append(("approval_without_owner_context", no_owner_ctx, "hash equality is not owner authentication"))
    for name, data, reason in bad:
        write(FIX / "bad" / f"{name}.json", {"synthetic": True, "expect": "reject", "reason": reason, "input": data})

    vectors = []
    for env in (send_message, record_payment):
        body = {k: v for k, v in env.items() if k != "digest"}
        vectors.append({
            "name": env["kind"],
            "envelope_without_digest": body,
            "canonical_utf8_hex": canonical_bytes(body).hex(),
            "domain": ENVELOPE_DOMAIN.decode(),
            "digest": env["digest"],
        })
    write(FIX / "digest-vectors.json", {"synthetic": True, "note": NOTE, "vectors": vectors})
    print(f"wrote fixtures under {FIX}")


if __name__ == "__main__":
    main()
