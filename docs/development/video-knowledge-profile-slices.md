# 视频知识档案与下游实时素材使用：纵向切片开发文档

**日期：** 2026-07-16
**来源 PRD：** `docs/prd/video-knowledge-profile-and-runtime-use.md`
**状态：** 自动化开发完成；S01–S05、S07–S10 代码能力与自动回归已实现，S06 及各切片真实视频 HITL 统一推迟到部署至用户电脑后验收
**范围：** 知识库视频生产、Agent 接口和视频创作消费链路

## 1. 切片原则

每个切片必须交付一条可运行、可验证的业务能力，不能只完成 schema、缓存脚本或单独 UI。

稳定边界：

- raw 源视频不可变；
- 普通用户只使用自然语言；
- 知识生产和视频创作保持 Agent 边界；
- 下游 `raw_access=false`；
- 产品事实仍来自正式产品知识和证据；
- 每次知识发布必须刷新并验证 Agent 接口；
- 当前语义分析由 Codex 完成，不要求独立多模态 API Key；
- 测试验证视频最后处理。

## 2. 切片总览

| 编号 | 切片 | 类型 | Blocked by | 端到端价值 |
| --- | --- | --- | --- | --- |
| S01 | 真实产品视频 tracer：登记到可读档案 | AFK + HITL | 无 | 一条真实视频首次能回答“讲了什么” |
| S02 | Tracer Agent 接口与运行时抽帧 | AFK + HITL | S01 | 下游按 ID 获取档案和精确任务帧 |
| S03 | Tracer 真实片段进入分镜与组装 | AFK + HITL | S02 | 真实 raw 片段成为视频创作输入 |
| S04 | `video_profile` 正式卡型与事务式发布 | AFK | S01-S03 | 从 tracer 临时路径收敛到正式知识模型 |
| S05 | 单视频原子检查点、恢复与批次预检 | AFK | S04 | 批次中断不重做，环境故障不污染视频状态 |
| S06 | 产品视频 8 条批次与全量验收 | HITL | S05 | 产品视频全部形成可用档案 |
| S07 | 应用场景文件夹分类与逐场景批次 | AFK + HITL | S06 | 127 条应用视频可按业务场景逐步上线 |
| S08 | 音频、ASR 缺口与风险策略 | AFK + HITL | S05 | 有语音和音乐的视频不被错误当成静音素材 |
| S09 | 测试验证视频与证据发布门禁 | HITL | S06-S08 | 测试视频可中性使用且不制造结论 |
| S10 | 缓存治理、撤销、迁移和全量回归 | AFK + HITL | S01-S09 | 长期维护、失效和升级可控 |

依赖关系：

```text
S01 → S02 → S03 → S04 → S05 → S06 → S07
                         └────→ S08 ──→ S09
S01-S09 ─────────────────────────────→ S10
```

## 3. 详细切片

### S01 — 真实产品视频 tracer：登记到可读档案

**类型：** AFK + HITL
**Blocked by：** 无
**当前实现状态：** 自动测试与代码能力已完成；真实 8 条视频和 tracer 人工确认列为部署验收项，不再阻塞后续代码开发。

当前部署验收事实：

- 配置中的 raw 路径不存在；
- 当前实际检查目录只发现 3/8 条产品视频；
- 3 条候选已完成 Codex 检查缓存，但未生成 tracer 正式暂存稿；
- 未获得基于完整 8 条候选的推荐和用户 Asset ID 确认。

已实现的自然语言入口：

- `确认，检查固定 raw 文件夹中的石英纤维隔热带产品视频。`
- `确认，开始处理这 8 条石英纤维隔热带产品视频候选。`
- `查看石英纤维隔热带产品视频候选状态。`
- `确认 tracer Asset ID：video_asset_...`

入口同时识别当前 legacy 固定目录 `04_产品/01_石英纤维隔热带/03_视频` 和新模板目录
`01_产品/02_石英纤维隔热带/03_产品视频`；两个目录同时含视频时阻止执行并要求人工确认。

#### 业务结果

