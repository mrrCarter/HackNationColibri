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
import { sealEnvelope, verifyEnvelope, approveExact, observeClock, checkDispatch,
         beginDispatch, recordAcceptance, recordFailure, applyReceipt, requestCancel,
         validateEvidence, summarizeThemes } from "@sauti/core";

// 1. Build a proposal. Code fills every field; the model only suggested spans and a template.
const sealed = sealEnvelope(bodyWithoutDigest, sha256);         // validates, then sets digest
if (!sealed.ok) show(sealed.errors);                            // never hash an invalid envelope

// 2. Render the card from the envelope and hash what was rendered.
const renderedDigest = envelopeDigest(renderedEnvelope, sha256); // must equal sealed.value.digest

// 3. Noor taps approve, after local owner unlock.
const clock = observeClock(persistedClockState, Date.now());
const result = await approveExact(store, { actionId, renderedDigest, owner, clock, approvalId: uuid(), sha256 });
// result.ok === false carries an enumerated reason: rendered_digest_mismatch, fact_revision_mismatch,
// expired, clock_suspect, device_not_trusted, unlock_not_allowed, ... Show it; never retry blindly.

// 4. Worker, later, with signal.
const check = checkDispatch({ action, clock, currentFactRevision, sha256 });
if (!check.ok) hold(check.hold);                                 // expired / revoked / fact_revision_changed / needs_reconcile
let a = beginDispatch(action);                                   // persist BEFORE the provider call
try { a = recordAcceptance(a, providerRef); }                   // sent (simulated channel gets a "simulated:" prefix)
catch (e) { a = recordFailure(a, provesNoAcceptance(e)); }      // failed (retry with same key) or send_unknown (reconcile)

// 5. Receipts: authenticated by the host first, then
const out = applyReceipt(a, receipt, seenProviderEventIds);     // duplicate / would_regress / wrong_reference are ignored and audited
```

## Evidence

```ts
const report = validateEvidence(items, sources, sha256);        // exact UTF-8 byte spans, hash of the immutable original
const themes = summarizeThemes(tagged, sources, sha256);        // unique COMMENT counts; <3 insufficient; conflicting; one dissent named
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
| `evidence.ts` | span validation, unique counts, theme verdicts |
| `calendar.ts` | slot reconciliation (at most the remaining capacity, tentative offline requests), absolute appointments |

## Not in this package, on purpose

Persistence, encryption, UI, model inference, translation, provider adapters, the sync wire format (Platform's contract). Payments and listings are later phases; the envelope kinds exist so the schema need not change, the workflows do not.
