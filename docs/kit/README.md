# Sauti Host shared build kit

Original kit r1.0, prepared 3 October 2026. The Markdown packets are extracted from the original HTML document's copy-source textareas with HTML entities decoded. The HTML is preserved byte for byte, including the illustrative contracts/pseudocode appendix. These documents are design instructions, not evidence of a working implementation.

## Read order

[Start here](00_START_HERE.md) → [build specification](01_BUILD_SPEC.md) → your [lane packet](packets/) → [acceptance matrix](11_ACCEPTANCE_AND_EDGE_CASES.md). [Source register](SOURCE_REGISTER.md) records the kit's source claims and original unknowns; builders must verify current dependencies and record achieved results separately.

`repo/AGENTS.md` is the original scoped starter stored here for review. It has not replaced the repository's actual root instructions. The original source is [Sauti_Host_Build_Playbook.html](Sauti_Host_Build_Playbook.html).

## Current room decisions take precedence

Senti session: `4fabea10-ab74-4998-beb9-8918f0e497f9`.

- Event `47461` supersedes the kit's main-merge instructions: each builder works on its own branch and sends a reviewed HANDOFF to `claude-warden`. Warden opens PRs and merges green reviewed slices. No direct pushes to main.
- Platform (`codex`) owns contracts publication, root configuration/lockfiles and integration decisions. Domain (`fable-5.1-nav`) owns `packages/core` and jointly reviews the contract freeze. Mobile (`codex-mobile`) owns `apps/mobile` and real Android proof. Experience (`cosme-claude`) was confirmed by Carter in event `47463`.
- Contract drafts and fixture test passes are not a contract freeze. Platform and Domain must agree on the exact reviewed revision; Experience is then rebased onto it for a slice limited to its owned files (event `47465`).
- The room is connected and Mobile has claimed its lane. The actual test phone and native Swahili review remain unproved at publication. Every acceptance row stays UNRUN until actual evidence is recorded.
- Carter's device decision relayed in event `47479` supersedes the kit's Android implementation target: use a real iPhone/iOS native React Native build, local llama.rn/Metal inference with a pinned bundled model, tested encrypted SQLCipher persistence and Keychain-protected keys. CI and build documentation must cover iOS. The exact iPhone inventory and Mac/Xcode or EAS/signing path are still required; no on-device result is claimed. The core, contracts and Azure boundaries remain the same. Keep airplane mode on and Wi-Fi/Bluetooth off for the offline proof.

## Provenance

Original HTML SHA-256: `53bb3a789bcf7130465c148c85fb818ebe8b3f213f65821f311b546c9df8c69a`.

The original kit is archived unchanged. Later room decisions appear in this index rather than silently rewriting the supplied packets. No third-party implementation or runtime model is bundled here.
