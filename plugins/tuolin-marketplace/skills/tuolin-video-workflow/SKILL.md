---
name: tuolin-video-workflow
description: Create Tuolin quartz-fiber-tape video plans and complete language-specific short-video deliverables from the local knowledge-base Agent interface. Use when the user asks in Chinese to make 石英纤维隔热带 product videos for YouTube Shorts or TikTok.
---

# tuolin-video-workflow

This skill is part of `tuolin-marketplace`. It is a video-creation application-layer Agent: it consumes formal knowledge and content assets through the Agent读取接口, but it does not maintain the knowledge base.

## Scope

- Initial scope only: 石英纤维隔热带 product videos.
- Supported platforms: YouTube Shorts, TikTok, or both.
- Supported output: one complete language-specific 9:16 video per run.
- Supported durations: 60, 90, or 120 seconds.
- Default output resolution: 1080×1920.
- Default Dreamina model for generated shots: `seedance2.0_vip`.

Out of scope:

- Workshop videos.
- Other Tuolin product lines.
- Platform titles, descriptions, post copy, hashtags, scheduling, or publishing.
- Any workflow that asks ordinary users to invoke Dreamina runner, narration tools, music tools, ffmpeg, or JSON files directly.

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
- Do not generate or embed TikTok trending songs. Background music must be commercially usable and must keep source/license metadata.

## Workflow

1. Identify a 石英纤维隔热带 video request.
2. Confirm video language version:
   - 中文版: Chinese narration, Chinese burned-in subtitles, BGM.
   - 英文版: English narration, English burned-in subtitles, BGM.
3. Confirm platform, duration, audience, and core objective.
4. Show all 16 fixed video creative directions plus exactly 3 ranked dynamic recommendations.
5. Confirm one primary creative direction and at most one supporting direction.
6. Create a run directory under:
   - `generated/reports/video-creation/{timestamp}_quartz_fiber_tape_{zh|en}/`
7. Generate `video_plan.md` and wait for `确认策划`.
8. Generate `storyboard.md`, `storyboard.json`, `prompts.md`, and `prompts.json`; wait for `确认分镜`.
9. Show complete narration script; wait for `确认旁白文案`.
10. Generate three voice samples from the same 8-12 second excerpt of the confirmed narration script.
11. Wait for a voice choice, such as `声音选 2`.
12. Generate full narration audio and sentence-level timing; wait for `确认旁白`.
13. Plan Dreamina jobs and show job type, material, duration, estimated credit use, and risks.
14. Wait for `确认即梦生成`.
15. Submit/query Dreamina jobs internally.
16. Assemble `dreamina_generation/shot_preview.mp4` with confirmed narration and temporary subtitles, but without final BGM.
17. Allow shot-level retry such as `重做镜头 03`; show estimated credit use before retry.
18. Wait for `确认镜头`.
19. Generate/select commercially usable BGM, render final subtitles, allowed information overlays, and end logo.
20. Run quality gate. Blocking defects must be fixed before showing `final_preview.mp4`.
21. Wait for `确认成片`.
22. Output:
   - Chinese: `quartz_fiber_tape_zh_9x16.mp4`
   - English: `quartz_fiber_tape_en_9x16.mp4`

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
- For final preview checks, manual review handoff, or final confirmation, read `references/video-quality-gate-rules.md`.

External Seedance/Dreamina skills are absorbed as methodology only. Do not copy entertainment, short-drama, or cinematic categories into Tuolin's fixed 16-direction industrial product taxonomy.

## Material readiness reporting

Before asking the user to confirm a video plan or Dreamina generation, always show a plain-language material readiness summary:

- How many official content assets were read for the quartz-fiber tape product.
- How many are product images, product videos, application-scene assets, and test/validation assets.
- How many can be used as real visual references for `image2video` or direct video reuse.
- Whether product-visible shots are likely to be blocked because there is no real product reference.

Do not ask the user to “sync content_asset cards” as the primary next step. Say what they need to do in operational terms, such as “请先整理石英纤维隔热带产品图片和产品视频，让视频 Agent 能读取真实产品素材。”

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
  --primary-direction multiple_benefit_overview \
  --supporting-direction product_detail \
  --project-dir /path/to/knowledge-project
