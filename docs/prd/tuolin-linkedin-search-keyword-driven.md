# Keyword-Driven LinkedIn Prospect Search

> Status: Confirmed locally on 2026-07-23. This PRD supersedes the product-bound run design for all newly created test runs. It is intentionally not published to an issue tracker.

## Problem Statement

The current `tuolin-linkedin-search` workflow requires every prospect-search task to resolve one formal Tuolin product through a verified knowledge-base Agent interface before it can begin its interview. Real testing showed that this prerequisite adds friction without improving the operator's immediate task: the sales operator already knows the exact market phrases to search, and LinkedIn Posts discovery can be evaluated from those phrases and visible LinkedIn evidence.

The current browser orchestration also treats a temporarily visible footer or one stalled load as evidence that a LinkedIn Posts result stream is exhausted. In a real `exhaust wrap`, `Latest`, `Past month` test, the workflow stopped after six visible posts even though manual scrolling exposed more results. LinkedIn uses infinite scrolling rather than reliable `page=2` pagination, so the current exhaustion signal can end discovery prematurely and prevent the workflow from finding the requested candidate count.

AI screening is useful for removing obvious noise, but it cannot reliably decide whether every plausible company is an actual buyer. A company may look relevant while being a direct competitor, an installer without purchasing authority, or a channel brand that sources externally. The operator must therefore see the complete source post and identity evidence before making the final candidate decision. AI output must remain provisional and must never be presented as a confirmed customer or qualified lead.

## Solution

Convert new LinkedIn prospect-search runs into operator-keyword-driven workflows. A run starts from one or more complete search phrases supplied by the operator and no longer selects a formal product, validates a knowledge interface, generates keyword suggestions, or reads product knowledge. It retains a writable task workspace for durable run state, candidate cards, shared deduplication, recovery, and rolling invitation limits.

The interview resolves only six executable decisions: ordered keyword phrases, Posts sort, publication range, note/no-note, fixed dispatch interval, and maximum invitations. The keyword question provides format guidance but never proposes keyword content. Every phrase is searched independently and intact in the operator's order.

For each phrase, the Chrome workflow continues infinite scrolling until the reviewable candidate pool reaches the effective run limit, fifty unique opened posts have been evaluated, or three consecutive bottom-scroll-and-load-wait cycles produce no new unique post identity. A footer, advertisement, one delayed load, current rendered count, or discarded `page=2` parameter is not exhaustion.

AI performs provisional visible-evidence screening. Obvious noise and direct same-material manufacturers are skipped. Plausible downstream users and channel prospects may proceed to human review even without a public RFQ. A reviewable candidate must have a verifiable personal LinkedIn profile, a standard Connect path, and clear deduplication eligibility. Every candidate card prints the complete visible source post, URL, author/company evidence, selected member evidence, AI reasoning, and uncertainty in Codex. The operator approves or removes candidates as a batch; removals are never automatically replaced.

Existing account binding, explicit browser authorization, shared-ledger reconciliation, invitation limits, final batch authorization, fixed dispatch interval, sequential sending, durable outcome recording, and platform-level stop behavior remain in force.

## User Stories

