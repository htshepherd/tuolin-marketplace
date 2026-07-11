---
name: tuolin-video-workflow
description: Create Tuolin quartz-fiber-tape video interviews, plans, visual storyboards, Dreamina prompts, Dreamina CLI handoff files, and stitched videos from the local knowledge-base Agent interface. Use when the user asks in Chinese to make 石英纤维隔热带 product videos for YouTube Shorts or TikTok.
---

# tuolin-video-workflow

This skill is the only user-facing entrypoint for Tuolin video creation. It consumes formal product knowledge and official image assets through the Agent读取接口. It does not maintain the knowledge base and does not depend on a separately installed interview skill.

## Scope

- Initial product: 石英纤维隔热带.
- Platforms: YouTube Shorts, TikTok, or both.
- Durations: 15, 20, 30, 45, 60, 90, or 120 seconds.
- Output: one language-specific 9:16 Dreamina-generated shot set per isolated run.
- Default Dreamina profile: `seedance2.0_vip`, 1080×1920.
- Audio, subtitles, BGM, publishing, and post-generation result improvement are out of scope.

## Hard boundaries

- Use `video_creation` Agent context only. Never read old `video_script` context.
- Do not scan unorganized raw files and do not use knowledge-card video files for planning or generation.
- Use formal product knowledge and official `content_asset` images only.
- Do not write to `knowledge/okf/`.
- Read external product names from formal knowledge/config; never invent them.
- Do not submit paid Dreamina jobs until the user says `确认即梦生成`.
- Preserve the existing PowerShell handoff, `manual_submission.json`, submit ID, resume, query/download, and ffmpeg assembly protocols.
- Each new video task gets a new timestamped run directory. Continue an existing task only when the user supplies that exact run directory.

## Video Creation Interview

Do not show or use fixed creative-direction categories, primary/supporting directions, ranked direction combinations, or a hidden replacement taxonomy.

Extract information already present in the request, then ask only unresolved core business questions:

1. target audience;
2. intended viewer takeaway;
3. desired viewer action;
4. priority product messages;
5. preferred balance between product-detail and application visuals;
6. excluded content.

Interview rules:

- Ask one question at a time.
- For each question, provide exactly one recommended answer and one short reason.
- The user may answer freely or reply `按推荐` for the current question only.
- Accept all remaining recommendations only after `剩下都按推荐` or `你来决定并直接出策划`.
- Do not ask users to decide shot count, timing, camera movement, sequence, image assignment, Dreamina mode, repetition control, or Prompt wording.
- When all core information is complete, automatically generate the plan. Do not add a separate brief-confirmation step.

## Planning and visual inspection

Before presenting a plan:

1. Read only official image `content_asset` entries linked to the product.
2. Use filename/title/tags only for initial filtering.
3. Actually open candidate images with the available image-viewing tool.
4. Inspect subject, clarity, composition, vertical-crop suitability, and near-duplicates.
5. Never infer product facts from pixels.
6. If distinct usable images cannot support the requested duration, recommend a shorter duration; never silently repeat images.

When `generate_video_plan` returns `material_visual_inspection_required`, this is an internal Codex checkpoint, not a user confirmation. In the same working turn, Codex must open every candidate `preview_path`, create one assessment for every candidate, and call `record_video_material_inspection.py`. Filename review, guessed assessments, partial coverage, and asking the user to edit the inspection JSON are not acceptable.

If the completed inspection reports that the requested duration exceeds the distinct-image capacity, stop before plan confirmation. Offer the user two plain-language choices: shorten to a supported duration, or explicitly approve deliberate image repetition. Record the chosen decision through the workflow; never infer approval.

Generate full `video_plan.md/json` and `material_visual_inspection.json`. In the Codex response, show a concise Chinese operator summary and 3–6 inspected representative images directly. Do not return only file paths.

For an English video, operator review remains Chinese, while external product names, target-language content, and Dreamina Prompts remain English. Never leak Chinese planning labels into English Prompts.

## Storyboard

When the user says `确认策划`, automatically generate:

- `storyboard.md`
- `storyboard.json`
- `prompts.md`
- `prompts.json`

In the Codex response, show every shot with:

- shot number and exact time range;
- shot purpose and visible action;
- exact image assignment;
- original image path;
- the image itself;
- duplicate-image warning when applicable.

Do not run a second routine interview. Ask another question only for a real knowledge, material, or unresolved-choice blocker.

