---
name: tuolin-video-workflow
description: Create Tuolin quartz-fiber-tape video plans, storyboards, Dreamina prompts, and Dreamina CLI video-generation handoff files from the local knowledge-base Agent interface. Use when the user asks in Chinese to make 石英纤维隔热带 product videos for YouTube Shorts or TikTok.
---

# tuolin-video-workflow

This skill is part of `tuolin-marketplace`. It is a video-creation application-layer Agent: it consumes formal knowledge and content assets through the Agent读取接口, but it does not maintain the knowledge base.

## Scope

- Initial scope only: 石英纤维隔热带 product videos.
- Supported platforms: YouTube Shorts, TikTok, or both.
- Supported output: one language-specific 9:16 Dreamina-generated video-shot set per run.
- Supported durations: 60, 90, or 120 seconds.
- Default output resolution: 1080×1920.
- Default Dreamina model for generated shots: `seedance2.0_vip`.

Out of scope:

- Workshop videos.
- Other Tuolin product lines.
- Platform titles, descriptions, post copy, hashtags, scheduling, or publishing.
- Any workflow that asks ordinary users to invoke internal scripts, ffmpeg, or JSON files directly.

## Hard boundaries

- Use this only through the Codex client.
- Run from a local knowledge project directory, not from the plugin repository directory.
- Use `video_creation` downstream context only.
- Do not use old `video_script` as the task context.
- Do not scan raw.
- Do not write to `knowledge/okf/`.
- Do not hard-code Chinese or English external product names; read them from formal knowledge/config.
- Do not use “master” or “母版” as a user-facing output concept or filename.
- Do not submit paid Dreamina jobs until the user says `确认即梦生成`.

## Workflow

1. Identify a 石英纤维隔热带 video request.
2. Confirm video language version:
   - 中文版: Chinese planning and visual-prompt language.
   - 英文版: English planning and visual-prompt language.
3. Confirm platform, duration, audience, and core objective.
4. Create a run directory under:
   - `generated/reports/video-creation/{timestamp}_quartz_fiber_tape_{zh|en}/`
5. Show all 16 fixed video creative directions plus exactly 3 ranked dynamic recommendations in `requirements.md`.
6. Stop and confirm one primary creative direction and at most one supporting direction. Do not generate `video_plan.md` before this confirmation.
7. When the user confirms the creative direction through natural language, automatically generate `video_plan.md` / `video_plan.json`, then wait for `确认策划`.
8. When the user says `确认策划`, automatically generate the Visual Storyboard: `storyboard.md`, `storyboard.json`, `prompts.md`, and `prompts.json`; then wait for `确认分镜`.
9. `storyboard.md` must show inline reference-image previews copied into `storyboard_assets/`, the original image path, and duplicate-image warnings. Users may delete shots or replace a shot image by natural language before confirming.
10. When the user says `确认分镜`, automatically plan Dreamina jobs and show job type, material, duration, estimated credit use, and risks.
11. Wait for `确认即梦生成`.
12. Submit/query Dreamina jobs internally or generate the manual PowerShell handoff for real Dreamina CLI submission.
13. Allow shot-level retry such as `重做镜头 03`; show estimated credit use before retry.
14. Wait for `确认镜头`.
15. After shots are confirmed, merge the downloaded shot videos into `dreamina_generation/stitched_video.mp4` and generate `dreamina_generation/editing_subtitles.md` for manual subtitle/voiceover editing.
16. End the video-creation Agent run only after local shot stitching succeeds. If shot video files are missing or ffmpeg fails, keep the run blocked at `合并视频` and show the missing inputs.

## Fixed video creative directions

Always show the complete list when asking the user to choose the direction:

1. 产品总览型
2. 单一核心卖点型
3. 多卖点概览型
4. 产品细节型
5. 应用演示型
6. 客户痛点解决型
7. 安装演示型
8. 使用注意事项型
9. 技术科普型
10. 性能测试型
11. FAQ 问答型
12. 材料对比与选型型
13. 规格与定制型
14. 采购指南型
15. 真实案例型
16. 询盘转化型

