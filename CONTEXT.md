# Tuolin Marketplace Agent Context

This context describes the business language for Tuolin's local knowledge agents and downstream marketing agents.

## Language

**LinkedIn Campaign Plan**:
A Chinese marketing strategy document that defines campaign positioning, audience, claims, content rhythm, and asset direction before daily post copy is produced.
_Avoid_: treating it as the final 30-day post copy

**Marketing Plan Review**:
An optional review of the **LinkedIn Campaign Plan** for market fit, messaging quality, compliance risk, and readiness to generate daily posts.
_Avoid_: knowledge review, review item, fact review

**LinkedIn Marketing Review Skill**:
A dedicated skill named `tuolin-linkedin-marketing-review` that reviews `01_中文策划.md` and produces a conclusion, risks, suggestions, and a recommendation on whether to continue to daily post generation.
_Avoid_: generic discussion skill, knowledge-base review workflow

**Single-Day Publishing Image Generation**:
An on-demand workflow that creates publishing images for one LinkedIn campaign day after loading that day's content, asset notes, source image, and tags.
_Avoid_: bulk 30-day image generation

**Publishing Image Selection Sheet**:
A pre-generation response that summarizes one day's post theme, source image, tags, size suggestions, and visual style choices before any image model is called.
_Avoid_: immediate image generation

**Desktop Delivery Copy**:
A copied LinkedIn campaign folder on the user's Desktop for boss review and manual operation, derived from the canonical campaign output without replacing it.
_Avoid_: canonical campaign directory

**Publishing Image Style Prompt**:
A reusable prompt template for one visual style category that can be filled with a specific day's post theme, tags, source image, logo, email, and size recommendation.
_Avoid_: one-off chat-only prompt

**Tuolin LinkedIn Image Style Skill**:
A dedicated skill named `tuolin-linkedin-image-style` that loads visual style categories and guides Codex to generate single-day LinkedIn publishing images with an image model.
_Avoid_: embedding all image style prompts directly in the campaign-generation code

**Knowledge Review**:
A formal review of uncertain knowledge-base facts before they can become approved external knowledge.
_Avoid_: marketing plan review

**Video Language Version**:
A user-selected Chinese or English deliverable whose narration and subtitles use the selected language.
_Avoid_: base master, visual master, final master

**Video Creative Direction**:
A user-confirmed item from the complete fixed video-direction taxonomy that guides one video plan.
_Avoid_: publishing image style, image style category

**Recommended Video Creative Directions**:
A ranked subset of the fixed video-direction taxonomy selected dynamically from the request, audience, platform, product knowledge, and available materials.
_Avoid_: hiding the complete taxonomy, generating an unregistered direction

**External Video Generation Skill Internalization**:
The conversion of external Seedance/Dreamina skill methods into Tuolin-owned prompt, shot-validation, execution, and quality-gate rules.
_Avoid_: copying external code, importing entertainment categories, bypassing knowledge-card facts

**Creative Quality Matrix by Video Direction**:
Direction-specific checks for hook, visual focus, message focus, and CTA behavior that change according to the selected fixed video creative direction.
_Avoid_: one generic visual quality score, cinematic style overriding the selected direction

**Industrial Product Video Style Matrix**:
The internal mapping from Tuolin's fixed video creative directions to industrial B2B styles such as professional industrial, minimal product, technical explainer, application scene, and procurement decision.
_Avoid_: Apple/Vercel consumer-product style labels as user-facing categories

**Industrial Visual Quality Gate**:
The automated video quality gate that checks industrial-product planning quality, real-material references, structured Dreamina prompts, job validation, subtitles, BGM, timing, and final-review readiness.
_Avoid_: automatic creative approval, platform-restricted-word module detached from knowledge facts

**Quartz Fiber Tape Video Scope**:
The initial video workflow scope covering product videos for the internally identified product 石英纤维隔热带.
_Avoid_: workshop videos, other product lines, generic all-product taxonomy

**Knowledge Producer**:
The Tuolin knowledge-base agent that publishes approved product knowledge and content-asset references through the Agent interface.
_Avoid_: a marketing or video deliverable generator

**Video Creation Consumer**:
An application-layer agent that consumes the Agent interface to produce product-video deliverables without owning or redefining product knowledge.
_Avoid_: knowledge producer, LinkedIn consumer, hard-coded product facts

