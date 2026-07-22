# LinkedIn 搜索 Skill 安装与远程真实业务测试

适用版本：Tuolin Marketplace `1.53.0`。

## 1. 测试边界

`tuolin-linkedin-search` 只需要可写的 Tuolin 运行目录，不要求本地产品知识库或 `generated/agent-interface/`。开发电脑可以完成全部确定性测试；真实 LinkedIn 搜索、候选质量与一条邀请验收仍在老板电脑完成，因为那里有老板本人 Chrome profile、已登录 LinkedIn 账号和现场人工判断。

不得复制密码、Cookie、OTP、会话令牌或 Chrome profile 到开发电脑。

## 2. 安装

从 GitHub marketplace 安装：

```powershell
codex plugin marketplace add htshepherd/tuolin-marketplace --ref main
codex plugin add tuolin-marketplace@tuolin-marketplace
codex plugin add chrome@openai-bundled
codex plugin list
```

或解压 `tuolin-marketplace-1.53.0.zip` 后从本地目录安装：

```powershell
codex plugin marketplace add C:\Tuolin\tuolin-marketplace-1.53.0
codex plugin add tuolin-marketplace@tuolin-marketplace
codex plugin add chrome@openai-bundled
codex plugin list
```

安装或升级后新开 Codex 会话。若界面版本与 `codex plugin list` 不是 `1.53.0`，停止业务测试并先解决版本冲突。

## 3. 自动安装预检

用户说：

```text
请检查 tuolin-linkedin-search 是否可以开始真实测试；只检查，不打开 LinkedIn。
```

预检必须确认插件版本、Skill/运行时文件、Python 版本和运行目录可写。知识库或 Agent 接口缺失不是阻塞项。

## 4. 只读业务验收

示例请求：

```text
$tuolin-linkedin-search 关键词：Exhaust Wrap, Exhaust Heat Wrap。通过 LinkedIn Posts 搜索潜在客户，先完成候选审核，不发送连接邀请。
```

验收顺序：

1. 访谈只补齐六个可执行字段；关键词缺失时只解释完整短语格式，不给推荐词。
2. 组合关键词按输入顺序逐个原样搜索，不拆词、翻译、纠错、扩词或布尔合并；大小写不敏感的完全重复只保留第一个。
3. 用户授权只读 Chrome 操作后，Codex 通过官方 Chrome 插件绑定可见账号。
4. 只搜索 Posts，不切 People，不添加地区条件。
5. 对每个词持续滚动，直到候选达有效上限、已打开判断 50 条唯一贴文，或连续 3 次到底等待无新唯一 URL/URN。页脚、广告、一次卡顿或 `page=2` 失效不能证明耗尽。
6. 候选卡显示完整可见贴文、URL、来源词、作者、公司、联系人、Connect 证据、AI 支持证据与重大疑点，并明确 AI 判断只是暂定。
7. 同类/基础材料直接制造商或供应商跳过；渠道商和下游使用方可进入人工复核；公司相关但无可验证联系人时记录为未解析线索且不占候选数。
8. 用户可批量删除；删除后不找补，封闭批次不能增加或替换候选。

## 5. 一条真实邀请验收

只读链路通过后，用户明确要求只保留 1 名候选并生成最终发送授权简报。简报必须显示绑定账号、精确候选、固定留言或无留言、固定间隔、请求上限、有效上限和滚动容量。

若使用留言，只能用关键词共同主题或通用行业语境生成简短英文文案，不得添加产品知识、参数、认证、价格或夸大声明；用户确认或修改后冻结整批文本。

最终简报确认后：

1. 重新读取账号、profile、公司/贴文 reservation、实时连接状态、标准 Connect 与留言可用性。
2. 运行时返回一次性 dispatch attempt 后才点击一次 Connect。
3. 只有 LinkedIn 显示邀请已发出或 profile 变成 Pending 才记录成功。
4. 结果不明确时停止且不重复点击；CAPTCHA、限制、安全检查、退出登录或账号不一致停止整个批次。

## 6. 去重、间隔和恢复

- 同一账号下，已保留、待处理、已发送、已连接或状态不明确的联系人不得再次进入候选卡。
- 同一公司已保留或联系时，不得换员工重复出现；同一贴文的查询参数和尾斜杠差异不得造成重复。
- 每次成功后执行授权的固定间隔；本地滚动 168 小时最多记录 100 次成功，单次默认上限 10。
- 普通中断必须核对最后动作并重新授权剩余封闭批次。平台级停止只能新建 restart 任务，重新绑定同一账号并复核原剩余候选，不重新搜索或找补。

## 7. 通过标准

完整验收需要：本地自动测试和安装预检通过、老板电脑只读搜索通过、完整候选卡与批量审核通过、跨任务去重通过，以及一条真实邀请完成“预检—点击—可见结果—账本”闭环。S10/S11 未在老板电脑执行前必须标记为待验收，不能冒充通过。
