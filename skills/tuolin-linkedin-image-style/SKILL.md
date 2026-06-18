---
name: tuolin-linkedin-image-style
description: Generate one Tuolin LinkedIn publishing image for a single campaign day from that day's source image, tags, contact email, transparent logo, and selected image style category. Use when the user has chosen Day XX source image and one style category after the publishing image selection sheet.
---

# Tuolin LinkedIn Image Style

Use this skill only after the campaign Agent has prepared a single-day image generation plan. It creates exactly one publishing image for one selected style category.

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
