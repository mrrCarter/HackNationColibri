/**
 * Outbox dispatch rules. The core decides; the host's worker performs the
 * provider call and persists the result. Every function here is pure.
 *
 * Queued means not dispatched. Sent means the provider accepted. Delivered
 * needs an authenticated receipt. A timeout after a possible acceptance is
 * send_unknown and is reconciled, never retried blindly. Receipts never move a
 * state backwards, and a cancel that arrives after acceptance cannot recall it.
 */

import type { StoredAction } from "./approval.js";
import { type ClockReading, formatTimestamp, isExpired } from "./clock.js";
import { envelopeDigest } from "./envelope.js";
import type { Sha256 } from "./canon.js";
import { assertTransport, receiptAllowed, recallPossible } from "./states.js";

export type DispatchHold =
  | "not_approved"
  | "revoked"
  | "expired"
  | "clock_suspect"
  | "fact_revision_changed"
  | "digest_mismatch"
  | "needs_reconcile"
  | "already_accepted"
  | "terminal";

export type DispatchDecision = { ok: true; simulated: boolean } | { ok: false; hold: DispatchHold; detail: string };

export interface DispatchCheckInput {
  action: StoredAction;
  clock: ClockReading;
  currentFactRevision: number;
  sha256: Sha256;
}

/** Re-check authority immediately before a provider call. Expiry and revocation are checked at dispatch, not only at approval. */
export function checkDispatch(input: DispatchCheckInput): DispatchDecision {
  const { action, clock } = input;
  const env = action.envelope;
  if (action.business !== "approved") return { ok: false, hold: "not_approved", detail: `business state ${action.business}` };
  if (action.revoked_at) return { ok: false, hold: "revoked", detail: `revoked at ${action.revoked_at}` };
  if (action.transport === "sent" || action.transport === "delivered") return { ok: false, hold: "already_accepted", detail: "provider already accepted this action" };
  if (action.transport === "sending" || action.transport === "send_unknown") {
    return { ok: false, hold: "needs_reconcile", detail: "a previous attempt may have been accepted; look the status up or hold for the owner" };
  }
  if (action.transport !== "queued") return { ok: false, hold: "terminal", detail: `transport state ${action.transport}` };
  if (clock.suspect) return { ok: false, hold: "clock_suspect", detail: "device clock behind its high-water mark; dispatch held" };
  if (isExpired(env.valid_until, clock.effectiveMs)) return { ok: false, hold: "expired", detail: `valid_until ${env.valid_until} passed` };
  if (env.fact_revision !== input.currentFactRevision) {
    return { ok: false, hold: "fact_revision_changed", detail: `built on ${env.fact_revision}, current ${input.currentFactRevision}; held for re-approval` };
  }
  if (envelopeDigest(env, input.sha256) !== env.digest) return { ok: false, hold: "digest_mismatch", detail: "stored content no longer matches its digest" };
  return { ok: true, simulated: env.recipient.channel === "simulated" };
}

/** Record the attempt BEFORE the provider call, so a crash mid-call leaves `sending`, which forces reconciliation. */
export function beginDispatch(action: StoredAction): StoredAction {
  assertTransport(action.transport, "sending");
  return { ...action, transport: "sending", attempts: action.attempts + 1 };
}

/** Provider accepted. For the simulated channel the reference is prefixed so the UI can never show it as a real send. */
export function recordAcceptance(action: StoredAction, providerRef: string): StoredAction {
  assertTransport(action.transport, "sent");
  const simulated = action.envelope.recipient.channel === "simulated";
  const ref = simulated && !providerRef.startsWith("simulated:") ? `simulated:${providerRef}` : providerRef;
  return { ...action, transport: "sent", provider_ref: ref };
}

/**
 * The provider call ended without a usable acceptance.
 * `provenNotAccepted` must be true only for errors that prove nothing was sent
 * (connection refused before the request, a 4xx with no message id). Anything
 * ambiguous (timeout, 5xx after the body went out, lost response) is send_unknown.
 */
