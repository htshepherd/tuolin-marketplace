---
name: tuolin-linkedin
description: Create Tuolin LinkedIn campaign plans and publishing packages from the local knowledge base. Use when the user asks in Chinese to make a LinkedIn posting plan, 30-day LinkedIn campaign, LinkedIn copy, or LinkedIn promotional content for Tuolin products.
---

# Tuolin LinkedIn Agent

This skill is part of `tuolin-marketplace`. It is an application-layer Agent: it produces LinkedIn campaign deliverables from the formal knowledge interface, but it does not maintain the knowledge base.

## Operating Boundaries

- Use this only through the Codex client.
- Run from the local knowledge project directory, not from the plugin repository directory.
- Read knowledge only through `generated/agent-interface/`.
- Do not scan `raw/` for LinkedIn content or images.
- Do not write LinkedIn outputs back to `knowledge/okf/`.
- Do not treat campaign outputs as formal knowledge.
- Do not authorize, schedule, or automatically publish LinkedIn posts.
- Use internal product `石英纤维隔热带` / `product/quartz_fiber_tape` for retrieval.
- Use external product name `特种玻璃纤维带` in Chinese campaign content.
- Use external product name `Specialty Glass Fiber Tape` in English publishing content.
- Do not use `Quartz Fiber Tape` in user-copyable external publishing content.
- Content assets may support image selection and image briefs only; they do not prove product performance facts.
- Watermarked publishing images require an independent transparent logo file. Prefer `linkedin.transparent_logo_path` from config, defaulting to `assets/logo/tuolin-logo-transparent.png`; reference images are layout examples only.

## Natural Language Entry Points

Common user requests:

- “请做一个30天在Linkedin上发贴宣传的计划。”
- “确认策划，活动文件夹：<campaign-dir>”
- “确认中文总稿，活动文件夹：<campaign-dir>”
- “生成 LinkedIn 配图，活动文件夹：<campaign-dir>，源图：<approved-image.png>”
- “生成 LinkedIn 配图，活动文件夹：<campaign-dir>，logo：<transparent-logo.png>，源图：<approved-image.png>”
- “重新生成 LinkedIn Day 03 发布图，活动文件夹：<campaign-dir>，tags：1000°C Heat Resistance, No Itching, No Smoke”

The natural-language router supports the full manual flow: Chinese plan, Chinese 30-day draft, English daily publishing package, static image generation, and single-day image regeneration with manually supplied tags. Each step stops for user confirmation; no step publishes to LinkedIn.

## Internal Tools

Use this script only as an internal implementation helper:

```bash
python3 scripts/create_linkedin_campaign.py "请做一个30天在Linkedin上发贴宣传的计划。要求：产品面向欧美市场；产品名称不叫石英纤维，改成特种玻璃纤维带；重点突出带子的耐高温1000度、不刺痒、不冒烟的特性。" --project-dir <knowledge-project-dir>
```

Optional deterministic output root for testing:

```bash
python3 scripts/create_linkedin_campaign.py "<request>" --project-dir <knowledge-project-dir> --output-root <desktop-or-test-dir> --timestamp 20260617_1530
```

After the user confirms the Chinese plan:

```bash
python3 scripts/confirm_linkedin_plan.py --campaign-dir <campaign-dir>
```

After the user confirms the Chinese 30-day draft:

```bash
python3 scripts/confirm_linkedin_chinese_draft.py --campaign-dir <campaign-dir>
```

After the English package exists and the user provides an approved source image, using the configured/default transparent logo:

```bash
python3 scripts/generate_linkedin_images.py --campaign-dir <campaign-dir> --source-image <approved-image.png>
```

To override the configured/default transparent logo:

```bash
python3 scripts/generate_linkedin_images.py --campaign-dir <campaign-dir> --logo <transparent-logo.png> --source-image <approved-image.png>
```

## Campaign Flow

When the user asks for a LinkedIn 30-day campaign:

1. Confirm the current directory is a valid knowledge project with `generated/agent-interface/`.
2. Build a `linkedin_post` downstream context for `product/quartz_fiber_tape`.
3. Create a desktop campaign folder named `拓霖领英30天_特种玻璃纤维带_YYYYMMDD_HHMM`.
4. Write `01_中文策划.md`.
5. Initialize `daily/`, `assets/logo/`, `assets/source-images/`, and `assets/publishing-images/`.
6. Write the resolved default transparent logo path into `campaign-manifest.json`.
7. Write `campaign-manifest.json` with status `planning_ready`.
8. Stop and ask the user to confirm the Chinese plan before generating the Chinese 30-day draft.

When the user confirms the Chinese plan:

1. Read `campaign-manifest.json` from the campaign folder.
2. Require status `planning_ready`.
3. Write `02_中文30天贴文总稿.md`.
4. Include Day 1 through Day 30.
5. Keep the draft in Chinese for internal review.
6. Update manifest status to `chinese_draft_ready`.
7. Stop and ask the user to confirm the Chinese draft before generating the English publishing package.

When the user confirms the Chinese draft:

1. Read `campaign-manifest.json` from the campaign folder.
2. Require status `chinese_draft_ready`.
3. Write `03_英文发布总览.md`.
4. Write `04_英文发布日历.csv`.
5. Write `daily/day-01.md` through `daily/day-30.md`.
6. Write `Manual-Posting-Package/Campaign Overview.md`.
7. Write `Manual-Posting-Package/Publishing Calendar.csv`.
8. Write `Manual-Posting-Package/Day 01/LinkedIn Post Content.md`, `Asset Notes.md`, and `assets/` through Day 30.
9. Use Day 1 through Day 30, not calendar dates.
10. Include 3-5 professional LinkedIn hashtags in every daily file.
11. Keep all LinkedIn publishing manual; do not authorize, schedule, or auto-publish.
12. Update manifest status to `english_package_ready`.
13. Stop and ask the user to inspect or request edits before image generation.

When the user provides image inputs:

1. Resolve the transparent logo from explicit `logo`, then campaign manifest config/default path.
2. Require a user-provided approved source image.
3. Do not scan `raw/` for images.
4. Preserve the source image dimensions, crop, background, color, and brightness.
5. Do not add poster overlays, dark masks, title blocks, hashtag pills, cards, or generated backgrounds.
6. Overlay only transparent visual elements: the transparent logo and 2-3 daily visual tags.
7. Generate the primary human-use image at `Manual-Posting-Package/Day XX/assets/linkedin-publishing-image.png`.
8. Copy a compatibility archive to `assets/publishing-images/day-XX.png`.
9. Add publishing image references to the daily English files and each Day's `Asset Notes.md`.
10. Update manifest status to `image_assets_ready`.

When the user wants to adjust one day's image tags:

1. Require a campaign folder, Day number, and manually supplied tags.
2. Reuse the manifest's previous source image and transparent logo when present; otherwise require source image/logo paths.
3. Regenerate only that day's publishing image.
4. Keep the original source image dimensions and visual appearance.
5. Update `Manual-Posting-Package/Day XX/assets/linkedin-publishing-image.png` as the primary output.
6. Update `assets/publishing-images/day-XX.png` as the compatibility archive.
7. Update that Day's `Asset Notes.md` and manifest `custom_visual_tags`.
8. Do not modify other days and do not publish to LinkedIn.
