# PRD：将视频创作 Agent 升级为证据驱动的创意需求追问工作流

> 实现状态（2026-07-13）：本地首期实现与自动化验证已完成。按用户要求不创建 GitHub Issue、不安装或发布插件、不执行真实付费生成。真实工业品访谈质量和实际 Dreamina 多图能力保留为 HITL 验收。

## Problem Statement

当前 Tuolin 视频创作 Agent 的追问更接近固定字段收集，无法像高质量需求分析技能一样沿着依赖关系持续推理、质疑模糊答案并收敛真正影响视频效果的决策。它容易过早进入策划、分镜或 Prompt 阶段，也容易把“画面炫技”误当成创意方向，却没有先回答目标观众为什么会看、为什么会继续看、看完应该记住什么和采取什么行动。

对工业品短视频而言，这会直接降低成片价值：视频即使技术上生成成功，也可能与采购、工程、维护等真实受众的决策场景脱节，无法利用当前 YouTube Shorts 中已经验证的传播机制，或超出正式知识卡和官方素材能够支持的事实与画面边界。

实施前的运行时还存在与目标流程不一致的问题，包括固定六问、同时支持 TikTok、固定镜头时长和角色、每镜头单图、分镜阶段提前生成 Prompt、缺少标准 SRT 合同、字幕可能从画面描述回退、把状态查询暴露为用户步骤，以及要求用户通过文件而非 Codex 对话完成关键确认。这些问题使 Skill 中描述的创作方法无法可靠地落到自然语言工作流和状态门禁上。

## Solution

将 **Creative Discovery Core（创意需求追问核心）** 建设为视频 Agent 的首要质量能力。Agent 在策划前必须通过知识库 Agent 读取接口获得当前产品的正式知识卡和官方图片，结合目标受众、业务场景、公开 YouTube 趋势证据和实际素材可行性，动态决定下一项最有价值的问题。每次只推进一个依赖决策，给出一个有理由、有证据的建议，并询问用户是否确认；用户的普通确认只作用于当前决策。

追问不采用固定问题脚本或预设创意方向菜单，而以 **Decision Sufficiency（决策充分性）** 为完成标准。只有当产品知识来源、YouTube Shorts 格式、语言与时长、可行动受众、受众问题场景、观看动机、观众兴趣方向、趋势机制、核心记忆、期望行动、优先事实、人的关联角度、素材可行性、风险和 AI 模拟边界均已得到证据支持或用户确认后，才允许把对话决策转换为正式视频策划。

整个用户流程统一为：读取正式产品知识与图片 → 动态追问 → 公开 YouTube 趋势扫描与素材检查 → 在 Codex 中确认策划 → 动态生成并在 Codex 中共同确认可视化分镜与标准 SRT → 内部生成 Prompt → 在 Codex 中确认即梦任务和额度 → 显式确认真实提交 → 操作者在即梦网页端监测 → 操作者声明全部完成后一次性下载并校验 → 合并视频。Markdown 和 JSON 仅用于持久化、审计与恢复，不作为用户确认界面。

## User Stories

