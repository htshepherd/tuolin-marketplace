# `$tuolin-video-planner` 纵向开发切片

本文件把 `docs/prd/tuolin-video-planner.md` 转换为可独立领取、可单独验证的 tracer-bullet 切片。每个切片必须交付一条端到端可观察路径；不得只提交孤立 schema、内部 helper 或未接入用户流程的脚手架。

## 状态

- [x] Slice 01 — 专属知识接口最小闭环
- [x] Slice 02 — 图片版最小策划闭环
- [x] Slice 03 — 知识写入后自动刷新事务
- [x] Slice 04 — 无趋势动态访谈与策划推断
- [x] Slice 05 — 平台、语言与时长范围
- [x] Slice 06 — 正式图片检查与风险门禁
- [x] Slice 07 — 视频资产目录优先检索
- [x] Slice 08 — 授权关键片段预览
- [ ] Slice 09 — 真实视频片段策划 Tracer
- [x] Slice 10 — 受约束的 AI 模拟镜头
- [x] Slice 11 — 镜头时间、旁白与自然语言修订
- [x] Slice 12 — SRT 与交付后版本化修订
- [ ] Slice 13 — 固定接口版本与最终复核
- [ ] Slice 14 — 显式调用、插件打包与全量回归

### 2026-07-28 实现检查点

- Slice 01–08、10–12 的 AFK 实现与自动测试已完成。
- Slice 09 的受控授权、静音预览、同时间范围引用和真实视频镜头数据路径已实现并通过 fixture 测试；按本文件完成规则，仍需使用一项真实企业视频资产在 Codex 中展示并获得人工确认。
- Slice 13 的固定 revision、引用指纹、无关刷新放行、实质变化阻止逻辑已实现并通过自动测试，但保持未勾选，等待 Slice 09 HITL 解除依赖。
- Slice 14 的显式调用、`allow_implicit_invocation: false`、源/插件镜像、skill 校验和全量回归已完成，但保持未勾选，等待 Slice 09/13 完成后进行最终交付验收。
- 2026-07-28 二次复审修复：专属接口改为隔离快照构建；失败修订不再删除当前 SRT；最终确认复核事实证据、图片/预览字节、AI 产品参考和视频源；`按推荐` 与全部剩余建议授权按约定执行；显式调用下沉到运行接口；预览改为 540×960、全失败审计并绑定内容指纹；确认视图显示来源、预览、风险和 simulated 标识。
- 验证：`python3 -m unittest discover -s tests` — 400 tests passed；源 skill 与插件 skill 均通过 `quick_validate.py`。

## Slice 01 — 专属知识接口最小闭环

- Type: AFK
- Blocked by: None
- User stories: 7–9, 13–16, 79

交付从正式知识到 `tuolin-video-planner` 专属投影再到用户可见产品列表的完整路径。接口拥有独立 manifest、revision、产品索引和卡片投影，不读取其他 Agent 的上下文。

### Acceptance criteria

- [x] 初始化项目时创建专属接口目录，但不改变 legacy 接口路径。
- [x] 重建操作从正式知识生成独立 manifest、产品目录和允许卡型投影。
- [x] 接口支持多个正式产品，不写死石英纤维隔热带。
- [x] 接口声明 `raw_access=false`、自身 revision 和 source knowledge revision。
- [x] 专属读取 API 能列出产品并拒绝读取未发布产品。
- [x] 测试证明消费者不读取 `generated/agent-interface/contexts`。

## Slice 02 — 图片版最小策划闭环

- Type: AFK
- Blocked by: Slice 01
- User stories: 1, 2, 4, 17, 18, 21, 23, 31, 53, 54, 56, 59–67, 76, 80

交付一条最小但完整的中文图片策划路径：显式调用新 skill、创建独立运行、从正式图片生成逐镜头方案和逐字旁白、一次确认后自动生成 SRT 并结束。

### Acceptance criteria

- [x] 新运行写入 `generated/reports/video-planning/`，不复用 `video-creation`。
- [x] 完整请求可跳过已知访谈项并直接产生图片版镜头草稿。
- [x] 镜头草稿包含时间、用途、动作、素材、运镜、转场、剪辑提示和逐字旁白。
- [x] 确认前不存在 SRT；确认后自动生成逐字匹配的 SRT。
- [x] 运行结束状态不包含 Prompt、即梦、下载、合并或发布阶段。
- [x] 旧 `$tuolin-video-workflow` 行为测试继续通过。

## Slice 03 — 知识写入后自动刷新事务

- Type: AFK
- Blocked by: Slice 01
- User stories: 10–14

把专属接口接入知识写入完成事务。用户组织、更新或复核知识后，不运行额外命令即可获得已验证的新投影。

### Acceptance criteria