1. As a Tuolin sales operator, I want to start a LinkedIn prospect-search run with keywords alone, so that I do not need to identify a formal product first.
2. As a Tuolin sales operator, I want the run to work without a knowledge-base Agent interface, so that missing or stale product knowledge does not block search.
3. As a data steward, I want supplied keywords to remain task-local search vocabulary, so that they do not become product names, facts, specifications, or claims.
4. As an operator, I want each run stored in a writable workspace, so that browser interruptions do not erase progress.
5. As an operator, I want candidate cards, decisions, and completion state persisted, so that the run can be reviewed and audited.
6. As an account owner, I want shared contact history to persist across runs, so that the same person or company does not repeatedly appear.
7. As a maintainer, I do not want product-bound test runs migrated, so that the test-phase redesign can remain simple and explicit.
8. As a maintainer, I want product-bound test runs rejected or retired clearly, so that old and new schemas are not silently mixed.
9. As an operator, I want every new task explicitly started through natural language, so that no unattended recurring search begins automatically.
10. As an operator, I want the run brief to state that it is keyword-driven, so that nobody assumes hidden product grounding.
11. As an operator, I want the interview to ask only unresolved decisions, so that information in my initial request is not repeated.
12. As an operator, I want the interview limited to six executable decisions, so that every answer affects LinkedIn search or invitation behavior.
13. As an operator, I want the keyword question to wait for my input, so that AI does not guess my market vocabulary.
14. As an operator, I want the keyword question to explain accepted separators, so that I can paste a comma-, semicolon-, or line-separated list.
15. As an operator, I want a valid custom answer saved once and followed by the next question, so that numbered questions do not repeat.
16. As an operator, I want `确认` to accept only the recommendation shown for the current question, so that later decisions are not approved accidentally.
17. As an operator, I do not want one reply to accept every remaining recommendation, so that unresolved external-action decisions remain explicit.
18. As an operator, I want missing sort order to recommend `Latest`, so that recent commercial activity is prioritized.
19. As an operator, I want missing publication range to recommend `Past month`, so that search balances recency and volume.
20. As an operator, I want note/no-note to remain a per-run decision, so that outreach text is never assumed.
21. As an operator, I want a five-minute fixed interval recommended when pacing is unspecified, so that dispatch behavior is predictable.
22. As an operator, I want a default maximum of ten invitation successes when no number is supplied, so that every run is bounded.
23. As an operator, I do not want geography asked for Posts search, so that the interview does not collect an unusable condition.
24. As an operator, I do not want product, category, knowledge-base, keyword-language, or AI-keyword questions, so that the interview remains executable.
25. As an operator, I want every comma- or line-separated item treated as one complete search phrase, so that multi-word phrases remain intact.
26. As an operator, I want `Motorcycle Exhaust Wrap` searched as one entered query, so that the workflow does not split it into unrelated terms.
27. As an operator, I want every phrase searched independently, so that the whole list is not merged into one uncontrolled query.
28. As an operator, I do not want Boolean composition inferred, so that commas and newlines mean separate searches only.
29. As an operator, I do not want phrases translated, corrected, or expanded, so that the workflow stays within my approved scope.
30. As an operator, I want phrases processed in my order, so that earlier market language has priority.
31. As an operator, I want the first phrase treated only as the first priority, so that a separate “main keyword” field adds no hidden behavior.
32. As an operator, I want exact duplicates removed case-insensitively, so that repeated phrases do not waste a search.
33. As an operator, I want the first duplicate occurrence to keep its position and spelling, so that my priority and visible wording are preserved.
34. As an operator, I do not want a keyword whitelist, so that new market phrases can be used without a release.
35. As an operator, I do not want a fixed phrase-count ceiling, so that the examples do not become an artificial supported list.
36. As an operator, I want the run brief to show the deduplicated keyword count and complete order, so that I can verify parsing before browser work.
37. As an auditor, I want every evaluation and candidate to retain its exact source phrase, so that discovery provenance is never lost.
38. As an operator, I want the workflow to use LinkedIn Posts before People, so that candidates originate from visible topical evidence.
39. As an account owner, I want browser work performed only through the official Codex Chrome extension, so that it uses my signed-in Chrome profile.
40. As an account owner, I want read-only browser authorization before account binding and discovery, so that browser access remains human-controlled.
41. As an account owner, I want the visible LinkedIn member name and profile URL bound to the run, so that the acting account is explicit.
42. As an account owner, I want the workflow to stop if the LinkedIn identity is missing or changes, so that actions cannot move to another account silently.
43. As an account owner, I do not want passwords, cookies, OTPs, local storage, or session data persisted, so that authentication stays in Chrome.
44. As an operator, I want each phrase searched with the confirmed sort and publication range, so that browser actions match the brief.
45. As an operator, I want infinite scrolling to continue while the candidate pool is below the effective limit, so that six initially visible posts are not treated as the whole result set.
46. As an operator, I want advertisements excluded from post counts, so that paid placements do not consume inspection capacity.
47. As an operator, I want duplicate post URLs or URNs excluded from post counts, so that rerendered content is not reviewed twice.
48. As an operator, I want only actually opened and evaluated unique posts counted toward the fifty-post limit, so that visible placeholders do not end a phrase.
49. As an operator, I want a visible footer treated as temporary page state, so that it does not prove exhaustion.
50. As an operator, I want one stalled load treated as inconclusive, so that transient network delay does not end discovery.
51. As an operator, I do not want `page=2` used as a pagination strategy, so that LinkedIn's discarded parameter is not misread as a second-page result.
52. As an operator, I want three consecutive no-growth bottom-scroll cycles required for exhaustion, so that stopping has repeatable evidence.
53. As an auditor, I want each exhaustion cycle recorded with before/after unique counts, so that premature termination can be diagnosed.
54. As an operator, I want a phrase to advance only after candidate limit, fifty evaluated posts, or verified exhaustion, so that switching cannot occur arbitrarily.
55. As an operator, I want the next phrase searched when the current phrase ends below the candidate limit, so that later combinations work as fallbacks.
56. As an operator, I want discovery to stop once the reviewable candidate pool reaches the effective run limit, so that later phrases do not create unusable excess cards.
57. As an operator, I do not want the workflow to invent keywords or relax filters to fill a batch, so that discovery remains authorized.
58. As an operator, I want obvious homonyms, incidental mentions, consumer posts, unrelated news, software terms, and spam skipped, so that clear noise does not enter review.
59. As an operator, I want a visible direct manufacturer of the same or substitutable base material skipped as a competitor, so that supplier promotions are not mistaken for buyer intent.
60. As an operator, I want downstream installers and contractors considered provisionally, so that lack of a public RFQ does not exclude likely material users.
61. As an operator, I want fabricators, equipment makers, integrators, and project operators considered provisionally, so that finished-product users remain discoverable.
62. As an operator, I want brands, distributors, retailers, and private-label sellers considered provisionally, so that possible externally sourced channel customers are not filtered as competitors automatically.
63. As an operator, I want unclear make-versus-source evidence exposed as uncertainty, so that AI does not pretend to know a company's supply model.
64. As an operator, I want AI screening labeled provisional, so that a plausible company is not presented as an actual buyer.
65. As an operator, I want each provisional decision to contain visible supporting evidence and material doubts, so that I can judge it independently.
66. As an operator, I want a verifiable personal profile required for a candidate, so that the batch contains people rather than unconnectable company pages.
67. As an operator, I want a standard visible Connect path required, so that Follow, Message, InMail, email guessing, or identity bypass is never substituted.
68. As an operator, I want one prioritized contact resolved for a company-authored post, so that the workflow does not invite several employees from one company.
69. As an operator, I want contact priority to remain Owner/Founder, Procurement/Purchasing/Sourcing, Managing Director/General Manager, then Product Manager, so that selection stays commercially plausible.
70. As an operator, I want a relevant company without a resolvable connectable member recorded as an unresolved lead, so that the evidence is retained without fabricating a candidate.
71. As an operator, I do not want unresolved leads to consume one of ten candidate slots, so that discovery continues for actionable people.
72. As an operator, I want every candidate checked against the shared ledger and live LinkedIn state before review, so that sent, pending, connected, reserved, or ambiguous members do not reappear.
73. As an operator, I want every candidate card printed directly in Codex, so that I do not need to open internal files to review it.
74. As an operator, I want the complete visible source-post text printed, so that a summary cannot hide context material to my decision.
75. As an operator, I want the post URL, source phrase, author, company, selected member, title, company, profile URL, and Connect evidence printed, so that the proposed action is traceable.
76. As an operator, I want the AI relevance reason and uncertainty printed, so that I can challenge the provisional judgment.
77. As an operator, I want candidate cards persisted as matching Markdown and JSON, so that human review and deterministic execution use the same evidence.
78. As an operator, I want to approve or remove candidates as a batch, so that final judgment remains efficient and human-controlled.
79. As an operator, I do not want AI to label a card as a confirmed customer or qualified lead, so that provisional discovery is not overstated.
80. As an operator, I do not want removed candidates automatically replaced, so that the review set cannot change behind my back.
81. As an operator, I accept a final approved batch smaller than ten, so that the invitation maximum is not treated as a quota.
82. As an operator, I want a new task required for more candidates after review, so that further discovery receives a fresh brief.
83. As an operator, I want no invitation sent before the exact candidate batch is approved, so that viewing a card is never treated as authorization.
84. As an operator, I want an enabled invitation note drafted in concise English from keyword scope only, so that no product knowledge is invented.
85. As an operator, I want a generic industry-connection note when phrases have no safe common topic, so that AI does not force an unsupported product description.
86. As an operator, I want to confirm or edit the exact note before it enters the brief, so that external text remains human-controlled.
87. As an operator, I want one confirmed note reused unchanged across the batch, so that execution cannot personalize or rewrite it silently.
88. As an operator, I want dispatch to pause if LinkedIn cannot send the approved note, so that it cannot silently downgrade to no-note invitations.
89. As an account owner, I want the effective run limit to remain the lesser of the requested limit and remaining locally recorded rolling capacity, so that the batch respects the local operating boundary.
90. As an account owner, I want no more than 100 skill-recorded invitation successes in any rolling 168-hour window for one bound account, so that cross-run capacity remains bounded.
91. As an account owner, I want the workflow to disclose that manual LinkedIn actions are not counted, so that the local ceiling is not presented as complete account history or an official LinkedIn rule.
92. As an operator, I want final authorization to display the bound account, exact candidates, count, note, interval, and effective limit, so that permission is specific.
93. As an operator, I want invitations dispatched sequentially with the confirmed interval, so that each external outcome is recorded before the next action.
94. As an operator, I want a candidate-local failure recorded before continuing, so that one missing Connect path does not erase other approved candidates.
95. As an account owner, I want restrictions, CAPTCHA, security checks, logout, or repeated unexplained failures to stop the full batch immediately, so that execution does not continue through ambiguous platform state.
96. As an operator, I want ordinary interruptions reconciled against durable state before any continuation, so that recovery cannot duplicate an invitation.
97. As an operator, I do not want automatic restart after a platform-level stop, so that a new task and authorization are required.
98. As an operator, I want completion reports to distinguish succeeded, skipped, failed, unresolved, and unexecuted items, so that the result is auditable.

