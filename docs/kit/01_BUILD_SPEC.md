# Sauti Host — build specification

Revision 1.0 · 3 October 2026 · Implementation proposal under the agreed five-phase roadmap

## 1. Product contract

Noor is a small farm-tourism operator. The first release helps her learn from saved visitor feedback and decide a useful next action in Swahili. It runs on an existing household Android phone without a network. Azure carries messages and stores authorized replicas; it does not understand feedback, draft responses or make business decisions. A basic phone can reach the system only when an appropriate telecom channel and the home device are reachable; it is not an offline inference device.

Success is a recorded, reproducible offline workflow with truthful source links and exact approval. A phone UI that only displays precomputed server answers is not this prototype. A synthetic fixture is acceptable when labeled; it is not evidence of real customer outcomes. The challenge's Tourism annex and submission/judging requirements are controlling: sources S01–S02.

### What this release implements

Import a small, documented set of reviews and visitor messages. Show evidence-backed topics, deterministic counts and an uncertainty option. Present one useful proposal in native-reviewed Swahili; let Noor inspect sources, reject, ask a person or approve the exact message. Save approval and queued content in encrypted local storage. Restore them after an app restart. If online transport is implemented, demonstrate it separately after the offline proof.

Live translation, phone calls, WhatsApp automation, payments, listing edits and MCP booking delegation are later phases. Interfaces may be designed now; adapters must not pretend to work or block the core. The pilot requires the household phone to be present. The daughter's weekend-only availability is a deployment limitation, not an always-on service assumption.

## 2. Technology decisions

| Component | Initial choice | Gate or limitation |
|---|---|---|
| Mobile | React Native with a native Android build and TypeScript | Use an existing proven native setup if available. Expo Go cannot supply custom native model/database modules; use a development/production native build. |
| Local reasoning | Qwen3 0.6B GGUF through llama.rn / llama.cpp | Apache 2.0 model; pin source revision, tokenizer/template, quantizer and SHA-256. Actual device benchmark first. S03–S04. |
| Larger model | Qwen3 1.7B | Optional only after it passes the same device and Swahili gates. A larger parameter count does not establish better task performance. |
| Persistence | SQLCipher for Android behind a tested RN native adapter | Ordinary SQLite is not encrypted. Prefer current sqlcipher-android; store a random DB key wrapped by Android Keystore. Model-only MIT/Apache rule does not forbid a compatible software-library license. S05–S06. |
| Domain logic | Small portable TypeScript package, schema validated | No network, provider SDK or model call inside approval/count/state functions. |
| Speech input | Multilingual Whisper via whisper.cpp | MIT; optional after text workflow passes. Test local recordings and phone-line audio separately. S07. |
| Speech output | Native-reviewed prerecorded Swahili prompts first | Dynamic local TTS is a separate experiment. Chatterbox Multilingual V3 is an MIT candidate that lists Swahili, but Android feasibility is unproven. S08. |
| Connected voice | LiveKit on Azure Linux VM; SIP only with a verified carrier | Transport only. Device still performs inference. Never silently substitute a cloud voice agent. S09–S10. |
| ElevenLabs | Build-time reviewed audio assets; connected experiments only within declared scope | API credits do not grant enterprise on-device deployment or an Apache/MIT model license. Cloud-generated runtime speech would change the strict local-inference principle. S11–S13. |

Mobile default: one inference at a time, CPU first, initial context ceiling 2,048 tokens and output ceiling 256 tokens. These are tunable starting budgets, not benchmarks. Disable thinking only through a validated Qwen chat-template/runtime setting; do not assume the option exists in every wrapper. Process feedback in small units, validate outputs, then aggregate by code. Stop cleanly on cancellation or low storage. Avoid simultaneous ASR and LLM loads until peak RAM is measured.

First-hour decision: load the chosen model, produce one real structured answer, read/write an encrypted record, and build/install the app on the test phone. If the existing RN/native bridge cannot do this within a bounded spike, Mobile and Platform publish the failure and choose a viable native route together. Do not spend the weekend rebuilding a wrapper while shipping a mocked inference demo.

## 3. Repository and ownership

Proposed monorepo paths: apps/mobile; apps/portal; packages/core; packages/contracts; packages/experience; services/sync; services/delivery; infra/azure; data; eval; docs. Platform owns the root workspace, lockfile, CI, contracts publication and merges. Domain owns core. Mobile owns apps/mobile. Experience owns design/interaction/localization assets and the optional portal/voice adapter. Contributors own distinct contrib subfolders, data manifests or evaluation fixtures agreed before editing.

