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
- “进行营销策划审阅，活动文件夹：<campaign-dir>”
- “采纳营销审阅建议，活动文件夹：<campaign-dir>”
- “确认策划，活动文件夹：<campaign-dir>”
- “确认中文总稿，活动文件夹：<campaign-dir>”
- “将30天发帖计划复制到桌面方便查看，活动文件夹：<campaign-dir>”
- “生成 LinkedIn Day 01 发布图，活动文件夹：<campaign-dir>”
- “Day 01 源图选 1，风格选：原图轻量增强型，活动文件夹：<campaign-dir>”

The natural-language router supports the manual flow: Chinese plan, optional marketing review, Chinese 30-day draft, English daily publishing package, desktop review copy, and single-day image generation preparation. Each step stops for user confirmation; no step publishes to LinkedIn.

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

## Campaign Flow

When the user asks for a LinkedIn 30-day campaign:

1. Confirm the current directory is a valid knowledge project with `generated/agent-interface/`.
2. Build a `linkedin_post` downstream context for `product/quartz_fiber_tape`.
3. Create a desktop campaign folder named `拓霖领英30天_特种玻璃纤维带_YYYYMMDD_HHMM`.
4. Write `01_中文策划.md`.
5. Initialize `daily/`, `assets/logo/`, and `assets/source-images/`.
6. Write the resolved default transparent logo path into `campaign-manifest.json`.
7. Write `campaign-manifest.json` with status `planning_ready`.
8. Stop and ask whether to run marketing review before generating the Chinese 30-day draft.

When the user asks for marketing review:

1. Read `01_中文策划.md`.
2. Use `tuolin-linkedin-marketing-review`.
3. Write `01_中文策划_营销审阅.md`.
4. Update manifest status to `marketing_review_ready`.
5. Stop and ask whether the user采纳 or不采纳 the review.

When the user confirms the Chinese plan or records the marketing review decision:

1. Read `campaign-manifest.json` from the campaign folder.
2. Require status `planning_ready` or `marketing_review_ready`.
3. Write `02_中文30天贴文总稿.md`.
4. Include Day 1 through Day 30.
5. Keep the draft in Chinese for internal review.
6. Record whether marketing review was skipped, accepted, or rejected.
7. Update manifest status to `chinese_draft_ready`.
8. Stop and ask the user to confirm the Chinese draft before generating the English publishing package.

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
13. Stop and ask the user to copy the package to the desktop for review or inspect/request edits.

When the user asks to copy the 30-day posting plan to the desktop:

1. Require that `02_中文30天贴文总稿.md` exists.
2. Copy the whole campaign folder to the desktop review directory.
3. Store `desktop_delivery.path` in `campaign-manifest.json`.
4. Future single-day publishing images should also be copied to the matching desktop Day folder when this path exists.

When the user asks to generate one Day's publishing image:

1. Require the English manual package.
2. Require approved source images inside `Manual-Posting-Package/Day XX/assets/`.
3. Generate `Manual-Posting-Package/Day XX/Publishing Image Selection.md`.
4. Show 20 style categories and Day-specific recommendations.
5. Ask the user to choose one source image and 1-3 categories.
6. Prepare output directories under `Manual-Posting-Package/Day XX/Publish-Images/<category-slug>/`.
7. Use `tuolin-linkedin-image-style` to generate exactly one image per selected category.
8. Do not generate all 30 days in one batch.
