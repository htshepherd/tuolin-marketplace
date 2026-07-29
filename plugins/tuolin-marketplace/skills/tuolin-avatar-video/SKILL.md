---
name: tuolin-avatar-video
description: Create evidence-grounded 30–90 second digital-avatar product videos with Fish Audio, a fixed HeyGen avatar, HyperFrames-first packaging, FFmpeg fallback, and local delivery. Use only when the user explicitly invokes $tuolin-avatar-video for English YouTube Shorts or Chinese Douyin and Kuaishou output.
---

# Tuolin Avatar Video

This is an independent digital-avatar production Agent. It never replaces `$tuolin-video-planner` or `$tuolin-video-workflow`, and it starts only after explicit `$tuolin-avatar-video` invocation.

## Boundaries

- Read products, facts, evidence, and allowed images only through the `tuolin-avatar-video` Agent interface. Never scan `raw/`, another Agent's projection, legacy context, or a prior video plan.
- Do not search trends. Do not create Dreamina shots. Do not log in, upload, schedule, write publishing metadata, or publish.
- Support one language per run: English produces one YouTube Shorts file; Chinese produces a shared master plus Kuaishou and Douyin files.
- Accept any integer duration from 30 through 90 seconds; all outputs are 1080x1920.
- Fish Audio supplies the fixed cloned voice. HeyGen uses the plan's versioned public Avatar. A custom Digital Twin is only a later avatar-ID replacement, never created here.
- Use the official HeyGen CLI/App path backed by the supported v3 API. Do not call deprecated direct v1/v2 video-generation endpoints.
- Prefer the real HyperFrames CLI pipeline (`init → lint → inspect → render`) for packaging and automatically use deterministic FFmpeg fallback when it is missing, fails, or returns invalid media.
- Burn same-language captions by default. Do not ask about music; default to no BGM. Use music only when the user explicitly supplies a readable local file before plan confirmation.

## Workflow

1. Create an isolated run and pin the dedicated interface revision and product fingerprint.
2. Extract known business decisions. Ask one missing load-bearing business question at a time, with exactly one recommendation and reason. Never ask trend, editing, shot-count, animation, subtitle-style, or BGM questions.
3. Internally open every candidate official image and record subject, clarity, composition, 9:16 crop, near-duplicates, and risks. Block plan confirmation when distinct usable images cannot support the duration unless the user shortens it or explicitly approves deliberate repetition or bounded simulation.
4. Show one complete production plan: audience logic, exact narration, continuous presenter/evidence timeline, inspected visuals, auxiliary-image batch, Fish voice, fixed HeyGen Avatar/version, captions, no-BGM default, provider consumption estimate, and risks.
5. One explicit plan confirmation locks the plan and authorizes only its disclosed first provider attempts. Repeated commands are idempotent. Changed scope or retry needs new explicit authorization.
6. Generate Fish audio with the official `/v1/tts` MessagePack contract and any disclosed auxiliary-image batch through the connected replaceable image-generator adapter in parallel. The image adapter must receive the exact authorized count, purpose, and inspected product reference and return real local pixels plus a task ID. Show the complete playable audio and every real image; one reply confirms this combined input set.
7. Upload only that confirmed Fish audio through the HeyGen CLI, create the fixed-avatar v3 task, and durably save its task ID before polling. On interruption, query/download the same task; never re-upload or resubmit it. Show the playable original; confirmation requires full viewing.
8. Compose through the real HyperFrames CLI pipeline or automatic FFmpeg fallback. Show every complete platform file and media-validation summary. One final confirmation is enough.
9. Create an immutable local handoff pack only after final confirmation. End there without publication.

Natural-language revisions must change real plan, provider, or packaging fields. Packaging-only changes create a new render revision without repeating Fish or HeyGen. Protected changes invalidate exactly their downstream dependencies.

Read [workflow-contract.md](references/workflow-contract.md) for state, confirmation, provider, recovery, and failure rules.

## User operation

Users operate only through natural language. Never ask them to edit JSON, inspect ledgers, or run internal scripts. At each checkpoint, show the decision-sufficient result, file locations, verification state, blocker if any, and the next recommended natural-language reply.
