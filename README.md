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

To upgrade an existing installation:

```powershell
codex plugin marketplace upgrade tuolin-marketplace
codex plugin add tuolin-marketplace@tuolin-marketplace
codex plugin list
```

## LinkedIn prospect search

Version 1.52.2 includes `$tuolin-linkedin-search`, a product-grounded LinkedIn Posts workflow. It requires:

- the real Tuolin knowledge project with a refreshed and verified `generated/agent-interface/`;
- the official `chrome@openai-bundled` plugin;
- the account owner's existing Chrome profile with LinkedIn already signed in;
- explicit confirmation before read-only browser work and again before the exact invitation batch.

Recommended first request on the business computer:

```text
$tuolin-linkedin-search 请基于正式产品知识，通过 LinkedIn 贴文搜索潜在客户。先访谈并做只读候选测试，不发送连接邀请。
```

The workflow prints and persists the source post, author, company, selected contact, and selection reason before authorization. Real invitation tests use a preflight-before-click contract, a fixed interval, account-scoped cross-task deduplication, and a local maximum of 100 recorded successes in a rolling 168-hour window. The local limit is a product rule, not an official LinkedIn limit, and it does not count manual activity.

Remote installation and acceptance details: `docs/operations/linkedin-search-install-and-remote-test.md`.

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
