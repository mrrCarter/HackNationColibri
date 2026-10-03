/**
 * Exact approval. Noor approves one envelope, identified by its digest, with a
 * trusted local owner context. The decision is a pure function; persistence
 * happens through a transaction port so that envelope state, approval record
 * and outbox row are written together or not at all.
 *
 * Hash equality is not owner authentication: the owner context must come from
 * the host's local authentication (PIN, biometric), never from text the model
 * or a tourist produced.
 */

import { APPROVAL_DOMAIN, digest, type Sha256 } from "./canon.js";
import { type ClockReading, formatTimestamp, isExpired } from "./clock.js";
import { type ActionEnvelope, envelopeDigest } from "./envelope.js";
import { type BusinessState, type TransportState } from "./states.js";
import { utf8Encode } from "./utf8.js";

export const APPROVAL_SCHEMA = "sauti.approval_record";
export const APPROVAL_SCHEMA_VERSION = "1.0.0";

export const UNLOCK_METHODS = ["pin", "biometric", "voice_confirm", "text_confirm"] as const;
export type UnlockMethod = (typeof UNLOCK_METHODS)[number];

export interface OwnerContext {
  owner_id: string;
  device_id: string;
  unlock: UnlockMethod;
  session_id: string;
}

/** What the host's local authentication vouches for. Comes from the tenant's trusted-device registry, not from the request. */
export interface TrustedOwner {
  owner_id: string;
  trusted_device_ids: ReadonlySet<string>;
  allowed_unlock: ReadonlySet<UnlockMethod>;
}

export interface ApprovalRecord {
  schema: typeof APPROVAL_SCHEMA;
  schema_version: typeof APPROVAL_SCHEMA_VERSION;
  approval_id: string;
  action_id: string;
  digest: string;
  fact_revision: number;
  decision: "approved" | "rejected";
  decided_at: string;
  owner_context: OwnerContext;
}

export interface StoredAction {
  envelope: ActionEnvelope;
  business: BusinessState;
  transport: TransportState;
  /** Set when the owner revoked after approval. Terminal. */
  revoked_at: string | null;
  /** Provider reference once accepted; null before. */
  provider_ref: string | null;
  attempts: number;
}

export interface OutboxRow {
  action_id: string;
  tenant_id: string;
  idempotency_key: string;
  digest: string;
  channel: ActionEnvelope["recipient"]["channel"];
  address: string;
  /** The exact payload the transport will carry: canonical JSON of envelope.payload. */
  payload_json: string;
  created_at: string;
}

export type ApprovalFailure =
  | "invalid_envelope"
  | "not_proposed"
  | "revoked"
  | "digest_mismatch"
  | "rendered_digest_mismatch"
  | "fact_revision_mismatch"
  | "expired"
  | "clock_suspect"
  | "owner_mismatch"
  | "device_not_trusted"
  | "unlock_not_allowed"
  | "tenant_mismatch";

export type ApproveResult =
  | { ok: true; action: StoredAction; approval: ApprovalRecord; outbox: OutboxRow }
  | { ok: false; reason: ApprovalFailure; detail: string };

export interface ApproveInput {
  action: StoredAction;
  /** Digest of what was actually rendered to the owner, computed by the host from the rendered envelope. */
  renderedDigest: string;
  currentFactRevision: number;
  owner: OwnerContext;
  trusted: TrustedOwner | null;
  clock: ClockReading;
  approvalId: string;
  sha256: Sha256;
}

/** Stable per-provider key: same action + same content always yields the same key, so a retry can never double-send. */
export function idempotencyKey(tenantId: string, actionId: string, envelopeDigestHex: string, sha256: Sha256): string {
  return sha256(utf8Encode(`${tenantId}|${actionId}|${envelopeDigestHex}`));
}

function fail(reason: ApprovalFailure, detail: string): ApproveResult {
  return { ok: false, reason, detail };
}