## Implementation Decisions

- Replace mandatory product resolution with a keyword-only run-creation contract. Run creation validates writable operational storage but does not validate or consume the knowledge-base Agent interface.
- Introduce a new run schema for keyword-driven test runs. Product fields and product-context identifiers are absent; old product-bound test runs are not migrated.
- Keep the run store as a deep persistence boundary owning atomic state transitions, human-readable artifacts, machine-readable artifacts, status history, and safe reload.
- Refactor the interview engine around the six-field Keyword-Driven Interview Scope. The keyword field has a required-input prompt rather than a recommended value; the other fields retain deterministic recommendations and current-question confirmation.
- Extract a keyword-list parser with one stable interface returning ordered, intact, case-insensitively deduplicated phrases plus display metadata. It owns supported separators and rejects an empty result without translating, splitting, correcting, or expanding content.
- Preserve exact source-phrase provenance throughout search progress, post evaluation, unresolved leads, candidate cards, review artifacts, and reports.
- Keep the browser adapter on the official Codex Chrome extension. Do not add a repository-owned browser, headless mode, full-CDP requirement, or built-in Browser fallback.
- Extract an Infinite Scroll Evidence Tracker as a deep deterministic module. It records unique post identities, opened/evaluated counts, before/after counts for bottom-scroll cycles, consecutive no-growth cycles, and the only legal keyword stop reasons.
- Require three consecutive bottom-scroll-and-load-wait cycles with no new unique post URL or URN before exhaustion is accepted below the candidate and inspection limits.
- Count only unique, actually opened and evaluated posts toward the fixed fifty-post inspection limit. Exclude advertisements, placeholders, and duplicate identities.
- Reject an early `finish-keyword` transition unless the candidate limit, inspection limit, or verified exhaustion contract is satisfied.
- Keep ordered phrase fallback progression: advance after verified exhaustion or inspection limit when the candidate pool is short; stop all discovery when the pool reaches the effective run limit.
- Extract a Prospect Classification Policy behind a narrow semantic interface. It receives the source phrase and visible post/author/company/profile evidence and returns obvious skip, provisional fit, or unresolved relevant lead with reasons and uncertainty.
- Treat direct same-material manufacturers as competitor skips; treat downstream users and same-category channel businesses as provisional rather than confirmed buyers; expose ambiguous make-versus-source evidence for human review.
- Keep deterministic policy separate from AI judgment. Deterministic code validates that classifications have evidence and allowed outcomes but does not invent commercial conclusions.
- Keep the contact resolver's one-contact-per-company behavior, role priority, verifiable personal identity requirement, and standard Connect eligibility gate.
- Add unresolved-relevant-lead persistence. These records retain post/company evidence but are not reserved as candidates and do not count toward the effective candidate limit.
- Update the candidate review renderer so the Codex-visible card and persisted Markdown/JSON include the complete visible post text rather than only a summary, plus all identity evidence and provisional uncertainty.
- Preserve shared cross-run person/company/post deduplication, account-scoped reservations, live-state reconciliation, rolling-capacity enforcement, fixed dispatch pacing, two-phase dispatch recording, and platform-stop behavior.
- Keep the approved candidate batch immutable. Human removals release reservations as appropriate but never reopen discovery or trigger backfill.
- Generate an enabled invitation note from confirmed keyword scope only. The note generator cannot access product knowledge and must fall back to generic industry-connection language when no common topic is safe.
- Update natural-language routing, installation preflight, Skill instructions, source/plugin mirrors, manifests, documentation, and package tests together so the installed plugin exposes the new contract consistently.