**Video Workflow Entrypoint**:
The user-facing `tuolin-video-workflow` skill that orchestrates the complete video-creation run through natural-language confirmations.
_Avoid_: requiring users to invoke internal runners or copy run-directory paths

**Video Creation Context**:
The `video_creation` downstream task context used by the complete quartz-fiber-tape video workflow.
_Avoid_: video_script, treating video creation as only narration writing

**Video Creation Run**:
One language-specific quartz-fiber-tape video production record stored under `generated/reports/video-creation/`.
_Avoid_: formal knowledge, raw evidence archive

**Video Narration Audio**:
The workflow-generated spoken audio in the selected video language version.
_Avoid_: user-supplied WAV prerequisite, narration in a different language

**Video Background Music**:
Commercially usable music selected automatically to match the confirmed creative direction and embedded in the delivered video.
_Avoid_: requiring the user to choose a track before planning, downloading TikTok trending songs

**Music Brief**:
The planning output that specifies the required mood, pacing, intensity, and usage constraints for background music.
_Avoid_: an actual music file, a TikTok song reference

**Music Provider Adapter**:
The independent capability that retrieves or generates commercially usable music from a **Music Brief** and records source and licensing metadata.
_Avoid_: embedding music-provider logic in creative planning

**Narration Provider Adapter**:
The independent capability that generates narration audio and sentence-level timing in the selected language.
_Avoid_: relying on Dreamina CLI for text-to-speech

**Narration Voice Selection**:
The user choice of one voice after hearing three samples recommended for the selected language, audience, and creative direction.
_Avoid_: generating full narration before choosing a voice

**Burned-in Video Subtitles**:
Always-visible subtitles rendered into the video image in the selected language version.
_Avoid_: optional subtitle track, subtitles in a different language

**Video Information Overlay**:
Controlled on-screen text for titles, confirmed parameters, short benefit labels, and calls to action in the selected language.
_Avoid_: unsupported claims, uncontrolled text-heavy cards

**Video End Logo**:
The transparent logo from project configuration, displayed once at the end of the video.
_Avoid_: full-video watermark, hard-coded logo path

**Video Quality Gate**:
The automated pre-preview check that separates blocking render defects from user-reviewable warnings.
_Avoid_: automatic creative approval

## Relationships

