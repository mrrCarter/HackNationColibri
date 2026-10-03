# Claude Domain — primary builder packet

Suggested room alias: Claude Domain. Use the actual identity granted to your session.

## Your mission

Make Sauti's business truth and owner control dependable. Own packages/core: facts, evidence validation, deterministic counts, action envelopes, exact approval, queue transitions and calendar constraints. You are a builder, not only an architect: implement the portable domain package and meaningful fault tests.

Carther's PC has his GitHub access. AIdenID may already contain scoped authorization/receipts/revocation, FencesNGates may contain validated facts and constrained proposals, and Senti may contain event/idempotency patterns. Inspect actual source through Platform's inventory; preserve attribution, licensing and source instructions. Existing private components are not verified by this packet.

## First deliverable

Within the initial contract pass, publish a small schema with Platform. Start from contracts/action-envelope.schema.json and pseudocode/core.ts in this kit; they are draft design aids, not working implementations. Define field names, versions, timestamps, UTF-8 offsets, integer money/currency units, authority and error semantics. Include a minimal good fixture and bad fixtures. Mobile must implement against one contract, not infer your intentions from chat.

## Implementation scope

Separate model-assisted extraction from deterministic authority. The model can label topics and suggest candidate evidence. It cannot create owner facts, counts, approvals, capacity, money operations or delivery receipts. Validate each cited ID and span; count unique messages by code. A semantic support judgement still needs the independent evaluation set; exact spans alone are insufficient.

Implement an explicit ask-a-person result for missing facts, ambiguous dates/parties, contradictory reviews, unsupported language and structured-output failures. Recommendations are bounded templates, visibly prospective. Keep owner facts versioned and source messages immutable. Treat all imported content as untrusted, including adversarial approval instructions.

Bind the action to recipient, channel, exact payload, validity, fact revision, evidence snapshot and rendered preview. Canonicalize using a vetted RFC 8785 implementation; integer fields only where appropriate, finite values, explicit schema validation, domain-separated SHA-256. Hash equality is not owner authentication: require the trusted local owner context. Commit approval and outbox in one transaction with a revision check. Changes void approval.

Define states that include rejected, expired, revoked, cancelled, failed and send_unknown as well as proposed/approved/queued/sending/sent/delivered. Distinguish business status from transport status. A timeout after possible send cannot be classed as a definite failure or retried blindly. A cancellation after provider acceptance cannot recall the send.

Do not confirm the last booking slot independently on two offline devices. Phase 4 must choose one authoritative calendar or explicitly preallocated capacity; unsynchronized requests are tentative until reconciled. Payment deposits are owner-confirmed records only. Batch template approvals bind exact actions and schedule; dynamic future delegation is a separately authorized Phase 5 capability.

## Required meaningful tests

1. Changed recipient, payload, fact revision, render locale or expiry invalidates approval.
2. Force-close/crash boundary cannot create an approved action with missing durable outbox or vice versa.
3. Duplicate import does not inflate counts; nonexistent ID and altered quote fail validation.
4. Malicious review instructions do not authorize a send or introduce a fact.
5. Relative/ambiguous date or unknown currency unit requires clarification.
6. A provider acceptance timeout leads to send_unknown; callback duplicates and late callbacks do not regress state.
7. Two devices requesting the last slot cannot both become confirmed through the authoritative reconciliation path.
8. Clock rollback, expiry and revocation cannot silently extend authority.

Nat independently provides expected outcomes and a held-out fixture set. Coordinate without tailoring tests only to your implementation. Platform cross-reviews policy/tenant/send boundaries; you review Platform's ledger and deduplication behavior. Carther resolves material product-policy ambiguity, not every routine coding choice.

## Handoff

Commit your core/tests, publish the exact contract revision and a brief usage example. Include actual test commands/results and unresolved assumptions. No claims of verified Swahili or real telecom performance from schema tests. In Senti, ACK/claim once; send only a blocker, contract decision or final handoff, each linked to a small artifact. Do not broadcast full deliberation or wake all builders for research notes.
