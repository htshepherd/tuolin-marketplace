---
name: tuolin-kb
description: Manage Tuolin's local knowledge base inside the Tuolin Marketplace. Use when the user asks in Chinese to initialize, inspect, organize, update, review, or query Tuolin knowledge materials.
---

# Tuolin Knowledge Base Agent

This skill is part of `tuolin-marketplace`. The marketplace may contain multiple Tuolin agents; this skill only covers the local knowledge base agent.

## Operating Boundaries

- Use this only through the Codex client.
- Do not present scripts as a user-facing standalone CLI product.
- Treat `raw/` as original evidence. Do not move, rename, delete, or write generated files into raw.
- Treat “核心资料” as exactly `raw/00_知识库核心资料/`. No other folder is allowed to mean core materials.
- Treat `knowledge/okf/` as the official knowledge layer. Human-confirmed card edits live here.
- Treat `generated/` as rebuildable output. Do not ask humans to maintain it manually.
- Treat `config/tuolin-okf-profile/` as the card template profile. Initialize it automatically; ordinary users do not configure templates by hand.
- Use Chinese business titles for card filenames, the `title` field, and user-visible summaries. English names belong in `id` or `aliases`, not as the main title.
- Treat `knowledge/okf/首页.md` and `knowledge/okf/变更记录.md` as rebuildable navigation files, not fact sources.
- MinerU and ffmpeg may be called as internal local tools by Codex.
- On Windows, check local dependencies before first use.

## Natural Language Entry Points

Common user requests:

- “整理一下拓霖知识库。”
- “查看当前还有哪些资料需要继续整理。”
- “查看知识库状态。”
- “阅读一下知识库核心资料，整理进知识库。”
- “整理石英纤维隔热带资料。”
- “继续看核心资料里的图片、报告和视频。”
- “整理不好判断归属的素材。”
- “有哪些内容需要我确认？”
- “更新一下知识库。请先告诉我哪些资料需要更新，执行前等我确认。”

Route these requests through `route_natural_language.py` before choosing lower-level tools.

## Internal Tools

Use these scripts only as internal implementation helpers:

```bash
python3 scripts/validate_project.py --project-dir <project-dir>
python3 scripts/run_acceptance.py --project-dir <acceptance-project-dir>
python3 scripts/initialize_project.py --project-dir <project-dir>
python3 scripts/validate_cards.py <project-dir>/knowledge/okf
python3 scripts/prepare_pdf_text.py <project-dir>/raw/example.pdf --project-dir <project-dir>
python3 scripts/extract_video_keyframes.py <project-dir>/raw/example.mp4 --project-dir <project-dir>
python3 scripts/scan_partitions.py --project-dir <project-dir>
python3 scripts/organize_partition.py 标准法规 --project-dir <project-dir>
python3 scripts/organize_product.py 石英纤维隔热带 --project-dir <project-dir>
python3 scripts/organize_core_upstream.py --project-dir <project-dir> --preview-only
python3 scripts/organize_core_upstream.py --project-dir <project-dir>
python3 scripts/list_reviews.py --project-dir <project-dir>
python3 scripts/list_reviews.py --project-dir <project-dir> --partition 石英纤维隔热带
python3 scripts/preview_review.py review_item/quartz_fiber_tape/product_facts_pending --decision approve_external --project-dir <project-dir>
python3 scripts/apply_review.py review_item/quartz_fiber_tape/product_facts_pending --decision approve_external --confirmation-token <token-from-preview> --project-dir <project-dir>
python3 scripts/rebuild_generated.py --project-dir <project-dir>
python3 scripts/read_agent_interface.py --project-dir <project-dir> status
python3 scripts/read_agent_interface.py --project-dir <project-dir> cards product
python3 scripts/read_agent_interface.py --project-dir <project-dir> search 石英纤维隔热带
python3 scripts/read_agent_interface.py --project-dir <project-dir> evidence product/quartz_fiber_tape
python3 scripts/read_agent_interface.py --project-dir <project-dir> reviews
python3 scripts/route_natural_language.py "整理一下拓霖知识库。" --project-dir <project-dir>
python3 scripts/route_natural_language.py "确认，按推荐的下一步执行。" --project-dir <project-dir>
python3 scripts/answer_question.py "石英纤维隔热带适合哪些客户场景？" --project-dir <project-dir>
```