- A **LinkedIn Campaign Plan** may receive zero or one **Marketing Plan Review** before daily post copy is generated.
- A **LinkedIn Marketing Review Skill** performs the **Marketing Plan Review** for a LinkedIn campaign.
- A **Marketing Plan Review** is optional; skipping it still allows the campaign to continue to Chinese 30-day draft generation.
- Accepted **Marketing Plan Review** suggestions are applied directly when generating the Chinese 30-day post draft; no separate campaign-plan final draft approval is required.
- **Single-Day Publishing Image Generation** must be driven by one day's actual post theme, tags, and source image.
- A LinkedIn campaign should not generate all 30 days of publishing images in one batch.
- A **Publishing Image Selection Sheet** must be shown before single-day image generation, and the user must choose one to three visual style categories before image generation starts.
- Generated day images should be saved under `Manual-Posting-Package/Day XX/Publish-Images/<category-slug>/`.
- The image style capability is provided by **Tuolin LinkedIn Image Style Skill**.
- Generated day image folders do not need to save `source-info.json` or `prompt.md`.
- Single-day image generation creates one image per selected style category, with at most three images per request.
- Image-model work must edit from the selected day's source image instead of inventing a disconnected product image.
- Scenario-oriented styles require a compatible scenario source image; if the day only has a product cutout or white-background source, the agent should ask for a better source image instead of fabricating a fake application scene.
- Publishing images default to the source image dimensions; size recommendations are advisory unless the user explicitly chooses a different size.
- A **Publishing Image Selection Sheet** should show all 20 primary style categories, recommend three categories for the current day, and warn about categories that do not fit the current source image or post theme.
- After the user chooses style categories, Codex should call the image model directly; the user should not have to copy prompts manually.
- A **Desktop Delivery Copy** may be created after 30-day post content is ready, and generated single-day publishing images should also be copied into that desktop delivery folder for boss review.
- A **Marketing Plan Review** does not approve or reject knowledge-base facts.
- A **Knowledge Review** may affect formal knowledge cards, but it does not review marketing campaign quality.
- Every video production run must select exactly one **Video Language Version** before creative planning proceeds.
- Chinese and English videos are first-class deliverables; neither is modeled as a derivative of a master.
- A Chinese **Video Language Version** contains Chinese narration, Chinese subtitles, and background music.
- An English **Video Language Version** contains English narration, English subtitles, and background music.
- One video production run produces only the **Video Language Version** confirmed by the user.
- Every video production run must confirm one **Video Creative Direction** before the formal video plan is generated.
- The 20 publishing image style categories do not define or constrain **Video Creative Directions**.
- Creative-direction selection must show the complete fixed taxonomy and the **Recommended Video Creative Directions** together.
- Recommendations help the user choose but never replace or hide the complete taxonomy.
- The fixed video-direction taxonomy must be defined explicitly before implementation.
- The initial fixed video-direction taxonomy applies only to **Quartz Fiber Tape Video Scope**.
- Workshop-video directions and directions for other Tuolin products are outside the initial scope.
- The initial quartz-fiber-tape taxonomy contains 16 fixed **Video Creative Directions**: product overview, single core benefit, multiple-benefit overview, product detail, application demonstration, customer pain-point solution, installation demonstration, usage precautions, technical education, performance test, FAQ, material comparison and selection, specification and customization, procurement guide, real case study, and inquiry conversion.
- New directions may be added later when the fixed taxonomy is insufficient; existing direction identities must remain stable for prior video runs.
- One video run must select exactly one primary **Video Creative Direction** and may select at most one supporting direction.
- Dynamic recommendations should propose primary-and-supporting direction combinations while still showing the complete 16-direction taxonomy.
- Creative-direction selection must show exactly three ranked recommendation combinations.
- Each recommendation must state its primary direction, optional supporting direction, recommendation rationale, material coverage, missing materials, and AI-generation risk.
- **External Video Generation Skill Internalization** is a bottom-layer enhancement of prompt writing, shot validation, execution reliability, references organization, continuity, and quality gates; it does not create new user-facing video direction categories.
- `dexhunter/seedance2-skill` is internalized as Seedance/Dreamina prompt grammar and structure, not as a business taxonomy source.
- The **Creative Quality Matrix by Video Direction** must be selected from the confirmed primary **Video Creative Direction** and carried through plan, storyboard, prompt generation, Dreamina job planning, and quality gate.
- The **Industrial Product Video Style Matrix** is selected internally from the confirmed directions; users still choose the fixed video creative directions rather than style labels.
- The initial workflow order is: identify a quartz-fiber-tape video request; confirm the **Video Language Version**; collect platform, duration, audience, and core objective; show recommendations and all 16 directions; confirm the direction selection; then generate the formal video plan.
- A formal video plan must not be generated before both the language version and creative direction are confirmed.
- The initial workflow supports only 60-, 90-, and 120-second videos; 60 seconds is the default.
- The initial workflow targets YouTube Shorts and TikTok only; standard horizontal YouTube videos and other platforms are outside the initial scope.
- All initial YouTube Shorts and TikTok deliverables use a 9:16 vertical aspect ratio; the workflow does not maintain platform-specific framing variants.
- A run may target TikTok, YouTube Shorts, or both.
- When both platforms are selected, they share one 9:16 deliverable; the workflow records both targets but does not render duplicate platform files.
- For multi-platform runs, subtitles, logos, and information overlays use the intersection of TikTok and YouTube Shorts safe areas.
- The initial video workflow does not generate platform titles, post copy, descriptions, or hashtags; those belong to a later publishing skill.
- Each 60-, 90-, or 120-second run produces one complete video; the initial workflow does not split longer videos into a series.
- The **Knowledge Producer** supplies formal product knowledge to both the LinkedIn consumer and the **Video Creation Consumer**.
- The LinkedIn consumer and **Video Creation Consumer** are separate application scenarios with separate workflows and outputs.
- The **Video Creation Consumer** must read Chinese and English external product names from published knowledge cards instead of defining them itself.
- The **Video Creation Consumer** uses **Video Creation Context** as its only task-specific knowledge entrypoint.
- **Video Creation Context** supports the full workflow from creative direction through final video delivery.
- **Video Workflow Entrypoint** is the only user-facing video skill.
- The Dreamina runner is an internal execution capability invoked by the workflow; users do not trigger it separately or copy run-directory paths between skills.
- Narration and music provider adapters are also internal capabilities; users interact only with voice samples, narration confirmations, and video previews through the workflow.
- Provider names, commands, and intermediate file handoffs are not part of the ordinary user workflow.
- Narration and music integrations use provider-neutral adapter contracts and output formats.
- The initial workflow design does not bind a specific narration or music provider, and replacing a provider must not change workflow phases or business-facing filenames.
- The initial **Video Creation Context** is requested only for the quartz-fiber-tape product identified from the user's natural-language video request.
- The initial **Video Creation Context** contains the quartz-fiber-tape product card and only the content-asset cards explicitly related to that product.
- The initial video consumer does not expand retrieval through keyword search and does not read knowledge for other products.
- Each **Video Creation Run** is stored at `generated/reports/video-creation/{timestamp}_quartz_fiber_tape_{zh|en}/`.
- A **Video Creation Run** is an application-layer deliverable and must not be written into the formal knowledge layer or raw archive.
- A **Video Creation Run** retains requirements and direction decisions, plan, storyboard, prompts, narration script, voice samples, narration audio and timing, Dreamina jobs and shot files, music and licensing metadata, subtitle files, previews, confirmed deliverable, workflow state, and change log.
- Video creation run directories support audit and partial regeneration and must not be treated as disposable indexes merely because they live under `generated/reports/`.
- Video creation requires the knowledge base to be organized and its Agent interface to be available before a run starts.
- The initial workflow does not monitor or switch knowledge revisions during an active run.
- If the quartz-fiber-tape knowledge or Agent interface is unavailable, the video consumer stops and routes the user to organize the product through the knowledge producer first.
- The video consumer does not organize knowledge, scan raw, or bypass the formal interface with ad hoc facts.
- User-provided wording preferences may influence creative treatment, but task-specific product facts, parameters, performance claims, or promises that are absent from formal knowledge cannot enter a video.
- New product facts must be confirmed and published through the knowledge producer before video creation uses them; the video consumer has no one-run fact exception.
- When real application footage is unavailable, Dreamina may generate a simulated application scene only for applications confirmed by formal knowledge.
- AI-generated scenes must be identified as generated in the run record and must not be represented as a real customer case, real test record, or product-performance evidence.
- Generated scenes must not introduce unsupported equipment details, parameters, applications, or performance outcomes.
- Shot material selection follows this strict fallback order: real product video, real application video, real product image animated into video, real application image animated into video, AI-simulated scene, then text-only generated video.
- A lower-priority material mode is used only when higher-priority modes cannot satisfy the shot.
- Any generated shot that visibly contains the product must use real product imagery as an image-to-video or multimodal visual reference.
- Text-only video generation is allowed only for environmental or transitional shots that do not depict the specific product.
- Dreamina generation defaults to `seedance2.0_vip` at 1080P because the operating account has premium access.
- Final 9:16 deliverables use 1080 by 1920 pixels.
- Dreamina job review still displays estimated credit use before paid submission.
- Generated shots default to five seconds, may range from four to fifteen seconds, and should normally remain within four to eight seconds for short-form pacing.
- A 60-second run must finish within 55-65 seconds, a 90-second run within 85-95 seconds, and a 120-second run within 115-125 seconds.
- Runs outside the selected duration tolerance must revise narration or shot timing rather than truncate audio or pad with empty footage.
- Inquiry-conversion videos require a call to action; other creative directions may use a light call to action when appropriate.
- Call-to-action details must come from formal knowledge or project configuration and must not be hard-coded in the video skills.
- The **Video Creation Consumer** generates **Video Narration Audio** automatically; the user is not required to provide an audio file.
- The Dreamina runner mixes generated narration into the selected video deliverable during assembly.
- The **Video Creation Consumer** automatically selects **Video Background Music** according to the confirmed creative direction.
- The delivered video embeds **Video Background Music** directly.
- The workflow must not download, copy, or embed TikTok trending songs; it selects commercially usable music with a suitable style.
- Video planning produces a **Music Brief** but does not obtain the audio track itself.
- A **Music Provider Adapter** turns the brief into a usable music file and records its source and licensing information.
- If no music provider is available, the run cannot be marked complete.
- Background music has no separate mandatory user-confirmation gate; it is reviewed as part of the final video preview.
- A request to replace background music reruns music selection and audiovisual assembly without invalidating the confirmed storyboard, generated visual clips, or narration.
- A **Narration Provider Adapter** generates the selected-language narration audio and sentence-level timing data.
- Dreamina CLI generates visual clips and may accept existing audio references, but it does not replace the narration or music provider adapters.
- Before generating complete narration, the workflow presents three recommended voice samples and requires one **Narration Voice Selection**.
- After storyboard confirmation, the workflow first presents the complete narration text and waits for `确认旁白文案`.
- Voice samples are generated only after narration text confirmation.
- The three samples use the same 8-12 second excerpt from the actual narration so the voices can be compared fairly.
- The English version uses a middle-aged Western male voice.
- The Chinese version uses a natural, fluent middle-aged male Chinese voice without an intentionally Western accent.
- The user selects a sample with a natural-language reply such as `声音选 2`.
- After voice selection, the workflow generates a complete narration preview before submitting visual-generation jobs.
- The user must confirm the narration voice, pace, pronunciation, and content before visual generation proceeds.
- Confirmed narration timing drives shot duration and visual-generation planning.
- The natural-language command `确认旁白` locks the current narration text, voice, and timing and allows Dreamina job planning to proceed.
- A narration revision clears the prior confirmation, regenerates the preview and timing, and requires a new `确认旁白`.
- Dreamina job planning occurs only after `确认旁白`.
- Before submission, the user reviews job type, selected material, duration, and estimated credit use.
- Paid visual-generation jobs are submitted only after the user says `确认即梦生成`.
- Failed or unsatisfactory Dreamina shots may be regenerated individually without resubmitting accepted shots.
- Before a shot-level retry, the workflow shows that shot's estimated credit use and waits for explicit authorization such as `重做镜头 03`.
- After all visual jobs finish, the workflow assembles a shot preview using confirmed narration and temporary subtitles but no final background music.
- The user may request shot-level regeneration from the shot preview.
- The command `确认镜头` locks the accepted visual clips and permits final music selection, final subtitle rendering, and final assembly.
- Final assembly produces a final preview that remains incomplete until the user says `确认成片`.
- Before final confirmation, the user may request changes to music, subtitle styling, audio levels, or specified shots.
- Automated quality checks cannot mark the run complete; only `确认成片` does.
- The shot-review file is named `shot_preview.mp4`.
- The pre-confirmation final render is named `final_preview.mp4`.
- The confirmed Chinese deliverable is named `quartz_fiber_tape_zh_9x16.mp4`; the confirmed English deliverable is named `quartz_fiber_tape_en_9x16.mp4`.
- Video output filenames must not use the term `master`.
- Initial video deliverables use **Burned-in Video Subtitles** rather than an optional subtitle track.
- **Burned-in Video Subtitles** use the same language as the narration and selected **Video Language Version**.
- Subtitles use short sentence units, with one or two lines per screen.
- Subtitle timing follows narration sentences rather than word-by-word karaoke timing.
- Subtitle placement must remain inside the safe area between the top and bottom platform UI regions.
- Video deliverables may include **Video Information Overlays** in addition to subtitles.
- Overlays are limited to titles, formally confirmed parameters, short benefit labels, and calls to action.
- Overlay content must use the selected language, come from formal knowledge or approved configuration, and remain inside platform-safe areas.
- The workflow displays the configured **Video End Logo** once at the end by default and does not apply a full-video watermark.
- A missing configured logo produces a warning but does not block final assembly.
- **Video Quality Gate** blocks final preview for corrupt files, missing audio tracks, missing subtitles, wrong language, incorrect resolution or aspect ratio, out-of-tolerance duration, black frames, or missing shots.
- Subtitle density, loud music, rough transitions, missing logo, and weaker visual consistency are warnings shown to the user rather than automatic blockers.
- Blocking defects must be repaired before final preview; warnings remain visible for the user's `确认成片` decision.
- A **Video Creation Run** persists its current workflow phase and confirmations in `workflow_state.json`.
- Resuming a run restores the latest valid phase and asks only for the current pending confirmation instead of restarting or repeating locked work.
- Automated final-video checks may inspect audiovisual synchronization, subtitle timing, and audio levels, but they do not replace the user's final preview confirmation.

