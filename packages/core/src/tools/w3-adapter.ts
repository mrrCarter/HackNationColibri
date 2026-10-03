#!/usr/bin/env node
/// <reference types="node" />
/**
 * Adapter for Nat's W3 fixtures (eval/w3/README.md, adapter contract).
 *
 * Reads {"fixture_id", "input"} on stdin, runs the real core (ingest, model
 * output parsing, evidence validation, theme counts, ask-a-person, decision
 * cards, owner choice) and prints one outcome JSON. It never sees "gold" or
 * "expected". Reason strings are the core's, verbatim. Node-only on purpose:
 * it is a test harness, not the core.
 *
 *   npm run build && node dist/tools/w3-adapter.js < fixture.json
 */

import { createHash } from "node:crypto";

import { type Sha256 } from "../canon.js";
import { buildDecisionCards, type DecisionCard, recordChoice } from "../decisions.js";
import { type ThemeSummary } from "../evidence.js";
import { ingestMessages, type StoredSource } from "../ingest.js";
import { analyzeFeedback, type FeedbackAnalysis } from "../tagging.js";

const sha256: Sha256 = (bytes) => createHash("sha256").update(bytes).digest("hex");

const THEMES = new Set(["coffee", "farm_walk", "food", "host", "directions", "price", "timing", "booking", "language", "facilities", "buy_coffee"]);
const LANGUAGES = new Set(["en", "sw", "de", "fr"]);

/**
 * HARNESS-ONLY language id for sources that declare no language, so the dev
 * fixtures can exercise the core end to end. It is a stand-in for the product's
 * language-id step (Max lane is evaluating a real detector) and claims nothing:
 * the word lists are small function-word sets plus a Kikuyu orthography mark.
 * Unknown is unknown: "und", and the core then asks a person (fail closed).
 */
const STOPWORDS: Record<string, Set<string>> = {
  en: new Set(["the", "and", "was", "were", "we", "our", "us", "is", "are", "it", "to", "of", "for", "very", "too", "not", "no", "a", "at", "there", "this", "that", "with", "they", "you"]),
  sw: new Set(["na", "ya", "wa", "ni", "kwa", "la", "za", "cha", "kila", "sana", "lakini", "hakuna", "wageni", "kahawa", "ilikuwa", "chakula", "mchana", "shamba", "nzuri", "mbaya", "bei", "saa", "ziara", "mgeni", "asante", "karibu", "sisi", "hii", "hiyo"]),
  de: new Set(["der", "die", "das", "und", "war", "waren", "wir", "uns", "ist", "sehr", "nicht", "kaffee", "zu", "mit", "für", "ein", "eine", "haben", "den", "dem", "auf", "im", "es"]),
  fr: new Set(["le", "la", "les", "et", "était", "étaient", "nous", "est", "très", "pas", "café", "pour", "du", "de", "un", "une", "à", "des", "il", "elle", "on"]),
};
const KIKUYU_MARKS = /[ĩũ]/i;

