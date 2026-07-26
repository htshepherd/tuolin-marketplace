# LinkedIn Human Review Pool and Cumulative Prospect Workbook

> Status: Confirmed locally on 2026-07-26. This PRD supersedes the discovery-volume, candidate-review, invitation-count, and dispatch-interval decisions in `Keyword-Driven LinkedIn Prospect Search`. It retains that PRD's keyword-only search scope, official Codex Chrome surface, visible-evidence boundary, account binding, deduplication, final authorization, ledger, and recovery rules. It is intentionally not published to an external issue tracker.

## Problem Statement

The keyword-driven LinkedIn search workflow still treats the requested invitation count as the maximum discovery pool. When a task asks to contact ten people, discovery stops after producing at most ten AI-screened candidate cards. Real tests show that roughly half of the resulting names may have low business relevance, so the boss may approve only two useful contacts even though LinkedIn contains many more posts and people that could have been considered.

The existing fifty-post inspection ceiling does not solve this problem. Fifty opened posts are raw search evidence, not fifty distinct people for the boss to compare. AI currently removes uncertain contacts before the boss sees them, and the workflow may stop a keyword after fifty inspected posts even when the human review pool is far below the desired size. The first broad keyword can also fill the pool before later, more specific keyword phrases are searched.

Review output is fragmented across runs. A large chat-only batch is difficult to compare, while separate spreadsheets lose cross-task history and create duplicate contacts. The boss needs one account-scoped cumulative workbook that preserves one row per person, appends repeated post evidence, exposes consistent review choices, and retains immutable dispatch history.

Discovery and dispatch capacity are also coupled too early. The current interview recommends ten invitations and a five-minute interval; account capacity is evaluated before browser discovery and can block search completely. The confirmed business workflow instead requires discovery first, human screening second, and selection-based dispatch third. The boss may select twelve people from a fifty-person review pool, use a fixed two-minute interval, or continue building the workbook while current seven-day dispatch capacity is zero.

Finally, the boss wants Codex to reason about each proposed contact before human review, but does not yet have a stable relevance standard. Codex must therefore perform a broad, evidence-based preliminary assessment, explain its recommendation and uncertainty, retain plausible ambiguous contacts, and learn from boss feedback only as cited evidence. It must never silently turn a few decisions into permanent screening rules.

## Solution

Replace invitation-sized discovery with a two-stage model: a configurable **Human Review Pool** followed by an independently selected dispatch batch. During the interview, ask “本次最多找多少个联系人给您筛选？”, recommend fifty, and accept a whole number from one through one hundred. Remove the pre-search invitation-count question. The pool counts only **New Review Contacts**: deduplicated, connectable members absent from the account's cumulative workbook when the run first encounters them.

Use **Balanced Keyword Sampling**. Every confirmed exact phrase receives a soft first-pass share calculated from the review-pool limit and keyword count. Exhausted phrases yield unused capacity to other phrases. After all phrases receive a first pass, productive phrases are revisited in original order until the pool is full or every phrase reaches **Verified Infinite-Scroll Exhaustion**. Remove the fixed fifty-post-per-keyword inspection ceiling. Do not expand keywords, change confirmed filters, or weaken hard eligibility rules when the pool remains short.

Apply broad-entry Codex screening. Automatically exclude only obvious semantic mismatches, direct manufacturers or suppliers of the same base category, duplicate or already-contacted members, and members without a verifiable ordinary Connect path. Plausible installers, contractors, integrators, fabricators, equipment makers, project operators, brands, distributors, retailers, private-label sellers, and other uncertain business roles enter human review. For every included contact, Codex produces a **Codex Preliminary Prospect Assessment** explaining visible evidence, likely business role, uncertainty, and a keep-or-remove recommendation. It does not output an unexplained score or claim buyer status.

Keep one member per company in the review pool. Resolve company-authored posts to Owner or Founder, Procurement or Sourcing, Managing Director or General Manager, Product Manager, then another visibly relevant responsible manager only when Codex records an explicit role-to-business selection reason. If no verifiable connectable person can be resolved, retain an **Unresolved Relevant Lead** outside the pool.