export function recordFailure(action: StoredAction, provenNotAccepted: boolean): StoredAction {
  const to = provenNotAccepted ? "failed" : "send_unknown";
  assertTransport(action.transport, to);
  return { ...action, transport: to };
}

export const DEFAULT_RETRY_BUDGET = 5;

/** Bounded retry with the same idempotency key. Only from a PROVEN failure. */
export function retry(action: StoredAction, budget: number = DEFAULT_RETRY_BUDGET): StoredAction | null {
  if (action.transport !== "failed") return null;
  if (action.attempts >= budget) return null;
  assertTransport(action.transport, "queued");
  return { ...action, transport: "queued" };
}

export interface ProviderReceipt {
  /** Provider's own event id, unique per callback. Used to drop duplicates. */
  provider_event_id: string;
  provider_ref: string;
  status: "sent" | "delivered" | "failed_proven";
}

export interface ReceiptOutcome {
  action: StoredAction;
  applied: boolean;
  reason: "applied" | "duplicate" | "wrong_reference" | "would_regress" | "not_approved";
}

/**
 * Apply an authenticated provider receipt. Deduplicated by provider_event_id,
 * monotonic by rank, and a receipt never resolves anything except send_unknown
 * and the sent -> delivered step. Authentication of the callback is the host's
 * job and must happen before this is called.
 */
export function applyReceipt(action: StoredAction, receipt: ProviderReceipt, seenEventIds: Set<string>): ReceiptOutcome {
  if (seenEventIds.has(receipt.provider_event_id)) return { action, applied: false, reason: "duplicate" };
  seenEventIds.add(receipt.provider_event_id);
  if (action.business !== "approved") return { action, applied: false, reason: "not_approved" };
  if (action.provider_ref !== null && action.provider_ref !== receipt.provider_ref) return { action, applied: false, reason: "wrong_reference" };
  if (receipt.status === "failed_proven") {
    if (action.transport === "send_unknown") return { action: { ...action, transport: "failed" }, applied: true, reason: "applied" };
    return { action, applied: false, reason: "would_regress" };
  }
  if (!receiptAllowed(action.transport, receipt.status)) return { action, applied: false, reason: "would_regress" };
  return { action: { ...action, transport: receipt.status, provider_ref: action.provider_ref ?? receipt.provider_ref }, applied: true, reason: "applied" };
}

export interface CancelOutcome {
  action: StoredAction;
  recalled: boolean;
  /** Audit text for the host. When not recalled, the UI must say the send cannot be undone. */
  note: "revoked_before_acceptance" | "cancel_requested_after_acceptance" | "nothing_to_cancel";
}

/** Owner revokes an approved action. Guaranteed only before provider acceptance. */
export function requestCancel(action: StoredAction, clock: ClockReading): CancelOutcome {
  if (action.business !== "approved") return { action, recalled: false, note: "nothing_to_cancel" };
  if (recallPossible(action.transport)) {
    return {
      action: { ...action, business: "revoked", revoked_at: formatTimestamp(clock.effectiveMs) },
      recalled: true,
      note: "revoked_before_acceptance",
    };
  }
  return { action, recalled: false, note: "cancel_requested_after_acceptance" };
}

/** What the UI may say. Never "sent" for queued, never "delivered" for sent, never a real send for simulated. */
export function transportLabel(action: StoredAction): "queued_waiting_for_signal" | "sending" | "sent_simulated" | "sent" | "delivered" | "send_unknown" | "failed" | "not_sent" {
  if (action.business !== "approved") return "not_sent";
  switch (action.transport) {
    case "queued":
      return "queued_waiting_for_signal";
    case "sending":
      return "sending";
    case "sent":
      return action.envelope.recipient.channel === "simulated" ? "sent_simulated" : "sent";
    case "delivered":
      return "delivered";
    case "send_unknown":
      return "send_unknown";
    case "failed":
      return "failed";
    case "none":
      return "not_sent";
  }
}
