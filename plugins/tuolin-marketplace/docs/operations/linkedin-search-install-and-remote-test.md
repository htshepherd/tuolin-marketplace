# LinkedIn 搜索 Skill 安装与远程真实业务测试

适用版本：Tuolin Marketplace `1.52.1`。

## 1. 测试边界

开发电脑没有老板电脑上的知识库不影响代码级自动测试。正式产品解析、真实候选质量和浏览器交互必须在老板电脑完成，因为那里才有：

- 已刷新并验证的 `generated/agent-interface/`；
- 老板本人正在使用的 Chrome profile；
- 已登录的 LinkedIn 账号；
- 用户对只读搜索和最终外部发送的现场确认。

不复制知识库、密码、Cookie、OTP 或浏览器会话到开发电脑。

## 2. 安装

### 从 GitHub marketplace 安装

在老板电脑的 PowerShell 中：

```powershell
codex plugin marketplace add htshepherd/tuolin-marketplace --ref main
codex plugin add tuolin-marketplace@tuolin-marketplace
codex plugin add chrome@openai-bundled
codex plugin list
```

### 从本地安装包安装

解压 `tuolin-marketplace-1.52.1.zip`，假设目录为 `C:\Tuolin\tuolin-marketplace-1.52.1`：

```powershell
codex plugin marketplace add C:\Tuolin\tuolin-marketplace-1.52.1
codex plugin add tuolin-marketplace@tuolin-marketplace
codex plugin add chrome@openai-bundled
codex plugin list
```

安装或升级后新开一个 Codex 会话。若界面版本、`codex plugin list` 与 `1.52.1` 不一致，停止测试并先解决版本冲突。

## 3. 自动安装预检

用户只需在 Codex 中说：

```text
请检查 tuolin-linkedin-search 是否可以在当前知识项目中开始真实测试；只检查，不打开 LinkedIn，不改知识库。
```

Codex 应在内部执行安装预检。必须同时满足：

- 插件版本是 `1.52.1`；
- LinkedIn Search Skill 和运行时文件完整；
- `generated/agent-interface/manifest.json` 与 `manifest_summary.json` revision 一致；
- Agent 接口没有校验错误；
- `generated/agent-interface/cards/` 存在。

如果知识接口缺失或过期，使用 `$tuolin-kb` 刷新并验证。刷新失败时不得继续让 LinkedIn Skill 读取历史接口。

## 4. 只读业务验收

先发出：

```text
$tuolin-linkedin-search 请基于正式产品知识，通过 LinkedIn 贴文搜索潜在客户。先逐题访谈，完成候选批次审核，但不要发送连接邀请。
```

按以下顺序验收：

1. Skill 只追问当前 LinkedIn Posts UI 真正能执行的业务条件，不询问无法用于贴文搜索的地区条件。
2. 用户确认关键词、排序、发布日期、是否留言、固定间隔和最多人数。
3. 用户明确授权后，Codex 通过官方 Chrome 插件读取已登录账号的可见姓名和 profile URL。
4. Skill 按确认顺序搜索 Posts，不切到 People，不自动扩词或放宽条件。
5. 每条候选卡在 Codex 中显示来源关键词、贴文正文和 URL、相关理由、作者及主页、公司及主页、联系人姓名/职位/profile 和选择理由。
6. 用户可批量删除候选；删除后不自动找补。
7. 候选批次确认后不可增加或替换候选。

## 5. 一条真实邀请验收

只读链路确认无误后，再明确说：

```text
请为当前封闭批次生成最终发送授权简报；本次真实验收只保留 1 名候选，先不要点击发送。
```

最终简报必须显示绑定账号、精确候选、数量、固定留言或无留言、固定间隔、请求上限、有效上限和滚动容量。用户确认该简报后：

1. Codex 先重新读取账号、候选 profile、实时连接状态、标准 Connect 和 Add a note 可用性。
2. 运行时返回一次性 dispatch attempt 后，才允许执行一次 Connect。
3. 点击后立即读取可见结果；只有 LinkedIn 明确显示邀请已发出才记录成功。
4. 成功事件必须包含账号、候选、公司、源贴文、封闭批次摘要、时间和结果。
5. 结果不明确时停止，不重复点击；CAPTCHA、限制提示、安全检查或退出登录时停止整个批次。

## 6. 去重和恢复验收

- 同一账号下，已保留、待处理、已发送、已连接或状态不明确的联系人不得再次进入候选卡。
- 同一公司已被保留或联系时，不得换另一个员工重复出现。
- 同一来源贴文不得通过 URL 查询参数或尾斜杠差异重复进入。
- 普通中断恢复前必须重新核对最后动作，打印剩余候选、留言、间隔和容量，并重新获得授权。
- 平台级停止不得原地恢复；只能创建独立 restart 任务，重新绑定同一账号、审核原有剩余候选并重新授权。不得重新搜索或找补。

## 7. 截图证据

默认不保存浏览器截图。只有用户明确要求、交互状态有争议或出现平台级停止时，才可保存截图并绑定原因和候选。保存后仍需人工检查是否包含不必要的会话或个人数据。

## 8. 通过标准

自动测试通过不等于真实业务验收通过。1.52.1 的完整通过条件是：

- 安装预检通过；
- 只读搜索和候选卡验收通过；
- 跨任务去重验证通过；
- 一条真实邀请在“预检—点击—可见结果—账本”链路中成功；
- 无账号切换、无未授权发送、无重复点击、无静默恢复。