Create one **Prospect Review Workbook** for each bound LinkedIn account. All search runs for that account append to the same Excel file. The workbook contains:

- **Prospect Contact Sheet**: one current row per deduplicated member, including identity, company, connection state, first/latest discovery, a required Send/Exclude/Pending dropdown, and optional boss note.
- **Prospect Evidence Sheet**: one row per retained discovery occurrence, including run, keyword, complete post, post URL, Codex assessment, evidence, uncertainty, and contact reference.
- **Prospect Dispatch Sheet**: immutable authorized batch membership, note decision, fixed interval, timestamps, dispatch attempts, and outcomes.

Repeated contacts update the existing contact row and append new evidence without consuming a current-run pool position. Sent, invitation-Pending, connected, or Exclude contacts do not re-enter review. A boss-marked Pending contact remains in the workbook and may later be explicitly selected, but is not counted as newly found. Exclude contacts return only after the boss changes them back to Pending.

After screening, the boss makes a **Current Dispatch Selection** from new contacts and/or historical Pending contacts. Codex revalidates ledger state, live relationship state, company duplication, ordinary Connect eligibility, and seven-day capacity, then writes an immutable **Final Dispatch Snapshot** and reprints the exact selected people with source evidence before requesting final authorization. The selected count becomes the **Approved Dispatch Count**; there is no fixed ten-person per-run ceiling. The **Effective Run Invitation Limit** is the lesser of the approved count and remaining capacity under the existing rolling 168-hour, one-hundred-success account ceiling. Capacity reduction never silently chooses the first N contacts: the boss must confirm the exact reduced subset.

Recommend a fixed two-minute **Invitation Dispatch Interval**, accept whole-minute values of at least one minute, and keep the chosen value unchanged throughout the authorized batch. Zero remaining dispatch capacity blocks Connect but does not block search, Codex assessment, workbook updates, or boss review.

Persist **Prospect Review Feedback** from the dropdown and optional boss note. Later Codex assessments may cite previous decisions as context. Codex may summarize repeated keep, exclude, and contradictory patterns and propose reusable rules, but only a boss-confirmed **Confirmed Prospect Screening Rule** may alter future hard screening behavior.

## User Stories

