---
status: accepted
---

# Use operator keywords without product binding for LinkedIn prospect search

New `tuolin-linkedin-search` runs are driven by an operator-supplied ordered list of exact LinkedIn Posts search phrases and do not resolve a formal product or require the knowledge-base Agent interface. Testing showed that mandatory product binding added a blocking dependency without improving execution, while the operator already owns the market vocabulary and final candidate judgment; AI therefore performs only provisional screening from the source phrase and visible LinkedIn evidence, never expands the keyword list, and drafts enabled invitation notes without product or company claims. Runs still require durable writable task storage for candidate review, deduplication, recovery, and invitation limits. Product-bound test runs are not migrated because the workflow is still in its test phase. This decision supersedes ADR-0020.
