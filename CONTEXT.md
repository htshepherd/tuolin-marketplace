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
A user-selected Chinese or English video-creation run whose product naming and Dreamina prompts use the selected output language, while the Chinese operator may review the interview, plan summary, storyboard explanation, risks, and modification guidance in Chinese. Voiceover, subtitles, and background music are added outside the current video Agent.
_Avoid_: base master, visual master, final master

**Video Creation Interview**:
A one-question-at-a-time conversation that helps a non-professional user express the video's business goal, audience, desired viewer response, material preferences, and creative constraints before planning begins.
_Avoid_: fixed creative-direction menu, director terminology, asking the user to design the storyboard

**Confirmed Video Brief**:
The complete set of user answers and accepted Agent recommendations produced by the **Video Creation Interview** and used as the direct input to the video plan.
_Avoid_: fixed direction ID, hidden taxonomy, unconfirmed Agent assumptions

**Interview Recommendation**:
One concise, evidence-based recommended answer presented with each unresolved interview question so the user may accept it by replying “按推荐” or provide a different answer.
_Avoid_: option overload, unexplained recommendation, unsupported creative assumption

**Remaining Interview Delegation**:
An explicit user instruction such as “剩下都按推荐” or “你来决定并直接出策划” that accepts all unresolved **Interview Recommendations** and authorizes immediate plan generation.
_Avoid_: treating a short answer or one “按推荐” reply as blanket authorization

**Core Video Brief Information**:
The minimum business information that must be resolved before the **Video Creation Interview** can end: audience, intended takeaway, desired viewer action, priority product messages, preferred balance between product and application visuals, and excluded content.
_Avoid_: fixed questionnaire order, director terminology, information already supplied by the user

**Professional Video Decisions**:
Shot count, timing, image assignment, camera movement, pacing, sequence, visual-generation mode, repetition control, and Dreamina prompt design owned by the Agent and reviewed later through the plan and storyboard.
_Avoid_: asking a non-professional user to direct or edit the video during the interview

**External Video Generation Skill Internalization**:
The conversion of external Seedance/Dreamina skill methods into Tuolin-owned prompt, shot-validation, execution, and quality-gate rules.
_Avoid_: copying external code, importing entertainment categories, bypassing knowledge-card facts

**Video Planning Quality Criteria**:
Checks for hook, visual focus, message focus, material suitability, shot diversity, claim safety, and viewer action derived from the **Confirmed Video Brief** and formal product knowledge.
_Avoid_: fixed creative-direction taxonomy, one generic cinematic score, unsupported creative assumptions

**Industrial Visual Quality Gate**:
The automated planning and Dreamina-job gate that checks industrial-product planning quality, real-image references, structured prompts, job validation, repeated image references, and shot-review readiness.
_Avoid_: automatic creative approval, platform-restricted-word module detached from knowledge facts

**Frame Continuity Upgrade**:
A video-quality upgrade that improves shot-to-shot flow by planning stable reference frames, transition intent, and continuity checks before Dreamina generation.
_Avoid_: audio automation, Jianying automation, treating "Hyperframes" as a confirmed installed provider

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

**New Video Task**:
A request to create another video deliverable, which always creates a new isolated **Video Creation Run** directory even when product, language, platform, or duration match a previous task.
_Avoid_: reusing the latest run directory, mixing artifacts from separate videos

**Visual Storyboard**:
The user-confirmed shot list that shows each shot's visual intent, selected image reference, local image path, inline thumbnail, material role, and risk notes before any paid Dreamina generation.
_Avoid_: text-only shot list, hidden image selection, confirming only after generation

**Plan Representative Images**:
Three to six available material images shown with the video-plan summary to communicate the proposed overall visual treatment before exact shot-to-image binding.
_Avoid_: full material dump, pretending a representative image is already locked to a shot

**Visually Inspected Candidate Image**:
A formal content-asset image whose actual pixels have been reviewed for subject, scene, clarity, composition, aspect-ratio suitability, and visual duplication before it may appear in a plan or storyboard.
_Avoid_: selecting by filename, title, tag, or path alone; treating visible appearance as performance evidence

**Material-Supported Duration**:
The longest coherent video duration that the inspected image set can support without unapproved repetition, fabricated product appearance, or filler shots.
_Avoid_: forcing the requested duration when the available visuals cannot sustain it

