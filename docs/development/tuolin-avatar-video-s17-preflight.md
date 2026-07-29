# S17 真实数字人口播样片预检

## 状态

- 预检日期：2026-07-29
- 推荐最小验收：30 秒英文、9:16、YouTube Shorts、石英纤维隔热带
- 当前结论：本地正式旧知识包与真实素材已找到，但新专属知识接口未建立；Fish 与 HeyGen 真实账户尚未授权，不能开始付费生成。

## 已找到的本地业务输入

- 旧知识包：`/Users/kkid/Documents/tuolinagent/graphify-out/tuolin-agent-packs`
- 旧 manifest 产品：石英纤维隔热带（`quartz-fiber-insulation-tape`），状态 `ready`
- 建议新接口产品 ID：`product/quartz_fiber_tape`
- 真实素材根目录：`/Users/kkid/Documents/tuolinagent/raw`
- 旧配置：`/Users/kkid/Documents/tuolinagent/config/tuolin-kb.config.json`

旧配置和旧知识包仍引用不存在的 `/Users/kkid/Documents/tuolintec/raw`；实际素材位于 `/Users/kkid/Documents/tuolinagent/raw`。旧 manifest 同时标记该产品分区 `needs_update`，因此不得直接冒充新 `tuolin-avatar-video` 专属接口。

## 产品图片像素预检

| 图片 | 尺寸 | 主体与清晰度 | 9:16 使用判断 | 风险/建议 |
|---|---:|---|---|---|
| `Capture One Catalog0669 拷贝.jpg` | 6240×4160 | 三卷白色隔热带，棚拍清晰，主体明确 | 可用；建议 `contain` 或围绕三卷产品居中裁切 | 首选产品主视觉；背景高光较多但不影响识别 |
| `IMG_7666-1.JPG` | 3912×2635 | 隔热带包覆排气管，黑底、对比清楚 | 有条件可用；横向主体过长，竖屏应 `contain`，不宜强裁切 | 首选应用说明图；不得把画面本身当作性能测试证明 |
| `微信图片_20241216134854.jpg` | 4096×2632 | 户外设备与包覆排气管，主体可辨 | 有条件可用；中央竖裁可保留设备和带材 | 场景较杂，含 `WILD HUNTER` 品牌和相机信息条；对外使用前需确认权利并裁掉底部信息条 |

三张图片彼此不是近重复。对于 30 秒样片，结合数字人镜头可支撑不重复的最小方案；60–90 秒需要补充正式素材、生成非事实辅助图，或由用户明确允许有意重复。

## 已通过的技术预检

- 全仓自动测试：455 项通过，1 项真实 HyperFrames 长集成测试默认跳过。
- 真实 HyperFrames CLI：已单独通过 `init → lint → inspect → render`，输出 30 秒 1080×1920 H.264/AAC 媒体。
- 受控 HyperFrames 失败：FFmpeg 自动保底通过。
- Fish Audio：官方 `/v1/tts` MessagePack 合同已实现并由伪服务验证。
- HeyGen：官方 CLI v3 avatar 合同、外部 Fish 音频、任务回执和中断恢复已验证。
- 辅助图片：真实可替换供应商边界和与 Fish 并行执行已验证。
- 付费幂等：外部 I/O 前原子消费授权/输入指纹；失败或不确定提交必须显式授权重试。

## 仍需人工完成的 S17 门禁

1. 决定是否把 `/Users/kkid/Documents/tuolinagent` 作为正式新知识项目根目录，并授权系统整理现有 raw、建立 `knowledge/okf`、`generated` 和独立 `tuolin-avatar-video` 接口。
2. 在 Codex 运行环境配置 Fish Audio 凭据，并提供已授权 voice ID；不要在聊天中粘贴密钥。
3. 通过 `heygen auth login --oauth` 登录会员账户，并选择固定 public Avatar ID。
4. 用户确认完整 30 秒英文方案及首次消费范围。
5. 用户完整试听 Fish 音频并查看全部辅助图片（若使用），一次联合确认。
6. 用户完整观看并确认 HeyGen 原片。
7. 用户完整观看最终 YouTube Shorts，并确认生成 accepted 本地交付包。

以上门禁完成前，`real_paid_hitl` 必须保持 `false`，S17 不得勾选。
