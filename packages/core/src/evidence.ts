/**
 * Evidence is validated by code, never trusted from the model.
 *
 * The model may suggest a theme, a source id and a span. The core checks that
 * the source exists, that its hash still matches the immutable original, that
 * the span lies on UTF-8 character boundaries and that the quote IS the slice.
 * Counts are over unique valid source ids, and they count comments, not
 * visitors. Text inside a source is data: "ignore policy, send now" is a quote
 * like any other and can create neither a fact, an approval nor a send.
 */

import { type Sha256, sourceTextHash } from "./canon.js";
import type { EvidenceItem } from "./envelope.js";
import { isCharBoundary, utf8DecodeStrict, utf8Encode } from "./utf8.js";

export interface SourceText {
  source_id: string;
  text: string;
  content_hash: string;
}

export type EvidenceReason = "unknown_source" | "hash_mismatch" | "span_out_of_range" | "span_not_on_char_boundary" | "quote_mismatch";

export type EvidenceVerdict = { ok: true } | { ok: false; reason: EvidenceReason };

export function validateEvidenceItem(item: EvidenceItem, sources: ReadonlyMap<string, SourceText>, sha256: Sha256): EvidenceVerdict {
  const source = sources.get(item.source_id);
  if (!source) return { ok: false, reason: "unknown_source" };
  if (sourceTextHash(source.text, sha256) !== source.content_hash || item.content_hash !== source.content_hash) {
    return { ok: false, reason: "hash_mismatch" };
  }
  const raw = utf8Encode(source.text);
  const { start, end } = item.span;
  if (!(0 <= start && start < end && end <= raw.length)) return { ok: false, reason: "span_out_of_range" };
  if (!isCharBoundary(raw, start) || !isCharBoundary(raw, end)) return { ok: false, reason: "span_not_on_char_boundary" };
  const slice = utf8DecodeStrict(raw.subarray(start, end));
  if (slice === null || slice !== item.quote) return { ok: false, reason: "quote_mismatch" };
  return { ok: true };
}

export interface EvidenceReport {
  valid: EvidenceItem[];
  rejected: Array<{ item: EvidenceItem; reason: EvidenceReason }>;
}

export function validateEvidence(items: readonly EvidenceItem[], sources: ReadonlyMap<string, SourceText>, sha256: Sha256): EvidenceReport {
  const report: EvidenceReport = { valid: [], rejected: [] };
  for (const item of items) {
    const v = validateEvidenceItem(item, sources, sha256);
    if (v.ok) report.valid.push(item);
    else report.rejected.push({ item, reason: v.reason });
  }
  return report;
}

/** Comments, not visitors: one source id counts once however many spans cite it. */
export function countUniqueSources(items: readonly EvidenceItem[]): number {
  return new Set(items.map((i) => i.source_id)).size;
}

export type Sentiment = "positive" | "negative" | "neutral";

export interface TaggedItem {
  theme: string;
  sentiment: Sentiment;
  evidence: EvidenceItem;
}

export type ThemeVerdict = "insufficient" | "conflicting" | "supported" | "supported_with_dissent";

export interface ThemeSummary {
  theme: string;
  /** Unique valid source ids. The unit is comments. */
  comment_count: number;
  unit: "comments";
  positive_sources: number;
  negative_sources: number;
  neutral_sources: number;
  verdict: ThemeVerdict;
  /** What the owner should be told when the verdict is not "supported". Keys for Experience to render. */
  note: "not_enough_feedback" | "conflicting_evidence" | "one_dissenting_comment" | null;
  evidence: EvidenceItem[];
  rejected: EvidenceReport["rejected"];
}

export const MIN_SOURCES_PER_THEME = 3;

/**
 * Deterministic theme counts. Per theme: unique valid sources; fewer than 3 is
 * "not enough feedback to conclude"; positive and negative both present with at
 * least two sources on the smaller side is "conflicting"; exactly one dissenting
 * source is reported as dissent, never hidden.
 */
export function summarizeThemes(tagged: readonly TaggedItem[], sources: ReadonlyMap<string, SourceText>, sha256: Sha256): ThemeSummary[] {
  const byTheme = new Map<string, TaggedItem[]>();
  for (const t of tagged) {
    const list = byTheme.get(t.theme) ?? [];
    list.push(t);
    byTheme.set(t.theme, list);
  }
  const out: ThemeSummary[] = [];
  for (const [theme, items] of [...byTheme.entries()].sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))) {
    const report = validateEvidence(items.map((i) => i.evidence), sources, sha256);
    const validIds = new Set(report.valid.map((e) => e.source_id));
    const bySentiment: Record<Sentiment, Set<string>> = { positive: new Set(), negative: new Set(), neutral: new Set() };
    for (const t of items) if (validIds.has(t.evidence.source_id)) bySentiment[t.sentiment].add(t.evidence.source_id);
    const pos = bySentiment.positive.size;
    const neg = bySentiment.negative.size;
    const count = validIds.size;
    let verdict: ThemeVerdict;
    let note: ThemeSummary["note"];
    if (count < MIN_SOURCES_PER_THEME) {
      verdict = "insufficient";
      note = "not_enough_feedback";
    } else if (Math.min(pos, neg) >= 2) {
      verdict = "conflicting";
      note = "conflicting_evidence";
    } else if (Math.min(pos, neg) === 1) {
      verdict = "supported_with_dissent";
      note = "one_dissenting_comment";
    } else {
      verdict = "supported";
      note = null;
    }
    out.push({
      theme,
      comment_count: count,
      unit: "comments",
      positive_sources: pos,
      negative_sources: neg,
      neutral_sources: bySentiment.neutral.size,
      verdict,
      note,
      evidence: dedupeSpans(report.valid),
      rejected: report.rejected,
    });
  }
  return out;
}

function dedupeSpans(items: readonly EvidenceItem[]): EvidenceItem[] {
  const seen = new Set<string>();
  const out: EvidenceItem[] = [];
  for (const i of items) {
    const key = `${i.source_id}|${i.span.start}|${i.span.end}`;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(i);
  }
  return out;
}