**Shot Image Override**:
A user-provided local image path used to replace the selected image reference for a specific storyboard shot.
_Avoid_: adding a new product fact, bypassing product-knowledge claims, replacing all shots accidentally

**Dreamina Shot Plan**:
The final pre-submission plan that maps each confirmed storyboard shot to a Dreamina task, prompt, image reference, expected credit use, and manual submission command.
_Avoid_: paid submission, final edited video, audio/subtitle package

**Shot Review**:
The user review of generated Dreamina clips for acceptance into the current video result or handoff to a separate improvement workflow.
_Avoid_: returning to unconfirmed planning, editing the locked storyboard, treating improvement as part of initial creation

**Video Result Improvement Workflow**:
A future, out-of-scope post-generation workflow for improving an unsatisfactory generated clip or assembled video while preserving the completed initial creation run.
_Avoid_: rewinding the initial planning state, silently replacing accepted generation records

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
- A Chinese **Video Language Version** uses Chinese product naming, Chinese planning copy, and Chinese review text where applicable.
- An English **Video Language Version** uses the formal English product name and English Dreamina prompts, while the Codex interview and user-review summaries remain in Chinese for a Chinese operator.
- Chinese interview terminology, creative notes, and review labels must not leak into English Dreamina prompts or target-language content.
- One video production run produces only the **Video Language Version** confirmed by the user.
- Every video production run must complete a **Video Creation Interview** before the formal video plan is generated.
- The **Video Creation Interview** replaces fixed creative-direction selection; the video workflow has no fixed direction taxonomy, primary direction, supporting direction, or ranked direction combinations.
- Interview questions use ordinary business language and must not require the user to understand directing, shot design, or creative-category terminology.
- The interview is adaptive rather than a fixed questionnaire: it extracts answers already present in the user's request and asks only for unresolved **Core Video Brief Information**.
- Production cost versus visual richness is not required **Core Video Brief Information**. Record it only when the user raises it; otherwise the Agent uses available real images efficiently without adding a budget question.
- Language, platform, duration, audience, or other information already supplied by the user must not be asked again.
- The Agent inspects formal knowledge and available image materials itself; it does not ask the user to judge professional material sufficiency or shot feasibility.
- The interview asks only for business intent that the user can reasonably judge; all **Professional Video Decisions** are made by the Agent after the brief is complete.
- **Professional Video Decisions** must be visible in the plan or storyboard and remain revisable through natural-language feedback before paid generation.
- The interview ends only when all **Core Video Brief Information** is resolved or the user explicitly accepts an Agent recommendation for an unresolved item.
- Every unresolved question includes exactly one **Interview Recommendation** with a short reason based on the current request, formal knowledge, available images, platform, audience, and duration.
- Users may answer freely or reply “按推荐”; accepting a recommendation records that recommendation as an explicit user-approved brief decision.
- “按推荐” accepts only the current question; the Agent continues with the next unresolved item.
- Only an explicit **Remaining Interview Delegation** may accept all unresolved recommendations and end the interview immediately.
- Every delegated recommendation is still recorded in the **Confirmed Video Brief** and summarized in the generated plan.
- Interview questions must not present a long menu of creative options or shift professional planning work back to the user.
- Each user answer and accepted Agent recommendation becomes part of the **Confirmed Video Brief**.
- Completing the interview does not create a separate brief-confirmation gate. The workflow automatically generates the video plan, and `确认策划` confirms both the interpreted brief and the proposed plan.
- The complete interview decisions remain recorded in the run artifacts even though the user is not asked to confirm a separate interview-summary document.
- There is one **Video Creation Interview** per run. After `确认策划`, the workflow generates the **Visual Storyboard** without starting a second storyboard interview.
- Storyboard generation may ask a new question only when a required visual has no usable material or safe generation path, a requested claim conflicts with formal knowledge, or two materially different choices cannot be resolved from the **Confirmed Video Brief**.
- The **Confirmed Video Brief**, formal product knowledge, and available image materials are the direct inputs to planning and storyboard generation.
- Material metadata may narrow the candidate set, but every **Plan Representative Image** and storyboard reference must be a **Visually Inspected Candidate Image**.
- Visual inspection classifies presentation use such as product roll, woven detail, wrapped pipe, installation, or test scene and checks clarity, composition, 9:16 suitability, and near-duplicate content.
- If the pixels and card metadata disagree, the pixels control visual-use classification, but neither source may create a new product-performance fact.
- Before generating the plan, the Agent compares the requested duration with the **Material-Supported Duration**.
- When inspected images cannot support the requested duration, the Agent recommends a shorter duration in ordinary language instead of silently repeating similar images or fabricating the product.
- A confirmed application may use an explicitly recorded AI-simulated environment or transition, but generated visuals must not masquerade as a real case or replace the required real-product reference.
- Reusing the same or near-duplicate image as a deliberate treatment requires explicit user approval and remains visibly marked in the storyboard.
- The Codex response for a generated plan must show a concise business-readable plan and three to six **Plan Representative Images**; the full plan is still written to the run Markdown and JSON artifacts.
- **Plan Representative Images** communicate the overall visual approach but do not become confirmed shot assignments.
- Returning only a plan or storyboard file path is not a sufficient user-facing result; the workflow step result must carry the concise review content and renderable run-local image references directly into the Codex conversation.
- **External Video Generation Skill Internalization** is a bottom-layer enhancement of prompt writing, shot validation, execution reliability, references organization, continuity, and quality gates; it does not create a hidden creative taxonomy.
- `dexhunter/seedance2-skill` is internalized as Seedance/Dreamina prompt grammar and structure, not as a business taxonomy source.
- The **Video Planning Quality Criteria** must be applied to the **Confirmed Video Brief** and carried through plan, storyboard, prompt generation, Dreamina job planning, and quality checks.
- The current upgrade focuses on **Frame Continuity Upgrade** and intentionally does not add TTS, BGM, subtitle, or Jianying automation.
- The term "Hyperframes" is treated as a possible implementation inspiration for frame continuity, not as a confirmed dependency, until a specific open-source/free project is selected.
- The workflow order is: identify a quartz-fiber-tape video request; confirm the **Video Language Version** and known request facts; complete the **Video Creation Interview**; generate and confirm the formal video plan; generate and confirm the **Visual Storyboard**; generate the **Dreamina Shot Plan**; hand off paid Dreamina submission; query results; then complete **Shot Review**.
- A formal video plan must not be generated before the **Video Creation Interview** produces a complete **Confirmed Video Brief**.
- After the interview is complete, the workflow generates the formal video plan automatically; the user should not have to issue a separate "生成策划" command unless they explicitly want manual control.
- After the user confirms the formal video plan, the workflow may generate the **Visual Storyboard** automatically; the user should not have to issue a separate "生成分镜" command unless they explicitly want manual control.
- After the user confirms the **Visual Storyboard**, the workflow may generate the **Dreamina Shot Plan** automatically; the user should not have to issue a separate "规划即梦任务" command unless they explicitly wants manual control.
- The user-facing video workflow keeps confirmation gates for the plan, visual storyboard, Dreamina paid generation, and shot review, but has no separate creative-direction confirmation gate.
- The initial workflow supports only 60-, 90-, and 120-second videos; 60 seconds is the default.
- The initial workflow targets YouTube Shorts and TikTok only; standard horizontal YouTube videos and other platforms are outside the initial scope.
- All initial YouTube Shorts and TikTok deliverables use a 9:16 vertical aspect ratio; the workflow does not maintain platform-specific framing variants.
- A run may target TikTok, YouTube Shorts, or both.
- When both platforms are selected, they share one 9:16 deliverable; the workflow records both targets but does not render duplicate platform files.
- For multi-platform runs, visual composition should preserve the intersection of TikTok and YouTube Shorts safe areas.
- The initial video workflow does not generate platform titles, post copy, descriptions, or hashtags; those belong to a later publishing skill.
- Each 60-, 90-, or 120-second run produces one complete video; the initial workflow does not split longer videos into a series.
- The **Knowledge Producer** supplies formal product knowledge to both the LinkedIn consumer and the **Video Creation Consumer**.
- The LinkedIn consumer and **Video Creation Consumer** are separate application scenarios with separate workflows and outputs.
- The **Video Creation Consumer** must read Chinese and English external product names from published knowledge cards instead of defining them itself.
- The **Video Creation Consumer** uses **Video Creation Context** as its only task-specific knowledge entrypoint.
- **Video Creation Context** supports the full workflow from the **Video Creation Interview** through Dreamina shot generation and shot review.
- **Video Workflow Entrypoint** is the only user-facing video skill.
- The one-question-at-a-time interview method is owned by **Video Workflow Entrypoint** itself; users do not install or invoke a separate `grill-me` skill, and no second Agent owns the video run.
- Dreamina submission is represented as a safe manual handoff when the Agent environment cannot perform paid external submission directly.
- The user should not need to copy internal script parameters; when manual execution is required, the workflow provides a single PowerShell command.
- The working Dreamina CLI submission, manual-submission JSON, resumable PowerShell handoff, result query, and download path are stable execution infrastructure; upstream workflow improvements must not casually modify this execution path.
- The initial **Video Creation Context** is requested only for the quartz-fiber-tape product identified from the user's natural-language video request.
- The initial **Video Creation Context** contains the quartz-fiber-tape product card and only the content-asset cards explicitly related to that product.
- The initial video consumer does not expand retrieval through keyword search and does not read knowledge for other products.
- Each **Video Creation Run** is stored at `generated/reports/video-creation/{timestamp}_quartz_fiber_tape_{zh|en}/`.
- Every **New Video Task** creates its own timestamped **Video Creation Run** directory; plan, storyboard, prompts, Dreamina records, generated clips, and assembly files from separate tasks must never be mixed.
- Test-stage runs created before the **Video Creation Interview** change do not require migration; validation starts with a new conversation and a new run.
- A **Video Creation Run** is an application-layer deliverable and must not be written into the formal knowledge layer or raw archive.
- A **Video Creation Run** retains requirements and direction decisions, plan, visual storyboard, prompts, Dreamina shot plan, manual submission records, generated shot files, shot-review state, workflow state, and change log.
- Video creation run directories support audit and exact task continuation and must not be treated as disposable indexes merely because they live under `generated/reports/`.
- Video creation requires the knowledge base to be organized and its Agent interface to be available before a run starts.
- The initial workflow does not monitor or switch knowledge revisions during an active run.
- If the quartz-fiber-tape knowledge or Agent interface is unavailable, the video consumer stops and routes the user to organize the product through the knowledge producer first.
- The video consumer does not organize knowledge, scan raw, or bypass the formal interface with ad hoc facts.
- User-provided wording preferences may influence creative treatment, but task-specific product facts, parameters, performance claims, or promises that are absent from formal knowledge cannot enter a video.
- New product facts must be confirmed and published through the knowledge producer before video creation uses them; the video consumer has no one-run fact exception.
- The video workflow uses formal knowledge-card text and image content assets; knowledge-base video files are not used for planning or Dreamina task generation in the current scope.
- When real application imagery is unavailable, Dreamina may generate a simulated application scene only for applications confirmed by formal knowledge.
- AI-generated scenes must be identified as generated in the run record and must not be represented as a real customer case, real test record, or product-performance evidence.
- Generated scenes must not introduce unsupported equipment details, parameters, applications, or performance outcomes.
- Shot material selection follows this strict fallback order: real product image animated into video, real application image animated into video, AI-simulated scene, then text-only generated video.
- A lower-priority material mode is used only when higher-priority modes cannot satisfy the shot.
- Any generated shot that visibly contains the product must use real product or real application imagery as an image-to-video visual reference.
- A **Visual Storyboard** must show each selected image as an inline thumbnail or preview, not only as a local path or content-asset ID.
- The Codex response for a generated **Visual Storyboard** must show every shot's number, time range, purpose, visual action, exact reference image, and original source path in concise user-facing language.
- Repeated image references must be marked directly in the Codex storyboard response before the user confirms the storyboard.
- A **Visual Storyboard** should copy each selected reference image into the run directory, render that run-local copy as a Markdown image preview, and still display the original absolute source path for traceability.
- Run-local storyboard image previews improve review reliability for Windows paths, Chinese filenames, spaces, and Markdown renderers without changing the stable Dreamina CLI submission path.
- A **Visual Storyboard** must make repeated image references visible before paid Dreamina submission.
- Accidental repeated image references across multiple paid Dreamina shots should block confirmation unless the user explicitly approves the repetition as a deliberate visual choice.
- Users may revise the **Visual Storyboard** with natural language, including deleting shots, shortening the shot list, changing shot order, or replacing a specific shot's image.
- A **Shot Image Override** may use a local image path supplied directly in the Codex conversation, but it only changes the visual reference for that shot; it does not create or approve new product facts.
- When a user supplies a **Shot Image Override** before storyboard confirmation, the workflow should validate that the file exists, is an image type supported by Dreamina, and does not introduce clear-face or unsupported-claim risk before updating the storyboard and prompts.
- Before storyboard confirmation, users may freely replace shot images, delete shots, reorder shots, or revise shot intent; no **Dreamina Shot Plan** exists yet.
- Confirming the **Visual Storyboard** locks its shot structure and image assignments, then creates the **Dreamina Shot Plan** for separate confirmation and submission.
- After real generation, dissatisfaction does not reopen the initial planning or storyboard flow; it enters a **Video Result Improvement Workflow**.
- Text-only video generation is allowed only for environmental or transitional shots that do not depict the specific product.
- Dreamina generation defaults to `seedance2.0_vip` at 1080P because the operating account has premium access.
- Dreamina clips use 9:16 1080 by 1920 pixels unless the user explicitly chooses another supported configuration.
- **Dreamina Shot Plan** review displays estimated credit use before paid submission.
- Generated shots default to five seconds, may range from four to fifteen seconds, and should normally remain within four to eight seconds for short-form pacing.
- A 60-second run should plan roughly twelve five-second shots unless the user deletes or merges shots.
- If the user deletes shots before storyboard confirmation, the workflow should show the new estimated total duration before the storyboard can be confirmed.
- Users may intentionally shorten a video below the original duration target by deleting shots. If the new duration materially deviates from the original target, the workflow must surface the new estimated duration and ask whether to accept the shorter target or add replacement shots before paid generation.
- When the **Confirmed Video Brief** requires a viewer action, the plan must include a matching call to action; otherwise the Agent may propose a light call to action for the user to confirm.
- Call-to-action details must come from formal knowledge or project configuration and must not be hard-coded in the video skills.
- Before submission, the user reviews job type, selected image, image thumbnail, duration, and estimated credit use.
- Paid visual-generation jobs are submitted only after the user says `确认即梦生成`.
- After all visual jobs finish, the workflow records the generated shot results for **Shot Review**.
- The user may accept the generated result or request a separate **Video Result Improvement Workflow** from **Shot Review**.
- **Video Result Improvement Workflow** is not implemented in the current release. If the user rejects generated quality, the current workflow records the result as not accepted and stops without changing the original run.
- The command `确认镜头` locks the accepted Dreamina clips and marks the video-creation run complete.
- Audio, subtitles, BGM, logos, final editing, publishing titles, post copy, descriptions, and hashtags are outside the current video Agent and belong to manual editing or later publishing workflows.
- A **Video Creation Run** persists its current workflow phase and confirmations in `workflow_state.json`.
- Resuming a run restores the latest valid phase and asks only for the current pending confirmation instead of restarting or repeating locked work.
- Automated checks may inspect Dreamina shot planning and generated-shot availability, but they do not replace the user's **Shot Review** confirmation.

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
> **Domain expert:** "No. Ask the user to choose the Chinese or English **Video Language Version** first. The current Agent generates Dreamina video shots for that version; voiceover and subtitles are outside this Agent."
>
> **Dev:** "Should we ask the user to choose from fixed video categories before planning?"
> **Domain expert:** "No. Complete a **Video Creation Interview** in ordinary business language and use the resulting **Confirmed Video Brief** directly."
>
> **Dev:** "Can the Agent keep the old 16 directions as a hidden internal taxonomy?"
> **Domain expert:** "No. Remove the fixed taxonomy completely; it is neither necessary nor accurate for real users."
>
> **Dev:** "Should every video user answer the same questionnaire?"
> **Domain expert:** "No. Extract what the user already said, then ask one question at a time until all **Core Video Brief Information** is resolved."
>
> **Dev:** "What if the user does not know how to answer a creative question?"
> **Domain expert:** "Give one justified **Interview Recommendation** and let the user reply ‘按推荐’."
>
> **Dev:** "Should the user confirm the interview summary before planning?"
> **Domain expert:** "No. Generate the plan when the brief is complete, then let `确认策划` confirm the interpreted brief and plan together."
>
> **Dev:** "Do we run another interview before generating the storyboard?"
> **Domain expert:** "No. Generate it after plan confirmation and ask only when a real material, knowledge, or unresolved-choice blocker appears."
>
> **Dev:** "Does one ‘按推荐’ authorize every remaining decision?"
> **Domain expert:** "No. It accepts the current recommendation only; blanket delegation requires explicit wording such as ‘剩下都按推荐’."
>
> **Dev:** "Should the interview ask the user how many shots to use or which camera move to choose?"
> **Domain expert:** "No. Those are **Professional Video Decisions** owned by the Agent and reviewed later in the plan and storyboard."
>
> **Dev:** "Can the initial workflow accept an arbitrary video duration?"
> **Domain expert:** "No. Offer a controlled set of short-video durations: 15, 20, 30, 45, 60, 90, or 120 seconds, defaulting to 60 seconds."
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
> **Domain expert:** "Use the intersection of both safe areas so one 9:16 visual output remains usable on each platform."
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
> **Dev:** "Should video production continue using `video_script`?"
> **Domain expert:** "No. Rename the task context to **Video Creation Context** because the workflow plans and generates Dreamina video shots, not only a script."
>
> **Dev:** "Should users invoke a separate Dreamina runner skill after confirming prompts?"
> **Domain expert:** "No. Keep `tuolin-video-workflow` as the single natural-language entrypoint. If paid submission must happen locally, hand off one safe PowerShell command."
>
> **Dev:** "Can upstream user-flow improvements rewrite the working Dreamina CLI submission code?"
> **Domain expert:** "No. Treat the current CLI submission, resumable handoff, submit-id recording, query, and download behavior as stable infrastructure unless a specific execution bug is being fixed."
>
> **Dev:** "Can the initial video consumer search broadly for additional product or asset cards?"
> **Domain expert:** "No. Read the quartz-fiber-tape product card and its explicitly related content assets only."
>
> **Dev:** "Should video runs live in a separate external output root?"
> **Domain expert:** "No. Store them with application-layer reports under `generated/reports/video-creation/`."
>
> **Dev:** "Can a completed video run discard intermediate files?"
> **Domain expert:** "No. Retain the interview decisions, plan, storyboard, generation records, and generated assets needed for audit."
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
> **Dev:** "Can the video workflow use knowledge-base video files for planning or Dreamina generation?"
> **Domain expert:** "No. In the current scope, use formal knowledge-card text and image content assets only."
>
> **Dev:** "Can Dreamina invent an application scene when no real application image exists?"
> **Domain expert:** "Yes, but only for a formally confirmed application, with clear generated-asset traceability and no implication that it is a real case or test."
>
> **Dev:** "Should text-to-video be used whenever it gives a more cinematic result?"
> **Domain expert:** "No. Preserve real product and application materials first and descend through the fixed fallback order only when necessary."
>
> **Dev:** "Can a text-only prompt generate the product itself?"
> **Domain expert:** "No. Any visible product must be grounded in real product or application imagery."
>
> **Dev:** "Should the initial workflow default to 720P to reduce cost?"
> **Domain expert:** "No. Use premium `seedance2.0_vip` generation at 1080P and show the estimated credit use before submission."
>
> **Dev:** "Must every Dreamina shot be exactly five seconds?"
> **Domain expert:** "No. Five seconds is the default; use four to fifteen seconds as needed, normally staying within four to eight seconds."
>
> **Dev:** "Can a 60-second run become shorter if the user deletes shots?"
> **Domain expert:** "Yes, but show the new estimated total duration before the storyboard is confirmed and before any **Dreamina Shot Plan** exists."
>
> **Dev:** "Must every video end with an inquiry request?"
> **Domain expert:** "No. Follow the desired viewer action in the **Confirmed Video Brief** and source any call-to-action details from knowledge or configuration."
>
> **Dev:** "Can the user confirm a storyboard if it only lists local paths?"
> **Domain expert:** "No. The **Visual Storyboard** must show inline image previews for each selected shot image."
>
> **Dev:** "Should storyboard previews link directly to raw Windows paths?"
> **Domain expert:** "No. Copy the selected image into the run directory and render that copy in Markdown, while retaining the original absolute source path for traceability."
>
> **Dev:** "Can multiple Dreamina shots accidentally reuse the same image?"
> **Domain expert:** "No. Repeated image references must be visible and should block confirmation unless the user explicitly approves the repetition."
>
> **Dev:** "Can the user replace a shot image from the Codex conversation?"
> **Domain expert:** "Yes. Before storyboard confirmation, they can provide a local image path as a **Shot Image Override**; validate it before updating the storyboard and prompts."
>
> **Dev:** "Can the user freely replace shot images after confirming Dreamina generation?"
> **Domain expert:** "No. Replacement belongs before storyboard confirmation. After real generation, the initial run remains locked; post-generation improvement is outside the current release."
>
> **Dev:** "Can the user delete storyboard shots with natural language?"
> **Domain expert:** "Yes. Before storyboard confirmation, update the storyboard and prompts and show the revised duration; the Dreamina task plan is created only after confirmation."
>
> **Dev:** "Can a 60-second request become a 30-second video after shot deletion?"
> **Domain expert:** "Yes, if the user confirms the new shorter target. Do not silently treat a materially shorter video as still satisfying the original 60-second request."
>
> **Dev:** "Can Dreamina jobs be submitted immediately after storyboard confirmation?"
> **Domain expert:** "No. First show the **Dreamina Shot Plan**, selected image previews, and estimated credit use, then wait for `确认即梦生成`."
>
> **Dev:** "Should users have to say `生成策划`, `生成分镜`, or `规划即梦任务` during normal operation?"
> **Domain expert:** "No. After each confirmation, the workflow should generate the next artifact automatically and stop only at the next meaningful confirmation gate."
>
> **Dev:** "What happens when the user dislikes a generated result?"
> **Domain expert:** "Record it as not accepted and stop. A separate **Video Result Improvement Workflow** is outside the current release."
>
> **Dev:** "Should audio, subtitles, BGM, logos, and final editing happen inside this Agent?"
> **Domain expert:** "No. The current Agent assembles the confirmed visual clips and produces editing handoff files; audio, subtitles, BGM, logos, and final editing remain manual or owned by a later workflow."
>
> **Dev:** "Can technically valid Dreamina clips automatically complete the workflow?"
> **Domain expert:** "No. The user must review the generated shots and say `确认镜头`."
>
> **Dev:** "Should an interrupted video run restart from requirement collection?"
> **Domain expert:** "No. Restore `workflow_state.json` and continue from the current pending confirmation."

