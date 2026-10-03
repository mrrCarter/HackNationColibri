# Max — model, device and language-data packet

For Maximilien Rambaud. Recommended from your AI-research and operations-research background in the profiles supplied by Carther; confirm fit rather than treating the profile as a skills assessment.

## Your contribution

Give the builders a measured model choice and a trustworthy data/model manifest. Your experiments directly unblock Codex Mobile. You own contrib/max, model manifests and experimental reports; you do not rewrite the mobile runtime in parallel.

Start with Qwen3 0.6B, then test 1.7B only if the actual device has headroom. Evaluate this task's Swahili comprehension and grounded extraction, not a general benchmark headline. Pin the exact weights, license, revision, tokenizer/chat template, quantization procedure and hashes. Record all adapters/base models/vocoders for speech: a permissive top-level tag does not license a restrictive underlying model. Reject noncommercial weights for the final commercial product.

Use one shared-phone experiment reservation with Mobile. Record phone/OS/ABI/RAM/free storage; APK and model/data sizes separately; cold model load, warm time to first output, full task duration, peak process memory, cancellation and ten consecutive task runs. Keep RAM/latency blank until measured. Label desktop and phone results separately. Test all radios off. Record thermal/battery observations and low-memory failures without extrapolating from a single run.

## Packet outputs

| Artifact | Required content |
|---|---|
| contrib/max/model-decision.md | Candidates, measured results, choice, limitations, reproducible command/config |
| data/model-manifest.json | Upstream URL/revision, all licenses, bytes, SHA-256, quantizer/runtime revision, language claims and validation status |
| contrib/max/language-review.csv | Intent/draft/corrected Swahili/reviewer/date/factual check/status |
| contrib/max/data-card.md | Source, country/year, consent/license, size, split, synthetic labels and exclusions |

You can use Perplexity or web search to discover candidate sources, ChatGPT/Claude to challenge the experiment design, and one Codex/Python session for an isolated benchmark/fixture script. Final technical claims need original model cards/repositories/docs. A model saying 'Swahili supported' is not native-speaker validation.

A helper assignment should be narrow: 'Find permissive Swahili TTS candidates; return base/adapter/vocoder provenance and exact upstream links; do not change application files; stop after a ranked evidence table.' Local speech is optional after the text gate. MIT Chatterbox Multilingual V3 is a candidate, not a promise that a cheap Android phone can run it.

## Handoff to the room

Claim your lane once. Send one concise result to Codex Mobile and Claude Experience: artifact links, chosen configuration, actual device result, unresolved language/license issue and a concrete decision if needed. Never post keys, raw customer conversations or long benchmark logs. For routine receipt use one ACK/reaction; a builder pulls your full file only when relevant.

Done when Mobile can reproduce the selected model run and Experience has a clear reviewed/unreviewed language record. If no suitable phone/model combination passes, state that as a blocker immediately; do not replace the device test with a cloud demo.