## Reference loading

Load the relevant reference before generating or validating that stage:

- For creative-direction recommendation, video planning, or quality review, read `references/creative-quality-matrix.md`.
- For storyboard-to-Dreamina Prompt conversion, read `references/industrial-seedance-prompt-rules.md`.
- For Dreamina job planning, confirmation, querying, or shot retry, read `references/dreamina-task-planning-rules.md`.

External Seedance/Dreamina skills are absorbed as methodology only. Do not copy entertainment, short-drama, or cinematic categories into Tuolin's fixed 16-direction industrial product taxonomy.

## Material readiness reporting

Before asking the user to confirm a video plan or Dreamina generation, always show a plain-language material readiness summary:

- How many official content assets were read for the quartz-fiber tape product.
- How many are product images, application-scene image assets, and test/validation image assets.
- How many can be used as real image references for `image2video`.
- Whether product-visible shots are likely to be blocked because there is no real product reference.
- Whether the storyboard and Dreamina plan use distinct image references across shots. Do not allow multiple paid Dreamina shots to reuse the same image reference unless the user explicitly asks for a deliberate repeated visual. If repeated references appear by accident, block confirmation and explain that more varied source images or a revised storyboard is needed.

Do not ask the user to “sync content_asset cards” as the primary next step. Say what they need to do in operational terms, such as “请先整理石英纤维隔热带产品图片，让视频 Agent 能读取真实产品图片素材。”

## Current executable entrypoint

Use this script for the current implemented run-initialization slice:

```text
python3 scripts/create_video_creation_run.py "做一个60秒石英纤维隔热带产品介绍视频，面向欧美工业采购商，用在 YouTube Shorts 和 TikTok。" \
  --language en \
  --platform youtube_shorts \
  --platform tiktok \
  --duration 60 \
  --audience 欧美工业采购商 \
  --objective 突出耐高温、隔热、不刺痒和不冒烟 \
  --project-dir /path/to/knowledge-project
```

This creates:

- `requirements.md`
- `workflow_state.json`
- `change_log.md`

Then confirm the creative direction before planning:

```text
python3 scripts/confirm_creative_direction.py {run_dir} \
  --primary-direction procurement_guide \
  --supporting-direction product_detail
```

Implemented planning commands:

```text
python3 scripts/confirm_creative_direction.py {run_dir} --primary-direction procurement_guide --supporting-direction product_detail
python3 scripts/generate_video_plan.py {run_dir}
python3 scripts/confirm_video_plan.py {run_dir}
python3 scripts/generate_storyboard.py {run_dir}
python3 scripts/confirm_storyboard.py {run_dir}
python3 scripts/generate_dreamina_jobs.py {run_dir}
python3 scripts/confirm_dreamina_generation.py {run_dir}
python3 scripts/submit_dreamina_jobs.py {run_dir}
python3 scripts/query_dreamina_results.py {run_dir}
python3 scripts/confirm_shots.py {run_dir}
python3 scripts/assemble_confirmed_video.py {run_dir}
python3 scripts/plan_shot_retry.py {run_dir} 03 --reason "product edge is unclear"
python3 scripts/confirm_shot_retry.py {run_dir} 03
python3 scripts/submit_shot_retry.py {run_dir} --shot-id 03
python3 scripts/query_shot_retry_results.py {run_dir} --shot-id 03
python3 scripts/inspect_video_creation_adapters.py {run_dir}
python3 scripts/resume_video_creation_run.py {run_dir}
python3 scripts/handle_video_creation_reply.py {run_dir} "确认策划"
```

