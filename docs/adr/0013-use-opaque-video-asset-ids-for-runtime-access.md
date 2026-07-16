# Use opaque video asset IDs for runtime source access

Downstream contexts and runtime extractors refer to registered source videos through opaque video asset IDs rather than raw filesystem paths. The knowledge producer privately resolves each ID and validates product scope, profile revision, allowed operation, task identity, timestamp bounds, and revocation before reading the source. This makes `raw_access=false` enforceable and keeps downstream contracts stable when source directories move.