On Windows:

```powershell
.\scripts\windows_check_dependencies.ps1
```

## First-Run Behavior

When the user asks to set up the knowledge base:

1. Confirm the target local knowledge project directory.
2. Validate that `raw_dir`, `knowledge_dir`, and `generated_dir` do not overlap.
3. Initialize `config/tuolin-okf-profile/profile.yaml` and the ten card templates.
4. Initialize `knowledge/okf/首页.md`, `knowledge/okf/变更记录.md`, the ten card directories, and generated output directories.
5. If requested, create the raw template directory structure.
6. Report the result in business language.

## PDF And Video Boundary

- If a PDF has a same-name Markdown file beside it in `raw/`, read that Markdown.
- If not, use local MinerU CLI and write conversion output to `generated/cache/pdf-markdown/`.
- Use ffmpeg for video keyframes and write frames to `generated/cache/video-frames/`.
- Report MinerU or ffmpeg failures with the failed file and error message.
- Do not use filenames, OS previews, browser screenshots, or temporary scripts as substitutes for PDF text extraction or video keyframe extraction.

## Partition Status

Use `scan_partitions.py` when the user asks:

- “整理一下拓霖知识库。”
- “查看当前还有哪些资料需要继续整理。”
- “查看知识库状态。”
- “更新一下知识库。”

Rules:

- Do not treat `raw/00_知识库核心资料/` as a long-term business partition.
- The business priority is: first organize the core upstream queue when the user explicitly asks to整理核心资料; after core materials are handled, prioritize `石英纤维隔热带` before other product or domain partitions whenever it still has a next action.
- Product partitions may include the core upstream queue in their fingerprint.
- If the user says “高硅氧纤维隔热带资料” without adhesive/non-adhesive, ask them to choose or recommend one explicit partition.
- Missing or empty raw folders should produce `prepare_raw`, not a fake complete knowledge result.
- Do not say a partition is “整理完了” unless `pending_material_count`, `pending_processing_count`, `review_item_count`, and `recognized_unapplied_count` are all zero.
- `ready` means business knowledge can be used; it does not by itself mean all PDFs and videos have been deeply processed. Always report PDF and video progress separately.

## Partition Scope Protocol

Every natural-language organization request must resolve to exactly one fixed raw folder before reading files:

- `整理石英纤维隔热带资料` means only `raw/01_产品/02_石英纤维隔热带/`.
- `整理公司资料` means only `raw/02_公司能力/`.
- `整理标准资料` means only `raw/03_标准法规/`.
- `整理市场资料` means only `raw/04_市场情报/`.
- `整理销售物料` means only `raw/05_销售物料/`.
- `整理客户问题` or `整理客服反馈` means only `raw/06_客户问题与客服反馈/`.
- `整理不好判断归属的素材` means only `raw/90_待迁移素材暂存区/`.

Rules:

- Do not broaden any partition request by keyword search across other raw folders.
- Do not use `generated/cache/` as source material for a partition organization request. Cache files are tool outputs and can only support the explicit file that produced them.
- `fingerprint_raw_paths` can be broader for update detection, but write-time card generation must use only the resolved partition raw folder.
- Cross-partition relations are allowed only as explicit references or review candidates; they do not authorize reading another partition during the current organization action.
- All generated cards for a partition must have `raw_partitions` set to that partition's fixed raw folder. Evidence `source_paths` must also stay under that folder.

## Product Tracer

Use `organize_product.py` for the Slice 05 product tracer after the user confirms a specific product partition.

Current behavior:

- A product name always means the matching folder under `raw/01_产品/`. For example, `石英纤维隔热带` means exactly `raw/01_产品/02_石英纤维隔热带/`.
- When organizing a product partition, do not search or merge `raw/00_知识库核心资料/`, `raw/04_市场情报/`, `raw/05_销售物料/`, `raw/06_客户问题与客服反馈/`, `raw/90_待迁移素材暂存区/`, or `generated/cache/pdf-markdown/`.
- Generates a draft product card.
- Generates evidence cards for raw files.
- Generates content asset cards for images and videos.
- Generates application scenario cards for files under `04_应用场景素材/`.
- Generates a review item for product facts that still need confirmation.
- Rebuilds generated indexes and reports.
- Does not invent product parameters or external claims.

