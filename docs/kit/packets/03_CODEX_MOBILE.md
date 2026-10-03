# Codex Mobile — primary builder packet

Suggested room alias: Codex Mobile. Use your actual existing session identity.

## Your mission

Deliver the real Android offline core on an actual phone. You own apps/mobile, native model integration, encrypted local storage, import, the three-screen UI implementation and on-device measurements. Carther's PC provides authenticated access to FencesNGates, AIdenID and Senti; consult Platform's reuse inventory and inspect source before adapting it. Do not assume a prior web demo proves offline Android inference.

Read 00_START_HERE.md, 01_BUILD_SPEC.md, your actual repo instructions, 11_ACCEPTANCE_AND_EDGE_CASES.md and the frozen contracts. Coordinate native dependency choices with Platform. You own mobile files; Experience supplies interaction/copy/assets rather than editing these same files.

## First gate

Record phone model, OS, ABI, RAM, available storage and test availability. Install a native/release-capable build, load a pinned local Qwen3 0.6B quantization and produce one real answer with airplane mode on and Wi-Fi/Bluetooth separately off. Record actual model bytes, load time, inference time and memory. Add a persistent encrypted record and show it after force-close/restart. Present unsupported devices honestly.

Initial plan: React Native plus llama.rn / llama.cpp and a tested current SQLCipher Android adapter. Expo Go is not the test artifact. JS, model weights, tokenizer/template and required assets must exist on-device; no dev server or remote model download during the offline demonstration. CPU first, one model task at a time, short context/output. Set the Qwen nonthinking template only if verified in the pinned runtime. Report a failure quickly; don't silently mock the result or use a server.

## Implementation

1. Sideload/import a versioned model/data pack by USB or local file. Verify manifest/hash and license; an interrupted update cannot replace a working model. Download is an optional convenience, not bootstrap dependence.
2. Save immutable original feedback and separate normalized display records. Use stable source IDs/hashes and exact UTF-8 evidence spans supplied by the core contract.
3. Call the local model for bounded extraction. Validate structured output with Domain's schema. Show an explicit uncertain card on failure rather than repairing JSON by inventing fields.
4. Render Today, Evidence and Outbox from the frozen Experience spec. Preview exact recipient/channel/payload. Use a single local owner approval call with the digest of what was rendered; do not build a second approval state machine in UI code.
5. Persist proposal/approval/outbox atomically. Test a crash/restart after approval. Send only through the frozen transport adapter after separate authorization checks. Fake transport stays visibly simulated.

Keep the UI responsive: cancellation, progress, retry, low-storage handling and one inference task queue. Large-font labels plus icons, shared-phone lock and explicit pending/send_unknown states. A helper can import feedback but cannot approve outgoing actions. Keys stay in Keystore-backed storage where available; back up only encrypted data under a documented recoverable-key policy. Never promise hardware-backed keys on every cheap phone.

## Speech boundary

Swahili text is enough for Phase 1 if native-reviewed. Optional local Whisper listens to the microphone, not an ordinary SIM call. Reviewed audio assets can explain fixed UI states; they must not imply an unapproved message was spoken. Dynamic local TTS is only added after actual memory/latency/license testing. LiveKit is a later connected audio path and must not introduce a hidden cloud reasoning step.

## Evidence you must hand off

- Exact source/runtime/quantization/asset revisions and hashes, phone specs, install instructions, model pack size and APK size separately.
- Warm/cold timings and observed peak memory; test conditions and number of runs. Desktop tokens/sec is not a phone measurement.
- Airplane-mode journey recording, restart proof, model-failure and low-storage behavior.
- Passing core tests plus mobile integration tests for rendered-digest matching, pending restore and source deep links.
- Any permission, battery/background or Android compatibility limitation still unresolved.

Max owns independent model experiments and provenance; share the one test phone by a short reservation file rather than run competing measurements. Nat supplies adversarial fixtures. Experience reviews interface/copy. Platform reviews integration and key/transport boundaries.

## Communication

Claim your lane and ACK the contract revision once in the verified Senti room. Keep ongoing status in your artifact/checkpoint. Thread blockers; emit a single HANDOFF with commit, paths, commands/results, device evidence and next owner. No chatter while builds run, no raw logs or secrets. You may request one bounded read-only diagnostic helper for a specific issue; don't start another agent editing apps/mobile.
