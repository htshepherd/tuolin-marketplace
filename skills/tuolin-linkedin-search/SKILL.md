---
name: tuolin-linkedin-search
description: Create and operate keyword-driven Tuolin LinkedIn prospect-search runs through LinkedIn Posts, including a six-question interview, balanced multi-keyword infinite scrolling, broad evidence-based AI screening, an account-scoped cumulative Excel review workbook, boss-selected immutable dispatch snapshots, and fixed-interval connection invitations through the official Codex Chrome extension. Use when the user asks to find LinkedIn customers, prospects, distributors, retailers, sourcing contacts, or connection-invitation candidates. Do not use for LinkedIn content planning or publishing.
---

# Tuolin LinkedIn Search

Run a human-controlled prospecting workflow from complete keyword phrases supplied by the operator. Do not require or read a product selection or Tuolin knowledge base.

## Non-negotiable boundaries

- Use only the official Codex Chrome extension and the already signed-in Chrome profile. Never substitute the in-app Browser.
- Never request, read, store, or print passwords, cookies, OTPs, session tokens, or browser-profile secrets.
- Preserve operator phrases intact and search them independently. Split only on comma, Chinese comma, semicolon, Chinese semicolon, or newline; remove case-insensitive exact duplicates while retaining first spelling and order. Never translate, correct, expand, or combine phrases.
- Search LinkedIn `Posts` only. Do not invent a geography filter for Posts.
- Treat Codex relevance as a preliminary assessment. The boss makes the final decision in the cumulative workbook.
- Search and review never imply permission to send. Before any invitation, reprint and require final authorization for the exact account, immutable selected people, source evidence, note/no-note choice, fixed interval, capacity, and snapshot digest.
- Enforce at most 100 locally recorded successful invitations per bound account in a rolling 168-hour period. This is a local operational ceiling, not a claim about LinkedIn policy; manual actions are outside the count.

## Start and resume

Create a run in the writable operational workspace:

```bash
python3 "<plugin-root>/scripts/create_linkedin_search_run.py" "<user request>" --project-dir <workspace>
```

Resume only from the exact run directory and read `workflow_state.json` first. New runs use schema version 3. Do not migrate or reinterpret older runs; tell the operator to start a new task when an incompatible transition is requested.

Apply deterministic transitions with:

```bash
python3 "<plugin-root>/scripts/update_linkedin_search_run.py" <action> --run-dir <run-dir> --data-json '<json object>'
```

## Six-question interview

Ask only missing fields, one at a time, with stable numbering:

1. Ordered complete keyword phrases.
2. Posts sort order.
3. Publication date range.
4. Add a note or no note.
5. Fixed whole-minute interval between invitations.
6. `本次最多找多少个联系人给您筛选？`

For question 1, give format guidance only and wait for operator phrases. For questions 2–6, give exactly one recommendation and one reason, then ask `是否确认？`. `确认` accepts only the current recommendation.

- Recommend Latest and Past month.
- Keep the existing note/no-note interview and require note review before final snapshot.
- Recommend 2 minutes; accept whole-minute intervals of at least 1 minute. Freeze the confirmed value for the batch.
- Recommend 50 review contacts; accept an integer from 1 through 100. This is a human-review pool, not an invitation count.
- Never ask for invitation count before discovery. The boss's later exact selection determines the proposed dispatch count.

## Account binding and discovery

After the brief is complete, obtain read-only Chrome authorization, bind the visible LinkedIn name and normalized profile URL, and create the account-scoped workbook identity. Record rolling capacity for information only. Capacity—including zero—must not reduce or block discovery, assessment, workbook updates, or boss review.

Apply the confirmed Posts filters and use Balanced Keyword Sampling:

1. Allocate deterministic soft first-pass shares from review-pool size and keyword count; assign remainders in original order.
2. Give every phrase a first-pass search opportunity. A soft share is a scheduling boundary, not a relevance quota.
3. Count a pool position only after a new, deduplicated, ordinary-Connect member has a persisted candidate card and successful workbook-sync receipt.
4. Repeated members or companies append evidence but do not consume a new-contact position.
5. After all first passes, revisit non-exhausted productive phrases in original order until the pool is full or all phrases are verified exhausted.
6. Do not use a raw opened-post ceiling. Continue infinite scrolling until the current soft boundary is reached or three consecutive cycles each reach the current bottom, wait for loading, and add no new unique post URL/URN.
7. Reset the no-growth counter whenever a new unique post appears. Ignore ads, placeholders, duplicate posts, footer visibility, displayed counts, and discarded `page=2` parameters as exhaustion evidence.
8. Never expand keywords or relax confirmed filters when the pool remains short.

## Preliminary prospect assessment

Base every decision only on the exact phrase, complete visible post, author, company, role, profile, ordinary Connect evidence, explicitly permitted historical feedback, and confirmed screening rules.