Platform can change this layout to fit an existing proven repository after publishing the ownership map. Agents must read actual root and nested AGENTS.md/CLAUDE.md instructions. The supplied repo/AGENTS.md is a scoped starter; it never replaces the user's existing governance blindly.

Reusable source is a hypothesis until audited. FencesNGates may supply validated catalog/quote constraints and approval UI; AIdenID may supply scoped policy, revocation and receipt primitives; Senti may supply bounded hydration, claims, durable ACKs and session streaming. For each accepted component record repo URL, commit, exact paths, license, dependencies, meaningful existing tests, passing rerun and adaptation. Keep customer records and production secrets out of test fixtures. Time-box discovery before building a minimal replacement.

## 4. Evidence and truth

Keep original messages immutable with source ID, source type, content hash, language, import time and optional visit/customer ID. Normalize a separate display copy, never overwrite the evidence. Preserve exact quotes with UTF-8 byte ranges and verify them against the hashed original. User-generated messages are untrusted data, including text that says to ignore instructions or approve a send.

The model suggests bounded labels and evidence IDs/spans. Code checks that every ID exists and every span is exact. Counts are computed from unique source IDs. Distinguish 6 comments from 6 visitors; without reliable visit IDs the UI must say comments. Independent human labels evaluate whether a source supports a finding: valid IDs alone do not prove semantic truth. No model confidence percentage is shown unless calibrated on a held-out set.

Recommendations use a small reviewed action catalogue. A suggested experiment is visibly a suggestion, not a claim that Noor already offers it. No invented price, time, accessibility claim, menu, transport promise or free capacity. Missing or conflicting information yields a specific question and an ask-a-person option. Do not collapse a single vivid comment into a universal claim.

Owner facts have revisions and validation records. Money is an integer in the currency's minor units, with ISO currency code; do not assume every currency has two decimal places. Appointments contain an absolute local date/time and IANA time zone. Relative dates, party size, child pricing, names and language ambiguities need clarification. A translation never becomes a new owner fact just because the model produced it.

## 5. Exact approvals and durable state

An ActionEnvelope binds action ID, conversation, exact recipient and transport, exact payload, fact revision, evidence-set hash, display/locale version, validity window and schema version. Its approval digest is SHA-256 over RFC 8785 canonical JSON with a domain separator. Hash only canonical fields, reject unknown action fields, and validate the schema before hashing. The pseudocode specifies the design, not a cryptographic proof. S14.

Approval requires authenticated local owner interaction. Render the bound content before a tap; a voice readback must finish before a scoped confirmation. Persist envelope, digest, owner authorization record and local outbox entry in one database transaction. Compare the current fact revision and expected rendered digest inside that transaction. Any change creates a new action ID or revision and requires new approval. A room reaction, tourist's reply, ASR transcript or generic 'yes' is never owner approval.

Primary transport states are proposed → approved → queued → sending → sent → delivered. Also support rejected, expired, revoked, cancelled, failed and **send_unknown**. Queued means not dispatched. Sent means the carrier/provider accepted the message. Delivered requires a supported authenticated receipt; neither means read. If a send times out after possible acceptance and the provider offers no reliable idempotency/status lookup, enter send_unknown and reconcile rather than retry blindly. Preserve a separate business state: a sent booking request is not a confirmed booking.

Expiry and revocation are checked at dispatch. The server must reconcile the current authoritative facts before dispatching a stale offline approval. Noor can still draft and approve offline, but if facts changed elsewhere the action is held for reapproval. Revoke/cancel is guaranteed before acceptance; after acceptance it cannot undo a carrier send. Device wall-clock rollback must not extend approvals; without trustworthy expiry reconciliation, hold dispatch.

Phase 4 templates stay consistent with 'every action approved': Noor can review a manifest of exact recipient/payload/schedule tuples and approve that batch. It is not an unlimited future permission. Phase 5 may add an explicitly authorized, bounded delegation with policy revision, expiry, caps and revocation. The initial prototype does not infer that grant.

## 6. Sync and delivery on Azure

