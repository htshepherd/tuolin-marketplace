# 拓霖工业产品即梦 Prompt 规则

本文件吸收 `dexhunter/seedance2-skill`、`songguoxs/seedance-prompt-skill`、`zhanghaonan777/Seedance2-skill` 和 `MapleShaw/seedance2.0-prompt-skill` 中适合工业产品视频的 Prompt 方法论。

## Prompt 结构

每个镜头 Prompt 必须包含：

1. Timebox：镜头时间段和 9:16 竖屏要求。
2. Subject：主体画面和产品上下文。
3. Reference material：`@图片1`、`@视频1`、`@音频1` 等运行内编号引用，或明确说明无具体产品描绘。
4. Time segments：按 0-2s、2-4s、4-5s 等分时段描述可执行画面变化。
5. Motion and camera：工业产品运镜，例如慢推、后拉、轻微环绕、织纹微距、局部特写、包覆动作跟随镜头。
6. Environment：工业 B2B 画面环境。
7. Material texture：织物、边缘、厚度、柔性等材料细节。
8. Product display template：石英纤维隔热带展示模板，例如卷装 hero、织纹微距、边缘/厚度特写、柔性弯折、包覆动作、CTA 收尾。
9. Safety and negative constraints：禁止字幕、平台 UI、水印、虚假认证、夸大测试、虚假客户现场、攻击竞品。

## 生成边界

- Prompt 是给即梦使用，不是字幕、旁白或发布文案。
- 产品可见镜头必须使用真实产品图片或视频作为参考。
- 每个进入即梦任务的素材必须有稳定编号和明确用途；不得只写“参考素材”或“参考 @图片1”。
- `prompts.md/json` 与 `dreamina_jobs.md/json` 必须使用同一套素材编号映射。
- 如果素材用途缺失、编号缺失或超过 `dreamina_capability_profile` 的多模态数量限制，任务必须 blocked。
- 产品 hero、产品细节和应用解释镜头应优先使用真实产品图作为首帧参考，CTA 镜头可使用真实产品图作为尾帧/定格参考。
- 素材如果标记为 `human_face_risk: clear_face`，不能进入真实即梦任务；`unclear` 必须给出裁切、打码或替换为手部/设备局部的警告。
- 4-8 秒镜头也必须拆成 2-3 个分时段动作；8 秒以上镜头必须分时段。
- Prompt 必须做指令冲突检查：固定镜头不能同时要求快速环绕/跟拍；禁止字幕/文字时不能要求生成画面文字；禁止虚假客户现场时不能写成真实客户现场；禁止夸大测试时不能要求证明性认证或保证性表达。
- Prompt 必须做时长复杂度检查：5 秒镜头最多 3 个分时段，8 秒镜头最多 4 个分时段，15 秒镜头最多 5 个分时段；短镜头不得堆叠过多 cut、montage、split screen、rapid transition 等场景/转场动作。
- Prompt 不得吸收短剧、舞蹈、仙侠、强情绪台词、医学科普或泛娱乐模板。
- 纯 text2video 只能用于环境、过渡或非具体产品镜头。
- 不硬编码中文或英文对外产品名；名称来自知识卡。
- 不引入知识卡之外的参数、认证、检测结论或应用承诺。
