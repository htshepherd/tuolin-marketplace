# Use Codex directly for video semantic review

The current release uses Codex as the semantic reviewer for video profiles and does not require the operator to configure a separate multimodal-model API key. The knowledge producer uses deterministic local tools to prepare bounded frames, necessary short clips, media facts, folder classification, and available transcript evidence; Codex inspects those inputs and proposes the structured video semantics.

Codex does not receive unrestricted raw-directory browsing authority, and its proposal is not published directly. The result must pass profile-schema, source-link, timestamp, representative-frame, risk, and revision validation before it can enter formal knowledge. If the current Codex environment cannot inspect the prepared visual inputs, batch preflight blocks processing instead of calling an unknown external service or generating filename-based semantics.
