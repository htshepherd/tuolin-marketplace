# LinkedIn 搜索 Skill 安装与远程真实业务测试

适用版本：Tuolin Marketplace `2.0.3`。

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

或解压 `tuolin-marketplace-2.0.3.zip` 后从本地目录安装：

```powershell
codex plugin marketplace add C:\Tuolin\tuolin-marketplace-2.0.3
codex plugin add tuolin-marketplace@tuolin-marketplace
codex plugin add chrome@openai-bundled
codex plugin list
```

安装或升级后新开 Codex 会话。若界面版本与 `codex plugin list` 不是 `2.0.3`，停止业务测试并先解决版本冲突。

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

1. 访谈只补齐六个可执行字段；最后一题询问“本次最多找多少个联系人给您筛选？”，默认 50，允许 1–100；不预先询问邀请人数。
2. 组合关键词按输入顺序逐个原样搜索，不拆词、翻译、纠错、扩词或布尔合并；大小写不敏感的完全重复只保留第一个。
3. 用户授权只读 Chrome 操作后，Codex 通过官方 Chrome 插件绑定可见账号。
4. 只搜索 Posts，不切 People，不添加地区条件。
5. 系统为所有关键词分配首轮软份额，每个词都获得搜索机会；首轮后按原顺序继续产出词，直到审核人数满足或全部词可验证耗尽。
6. 不再使用“每词打开 50 条贴文”上限。连续 3 次到底、等待且无新唯一 URL/URN 才能证明耗尽；页脚、广告、一次卡顿或 `page=2` 失效不能证明耗尽。
7. Codex 只硬排除明显误命中、同类直接供应商、重复/已联系对象和无普通 Connect 的人；其他业务上可能相关但不确定的对象进入老板审核，并记录完整贴文、判断依据和疑点。
8. 每个账号生成一份累计 Excel，包含“潜客联系人、潜客证据、发送记录”；老板在联系人表使用“发送/排除/待定”下拉框和可选备注完成筛选。
9. 同一成员重复出现时更新原行并追加贴文证据，不占本轮新增人数；同一公司同时只保留一名联系人。

## 5. 一条真实邀请验收

只读链路通过后，老板在累计表选择精确联系人。Codex 重新打印每个人的完整来源贴文、判断依据和疑点，并生成不可变最终发送快照。简报必须显示绑定账号、精确候选、固定留言或无留言、固定间隔、老板批准人数、滚动容量和快照摘要。

老板选择的人数就是拟发送人数；不存在固定单次 10 人上限。容量不足时系统不得自动截取前 N 人，必须让老板重新选择并确认精确子集。容量为 0 时只阻止 Connect，不影响继续搜索和整理 Excel。

若使用留言，只能用关键词共同主题或通用行业语境生成简短英文文案，不得添加产品知识、参数、认证、价格或夸大声明；用户确认或修改后冻结整批文本。

最终简报确认后：

1. 重新读取账号、profile、公司/贴文 reservation、实时连接状态、标准 Connect 与留言可用性。
2. 运行时返回一次性 dispatch attempt 后才点击一次 Connect。
3. 只有 LinkedIn 显示邀请已发出或 profile 变成 Pending 才记录成功。
4. 结果不明确时停止且不重复点击；CAPTCHA、限制、安全检查、退出登录或账号不一致停止整个批次。

## 6. 去重、间隔和恢复

- 同一账号的所有任务写入同一累计潜客表；不同账号使用不同工作簿。
- 已发送、邀请 Pending、已连接或老板排除的联系人不得再次进入新审核池；历史待定只有在老板本次明确选择后才进入快照。
- 同一公司已保留或联系时，不得换员工重复出现；同一贴文的查询参数和尾斜杠差异不得造成重复。
- 默认固定间隔为 2 分钟，允许不低于 1 分钟的整数分钟，并在快照中冻结；本地滚动 168 小时最多记录 100 次成功。
- 普通中断必须核对最后动作并重新授权剩余封闭批次。平台级停止只能新建 restart 任务，重新绑定同一账号并复核原剩余候选，不重新搜索或找补。

## 7. 通过标准

完整验收需要：本地自动测试和安装预检通过、老板电脑约 50 人的只读审核池和累计 Excel 通过、跨任务去重通过，以及一个老板精确选择的真实批次完成“快照—授权—预检—点击—可见结果—账本—Excel”闭环。真实只读/邀请验收未在老板电脑执行前必须标记为待验收，不能冒充通过。