function detectLanguage(text: string): string | null {
  if (KIKUYU_MARKS.test(text)) return "ki";
  const tokens = text.toLowerCase().match(/[\p{L}']+/gu) ?? [];
  let best: string | null = null;
  let bestScore = 0;
  for (const [lang, words] of Object.entries(STOPWORDS)) {
    const score = tokens.filter((t) => words.has(t)).length;
    if (score > bestScore) {
      best = lang;
      bestScore = score;
    }
  }
  return bestScore > 0 ? best : null;
}

type OwnerInput =
  | { type: "show_cards" }
  | { type: "owner_says"; card_theme?: string; transcript?: string; asr_uncertain?: boolean }
  | { type: "new_messages"; messages?: unknown[]; labels?: unknown[] };

interface Input {
  messages?: unknown[];
  model_output?: unknown;
  owner_facts?: unknown;
  owner_inputs?: OwnerInput[];
}

function findingStatus(t: ThemeSummary): "enough_evidence" | "not_enough_feedback" | "contradictory" {
  if (t.verdict === "conflicting") return "contradictory";
  if (t.verdict === "supported" || t.verdict === "supported_with_dissent") return "enough_evidence";
  return "not_enough_feedback";
}

/** Everything the core knows about the feedback so far. Re-analysed whenever messages or labels arrive. */
class Session {
  readonly sources = new Map<string, StoredSource>();
  readonly duplicates: string[] = [];
  readonly ingestRejected: Array<{ message_id: string; reason: string }> = [];
  modelOutput: unknown = { status: "ok", labels: [] as unknown[] };

  addMessages(messages: unknown[]): void {
    const result = ingestMessages(messages, sha256, this.sources);
    for (const [id, s] of result.sources) {
      const language = s.language ?? detectLanguage(s.text) ?? "und";
      this.sources.set(id, { ...s, language });
    }
    for (const d of result.duplicates) if (!this.duplicates.includes(d)) this.duplicates.push(d);
    for (const r of result.rejected) if (!this.ingestRejected.some((x) => x.message_id === r.message_id)) this.ingestRejected.push({ message_id: r.message_id, reason: "invalid_message" });
  }

  /** Later labels (new_messages steps) extend an ok output; a malformed output stays malformed. */
  addLabels(labels: unknown[]): void {
    const mo = this.modelOutput;
    if (typeof mo === "object" && mo !== null && !Array.isArray(mo) && (mo as { status?: unknown }).status === "ok" && Array.isArray((mo as { labels?: unknown }).labels)) {
      this.modelOutput = { status: "ok", labels: [...((mo as { labels: unknown[] }).labels), ...labels] };
    }
  }

  analyze(): FeedbackAnalysis {
    return analyzeFeedback(this.modelOutput, this.sources, sha256, { allowedThemes: THEMES, supportedLanguages: LANGUAGES }, new Set(this.duplicates));
  }
}

export function runFixture(input: Input): Record<string, unknown> {
  const session = new Session();
  session.addMessages(Array.isArray(input.messages) ? input.messages : []);
  session.modelOutput = input.model_output;

  // Steps 4 and 5: cards shown, owner speaks, new evidence may arrive in between.
  let shownCards: DecisionCard[] = [];
  const decisions: Array<{ theme: string; choice: string }> = [];
  const choiceRefusals: Array<{ theme: string; reason: string }> = [];
  for (const step of input.owner_inputs ?? []) {
    if (step.type === "show_cards") {
      shownCards = buildDecisionCards(session.analyze(), sha256);
    } else if (step.type === "new_messages") {
      session.addMessages(Array.isArray(step.messages) ? step.messages : []);
      session.addLabels(Array.isArray(step.labels) ? step.labels : []);
    } else if (step.type === "owner_says") {
      const shown = shownCards.find((c) => c.theme === step.card_theme);
      if (!shown) {
        choiceRefusals.push({ theme: String(step.card_theme), reason: "card_not_shown" });
        continue;
      }
      const current = buildDecisionCards(session.analyze(), sha256).find((c) => c.theme === step.card_theme) ?? null;
      const r = recordChoice({ shownCard: shown, currentCard: current, transcript: String(step.transcript ?? ""), asrUncertain: step.asr_uncertain === true });
      if (r.ok) decisions.push({ theme: r.decision.theme, choice: r.decision.choice });
      else choiceRefusals.push({ theme: shown.theme, reason: r.reason });
    }
  }

  const analysis = session.analyze();
  const rejectedLabels: Array<{ message_id: string; theme: string; reason: string }> = [...analysis.parse.rejected];
  for (const r of analysis.rejected_tags) rejectedLabels.push({ message_id: r.item.evidence.source_id, theme: r.item.theme, reason: r.reason });
  const acceptedLabels: Array<{ message_id: string; theme: string }> = [];
  const counts: Record<string, { unique_messages: number; positive: number; negative: number; neutral: number }> = {};
  const findings: Array<Record<string, unknown>> = [];
  for (const t of analysis.themes) {
    for (const r of t.rejected) rejectedLabels.push({ message_id: r.item.source_id, theme: t.theme, reason: r.reason });
    if (t.comment_count === 0) continue; // every label on this theme was rejected: no count, no finding
    for (const id of [...new Set(t.evidence.map((e) => e.source_id))]) acceptedLabels.push({ message_id: id, theme: t.theme });
    counts[t.theme] = { unique_messages: t.comment_count, positive: t.positive_sources, negative: t.negative_sources, neutral: t.neutral_sources };
    const status = findingStatus(t);
    const finding: Record<string, unknown> = { theme: t.theme, status };
    if (status === "enough_evidence") {
      finding["sentiment"] = t.direction;
      finding["evidence_message_ids"] = t.supporting_source_ids; // the dissent is counted and shown, it does not support the finding
      if (t.dissenting_source_ids.length > 0) finding["dissenting_message_ids"] = t.dissenting_source_ids;
    }
    findings.push(finding);
  }

  const ask: Array<{ reason: string; message_ids: string[] }> = [];
  for (const a of analysis.ask_a_person) {
    if (a.reason === "contradictory_reviews") {
      const ids = analysis.themes.filter((t) => a.about.includes(t.theme)).flatMap((t) => t.evidence.map((e) => e.source_id));
      ask.push({ reason: a.reason, message_ids: [...new Set(ids)] });
    } else if (a.reason === "structured_output_failure" && !analysis.parse.malformed) {
      ask.push({ reason: a.reason, message_ids: [...new Set(analysis.rejected_tags.map((r) => r.item.evidence.source_id))] });
    } else {
      ask.push({ reason: a.reason, message_ids: a.about });
    }
  }

  const cards = (input.owner_inputs ?? []).some((s) => s.type === "show_cards") ? shownCards : buildDecisionCards(analysis, sha256);

  return {
    ingest: { duplicates: session.duplicates, rejected: session.ingestRejected },
    accepted_labels: acceptedLabels,
    rejected_labels: rejectedLabels,
    counts,
    findings,
    ask_a_person: ask,
    cards: cards.map((c) => ({ theme: c.theme, text: c.text, quotes: c.quotes, choices: [...c.choices], prospective: c.prospective, card_digest: c.card_digest, text_review: c.text_review })),
    decisions,
    choice_refusals: choiceRefusals,
    side_effects: { facts_changed: false, approvals_created: 0, outbox_entries: 0 },
    core_revision: process.env["SAUTI_CORE_REVISION"] ?? "unknown",
    harness_notes: ["language id for undeclared sources is harness-only (stopword sets); the product's detector replaces it"],
  };
}

async function main(): Promise<void> {
  const chunks: Buffer[] = [];
  for await (const chunk of process.stdin) chunks.push(chunk as Buffer);
  const text = Buffer.concat(chunks).toString("utf8");
  let parsed: { fixture_id?: unknown; input?: Input };
  try {
    parsed = JSON.parse(text) as { fixture_id?: unknown; input?: Input };
  } catch {
    process.stdout.write(JSON.stringify({ error: "stdin is not JSON" }) + "\n");
    return;
  }
  const outcome = runFixture(parsed.input ?? {});
  process.stdout.write(JSON.stringify({ fixture_id: parsed.fixture_id ?? null, ...outcome }) + "\n");
}

const invokedDirectly = typeof process !== "undefined" && Array.isArray(process.argv) && /w3-adapter\.[cm]?js$/.test(process.argv[1] ?? "");
if (invokedDirectly) {
  main().catch((err: unknown) => {
    process.stderr.write(String(err) + "\n");
    process.exit(1);
  });
}