## All-Partition Organization

Use `organize_partition.py` as the preferred internal write tool after the user confirms a specific partition. It accepts product and domain partition names, including:

- The five product partitions.
- `公司能力`
- `标准法规`
- `市场情报`
- `销售物料`
- `客户问题/客服反馈`
- `待迁移素材暂存区`

Current behavior:

- Product partitions delegate to the product tracer and keep product facts in draft/review until confirmed.
- Company capability materials generate draft company capability cards, evidence cards, and review items.
- Standards materials generate draft standard cards, evidence cards, and review items.
- Market materials generate draft market intelligence cards, evidence cards, and review items.
- Sales materials generate draft sales material cards, evidence cards, and review items.
- Customer question/support materials generate internal-only draft customer question cards, evidence cards, and review items.
- The temporary manual-judgment buffer generates only `MANUAL_REVIEW_BUFFER_REPORT.md` and manual-judgment review items.

Rules:

- Do not fabricate official cards when materials are missing or incomplete.
- Do not create free-form Markdown directly under `knowledge/okf/` as a completed knowledge result. Formal knowledge must be written as one of the ten card types.
- Do not ask the user to request technical card checks. Validate and rebuild the generated interface before reporting that materials are organized.
- Keep the main card title in Chinese. Put English product names, test names, platform names, and customer wording into `aliases`, evidence text, or source paths.
- Do not broaden a product organization request by keyword search. Related sales, market, customer-service, core, or cached PDF materials must be handled by their own explicit flow.
- If `首页.md` or `变更记录.md` cannot be patched because of old encoding, stale text, or merge mismatch, do not ask the user what to do. Back up the old navigation file under `generated/cache/navigation-backups/`, rebuild the navigation file, continue writing formal cards, then validate and refresh `generated/`.
- Do not let market, sales, or customer materials create product facts.
- Images and videos can support appearance or content-asset notes only; performance, certification, safety, and compliance claims require reports, standards, or human confirmation.
- Keep temporary manual-judgment materials out of official knowledge until a human decides where they belong.

## Core Upstream Queue

Use `organize_core_upstream.py --preview-only` when the user says:

- “请先生成核心资料修改预览，不要直接写回。”
- “阅读一下知识库核心资料，整理进知识库。有需要我确认的内容，请先列出来让我确认。”

Use `organize_core_upstream.py` only after the user confirms that Codex may整理核心资料候选内容。

Current behavior:

- Scans only `raw/00_知识库核心资料/`.
- Never include temporary folders whose names contain “核心资料”, including `raw/90_待迁移素材暂存区/00_核心资料PDF暂存/`; those belong to migration/manual judgment, not the core upstream queue.
- Does not treat core materials as a long-term business partition.
- Generates evidence cards for core source files.
- Routes customer answers to draft customer question cards.
- Routes public materials to draft content asset cards.
- Routes product comparison materials to draft application scenario cards.
- Routes product fact candidates to recognized-unapplied records and review items, not directly into product cards.
- Writes previews and intermediate records under `generated/cache/`.
- Never moves, deletes, renames, or writes back to `raw/`.

## Review Write-Back

Use `list_reviews.py` when the user asks:

- “有哪些内容需要我确认？”
- “石英纤维隔热带有哪些内容需要我确认？”

Use `preview_review.py` when the user asks for a modification preview. Show the affected cards, evidence refs, proposed changes, and confirmation token in business language.

Use `apply_review.py` only after the user explicitly confirms the preview. The confirmation token must come from the latest preview.

Current decisions:

- `approve_external`: promote affected draft cards to `official` and `external_allowed`.
- `approve_internal`: promote affected draft cards to `official` and `internal_only`.
- `reject`: archive the review item without changing affected cards.
- `defer`: archive the review item as a recorded decision without changing affected cards.