1. As a Tuolin video operator, I want to start a new video task with a natural-language business goal, so that I do not need to know internal scripts or data structures.
2. As a Tuolin video operator, I want every new task to receive an isolated run, so that artifacts and state from different videos cannot be mixed.
3. As a Tuolin video operator, I want the Agent to read the current product’s formal knowledge card through the knowledge Agent interface before interviewing me, so that the conversation is grounded in approved facts.
4. As a Tuolin video operator, I want the Agent to read only official product images associated with that knowledge context, so that unrelated or stale assets are not introduced.
5. As a knowledge owner, I want video creation to stop when the Agent read interface is missing or stale, so that downstream work cannot silently consume old knowledge.
6. As a product owner, I want the video Agent to avoid inventing product names, certifications, parameters, applications, or claims, so that external content remains defensible.
7. As a Tuolin video operator, I want the Agent to infer already-known requirements from my initial request, so that I am only asked about unresolved decisions.
8. As a Tuolin video operator, I want the Agent to ask one business question at a time, so that I can make each decision clearly without handling a questionnaire.
9. As a Tuolin video operator, I want each question to include exactly one recommended answer and the reason for it, so that I can evaluate a concrete proposal rather than choose from vague categories.
10. As a Tuolin video operator, I want to confirm or correct the current recommendation in ordinary language, so that I do not need to learn special commands such as “按推荐”.
11. As a Tuolin video operator, I want a confirmation to apply only to the current decision, so that it cannot silently authorize later creative or paid actions.
12. As a Tuolin video operator, I want the Agent to challenge vague audiences such as “industrial customers,” so that the plan resolves a group with a concrete decision or use situation.
13. As a Tuolin video operator, I want the Agent to identify the audience’s actual problem or decision scenario, so that the video starts from something the viewer already cares about.
14. As a Tuolin video operator, I want the Agent to explain why the target viewer would start and continue watching, so that spectacle is not mistaken for useful creative strategy.
15. As a Tuolin video operator, I want the Agent to challenge unsupported or low-value creative ideas, so that the final direction serves product understanding or a business outcome.
16. As a Tuolin video operator, I want the Agent to evaluate a concrete human situation involving operators, maintainers, engineers, or buyers, so that industrial content can gain human relevance when appropriate.
17. As a Tuolin video operator, I want the Agent to avoid forcing a lifestyle angle when it does not fit the product and audience, so that human relevance remains credible.
18. As a Tuolin video operator, I want every run to target YouTube Shorts only in the current release, so that platform assumptions and output contracts are unambiguous.
19. As a Tuolin video operator, I want trend research to use the target audience’s language and region, so that the evidence reflects the intended market instead of the operator’s language.
20. As a Tuolin video operator, I want the Agent to scan current public YouTube examples after understanding the audience and problem, so that trend research is relevant rather than generic.
21. As a Tuolin video operator, I want the Agent to prefer comparable industrial examples, then adjacent manufacturing or engineering examples, and only then broader transferable mechanisms, so that popularity is adapted rather than copied blindly.
22. As a Tuolin video operator, I want trend evidence to identify the mechanism that made examples effective, so that the plan can translate hooks, tension, proof, transformation, or pacing into the product context.
23. As a Tuolin video operator, I want the Agent to show a compact trend evidence brief with source links and scan date, so that I can judge the basis of its recommendation without reading a research report.
24. As a Tuolin video operator, I want the Agent to state when current public evidence is unavailable or weak, so that an inference is not presented as verified trend data.
25. As a Tuolin video operator, I want the Agent to exclude popular techniques that conflict with audience expectations, product facts, or claim safety, so that trend adaptation does not create misleading content.
26. As a Tuolin video operator, I want the Agent to open and inspect candidate images before finalizing the viewer-interest direction, so that the recommended concept is visually achievable.
27. As a Tuolin video operator, I want each candidate image checked for subject, clarity, composition, vertical crop, and near-duplication, so that weak or redundant assets do not reach the plan.
28. As a Tuolin video operator, I want the Agent to block plan confirmation when distinct usable images cannot support the requested duration, so that the storyboard is not based on hidden repetition.
29. As a Tuolin video operator, I want to shorten the duration or explicitly approve deliberate repetition when material capacity is insufficient, so that the trade-off remains under human control.
30. As a Tuolin video operator, I want the interview to end based on decision sufficiency rather than a fixed question count, so that simple tasks stay efficient and complex tasks receive enough reasoning.
31. As a Tuolin video operator, I want the completed interview to record facts, evidence, user decisions, risks, exclusions, and unresolved blockers, so that later stages consume one coherent Confirmed Video Brief.
32. As a Tuolin video operator, I want the Agent to convert the confirmed conversation decisions into a formal plan automatically, so that I do not repeat the same requirements.
33. As a Tuolin video operator, I want the plan summary printed directly in Codex, so that I do not need to open Markdown or JSON files to approve it.
34. As a Tuolin video operator, I want the plan confirmation view to show the audience problem, interest direction, trend evidence, narrative, product facts, risks, duration, and three to six representative images, so that the core strategy is reviewable in one place.
35. As a Tuolin video operator, I want natural-language plan revisions to change the actual allowed plan fields before redisplay, so that logged comments cannot be mistaken for completed edits.
36. As a product owner, I want plan revisions to preserve product identity, knowledge boundaries, source assets, format, and confirmation gates, so that creative editing cannot bypass safety controls.
37. As a Tuolin video operator, I want ordinary “确认” to approve only the currently displayed plan, so that later storyboard and paid-generation gates still require separate consent.
38. As a Tuolin video operator, I want the Agent to design shot count, timing, pacing, and sequence dynamically from the confirmed plan, so that videos are not forced into fixed five-second shot roles.
39. As a Tuolin video operator, I want every storyboard shot to show exact timing, audience-facing purpose, visible action, continuity intent, risk notes, and all ordered reference images, so that the proposed execution is concrete.
40. As a Tuolin video operator, I want one continuous shot to support multiple ordered images when continuity can be maintained, so that image use is not artificially limited to one file.
41. As a Tuolin video operator, I want multi-image continuity checked for product identity, scale, environment, lighting, action, and transition, so that the generated segment does not visibly break.
42. As a Tuolin video operator, I want every referenced storyboard image opened and displayed in Codex with its role and order, so that I can review what each shot will actually use.
43. As a Tuolin video operator, I want the storyboard to make repeated image use visible, so that accidental repetition can block confirmation unless I explicitly approve it.
44. As a Tuolin video operator, I want to delete, reorder, rewrite, or replace storyboard shots in natural language before confirmation, so that creative revision remains conversational.
45. As a Tuolin video operator, I want storyboard changes to update the actual artifact and recalculated duration before redisplay, so that the review reflects executable state.
46. As a Tuolin video operator, I want a standard SRT draft generated with the storyboard, so that visual timing and future narration are designed together.
47. As a Tuolin video operator, I want every SRT cue visibly mapped to one shot or a consecutive same-meaning shot group, so that narration and visuals cannot drift apart.
48. As a Tuolin video operator, I want a visual shot to support intentional silence, so that subtitles are not mechanically forced onto every shot.
49. As a Tuolin video operator, I want SRT text to be written from audience-facing meaning and approved product facts, so that visual descriptions or provider prompts never leak into narration.
50. As a Tuolin video operator, I want the confirmed SRT to be the sole verbatim future narration transcript, so that no conflicting voiceover script exists.
51. As a Tuolin video operator, I want changes to shot purpose, timing, order, or deletion to regenerate affected SRT cues and reset confirmation, so that the locked narration stays synchronized.
52. As a Tuolin video operator, I want the complete storyboard and SRT core content printed together in Codex for one confirmation, so that shot-level creative execution has one clear contract.
53. As a Tuolin video operator, I want Dreamina Prompt artifacts created only after storyboard-plus-SRT confirmation, so that internal production text cannot get ahead of approved creative execution.
54. As a Tuolin video operator, I want Prompt artifacts to be internal and auditable without requiring a separate wording confirmation, so that I review business meaning rather than provider syntax.
55. As a Tuolin video operator, I want each Dreamina task mapped to a confirmed storyboard shot and its ordered references, so that paid work is traceable to approved content.
56. As a Tuolin video operator, I want provider capability checks before task confirmation, so that unsupported multi-image behavior is discovered before credits are consumed.
57. As a Tuolin video operator, I want unsupported multi-image shots to trigger a proposed consecutive-shot revision and renewed storyboard-plus-SRT confirmation, so that references are never dropped or split silently.
58. As a Tuolin video operator, I want the Dreamina confirmation view printed in Codex with every task, references, duration, estimated credits, provider adaptations, and blockers, so that paid intent is fully visible.
59. As a Tuolin video operator, I want generic confirmation to be insufficient for paid generation, so that credits cannot be consumed accidentally.
60. As a Tuolin video operator, I want paid-generation approval to explicitly name Dreamina generation, so that the authorization is unmistakable.
61. As a Tuolin video operator, I want real submission to remain a separate explicit action after task-plan approval, so that reviewing a plan does not submit jobs.
62. As a Tuolin video operator, I want the existing reliable CLI submission, resumable handoff, and real task-ID recording preserved, so that creative improvements do not destabilize execution.
63. As a Tuolin video operator, I want to monitor generation completion in the Dreamina web interface, so that the workflow does not expose a redundant automated status-query step.
64. As a Tuolin video operator, I want to tell the Agent when all tasks are complete and trigger one download action, so that result retrieval is simple and bounded.
65. As a Tuolin video operator, I want the one-shot download to use recorded real task IDs and validate expected file count and readability, so that missing or mock results cannot reach assembly.
66. As a Tuolin video operator, I want dry-run, blocked, incomplete, or malformed results labeled loudly, so that I cannot mistake them for finished video assets.
67. As a Tuolin video operator, I want accepted downloaded shots merged in storyboard order, so that the final base video follows the confirmed execution contract.
68. As a Tuolin video operator, I want rejected generated results recorded and the current run stopped, so that the system does not silently rewind or resubmit paid work.
69. As a Tuolin video operator, I want an unsatisfactory result to start a new video task in this release, so that post-generation improvement remains an explicit future capability.
70. As a Tuolin video operator, I want every meaningful stage to report current state, produced artifacts, verification results, blockers, and the next natural-language action, so that long workflows remain recoverable.
71. As a Tuolin video operator, I want a resumed run to read its persisted workflow state before acting, so that remembered state cannot override actual state.
72. As a plugin user, I want installed Skill behavior to match repository runtime behavior, so that development and installed use do not diverge.
73. As a maintainer, I want the repository Skill and plugin mirror validated together, so that releases cannot ship stale instructions or code copies.
74. As a maintainer, I want existing runs to fail clearly or migrate safely when old interview, platform, storyboard, or subtitle fields are encountered, so that schema evolution is controlled.
75. As a maintainer, I want the core interview reasoning contract testable independently from Dreamina and filesystem execution, so that the most important quality capability can evolve without running the entire pipeline.

