# Digital-avatar workflow contract

## Required state order

`interview → plan confirmation → combined input confirmation → presenter confirmation → composition → final confirmation → local delivery`

Resume from the persisted current phase. Never replay a completed provider call. A missing or corrupt active artifact, changed dedicated-interface revision, or changed product projection blocks continuation visibly.

## Confirmation semantics

- Ordinary confirmation applies only to the result currently displayed.
- Plan confirmation also authorizes the disclosed first Fish, auxiliary-image, and HeyGen attempts.
- A provider retry or newly added paid scope requires explicit new authorization.
- Provider completion never implies user acceptance. Complete Fish audio, all images, the full HeyGen original, and all final platform files must each reach their defined human checkpoint.
- Final delivery needs one confirmation after the user sees all complete platform files; do not add a second submission confirmation.

## Evidence and generation

- Formal interface cards establish facts; pixel inspection establishes visual usability.
- Generated images may support atmosphere, layout, or explanation only. They cannot prove a product parameter, certification, test, customer, or real application.
- Viewer-visible AI or “illustration” labels are not added by default because the user participates throughout. Preserve generation provenance internally.
- Narration continues across presenter and full-screen evidence intervals.

## Provider attempts

Persist an immutable attempt per provider and input fingerprint: authorization ID, input revision, safe settings, task ID, estimated/actual consumption, output, media probe, and human review. Never persist keys, tokens, cookies, authorization headers, or secret URL query values.

For Fish Audio, send the confirmed text to `/v1/tts` as `application/msgpack`, keep speed under `prosody`, and pin the selected voice/model settings. For HeyGen production, use the official CLI/App v3 path with external Fish audio; direct deprecated v1/v2 generation endpoints are compatibility fixtures only. Persist a local task receipt and provider attempt immediately after HeyGen returns a video ID. A timeout or local interruption resumes status polling and download for that ID instead of creating another paid task.

When the confirmed plan contains support visuals, use the replaceable connected image-generator adapter and start it concurrently with Fish Audio. The adapter must receive the exact authorized batch and return the exact number of readable local images plus a provider task ID. Prompt text, task status, missing pixels, or an extra image count never satisfies the combined-input checkpoint.

`mock`, `dry-run`, `failed`, `rejected`, `stale`, and `incomplete` are not accepted real outputs. Rejection retains the old attempt and reason; a retry creates a new attempt.

## Revisions

- Caption, title/parameter layout, user BGM, transition, or confirmed-asset timing: invalidate only composition, final confirmation, and delivery.
- Narration: invalidate plan confirmation, Fish, HeyGen, composition, and delivery.
- Fish settings or audio: invalidate confirmed input, HeyGen, composition, and delivery; require retry authorization.
- Avatar/settings or presenter original: invalidate HeyGen, composition, and delivery; require retry authorization.
- Facts or official evidence: return to material/plan confirmation.

Never overwrite prior provider attempts, renders, rejected results, or an existing accepted delivery directory.

## Failure and fallback

HyperFrames production executes `init`, writes the real composition project, then requires successful `lint`, `inspect`, and strict `render`. HyperFrames absence, execution failure, or invalid media automatically invokes the FFmpeg composer with the same narration, evidence order, continuous timeline, captions, BGM contract, and platform specs. Record diagnostics, the path used, and fallback reason without adding a confirmation gate.

Fail loudly on stale interfaces, missing image paths, uninspected or risky materials, malformed provider responses, timeouts, corrupt media, unexpected platform counts, archive conflicts, or any state that could be mistaken for publishable output.