Rules:

- Do not modify an existing `official` card through this generic path.
- Do not create facts from a review item body automatically.
- After applying a decision, update `knowledge/okf/变更记录.md`, archive the review item, refresh `generated/`, and keep the review record for traceability. If the changelog cannot be appended cleanly, back it up, rebuild it, append the decision, and continue without asking the user.

## Generated Agent Interface

Use `rebuild_generated.py` when `generated/` is missing, stale, or needs to be recreated from `knowledge/okf/`.

Use `read_agent_interface.py` for generated-layer reads:

- `status`: read manifest, ten-card counts, partition status, pending material counts, recognized-unapplied counts, review counts, and recommended next actions.
- `cards <type>`: read one of the ten card type indexes.
- `search <query>`: search official allowed cards and evidence cards by title, alias, tag, partition, product, evidence ref, or source path.
- `evidence <card_id>`: return evidence cards linked from a card.
- `reviews`: return open review items.

Rules:

- Default reads must not return `draft`, `review_required`, or `archived` cards as facts.

## Natural Language Routing

Use `route_natural_language.py` first for ordinary employee wording. Use lower-level scripts only after the route response identifies a confirmed internal action or during developer validation.

Supported flows:

- “整理一下拓霖知识库。” returns one recommended next step and a copyable confirmation reply.
- “查看当前还有哪些资料需要继续整理。” returns only actionable partitions.
- “查看知识库状态。” returns full partition status and card counts in business language.
- “全量整理/从头整理/重新整理” returns a partition queue and waits for confirmation.
- “整理高硅氧纤维隔热带资料。” asks the user to choose adhesive or non-adhesive.
- “阅读一下知识库核心资料，整理进知识库。” creates a preview before writing knowledge cards.
- Confirmed wording can execute supported write actions, such as all-partition organization or core upstream organization.

Rules:

- Do not execute knowledge-layer writes unless the route sees explicit confirmation.
- For general “整理一下拓霖知识库” or “查看当前还有哪些资料需要继续整理” requests, recommend `石英纤维隔热带` first when it has any actionable state. This reflects the current business focus on the quartz product.
- User-visible messages should say “整理资料”“继续看资料”“整理成可用资料”“需要你确认”.
- For status answers, distinguish “业务可用” from “素材处理完成”. If PDFs or videos remain pending, say the partition is usable but still has material work left.
- Avoid exposing internal terms such as cache, indexes, manifest, frontmatter, or generated file paths as the main answer.
- Every suggested next step should include a copyable Chinese reply.

## Official-Only Q&A

Use `answer_question.py` or the natural-language route for business questions such as:

- “石英纤维隔热带适合哪些客户场景？”
- “陶瓷纤维隔热带和玄武岩纤维隔热带有什么区别？”
- “哪些产品适合排气管隔热？”

Rules:

- Read only `generated/agent-interface/`; do not scan `raw/`.
- Use only `official` fact cards with an allowed `usage_scope`.
- Treat evidence-only cards as citations, not as standalone product facts.
- Do not use `draft`, `review_required`, or `archived` cards as facts.
- If the relevant partition is `needs_update`, tell the user to update that partition first.
- When no confirmed answer exists, say “无法给出已确认答案” and give a concrete next step.

## Acceptance Checks

Use `run_acceptance.py` for maintainer validation after implementation changes. It creates a local sample project, runs the main knowledge-base workflow, and writes `generated/reports/ACCEPTANCE_REPORT.md`.

The acceptance runner must verify:

- All nine PRD use cases have a pass record.
- All ten card types appear in generated indexes.
- Product organization, review preview/apply, official-only Q&A, raw update detection, and generated rebuild all pass.
- System actions do not modify raw files.
- Windows dependency check and Codex plugin manifest are present.

For human validation, use `doc/acceptance-checklist.md`.

## Do Not

- Do not run unbounded full-library scans.
- Do not write into `raw/`.
- Do not treat videos as product facts.
- Do not treat customer conversations as product facts.
- Do not use unconfirmed draft or review-required cards as official answers.
- Do not expose internal filenames as the primary user action.
