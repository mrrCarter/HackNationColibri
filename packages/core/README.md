# @sauti/core (Claude Domain lane)

Portable TypeScript domain core for Sauti Host. Pure functions plus one transaction port. No network, no model call, no provider SDK, no clock reads of its own: the host passes time, hashing and storage in.

Built against `contracts/` revision 1.0.0. `tests/contract.test.ts` loads the shared fixtures and digest vectors, so this package and the Python reference (`sauti/core/canon.py`) cannot drift apart silently.

```
npm install
npm run typecheck
npx vitest run
```

## What the host (Mobile, sync service) must provide

| Port | Why | Notes |
|---|---|---|
| `Sha256` `(bytes: Uint8Array) => hex` | digests | node:crypto in tests; react-native-quick-crypto or an equivalent native module on the phone. Must be SHA-256 over raw bytes. |
| `ApprovalStore.transaction(fn)` | exact approval | One database transaction (`BEGIN IMMEDIATE` on SQLite/SQLCipher). If `fn` throws, nothing it wrote persists. `insertApproval` must be unique per `action_id`; `insertOutbox` unique per `idempotency_key`. |
| `ClockState.highWaterMs` | monotonic time | Persist the highest wall clock ever observed and feed it to `observeClock` on every read. The reading's `suspect` flag holds approval and dispatch. |
| trusted owner registry | owner authentication | `TrustedOwner` (registered owner id, trusted device ids, allowed unlock methods, max session age, revoked session ids) comes from the device's local authentication, never from request data or model output. `OwnerContext.authenticated_at` is when the session was unlocked; voice/text are confirmations inside it. |
| restart hook | abandoned dispatch | At process start call `recoverAfterRestart` on every `sending` row: it becomes `send_unknown`, to be reconciled, never requeued blindly. |

## Flow

```ts
import { sealEnvelope, envelopeDigest, approveExact, revokeExact, observeClock, checkDispatch,
         beginDispatch, recordAcceptance, recordFailure, recoverAfterRestart, applyReceipt,
         ingestMessages, analyzeFeedback, buildDecisionCards, recordChoice } from "@sauti/core";

// 1. Build a proposal. Code fills every field; the model only suggested spans and a template.
const sealed = sealEnvelope(bodyWithoutDigest, sha256);         // validates, then sets digest
if (!sealed.ok) show(sealed.errors);                            // never hash an invalid envelope

// 2. Render the card from the envelope and hash what was rendered.
const renderedDigest = envelopeDigest(renderedEnvelope, sha256); // must equal sealed.value.digest

// 3. Noor taps approve, after local owner unlock. The request carries NO owner: the store's
//    getOwnerSession(tenant) is read inside the transaction and checked against the trusted registry.
const clock = observeClock(persistedClockState, Date.now(), monotonicNowMs /* optional, trusted elapsed time */);
persist(clock.state);                                            // the high-water mark must survive restarts
const result = await approveExact(store, { actionId, renderedDigest, confirmation: "tap", clock, approvalId: uuid(), sha256 });
// result.ok === false carries an enumerated reason: rendered_digest_mismatch, fact_revision_mismatch,
// expired, clock_suspect, no_owner_session, device_not_trusted, session_stale, ... Show it; never retry blindly.

// 3b. Noor changes her mind: same session rules, same transaction boundary.
const revoked = await revokeExact(store, { actionId, clock });  // recalled only when nothing was in flight

// 4. Worker, later, with signal. Load the IMMUTABLE approval record and outbox row for the action.
const check = checkDispatch({ action, approval, outbox, clock, currentFactRevision, sha256 });
if (!check.ok) hold(check.hold);                                 // expired / revoked / fact_revision_changed / needs_reconcile / digest_mismatch
let a = beginDispatch(action);                                   // persist BEFORE the provider call
try { a = recordAcceptance(a, await provider.send(check.send)); } // send ONLY check.send: the pinned bytes and stable key
catch (e) { a = recordFailure(a, provesNoAcceptance(e)); }      // failed (retry with same key) or send_unknown (reconcile)
// At process start: for every row in `sending`, a = recoverAfterRestart(a)  -> send_unknown, never requeued blindly

// 5. Receipts: authenticated by the host first, then
const out = applyReceipt(a, receipt, seenProviderEventIds);     // pure; duplicate / would_regress / wrong_reference leave both unchanged
persistTogether(out.action, out.seen);                          // action and seen-set in ONE transaction
```

## Feedback to decision (W3 steps 1 to 5)

```ts
const stored = ingestMessages(incoming, sha256, existingSources);          // immutable originals; (source, external_id) duplicates reported
// language id (a separate step) writes SourceText.language; "und"/"unsure" means ask a person
const analysis = analyzeFeedback(modelOutput, sources, sha256, {           // model output read as DATA
  allowedThemes: CATALOGUE, supportedLanguages: new Set(["sw", "en", "de", "fr"]) });
// analysis.themes: unique COMMENT counts (cross-posts folded), supporting side >= 3, dissent named, conflicting -> ask
// analysis.ask_a_person: structured_output_failure / unsupported_language / contradictory_reviews / evidence_invalid
const cards = buildDecisionCards(analysis, sha256);                        // only with enough evidence; digest-bound to the evidence set
const choice = recordChoice({ shownCard, currentCard, transcript, asrUncertain }); // explicit try/reject/ask_someone only; stale card refused
```

Text inside a source is data. Nothing in this package reads instructions from it.

## Files

| Module | Owns |
|---|---|
| `utf8.ts` | strict UTF-8 encode/decode, byte-boundary checks |
| `canon.ts` | RFC 8785 canonical bytes, domain-separated digests, source text hash |
| `envelope.ts` | envelope types, structural validation mirroring the JSON Schema, `sealEnvelope`, `verifyEnvelope` |
| `money.ts` | integer minor units, ISO 4217 exponents, unknown currency = clarification |
| `states.ts` | business and transport states, transitions, monotonic receipt rule, recall rule |
| `clock.ts` | monotonic high-water clock, strict RFC 3339 timestamps, expiry |
| `approval.ts` | `decideApproval` (pure), `approveExact` (transactional), rejection, idempotency key |
| `outbox.ts` | dispatch re-check, sending / sent / failed / send_unknown, receipts, cancel after acceptance, truthful labels |
| `evidence.ts` | span validation, unique comment counts with cross-post folding, theme verdicts, ask-a-person |
| `tagging.ts` | the model's output read as data: label parsing, structured-output failure |
| `ingest.ts` | immutable sources, duplicate detection by (source, external_id) |
| `decisions.ts` | decision cards bound to their evidence, the owner's explicit choice |
| `calendar.ts` | slot reconciliation (at most the remaining capacity, tentative offline requests), absolute appointments |
| `tools/w3-adapter.ts` | Node-only harness for Nat's fixtures; not exported by the package |

## Not in this package, on purpose

Persistence, encryption, UI, model inference, translation, provider adapters, the sync wire format (Platform's contract). Payments and listings are later phases; the envelope kinds exist so the schema need not change, the workflows do not.