/** Pure decision. Every check the approval transaction must make, in order. */
export function decideApproval(input: ApproveInput): ApproveResult {
  const { action, owner, trusted, clock, sha256 } = input;
  const env = action.envelope;
  if (action.business !== "proposed") return fail("not_proposed", `business state is ${action.business}`);
  if (action.revoked_at) return fail("revoked", `revoked at ${action.revoked_at}`);
  const contentDigest = envelopeDigest(env, sha256);
  if (contentDigest !== env.digest) return fail("digest_mismatch", "stored envelope content does not match its digest: it was edited");
  if (input.renderedDigest !== env.digest) return fail("rendered_digest_mismatch", "the owner was shown something other than this envelope");
  if (env.fact_revision !== input.currentFactRevision) {
    return fail("fact_revision_mismatch", `envelope built on fact revision ${env.fact_revision}, current is ${input.currentFactRevision}`);
  }
  if (clock.suspect) return fail("clock_suspect", "device clock is behind its own high-water mark; approval held");
  if (isExpired(env.valid_until, clock.effectiveMs)) return fail("expired", `valid_until ${env.valid_until} has passed`);
  if (!trusted) return fail("owner_mismatch", "no trusted owner registered for this tenant");
  if (trusted.owner_id !== owner.owner_id || owner.owner_id !== env.tenant_id) return fail("owner_mismatch", "owner context does not belong to this tenant's owner");
  if (!trusted.trusted_device_ids.has(owner.device_id)) return fail("device_not_trusted", `device ${owner.device_id} is not in the trusted list`);
  if (!trusted.allowed_unlock.has(owner.unlock)) return fail("unlock_not_allowed", `unlock method ${owner.unlock} is not allowed`);

  const decidedAt = formatTimestamp(clock.effectiveMs);
  const approval: ApprovalRecord = {
    schema: APPROVAL_SCHEMA,
    schema_version: APPROVAL_SCHEMA_VERSION,
    approval_id: input.approvalId,
    action_id: env.action_id,
    digest: env.digest,
    fact_revision: env.fact_revision,
    decision: "approved",
    decided_at: decidedAt,
    owner_context: { ...owner },
  };
  const outbox: OutboxRow = {
    action_id: env.action_id,
    tenant_id: env.tenant_id,
    idempotency_key: idempotencyKey(env.tenant_id, env.action_id, env.digest, sha256),
    digest: env.digest,
    channel: env.recipient.channel,
    address: env.recipient.address,
    payload_json: JSON.stringify(env.payload),
    created_at: decidedAt,
  };
  const next: StoredAction = { ...action, business: "approved", transport: "queued" };
  return { ok: true, action: next, approval, outbox };
}

export function approvalRecordDigest(record: ApprovalRecord, sha256: Sha256): string {
  return digest(APPROVAL_DOMAIN, record, sha256);
}

/** Owner says no. Terminal; no outbox row is ever written. */
export function decideRejection(action: StoredAction, owner: OwnerContext, clock: ClockReading, approvalId: string): { action: StoredAction; approval: ApprovalRecord } | null {
  if (action.business !== "proposed") return null;
  const env = action.envelope;
  return {
    action: { ...action, business: "rejected" },
    approval: {
      schema: APPROVAL_SCHEMA,
      schema_version: APPROVAL_SCHEMA_VERSION,
      approval_id: approvalId,
      action_id: env.action_id,
      digest: env.digest,
      fact_revision: env.fact_revision,
      decision: "rejected",
      decided_at: formatTimestamp(clock.effectiveMs),
      owner_context: { ...owner },
    },
  };
}

// ---------------------------------------------------------------- persistence port

export interface AuditEntry {
  at: string;
  action_id: string;
  event: string;
  detail?: string;
}

/** One transaction. The host implements this over SQLCipher (BEGIN IMMEDIATE ... COMMIT) or PostgreSQL. */
export interface ApprovalTx {
  getAction(actionId: string): Promise<StoredAction | null>;
  getCurrentFactRevision(tenantId: string): Promise<number>;
  getTrustedOwner(tenantId: string): Promise<TrustedOwner | null>;
  /** Must fail on a second record for the same action_id. */
  insertApproval(record: ApprovalRecord): Promise<void>;
  /** Must fail on a duplicate idempotency_key. */
  insertOutbox(row: OutboxRow): Promise<void>;
  updateAction(action: StoredAction): Promise<void>;
  appendAudit(entry: AuditEntry): Promise<void>;
}

export interface ApprovalStore {
  /** Runs fn atomically: if fn throws, nothing it wrote persists. */
  transaction<T>(fn: (tx: ApprovalTx) => Promise<T>): Promise<T>;
}

export class ApprovalRefused extends Error {
  override readonly name = "ApprovalRefused";
  constructor(readonly reason: ApprovalFailure, readonly detail: string) {
    super(`${reason}: ${detail}`);
  }
}

export interface ApproveExactRequest {
  actionId: string;
  renderedDigest: string;
  owner: OwnerContext;
  clock: ClockReading;
  approvalId: string;
  sha256: Sha256;
}

/**
 * Approve inside one transaction. Returns the refusal instead of throwing so the
 * UI can explain it; the transaction itself is rolled back on any refusal because
 * nothing is written before the decision passes.
 */
export async function approveExact(store: ApprovalStore, req: ApproveExactRequest): Promise<ApproveResult> {
  return store.transaction(async (tx) => {
    const action = await tx.getAction(req.actionId);
    if (!action) return fail("invalid_envelope", `no action ${req.actionId}`);
    const [currentFactRevision, trusted] = await Promise.all([
      tx.getCurrentFactRevision(action.envelope.tenant_id),
      tx.getTrustedOwner(action.envelope.tenant_id),
    ]);
    const result = decideApproval({ action, renderedDigest: req.renderedDigest, currentFactRevision, owner: req.owner, trusted, clock: req.clock, approvalId: req.approvalId, sha256: req.sha256 });
    if (!result.ok) {
      await tx.appendAudit({ at: formatTimestamp(req.clock.effectiveMs), action_id: req.actionId, event: "approval_refused", detail: `${result.reason}: ${result.detail}` });
      return result;
    }
    await tx.insertApproval(result.approval);
    await tx.insertOutbox(result.outbox);
    await tx.updateAction(result.action);
    await tx.appendAudit({ at: result.approval.decided_at, action_id: req.actionId, event: "approval_and_outbox_committed" });
    return result;
  });
}