| Service | Responsibility | Deployment approach |
|---|---|---|
| Container Apps API | Authenticated HTTPS sync and read-only public offers | Min 1 for a live demo; stateless handlers; production redundancy after load/SLO measurement. |
| Container Apps worker | Deterministic outbox delivery and receipts | No public ingress; managed identity; provider adapter behind a narrow interface. |
| PostgreSQL Flexible Server | Tenant/device registry, inbox deduplication, action ledger, broker outbox, capacity locks | Uniqueness constraints and transactions; bounded connection pools; HA/backup policy after cost and region check. |
| Service Bus Standard | Per-conversation work queues | Sessions for processing order; duplicate detection as an additional safeguard. |
| Private Blob storage | Versioned/hash-verified model packs, authorized attachments, encrypted backups | No public bucket. Short-lived scoped downloads; do not claim keyless recovery of encrypted data. |
| Key Vault + managed identities | Provider credentials and service authorization | No provider keys in APK, room, logs or git. |
| Monitor / Application Insights | Redacted failures, queue lag, latency and costs | Avoid bodies, phone numbers, audio and raw prompts in telemetry. |
| Linux VM, later | LiveKit media/SIP/TURN | Separate media network and deployment from the HTTPS app. |

An authenticated device submits events with stable event and action IDs, device sequence and payload hash. Derive the tenant from its server-issued grant, not a body field. In one server transaction: verify, insert inbox uniquely by tenant/event, insert or validate the action uniquely by tenant/action, and add the broker outbox record. Acknowledge only after commit. A repeated ID with a different payload is an integrity error; an identical retry returns the original result.

The publisher may republish after a crash. Broker MessageId is the stable action ID; SessionId scopes tenant plus conversation. Service Bus duplicate detection has a finite window; retain the database deduplication/ledger longer than the supported offline retry period. Broker order alone cannot resolve two devices that created conflicting offline events. S15.

The worker claims a lease, checks approval, revocation, expiry, exact payload/recipient and current fact/policy version, then calls the provider using its idempotency key when supported. Authenticated callbacks are deduplicated and never regress a terminal state. Rate limits and retry budgets are per tenant and provider. Server-side inference is absent, including in error fallbacks.

Azure Container Apps ingress handles HTTP/TCP; LiveKit's media needs an appropriate UDP/TURN setup. Use a separate VM for the first media trial. Add a tested distributed LiveKit/Redis deployment only after real call-load and node-drain experiments. Prefer Azure Managed Redis for a new managed Redis deployment; verify compatibility before selecting it. AKS, global sharding and multi-region active/active are not prerequisites for this workflow. S09, S16–S17.

## 7. Channels and basic phones

An ordinary Android application cannot capture SIM voice-call audio using normal microphone permissions. Do not promise an autonomous IVR by simply installing the app in the home phone. S10.

The connected voice path is basic phone → carrier/PSTN/SIP → LiveKit media transport → reachable authenticated home device → local Whisper/Qwen/local speech → media return. The home device needs a tested running audio session, permissions, power and IP access. If unreachable, say that a response is pending or record a consented message for later sync. There is no magical offline call when all radios are off. Caller ID alone does not authenticate Noor; use an enrolled owner session and a tested PIN/confirmation mechanism, with lockout/recovery.

SMS needs cellular coverage and country-verified two-way service. Incoming/outgoing SMS, callback rates, sender registration, local-script segmentation and sponsored/toll-free service are measured commercial constraints. A cloud SMS gateway also needs a path to the home device for reasoning. The initial import can use a file/manual share flow; do not require sensitive SMS permissions or assume Play Store eligibility without verification. WhatsApp API permissions, number setup and messaging windows are Phase 2 gates, not a claim that any Android app can periodically scrape private chats.

ElevenLabs' current Swahili-supporting model and API endpoint must be selected explicitly. The LiveKit example/default cannot be assumed to support Swahili. LiveKit Inference retired ElevenLabs on 31 August 2026; the direct plugin can still use your account. The newer conversational endpoints need an actual compatibility test. The strict local product can use reviewed audio generated at build time if output rights permit; it cannot silently call cloud TTS for every utterance. Enterprise offline deployment is a separate proprietary offering. S11–S13.

## 8. Interface and inclusion

Three primary views: **Today**, **Evidence**, **Outbox**. One decision per card, with a source-count label and clear try/reject/ask options. Use large targets, readable Swahili, optional reviewed audio, icons plus words, and explicit offline/last-sync status. A green approval state must not imply delivery. Never make a busy operator manage a generic chat transcript or resolve raw JSON.

Approval preview includes recipient, channel, exact message, date/time when relevant and whether it waits for signal. Ask a single bounded clarification when possible, such as which of two dates. Show pending enquiries by distinct conversation/proposal IDs and customer-safe labels; on a shared phone reveal personal details only after owner unlock. A child/daughter helper can import feedback without gaining permission to approve sends. Device theft, lost keys and owner recovery need a documented policy; encryption alone does not solve these workflows.

