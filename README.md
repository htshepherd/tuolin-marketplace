# Tuolin Marketplace

Codex plugin marketplace for Tuolin business agents.

## Usage

Add this repository as a Codex plugin marketplace, then install the Tuolin plugin and the official Chrome plugin:

```powershell
codex plugin marketplace add htshepherd/tuolin-marketplace --ref main
codex plugin add tuolin-marketplace@tuolin-marketplace
codex plugin add chrome@openai-bundled
codex plugin list
```

Open a new Codex conversation after installation. Use the plugin with Chinese natural-language requests; end users do not need to invoke its internal scripts.

Version 2.0.1 automatically discovers `<project-dir>/config/tuolin-kb.config.json` for every internal entry point. It also caches verified video hashes with file size and modification time, so routine knowledge-card refreshes do not reread unchanged local videos. Configured absolute MinerU and ffmpeg paths are reused directly; knowledge workflows do not create replacement Python environments or reinstall MinerU implicitly.

To upgrade an existing installation:

```powershell
codex plugin marketplace upgrade tuolin-marketplace
codex plugin add tuolin-marketplace@tuolin-marketplace
codex plugin list
```

## LinkedIn prospect search

Version 2.0.1 includes `$tuolin-linkedin-search`, a keyword-driven LinkedIn Posts review-pool workflow. It requires:

- a writable Tuolin operational workspace; no product knowledge base is required;
- the official `chrome@openai-bundled` plugin;
- the account owner's existing Chrome profile with LinkedIn already signed in;
- explicit confirmation before read-only browser work and again before the exact invitation batch.

Recommended first request on the business computer:

```text
$tuolin-linkedin-search 关键词：Exhaust Wrap, Exhaust Heat Wrap。通过 LinkedIn Posts 搜索潜在客户，先做只读候选测试，不发送连接邀请。
```

The workflow uses balanced sampling across every supplied phrase and keeps scrolling until the requested human-review pool is full or every phrase has proven exhaustion. It writes complete posts, contact identity, Codex reasoning, doubts, and a `发送/排除/待定` dropdown into one cumulative Excel workbook per LinkedIn account. Discovery is independent of dispatch capacity. The boss's exact workbook selection becomes an immutable final snapshot; there is no fixed ten-person batch ceiling, and the default fixed interval is two minutes with a one-minute minimum. Dispatch still uses preflight-before-click, account-scoped deduplication, and a local maximum of 100 recorded successes in a rolling 168-hour window. The local limit is a workflow rule, not an official LinkedIn limit, and it does not count manual activity.

Remote installation and acceptance details: `docs/operations/linkedin-search-install-and-remote-test.md`.

LinkedIn publishing image requests are controlled by the Tuolin LinkedIn agent. For example:

```text
生成 LinkedIn Day 01 发布图
```

The first response must be a Day image selection sheet and a question asking the user to choose a source image and image style category. Codex must not directly generate or save a publishing image for this initial request.

Planning-only video requests must explicitly use the independent planner. It supports formally published products, YouTube Shorts and TikTok, and stops after the confirmed shot plan, narration, and SRT:

```text
$tuolin-video-planner 为石英纤维隔热带做一个30秒英文镜头策划，面向欧美工业采购商，用于 YouTube Shorts 和 TikTok。
```

Full video creation remains controlled by the existing workflow agent:

```text
$tuolin-video-workflow 做一个60秒石英纤维隔热带产品介绍视频，面向欧美工业采购商，用在 YouTube Shorts。
```

Local documentation:

- `doc/video-creation-natural-language-operations.md`
- `doc/video-creation-deployment-and-config.md`

## Notes

- Codex client only.
- Windows supported.
- Do not commit local enterprise data.