- [x] 统一注册表声明每个已迁移接口的 builder 和 verifier。
- [x] 产品整理、复核写回和视频档案发布均触发专属接口刷新。
- [x] 本次应进入接口的卡片被逐一验证。
- [x] 任一已注册接口失败时，上游知识操作报告 incomplete。
- [x] 返回结果明确标记旧消费者仍使用 legacy shared interface。
- [x] 不迁移或改写现有 Agent 的消费逻辑。

## Slice 04 — 无趋势动态访谈与策划推断

- Type: AFK
- Blocked by: Slice 02
- User stories: 4–6, 26–34

交付新 Agent 自有的动态访谈状态机。它不包含公开趋势字段，一次只确认一个承重决策，并在事实与策划推断之间保持可审计边界。

### Acceptance criteria

- [x] 访谈字段不包含 trend evidence 或 trend mechanism。
- [x] 初始请求中已经充分的信息不会重复询问。
- [x] 任意时刻至多存在一个待确认决策。
- [x] 每问显示一个推荐、具体理由和来源类型。
- [x] 产品事实修正没有正式卡片证据时不能进入已确认 brief。
- [x] 决策充分后直接进入镜头草稿，不产生中间总体策划确认。
- [x] 未明确期望行动时不自动生成销售 CTA。

## Slice 05 — 平台、语言与时长范围

- Type: AFK
- Blocked by: Slice 02
- User stories: 17–25

扩展最小闭环，使一个运行可以声明 YouTube Shorts、TikTok 或两者，生成中文或英文单语言版本，并接受 15–90 秒任意整数时长。

### Acceptance criteria

- [x] 只接受 YouTube Shorts 和 TikTok 平台值。
- [x] 所有方案固定 9:16，不生成平台安全区字段。
- [x] 只接受 `zh` 或 `en`，一个运行只允许一个目标语言。
- [x] 英文产品名称必须来自正式接口。
- [x] 只接受 15–90 秒整数；省略时推荐 30 秒。
- [x] 镜头数和单镜时长动态派生，不使用固定五秒模板。

## Slice 06 — 正式图片检查与风险门禁

- Type: AFK
- Blocked by: Slice 01, Slice 04
- User stories: 43, 49–51, 56

把实际图片检查接入镜头选择和确认门禁。文件名、标签和路径不能替代像素判断。

### Acceptance criteria

- [x] 每张入选图片记录主体、清晰度、构图、9:16 适用性和近重复判断。
- [x] 用户确认视图显示实际预览和原始引用路径。
- [x] 路径失效、未检查或明显不匹配的图片阻止确认。
- [x] `review_before_external` 资产可显示为 blocked candidate，但不能进入最终方案。
- [x] 产品身份、隐私、权利、测试含义和声明风险阻止确认。
- [x] 素材数量不足不触发缩短或重复审批分支。

## Slice 07 — 视频资产目录优先检索

- Type: AFK
- Blocked by: Slice 01, Slice 04
- User stories: 35, 36, 39, 40

接入已处理视频资产的 catalog/detail/representative-media 三级读取前两级，证明 Agent 能先从资产找镜头，而不是读取大量源视频。

### Acceptance criteria

- [x] 专属接口拥有自己的轻量视频档案目录和详情投影。
- [x] 目录支持按产品、语义和用途能力筛选。
- [x] 目录不返回完整转录、源路径或关键片段详情。
- [x] 仅对 shortlist 加载档案详情和代表媒体。
- [x] 代表媒体绑定档案 revision 与内容指纹。
- [x] 用户可见候选显示摘要、代表画面、风险和可用能力。

## Slice 08 — 授权关键片段预览

- Type: AFK
- Blocked by: Slice 07
- User stories: 37–39

完成视频资产检索第三级：只在具体候选的授权关键片段内生成任务级检查帧或低清预览。

### Acceptance criteria

- [x] 运行授权绑定 asset ID、产品、接口 revision、档案 revision、源 revision 和关键片段范围。
- [x] 任意 raw 路径、错误产品、过期 revision、撤销资产和越界时间均被拒绝。
- [x] 一个计划用途最多生成三个候选预览。
- [x] 预览自动静音并使用低清配置。
- [x] 预览只写入当前 planning run，不成为正式知识或交付片段。
- [x] 每次成功和失败读取均写入运行审计。

## Slice 09 — 真实视频片段策划 Tracer

- Type: HITL
- Blocked by: Slice 06, Slice 08
- User stories: 41, 42, 49, 52, 53

使用一项真实视频档案完成从目录检索、代表媒体、受限预览到逐镜头方案的真实 tracer，并由人工确认展示是否足以支持后续剪辑。

### Acceptance criteria

