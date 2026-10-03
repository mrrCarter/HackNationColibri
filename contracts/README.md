# Sauti contracts, revision 1.0.0 (DRAFT until Platform and Domain freeze it)

Owner: Claude Domain (`fable-5.1-nav`). Publication and freeze: Codex Platform (`codex`). Consumers: Mobile (`apps/mobile`), Experience (`packages/experience`), the sync service, Nat's failure fixtures.

Files:

| File | What it is |
|---|---|
| `action-envelope.schema.json` | One exact action Noor may approve. Everything the owner sees and everything a transport will do is inside it. |
| `approval-record.schema.json` | Noor's decision on one envelope, bound to its digest and to a trusted owner context. |
| `states.json` | Business and transport states, allowed transitions, monotonic ranks and the rules around them. |
| `fixtures/good/*.json` | Valid envelopes and approval records with correct digests. |
| `fixtures/bad/*.json` | Inputs that must be rejected, each with the expected reason. |
| `fixtures/digest-vectors.json` | Canonical bytes and digests for cross-language tests. A TypeScript or Kotlin implementation must reproduce every vector before it may approve anything. |
| `fixtures/sources/*.json` | Synthetic immutable source texts used by the evidence fixtures. Labeled synthetic. |

## Digest

```
canonical = RFC 8785 (JCS) bytes of the envelope WITHOUT the "digest" member
digest    = sha256( "sauti.action_envelope.v1" || 0x00 || canonical )   as lowercase hex
```

- The envelope is schema-validated BEFORE hashing. Unknown members are a validation error, not ignored.
- No floats anywhere. Money is `{amount_minor, currency, exponent}` with integers only.
- Timestamps are RFC 3339 UTC with a literal `Z` and second precision, so two devices render the same instant the same way.
- The domain prefix keeps an envelope digest from colliding with an approval or source digest of the same bytes. Source texts hash as `sha256("sauti.source_text.v1" || 0x00 || utf8(text))`.
- Hash equality is not owner authentication. It proves the owner saw these bytes; the owner context proves who the owner was.

## Approval, in one transaction

```
BEGIN IMMEDIATE
  action   = load(action_id)                     ; must be business_state = proposed
  assert   action.digest == rendered_digest      ; what the owner was shown
  assert   action.fact_revision == current_fact_revision
  assert   now_effective < action.valid_until    ; monotonic clock, see states.json
  assert   owner_context is trusted              ; device in tenant's trusted list, owner id matches, unlock method allowed
  insert   approval_record (unique per action_id)
  update   business_state = approved, transport_state = queued
  insert   outbox row (idempotency_key = sha256(tenant_id || action_id || digest), unique)
COMMIT
```

Any failed assertion rolls everything back. A crash between the first insert and COMMIT leaves nothing. There is no state where an approval exists without its outbox row, or an outbox row without its approval.

## What voids an approval

Any change to the envelope: recipient, channel, payload text, language, preview text or locale, fact revision, validity window. The change produces a new `action_id` (or a new revision under a new id); the old one is cancelled. The old approval cannot be reused because its digest no longer matches anything that can be dispatched.

A farm sheet change after approval and before dispatch cancels the action at dispatch time (fact revision check) and the owner is asked again.

## Evidence

Every `evidence` item is validated by code, never trusted from the model:

1. `source_id` exists for this tenant.
2. `content_hash` equals the stored hash of the immutable original text.
3. `span.start < span.end <= len(utf8(original))`, both on UTF-8 character boundaries.
4. `quote == utf8(original)[start:end]` exactly.

A failed item is dropped and the finding is marked uncertain. Counts are over unique `source_id`s of valid items only. Fewer than 3 sources on a theme is "not enough feedback to conclude". Positive and negative evidence on the same theme is "conflicting evidence", not a majority claim. Text inside a source that reads like an instruction ("ignore policy, send now") is text; it cannot create a fact, an approval or a send.

## Open questions for the freeze (Platform)

1. `tenant_id` on the device is the operator id; the server derives tenant from the device grant. Confirm the field name stays `tenant_id` in both places.
2. Idempotency key length: full 64 hex, or the first 32 for provider APIs with a 36-character cap.
3. `send_reply` vs `send_message`: keep both kinds, or one kind with `in_reply_to` optional. Domain prefers one kind; the draft keeps both for Experience's wording.