知识库 Agent 检查固定产品视频文件夹中的全部 8 条真实视频，展示每条视频的媒体事实、风险和初步代表帧，并推荐一条低风险 tracer。用户确认文件后，该视频形成第一份可人工阅读和机器校验的档案草稿。

#### 实现内容

- 为视频登记持久化不透明 `Video Asset ID` 和来源指纹。
- 加入 `ffprobe` 媒体事实读取。
- 加入两阶段自适应抽帧：
  - 全片均匀覆盖；
  - 场景、主体、可见度、动作和状态变化候选。
- 加入黑帧、严重模糊和近重复过滤。
- 只在连续动作需要时生成分析短片。
- 由 Codex 查看准备好的帧和短片，生成固定结构的档案建议。
- 生成标题、2–4 句摘要、关键片段、锚点、产品可见度、画面描述、分类、风险、使用能力和 3–6 张代表帧。
- 保存 tracer 检查缓存和正式档案暂存稿，不修改 raw。

#### 自动测试

- `test_video_asset_id_is_opaque_and_persisted`
- `test_ffprobe_media_facts_are_not_model_inferred`
- `test_adaptive_sampling_covers_beginning_middle_end`
- `test_process_sampling_adds_before_action_after_candidates`
- `test_black_blur_and_near_duplicate_frames_are_not_representatives`
- `test_analysis_clip_is_created_only_for_temporal_need`
- `test_profile_schema_rejects_out_of_range_segments`
- `test_raw_hash_is_unchanged_after_analysis`
- `test_legacy_zero_second_frame_does_not_mark_profile_complete`

#### HITL 验收

- Codex 实际打开全部 8 条产品视频的候选帧。
- 用户明确确认 tracer 源视频。
- 对确认视频检查 3–6 张代表帧是否覆盖主要内容。
- 人工确认摘要能在不打开 raw 视频的情况下说明“视频在讲什么”。

#### 完成门槛

只生成抽帧或 JSON 不算完成。必须有一条真实视频的可阅读档案、结构化档案、代表帧和 raw 不变校验。

---

### S02 — Tracer Agent 接口与运行时抽帧

**类型：** AFK + HITL
**Blocked by：** S01
**当前实现状态：** 自动化能力已完成；使用 tracer 临时接口承接 S04 正式 `video_profile` 卡型之前的下游契约，真实视频 HITL 推迟到用户电脑部署后执行。

#### 业务结果

视频创作 Agent 可以通过 Agent 接口找到 tracer 视频、查看代表帧和关键片段，并通过 Asset ID 从授权时间范围提取精确任务帧，不接触 raw 路径。

#### 实现内容

- 新增轻量 `Video Profile Catalog`。
- 新增按 profile ID 读取完整详情。
- 新增修订绑定的代表帧引用。
- 新增受控代表帧解析；公开目录和详情不暴露生成缓存路径。
- 新增结构化/文本召回。
- 召回后由 Codex 打开小规模代表帧进行视觉复排。
- 新增运行时抽帧接口：
  - 输入 run ID、接口修订、Asset ID、profile 修订、关键片段和时间点；
  - 校验产品、授权、修订、撤销和时间范围；
  - 输出到视频创作运行目录。
- 记录成功和拒绝的提取审计。

#### 自动测试

- `test_catalog_returns_summary_without_full_transcript`
- `test_profile_detail_returns_revision_bound_representative_frames`
- `test_catalog_does_not_expose_raw_or_cache_paths`
- `test_catalog_supports_structured_and_text_recall`
- `test_representative_media_ref_resolves_without_catalog_path_leak`
- `test_runtime_frame_extraction_accepts_authorized_asset_id`
- `test_runtime_frame_extraction_rejects_arbitrary_local_path`
- `test_runtime_frame_extraction_rejects_out_of_segment_timestamp`
- `test_runtime_frame_extraction_rejects_stale_profile_revision`
- `test_runtime_frame_is_written_only_inside_video_run`
- `test_every_runtime_extraction_attempt_is_audited`
- `test_interface_reports_codex_visual_rerank_without_vector_index`

