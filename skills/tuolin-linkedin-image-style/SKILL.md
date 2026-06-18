---
name: tuolin-linkedin-image-style
description: Generate one Tuolin LinkedIn publishing image for a single campaign day from that day's selected source image, tags, contact email, transparent logo, and selected image style category. Use only after the user has already chosen Day XX source image and one style category from the publishing image selection sheet, such as "Day 01 源图选 1，风格选：原图轻量增强型". Do not use for the initial request "生成 LinkedIn Day XX 发布图"; that request must be handled by tuolin-linkedin to create a selection sheet first.
---

# Tuolin LinkedIn Image Style

Use this skill only after the campaign Agent has prepared a single-day image generation plan. It creates exactly one publishing image for one selected style category.

If the user only says `生成 LinkedIn Day XX 发布图`, stop and route to `tuolin-linkedin`; do not generate an image from this skill yet.

If the user has not explicitly selected a source image index and at least one exact style category name, do not infer the style from the Day topic and do not generate a publishing image.

## Workflow

1. Read the Day folder:
   - `Manual-Posting-Package/Day XX/LinkedIn Post Content.md`
   - `Manual-Posting-Package/Day XX/Asset Notes.md`
   - `Manual-Posting-Package/Day XX/Publishing Image Selection.md`
2. Read the selected source image path and output directory from the Agent response or `campaign-manifest.json`.
3. Read `references/style-categories.md` for the selected category.
4. Read `references/style-prompt-rules.md`.
5. Read `references/size-recommendations.md`.
6. Generate exactly one image for the chosen category.
7. Save it under `Manual-Posting-Package/Day XX/Publish-Images/<category-slug>/`.
8. If the manifest has `desktop_delivery.path`, copy the generated image to the matching desktop Day folder.

## Required Overlay Content

- Transparent Tuolin logo from the configured logo path.
- Day-specific visual tags from the Day files or selection sheet.
- Contact email: `tuolin@tuolintech.com`.

## Hard Rules

- Generate one image only.
- Base the result on the selected Day source image.
- Preserve real product appearance unless the selected category explicitly requires a creative layout.
- Do not claim or imply unverified test results.
- Do not use Chinese text on the LinkedIn publishing image unless the user explicitly asks.
- Do not automatically publish to LinkedIn.
- Do not create `prompt.md` or `source-info.json` files.