## Implementation Decisions

- `tuolin-video-workflow` remains the sole user-facing owner of the complete Video Creation Context. External grilling or video-generation skills may inspire methods but do not become alternate user workflows or business taxonomies.
- The Skill is rewritten around Creative Discovery Core: investigate evidence first, follow dependent decisions, ask one business question at a time, make exactly one reasoned recommendation, challenge weak answers, and stop only at Decision Sufficiency.
- The Creative Discovery Core becomes a deep, independently testable module. Its stable interface accepts current evidence, confirmed decisions, conversation history, and blockers; it returns the next decision proposal or a decision-sufficiency result. It does not own file layout, provider commands, or presentation formatting.
- A decision ledger replaces the fixed six-question structure. It records confirmed decisions, source type, supporting evidence, correction history, pending decision, unresolved completion dimensions, and blockers.
- The completion contract is semantic rather than scripted. It covers product and formal source; language, YouTube Shorts and target duration; Actionable Video Audience; Audience Problem Scenario; viewing motivation; Viewer-Interest Direction; Short-Video Trend Mechanism and evidence; intended takeaway and action; priority facts; Human-Relevance Angle when applicable; material-supported visual direction; exclusions and claim risks; and approved AI-simulation scope.
- Confirmation is phase-scoped. Ordinary natural-language confirmation applies only to the currently displayed interview decision, plan, or storyboard-plus-SRT contract. There is no special “按推荐” requirement and no implicit bulk acceptance of remaining recommendations.
- The knowledge context adapter must read the published Agent interface and verify product identity, knowledge version, formal product card, and associated official images before creative discovery can complete.
- Trend evidence acquisition is a separate evidence module. In this release it uses public YouTube sources only, searches in the target audience’s language and region, records links and scan date, applies the relevance ladder, and clearly distinguishes verified signals from inference or degraded evidence.
- First-party YouTube channel analytics are not modeled or simulated until real data is available.
- Material feasibility is a deep module that accepts candidate images and returns per-image inspection findings, near-duplicate groups, vertical-crop feasibility, usable distinct capacity, continuity observations, and confirmation blockers.
- The final Viewer-Interest Direction cannot be confirmed before the mandatory public trend scan and Pre-Direction Material Feasibility Check are complete.
- A Confirmed Video Brief is the sole planning input. The plan generator projects confirmed decisions into audience problem, interest direction, narrative, evidence, facts, risks, target duration, and representative images without reopening resolved interview choices.
- The conversation presenter is responsible for rendering all confirmation views directly in Codex. Persistence files remain for audit, recovery, automation, and diagnostics only.
- The storyboard engine dynamically owns shot count, duration, purpose, visible action, pacing, sequence, ordered image references, continuity intent, subtitle mapping, and risk notes. Fixed five-second shots and fixed shot-role sequences are removed.
- A shot exposes an ordered Shot Reference Sequence rather than one selected image. A legacy single-image value may be read only through an explicit compatibility layer, not treated as the new contract.
- The Visual Storyboard and Confirmed Storyboard SRT form one shot-level creative execution contract and are confirmed together.
- Standard SRT is generated as a storyboard draft and locked on confirmation. Cue text is the sole verbatim future narration transcript. Visual descriptions and Dreamina prompts are prohibited fallback sources.
- SRT cues may map to one shot or consecutive same-meaning shots; a shot may deliberately contain no cue. Every non-silent cue must pass semantic alignment checks against shot purpose, visible action, and approved facts.
- Any revision to shot purpose, timing, order, or deletion regenerates affected SRT and invalidates the previous storyboard-plus-SRT confirmation.
- Dreamina Prompt artifacts are generated only after storyboard-plus-SRT confirmation. Machine-readable Prompt data drives task creation; human-readable Prompt output exists only for audit and debugging.
- Dreamina capability adaptation is explicit. When a mode supports ordered multi-image references, one continuous storyboard shot maps to one task. When it does not, the workflow blocks and proposes a consecutive-shot revision for user reconfirmation.
- The paid-generation confirmation view includes every task, storyboard mapping, ordered references, duration, estimated credits, provider adaptations, and blockers. Paid approval requires explicit Dreamina wording, and actual submission remains a second explicit action.
- Existing proven Dreamina submission, resumable manual handoff, and real task-ID recording are preserved behind a provider adapter.
- Automated status polling is removed from the user-visible workflow. After the operator confirms completion in the Dreamina web interface, a One-Shot Dreamina Download retrieves results by recorded IDs exactly once and validates completeness and readability before assembly.
- The assembly stage consumes validated shot files in confirmed storyboard order and retains the locked SRT as the subtitle/narration handoff artifact; it does not synthesize voiceover or burn subtitles.
- Runtime state transitions enforce every creative, factual, material, paid-action, and result-integrity gate. Natural-language revisions must mutate allowed artifact fields before being reported as complete.
- Repository Skill content, runtime behavior, command wrappers, examples, plugin mirror, and release validation are updated as one change so installed behavior cannot lag behind source behavior.
- Legacy run compatibility is explicit: old TikTok requests, fixed interview fields, singular image fields, early Prompt artifacts, Markdown subtitle files, or status-query states must either be safely normalized or fail with a clear migration message. They must never be silently interpreted as the new confirmed contract.