#### HITL 验收

- 用自然语言要求下游找一条“产品清晰可见且有连续操作”的视频。
- 查看目录缩略图和完整档案代表帧。
- 从锚点附近提取不超过 5 张候选任务帧。
- 确认最终任务帧与时间点和画面描述一致。

---

### S03 — Tracer 真实片段进入分镜与组装

**类型：** AFK + HITL
**Blocked by：** S02
**当前实现状态：** 自动化能力已完成；真实 tracer 片段的分镜预览、确认和组装 HITL 推迟到用户电脑部署后执行。

#### 业务结果

视频创作 Agent 能将 tracer 的真实连续动作片段用于一个具体镜头，分镜确认前显示实际任务预览，并在组装时使用该真实片段。

#### 实现内容

- 新增运行时片段提取和审计。
- 每个计划用途最多生成 3 个低成本候选预览。
- 选中后生成交付质量任务片段。
- 自动处理仅限裁切、旋转、转码、分辨率/帧率规范化、确认的裁剪/留边和按策略静音。
- 分镜记录 Asset ID、profile 修订、源时间范围、任务文件、处理方式和风险。
- 分镜确认界面显示真实任务预览，不能用代表帧替代。
- 组装流程优先使用真实任务片段。

#### 自动测试

- `test_runtime_clip_extraction_rejects_unapproved_asset`
- `test_candidate_preview_limit_is_three_per_planned_use`
- `test_task_clip_preserves_source_chronology`
- `test_only_meaning_preserving_adaptations_are_automatic`
- `test_storyboard_requires_exact_task_preview_for_real_clip`
- `test_storyboard_records_source_range_and_adaptations`
- `test_real_task_clip_is_preferred_over_regeneration`
- `test_assembly_uses_real_extracted_clip`
- `test_revoked_asset_blocks_submission_after_storyboard`

#### HITL 验收

- 在真实视频策划中选用 tracer 片段。
- 用户看到片段的实际预览、时间范围、音频策略和风险。
- 用户确认分镜后，组装输入确实是该任务片段。
- raw 哈希再次保持不变。

---

### S04 — `video_profile` 正式卡型与事务式发布

**类型：** AFK
**Blocked by：** S01-S03
**当前实现状态：** 已完成。正式 `.md/.json` 配对、专用目录、Agent catalog/detail/media 投影、接口验证和失败回滚均已实现并通过自动测试。

#### 业务结果

Tracer 证明的结构正式进入知识模型，暂存稿不会被下游读取，Agent 接口只有在新档案提升和验证全部成功后才切换。

#### 实现内容

- 在 profile 配置、模板、validator 和目录映射中新增 `video_profile`。
- 建立 `视频档案` 正式目录。
- 同一领域对象生成 `.md` 和 `.json`。
- 两份文件包含相同 profile revision 和 content digest。
- 新增 `generated/staging/video-profiles/{batch_id}/`。
- 新增原子提升、接口重建、接口验证和版本激活。
- 发布失败时保留上一已验证接口。
- Agent 接口新增 catalog、detail 和代表帧媒体索引。

#### 自动测试

- `test_video_profile_is_supported_card_type`
- `test_video_profile_markdown_and_json_share_revision_and_digest`
- `test_missing_profile_counterpart_is_invalid`
- `test_conflicting_profile_pair_is_not_indexed`
- `test_staged_profile_is_invisible_to_downstream`
- `test_successful_publication_activates_new_interface_revision`
- `test_failed_interface_verification_keeps_previous_revision_active`
- `test_video_profile_paths_use_asset_id_not_raw_filename`
- `test_generated_analysis_media_is_not_scanned_as_formal_card`

---

### S05 — 单视频原子检查点、恢复与批次预检

**类型：** AFK
**Blocked by：** S04
**当前实现状态：** 已完成。批次预检、能力回执、逐视频原子检查点、来源变化重算、断点跳过和局部故障隔离均已实现。

#### 业务结果

