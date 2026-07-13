---
name: tuolin-video-workflow
description: Create evidence-grounded Tuolin industrial product videos through a dynamic creative-discovery interview, YouTube Shorts trend research, inspected official images, a confirmed plan, visual storyboard plus SRT, Dreamina task handoff, one-shot result download, and shot assembly. Use when the user asks in Chinese to create or continue a Tuolin product video for YouTube Shorts.
---

# Tuolin Video Workflow

This is the sole user-facing video-creation entrypoint. Its most important job is to discover why the intended audience would watch and care before designing shots. It consumes formal product knowledge and official images from the knowledge-base Agent interface; it never becomes a knowledge producer.

## Current scope

- Platform: YouTube Shorts only. Do not accept TikTok or standard horizontal YouTube in this release.
- Initial product scope: products supported by the runtime's formal `video_creation` context, currently quartz-fiber tape.
- Supported durations: 15, 20, 30, 45, 60, 90, or 120 seconds.
- One language version and one isolated run directory per video task.
- Dreamina default: `seedance2.0_vip`, 1080P, 9:16.
- Deliverables include the plan, visual storyboard, confirmed `.srt`, internal Dreamina prompts, task plan, downloaded shots, and stitched video.
- TTS, BGM, subtitle burn-in, publishing copy, first-party channel analytics, and generated-result improvement are out of scope.

## Non-negotiable evidence boundary

Before the first creative question, load the current product's formal knowledge card and related official `content_asset` images through the knowledge-base Agent interface.

- Never scan unorganized raw files or infer facts from pixels.
- Never invent product names, parameters, certifications, applications, customer cases, or performance claims.
- Pixels decide visual usability; formal cards decide product truth.
- If formal knowledge or the refreshed Agent interface is missing or stale, stop and route the user to `$tuolin-kb`.
- Never write video-task decisions into `knowledge/okf/`.

## Creative discovery is a reasoning process

Read [creative-discovery-protocol.md](references/creative-discovery-protocol.md) before conducting or continuing the interview.

Do not execute a fixed questionnaire, fixed creative-direction taxonomy, or form-like list. Instead:

1. Extract decisions already explicit in the user's request.
2. Build the dependency chain for this video.
3. Investigate missing evidence yourself where possible.
4. Surface the single load-bearing unresolved decision.
5. Propose exactly one contextual recommendation with a concrete reason.
6. Ask `是否确认？`; accept ordinary `确认` for this decision only, or record the user's correction.
7. Recompute the next decision from all confirmed answers and evidence.
8. Stop only when one coherent, evidence-supported, executable direction exists.

Never accept `按推荐`, `剩下都按推荐`, or an earlier confirmation as approval of later decisions. Never ask the user to choose shot count, timing, camera movement, image assignment, Dreamina mode, prompt wording, or other professional execution details.

Challenge weak choices. If spectacle, an abstract style preference, or a requested angle would not give the audience a credible reason to watch, say what concrete audience or business conflict it creates and recommend one better direction. The user keeps final authority.

## Required pre-plan evidence

After audience and audience-problem scenario are actionable, but before confirming viewer-interest direction:

1. Perform a lightweight public YouTube scan in the audience's relevant language/region.
2. Follow the relevance ladder: comparable industrial products, adjacent engineering/manufacturing content, then a broader category only when its mechanism safely transfers.
3. Record source URL, scan date, target language/region, observed signal, why it worked, mechanism, transfer to this product, relevance level, and excluded methods. If live evidence is unavailable, say so and mark any fallback as a general principle, not a current trend.
4. Show a compact trend evidence brief: signals found, shared reason they work, transferable mechanism, rejected popular methods, one recommended viewer-interest direction, links, and date.
5. Open every candidate official image and inspect subject, clarity, composition, 9:16 crop, near-duplicates, and support for the proposed mechanism.

Do not confirm a direction the available evidence-backed visuals cannot execute. Recommend a revised direction, shorter duration, or an explicitly labeled AI-simulated environment. Repetition requires explicit approval.

## From discovery to plan

The confirmed brief must resolve all factors that can materially change audience value, business outcome, evidence use, creative direction, or safe execution. It normally covers audience, problem scenario, viewing motivation, trend mechanism and evidence, material feasibility, viewer-interest direction, intended takeaway, desired action, priority facts, human relevance where useful, exclusions, and AI-simulation scope.

When sufficient, generate the plan automatically. In Codex, print the core plan and 3–6 inspected representative images. Include the audience problem, interest direction, why it should hold attention, trend evidence and sources, narrative, facts, visual treatment, CTA, risks, duration, and AI boundaries. Ask only `是否确认？`; do not make the user open Markdown or JSON.

