# Codex Platform — primary builder packet

Suggested room alias: Codex Platform. This is not a provisioned identity. Use the identity actually granted to your existing session.

## Your mission

Integrate the four lanes into a real offline Android prototype. You own source discovery, shared contract publication, root build configuration, safe merges and the Azure transport design. Carther's PC has his authenticated GitHub and Azure access; use it to inspect **FencesNGates, AIdenID and Senti**, whose components may already solve parts of this build. This research workspace could not verify their private source. Do not describe a component as proven here until you rerun the relevant checks.

Read 00_START_HERE.md, 01_BUILD_SPEC.md, the actual repo's AGENTS.md/CLAUDE.md, and your Senti session guidance. Read the existing room kickoff before adding this kit. Do not reset a live room, overwrite global agent instructions or start an unrelated agent swarm.

## Ownership

Own root workspace/lockfile, packages/contracts publication, services/sync, services/delivery, infra/azure, CI and integration docs. Domain proposes the core contracts; freeze them jointly before Mobile implementation depends on them. You are the sole main-branch integrator. Other agents commit in separate worktrees and send one concise handoff. Preserve all unrelated user work.

## First output, within a bounded discovery pass

1. Identify the current repo, branch, dirty changes and active instructions. Inspect local checkouts first with rg/rg --files. If needed, use authenticated GitHub CLI or the installed connector to locate source repositories; do not clone all repositories indiscriminately.
2. Produce docs/reuse-inventory.md: repo/path/commit/license/component/adaptation/test result. Candidates: AIdenID capability and approval receipts; Senti bounded hydration, claims, durable ACKs and event cursors; FencesNGates validated facts, deterministic quote constraints and approval components. Algorithms can port; Swift or web UI does not automatically become Android native code.
3. Record the actual Azure subscription/tenant/resource-group/region to use privately. Do not dump tokens, credentials, full environment variables or customer data into the room. Inspect existing resources before planning new ones.
4. Create one shared contract revision and file-ownership map. Publish one room decision with links. Resolve the native model/database dependency path with Mobile before adding incompatible dependencies.

If reuse is unavailable or adaptation is slower than a small implementation, document that and move on. Retain source attribution and licenses. Do not copy production customer records into demo data.

## Build order

First: make the local mobile build and shared core package integrate. Include a local fake transport clearly labeled as a simulator so the offline queue can be demonstrated without promising live SMS.

Second, if time remains: implement HTTPS sync and an idempotent server action ledger. Start with Azure Container Apps API/worker, PostgreSQL Flexible Server, Service Bus Standard, private Blob, Key Vault/managed identity and redacted monitoring. Produce validated Bicep and a cost/resource plan before deployment. Choose an existing authorized development environment where suitable; region, quotas and an explicit spending cap must be known before creating costly capacity. The offline judged path must run without Azure.

Never put LiveKit media/SIP on Container Apps as though TCP ingress handles its UDP requirements. A later isolated Linux VM runs the media trial. Do not provision AKS or a multi-region mesh for the weekend.

Sync contract: deduplicate by tenant/event and tenant/action in SQL, reject reused IDs with changed hashes, atomically add the broker outbox, acknowledge after commit. Derive tenant from authenticated device registration. Stable provider idempotency key; send_unknown after ambiguous acceptance. Broker deduplication is finite, not an exactly-once guarantee. Enforce per-tenant rate limits and leases. No LLM, ASR, translation or TTS fallback in the transport service.

## Review and acceptance

Review Domain's approval/state logic. Domain independently reviews tenant isolation and send semantics. Experience reviews channel truthfulness. Require evidence for restart persistence, duplicate reconnects, stale approvals, provider timeout ambiguity and cross-tenant rejection. Never merge a UI that labels queued as sent or accepted as delivered.

Only you edit shared schema versions and lockfiles after freeze. Broadcast a contract change once, naming consumers and migration. A room ACK is coordination, not product approval.

## Quiet Senti protocol

Hydrate the verified room with bounded recent events/checkpoints/actions before joining or writing. Use your actual granted session identity and the correct account link. Read from a cursor; filter your mentions, owned paths, contract changes and blockers. Claim your lane once with working_on and ACK the pinned revision once, targeting the actual event. Prefer a reaction/action for receipt and a threaded reply for a question.

Send only BLOCKED, DECISION or HANDOFF messages, normally 4–8 lines. No greetings, heartbeat transcript messages, ACK-of-ACK loops or full build logs. Do not rebroadcast all contributor research to all builders.

Handoff format: lane + commit; changed paths; behavior; validation with actual command/result/device; risk or blocked dependency; exact reviewer/next owner. Evidence and approvals in source artifacts matter more than cheerful completion messages.
