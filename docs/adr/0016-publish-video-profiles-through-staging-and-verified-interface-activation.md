# Publish video profiles through staging and verified interface activation

Each source video is processed atomically into a resumable staged checkpoint. A checkpoint contains the prepared-input manifest, Codex semantic proposal, human-readable profile draft, machine-validatable profile structure, representative-frame references, validation result, and processing state. Staged checkpoints are available to the knowledge-review workflow but invisible to downstream consumers.

Accepted profiles become formal knowledge only through one publication transaction that promotes the allowed profile files, rebuilds the Agent interface, verifies the expected catalog, detail, media references, and revision, and then activates the new interface version. If any step fails, the new version is not activated and downstream consumers continue using the previous verified interface. This preserves recoverability without exposing partial or stale knowledge.