Hard-exclude only:

- obvious semantic mismatches;
- direct manufacturers or suppliers of the same category or base material;
- duplicate, already-sent, invitation-Pending, connected, or boss-Excluded members;
- people without a verifiable ordinary Connect path.

Retain plausible installers, contractors, integrators, fabricators, equipment makers, project operators, brands, distributors, retailers, private-label sellers, and other ambiguous commercial roles for boss review. Public RFQ evidence is not required.

For every retained contact, state visible supporting evidence, likely business role, material uncertainty, a keep/remove recommendation, and any cited feedback IDs. Do not output an unexplained numerical score or call anyone a confirmed buyer or customer.

Keep one contact per company. Prefer Owner/Founder, Procurement/Purchasing/Sourcing, Managing Director/General Manager, then Product Manager. Allow another visibly relevant responsible manager only with an explicit role-to-business reason. If a preferred person cannot use ordinary Connect, try the next person. If none can be verified, record an Unresolved Relevant Lead outside the pool.

## Account cumulative workbook

Use one `.xlsx` per normalized bound LinkedIn account and another workbook for a different account. Keep exactly three stable sheets:

- `潜客联系人`: one current row per member, identity/company/relationship timestamps, required `发送/排除/待定` dropdown, and optional boss note. New rows default to `待定`.
- `潜客证据`: every retained occurrence, run, source phrase, complete post, URL, Codex assessment, evidence, uncertainty, and recommendation.
- `发送记录`: immutable authorization membership, note, interval, attempt time, and outcome.

Use atomic replacement, retain a recoverable previous version, and fail loudly on a malformed or unwritable workbook. Persist a run-local sync receipt containing pre/post revision, affected contact/evidence IDs, and content digest. Runtime JSON and the shared ledger remain authoritative for workflow and concurrency; Excel is the boss-facing review projection.

Repeated people update latest-seen metadata and append evidence. Sent, invitation-Pending, connected, or `排除` people do not re-enter. An Exclude contact returns only when the boss changes it back to `待定`. A historical `待定` contact may join a current batch only after the boss explicitly changes/selects it for this task.

## Boss selection and final snapshot

After discovery, summarize new versus repeated contacts, keyword contributions, hard exclusions, unresolved leads, workbook path, revision, and the next instruction. Let the boss review the workbook and choose `发送`, `排除`, or `待定`; do not dump fifty full cards into chat.

Read only the boss's current `发送` selection, capture the dropdown and note as review feedback, and revalidate each selected member against account, company/member identity, live state, ordinary Connect, and ledger. The selected count is the Approved Dispatch Count; there is no fixed ten-person run ceiling.

Recompute rolling capacity before the Final Dispatch Snapshot:

- If capacity is sufficient, freeze the exact selected people, complete evidence, note, interval, account, approved count, capacity evidence, and digest.
- If capacity is zero, retain search and workbook results but block Connect.
- If capacity is smaller than the selection, never take the first N. Require the boss to choose and reconfirm the exact reduced subset.
- Reprint every frozen person, complete source post, assessment evidence, doubts, account, note, interval, capacity, and digest in Codex before final authorization.

Workbook edits after snapshot creation cannot change the authorized set. After explicit snapshot authorization, send sequentially without per-person reconfirmation.

## Dispatch, feedback, and recovery

- Before every click, revalidate visible account, candidate identity, ordinary Connect path, live relationship state, ledger reservation, remaining capacity, fixed note, and interval gate.
- Record success only when LinkedIn visibly confirms the invitation or changes the relationship to Pending.
- Append authorization and every observed outcome to the workbook and shared ledger. A successful LinkedIn action followed by a workbook/ledger write failure requires reconciliation and immediate stop.
- Candidate-local failures may continue according to the deterministic contract. Restriction warnings, CAPTCHA, security checkpoints, logout, account mismatch, or ambiguous state stop the batch.
- Ordinary interruption requires reconciliation and fresh authorization for the remaining immutable snapshot. Platform stops require a new restart run; never silently resume.
- Persist every boss decision as feedback. Treat an explicit boss note as stronger evidence than a blank-note decision. Later assessments may cite relevant feedback IDs, but no pattern becomes a hard rule automatically.
- A proposed screening rule must show supporting and conflicting examples. Activate it only after explicit boss confirmation, and version its wording, scope, evidence, and confirmation time.

## Installation acceptance

Version `2.0.1` must pass local runtime, `.xlsx` round-trip, source/plugin mirror, Skill, plugin, and extracted-package checks without a Tuolin knowledge base. Real acceptance remains two stages on the boss's computer: first a read-only run that fills or verifies exhaustion of the requested review pool and updates the workbook; then, only after exact snapshot authorization, a bounded real invitation batch.