> **Dev:** "Can image filenames and tags alone determine which materials appear in the plan?"
> **Domain expert:** "No. Codex must actually open every shortlisted image and record subject, clarity, composition, vertical-crop suitability, and near-duplicates before showing the plan. This is an internal Agent checkpoint, not a user task."

> **Dev:** "What if the inspected distinct images cannot support the requested duration?"
> **Domain expert:** "Block plan confirmation until the user either shortens the target duration or explicitly approves deliberate image repetition. Only visually accepted images may enter the storyboard."

> **Dev:** "Is recording a natural-language plan or storyboard modification request enough?"
> **Domain expert:** "No. Codex must apply an actual controlled change to allowed artifact fields and show the revised result. Product identity, knowledge boundaries, format, source assets, and confirmation gates remain protected."

> **Dev:** "What state should a rejected generated result leave behind?"
> **Domain expert:** "Write a result-acceptance record, mark the run stopped, and direct the user to create a new task. Do not silently rewind or resubmit the confirmed storyboard."

## Flagged Ambiguities

- "审阅" was used for both marketing campaign quality review and knowledge-base fact review. Resolved: use **Marketing Plan Review** for LinkedIn campaign planning and **Knowledge Review** for formal knowledge-base review items.
- “母版” previously referred inconsistently to silent and narrated outputs. Resolved: remove the term and use **Video Language Version**.
- “创意方向” was previously modeled as 16 fixed categories with primary and supporting selections. Resolved: remove that taxonomy and use a **Video Creation Interview** to produce a **Confirmed Video Brief**.
- Product external names were considered as video-workflow constants. Resolved: they are knowledge owned by the **Knowledge Producer**, not by the video consumer.
- `video_script` was initially retained as the video task-context name. Resolved: rename it to `video_creation` to match the complete production responsibility.
