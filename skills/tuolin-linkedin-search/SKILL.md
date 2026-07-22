---
name: tuolin-linkedin-search
description: Create and operate product-grounded Tuolin LinkedIn prospect-search runs from LinkedIn Posts, including a one-question-at-a-time search interview, candidate review, cross-run deduplication, explicit batch authorization, and controlled connection invitations through the official Codex Chrome extension. Use when the user asks in Chinese or English to search LinkedIn posts for customers, prospects, distributors, retailers, sourcing contacts, or connection-invitation candidates for a Tuolin product. Do not use for LinkedIn content calendars, post copy, images, or publishing; use tuolin-linkedin for those tasks.
---

# Tuolin LinkedIn Search

Operate a human-confirmed prospecting workflow grounded in one formal Tuolin product. Keep content planning in `$tuolin-linkedin` and formal knowledge maintenance in `$tuolin-kb`.

## Hard boundaries

- Run from the user's Tuolin knowledge project directory.
- Read product facts only through `generated/agent-interface/` and a verified `linkedin_search` context.
- Bind exactly one formal product to each run. If it cannot be resolved, stop and direct the user to `$tuolin-kb`; never guess.
- Treat user-supplied market terms as search-only vocabulary. Never promote them to formal names, specifications, or claims.
- Keep prospect and operational artifacts outside `knowledge/okf/`.
- Use only the official Codex Chrome extension and the user's existing signed-in Chrome profile for LinkedIn.
- Before browser work, verify that the official `chrome@openai-bundled` plugin is installed and enabled. Do not fall back to the in-app browser for LinkedIn.
- Never request or store passwords, OTPs, cookies, local storage, or session data.
- Never use headless Chrome, fingerprint spoofing, IP tunneling, stealth claims, or detection-avoidance guarantees.
- Do not schedule unattended recurring runs.
- Do not send any invitation without an exact closed candidate batch and final user authorization.

## Start or resume through the router

Resolve `<plugin-root>` from this installed `SKILL.md`: it is the directory two levels above the skill directory and contains `.codex-plugin/`, `skills/`, and `scripts/`. Run plugin-owned scripts from that root while passing the user's real knowledge project through `--project-dir`. Do not assume the knowledge project contains a copy of the plugin scripts.

For a new request, run the natural-language router before browser work:

```bash
python3 "<plugin-root>/scripts/route_natural_language.py" "<user request>" --project-dir <knowledge-project-dir>
```

For deterministic testing or explicit product IDs, use:

```bash
python3 "<plugin-root>/scripts/create_linkedin_search_run.py" "<user request>" --product-id <canonical-product-id> --project-dir <knowledge-project-dir>
```

Read the returned run directory and `workflow_state.json` before continuing an existing task. Never infer the phase from conversation memory.

After Codex collects an approved Chrome observation or user decision, persist it through the deterministic transition helper:

```bash
python3 "<plugin-root>/scripts/update_linkedin_search_run.py" <action> --run-dir <run-dir> --data-json '<action-payload>'
```

Supported actions are `answer-interview`, `bind-account`, `confirm-effective-limit`, `record-first-search`, `record-next-search`, `finish-keyword`, `record-individual`, `record-company`, `prepare-review`, `remove-candidates`, `confirm-batch`, `prepare-authorization`, `authorize-batch`, `prepare-dispatch`, `record-dispatch-result`, `resolve-note-unavailable`, `prepare-recovery`, `authorize-recovery`, `prepare-platform-restart`, `create-platform-restart`, and `record-evidence`. Build payloads only from the current user decision and visible Chrome state. Never hand-edit `workflow_state.json`, candidate cards, the shared ledger, pending attempt, or authorization files.

## Interview transition contract

- While `workflow_state.json` is in `awaiting_search_interview`, submit every user reply exactly once through `answer-interview`, passing the user's reply unchanged as `data.reply`.
- Display the transition helper's returned `message` as the next interview prompt. Do not invent a second confirmation prompt, renumber it, or claim an answer was saved without this persisted transition.
- `确认` accepts the recommendation shown for the current question only.
- Any other valid reply is the user's final custom answer for the current question. Persist it as `user_supplied` and immediately advance to the next unresolved question; do not ask the same numbered question again.
- The deterministic prompt owns visible numbering (`第一问`, `第二问`, and so on). Never generate labels such as `第 1 题（自定义答案）` in the chat layer.