```

This creates:

- `requirements.md`
- `workflow_state.json`
- `change_log.md`

Implemented planning commands:

```text
python3 scripts/generate_video_plan.py {run_dir}
python3 scripts/confirm_video_plan.py {run_dir}
python3 scripts/generate_storyboard.py {run_dir}
python3 scripts/confirm_storyboard.py {run_dir}
python3 scripts/generate_narration_script.py {run_dir}
python3 scripts/confirm_narration_script.py {run_dir}
python3 scripts/generate_voice_samples.py {run_dir}
python3 scripts/select_narration_voice.py {run_dir} 2
python3 scripts/generate_full_narration.py {run_dir}
python3 scripts/confirm_narration.py {run_dir}
python3 scripts/generate_dreamina_jobs.py {run_dir}
python3 scripts/confirm_dreamina_generation.py {run_dir}
python3 scripts/submit_dreamina_jobs.py {run_dir}
python3 scripts/query_dreamina_results.py {run_dir}
python3 scripts/confirm_shots.py {run_dir}
python3 scripts/plan_shot_retry.py {run_dir} 03 --reason "product edge is unclear"
python3 scripts/confirm_shot_retry.py {run_dir} 03
python3 scripts/submit_shot_retry.py {run_dir} --shot-id 03
python3 scripts/query_shot_retry_results.py {run_dir} --shot-id 03
python3 scripts/inspect_video_creation_adapters.py {run_dir}
python3 scripts/assemble_final_preview.py {run_dir}
python3 scripts/select_bgm_track.py {run_dir} --title "Licensed track" --source "Provider" --license "commercial-use" --local-path /path/to/bgm.mp3
python3 scripts/run_video_quality_gate.py {run_dir}
python3 scripts/record_manual_quality_check.py {run_dir} --audio-ok --visual-ok --notes "checked in video editor"
python3 scripts/confirm_final_video.py {run_dir}
python3 scripts/resume_video_creation_run.py {run_dir}
python3 scripts/handle_video_creation_reply.py {run_dir} "确认策划"
```

`generate_video_plan.py` writes `video_plan.md` and `video_plan.json`, then waits for `确认策划`. `confirm_video_plan.py` locks the plan and moves the run to the storyboard phase.
`generate_storyboard.py` writes `storyboard.md`, `storyboard.json`, `prompts.md`, and `prompts.json`, then waits for `确认分镜`. `confirm_storyboard.py` locks the storyboard and moves the run to the narration-script phase.
The narration commands currently use a mock narration provider that writes valid placeholder WAV files and stable timing metadata. This keeps the workflow contract testable before a real TTS provider is connected.
`generate_dreamina_jobs.py` writes `dreamina_generation/dreamina_jobs.md` and `dreamina_generation/dreamina_jobs.json`, then waits for `确认即梦生成`. `confirm_dreamina_generation.py` records user authorization and moves the run to the submission phase; it does not submit paid jobs.
`submit_dreamina_jobs.py` defaults to dry-run and writes `dreamina_generation/dreamina_submission.md/json`; pass `--execute` only when the real Dreamina CLI should be called. `query_dreamina_results.py` writes `dreamina_generation/dreamina_results.md/json`. `confirm_shots.py` locks accepted shots. `plan_shot_retry.py` and `confirm_shot_retry.py` handle one-shot retry authorization with estimated credit use. `submit_shot_retry.py` and `query_shot_retry_results.py` submit/query only the confirmed retry shot and merge the successful retry result back into `dreamina_results.json` without resubmitting other shots.
`inspect_video_creation_adapters.py` checks local adapter configuration without paid generation. `assemble_final_preview.py` writes the short-sentence subtitle SRT, BGM authorization metadata, and final-preview assembly manifest. `select_bgm_track.py` records the required commercially usable BGM track and local file path. `run_video_quality_gate.py` blocks final confirmation if the preview, subtitles, selected BGM metadata, shot confirmation, or filename policy fails. `record_manual_quality_check.py` records the required human audio/visual check before `confirm_final_video.py` copies `final_preview.mp4` to the final language-specific output filename.
`resume_video_creation_run.py` writes `workflow_status.md/json` so Codex can continue from the current `workflow_state.json` phase without restarting. `handle_video_creation_reply.py` routes supported natural-language replies such as `生成分镜`, `确认策划`, `修改策划，开场更突出痛点`, `确认分镜`, `修改分镜，减少泛泛介绍`, `修改镜头03，突出产品细节`, `确认旁白文案`, `生成声音样本`, `声音选 2`, `确认旁白`, `规划即梦任务`, `确认即梦生成`, `提交即梦任务`, `查询即梦结果`, `重做镜头 03`, `确认重做镜头 03`, `提交重做镜头 03`, `查询重做镜头 03`, `确认镜头`, `生成成片预览`, `运行质量门禁`, `人工音视频检查通过`, `确认成片`, and `更换背景音乐` to the correct internal command. Upstream revisions clear affected downstream confirmations and keep a trace in `change_log.md`.

Later slices will replace dry-run media adapters with production Dreamina, TTS, BGM, and ffmpeg execution adapters.

## User interaction rules

- Ask one missing confirmation at a time.
- Never ask users to edit JSON directly.
- Never ask users to copy a run directory into another skill.
- If the current directory is not a valid knowledge project, stop and tell the user to open Codex in the knowledge project directory.
- If quartz-fiber-tape knowledge is missing or not official, stop and route the user to the knowledge-base Agent first.
- User wording preferences may influence style, but cannot introduce unsupported product facts, parameters, performance claims, certifications, or promises.
