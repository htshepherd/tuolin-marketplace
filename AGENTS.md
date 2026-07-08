# AGENTS.md - Tuolinagent Natural-Language Usage Rules

These rules apply to users operating Tuolinagent after installation. Tuolinagent is used primarily through natural-language requests in Codex. Users should not need to edit code, run internal scripts manually, or understand implementation details unless an agent explicitly hands off a safe command for local execution.

这些规则适用于安装后通过 Codex 使用 Tuolinagent 的用户。Tuolinagent 主要通过自然语言操作。除非 agent 明确交接一条安全的本地命令，否则用户不需要修改代码、手动运行内部脚本，也不需要理解实现细节。

## 1. Say the Goal Clearly

Use natural language to state the business goal, product, audience, platform, language, and expected output. If the request is incomplete, the agent should ask for the missing decision instead of guessing.

用自然语言说清业务目标、产品、受众、平台、语言版本和期望产物。如果信息不完整，agent 应追问关键决策，而不是替用户猜。

Good examples:

- `整理石英纤维隔热带的产品知识卡。`
- `做一个60秒英文版石英纤维隔热带视频，面向欧美工业采购商，用于 YouTube Shorts 和 TikTok。`
- `生成下周 LinkedIn 发帖计划，产品是石英纤维隔热带。`

## 2. Prefer Simple Instructions

Start with the simplest request that expresses the desired result. Do not ask the agent to run internal scripts unless the agent says a manual command is required.

优先用简单指令表达结果。不要主动要求 agent 跑内部脚本，除非 agent 明确说明某个手动命令是必要的。

Preferred:

`请基于这个运行目录继续生成分镜。`

Avoid:

`运行某某 Python 文件并传一堆参数。`

## 3. Keep Agent Boundaries Clear

Tuolinagent has multiple agents in one project. Use the right agent for the right task:

Tuolinagent 是一个项目多个 agent。不同任务应使用对应 agent：

- `$tuolin-kb`：整理、检查、更新本地知识库。
- `$tuolin-linkedin`：生成和管理 LinkedIn 发帖计划。
- `$tuolin-linkedin-image-style`：生成单日 LinkedIn 配图。
- `$tuolin-video-workflow`：视频创作策划、创意方向、可视化分镜、即梦任务计划和交接文件。
- `$tuolin-video-publisher`：发布本地已确认的视频和相关文案。

不要让一个 agent 承担不属于它的任务。例如：不要让视频 agent 直接整理原始知识库；应先用知识库 agent 整理知识，再让视频 agent 消费已整理结果。

## 4. Confirm Before Moving Forward

For multi-step workflows, confirm each key stage before the agent continues. The user should explicitly confirm decisions that affect output direction, external publication, credit consumption, or final delivery.

多步骤流程必须逐步确认。凡是影响创作方向、外部发布、额度消耗或最终交付的节点，都需要用户明确确认。

Typical video confirmations:

1. 确认语言版本：中文版或英文版。
2. 确认平台：YouTube Shorts、TikTok 等。
3. 确认视频创意方向。
4. 确认策划。
5. 确认分镜。
6. 确认即梦任务计划。
7. 确认是否真实提交即梦。
8. 确认镜头结果。
9. 合并镜头视频并生成剪辑字幕稿。

## 5. Use AI For Creative And Judgment Work

Use Tuolinagent for planning, writing, classification, summarization, material matching, prompt drafting, and review. Do not ask it to invent facts that are not in the knowledge base.

Tuolinagent 适合做策划、写作、分类、总结、素材匹配、Prompt 起草和审查。不要让它编造知识库中不存在的事实。

Allowed:

- `根据知识卡生成英文视频策划和分镜。`
- `帮我判断这些素材适合哪些视频镜头。`
- `检查这个视频脚本有没有夸大宣传风险。`

Not allowed:

- `没有证据也写成通过认证。`
- `把不确定参数写成确定参数。`
- `随便起一个英文产品名。`

## 6. Control Context And Token Usage

Keep each conversation focused. Long PRDs, JSON files, PowerShell logs, generated reports, and repeated full-file outputs can quickly exhaust Codex usage and context tokens.

保持每个会话聚焦。PRD、JSON、PowerShell 日志、生成报告和反复输出完整文件，会快速消耗 Codex 用量和上下文 token。

User rules:

