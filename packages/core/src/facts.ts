/**
 * Owner facts (the farm sheet) and how they change (W3 step 6 -> W5).
 *
 * Facts have revisions. A "try" on a decision card leads to Noor DICTATING
 * the new value in her own words; code parses it into the one field the theme
 * maps to. The change is read back and applied only after her explicit yes to
 * that exact read-back, on the revision it was proposed against: a fact change
 * made elsewhere in between voids it. Applying a change writes the new
 * revision, the approval record and the listing drafts (one per channel, never
 * published) as ONE bundle the host commits in one transaction. No value ever
 * comes from a review, a model or a transcript the owner did not dictate.
 */

import { digest, type Sha256 } from "./canon.js";
import { formatTimestamp } from "./clock.js";
import type { Choice } from "./decisions.js";
import { parseAmount, parseConfirmation, parseHours, timeToString } from "./swahili.js";

export const FACTS_DOMAIN = "sauti.farm_sheet.v1";
export const FACT_CHANGE_DOMAIN = "sauti.fact_change.v1";

export type Weekday = "mon" | "tue" | "wed" | "thu" | "fri" | "sat" | "sun";

/** Mirrors sauti/farm_sheet.py. null = "Noor has not told us". */
export interface FarmSheet {
  price_per_person_kes: number | null;
  capacity_per_tour: number | null;
  days: Weekday[] | null;
  hours: { start: string; end: string } | null;
  directions_sw: string | null;
  inclusions_sw: string[] | null;
}

export type FactField = keyof FarmSheet;

export interface FactRevision {
  revision: number;
  sheet: FarmSheet;
  content_hash: string;
  /** e.g. "w1_voice", "w3_step6", "w1_setup" */
  source: string;
  created_at: string;
}

/** Validated by Nat (eval/w3/README.md). Themes outside this table have no field and go to a person. */
export const THEME_FIELD: Readonly<Record<string, FactField>> = {
  directions: "directions_sw",
  price: "price_per_person_kes",
  timing: "hours",
  food: "inclusions_sw",
};

export function fieldForTheme(theme: string): FactField | null {
  return THEME_FIELD[theme] ?? null;
}

export function factsHash(sheet: FarmSheet, sha256: Sha256): string {
  return digest(FACTS_DOMAIN, sheet, sha256);
}

export function makeRevision(sheet: FarmSheet, revision: number, source: string, nowMs: number, sha256: Sha256): FactRevision {
  return { revision, sheet, content_hash: factsHash(sheet, sha256), source, created_at: formatTimestamp(nowMs) };
}

export type FactValue = FarmSheet[FactField];

export type ParsedValue = { ok: true; value: NonNullable<FactValue> } | { ok: false; reason: "no_readable_value"; detail: string };

/** Code reads the dictated value for a field. Anything unreadable is a refusal, never a guess. */
export function parseDictatedValue(field: FactField, transcript: string): ParsedValue {
  const text = transcript.replace(/\s+/g, " ").trim();
  switch (field) {
    case "price_per_person_kes": {
      const amount = parseAmount(text);
      if (amount === null || amount < 1 || amount > 1_000_000) return { ok: false, reason: "no_readable_value", detail: "no price between 1 and 1,000,000 shillings was said" };
      return { ok: true, value: amount };
    }
    case "capacity_per_tour": {
      const n = parseAmount(text);
      if (n === null || n < 1 || n > 200) return { ok: false, reason: "no_readable_value", detail: "no head count between 1 and 200 was said" };
      return { ok: true, value: n };
    }
    case "hours": {
      const hours = parseHours(text);
      if (!hours) return { ok: false, reason: "no_readable_value", detail: "need a start and an end time, end after start" };
      return { ok: true, value: { start: timeToString(hours.start), end: timeToString(hours.end) } };
    }
    case "directions_sw": {
      const cleaned = text.replace(/[ .,;]+$/g, "");
      if (cleaned.split(" ").length < 3 || cleaned.length > 2000) return { ok: false, reason: "no_readable_value", detail: "directions need at least three words" };
      return { ok: true, value: cleaned };
    }
    case "inclusions_sw": {
      const items = text.split(/,|;|\bpamoja na\b|\bna\b/).map((s) => s.trim().replace(/[ .]+$/g, "")).filter((s) => s.length > 1);
      if (items.length === 0) return { ok: false, reason: "no_readable_value", detail: "no inclusions were said" };
      return { ok: true, value: items };
    }
    case "days":
      return { ok: false, reason: "no_readable_value", detail: "weekday changes are made in farm setup (W1), not from a card" };
  }
}

export interface FactChangeProposal {
  theme: string;
  field: FactField;
  value: NonNullable<FactValue>;
  /** The farm sheet revision the change was proposed against. */
  from_revision: number;
  from_hash: string;
  /** What is read back to Noor before her yes. Template; Experience owns reviewed copy. */
  readback: string;
  digest: string;
}