`confirm_creative_direction.py` is required before `generate_video_plan.py` when the run was created without explicit directions. In the natural-language entrypoint, selecting a direction automatically generates `video_plan.md` and `video_plan.json`, then waits for `确认策划`. Direct maintenance scripts keep their single-step behavior for compatibility.
`generate_storyboard.py` writes `storyboard.md`, `storyboard.json`, `prompts.md`, and `prompts.json`, then waits for `确认分镜`. `storyboard.md` must include inline image previews from `storyboard_assets/`, original image paths, and duplicate-reference warnings. In the natural-language entrypoint, `确认策划` automatically generates this Visual Storyboard.
Before `确认分镜`, users may say `删除镜头 03` or `镜头 04 图片换成 E:/path/to/image.jpg`; the Agent updates the storyboard, recalculates duration if shots are deleted, and clears affected downstream Dreamina confirmations. If real Dreamina submission already exists, direct storyboard mutation is blocked and the user must use shot-level retry.
`confirm_storyboard.py` locks the storyboard and moves the run to Dreamina job planning. In the natural-language entrypoint, `确认分镜` automatically generates `dreamina_generation/dreamina_jobs.md/json`.
`generate_dreamina_jobs.py` writes `dreamina_generation/dreamina_jobs.md` and `dreamina_generation/dreamina_jobs.json`, then waits for `确认即梦生成`. `confirm_dreamina_generation.py` records user authorization and moves the run to the submission phase; it does not submit paid jobs.
`submit_dreamina_jobs.py` defaults to dry-run and writes `dreamina_generation/dreamina_submission.md/json`. It also writes `dreamina_generation/submit_real_dreamina_jobs.ps1` and `dreamina_generation/manual_submission_template.json` so the human operator can perform real paid Dreamina submission in PowerShell when the Agent environment is not allowed to upload local assets or consume credits. The PowerShell script writes real submit IDs to `dreamina_generation/manual_submission.json`; when that file exists, `query_dreamina_results.py` reads it first and queries/downloads real Dreamina results. Pass `--execute` only in an environment explicitly allowed to call the real Dreamina CLI directly. `confirm_shots.py` locks accepted shots. `plan_shot_retry.py` and `confirm_shot_retry.py` handle one-shot retry authorization with estimated credit use. `submit_shot_retry.py` and `query_shot_retry_results.py` submit/query only the confirmed retry shot and merge the successful retry result back into `dreamina_results.json` without resubmitting other shots.
`assemble_confirmed_video.py` / `handle_video_creation_reply.py {run_dir} "合并视频"` uses local ffmpeg to concatenate downloaded shot videos in storyboard order. It also writes `editing_subtitles.md`, a manual editing aid for subtitles and voiceover text; it does not generate voice, burn subtitles, add BGM, or publish.
`inspect_video_creation_adapters.py` checks local Dreamina and ffmpeg configuration without paid generation. `resume_video_creation_run.py` writes `workflow_status.md/json` so Codex can continue from the current `workflow_state.json` phase without restarting. `handle_video_creation_reply.py` routes supported natural-language replies such as `主方向：采购指南型，辅助方向：产品细节型`, `确认策划`, `修改策划，开场更突出痛点`, `确认分镜`, `删除镜头 03`, `镜头 04 图片换成 E:/path/to/image.jpg`, `修改分镜，减少泛泛介绍`, `修改镜头03，突出产品细节`, `确认即梦生成`, `提交即梦任务`, `查询即梦结果`, `重做镜头 03`, `确认重做镜头 03`, `提交重做镜头 03`, `查询重做镜头 03`, `确认镜头`, and `合并视频` to the correct internal command. Upstream revisions clear affected downstream confirmations and keep a trace in `change_log.md`.

Dreamina execution remains confirmation-gated and may still run as dry-run by default.

## User interaction rules

- Ask one missing confirmation at a time.
- Never ask users to edit JSON directly.
- Never ask users to copy a run directory into another skill.
- If the current directory is not a valid knowledge project, stop and tell the user to open Codex in the knowledge project directory.
- If quartz-fiber-tape knowledge is missing or not official, stop and route the user to the knowledge-base Agent first.
- User wording preferences may influence style, but cannot introduce unsupported product facts, parameters, performance claims, certifications, or promises.