- Do not paste large JSON, logs, or full generated reports unless the agent asks for them.
- When troubleshooting, paste only the smallest relevant error block.
- For long workflows, start a new conversation after a major milestone.
- When restarting, provide only the run directory, current stage, and last blocker.
- Ask the agent to read only targeted files, not scan the whole project.

用户规则：

- 除非 agent 要求，不要粘贴大段 JSON、日志或完整报告。
- 排查问题时，只粘贴最小相关错误片段。
- 长流程到达关键节点后，建议新开会话。
- 重开会话时，只提供运行目录、当前阶段和最后一个阻塞点。
- 要求 agent 只读取目标文件，不要扫描整个项目。

Good restart prompt:

`继续处理这个视频运行目录：E:/TuolinKnowledge/generated/reports/video-creation/xxx。当前已确认分镜，需要重新规划即梦任务，不改策划和分镜。`

## 7. Do Not Mix Conflicting States

If the agent reports conflicting paths, versions, product IDs, or workflow states, stop and resolve the conflict before continuing.

如果 agent 发现路径、版本、产品 ID 或流程状态冲突，应先解决冲突，再继续。

Examples:

- 插件界面显示旧版本，但安装目录已是新版本。
- 产品卡 ID 与视频上下文 ID 不一致。
- 即梦任务文件来自旧版本，但提交脚本来自新版本。
- dry-run 结果被误认为真实即梦结果。

## 8. Read The Current Run State Before Continuing

When continuing an existing task, tell the agent the exact run directory and ask it to inspect current state first. Do not assume the workflow is at the stage you remember.

继续已有任务时，先提供准确运行目录，并要求 agent 读取当前状态。不要假设流程还停在你记忆中的阶段。

Example:

`请先读取 E:/TuolinKnowledge/generated/reports/video-creation/xxx 的 workflow_state.json，告诉我当前阶段和下一步，不要改文件。`

## 9. Protect Business Intent

The user should confirm whether the output is for internal review, external publication, customer communication, LinkedIn, YouTube Shorts, TikTok, or sales material. The agent must keep the business intent visible in the output.

用户应明确产物用于内部复核、对外发布、客户沟通、LinkedIn、YouTube Shorts、TikTok 还是销售资料。agent 必须在输出中保持业务目的清晰。

For video creation, the agent must not skip:

- 目标受众；
- 平台；
- 语言版本；
- 视频创意方向；
- 产品知识来源；
- 素材使用边界；
- 是否需要人工复核。

## 10. Use Checkpoints In Long Workflows

After each meaningful stage, the agent should summarize what was produced, where files were written, what was verified, and what remains.

长流程中，每个关键阶段后，agent 应总结已产出什么、文件在哪里、验证了什么、下一步是什么。

A useful checkpoint includes:

- 当前阶段；
- 新增或更新的文件；
- 是否需要用户确认；
- 是否存在 blocked / warning；
- 下一条推荐自然语言指令。

## 11. Follow The Project’s Natural-Language Workflow

Use the project workflow instead of ad-hoc commands. The normal user-facing flow is:

优先使用项目自然语言流程，不要临时拼命令。常规使用流程是：

Knowledge base:

1. 整理或更新知识库。
2. 重建 Agent 读取接口。
3. 检查知识卡状态和复核项。

LinkedIn:

1. 生成发帖计划。
2. 确认计划。
3. 生成单日内容或配图。
4. 人工发布或后续发布 agent 处理。

Video creation:

1. 创建视频需求。
2. 选择语言版本。
3. 选择平台。
4. 选择视频创意方向。
5. 生成并确认策划。
6. 生成并确认分镜。
7. 生成即梦任务计划。
8. 人工确认真实提交。
9. 查询结果并确认镜头。
10. 合并镜头视频并生成剪辑字幕稿。

## 12. Fail Loudly And Keep Human Control

The agent must clearly say when something is blocked, mocked, dry-run, incomplete, or unsafe to publish. The user should not treat a draft, mock file, dry-run task, or blocked plan as a completed deliverable.

agent 必须明确说明 blocked、mock、dry-run、未完成或不适合发布的状态。用户不能把草稿、占位文件、dry-run 任务或 blocked 计划当成最终交付。

Never silently accept:

- dry-run Dreamina results as real generated videos;
- missing material paths;
- guessed product names;
- unreviewed claims as externally approved claims;
- malformed generated JSON;
- plugin version mismatches.

If real Dreamina submission or other paid/external action is needed, the agent must require explicit human confirmation or provide a manual handoff file for the user to execute locally.
