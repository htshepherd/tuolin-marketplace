# Invalidate video profiles when source or analysis policy changes

Each video content profile is bound to the source-video fingerprint, source-classification fingerprint, profile schema version, and analysis-policy version. A mismatch blocks publication of stale semantic content until re-analysis succeeds, while the underlying video asset may remain registered. Active video-creation runs keep their locked Agent-interface revision and never switch profiles silently.