用户确认一个视频批次后，系统逐个视频形成检查点；会话中断可从首个未完成视频继续；工具环境不完整时在批次开始前明确阻止。

#### 实现内容

- 新增批次 manifest 和能力预检回执。
- 必需能力：ffprobe、ffmpeg、Codex 视觉查看。
- 可选能力：ASR、辅助质量和去重组件。
- 每条视频完成后写入原子检查点。
- 检查点绑定来源指纹、分类指纹、schema、策略和能力修订。
- 恢复时跳过仍匹配的有效检查点。
- 单视频故障隔离；系统性故障暂停影响范围。

#### 自动测试

- `test_batch_preflight_blocks_when_ffprobe_missing`
- `test_batch_preflight_blocks_when_ffmpeg_missing`
- `test_batch_preflight_blocks_when_codex_visual_review_unavailable`
- `test_missing_optional_asr_does_not_block_visual_profile`
- `test_checkpoint_is_saved_after_each_valid_video`
- `test_resume_skips_unchanged_valid_checkpoints`
- `test_resume_reprocesses_changed_source`
- `test_local_video_failure_does_not_rollback_other_checkpoints`
- `test_systemic_failure_pauses_affected_batch_scope`

---

### S06 — 产品视频 8 条批次与全量验收

**类型：** HITL
**Blocked by：** S05

#### 业务结果

固定产品视频文件夹中的 8 条视频全部拥有明确状态，所有有效档案完成全量人工验收并进入 Agent 接口。

#### 实现内容

- 自然语言展示批次范围、数量、工具、raw 不变承诺和验收规则。
- 用户确认后逐视频处理。
- 批次回执展示 6–12 张跨视频概览图。
- 产品视频首批全部人工复核。
- 识别 exact duplicate、near duplicate、same-event multi-angle 和 semantic-similar `Video Asset Family`。
- 选出首选片段和替代片段，不删除重复 raw。

#### 自动测试

- `test_product_batch_requires_explicit_confirmation`
- `test_product_batch_requires_full_acceptance`
- `test_batch_receipt_reports_all_profile_states`
- `test_batch_overview_uses_six_to_twelve_cross_profile_images`
- `test_exact_duplicate_assets_keep_distinct_asset_ids`
- `test_asset_family_relationship_does_not_modify_raw`
- `test_unaccepted_product_profiles_are_not_selectable`

#### HITL 验收

- 逐条检查摘要、关键片段、代表帧、产品可见度、分类和风险。
- 系统性缺陷阻止整个影响批次。
- 验收通过后验证新 Agent 接口版本。

---

### S07 — 应用场景文件夹分类与逐场景批次

**类型：** AFK + HITL
**Blocked by：** S06
**当前实现状态：** 自动化能力已完成；一级场景分批、完整后代路径、来源/视觉冲突、风险抽样、场景验收和范围撤销均已实现。127 条真实应用视频 HITL 推迟到用户电脑部署后执行。

#### 业务结果

应用场景素材按固定一级子文件夹逐批生成视频档案，并保留更深目录上下文。下游可以按具体应用场景检索，而不是面对一个扁平的 127 视频列表。

#### 实现内容

- 第一级子文件夹映射为 `Source Application Scenario`。
- 完整后代路径有序保存。
- 文件夹分类和画面观察分别记录。
- 每个场景首次批次执行风险抽样验收：
  - 不超过 10 条全量；
  - 超过 10 条至少 5 条，覆盖首选、低置信、长视频和有音频视频。
- 稳定增量批次抽查 10%，最少 3 条。
- 批次按场景影响范围撤销，不影响其他已验证场景。

#### 自动测试

- `test_first_application_child_is_canonical_source_scenario`
- `test_deeper_application_folders_are_preserved_in_order`
- `test_source_scenario_does_not_override_visual_observation`
- `test_first_scenario_batch_acceptance_sample_is_risk_based`
- `test_stable_scenario_increment_uses_ten_percent_minimum_three`
- `test_scenario_systemic_defect_revokes_only_affected_scope`

---

