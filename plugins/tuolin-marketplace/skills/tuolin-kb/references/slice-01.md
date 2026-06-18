# Slice 01 Reference

Slice 01 establishes the repository and project layout only.

Acceptance checklist:

- `.codex-plugin/plugin.json` exists and points to `./skills/`.
- The repository is structured as a multi-agent marketplace.
- Knowledge base files are under a dedicated skill/module, not the whole repository.
- `raw_dir`, `knowledge_dir`, and `generated_dir` can be resolved from config.
- The three paths cannot overlap or nest inside one another.
- `knowledge/okf/首页.md` and `knowledge/okf/变更记录.md` are navigation files, not knowledge cards.
- Ten Chinese knowledge card directories can be initialized.
- `generated/` can be deleted and recreated.
- Windows dependency checks exist.
- Employee-facing docs do not describe a standalone user CLI product.

Slice 02 extends this with OKF card validation:

- Ten card types are recognized.
- Common fields and type-specific fields are validated.
- Navigation files are skipped.
- Chinese card directories are allowed, while card `id` values remain stable English identifiers.

Slice 04 extends this with partition scanning:

- Eleven business partitions are recognized.
- `raw/00_知识库核心资料/` is an upstream queue, not a long-term business partition.
- Partition summaries include status, pending material count, recognized-but-unapplied count, review count, raw change time, organized time, and recommended next action.
- High-silica requests without adhesive/non-adhesive are ambiguous.

Slice 05 extends this with the first product organization tracer:

- The quartz product partition can produce product, evidence, content asset, application scenario, and review item cards.
- Product facts remain draft/review until evidence or human confirmation is available.
- Generated indexes and reports are refreshed.