1. As a boss, I want the workflow to find substantially more people than I may eventually contact, so that I can make the final relevance judgment.
2. As a boss, I want discovery volume separated from invitation volume, so that a ten-person sending idea does not limit me to ten names to review.
3. As an operator, I want the interview to ask “本次最多找多少个联系人给您筛选？”, so that the business question is immediately understandable.
4. As an operator, I want fifty contacts recommended when I omit a value, so that normal tasks produce a useful comparison set.
5. As an operator, I want to choose any review-pool limit from one through one hundred, so that quick tests and larger reviews use the same workflow.
6. As an operator, I want values outside one through one hundred rejected clearly, so that one task remains bounded.
7. As an operator, I want more than one hundred contacts handled through another run, so that the cumulative workbook can grow without one unbounded browser task.
8. As an operator, I do not want the initial interview to ask how many invitations to send, so that I do not decide before seeing the people.
9. As a boss, I want the final dispatch count determined by my selected contacts, so that selecting twelve people permits a twelve-person authorization request.
10. As a boss, I do not want a fixed per-run maximum of ten invitations, so that a reviewed batch is not arbitrarily truncated.
11. As an account owner, I want final sending bounded by remaining rolling seven-day capacity, so that the existing account rule remains enforced.
12. As an operator, I want discovery to continue when seven-day dispatch capacity is zero, so that I can prepare future contacts while waiting.
13. As an operator, I want Connect blocked when capacity is zero, so that discovery permission is not confused with send permission.
14. As an operator, I want capacity checked after selection and before final authorization, so that it reflects the latest ledger state.
15. As a boss, I want an exact reduced subset shown when selected count exceeds capacity, so that the system does not choose people for me.
16. As a boss, I want to reconfirm that exact reduced subset, so that capacity changes cannot silently alter authorization.
17. As an operator, I want exact keyword phrases preserved from the prior design, so that the review-pool redesign does not expand search scope.
18. As an operator, I want every supplied phrase searched independently, so that combination keywords remain separate LinkedIn queries.
19. As an operator, I want every keyword represented in the initial discovery pass, so that one broad phrase cannot monopolize the review pool.
20. As an operator, I want the soft first-pass share computed from pool size and keyword count, so that allocation adapts to each brief.
21. As an operator, I want soft shares rounded deterministically, so that the planned keyword distribution is explainable.
22. As an operator, I want keyword execution order preserved, so that ties and refill order respect my priority.
23. As an operator, I want a keyword allowed to contribute fewer contacts when it is exhausted, so that equal distribution is not a hard quota.
24. As an operator, I want unused shares redistributed, so that weak keywords do not prevent the pool from filling.
25. As an operator, I want productive phrases revisited after every phrase receives a first pass, so that unused capacity can be filled.
26. As an operator, I want the run to stop searching once the human review pool is full, so that it does not collect unusable excess contacts.
27. As an operator, I want all keywords allowed to finish below the target, so that an actual-size result is valid.
28. As an operator, I do not want missing contacts replaced by AI-generated keywords, so that search remains within the confirmed scope.
29. As an operator, I do not want sort, publication range, or other filters relaxed automatically, so that search behavior remains authorized.
30. As an operator, I want the fixed fifty-post inspection ceiling removed, so that low candidate yield does not end search prematurely.
31. As an operator, I want current keyword scrolling to continue while its soft share remains unfilled and results remain available, so that deeper posts can be evaluated.
32. As an operator, I want three consecutive bottom-and-wait cycles without new unique post identities required for exhaustion, so that stopping remains evidence-based.
33. As an auditor, I want each no-growth cycle persisted, so that the run can explain why a phrase ended.
34. As an operator, I want a newly discovered unique post to reset the no-growth counter, so that delayed loading does not cause false exhaustion.
35. As an operator, I want advertisements, placeholders, and duplicate posts excluded from new-evidence counts, so that they cannot manipulate exhaustion.
36. As an operator, I want progress restorable across interruption, so that balanced sampling does not restart from the first keyword.
37. As an operator, I want first-pass share, consumed share, exhaustion state, and refill eligibility persisted per keyword, so that resumption is deterministic.
38. As a boss, I want Codex to reason about every proposed contact before I see it, so that the workbook is more useful than a raw scrape.
39. As a boss, I want the Codex assessment based on the complete visible post, company, author, role, and keyword evidence, so that its reasoning is inspectable.
40. As a boss, I want the assessment to state likely commercial relevance, so that I understand why the contact entered review.
41. As a boss, I want the assessment to state the likely business role, so that I can distinguish installer, channel seller, manufacturer, and unrelated activity.
42. As a boss, I want material uncertainties shown, so that Codex does not hide weak evidence.
43. As a boss, I want a keep-or-remove recommendation, so that I can scan the workbook efficiently.
44. As a boss, I do not want an unexplained relevance score, so that numerical precision is not fabricated.
45. As a boss, I do not want Codex to call a contact a confirmed buyer, so that provisional evidence is not overstated.
46. As an operator, I want clearly unrelated semantic matches removed, so that obvious noise does not occupy review positions.
47. As an operator, I want direct manufacturers or suppliers of the same base category removed, so that known peers do not fill the customer pool.
48. As an operator, I want duplicate and already-contacted members removed, so that the boss does not repeat prior work.
49. As an operator, I want people without an ordinary Connect path removed from the actionable pool, so that every review position can lead to the intended action.
50. As a boss, I want uncertain but plausible installers and contractors retained, so that public RFQ evidence is not required.
51. As a boss, I want uncertain but plausible fabricators, equipment makers, integrators, and project operators retained, so that downstream-use opportunities remain visible.
52. As a boss, I want brands, distributors, retailers, and private-label sellers retained provisionally, so that sourcing uncertainty is left for human judgment.
53. As a boss, I want other plausible commercial roles retained with an explicit uncertainty note, so that Codex uses broad-entry screening.
54. As an operator, I want one review contact per company, so that one business opportunity does not occupy multiple positions.
55. As an operator, I want Owner or Founder prioritized, so that company contacts remain commercially responsible.
56. As an operator, I want Procurement, Purchasing, or Sourcing prioritized next, so that buying roles remain preferred.
57. As an operator, I want Managing Director or General Manager prioritized next, so that senior decision makers remain discoverable.
58. As an operator, I want Product Manager prioritized next, so that product-responsible contacts remain eligible.
59. As an operator, I want another responsible manager allowed only with an explicit Codex selection reason, so that useful companies are not discarded for title vocabulary alone.
60. As an operator, I want the next company member considered when a preferred member cannot use ordinary Connect, so that the company opportunity is not lost unnecessarily.
61. As an operator, I do not want multiple employees from that company kept simultaneously, so that fallback does not create duplicates.
62. As an auditor, I want unresolved relevant companies retained outside the pool, so that evidence is not discarded or counted as actionable.
63. As a boss, I want one cumulative Excel workbook for my LinkedIn account, so that every task contributes to one review history.
64. As an operator, I want another LinkedIn account to use another workbook, so that identities, decisions, and dispatch outcomes never mix.
65. As an operator, I want all runs for one account to locate the same workbook deterministically, so that append behavior does not depend on chat memory.
66. As an operator, I want workbook creation and updates atomic and recoverable, so that interruption cannot corrupt the master record.
67. As an operator, I want a backup or recoverable prior version before replacing the workbook, so that accidental file damage is not permanent.
68. As a boss, I want a Prospect Contact Sheet with one row per member, so that I can compare distinct people.
69. As a boss, I want name, title, company, country when visible, profile URL, and connection state in the contact row, so that I can identify the person quickly.
70. As a boss, I want first-seen and latest-seen timestamps, so that I know whether evidence is current.
71. As a boss, I want source keyword and source-run references, so that every contact remains traceable.
72. As a boss, I want a required Excel dropdown limited to 发送、排除、待定, so that decisions remain consistent.
73. As a boss, I want 待定 as the initial default, so that a new contact is never pre-authorized for sending.
74. As a boss, I want an optional 老板备注 field, so that I can explain important decisions without being forced to comment on every row.
75. As an operator, I want invalid free-text decision values rejected or normalized only through explicit review, so that typos cannot become dispatch instructions.
76. As a boss, I want a Prospect Evidence Sheet containing every retained source occurrence, so that repeated posts do not overwrite earlier evidence.
77. As a boss, I want complete visible post text and URL in the evidence row, so that summaries cannot hide material context.
78. As a boss, I want Codex reasoning, uncertainty, and recommendation stored with the evidence, so that later review sees the original assessment.
79. As an auditor, I want evidence rows linked to the stable contact identity, so that one person's multiple posts remain connected.
80. As an auditor, I want run ID, keyword phrase, and discovery time on every evidence row, so that provenance survives cumulative append.
81. As an account owner, I want a Prospect Dispatch Sheet with immutable batch membership and outcomes, so that sent history cannot be rewritten by screening edits.
82. As an account owner, I want note mode, exact note, interval, authorization time, attempt time, and outcome retained, so that every external action is auditable.
83. As an operator, I want repeated contacts to update their existing contact row, so that the master table has no duplicate people.
84. As an operator, I want a repeated contact's new post appended to evidence, so that later context is not lost.
85. As an operator, I do not want repeated contacts to consume a current-run review-pool position, so that “fifty new contacts” means fifty new people.
86. As an operator, I want sent, invitation-Pending, and connected contacts excluded from new review, so that no duplicate invitation is proposed.
87. As a boss, I want Exclude contacts omitted from later review by default, so that prior rejection is respected.
88. As a boss, I want an Exclude contact reconsidered only after I change it back to Pending, so that reactivation remains explicit.
89. As a boss, I want historical Pending contacts retained in the workbook, so that I can revisit them later.
90. As a boss, I want historical Pending contacts excluded from the count of newly found people, so that current-run statistics remain honest.
91. As a boss, I want to select historical Pending contacts together with newly found contacts, so that the cumulative workbook remains operationally useful.
92. As a boss, I want historical contacts included only after a current explicit selection, so that old decisions do not trigger automatic dispatch.
93. As an operator, I want every selected historical contact revalidated, so that stale profile and relationship state cannot enter authorization.
94. As a boss, I want rows marked for current sending copied into an immutable Final Dispatch Snapshot, so that later workbook edits cannot change the authorized set.
95. As a boss, I want Codex to reprint every selected person and source evidence before authorization, so that the workbook is not treated as invisible permission.
96. As an account owner, I want the exact account, selected members, count, note, interval, capacity, and snapshot digest shown, so that final authorization is specific.
97. As an account owner, I want no invitation sent before I confirm that snapshot, so that search and screening never imply sending permission.
98. As an account owner, I do not want per-member confirmation after the exact batch is authorized, so that sequential dispatch remains usable.
99. As an operator, I want the selected count to become the requested dispatch count, so that selecting twelve supports twelve invitations.
100. As an operator, I want capacity reduction to return to exact subset selection, so that the system never takes the first N rows automatically.
101. As an operator, I want a two-minute interval recommended, so that pacing matches the confirmed operating preference.
102. As an operator, I want to choose another whole-minute value of at least one minute, so that one- and two-minute tasks are both supported.
103. As an operator, I want sub-minute values rejected, so that the confirmed minimum remains enforceable.
104. As an operator, I want one fixed interval frozen in the final snapshot, so that dispatch cannot vary it automatically.
105. As an operator, I want the existing sequential preflight-click-result cycle retained, so that every outcome is known before the next contact.
106. As an operator, I want each success appended to the workbook dispatch history and shared ledger, so that Excel and runtime state agree.
107. As an operator, I want local failures and platform stops handled by the existing recovery contracts, so that this redesign does not weaken interruption safety.
108. As a boss, I want every Send, Exclude, or Pending decision persisted as review feedback, so that future reasoning can learn from my judgment.
109. As a boss, I want my optional note treated as stronger evidence than an inferred reason, so that explicit feedback has priority.
110. As a boss, I want blank-note decisions used only for weak, labeled inference, so that Codex does not invent my rationale.
111. As a boss, I want Codex to cite relevant historical decisions in later assessments, so that its reasoning improves transparently.
112. As a boss, I want repeated keep, exclude, and contradictory patterns summarized, so that a real screening standard can emerge.
113. As a boss, I do not want patterns activated automatically, so that a small sample cannot create a permanent false rule.
114. As a boss, I want proposed screening rules shown with supporting and conflicting examples, so that I can judge their reliability.
115. As a boss, I want only explicitly confirmed rules applied as future hard screening behavior, so that policy remains human-controlled.
116. As an auditor, I want every confirmed rule versioned with wording, scope, confirmation time, and evidence references, so that later behavior is explainable.
117. As a maintainer, I want old keyword-driven test runs left on their old schema, so that the redesign does not silently reinterpret active state.
118. As a maintainer, I want new runs use an explicit new schema version, so that runtime contracts cannot be mixed accidentally.
119. As an operator, I want an old run to stop with a clear new-task instruction when it reaches an incompatible transition, so that data is not silently lost.
120. As a maintainer, I want source runtime and packaged plugin mirrors remain byte-identical, so that business-computer behavior matches tests.