### S08 — 音频、ASR 缺口与风险策略

**类型：** AFK + HITL
**Blocked by：** S05
**当前实现状态：** 自动化能力已完成；本地优先 ASR 合同、缺失状态、转录脱敏、片段音频策略、运行时静音门禁和音频增量事务发布均已实现。真实音频 HITL 推迟到用户电脑部署后执行。

#### 业务结果

有语音、音乐、客户信息或机器声的视频拥有明确音频观察和使用策略；ASR 缺失不会被伪装成完整分析。

#### 实现内容

- 建立 `Speech Transcription Adapter` 接口。
- 默认本地优先，不自动上传企业视频。
- 保存完整时间码转录详情和敏感/claim 标注。
- catalog 只返回音频摘要，不注入完整转录。
- ASR 缺失时设置 `audio_understanding_incomplete`。
- 每个可用片段设置 retain、mute-recommended、mute-required 或 human-review-required。
- 后续补转录只更新音频部分、provenance 和 Agent 接口。

#### 自动测试

- `test_asr_adapter_output_keeps_language_and_timestamps`
- `test_no_speech_video_may_skip_transcription`
- `test_clear_speech_without_asr_marks_audio_incomplete`
- `test_asr_unavailable_does_not_claim_no_important_speech`
- `test_sensitive_transcript_is_redacted_from_downstream`
- `test_original_audio_is_blocked_for_privacy_or_rights_risk`
- `test_transcript_refresh_does_not_regenerate_unrelated_visual_semantics`

---

### S09 — 测试验证视频与证据发布门禁

**类型：** HITL
**Blocked by：** S06-S08
**当前实现状态：** 自动化能力已完成；候选/确认即证据关系、中性描述、身份与条件门禁、测试风险人工复核、运行时不可误导裁切、原音频结论处理以及下游 `test_summary` 均已接入。真实测试验证视频仍按约定最后处理，并在用户电脑部署后执行 HITL。

#### 业务结果

测试视频可以被下游理解和选择，但不会因为“看起来像测试”而制造通过、耐温或性能结论。

#### 实现内容

- 测试片段覆盖前、过程、后。
- 分离 `Candidate Video Evidence Link` 与 `Confirmed Video Evidence Link`。
- 目录相邻只能创建候选证据关系。
- 外部结论必须使用确认关系且不得超出证据范围。
- 无证据时只允许经复核的中性画面描述。
- 产品身份、条件或前后关系不清时阻止外部使用。
- 防止误导性裁切、重排和原音频结论复用。

#### 自动测试

- `test_directory_proximity_creates_candidate_not_confirmed_evidence_link`
- `test_only_confirmed_evidence_link_supports_external_test_claim`
- `test_test_clip_without_evidence_uses_neutral_observation_only`
- `test_unclear_test_identity_or_conditions_block_external_use`
- `test_runtime_trim_cannot_hide_adverse_test_state`
- `test_unsupported_spoken_test_conclusion_is_muted_or_excluded`
- `test_all_test_risk_fields_require_human_review`

#### HITL 验收

- 所有测试视频风险字段人工复核。
- 选取一条有正式证据和一条无正式证据的测试视频，验证对外能力不同。
- 验证剪辑预览没有改变前后含义。

---

### S10 — 缓存治理、撤销、迁移和全量回归

**类型：** AFK + HITL
**Blocked by：** S01-S09
**当前实现状态：** 自动化能力已完成；缓存 manifest 与 30 天清理、活动/争议引用保护、Asset ID 移动/复制/替换协调、档案 amendment/exclusion/revocation、结构迁移与语义重分析门禁、来源修订失效以及有效档案进度重算均已实现。真实移动、复制、替换、撤销和缓存清理演练推迟到用户电脑部署后执行。

#### 业务结果

视频档案链路可长期维护：缓存不会无限增长，来源移动/复制/替换能正确处理，撤销立即影响下游，schema 升级不会伪造新语义。

#### 实现内容

