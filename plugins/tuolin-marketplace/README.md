# Tuolin Marketplace

Codex plugin marketplace for Tuolin business agents.

## Usage

Install this repository in the Codex client:

```text
https://github.com/htshepherd/tuolin-marketplace
```

Use the plugin from Codex with Chinese natural-language requests.

LinkedIn publishing image requests are controlled by the Tuolin LinkedIn agent. For example:

```text
生成 LinkedIn Day 01 发布图
```

The first response must be a Day image selection sheet and a question asking the user to choose a source image and image style category. Codex must not directly generate or save a publishing image for this initial request.

Quartz-fiber-tape video creation requests are controlled by the Tuolin video workflow agent. For example:

```text
$tuolin-video-workflow 做一个60秒石英纤维隔热带产品介绍视频，面向欧美工业采购商，用在 YouTube Shorts 和 TikTok。
```

Local documentation:

- `doc/video-creation-natural-language-operations.md`
- `doc/video-creation-deployment-and-config.md`

## Notes

- Codex client only.
- Windows supported.
- Do not commit local enterprise data.
