# Sauti Host — start here

Build kit r1.0 · 3 October 2026 · Prepared for Carther and the existing PC builders

## The decision

Use **two Codex sessions and two Claude sessions** as primary builders. Give each one a fixed lane and a separate worktree. One Codex session integrates. Teammates contribute experiments, fixtures, reviewed copy, customer evidence and design assets through bounded packets. More agents are useful only for a named, independent task with a concrete output and a stop condition.

This is a staffing recommendation, not a claim that Claude and Codex have inherent specializations. Use the strongest coding models already available in those sessions. Four concurrent local model tests or Android builds may exceed the PC's resources: permit one Android build and one phone inference experiment at a time.

These packets are instructions for your PC sessions. They have not been started, joined to your room or given access by this document.

| Session | Primary lane | Packet |
|---|---|---|
| Codex Platform | Contracts integration, repo reuse audit, Azure transport, merges | packets/02_CODEX_PLATFORM.md |
| Codex Mobile | Android app, on-device model, encrypted storage, offline proof | packets/03_CODEX_MOBILE.md |
| Claude Domain | Evidence, facts, exact approvals, state machine, deterministic tests | packets/04_CLAUDE_DOMAIN.md |
| Claude Experience | Interaction specification, Swahili review assets, voice boundary, demo | packets/05_CLAUDE_EXPERIENCE.md |

If you can run only two sessions, combine Mobile and Platform in Codex, and Domain and Experience in Claude. Preserve the same contracts, cross-review and acceptance gates. Do not launch eight competing implementation agents.

## What wins this challenge

Finish one workflow: **saved visitor feedback → local evidence-backed findings → a Swahili decision card → Noor approves one exact follow-up → durable offline queue**. Demonstrate that journey on the actual, already-owned household phone, with airplane mode on and Wi-Fi and Bluetooth also off. Force-close and restart it, then show that the approval and queue persist. Compare its findings with a manual reading and a simple keyword/template baseline.

The judged workflow does not need a live call, live WhatsApp, a cooperative-funded new device, cloud reasoning, an agent marketplace or all five roadmap phases. The challenge allows text or voice in a named local language; clear, native-reviewed Swahili text is the first gate. The product vision remains broader.

## Start order

1. Carther shares these files with the existing sessions and identifies the actual Sauti Senti room, repository, deadline and test phone. Read the existing room kickoff and repo instructions before adapting this addendum.
2. Platform inventories FencesNGates, AIdenID and Senti from the PC's authenticated GitHub access. Domain publishes contract r1.0. Mobile independently proves one real local model response on the phone. Experience prepares the three-screen interaction and language-review sheet. These four initial tasks can run together.
3. Freeze the shared contract after Platform/Domain review; implement against it. Platform alone changes shared root dependencies and integrates the branches. Contributors work in their assigned folders.
4. Deliver the offline workflow before enabling the optional Azure sync or voice branches. Hold the final quarter of the available time for device proof, review, measurement and the required 2–5 minute submission video.

## Read order

Builders: this file → 01_BUILD_SPEC.md → your packet → 11_ACCEPTANCE_AND_EDGE_CASES.md → repo/AGENTS.md. Read only the relevant parts of SOURCE_REGISTER.md and teammate packets when needed. Pseudocode is a design sketch, not tested or deployable code.

The active team is **Carther, Cosme de Ranieri, Nathanael (Nat) Muller and Maximilien (Max) Rambaud**, as Carther confirmed. Carther owns integration and the demo with Claude Experience; Cosme owns buyer economics and distribution; Nat owns independent evaluation and conflict tests; Max owns model/device experiments and language-data provenance. Teammates: this file → your named packet → 10_ROOM_ADDENDUM.md. Your role is a recommendation from the profiles you shared, not an assignment based on assumed abilities or language fluency.

## Important gates

- **Team eligibility:** your confirmed four-person roster meets the public team-size cap. Individual registration, age eligibility, roster timing and the applicable submission rules remain the team's responsibility. Source S02.
- **Actual hardware:** Android is the implementation target. The phone's OS, ABI, RAM, free storage and availability still need measurement. If only an iPhone is available, report that immediately; this Android plan is not proof on that device.
- **Speech:** neither native-speaker review nor on-phone Swahili speech quality is complete. Voice remains gated. Do not label generated Swahili as validated.
- **Access:** this workspace's GitHub connector returned no accessible repositories. Your PC sessions should have your broader access, as you stated; reusable source components remain unverified here.
- **Room:** no exact Sauti room identifier or existing kickoff was retrieved. The prepared addendum has not been posted. Do not publish into an older project room by guessing.

## Scope authority

Carther owns material product decisions. Routine implementation, review and reversible fixes proceed within this agreed scope. Changes that move inference to a server, loosen Noor's approval, introduce noncommercial/proprietary runtime models, silently invent business facts or substitute funded hardware for the existing-device proof require an explicit roadmap decision. Document a proposal; do not implement it as an invisible fallback.

The kit adds implementation safeguards and measurable gates to your roadmap. It does not certify a working product, completed integrations, native-reviewed language, scalability, revenue or a competition win.