Before `确认分镜`, support natural-language changes such as:

- `删除镜头 03`
- `把镜头 04 移到镜头 02 前面`
- `镜头 04 图片换成 E:/path/to/image.jpg`
- `修改镜头 03，突出产品织纹`

Re-display the updated visual storyboard after every change. Accidental repeated images block confirmation. Deliberate repetition requires explicit user approval and must be recorded.

For semantic requests such as “开场更突出痛点” or “镜头 03 更突出织纹”, do not merely log the request. Codex must draft the actual revised allowed fields and apply them through `apply_video_plan_revision.py` or `apply_storyboard_revision.py`, then re-display the revised plan/storyboard. Protected product identity, knowledge boundaries, format, source assets, and confirmation gates must not be rewritten through these semantic entrypoints.

There must be no `dreamina_jobs` before storyboard confirmation. `确认分镜` locks the storyboard and creates the Dreamina task plan for the first time.

## Stable Dreamina and assembly flow

After storyboard confirmation:

1. Show Dreamina job type, material, duration, estimated credits, and blockers.
2. Wait for `确认即梦生成`.
3. On `提交即梦任务`, create dry-run records and the real PowerShell handoff.
4. The Codex reply must directly print the exact PowerShell command the user can copy into Windows PowerShell.
5. Query and download with real submit IDs from `manual_submission.json`.
6. Wait for `确认镜头`.
7. On `合并视频`, concatenate downloaded shots in storyboard order and generate:
   - `dreamina_generation/stitched_video.mp4`
   - `voiceover_script.md`
   - `editing_notes.md`
   - `editing_subtitles.md`

The editing files are manual CapCut/Jianying references only. The Agent does not generate voice, burn subtitles, add BGM, or publish.

The current release does not expose shot retry or a video-result improvement workflow. If generated results are not accepted, record the rejection, stop that run, report that clearly, and start a new video task instead of mutating or resubmitting the confirmed storyboard.

## Natural-language flow

Typical user interaction:

1. `做一个15秒英文版石英纤维隔热带视频，面向欧美工业采购商，用于 YouTube Shorts 和 TikTok。`
2. Answer the current interview question, `按推荐`, or `剩下都按推荐`.
3. `确认策划`
4. Review/change the visual storyboard.
5. `确认分镜`
6. `确认即梦生成`
7. `提交即梦任务`
8. Run the PowerShell command printed by Codex.
9. `查询即梦结果`
10. `确认镜头`
11. `合并视频`

## Internal entrypoints

Ordinary users should not run these directly. Codex may use them internally:

```text
python3 scripts/create_video_creation_run.py "..." --language en --platform youtube_shorts --platform tiktok --duration 15 --project-dir /path/to/project
python3 scripts/handle_video_creation_reply.py {run_dir} "按推荐"
python3 scripts/record_video_material_inspection.py {run_dir} {assessment_json}
python3 scripts/apply_video_plan_revision.py {run_dir} {plan_change_json}
python3 scripts/apply_storyboard_revision.py {run_dir} {storyboard_change_json}
python3 scripts/handle_video_creation_reply.py {run_dir} "确认策划"
python3 scripts/handle_video_creation_reply.py {run_dir} "确认分镜"
python3 scripts/handle_video_creation_reply.py {run_dir} "确认即梦生成"
python3 scripts/handle_video_creation_reply.py {run_dir} "提交即梦任务"
python3 scripts/handle_video_creation_reply.py {run_dir} "查询即梦结果"
python3 scripts/handle_video_creation_reply.py {run_dir} "确认镜头"
python3 scripts/handle_video_creation_reply.py {run_dir} "合并视频"
python3 scripts/resume_video_creation_run.py {run_dir}
python3 scripts/inspect_video_creation_adapters.py {run_dir}
```

## Reference loading

- Read `references/industrial-seedance-prompt-rules.md` for storyboard-to-Dreamina Prompt conversion.
- Read `references/dreamina-task-planning-rules.md` for task planning, confirmation, submission, and querying.
- External Seedance/Dreamina skills are absorbed as methodology only; do not import entertainment or short-drama categories.

## Fail loudly

- If the current directory is not a valid knowledge project, stop and ask the user to open Codex in the knowledge project.
- If formal product knowledge or official image assets are missing, explain the operational fix in user language.
- Never report dry-run as real generation.
- Never accept malformed JSON, missing image paths, accidental duplicate references, unsupported claims, or plugin version mismatch silently.