## Implementation Decisions

- Introduce a new workflow schema version for new runs. Do not mutate old test runs into the new model.
- Replace the interview field representing maximum invitations with `human_review_pool_limit`. The user-facing question is “本次最多找多少个联系人给您筛选？”, the recommendation is fifty, and valid values are integers from one through one hundred.
- Retain six interview decisions: ordered keyword phrases, Posts sort, publication range, note/no-note, fixed invitation interval, and human review pool limit.
- Change the fixed interval recommendation from five minutes to two minutes. Normalize only whole-minute values and reject intervals shorter than one minute.
- Remove the fixed per-keyword opened-post limit from new briefs and search progress. Verified infinite-scroll exhaustion remains the finite keyword boundary.
- Extract a deep **Review Pool Policy** module. Its stable interface accepts pool target, ordered phrases, per-phrase progress, workbook identities, and newly eligible contacts; it returns first-pass soft shares, next phrase, refill eligibility, pool completion, and search completion reasons.
- Soft first-pass shares sum to the pool limit and are deterministic. Remainders are assigned in original keyword order. Shares are goals, not hard quotas.
- Persist per-keyword states for first-pass target, newly contributed contacts, current stream position evidence, exhaustion, and refill eligibility. A run can resume without losing balanced allocation.
- Revisit productive phrases only after every non-exhausted phrase has received its first-pass opportunity. Preserve original order during refill.
- Extract a deep **Preliminary Prospect Assessment** contract. Input is limited to exact source phrase and visible LinkedIn post, company, author, role, profile, and Connect evidence plus explicitly permitted historical review feedback. Output contains business-role classification, supporting evidence, uncertainty, keep/remove recommendation, hard-exclusion reason when applicable, and cited feedback references.
- The assessment contract does not expose or require a numerical relevance score.
- Hard exclusion remains deterministic around four business classes: obvious semantic mismatch, direct same/base-category manufacturer or supplier, duplicate/already-contacted identity, and missing standard Connect eligibility.
- Broaden company contact resolution with one evidence-bound fallback role after the four preferred role groups. Keep one contact per company.
- Extract a deep **Account Prospect Workbook** module with a small interface for locating/creating the account workbook, loading identity and review state, upserting contacts, appending evidence, appending immutable dispatch records, reading current selections, and producing a dispatch snapshot.
- Derive workbook identity from the normalized bound LinkedIn account profile URL, not display name. Never combine two account identities in one workbook.
- The workbook contains three stable sheets: Contact, Evidence, and Dispatch. User-facing Chinese sheet names and column headers should remain stable once released.
- Contact rows use normalized LinkedIn profile URL as primary identity, with normalized company URL as a company-level deduplication dimension. Display names are never identity keys.
- Configure the boss-decision cell with Excel list validation limited to `发送`, `排除`, and `待定`. New contacts default to `待定`. Boss note remains optional free text.
- Store full posts in the Evidence sheet rather than concatenating multiple long posts into the Contact row. Link evidence rows back to the stable contact identity.
- Use atomic workbook replacement and retain a recoverable prior version before update. A malformed or locked workbook stops append loudly and leaves the prior file usable.
- Maintain run-local candidate JSON/Markdown as deterministic execution evidence. The workbook is the operator review projection, not the only source of runtime truth.
- Introduce a workbook synchronization receipt in each run containing workbook identity, pre/post revision, appended contact IDs, appended evidence IDs, and content digest.
- Count a Human Review Pool position only after contact/card persistence and successful workbook synchronization establish a New Review Contact.
- Repeated contacts append evidence and update latest-seen metadata but do not increment current-run pool count.
- Preserve the shared contact ledger for reservations and live connection outcomes. Reconcile workbook state and ledger state explicitly instead of treating Excel as the concurrency lock.
- Replace pre-search capacity-based discovery blocking with a dispatch-only capacity gate. Account binding records capacity for information but does not reduce the human review pool or block search at zero.
- Replace discovery's candidate-limit stop with human-review-pool completion. Invitation capacity is not consulted when deciding whether to continue searching.
- Create a **Current Dispatch Selection** reader that accepts newly marked Send contacts and explicitly selected historical Pending contacts from the same account workbook.
- Before snapshot creation, reconcile every selected contact against normalized account, member/company ledger identity, live LinkedIn state, standard Connect, and current rolling capacity.
- Create a deep **Final Dispatch Snapshot** module that freezes exact selected cards, assessment/evidence digests, note, interval, account identity, approved count, effective count, and capacity evidence.
- If current capacity is lower than selected count, do not slice automatically. Return a capacity conflict requiring the operator to choose and confirm the exact reduced subset.
- Remove the fixed default ten-person run limit from new runs. The selected subset supplies the approved dispatch count.
- Retain the rolling one-hundred recorded successes in one hundred sixty-eight hours per bound account. Continue disclosing that manual actions are outside the local count.
- Keep note generation, user review, fixed batch text, preflight, dispatch result recording, interruption reconciliation, platform stop, and restart behavior from the existing workflow.
- Append authorized membership and every terminal/non-terminal dispatch outcome to the Dispatch sheet while preserving the deterministic ledger as the authoritative concurrency and capacity record.
- Persist boss feedback separately from confirmed screening rules. Later assessment may cite feedback, but only a versioned, explicitly confirmed screening rule may change hard inclusion/exclusion policy.
- Add a rule-proposal projection that summarizes repeated Send, Exclude, Pending, boss-note, and contradictory examples without automatically activating a rule.
- Update the Codex-visible review response to show run totals, new versus repeated contacts, keyword contributions, hard exclusions, unresolved leads, workbook path/revision, and next instruction rather than printing fifty full cards inline.
- Before final authorization, print the complete selected subset and source evidence in Codex even though bulk screening occurred in Excel.
- Update installation preflight, skill instructions, natural-language responses, source/plugin mirrors, version metadata, and remote acceptance documentation together.