Natural-language revisions must change the real plan fields before redisplay. Merely logging a request is not completion.

## Storyboard and SRT contract

After plan confirmation, dynamically create:

- `storyboard.md`
- `storyboard.json`
- `storyboard.srt`

Do not create `prompts.md/json` yet. The visual storyboard is the sole shot-level creative contract, and its SRT is the sole future verbatim narration transcript.

Print every shot in Codex with exact timing, audience-facing purpose, visible action, continuity intent, SRT cue or intentional silence, risks, every ordered reference image's role and original path, and the images themselves. One shot may use multiple ordered images when continuity is credible.

Before confirmation, support natural-language deletion, reorder, image replacement, visual-intent revision, subtitle revision, and intentional silence. Every revision must recalculate the timeline, regenerate the SRT, clear stale prompts/tasks, and redisplay the affected contract.

Validate that every non-silent shot or consecutive shot group has an SRT cue expressing the same idea as the visual. Never derive SRT text from a camera description or Dreamina prompt as fallback.

After the user confirms storyboard and SRT together, generate `prompts.md/json` internally. Prompt wording is an auditable provider translation, not a second creative source of truth and not another user confirmation gate. If provider capability cannot execute a multi-image shot, propose adjacent consecutive shots and reconfirm storyboard plus SRT; never drop references or split silently.

Read [industrial-seedance-prompt-rules.md](references/industrial-seedance-prompt-rules.md) during storyboard-to-prompt conversion.

## Dreamina and assembly

Read [dreamina-task-planning-rules.md](references/dreamina-task-planning-rules.md) before task planning.

1. Print every task's shot mapping, type, ordered references, duration, estimated credits, capability adaptations, and blockers in Codex.
2. Paid authorization requires exact `确认即梦生成`; ordinary `确认` is insufficient.
3. Actual submission remains a separate explicit `提交即梦任务` action.
4. When execution must occur on Windows, print the exact PowerShell handoff command.
5. The operator monitors the Dreamina web interface. Do not expose a user-facing status query.
6. After the user says `即梦已全部生成`, perform exactly one result download using real task IDs and validate expected count, mapping, existence, readability, and non-empty files.
7. On download failure, stop loudly; do not poll, retry, or silently resubmit.
8. On success, assemble shots in confirmed storyboard order and retain `storyboard.srt` beside the run artifacts. Do not generate a conflicting voiceover or subtitle Markdown file.

If generated clips are rejected, record the outcome and stop the run. The current release starts a new video task instead of rewinding or improving the confirmed run.

## Confirmation display rule

Every decision that needs confirmation must print its decision-sufficient core content in the Codex conversation. Files exist for audit and resume; they are never the primary confirmation surface.

Ordinary `确认` applies only to the currently displayed non-paid phase. It never authorizes paid generation, actual submission, later phases, or external publication.

## Internal entrypoints

Ordinary users should not run scripts. Codex may use these internally:

```text
python3 scripts/create_video_creation_run.py "..." --language en --platform youtube_shorts --duration 60 --project-dir /path/to/project
python3 scripts/propose_video_interview_decision.py {run_dir} {proposal_json}
python3 scripts/handle_video_creation_reply.py {run_dir} "确认"
python3 scripts/record_video_interview_evidence.py {run_dir} {evidence_json}
python3 scripts/record_video_material_inspection.py {run_dir} {assessment_json}
python3 scripts/apply_video_plan_revision.py {run_dir} {plan_change_json}
python3 scripts/apply_storyboard_revision.py {run_dir} {storyboard_change_json}
python3 scripts/set_storyboard_shot_references.py {run_dir} {ordered_references_json}
python3 scripts/handle_video_creation_reply.py {run_dir} "确认即梦生成"
python3 scripts/handle_video_creation_reply.py {run_dir} "提交即梦任务"
python3 scripts/handle_video_creation_reply.py {run_dir} "即梦已全部生成"
python3 scripts/handle_video_creation_reply.py {run_dir} "合并视频"
python3 scripts/resume_video_creation_run.py {run_dir}
```

## Fail loudly

Stop and state the exact blocker for stale or missing knowledge interfaces, unsupported platforms, missing image paths, incomplete pixel inspection, malformed evidence, unconfirmed claims, accidental duplicates, SRT mismatch, unsupported multi-image execution, blocked task validation, dry-run mistaken for real output, missing real task IDs, one-shot download failure, or plugin/source mismatch.
