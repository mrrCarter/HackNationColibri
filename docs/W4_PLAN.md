# W4 plan: manage confirmed visits

Owner: fable-5.1-nav (Claude Fable 5.1). Pair/reviewer: codex. Assigned by Cosme in the team room (#47450). Will adapt to Carter's lane spec when it lands.

## Scope (CLAUDE.md section 5, W4)

1. Noor says "Thomas amelipa" (Thomas paid). The agent works out which booking she means, reads it back, and only after her explicit "ndiyo" does code record the deposit.
2. A scheduler PREPARES two kinds of messages, never sends them:
   - day-before directions, from `farm_sheet.directions_sw` (read-only; W1 owns it),
   - after-visit review request.
3. Noor approves the prepared messages as a batch. Approved items are QUEUED in the outbox. Sending is the transport layer's job (W2/W5), not W4's.

The agent never moves money. W4 records that Noor said a payment happened; it talks to no mobile-money API.

## Boundaries held in code, not prompts

- `record_payment`, `approve_batch` are "needs Noor's yes" tools (CLAUDE.md section 6). Each approval is tied to a proposal id AND a content hash. Content change voids the approval.
- No LLM in this lane's core path. Name matching, amounts, dates, templates are code. Qwen may later adapt message wording, as a PROPOSAL only.
- Fail-safes: no matching booking -> "sina uhakika, muulize mtu" and nothing recorded. Two or more matches -> ask which one (keypad 1/2/3). Unclear yes -> never a yes. Missing `directions_sw` -> no directions message, Noor is told to add directions in W1.
- Scheduler is idempotent: one proposal per (booking, kind). Re-running it, or restarting mid-batch, never duplicates a message (unique idempotency key in the outbox).

## Dialog (Swahili, code-rendered)

```
Noor  > Thomas amelipa elfu mbili
Sauti > Thomas, ziara Jumamosi tarehe nne Oktoba, watu wawili.
        Niandike malipo ya shilingi elfu mbili? Ni sawa?
Noor  > ndiyo
Sauti > Nimeandika. Thomas amelipa shilingi elfu mbili kati ya elfu nne.
```

- Payment cue: a token with the stem "lip" (amelipa, kalipa, alilipa, malipo) or "paid".
- Name: remaining tokens matched against visitor names of open bookings, case-insensitive, one edit tolerated (Whisper misspells names).
- Amount: `sw.parse_amount`; when absent the agent asks "Shilingi ngapi?" and never assumes.
- Expected total = price_per_person_kes x party_size, computed by code, read back for information only.

Batch approval:

```
Sauti > Kesho: Thomas, Anna wanakuja, nimeandaa maelekezo. Jana: Peter alitembelea, nimeandaa ombi la maoni.
        Jumbe tatu. Nizipange zote zitumwe? Ni sawa?
Noor  > ndiyo        -> all three APPROVED then QUEUED
Noor  > hapana       -> nothing queued; agent offers to go one by one
```

## Storage W4 needs (coordinate with W2 before adding)

W4 reads `bookings` and writes `payments`. It creates proposals and outbox rows through the shared core.

| Table | Owner | W4 use |
|---|---|---|
| `bookings` (visitor_name, contact, channel, language, visit_date, party_size, state) | W2 | read; move state CONFIRMED -> DEPOSIT_PAID |
| `proposals` (id, kind, booking_id, batch_id, content JSON, content_hash, state) | shared core | kinds `record_payment`, `directions`, `review_request` |
| `approvals` (proposal_id, content_hash, approved_at, source) | shared core | one row per Noor yes |
| `outbox` (proposal_id, idempotency_key UNIQUE, to, channel, language, body, state) | shared core | QUEUED rows from approve_batch |
| `payments` (booking_id, proposal_id, amount_kes, recorded_at, note) | **W4** | insert only after approval |

Functions W4 calls from the shared core (`sauti/storage/states.py`, `sauti/workflows/outbox.py`):

- `create_proposal(conn, kind, content, booking_id=None, batch_id=None) -> Proposal`
- `approve(conn, proposal_id, content_hash) -> Proposal` (raises on hash mismatch or wrong state)
- `queue(conn, proposal) -> OutboxItem` (idempotency_key = proposal id + content hash)

**Coordination.** W5 (cosme-claude) has the same dependency and offered to own the shared core if W2 has nothing pushed (#47451). W4 builds against the three calls above with a fake core in its tests, and wires the real one the moment it is on a branch. W4 does not ship its own core unless the room asks for it: one core for W2, W4 and W5, not two.

## Files

- `sauti/workflows/visits.py`: payment dialog, scheduler (`prepare_visit_messages`), batch approval. One workflow, one file.
- `sauti/storage/schema.sql`: `payments` table only, appended. Other tables via the shared core.
- `tests/test_visits.py`: see below. Contributions to `test_policy.py`, `test_states.py`, `test_restart.py` if the fallback ships.
- `scripts/seed_demo_data.py`: synthetic bookings (marked synthetic) so the W4 demo runs in airplane mode.
- Entry point for the demo: `python -m sauti.workflows.visits --today 2026-10-04` (text channel), voice later through `noor_voice` once W6 routing exists.

## Tests (in priority order)

1. No payment row, no state change, without an approval tied to the proposal id and hash.
2. Approval voided when the proposal content changes between read-back and yes.
3. Scheduler run twice on the same day prepares each message once; a restart between approve and queue produces no duplicate outbox row.
4. Unknown name -> nothing recorded, "not sure" said. Two matching names -> the agent asks which.
5. Missing amount -> the agent asks; unclear answers are never a yes.
6. Missing directions_sw -> no directions proposal, Noor told.
7. Batch "hapana" -> outbox unchanged.

## Out of scope for W4

Sending (transport), translation of the prepared messages (NLLB, W2), creating bookings (W2), review ingestion (W3), listings (W5), voice routing (W6).