## Testing Decisions

- Good tests assert externally observable behavior: user-visible prompts, accepted natural-language replies, persisted contracts, state transitions, generated SRT, task plans, blockers, and assembly eligibility. Tests must not lock internal helper names or incidental JSON ordering.
- Creative Discovery Core receives isolated contract tests for evidence-aware next-decision selection, one-question behavior, exactly one recommendation, current-decision confirmation, correction handling, challenges to vague answers, and Decision Sufficiency.
- Knowledge context tests verify that formal product data and official images are required, stale or mismatched interfaces block downstream use, and unsupported facts cannot enter the brief.
- Trend evidence tests verify YouTube-only scope, target-language/region inputs, relevance-ladder ordering, links and dates in the evidence brief, excluded mechanisms, and explicit degraded-evidence behavior.
- Material feasibility tests verify subject/clarity/composition/vertical-crop findings, near-duplicate handling, distinct-capacity blocking, deliberate-repetition approval, and continuity checks for ordered references.
- Confirmation-state tests verify that ordinary confirmation is phase-scoped, corrections reset only affected decisions, later gates remain closed, and generic confirmation cannot authorize paid generation or real submission.
- Plan tests verify that only a decision-sufficient Confirmed Video Brief can generate a plan, required core content and representative images appear in the Codex view, and semantic revisions change the persisted plan while protected fields remain immutable.
- Storyboard tests verify dynamic timing and shot count, ordered multi-image references, visible reference roles, repeated-image blockers, natural-language deletion/reordering/replacement, recalculated duration, and confirmation invalidation.
- SRT tests verify valid standard formatting, exact cue time ranges, semantic shot mapping, intentional silence, grouped consecutive shots, sole-transcript behavior, regeneration after relevant revisions, and prohibition of visual-description or Prompt fallback text.
- Prompt and Dreamina task tests verify that no Prompt exists before storyboard-plus-SRT confirmation, generated tasks trace to confirmed shots and references, capability mismatches block rather than discard or silently split references, and the Codex paid view exposes credits and adaptations.
- Paid-action tests verify the explicit Dreamina approval phrase, separate real-submission authorization, dry-run labeling, task-ID persistence, and preservation of resumable handoff behavior.
- Result tests verify that no user-visible status-query step remains, operator-declared completion triggers one bounded download, all expected task IDs and files are validated, mock or unreadable files block assembly, and successful assembly follows storyboard order.
- Compatibility tests cover legacy run fields and require either safe normalization with unchanged meaning or a clear migration failure.
- Mirror and packaging tests compare source and plugin behavior, validate both Skill packages, and ensure installed natural-language routing exposes the same YouTube-only workflow.
- End-to-end workflow tests follow the existing video-creation test style: create an isolated temporary run, drive it only through public natural-language or application interfaces, inspect user-visible results and durable artifacts, and avoid real paid submissions.
- Existing video creation integration tests provide the primary prior art for stateful run setup, artifact assertions, confirmation gates, dry-run Dreamina behavior, and assembly checks. New tests replace obsolete fixed-question, TikTok, single-image, Markdown-subtitle, and status-query expectations.

