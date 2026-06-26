# 拓霖工业产品即梦 Prompt 规则

本文件吸收 `dexhunter/seedance2-skill`、`songguoxs/seedance-prompt-skill`、`zhanghaonan777/Seedance2-skill` 和 `MapleShaw/seedance2.0-prompt-skill` 中适合工业产品视频的 Prompt 方法论。

## Prompt 结构

每个镜头 Prompt 必须包含：

1. Timebox：镜头时间段和 9:16 竖屏要求。
2. Subject：主体画面和产品上下文。
3. Reference material：`@Image`、`@Video` 或明确说明无具体产品描绘。
4. Motion and camera：动作和运镜。
5. Environment：工业 B2B 画面环境。
6. Material texture：织物、边缘、厚度、柔性等材料细节。
7. Safety and negative constraints：禁止字幕、平台 UI、水印、虚假认证、夸大测试、虚假客户现场、攻击竞品。

## 生成边界

- Prompt 是给即梦使用，不是字幕、旁白或发布文案。
- 产品可见镜头必须使用真实产品图片或视频作为参考。
- 纯 text2video 只能用于环境、过渡或非具体产品镜头。
- 不硬编码中文或英文对外产品名；名称来自知识卡。
- 不引入知识卡之外的参数、认证、检测结论或应用承诺。