## Testing Decisions

- Tests assert externally observable state transitions, persisted artifacts, rendered prompts/cards, and legal stop conditions rather than private helper structure or brittle LinkedIn markup.
- Unit-test the keyword parser with English phrases, mixed comma types, semicolons, newlines, whitespace, quotes, case-insensitive duplicates, empty input, preserved order, and multi-word phrase integrity.
- Unit-test interview behavior so keyword input has no AI recommendation, existing answers are skipped, a custom answer advances once, question numbering remains monotonic, `确认` accepts only the current recommendation, and blanket remaining confirmation stays unsupported.
- Unit-test keyword-driven run creation in a writable workspace with no product cards, manifest, Agent interface, or knowledge context.
- Test that product fields and product-context identifiers are absent from the new run schema and that old product-bound runs are not silently migrated.
- Unit-test the Infinite Scroll Evidence Tracker with unique URLs/URNs, duplicate posts, advertisements, loading growth, one or two no-growth cycles, the third qualifying cycle, and reset of the no-growth counter when a new post appears.
- Unit-test all legal keyword completion paths: candidate limit reached, fifty unique evaluated posts reached, and verified exhaustion. Reject a footer, one stalled load, rendered-result count, or failed `page=2` attempt as completion evidence.
- Integration-test ordered keyword fallback so later phrases run only while the candidate pool is short and exact source provenance survives into every artifact.
- Test that reviewable candidates, not relevant posts or unresolved companies, determine the candidate limit.
- Unit-test the classification contract using representative fixtures from the real review: direct fiberglass-material supplier, downstream kitchen-exhaust installer, unrelated `dual exhaust` joke, insulation-product fabricator, software integer wraparound, and fiberglass-tape sales manager.
- Test direct-manufacturer skips, downstream-user provisional fits, channel-prospect provisional fits, obvious-noise skips, and ambiguous make-versus-source uncertainty without asserting a fabricated buyer status.
- Unit-test contact resolution, one-contact-per-company, role priority, personal-profile verification, ordinary Connect availability, and unresolved relevant leads that do not consume candidate slots.
- Unit-test candidate-card rendering so Markdown, JSON, and Codex output contain the complete visible post text, URL, exact source phrase, author/company evidence, selected-member evidence, AI reason, uncertainty, approval, note, and outcome.
- Test batch review so operator removals are honored, the approved subset may be smaller than the limit, and no discovery or backfill is triggered.
- Unit-test note generation without product context: keyword-common-topic note, generic fallback note, prohibited factual claims, exact human edit persistence, and byte-for-byte reuse.
- Re-run existing account binding, ledger normalization, cross-run deduplication, live-state reconciliation, rolling 168-hour capacity, account lock, final authorization, sequential dispatch, candidate-local failure, platform stop, and interruption recovery tests.
- Contract-test the Chrome adapter with fake observations for signed-in identity, Posts filter application, new post growth after scrolling, delayed loading, exhaustion evidence, Connect availability, pending/connected states, and platform warnings.
- Add a manual Chrome acceptance test that proves a result stream does not stop after six posts or a visible footer and that a complete candidate card appears in Codex before any send authorization.
- Keep source/plugin mirror tests and plugin validation so the installed Skill, runtime modules, manifests, and documentation remain synchronized.

