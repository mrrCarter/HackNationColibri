# Nat — independent evaluation and reliability packet

For Nathanael Muller. Recommended from your optimization and financial-access research background in the original profiles supplied by Carther. You are the independent correctness/evidence owner, not another overlapping application builder.

## Your contribution

Measure whether the AI adds value and whether its safe workflow survives realistic failures. Own contrib/nat and eval fixtures/results. Provide a truth oracle independent of the builders' implementation. Do not make expected labels by asking the same model to grade its own answer.

Build a small labeled feedback corpus, explicitly synthetic where needed. Separate development examples from a held-out set. Include mixed-language messages, duplicate comments, contradictory preferences, weak evidence, prompt injection, missing dates/prices and a strongly worded single outlier. Each reference topic/count/source label should be independently reviewed. Native Swahili semantics must be checked by an actual competent reviewer.

Run three comparable conditions: manual reading, keyword/template baseline and Sauti's local model. Hold inputs and task definition constant. Measure unsupported findings, evidence support, count accuracy, missed themes, actionable usefulness, owner time and clarity. Report sample size and limitations. 'Every ID exists' is not sufficient evidence that a finding is supported.

## Failure matrix

Test exact action edit invalidation, restart after approval, duplicate sync/import, reordered receipts, potential provider acceptance with a timeout, two requests for the last slot, revoked policy, clock rollback, low storage and wrong-owner/shared-phone access. Assign expected safe outcomes before running. Queue states and booking states remain separate. A booking conflict needs one authoritative reservation transaction or tentative status; two disconnected calendars cannot both promise the last slot.

Load testing is later and transport-only: 10 → 100 → 1,000 simulated reconnecting devices with explicit IDs and bounded payloads. Measure p95 sync latency, durable acceptance, duplicates, backlog/queue age, DB connections and per-tenant fairness. Coordinate against a local/staging environment with Platform; do not stress a production subscription or create large costs. This simulation does not prove 1,000 cheap phones can each run the model.

## Packet outputs

| Artifact | Required content |
|---|---|
| eval/heldout-feedback.jsonl | Independent labels, evidence IDs/spans, split and provenance |
| eval/failure-cases.json | Trigger, expected safe state, implementation under test, observed result |
| contrib/nat/results.md | Baselines, actual sample size, timings, error analysis, raw aggregate counts |
| contrib/nat/submission-evidence.md | Which claims pass, which are unmeasured, links to recordings/results |

Use one Codex/Python helper for independent fixture generators/fault harnesses in your folder. Claude/ChatGPT can challenge corner cases and interview phrasing. Perplexity/web can locate official benchmark sources; they cannot replace actual measurements. Keep helpers read-only outside eval/contrib/nat.

## Communication and completion

One room claim. Thread test discrepancies to Claude Domain or Codex Platform. A blocker message should contain the failing input ID, expected vs observed state, exact revision and reproduction link; not a full log dump. Deliver one final compact evidence summary to Carther for the video. Never describe an unrun test as passing, and never soften a critical failure to preserve the pitch.
