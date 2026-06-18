---
name: tuolin-linkedin-marketing-review
description: Review Tuolin LinkedIn Chinese marketing plans before campaign drafting. Use when Codex needs to review `01_中文策划.md`, output marketing conclusion, risks, concrete revision suggestions, and whether the plan should proceed to the 30-day Chinese post draft.
---

# Tuolin LinkedIn Marketing Review

Use this skill only for the LinkedIn campaign planning gate. It reviews `01_中文策划.md`; it does not review formal knowledge cards, does not write to the knowledge base, and does not generate posts or publishing images.

## Workflow

1. Locate the campaign folder and read `01_中文策划.md`.
2. Read `references/review-checklist.md`.
3. Read `references/review-output-format.md`.
4. Review only the marketing plan for market fit, product naming, message clarity, claim safety, and workflow compliance.
5. Write or update `01_中文策划_营销审阅.md` in the same campaign folder.
6. Return a concise conclusion to the user: pass, pass with changes, or do not proceed yet.
7. Ask the user to choose whether to采纳 or不采纳 the review before generating `02_中文30天贴文总稿.md`.

## Boundaries

- Do not generate `02_中文30天贴文总稿.md` inside this skill unless the user explicitly confirms the review decision through the Agent flow.
- Do not create English posts.
- Do not create publishing images.
- Do not introduce unverified claims.
- Do not rename the public product to quartz fiber.
- Treat content assets as visual material only; they do not prove performance claims.

## Required Product Positioning

- Public Chinese name: `特种玻璃纤维带`.
- Public English name: `Specialty Glass Fiber Tape`.
- Core benefits: `1000°C working temperature`, `itch-free handling`, `no smoke`.
- Market: Europe and North America.
- Posting mode: manual LinkedIn posting only.