## Out of Scope

- Selecting or resolving a formal Tuolin product for prospect search.
- Reading product knowledge, the Agent interface, raw knowledge files, campaign outputs, or knowledge-review artifacts.
- AI keyword generation, translation, spelling correction, synonym expansion, Boolean query construction, or filter relaxation.
- LinkedIn People search as the primary discovery path.
- Geography filtering when the Posts UI does not expose it.
- Treating provisional candidates as confirmed customers, qualified leads, or verified buyers.
- Lead scoring, confidence percentages, acceptance-rate optimization, conversion tracking, ROI measurement, or automatic learning from approvals.
- Connecting directly to company pages, selecting multiple contacts per company, guessing emails, scraping contact details, Follow fallback, Message, InMail, or post-acceptance messaging.
- Automatic replacement of candidates removed during human review.
- Migrating or resuming old product-bound test runs.
- Unattended scheduling, recurring background execution, headless Chrome, fingerprint spoofing, IP tunneling, stealth/evasion features, or account-safety guarantees.
- Managing LinkedIn passwords, OTPs, cookies, local storage, login recovery, or browser profiles.
- Counting manual LinkedIn invitations in the skill's rolling-capacity ledger or presenting the local limit as an official LinkedIn rule.
- Automatically resuming after a restriction, CAPTCHA, security checkpoint, or logout.

## Further Notes

- “Ten candidates” means at most ten reviewable, connectable candidate cards, not ten relevant posts and not a quota that must survive human review.
- A relevant company without a verifiable connectable member is useful discovery evidence but is not an actionable candidate.
- Human candidate review is the final qualification boundary. AI is intentionally optimized for reasonable recall after obvious-noise and direct-competitor filtering, while the operator owns precision.
- The three-cycle infinite-scroll rule is an auditable browser-exhaustion contract, not a claim that LinkedIn exposes a complete global result set. Results remain specific to the bound account, time, index, visibility, and personalization state.
- The fifty-post limit is an internal per-phrase inspection ceiling and is not asked in the business interview.
- The default run limit of ten and rolling 100-success/168-hour boundary remain local operating requirements, not LinkedIn-published limits or safety guarantees.
- ADR-0021 records the architectural removal of product binding and supersedes ADR-0020.