## Testing Decisions

- Tests assert externally observable state transitions, persisted artifacts, workbook contents, rendered prompts, dispatch authorization, and recovery outcomes. They must not assert private helper call order or internal implementation details.
- Preserve the existing end-to-end unittest style that creates a temporary workspace, starts a run through natural language/runtime APIs, advances deterministic browser observations, and inspects persisted state.
- Add pure contract tests for the Review Pool Policy: deterministic share allocation, remainder order, exhausted-share redistribution, all-keyword first pass, refill order, target completion, actual-size exhaustion, and interruption/resume.
- Add interview tests proving the new wording, default fifty, accepted one/one-hundred bounds, rejected zero/one-hundred-one, removal of pre-search invitation count, two-minute recommendation, and one-minute minimum.
- Add browser-state tests proving no fifty-post stop remains, pool completion stops search, one/two no-growth cycles do not exhaust, three cycles do, and a later unique post resets no-growth state.
- Add assessment contract tests for the six real review examples already used in testing: direct supplier, installer, semantic false hit, insulation-product fabricator, software terminology, and same-material sales manager.
- Add broad-entry tests for brands, distributors, retailers, private-label sellers, installers, contractors, fabricators, equipment makers, project operators, and ambiguous business models.
- Add hard-exclusion tests for direct category manufacturers, semantic noise, duplicate/live-state conflicts, and missing standard Connect.
- Add company-resolution tests for each preferred role, evidence-bound fallback role, unavailable preferred contact, one-contact-per-company enforcement, and unresolved relevant lead behavior.
- Add real `.xlsx` round-trip tests. Create a workbook, close it, reopen it through an independent reader, and verify sheet names, column values, full post text, formulas if any, and dropdown validation.
- Add account-scoping tests proving two normalized forms of the same profile share one workbook and two distinct account profiles never do.
- Add cumulative append tests across multiple runs: new contact, repeated member/new post, repeated company/different member, historical Pending, Exclude reactivation, sent/Pending/connected suppression, and latest-seen updates.
- Add workbook corruption/lock tests proving updates fail loudly without destroying the last good version.
- Add synchronization receipt tests proving run state identifies exactly what workbook revision and rows were written.
- Add tests proving a repeated workbook contact does not consume a current-run review-pool position.
- Add dropdown tests proving only the three Chinese choices are configured and new rows default to `待定`; boss note remains optional.
- Add feedback tests proving explicit notes are cited as stronger evidence, blank-note decisions produce only weak labeled inference, contradictory history is surfaced, and no rule activates without confirmation.
- Add selection tests for current new contacts, explicitly selected historical Pending contacts, exclusion of historical contacts without current selection, and stale/live-state invalidation.
- Add snapshot tests proving workbook edits after snapshot creation cannot change authorized members, evidence, note, interval, or digests.
- Add capacity tests proving zero capacity still permits discovery and workbook review, but blocks snapshot dispatch; lower-than-selection capacity requires explicit subset reduction rather than first-N truncation.
- Add dispatch tests proving twelve selected contacts can form a twelve-person batch when capacity permits and there is no fixed ten-person ceiling.
- Add interval tests for one minute, two minutes, larger whole-minute values, sub-minute rejection, exact freeze in the snapshot, and recovery preserving the remaining gate.
- Retain existing tests for account binding, official Chrome surface, no secret persistence, exact phrase parsing, note confirmation, ledger deduplication, preflight, success evidence, local failure, platform stop, and restart behavior.
- Add packaging parity tests for every new workbook and review-pool module, plus extracted-package installation checks without a knowledge base.
- Real acceptance remains two-stage: a boss-computer read-only run that fills or exhausts a review pool and updates the workbook, followed only after exact snapshot authorization by a bounded real invitation batch.