## Workflow

1. Resolve one formal product and create an isolated run.
2. Ask only missing business questions that affect supported Posts search controls, candidate boundaries, or external actions.
3. Ask one numbered Chinese question at a time. Give exactly one recommendation with a reason and end with `是否确认？`.
4. Treat `确认` as approval for only the current question. Do not support bulk confirmation of remaining questions.
5. Bind and display the visible LinkedIn member name and profile URL before discovery.
6. Search Posts using only confirmed ordered keywords and supported filters.
7. Classify each opened post `Continue` or `Skip` with one visible-content reason.
8. Resolve at most one standard-Connect candidate per company and reconcile local plus live LinkedIn state.
9. Print and persist candidate cards before authorization.
10. Let the user remove candidates, then freeze the remaining list as a closed batch without backfill.
11. If notes are enabled, freeze one user-confirmed short English note for the entire batch.
12. Show the bound account, exact candidates, count, note/no-note, fixed interval, and effective limit; require final confirmation.
13. Before each external action, read the profile and call `prepare-dispatch`. Do not click Connect until it returns `dispatch_preflight_passed` and an exact one-time attempt ID.
14. Execute exactly one Connect action for that attempt, then immediately call `record-dispatch-result` with the same account, candidate, attempt ID, and visible outcome. Record Invitation Dispatch Success only after LinkedIn visibly confirms submission.
15. Stop immediately for restrictions, CAPTCHA, security checkpoints, logout, ambiguous dispatch, or failed success-ledger persistence.
16. After an ordinary interruption, revalidate the account and last action, show the exact remaining closed batch with note, interval, and capacity, and obtain fresh authorization.
17. After a platform-level stop, create a handoff and then an isolated restart run. Rebind the same account, review the preserved candidates, and obtain a new authorization; never resume the stopped run or search for replacements.

## Stable operating rules

- Search Posts before People; People-first search is out of scope.
- Do not ask for geography when the Posts UI cannot apply it.
- Recommend `Latest` and `Past month` when sort/date are missing.
- Inspect at most 50 opened posts per keyword. Do not ask the user to configure this internal limit.
- Never add keywords, relax filters, repeat exhausted searches, or backfill candidates automatically.
- Prefer company contacts in this order: Owner/Founder; Procurement/Purchasing/Sourcing; Managing Director/General Manager; Product Manager.
- Require a standard Connect path. Do not substitute Follow, Message, InMail, email, or guessed identity.
- Default the requested run ceiling to 10. Treat it as a maximum, not a quota.
- Enforce at most 100 successes recorded by this skill per bound account in a rolling 168-hour window. State that manual actions are not counted and this is not an official LinkedIn limit.
- Recommend a fixed five-minute interval. Do not add random “human-like” jitter.
- Keep only one active run per bound account.
- Candidate-local failures may continue when non-dispatch is certain. Platform-level failures stop the entire batch.
- A platform-level stop requires a new task and new authorization. Ordinary interruption recovery requires state reload, account revalidation, last-action reconciliation, remaining-batch display, and fresh authorization.
- Do not combine preflight observation, browser click, and result into one transition. `dispatch-next` is retired because it cannot prove checks happened before the external action.
- Do not save screenshots by default. `record-evidence` is allowed only after explicit user authorization, for a disputed interaction state, or for a platform-level stop; bind the file to a reason and candidate when applicable.

## Installation and remote acceptance

On a newly installed business computer, internally run the installation preflight from the plugin package before opening LinkedIn:

```bash
python3 "<plugin-root>/scripts/check_linkedin_search_install.py" --project-dir <knowledge-project-dir>
```

If the verified Agent interface is missing or stale, stop and ask `$tuolin-kb` to refresh and verify it. The operator must not copy knowledge data to another computer merely for development tests.

Use this acceptance order:

1. Confirm plugin version `1.52.2`, the verified Agent interface, and the official Chrome plugin.
2. Start a new Codex conversation from the real knowledge project.
3. Run interview, account binding, Posts search, discovery, and candidate-card review without sending.
4. Verify cross-task deduplication with the preserved shared ledger.
5. Only after the operator confirms the exact final brief, test one real invitation through the two-phase dispatch contract.

## Current implementation gate

Obey `workflow_state.json`. If the runtime reports a phase or action as unavailable, report it as not implemented or blocked; do not imitate completion manually or bypass the persisted state machine.