- 建立缓存 manifest 和 30 天清理策略。
- 有效代表帧随当前 profile revision 保留。
- 争议、失败和待复核缓存问题解决前保留。
- 实现 Asset ID 移动/复制/替换协调。
- 实现档案 amendment、exclusion、revocation 和 migration。
- 只允许确定性结构迁移；新语义字段要求重分析。
- 重算视频处理进度，不再读取旧单帧缓存作为完成依据。
- 跑完整 tracer、产品、应用、测试和视频创作回归。

#### 自动测试

- `test_cache_cleanup_uses_manifest_and_live_references`
- `test_current_representative_frames_are_not_cleaned`
- `test_disputed_cache_is_retained`
- `test_raw_video_is_never_classified_as_cache`
- `test_verified_move_preserves_asset_id`
- `test_concurrent_copy_receives_new_asset_id`
- `test_same_path_replacement_creates_new_source_revision`
- `test_ambiguous_move_or_copy_requires_review`
- `test_local_profile_amendment_refreshes_interface`
- `test_semantic_schema_change_requires_reanalysis_not_default_migration`
- `test_revocation_blocks_retrieval_extraction_and_submission`
- `test_progress_counts_valid_profiles_not_legacy_images`

#### HITL 验收

- 模拟一条视频移动、一条复制和一条同路径替换。
- 模拟撤销后检查现有运行目录保留审计文件，但后续确认或提交被阻止。
- 清理一次超过 30 天且无引用的分析缓存，确认 raw 和代表帧未受影响。

## 4. 全链路测试矩阵

| 层级 | 必测内容 |
| --- | --- |
| 单元 | 时间范围、schema、风险枚举、Asset ID、修订、缓存引用、状态机 |
| 组件 | ffprobe、ffmpeg、抽帧、分析短片、代表帧、Markdown/JSON 投影 |
| 知识集成 | 暂存、验收、原子发布、接口刷新、接口回滚 |
| 下游集成 | catalog、detail、Codex 视觉复排、任务帧、任务片段、审计 |
| 视频创作 | 策划选材、真实预览、分镜确认、撤销检查、真实片段组装 |
| 安全 | raw 路径拒绝、stale 拒绝、revoked 拒绝、测试 claim 门禁、隐私/音频风险 |
| 恢复 | 单视频检查点、会话中断、来源变化、工具系统性故障 |
| 实体素材 | 至少一条真实产品视频完整 tracer；mock 只用于异常分支 |

## 5. 现有测试的明确替换

当前 `tests/test_video_creation_agent.py` 存在“产品视频素材不得进入策划”的断言，并在 fixture 正文中写明“视频创作 Agent 不应把视频文件用于策划素材或即梦任务”。该行为与本 PRD 冲突，不能在新链路实现后继续作为正确回归。

替换规则：

- 保留“未形成有效 profile 的视频不得进入策划”；
- 保留“视频素材不能证明产品事实”；
- 将“所有视频都不得进入策划”替换为“只有当前有效、授权且通过风险过滤的视频 profile 可以进入候选”；
- 将原 `assertNotIn(content_asset/quartz_product_video, plan)` 改为两个分支：
  - 只有 `content_asset` 登记、没有有效 profile 时仍不进入策划；
  - 有效 profile 发布并由 Agent 接口返回时，可以作为真实片段或任务帧候选；
- 新增 stale、excluded、revoked、跨产品、任意 raw 路径和接口修订不匹配的拒绝用例；
- 现有图片策划测试继续保留，视频能力是受控扩展，不是删除图片链路。

## 6. 完成定义

本项目不能以“164 个视频都生成了图片”作为完成标准。

完成必须同时满足：

- 每条在范围内的视频有明确 profile 状态；
- 有效档案通过来源和策略修订校验；
- 代表帧可通过 Agent 接口读取；
- 下游通过 Asset ID 提取任务素材；
- raw 路径和 raw 浏览被拒绝；
- 真实片段可进入分镜和组装；
- 测试和产品事实边界有效；
- 每次正式写入后 Agent 接口刷新和验证成功；
- 旧单点帧缓存不再影响进度。