## Out of Scope

- Automatically inventing, translating, expanding, or rewriting search keyword phrases.
- Switching from Posts-first discovery to People-first discovery.
- Automatically changing sort order, publication range, or other confirmed LinkedIn filters to fill the pool.
- Treating likes, comments, or followers as candidates unless a later PRD explicitly adds engagement-based discovery.
- Adding more than one contact per company to the same human review pool.
- Connecting to company pages or substituting Follow, Message, InMail, guessed email, or other outreach for ordinary Connect.
- Claiming that Codex has verified purchasing intent, buyer status, customer status, or sourcing model.
- Numerical relevance scoring or KPI-based automatic qualification.
- Silent activation of screening rules from workbook decisions.
- Automatic recurring or scheduled LinkedIn search.
- Counting manual LinkedIn invitations in the local rolling ledger.
- Claiming the local one-hundred-in-one-hundred-sixty-eight-hours ceiling or one-minute interval is an official LinkedIn policy or guarantees account safety.
- Automatically sending every row marked Send without a current Final Dispatch Snapshot and explicit authorization.
- Migrating existing test-run state in place to the new schema.
- Using one cumulative workbook for multiple LinkedIn accounts.
- Publishing the PRD to an external issue tracker in this task.

## Further Notes

- The current implementation materially conflicts with this PRD: it stores `requested_limit` as a pre-search invitation/candidate limit, recommends ten and five minutes, stops at fifty opened posts per keyword, couples account capacity to browser discovery, and has no cumulative workbook abstraction.
- The redesign should be implemented as a new schema and tracer-bullet slices rather than scattered condition changes. The Review Pool Policy, Account Prospect Workbook, Preliminary Prospect Assessment, and Final Dispatch Snapshot are the primary deep-module seams.
- The workbook is a human review projection and durable business record; deterministic run JSON and the shared ledger remain authoritative for workflow phase, concurrency, capacity, and dispatch outcomes.
- A new ADR is warranted because this design deliberately replaces invitation-sized discovery with a two-stage review-pool/dispatch boundary and introduces an account-scoped cumulative workbook shared across runs.
- The boss's first completed review batches are expected to provide evidence for future screening-rule proposals. Until explicit rules are confirmed, broad-entry screening remains the canonical behavior.
