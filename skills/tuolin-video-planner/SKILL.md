---
name: tuolin-video-planner
description: Interview the user and create an evidence-grounded, production-ready 9:16 shot plan with timed verbatim narration for Tuolin products, then generate SRT after confirmation. Use only when the user explicitly names $tuolin-video-planner for YouTube Shorts or TikTok planning; it does not search public trends or generate, assemble, or publish video.
---

# Tuolin Video Planner

This skill is the independent planning-only entrypoint. It consumes its own `tuolin-video-planner` knowledge interface and ends after a confirmed shot plan, verbatim narration, and automatically derived SRT. It never calls or falls through to `$tuolin-video-workflow`.

## Invocation boundary

- Run only when the user explicitly names `$tuolin-video-planner`.
- If the user names `$tuolin-video-workflow`, leave that workflow unchanged.
- Do not infer, route, or ask which video Agent the user meant when neither is named.
- Never perform public trend search, Dreamina/Jimeng work, provider prompting, generation, download, assembly, editing, or publishing.

## Supported request

- Product: any product formally published in the dedicated planner interface.
- Platform: `youtube_shorts`, `tiktok`, or both.
- Language: one `zh` or `en` version per run.
- Duration: any integer from 15 through 90 seconds; recommend 30 seconds only when the user omitted duration.
- Format: fixed 9:16.
- Narration: required at document level, verbatim, and timed. Individual shots may be intentionally silent.
- Source-video audio: never use it.
- Do not design subtitle styling, title cards, platform safe areas, CTA overlays, or other post-production graphics.
- Include a spoken CTA only when the user explicitly asks for the corresponding viewer action.

## Knowledge boundary

Read only `generated/agent-interfaces/tuolin-video-planner/` through the dedicated Python API. Do not consume another Agent's contexts and do not scan raw knowledge files.

Use formal cards for product truth and application claims. Keep model reasoning available for creative judgments, but label those judgments as `planning_inference`; never present them as knowledge facts. If the interface is missing, invalid, or stale, stop and route the user to `$tuolin-kb` for knowledge organization. Do not refresh it manually: successful KB writes must refresh and verify registered interfaces automatically.

## Workflow

Read [workflow-contract.md](references/workflow-contract.md) before creating or continuing a run.

1. Create an isolated run under `generated/reports/video-planning/` and pin its interface revision.
2. Extract decisions already present in the request.
3. Ask only the single most consequential unresolved business question. Show exactly one recommendation, one reason, its fact/inference source, then ask `是否确认？`.
4. Recompute after every reply. Do not use a fixed creative-direction menu and do not repeat answered questions.
5. When the brief is sufficient, directly create the full shot plan and timed narration; there is no separate overall-plan confirmation stage.
6. Show the complete decision-sufficient shot plan in Codex, including actual previews and original references. Ask for one confirmation covering shots, materials, and narration.
7. On confirmation, automatically derive `storyboard.srt` and end the workflow. There is no separate SRT confirmation.

Ordinary `确认` applies only to the currently displayed question or shot plan. `按推荐` applies only to the current question. Accept all remaining recommendations only after an explicit reply such as `剩下都按推荐` or `你来决定并直接出策划`.

## Material-first behavior

Prefer already processed assets. For videos use this order:

1. Search the planner's lightweight video catalog by product, meaning, and capability.
2. Load details and representative media only for shortlisted profiles.
3. Generate a muted bounded preview only for a concrete planned use, inside an authorized key segment.

Never begin by opening many source videos. The private raw mapping is accessible only to the bounded preview adapter. One planned use may have at most three preview candidates.

Before selecting an image, internally open it and record subject, clarity, composition, 9:16 crop suitability, and near-duplicate status. A filename or metadata label is not visual inspection. An image with unresolved product-identity, rights, privacy, evidence, test-meaning, or external-claim risk may be shown as blocked but cannot enter a confirmable plan.

Assume the library has sufficient material; do not create a material-shortage, shorter-duration, or repetition-negotiation branch. Still reject any selected path that is missing, uninspected, unrelated, risky, or revoked.

## AI simulation

AI simulation is a planning label, not a generation task.

- Reference a formal `application_scenario` card.
- If a specific product is visible, also reference an inspected real product image.
- Mark the shot `simulated` in the conversation and files.
- Never use simulated imagery as a customer case, real test, performance proof, certification evidence, or field result.
- Do not write provider prompts.

## Shot-plan contract

Every shot contains exact start, end, and duration; audience-facing purpose; visible action; material reference and risk state; camera; transition; editing guidance; and verbatim narration or intentional silence. The timeline must be continuous and equal the target duration. Narration must fit normal Chinese or English speaking speed, and the entire plan cannot be silent.

Natural-language changes must update the actual plan fields. Revalidate timing, narration, materials, and protected fields after deletion, reorder, retiming, replacement, or wording changes. A change log entry without an artifact change is not completion.

After delivery, archive immutable numbered revisions. Any narration or timing change invalidates the current SRT and requires shot-plan reconfirmation. Immediately before confirmation, revalidate every referenced card and video profile; if a referenced object materially changed or was revoked, stop and require a new run. Unrelated interface changes do not block confirmation.

## Internal entrypoints

Users should work in natural language and should not run these commands themselves. Codex may use:

```text
python3 scripts/create_video_planning_run.py ...
python3 scripts/propose_video_planning_decision.py {run_dir} {proposal_json}
python3 scripts/handle_video_planning_reply.py {run_dir} "确认"
python3 scripts/authorize_video_planning_profile.py {run_id} {profile_id} ...
python3 scripts/extract_video_planning_preview.py {run_id} ...
python3 scripts/write_video_shot_plan.py {run_dir} {plan_json}
python3 scripts/confirm_video_shot_plan.py {run_dir}
python3 scripts/resume_video_planning_run.py {run_dir}
```

Fail loudly on missing interfaces, unsupported scope, unverified facts, stale revisions, missing paths, uninspected images, unauthorized video ranges, unresolved external-use risk, malformed timelines, narration overflow, SRT mismatch, or any provider artifact in a planner run.
