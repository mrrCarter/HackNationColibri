# Lane map r1 (proposed by Claude Domain, 2026-10-03 22:10 UTC)

Source: Carter's build kit r1.0 (00_START_HERE, 01_BUILD_SPEC, packets 02 to 08, 10_ROOM_ADDENDUM, 11_ACCEPTANCE). The addendum supersedes the room's earlier W1 to W6 assignments; Cosme retracted those at 21:52Z. Carter confirms or changes this map; nobody commits product code against it before that.

## What changes versus CLAUDE.md (the team plan)

1. **Scope.** First release is ONE workflow: saved visitor feedback, evidence-backed findings with deterministic counts, a Swahili decision card, Noor approves ONE exact follow-up, durable offline queue that survives a force-close. Tourist replies (W2), payments (W4), listings (W5) and voice calls (W6) are later phases: interfaces may be designed, adapters must not pretend to work.
2. **Target.** A real, already-owned Android phone: React Native native build, Qwen3 0.6B via llama.rn, SQLCipher. The Python `sauti/` prototype does not run on the phone. It becomes the laptop reference and the evaluation harness (Nat's baselines, Max's experiments) unless Carter decides otherwise.
3. **Core.** A portable TypeScript package (`packages/core`) owned by Domain, built against a frozen contract (`packages/contracts`). Python core work (xam-claude's `w2-answer-tourist`, Domain's own `sauti/core` draft) is reference input, not the shipped core.
4. **Licenses.** Runtime models must be MIT or Apache-2.0 with full provenance. NLLB (CC-BY-NC) and MMS-TTS (CC-BY-NC) leave the runtime. Whisper (MIT) is optional after the text gate. Swahili output is native-reviewed text first, prerecorded reviewed audio second.
5. **Money.** Integer minor units with ISO currency code and a currency-specific exponent (kit section 4). Domain's first schema draft used whole units; it is corrected before publication.

## Lanes

| Lane | Owner (Senti id) | Paths | First deliverable |
|---|---|---|---|
| Codex Platform | `codex` (claimed) | root workspace, lockfile, CI, `packages/contracts` publication, `services/sync`, `services/delivery`, `infra/azure`, merges to main | `docs/reuse-inventory.md`, ownership map, contract freeze with Domain |
| Codex Mobile | second Codex session (Carter is starting it) | `apps/mobile` | G1: one real local Qwen answer with all radios off, encrypted record surviving restart, on the named test phone |
| Claude Domain | `fable-5.1-nav` (claimed) | `packages/core`, contract proposals in `packages/contracts`, domain tests | contract r1.0 (action envelope, approval record, states, good and bad fixtures, digest test vectors), then the TS core with the packet's fault tests 1 to 8 |
| Claude Experience | OPEN. Carter: a second Claude session, or `fable-5.1-nav` covers it under the kit's two-session fallback | `packages/experience`, interaction JSON and tokens, Swahili review sheet, demo script | Today / Evidence / Outbox interaction spec with every state; Swahili review sheet |
| Max | `xam-claude` (Max's helper) | `contrib/max`, `data/model-manifest.json` | `model-decision.md` (Qwen3 0.6B Swahili comprehension and grounded extraction, desktop results labeled desktop until the phone run), manifest with hashes and licenses, `language-review.csv`, `data-card.md` |
| Nat | `muller-claude` (Nat's helper) | `contrib/nat`, `eval/` | `eval/heldout-feedback.jsonl` (synthetic, labeled, dev/held-out split), `eval/failure-cases.json` from the kit's failure matrix with expected safe states, keyword/template baseline |
| Cosme | `cosme-claude` (claimed) | `contrib/cosme` | interview script, `economics.csv`, pilot offer, market evidence |
| Carther | `human-mrrcarter` | scope, access, test phone, demo, submission | name the test phone; confirm this map |

Builders work in separate worktrees, one owner per path. Teammates' helpers produce bounded artifacts inside their human's folder and do not edit builder-owned paths.

## Existing work: keep, port, park

- **Keep as reference:** `sauti/lang/swahili.py` (number, clock and weekday parsing plus readback), the "LLM span must be grounded in the transcript" check, the W1 fact-checker, and the measured result that Qwen3 0.6B misassigns fields on unseen dictation. Domain ports the grounded-span rule and "code overrules the model" into the TS evidence validation. The Swahili renderers feed Experience's review sheet.
- **Push as reference:** xam-claude's `w2-answer-tourist` (states, policy, outbox, calendar, simulated transport). Domain reads it for state and idempotency semantics. It is not merged to main as product code.
- **Park as roadmap:** W4 payments (Domain's own plan #47453, withdrawn), W5 listings, W2 live replies, W6 voice. Design notes may stay in `docs/`.
- **Port to Nat:** muller-claude's W3 ingest and tagging design becomes the evaluation corpus and oracle labels, not a product table.

## Open decisions for Carter

1. Experience owner (see table).
2. Python `sauti/` as laptop reference plus eval harness, or retired.
3. The test phone: model, OS, free storage, availability.

## Room protocol from here

`working_on` once per lane on the packet message, ACK the pinned revision once, status in files and checkpoints, top-level posts only BLOCKED, DECISION or HANDOFF.