## Out of Scope

- TikTok planning, trend research, safe-area rules, publishing, or runtime support.
- First-party YouTube channel analytics until real account data exists and a separate data contract is approved.
- Automated continuous Dreamina status polling or a user-visible “查询即梦结果” stage.
- Post-generation shot improvement, retry, silent storyboard rewind, or automatic resubmission. Rejected results end the current run and require a new video task.
- TTS generation, voice cloning, voiceover audio synthesis, background music, logo composition, subtitle burn-in, Jianying/CapCut automation, and final editorial polish.
- Automatic publishing to YouTube, publishing titles, descriptions, hashtags, or LinkedIn reuse.
- New product-fact authoring or raw knowledge-base organization inside the video Agent.
- Use of knowledge-base video files as planning or Dreamina references in the current release.
- Importing fixed entertainment, cinematic, viral, lifestyle, or industrial creative-direction taxonomies from external skills.
- Guaranteeing virality. Trend evidence informs a defensible creative mechanism but does not promise reach or conversion.
- Provider features that cannot be verified against the actual selected Dreamina mode and local execution contract.

## Further Notes

- This PRD operationalizes the domain decisions already recorded for Creative Discovery Core, Viewer-Interest Direction, Pre-Plan Trend Scan, Trend Evidence Brief, Pre-Direction Material Feasibility Check, Confirmed Video Brief, Visual Storyboard, Confirmed Storyboard SRT, Shot-Subtitle Alignment, Shot Reference Sequence, Dreamina Prompt Artifact, Phase-Scoped Confirmation, In-Conversation Confirmation View, and One-Shot Dreamina Download.
- The intended quality bar is analogous to a strong requirements-analysis grilling skill, but the reasoning target is video effectiveness: who watches, in what situation, for what reason, what evidence earns attention, what the available images can actually show, and what business action the video should support.
- The deepest module should be the Creative Discovery Core because it encapsulates the most valuable reasoning behind a small contract and can evolve independently from persistence, Codex rendering, and Dreamina execution.
- Source and plugin copies were synchronized and validated together. Legacy query/retry code remains internal only for historical compatibility; the current Skill, natural-language route, and migration gate do not expose it as a supported workflow.
