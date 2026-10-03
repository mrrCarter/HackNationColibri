/**
 * Evidence is validated by code, never trusted from the model.
 *
 * The model may suggest a theme, a sentiment, a source id and a span. The core
 * checks that the source exists, that its hash still matches the immutable
 * original, that the span lies on UTF-8 character boundaries and that the quote
 * IS the slice. Theme and sentiment must come from the catalogue. Counts are
 * over unique valid source ids, and they count comments, not visitors. Text
 * inside a source is data: "ignore policy, send now" is a quote like any other
 * and can create neither a fact, an approval nor a send.
 *
 * Anything the core cannot settle becomes an explicit ask-a-person entry, never
 * a guess: malformed model output, a source in a language nobody reviewed,
 * contradictory reviews.
 */

import { type Sha256, sourceTextHash } from "./canon.js";
import type { EvidenceItem } from "./envelope.js";
import { isCharBoundary, utf8DecodeStrict, utf8Encode } from "./utf8.js";

export interface SourceText {
  source_id: string;
  text: string;
  content_hash: string;
  /** BCP 47 tag of the original, when known. Used for the supported-language gate. */
  language?: string;
}

export type EvidenceReason = "unknown_source" | "hash_mismatch" | "span_out_of_range" | "span_not_on_char_boundary" | "quote_mismatch" | "unsupported_language";

export type EvidenceVerdict = { ok: true } | { ok: false; reason: EvidenceReason };

export interface EvidenceOptions {
  /** When given, a source whose language is outside this set is rejected: nobody can check the reading. */
  supportedLanguages?: ReadonlySet<string>;
}

function languageSupported(source: SourceText, options: EvidenceOptions): boolean {
  if (!options.supportedLanguages) return true;
  if (!source.language) return false; // unknown language cannot be called supported
  const primary = source.language.toLowerCase().split("-")[0] ?? "";
  return options.supportedLanguages.has(source.language.toLowerCase()) || options.supportedLanguages.has(primary);
}