- [x] 镜头优先选择合适真实视频片段而非重新生成。
- [x] 镜头显示准确源时间范围、asset ID、档案 revision、预览和用途。
- [x] 来源视频片段固定 `visual-only`，不保留或策划原声。
- [x] 预览与最终计划引用的是同一候选时间范围。
- [ ] 用户在 Codex 对话中能看到并理解真实片段选择。
- [ ] 人工确认一个真实样本后才标记本切片完成。

## Slice 10 — 受约束的 AI 模拟镜头

- Type: AFK
- Blocked by: Slice 04, Slice 06
- User stories: 44–48

允许在真实场景素材不适用时安排可追溯的 AI 模拟，同时保护产品身份和证据边界。

### Acceptance criteria

- [x] AI 模拟镜头必须引用正式应用场景卡。
- [x] 描绘具体产品时必须引用已检查的真实产品图片。
- [x] 缺少产品身份参考时阻止该镜头进入方案。
- [x] 每个模拟镜头在对话和文件中明确标注 simulated。
- [x] 客户案例、真实测试和性能证据表达被禁止。
- [x] AI 模拟不会创建供应商 Prompt 或生成任务。

## Slice 11 — 镜头时间、旁白与自然语言修订

- Type: AFK
- Blocked by: Slice 04, Slice 06
- User stories: 22, 54–58

使镜头草稿成为可编辑且可验证的创作合同。用户自然语言修改必须真正改变文件，并保持时间轴与旁白可执行。

### Acceptance criteria

- [x] 镜头时间连续且总时长等于运行目标。
- [x] 中文和英文旁白分别按正常语速校验。
- [x] 每镜有可读完旁白或明确 intentional silence；整份方案不能完全静默。
- [x] 删除、重排、改时长、换素材和改旁白均更新真实草稿。
- [x] 修改后重新计算时间、旁白和风险状态并展示受影响内容。
- [x] 产品、接口 revision、画幅、语言和平台等保护字段不能被语义修订绕过。

## Slice 12 — SRT 与交付后版本化修订

- Type: AFK
- Blocked by: Slice 11
- User stories: 60–63, 68–71

完成确认后的 SRT 投影与可审计修订。SRT 始终是旁白的派生产物，而不是第二份创作源。

### Acceptance criteria

- [x] Shot Plan Confirmation 同时确认镜头、素材和逐字旁白。
- [x] 确认后自动生成逐字、逐时间段一致的 SRT。
- [x] 工作流不存在独立 SRT 确认状态。
- [x] 修改 SRT 文本被转换为旁白修订并重新校验。
- [x] 已交付方案可创建新的编号修订版，旧确认版不可变。
- [x] 影响时间或旁白的修订使当前 SRT 失效，重新确认后生成新版。

## Slice 13 — 固定接口版本与最终复核

- Type: AFK
- Blocked by: Slice 03, Slice 09, Slice 10, Slice 12
- User stories: 72–75, 80

在知识持续更新的情况下保证单次运行可重现。无关更新不打断任务，引用事实或资产变化必须阻止旧方案确认。

### Acceptance criteria

- [x] 创建运行时固定专属接口 revision 和引用卡指纹。
- [x] 自动刷新不会静默切换活动运行的知识版本。
- [x] 最终确认前比较实际引用卡、视频档案和撤销状态。
- [x] 无关知识变化不阻止确认。
- [x] 引用内容实质变化或撤销时明确阻止并要求创建新运行。
- [x] blocked/stale/incomplete 状态在对话与运行文件中一致。

## Slice 14 — 显式调用、插件打包与全量回归

- Type: AFK
- Blocked by: Slice 13
- User stories: 1–3, 67, 76–80

完成可安装交付、显式触发约束和全量回归，确保新 Agent 独立可用且旧 Agent 未被改变。

### Acceptance criteria

- [x] skill 名称为 `tuolin-video-planner`，源目录和插件包内容同步。
- [x] `agents/openai.yaml` 设置 `allow_implicit_invocation: false`。
- [x] 普通“做视频”文本不路由到任一视频 Agent。
- [x] skill 验证器通过，所有内部入口由自然语言流程调用而非要求用户执行脚本。
- [x] planning run 中不存在 Prompt、Dreamina、生成结果或 assembly 文件。
- [x] 新增测试、视频与知识相关测试、完整测试套件全部通过。
- [x] 验收报告明确“新 Agent 已隔离，旧消费者仍为 legacy shared”。

## 完成规则

- 每完成一个切片，立即勾选状态并记录验证命令与结果。
- AFK 切片满足验收标准且测试通过即可进入下一项。
- Slice 09 必须展示真实资产并获得人工确认，不能用 fixture 或 dry-run 冒充 HITL 验收。
- 任一切片发现领域边界冲突时先更新 `CONTEXT.md` 或 ADR，再继续实现。
- 未完成 Slice 14 前不得报告整个 `$tuolin-video-planner` 已交付。