export type ProposeFactChangeResult =
  | { ok: true; proposal: FactChangeProposal }
  | { ok: false; reason: "no_try_decision" | "no_field_for_theme" | "no_readable_value"; detail: string };

function readback(field: FactField, value: NonNullable<FactValue>): string {
  switch (field) {
    case "price_per_person_kes":
      return `Bei mpya: shilingi ${value as number} kwa kila mgeni. Ni sawa?`;
    case "capacity_per_tour":
      return `Idadi mpya ya wageni: ${value as number} kwa ziara moja. Ni sawa?`;
    case "hours": {
      const h = value as { start: string; end: string };
      return `Saa mpya za ziara: kuanzia ${h.start.slice(0, 5)} hadi ${h.end.slice(0, 5)}. Ni sawa?`;
    }
    case "directions_sw":
      return `Maelekezo mapya: ${value as string}. Ni sawa?`;
    case "inclusions_sw":
      return `Ziara itajumuisha: ${(value as string[]).join(", ")}. Ni sawa?`;
    case "days":
      return `Siku mpya: ${(value as string[]).join(", ")}. Ni sawa?`;
  }
}

/**
 * From Noor's "try" and her dictation to a proposal. The theme must map to a
 * field, the choice must be "try", and the dictation must parse; otherwise
 * nothing is proposed and the caller asks a person.
 */
export function proposeFactChange(input: { theme: string; choice: Choice | null; transcript: string; current: FactRevision }, sha256: Sha256): ProposeFactChangeResult {
  if (input.choice !== "try") return { ok: false, reason: "no_try_decision", detail: "only a recorded try on this card can lead to a fact change" };
  const field = fieldForTheme(input.theme);
  if (!field) return { ok: false, reason: "no_field_for_theme", detail: `theme ${input.theme} has no farm sheet field; ask a person` };
  const parsed = parseDictatedValue(field, input.transcript);
  if (!parsed.ok) return parsed;
  const bound = { theme: input.theme, field, value: parsed.value, from_revision: input.current.revision, from_hash: input.current.content_hash };
  return {
    ok: true,
    proposal: { ...bound, readback: readback(field, parsed.value), digest: digest(FACT_CHANGE_DOMAIN, bound, sha256) },
  };
}

export const LISTING_CHANNELS = ["google_business", "getyourguide", "osm"] as const;
export type ListingChannel = (typeof LISTING_CHANNELS)[number];

export interface ListingDraft {
  channel: ListingChannel;
  field: FactField;
  value: NonNullable<FactValue>;
  from_revision: number;
  /** Always false here: publishing is W5's own approval. */
  published: false;
  draft_id: string;
}

export interface FactChangeApproval {
  proposal_digest: string;
  decided_at: string;
  transcript: string;
}

/** Everything the host writes in ONE transaction: new revision, the approval, the drafts. */
export interface AppliedFactChange {
  revision: FactRevision;
  approval: FactChangeApproval;
  drafts: ListingDraft[];
}

export type ConfirmFactChangeResult =
  | { ok: true; applied: AppliedFactChange }
  | { ok: false; reason: "asr_uncertain" | "no_explicit_yes" | "declined" | "facts_changed"; detail: string };

/**
 * Noor answers the read-back. Only an explicit yes applies the change, and only
 * if the farm sheet is still the revision the change was proposed against.
 */
export function confirmFactChange(
  input: { proposal: FactChangeProposal; transcript: string; asrUncertain?: boolean; current: FactRevision; nowMs: number },
  sha256: Sha256,
): ConfirmFactChangeResult {
  if (input.asrUncertain) return { ok: false, reason: "asr_uncertain", detail: "the recognizer was unsure; read back again" };
  const answer = parseConfirmation(input.transcript);
  if (answer === "no") return { ok: false, reason: "declined", detail: "Noor said no; nothing changes" };
  if (answer !== "yes") return { ok: false, reason: "no_explicit_yes", detail: "unclear is never a yes; read back again" };
  if (input.current.revision !== input.proposal.from_revision || input.current.content_hash !== input.proposal.from_hash) {
    return { ok: false, reason: "facts_changed", detail: `the farm sheet moved from revision ${input.proposal.from_revision} to ${input.current.revision}; propose again` };
  }
  const sheet: FarmSheet = { ...input.current.sheet, [input.proposal.field]: input.proposal.value };
  const revision = makeRevision(sheet, input.current.revision + 1, "w3_step6", input.nowMs, sha256);
  const drafts: ListingDraft[] = LISTING_CHANNELS.map((channel) => ({
    channel,
    field: input.proposal.field,
    value: input.proposal.value,
    from_revision: revision.revision,
    published: false,
    draft_id: digest("sauti.listing_draft.v1", { channel, field: input.proposal.field, revision: revision.revision, hash: revision.content_hash }, sha256),
  }));
  return { ok: true, applied: { revision, approval: { proposal_digest: input.proposal.digest, decided_at: revision.created_at, transcript: input.transcript }, drafts } };
}