## Example Dialogue

> **Dev:** "Should the LinkedIn plan call the knowledge-base review workflow?"
> **Domain expert:** "No. This is a **Marketing Plan Review**. It should check the campaign plan and give suggestions, not change formal knowledge."
>
> **Dev:** "Which tool performs that review?"
> **Domain expert:** "Use the dedicated `tuolin-linkedin-marketing-review` skill for the campaign plan."
>
> **Dev:** "After accepting the review suggestions, should we create another plan-finalization step?"
> **Domain expert:** "No. Apply accepted suggestions directly when generating the Chinese 30-day draft, and record the review source there."
>
> **Dev:** "Can a user skip marketing review?"
> **Domain expert:** "Yes. Marketing review is optional and should not block the original manual confirmation flow."
>
> **Dev:** "Should the campaign generator create all 30 publishing images at once?"
> **Domain expert:** "No. Each publishing image must be generated on demand for a specific day, using that day's content theme, tags, and source image."
>
> **Dev:** "When the user asks for a Day 01 publishing image, should we generate immediately?"
> **Domain expert:** "No. First show a **Publishing Image Selection Sheet** and wait for the user to choose one to three style categories."
>
> **Dev:** "Where should generated Day 01 image variants live?"
> **Domain expert:** "Save them under `Manual-Posting-Package/Day 01/Publish-Images/<category-slug>/`; do not add source-info or prompt files unless we later need traceability artifacts."
>
> **Dev:** "If the user selects three style categories, how many images should we generate?"
> **Domain expert:** "Generate one image per selected category, so at most three images in one request."
>
> **Dev:** "Can a scenario-style image be generated from a plain white-background product image?"
> **Domain expert:** "No. Use the day's real source image. If the source image does not support the chosen scenario, ask for a better source instead of inventing one."
>
> **Dev:** "Should the image generator automatically resize images based on style category?"
> **Domain expert:** "No. Keep the source image dimensions by default and only provide size recommendations unless the user explicitly chooses another size."
>
> **Dev:** "Should unsuitable style categories be hidden?"
> **Domain expert:** "No. Show all 20 primary categories, recommend three, and warn when a category does not fit the day's source image or theme."
>
> **Dev:** "After the user chooses a style, do we hand them a prompt?"
> **Domain expert:** "No. Codex should use the style prompt internally and call the image model directly."
>
> **Dev:** "When the user asks to copy the 30-day plan to Desktop, is Desktop the source of truth?"
> **Domain expert:** "No. It is a **Desktop Delivery Copy** for boss review and manual operation; the canonical campaign folder remains unchanged."
>
> **Dev:** "Should the video workflow create a master before choosing a language?"
> **Domain expert:** "No. Ask the user to choose the Chinese or English **Video Language Version** first, then produce that version directly."
>
> **Dev:** "Can an English video retain Chinese narration or omit English subtitles?"
> **Domain expert:** "No. Its narration and subtitles must both be English; the Chinese version follows the same rule in Chinese."
>
> **Dev:** "Should we offer the 20 LinkedIn image styles as video categories?"
> **Domain expert:** "No. Those belong to publishing images. Recommend and confirm a separate **Video Creative Direction** before video planning."
>
> **Dev:** "Can the workflow show only the three directions it recommends?"
> **Domain expert:** "No. Show the complete fixed taxonomy and clearly mark the dynamically recommended options within it."
>
> **Dev:** "How many fixed creative directions does the first quartz-fiber-tape workflow expose?"
> **Domain expert:** "Expose all 16 confirmed directions. Add new ones later only when the existing taxonomy cannot express a required video."
>
> **Dev:** "Can one video combine several equal creative directions?"
> **Domain expert:** "No. Confirm one primary direction and optionally one supporting direction so the narrative remains focused."
>
> **Dev:** "How many dynamic direction recommendations should the user see?"
> **Domain expert:** "Show three ranked combinations with rationale, material coverage, missing materials, and AI-generation risk, alongside all 16 fixed directions."
>
> **Dev:** "Should creative direction be chosen before the video language?"
> **Domain expert:** "No. Confirm language first because it affects audience expression, narration rhythm, and direction recommendations."
>
> **Dev:** "Can the initial workflow accept an arbitrary video duration?"
> **Domain expert:** "No. Offer 60, 90, or 120 seconds, defaulting to 60 seconds."
>
> **Dev:** "Does the first version need to support standard YouTube videos or LinkedIn?"
> **Domain expert:** "No. Target YouTube Shorts and TikTok only."
>
> **Dev:** "Should TikTok and YouTube Shorts use separate aspect ratios?"
> **Domain expert:** "No. Use 9:16 for both."
>
> **Dev:** "Does selecting both platforms require two video files?"
> **Domain expert:** "No. Record both targets and use the same 9:16 deliverable."
>
> **Dev:** "Which platform safe area applies when both targets are selected?"
> **Domain expert:** "Use the intersection of both safe areas so one render remains readable on each platform."
>
> **Dev:** "Should the video workflow also prepare TikTok and Shorts post copy?"
> **Domain expert:** "No. Deliver the video only; a later publishing skill owns publishing metadata and copy."
>
> **Dev:** "Should a 120-second request be split into several short videos?"
> **Domain expert:** "No. Produce one complete 120-second video; series splitting is outside the initial scope."
>
> **Dev:** "Do we need to define workshop-video directions in the first version?"
> **Domain expert:** "No. First define and implement directions only for **Quartz Fiber Tape Video Scope**."
>
> **Dev:** "Should the video agent hard-code the product's Chinese and English external names?"
> **Domain expert:** "No. Product naming is owned by the **Knowledge Producer** and must be consumed from the published knowledge cards."
>
> **Dev:** "Should complete video production continue using `video_script`?"
> **Domain expert:** "No. Rename the task context to **Video Creation Context** because the workflow produces a complete video, not only a script."
>
> **Dev:** "Should users invoke the Dreamina runner after confirming prompts?"
> **Domain expert:** "No. Keep `tuolin-video-workflow` as the single natural-language entrypoint and call the runner internally."
>
> **Dev:** "Should narration and music providers be exposed as separate user skills?"
> **Domain expert:** "No. Keep them behind the video workflow and expose only business choices and previews."
>
> **Dev:** "Must we choose narration and music vendors before defining the workflow?"
> **Domain expert:** "No. Define provider-neutral adapter contracts first and select replaceable providers during implementation."
>
> **Dev:** "Can the initial video consumer search broadly for additional product or asset cards?"
> **Domain expert:** "No. Read the quartz-fiber-tape product card and its explicitly related content assets only."
>
> **Dev:** "Should video runs live in a separate external output root?"
> **Domain expert:** "No. Store them with application-layer reports under `generated/reports/video-creation/`."
>
> **Dev:** "Can a completed video run discard intermediate files?"
> **Domain expert:** "No. Retain the decision records and generated assets needed for audit and shot-level regeneration."
>
> **Dev:** "Should an active video run handle knowledge changes automatically?"
> **Domain expert:** "No. Organize the knowledge base before starting video creation; mid-run knowledge revision handling is outside the initial scope."
>
> **Dev:** "Can video creation continue by reading raw files when the knowledge interface is missing?"
> **Domain expert:** "No. Stop and ask the user to organize the quartz-fiber-tape knowledge first."
>
> **Dev:** "Can the user verbally approve a new performance claim only for this video?"
> **Domain expert:** "No. Put new facts through the knowledge producer first; only creative wording preferences may remain task-local."
>
> **Dev:** "Can Dreamina invent an application scene when no real footage exists?"
> **Domain expert:** "Yes, but only for a formally confirmed application, with clear generated-asset traceability and no implication that it is a real case or test."
>
> **Dev:** "Should text-to-video be used whenever it gives a more cinematic result?"
> **Domain expert:** "No. Preserve real product and application materials first and descend through the fixed fallback order only when necessary."
>
> **Dev:** "Can a text-only prompt generate the product itself?"
> **Domain expert:** "No. Any visible product must be grounded in real product imagery."
>
> **Dev:** "Should the initial workflow default to 720P to reduce cost?"
> **Domain expert:** "No. Use premium `seedance2.0_vip` generation at 1080P and show the estimated credit use before submission."
>
> **Dev:** "Must every Dreamina shot be exactly five seconds?"
> **Domain expert:** "No. Five seconds is the default; use four to fifteen seconds as needed, normally staying within four to eight seconds."
>
> **Dev:** "Can an overlong render be delivered by cutting off the narration?"
> **Domain expert:** "No. Keep the final duration within the selected ±5-second tolerance by revising the narration or shots."
>
> **Dev:** "Must every video end with an inquiry request?"
> **Domain expert:** "No. Require it for inquiry-conversion videos and use it selectively elsewhere, with details sourced from knowledge or configuration."
>
> **Dev:** "Must the user prepare a narration WAV before assembly?"
> **Domain expert:** "No. The video workflow generates narration in the selected language and passes it to assembly."
>
> **Dev:** "Must the user choose background music manually?"
> **Domain expert:** "No. Select music automatically according to the creative direction."
>
> **Dev:** "Can the workflow copy a popular TikTok track into the delivered video?"
> **Domain expert:** "No. Embed commercially usable music with a matching style instead."
>
> **Dev:** "Can planning claim that background music is complete after writing a style description?"
> **Domain expert:** "No. A provider adapter must return a usable track with source and licensing metadata before the video is complete."
>
> **Dev:** "Must the user approve music before visual generation?"
> **Domain expert:** "No. Review it in the final preview; replacing it only requires remixing and reassembly."
>
> **Dev:** "Can Dreamina CLI generate the complete narration and music package?"
> **Domain expert:** "No. Use separate narration and music provider adapters, then assemble their outputs with the generated visuals."
>
> **Dev:** "Can the workflow choose a narration voice silently?"
> **Domain expert:** "No. Recommend three samples and let the user select one before generating the complete narration."
>
> **Dev:** "Should voice samples be generated before the narration text is approved?"
> **Domain expert:** "No. Follow `确认分镜 → 确认旁白文案 → 声音选择 → 完整试听 → 确认旁白`."
>
> **Dev:** "Should the three samples use different scripts?"
> **Domain expert:** "No. Use the same 8-12 second narration excerpt and vary only voices that fit the selected language profile."
>
> **Dev:** "Should the Chinese version imitate a Western accent?"
> **Domain expert:** "No. Use a natural, fluent middle-aged male Chinese voice; reserve the Western male profile for English."
>
> **Dev:** "Should we generate all visual clips before anyone hears the narration?"
> **Domain expert:** "No. Generate and confirm the complete narration first, then use its timing to drive visual generation."
>
> **Dev:** "Does changing one narration sentence preserve the previous confirmation?"
> **Domain expert:** "No. Regenerate the preview and require `确认旁白` again."
>
> **Dev:** "Can Dreamina jobs be submitted immediately after narration confirmation?"
> **Domain expert:** "No. First show the job plan and estimated credit use, then wait for `确认即梦生成`."
>
> **Dev:** "Does one bad generated shot require regenerating the whole video?"
> **Domain expert:** "No. Authorize and regenerate only that shot while preserving accepted shots."
>
> **Dev:** "Should final music and subtitle rendering happen before the user checks the generated shots?"
> **Domain expert:** "No. First provide a narration-led shot preview with temporary subtitles; continue to final assembly only after `确认镜头`."
>
> **Dev:** "Can a technically valid render automatically complete the workflow?"
> **Domain expert:** "No. The user must watch the final preview and say `确认成片`."
>
> **Dev:** "Should the confirmed output still be named a master?"
> **Domain expert:** "No. Use the language-specific quartz-fiber-tape filename and reserve explicit preview names for intermediate renders."
>
> **Dev:** "Should subtitles be delivered as a track viewers can disable?"
> **Domain expert:** "No. Burn them into the picture so they are visible by default on TikTok and YouTube Shorts."
>
> **Dev:** "Should subtitles highlight every spoken word?"
> **Domain expert:** "No. Show one or two lines per sentence, synchronize them to sentence timing, and keep them clear of platform UI."
>
> **Dev:** "Must the final video prohibit all text except subtitles?"
> **Domain expert:** "No. Allow controlled titles, confirmed parameters, short benefit labels, and calls to action."
>
> **Dev:** "Should the logo remain visible throughout the video?"
> **Domain expert:** "No. Use the configured transparent logo once at the end; warn but continue if it is unavailable."
>
> **Dev:** "Can a final preview be produced when the audio track is missing?"
> **Domain expert:** "No. Repair blocking quality defects first; present non-blocking warnings to the user with the preview."
>
> **Dev:** "Should an interrupted video run restart from requirement collection?"
> **Domain expert:** "No. Restore `workflow_state.json` and continue from the current pending confirmation."
>
> **Dev:** "Can automated audiovisual checks approve the final video on behalf of the user?"
> **Domain expert:** "No. Automation reports synchronization and rendering issues; the user confirms the final preview."

## Flagged Ambiguities

- "审阅" was used for both marketing campaign quality review and knowledge-base fact review. Resolved: use **Marketing Plan Review** for LinkedIn campaign planning and **Knowledge Review** for formal knowledge-base review items.
- “母版” previously referred inconsistently to silent and narrated outputs. Resolved: remove the term and use **Video Language Version**.
- “创意类型” was initially illustrated with the 20 publishing image styles. Resolved: video uses the separate term **Video Creative Direction**.
- Product external names were considered as video-workflow constants. Resolved: they are knowledge owned by the **Knowledge Producer**, not by the video consumer.
- `video_script` was initially retained as the video task-context name. Resolved: rename it to `video_creation` to match the complete production responsibility.
