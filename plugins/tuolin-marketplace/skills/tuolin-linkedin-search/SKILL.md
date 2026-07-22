---
name: tuolin-linkedin-search
description: Create and operate keyword-driven Tuolin LinkedIn prospect-search runs through LinkedIn Posts, including a six-question interview, verified infinite scrolling, full-post candidate review, account-scoped deduplication, explicit batch authorization, and fixed-interval connection invitations through the official Codex Chrome extension. Use when the user asks to find LinkedIn customers, prospects, distributors, retailers, sourcing contacts, or connection-invitation candidates. Do not use for LinkedIn content planning or publishing.
---

# Tuolin LinkedIn Search

Run a human-controlled prospecting workflow from complete keyword phrases supplied by the operator. A product selection and Tuolin knowledge base are not required and must not be read for this workflow.

## Non-negotiable boundaries

- Use only the official Codex Chrome extension and the already signed-in Chrome profile. Never substitute the in-app Browser.
- Never request, read, store, or print passwords, cookies, OTPs, session tokens, or browser-profile secrets.
- The operator supplies every search phrase. Preserve each phrase intact and search phrases independently in input order.
- Split phrases only on comma, Chinese comma, semicolon, Chinese semicolon, or newline. Remove case-insensitive exact duplicates while preserving the first spelling and order. Do not split words, translate, correct, expand, combine with Boolean operators, or impose a phrase-count cap.
- Search LinkedIn `Posts` only. Do not invent a geography filter for Posts.
- AI relevance is provisional. Show the complete visible post and identity evidence in the candidate card; the user makes the final inclusion decision.
- Before any external invitation, require a final authorization for the exact account, closed candidate list, fixed note/no-note choice, and fixed interval. After that authorization, send sequentially without per-person reconfirmation.
- Default ceiling is 10 invitations per run. The local ledger also enforces at most 100 recorded successful invitations in a rolling 168-hour period. These are ceilings, never targets that justify relaxing criteria.

## Start and resume

Create a run in the writable operational workspace:

```bash
python3 "<plugin-root>/scripts/create_linkedin_search_run.py" "<user request>" --project-dir <workspace>
```

Resume only from the exact run directory and read `workflow_state.json` first. Never assume the remembered phase is current.

Apply deterministic transitions with:

```bash
python3 "<plugin-root>/scripts/update_linkedin_search_run.py" <action> --run-dir <run-dir> --data-json '<json object>'
```

## Six-question interview

Ask only missing executable fields, one at a time, with stable numbering:

1. Ordered keyword phrases.
2. Posts sort order.
3. Publication date range.
4. Add a note or no note.
5. Fixed interval between invitations.
6. Maximum invitations.

For question 1, provide format guidance only—there is no recommended keyword. A valid custom keyword answer is persisted once and advances immediately. `确认` is invalid when keywords are missing.

For questions 2–6, provide exactly one recommendation with one reason and ask `是否确认？`. `确认` accepts only the current recommendation. Do not accept bulk confirmation of remaining questions. Do not repeat fields already explicit in the original request.

## Browser and search workflow

1. After the brief is complete, obtain the task's read-only Chrome authorization and bind the visible LinkedIn account.
2. Open a dedicated task tab group and apply `Posts`, the exact current phrase, confirmed sort, and confirmed date range.
3. Open and evaluate unique posts. Count a post only once by normalized LinkedIn URL/URN. Ads and duplicates do not count.
4. Keep scrolling and loading until one stop condition is proven:
   - reviewable candidate pool reaches the effective limit;
   - 50 unique posts have actually been opened and evaluated for the current phrase; or
   - three consecutive cycles each reach the current bottom, wait for loading, and yield no new unique post URL/URN.
5. Footer visibility, an ad, one stalled load, a displayed result count, or a discarded `page=2` URL is not exhaustion.
6. If the phrase ends below the candidate limit, move to the next supplied phrase. Stop when the candidate limit is reached or all phrases finish. Never expand keywords or relax filters.

## Provisional relevance classification

Use only the exact source phrase and visible LinkedIn post, author, company, profile, and Connect evidence.

- Direct manufacturers or suppliers of the same category or base material are competitors and must be `Skip`.
- Brands, distributors, retailers, and private-label sellers may be same-category channel prospects.
- Installers, contractors, integrators, fabricators, equipment makers, and project operators may be downstream material users even without a public RFQ.
- Clearly unrelated content is `Skip`.
- If the business model remains ambiguous, preserve it as a provisional candidate for human judgment and state the doubt explicitly.
- A relevant company with no verifiable preferred-role member and standard Connect path becomes an unresolved relevant lead. It does not count toward the candidate ceiling and cannot be dispatched.

Every reviewable candidate card must include the source phrase, complete visible post text, post URL, author, company, chosen member, profile URL, standard Connect evidence, AI supporting evidence, material doubts, and a statement that the judgment is provisional.

## Human review and note

Prepare one batch review containing the complete cards. The user may remove any candidate. Never backfill after removal; a smaller final batch is valid and a new run is required for more discovery.

If notes are enabled, draft one short English note grounded only in the common keyword topic or generic industry context. Do not add product claims, specifications, certifications, prices, or knowledge-base facts. The user must confirm or edit it before it enters the authorization brief. Freeze the exact note for the batch; do not rewrite it during dispatch.

## Dispatch and recovery

- Revalidate the visible account, candidate identity, profile/company/post reservations, live connection state, standard Connect path, rolling capacity, and fixed note before every click.
- Record success only when LinkedIn visibly confirms the invitation was sent or the profile state changes to Pending.
- Enforce the authorized fixed interval after each success.
- Candidate-local failures may be recorded and skipped according to the runtime contract. Platform-wide warnings, restrictions, CAPTCHA, account mismatch, or ambiguous state stop the batch.
- Ordinary interruption requires reconciliation and fresh authorization for the remaining closed batch. A platform stop requires an explicit new restart run; never silently resume.
- Save screenshots only for disputed state or platform-stop evidence and only under the evidence policy.

## Installation acceptance

Version `1.53.0` must pass local install/runtime checks without a Tuolin knowledge base. Real acceptance still requires the boss's computer, the official Codex Chrome extension, an already signed-in LinkedIn profile, a read-only Posts-search run, and—only after the exact final batch authorization—one real invitation test.
