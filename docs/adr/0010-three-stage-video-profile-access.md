# Expose video profiles through catalog, detail, and runtime extraction

The Agent interface provides a lightweight video profile catalog for filtering and semantic ranking, loads complete profile details only for shortlisted video IDs, and reads source-video bytes only for authorized runtime frame or clip extraction. This keeps downstream contexts bounded while preserving access to detailed time-coded semantics and real footage when a concrete planning decision requires them.