export function validateEvidenceItem(item: EvidenceItem, sources: ReadonlyMap<string, SourceText>, sha256: Sha256, options: EvidenceOptions = {}): EvidenceVerdict {
  const source = sources.get(item.source_id);
  if (!source) return { ok: false, reason: "unknown_source" };
  if (sourceTextHash(source.text, sha256) !== source.content_hash || item.content_hash !== source.content_hash) {
    return { ok: false, reason: "hash_mismatch" };
  }
  if (!languageSupported(source, options)) return { ok: false, reason: "unsupported_language" };
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

export function validateEvidence(items: readonly EvidenceItem[], sources: ReadonlyMap<string, SourceText>, sha256: Sha256, options: EvidenceOptions = {}): EvidenceReport {
  const report: EvidenceReport = { valid: [], rejected: [] };
  for (const item of items) {
    const v = validateEvidenceItem(item, sources, sha256, options);
    if (v.ok) report.valid.push(item);
    else report.rejected.push({ item, reason: v.reason });
  }
  return report;
}

/** Comments, not visitors: one source id counts once however many spans cite it. */
export function countUniqueSources(items: readonly EvidenceItem[]): number {
  return new Set(items.map((i) => i.source_id)).size;
}

export const SENTIMENTS = ["positive", "negative", "neutral"] as const;
export type Sentiment = (typeof SENTIMENTS)[number];

/** What the model suggested. Untrusted: theme and sentiment are checked against the catalogue before anything is counted. */
export interface TaggedItem {
  theme: string;
  sentiment: Sentiment | string;
  evidence: EvidenceItem;
}

export type TagReason = "theme_empty" | "theme_not_allowed" | "sentiment_not_allowed";

export type ThemeVerdict = "insufficient" | "conflicting" | "supported" | "supported_with_dissent" | "neutral_mentions";

export type ThemeDirection = "positive" | "negative" | "neutral" | "mixed" | null;

export interface ThemeSummary {
  theme: string;
  /** Unique valid source ids on this theme. The unit is comments. */
  comment_count: number;
  unit: "comments";
  positive_sources: number;
  negative_sources: number;
  neutral_sources: number;
  /** The side the conclusion would rest on, if any. */
  direction: ThemeDirection;
  verdict: ThemeVerdict;
  /** What the owner should be told when the verdict is not "supported". Keys for Experience to render. */
  note: "not_enough_feedback" | "conflicting_evidence" | "one_dissenting_comment" | "no_clear_opinion" | null;
  evidence: EvidenceItem[];
  rejected: EvidenceReport["rejected"];
}

export type AskAPersonReason = "structured_output_failure" | "unsupported_language" | "contradictory_reviews" | "evidence_invalid";

export interface AskAPerson {
  reason: AskAPersonReason;
  detail: string;
  /** Themes or source ids concerned, so the question can be specific. */
  about: string[];
}

export interface ThemeReport {
  themes: ThemeSummary[];
  /** Model suggestions dropped before counting, with the reason. Never silently. */
  rejected_tags: Array<{ item: TaggedItem; reason: TagReason }>;
  /** Explicit questions for a human. Empty means the counts above can be shown as they are. */
  ask_a_person: AskAPerson[];
}

export interface SummaryOptions extends EvidenceOptions {
  /** The reviewed action catalogue's themes. When given, any other theme is rejected, not counted. */
  allowedThemes?: ReadonlySet<string>;
}

/** Minimum unique comments on the SUPPORTING side before a direction may be stated. */
export const MIN_SOURCES_PER_THEME = 3;

function isSentiment(value: unknown): value is Sentiment {
  return typeof value === "string" && (SENTIMENTS as readonly string[]).includes(value);
}

/**
 * Deterministic theme counts. The supporting side (positive or negative) needs
 * at least 3 unique comments before a direction is stated. Two or more comments
 * on the other side is "conflicting"; exactly one is reported as dissent, never
 * hidden. Neutral-only mentions are shown as mentions with no opinion. Returns
 * themes only; use summarizeThemesReport for dropped tags and ask-a-person.
 */
export function summarizeThemes(tagged: readonly TaggedItem[], sources: ReadonlyMap<string, SourceText>, sha256: Sha256, options: SummaryOptions = {}): ThemeSummary[] {
  return summarizeThemesReport(tagged, sources, sha256, options).themes;
}

export function summarizeThemesReport(tagged: readonly TaggedItem[], sources: ReadonlyMap<string, SourceText>, sha256: Sha256, options: SummaryOptions = {}): ThemeReport {
  const byTheme = new Map<string, TaggedItem[]>();
  const rejectedTags: ThemeReport["rejected_tags"] = [];
  for (const t of tagged) {
    if (typeof t.theme !== "string" || t.theme.trim() === "") {
      rejectedTags.push({ item: t, reason: "theme_empty" });
      continue;
    }
    if (options.allowedThemes && !options.allowedThemes.has(t.theme)) {
      rejectedTags.push({ item: t, reason: "theme_not_allowed" });
      continue;
    }
    if (!isSentiment(t.sentiment)) {
      rejectedTags.push({ item: t, reason: "sentiment_not_allowed" });
      continue;
    }
    const list = byTheme.get(t.theme) ?? [];
    list.push(t);
    byTheme.set(t.theme, list);
  }

  const themes: ThemeSummary[] = [];
  const ask: AskAPerson[] = [];
  const unsupportedSources = new Set<string>();
  const invalidSources = new Set<string>();
  for (const [theme, items] of [...byTheme.entries()].sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))) {
    const report = validateEvidence(items.map((i) => i.evidence), sources, sha256, options);
    for (const r of report.rejected) (r.reason === "unsupported_language" ? unsupportedSources : invalidSources).add(r.item.source_id);
    const validIds = new Set(report.valid.map((e) => e.source_id));
    const bySentiment: Record<Sentiment, Set<string>> = { positive: new Set(), negative: new Set(), neutral: new Set() };
    for (const t of items) if (validIds.has(t.evidence.source_id) && isSentiment(t.sentiment)) bySentiment[t.sentiment].add(t.evidence.source_id);
    const pos = bySentiment.positive.size;
    const neg = bySentiment.negative.size;
    const neu = bySentiment.neutral.size;
    const count = validIds.size;
    const lead = Math.max(pos, neg);
    const minority = Math.min(pos, neg);
    let verdict: ThemeVerdict;
    let note: ThemeSummary["note"];
    let direction: ThemeDirection;
    if (minority >= 2) {
      verdict = "conflicting";
      note = "conflicting_evidence";
      direction = "mixed";
    } else if (lead >= MIN_SOURCES_PER_THEME) {
      direction = pos > neg ? "positive" : "negative";
      verdict = minority === 1 ? "supported_with_dissent" : "supported";
      note = minority === 1 ? "one_dissenting_comment" : null;
    } else if (pos === 0 && neg === 0 && neu >= MIN_SOURCES_PER_THEME) {
      verdict = "neutral_mentions";
      note = "no_clear_opinion";
      direction = "neutral";
    } else {
      verdict = "insufficient";
      note = "not_enough_feedback";
      direction = null;
    }
    if (verdict === "conflicting") ask.push({ reason: "contradictory_reviews", detail: `visitors disagree about ${theme}: ${pos} positive, ${neg} negative comments`, about: [theme] });
    themes.push({
      theme,
      comment_count: count,
      unit: "comments",
      positive_sources: pos,
      negative_sources: neg,
      neutral_sources: neu,
      direction,
      verdict,
      note,
      evidence: dedupeSpans(report.valid),
      rejected: report.rejected,
    });
  }

  if (rejectedTags.length > 0) {
    ask.unshift({ reason: "structured_output_failure", detail: `${rejectedTags.length} model suggestion(s) were outside the catalogue and were not counted`, about: [...new Set(rejectedTags.map((r) => r.item.theme || "(empty theme)"))] });
  }
  if (unsupportedSources.size > 0) {
    ask.push({ reason: "unsupported_language", detail: `${unsupportedSources.size} comment(s) are in a language nobody here can check`, about: [...unsupportedSources].sort() });
  }
  if (invalidSources.size > 0) {
    ask.push({ reason: "evidence_invalid", detail: `${invalidSources.size} cited comment(s) could not be verified against the original text`, about: [...invalidSources].sort() });
  }
  return { themes, rejected_tags: rejectedTags, ask_a_person: ask };
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