Native review covers UI, factual meaning, dates/prices, politeness, negation and code-switching. Label every unreviewed translation. Voice interrupts, silence, background speech and uncertain recognition cancel or pause confirmation. Keypad fallback is scoped to the proposal just read, expires, and cannot be replayed onto another action.

## 9. Learning from Muse, Dots and Instinct

| Product pattern, verified as of 3 October | What Sauti borrows | What Sauti must prove |
|---|---|---|
| Meta Muse: persistent agent context and app/WhatsApp access; Small Business explicitly asks approval before publishing, sending or spending | Familiar channel and permission controls | Measured local performance, narrower truth constraints and an existing-device offline workflow. Approval alone is not unique. S18–S19. |
| OpenAI Dots: persistent assistant with connected apps and configurable action rules | Continuity, memory, controlled proactive notices | Quiet bounded attention and durable pending decisions without mandatory cloud reasoning. S20. |
| Instinct: contextual assistant reached by text or calls | A simple, familiar interface | Tested carrier reachability, explicit owner authentication and reliable Swahili. S21. |
| Bókun: booking, availability and distribution tooling | Practical booking operations and reseller interfaces | Incremental value beyond a listing and booking tool. Its term 'offline booking' means manually entered bookings, not proof of airplane-mode AI. S22. |

This is a design comparison, not a claim that Sauti outperforms these products. Measure task quality, p95 device time, memory, number of owner steps, recovery and costs on the chosen device. Avoid copying their broad ambitions before proving this narrow workflow.

## 10. Commercial design and Porter's five forces

First buyer hypothesis: one cooperative pays for setup, training and a per-active-operator service subscription. Optional financed/leased hardware belongs to the later rollout; separate device, telecom and support costs from software. Noor controls her customer information; a cooperative sponsor does not automatically gain access to all messages. Credits subsidize experiments, not recurring economics.

| Force | Risk | Practical response and test |
|---|---|---|
| Rivalry: high | Booking platforms and broad agents already have distribution and business functions | Focus on validated offline feedback-to-action. Interview operators who cannot use today's tools; demonstrate a measured advantage. |
| New entrants: high | Small open models and app frameworks are accessible | Build locally reviewed task data, reliable offline operations and cooperative onboarding. Do not call these moats until adoption and retention support them. |
| Substitutes: high | Guide, daughter, paper, WhatsApp templates or a spreadsheet may be enough | Blind comparison with manual reading and keyword/template tools; include owner time and mistakes, not AI novelty alone. |
| Buyer power: high | Cooperatives have small budgets and operators can stop using it | Test a paid pilot and support burden. Avoid relying on a single grant buyer; make export and ownership clear. |
| Supplier power: mixed/high | Telecom channels, device constraints and voice services influence costs and availability | Keep core model portable and local, isolate provider adapters, verify country terms and budget replacements for gifted credits. |

Unit contribution = collected subscription/booking revenue − SMS/call/audio/provider cost − hosting − support − device/onboarding amortization − payment/refund exposure if later introduced. Keep currencies and periods consistent. Trial three locally informed price hypotheses; label prices untested until a buyer accepts. Record activation, weekly completed workflows, support minutes, retention and attributable completed bookings. No money moves automatically; deposits remain owner-confirmed records.

MCP is a later discovery channel, not the moat: publish approved offers separately from customer PII. Expose search and request_booking before confirm_booking. Authenticate scoped callers, validate token audiences and authorize tools; a ChatGPT/Claude subscription is not shareable backend compute. Partner agents consume your MCP/API and submit requests; the home device/Noor handles the business decision. S23.

A large company would require repeatable deployment, retention, paid distribution and expansion beyond one tourism workflow. A $10B valuation is an ambition, not a defensible forecast from this architecture. The next commercial gate is a paid cooperative pilot with measured unit economics.

## 11. Delivery gates

G0: source/phone inventory and contract freeze. G1: real local inference plus encrypted storage on phone. G2: full offline workflow, exact evidence and owner-approved queue. G3: restart/ambiguity/approval fault tests plus native language review and baseline comparison. G4: recorded 2–5 minute video and working code/link; only then optional sync/voice polish. Exact test matrix and video script are in 11_ACCEPTANCE_AND_EDGE_CASES.md.

Scale is a roadmap gate: simulate 10, 100 and 1,000 reconnecting devices; measure throughput, p95 sync latency, database connections, queue age and tenant fairness. Keep generation cost on the device; measure device latency separately from server transport. Publish achieved numbers and hardware, never the phrase 'hyper scalable' as a substitute for evidence.
