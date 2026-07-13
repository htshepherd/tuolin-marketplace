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
A user-selected Chinese or English video-creation run whose product naming, planned subtitle text, and Dreamina prompts use the selected output language, while the Chinese operator may review the interview, plan summary, storyboard explanation, risks, and modification guidance in Chinese. Voiceover and background music are added outside the current video Agent.
_Avoid_: base master, visual master, final master

**Video Creation Interview**:
A one-question-at-a-time creative discovery conversation grounded in the current product's published knowledge card and official images that helps a non-professional user clarify who should watch, why that audience would keep watching, which content angle is genuinely interesting to them, what they should remember or do afterward, and which creative boundaries the video must respect.
_Avoid_: fixed creative-direction menu, passive form filling, director terminology, asking the user to design the storyboard

**Creative Discovery Core**:
The primary video-Agent capability that investigates evidence, walks dependent creative decisions one at a time, challenges weak assumptions, and produces a decision-sufficient brief from which all later video artifacts are derived.
_Avoid_: treating interview quality as secondary to storyboard or prompt generation, a deterministic question list, a separate user-facing interview agent

**Viewer-Interest Direction**:
An evidence-based hypothesis about the subject, situation, tension, or presentation angle most likely to earn and hold the target audience's attention in the video's industrial-product context.
_Avoid_: fixed creative taxonomy, empty visual spectacle, treating an unsupported Agent guess as a confirmed audience preference

**Creative Strategy Challenge**:
A concrete explanation of why a requested creative choice may weaken audience interest or the business outcome, paired with one better alternative while preserving the user's final decision.
_Avoid_: passive compliance, taste-based rejection, silently overriding the user's choice

**Creative Strategy Inference**:
An explicitly identified creative judgment about audience motivation, viewing behavior, or content treatment derived from industrial-audience knowledge, platform patterns, public research when needed, and the current video context rather than from formal product facts.
_Avoid_: presenting an inference as a verified customer preference, using creative knowledge to invent product claims

**Video Interview Decision Sufficiency**:
The point at which all ambiguities that could materially change the video's audience value, business outcome, evidence use, or creative direction have been resolved, while professional execution choices remain owned by the Agent.
_Avoid_: completing a fixed question count, exploring every imaginable creative branch, asking the user to make shot-level decisions

**Actionable Video Audience**:
A target audience described only to the level needed to choose an effective viewing hook, content emphasis, evidence strategy, and viewer action for the current video.
_Avoid_: a broad market label with no creative implications, a full persona questionnaire, collecting demographics that do not change the video

**Audience Problem Scenario**:
A concrete situation, recurring customer question, or decision obstacle that reveals why the target audience would care about and continue watching the video.
_Avoid_: an abstract style preference with no viewer motivation, a fabricated customer case

**Short-Video Trend Mechanism**:
A reusable attention or storytelling principle extracted from recent high-performing short videos—such as a hook, tension, reveal, transformation, process payoff, or proof moment—without copying the original work or importing unsupported product claims.
_Avoid_: copying a viral video, chasing an unrelated meme, treating popularity as proof that a product claim is true

**Pre-Plan Trend Scan**:
A lightweight, platform- and audience-specific review of recent high-performing short videos performed after the audience problem is understood and before the viewer-interest direction and video plan are finalized.
_Avoid_: optional trend research performed only on request, an unbounded content survey, claiming current-trend evidence when live sources were unavailable

**Trend Relevance Ladder**:
The ordered expansion of trend research from comparable industrial products and audiences, to adjacent engineering or manufacturing content, and only then to transferable mechanisms from broader short-video categories.
_Avoid_: treating all viral content as equally relevant, importing a cross-industry trend without explaining its value to the current audience

**Trend Evidence Brief**:
A concise, source-linked explanation shown before viewer-interest confirmation that summarizes relevant current signals, why they work, which mechanism transfers, which popular approaches were rejected, and the Agent's single recommended direction.
_Avoid_: a hidden trend scan, a raw research dump, an unsupported claim that a direction is currently popular

**Human-Relevance Angle**:
A fact-supported connection between the industrial product and a person's concrete work situation, problem, decision, or changed experience that can make the video easier to care about.
_Avoid_: forced emotion, an abstract “lifestyle” label, inventing safety or comfort outcomes not supported by formal knowledge

**Pre-Direction Material Feasibility Check**:
A pixel-level review of official candidate images performed before viewer-interest confirmation to determine whether the proposed attention mechanism and human or application angle can be executed with available evidence-backed visuals.
_Avoid_: metadata-only review, assigning storyboard shots during the interview, confirming a direction before discovering that its required visuals are missing

**Confirmed Video Brief**:
The complete set of user answers and accepted Agent recommendations produced by the **Video Creation Interview** and used as the direct input to the video plan.
_Avoid_: fixed direction ID, hidden taxonomy, unconfirmed Agent assumptions

**Interview Recommendation**:
One concise, evidence-based proposed decision presented with each unresolved interview question for the user to confirm or revise.
_Avoid_: option overload, unexplained recommendation, unsupported creative assumption

**Interview Decision Confirmation**:
The user's explicit confirmation or correction of the single current **Interview Recommendation** before the Agent advances to the next dependent creative decision.
_Avoid_: requiring a special acceptance phrase, treating one confirmation as approval of unresolved later decisions

**Core Video Brief Information**:
The complete set of product-grounded audience, viewing, creative, evidence, action, visual-feasibility, risk, and AI-simulation decisions required to plan one coherent video.
_Avoid_: the legacy six-field form, fixed questionnaire order, director terminology, information already supplied by the user

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
The initial YouTube Shorts-only video workflow scope covering product videos for the internally identified product 石英纤维隔热带.
_Avoid_: TikTok, standard horizontal YouTube videos, workshop videos, other product lines, generic all-product taxonomy

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
The sole user-confirmed creative execution contract that shows each dynamically designed shot's timing, audience-facing purpose, visible action, ordered image references, continuity intent, aligned SRT cues, and risk notes before any Dreamina prompt or paid generation task is created.
_Avoid_: fixed shot-role template, text-only shot list, hidden image selection, a separate user confirmation for Dreamina prompt wording

**Confirmed Storyboard SRT**:
The language-specific `.srt` file whose cue text is the single verbatim future narration transcript and whose exact time ranges are derived from and locked with the user-confirmed visual storyboard before Dreamina tasks are created.
_Avoid_: a separate conflicting voiceover script, Markdown subtitle notes, subtitle text generated only after assembly, readable subtitle text inside Dreamina prompts, automatically burning subtitles into generated shots

**Shot-Subtitle Alignment**:
The confirmed semantic relationship in which every SRT cue expresses the same audience-facing idea as the storyboard shot or consecutive shot group visible during that cue.
_Avoid_: using a visual-direction description as subtitle copy, assigning an unrelated product claim to a shot, generating subtitles only from timing after the storyboard is locked

**Shot Reference Sequence**:
An ordered set of one or more inspected official images assigned distinct continuity roles within one storyboard shot, such as opening state, detail progression, action reference, or ending state.
_Avoid_: limiting every shot to one image, an unordered image collection, mixing incompatible subjects or environments and calling it continuity

**One-Shot Dreamina Download**:
The single download action triggered after the operator confirms completion in the Dreamina web interface, using recorded real task IDs to retrieve and validate all expected shot files without exposing status polling as a user step.
_Avoid_: repeated user-facing status queries, manual filename guessing, attempting assembly with missing or unreadable shots

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
_Avoid_: paid submission, final edited video, voiceover/BGM package, subtitle burn-in

**Dreamina Prompt Artifact**:
An internal, auditable translation of the confirmed visual storyboard into provider-compatible generation instructions used to create the Dreamina shot plan.
_Avoid_: a second creative source of truth, a user-authored prompt, generating prompts before storyboard-plus-SRT confirmation

**In-Conversation Confirmation View**:
The decision-sufficient plan, storyboard, SRT, task, image, evidence, risk, and cost information rendered directly in the Codex conversation whenever the user is asked to confirm a workflow stage.
_Avoid_: requiring the user to open Markdown or JSON files, returning only file paths, hiding confirmation-critical detail in artifacts

**Phase-Scoped Confirmation**:
An ordinary user confirmation applied only to the single visible non-paid decision currently pending in the video run, as determined by the persisted workflow phase.
_Avoid_: requiring stage-specific command memorization, applying one confirmation to later stages, using a generic confirmation to authorize paid generation or submission

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
- The **Creative Discovery Core** is the primary quality-determining capability of the video Agent; the plan, storyboard, SRT, Dreamina tasks, and final assembly must consume its confirmed decisions rather than compensate for a weak or incomplete interview.
- The user-facing `tuolin-video-workflow` skill owns model-led evidence exploration, decision-tree reasoning, questions, recommendations, challenges, and stopping judgment, while deterministic workflow code records decisions and enforces completeness and confirmation gates instead of supplying a fixed question script.
- The **Video Creation Interview** replaces fixed creative-direction selection; the video workflow has no fixed direction taxonomy, primary direction, supporting direction, or ranked direction combinations.
- The **Video Creation Interview** is creative requirements discovery rather than a fixed brief form: it must clarify both the business outcome and the audience's reason to watch.
- The Agent develops a contextual **Viewer-Interest Direction** from the product, audience, platform, use situation, available evidence, and prior answers, then challenges it with the user instead of presenting a generic direction menu.
- Every completed **Video Creation Interview** must produce one user-confirmed **Viewer-Interest Direction**, but the Agent must not turn that conclusion into a mandatory fixed-wording question or a predefined category choice.
- Visual novelty or technical spectacle is not a valid **Viewer-Interest Direction** unless it serves a credible audience interest, product understanding, or business outcome.
- When a requested creative preference conflicts with the target audience's likely viewing interest or the stated business outcome, the Agent must raise a **Creative Strategy Challenge** instead of merely recording the preference.
- A **Creative Strategy Challenge** must identify the concrete conflict and recommend one more effective alternative; the user retains the final creative decision.
- Product identity, parameters, applications, and external claims remain constrained to formal knowledge, while audience-interest and presentation recommendations may use **Creative Strategy Inferences**.
- A **Creative Strategy Inference** may draw on industrial-audience knowledge, platform viewing patterns, and current public research when recency matters, but it must remain visibly distinct from verified product or customer facts.
- The user must confirm the resulting **Viewer-Interest Direction** even when it is supported by a strong **Creative Strategy Inference**.
- The **Video Creation Interview** ends at **Video Interview Decision Sufficiency**, not after a fixed number of questions or exhaustive exploration of every possible creative branch.
- Relentless interviewing means resolving every load-bearing ambiguity, conflict, and dependency that could materially change the video direction; it does not mean maximizing the number of questions.
- Once one coherent, evidence-supported, executable direction is established, remaining **Professional Video Decisions** move to planning and storyboard review instead of extending the interview.
- A broad label such as “European and American industrial buyers” is not automatically an **Actionable Video Audience** when differences in role, buying stage, application situation, or primary concern would materially change the content direction.
- The Agent sharpens the audience only along the single unresolved dimension that affects the current video; it must not require a complete customer persona when the extra detail would not change the plan.
- The Agent should derive audience interest from an **Audience Problem Scenario** before asking the user to choose an abstract style such as “lifestyle” or “technical.”
- When the user has real recurring customer questions or viewing feedback, those observations take priority; otherwise the Agent proposes one evidence-bounded scenario for confirmation.
- A compatible **Short-Video Trend Mechanism** may be translated into the industrial-product context to strengthen the **Viewer-Interest Direction**.
- Trend inspiration contributes creative structure only: it must not copy a specific work, override formal product knowledge, fabricate a customer case, or justify spectacle that does not serve the audience and business outcome.
- Every YouTube Shorts run must complete a **Pre-Plan Trend Scan** after establishing the **Actionable Video Audience** and **Audience Problem Scenario**, but before the user confirms the final **Viewer-Interest Direction** and the Agent generates the plan.
- The **Pre-Plan Trend Scan** should examine a small relevant set of recent examples and extract why their hooks, tensions, reveals, transformations, process payoffs, or proof moments held attention.
- The current release uses public YouTube trend signals and relevant public examples only; first-party Tuolin channel analytics remain a future capability until the channel has sufficient usable data.
- Missing first-party channel history does not block the current **Pre-Plan Trend Scan** and must not be represented as known audience preference.
- The **Pre-Plan Trend Scan** follows the **Trend Relevance Ladder**: comparable industrial products first, adjacent manufacturing or engineering content second, and broader categories only when a specific mechanism can transfer safely.
- Every cross-industry mechanism must include a concrete explanation of why it can hold the current **Actionable Video Audience**; mechanisms without that explanation are excluded.
- If current trend sources are unavailable or do not provide usable evidence, the Agent must report that the live scan was not completed and may use only general creative principles without representing them as current trends.
- Before asking the user to confirm the **Viewer-Interest Direction**, the Agent must show a compact **Trend Evidence Brief** rather than keeping the trend reasoning hidden.
- The **Trend Evidence Brief** identifies the relevant examples or platform signals, their shared success mechanism, the mechanism suitable for the current industrial product, rejected popular approaches and their risks, one recommended direction with its rationale, source links, and scan date.
- The user-facing brief remains concise; raw search results and a long-form trend report are not required unless the user asks for them.
- The Agent evaluates whether a **Human-Relevance Angle** could materially strengthen the current **Viewer-Interest Direction** and may ask the user one concrete scenario question when that judgment remains unresolved.
- A human-relevance question must concern an actual work situation, recurring problem, purchasing decision, or observable experience; it must not ask the user to choose abstractly between “lifestyle” and “professional” styles.
- A **Human-Relevance Angle** is used only when formal knowledge or a user-confirmed real scenario supports it; otherwise the video remains grounded in professional application or purchasing value.
- Before the user confirms the final **Viewer-Interest Direction**, the Agent must complete a **Pre-Direction Material Feasibility Check** by opening the relevant official images and assessing subject, clarity, composition, vertical crop, near-duplicates, and support for the proposed creative mechanism.
- The feasibility check determines whether the direction has usable product-detail, application-process, human-operation, problem-situation, or result visuals, but it does not assign exact images to storyboard shots.
- Material assessments from the feasibility check are reused during planning and storyboard generation rather than repeated as a separate inspection.
- If available visuals cannot support the recommended direction, the Agent must revise the recommendation or ask whether the user explicitly accepts an evidence-safe AI-simulated visual; it must not confirm an unexecutable direction silently.
- Interview questions use ordinary business language and must not require the user to understand directing, shot design, or creative-category terminology.
- The interview is adaptive rather than a fixed questionnaire: it extracts answers already present in the user's request and asks only for unresolved **Core Video Brief Information**.
- **Core Video Brief Information** covers the current product and knowledge source; language, YouTube Shorts format, and duration; the **Actionable Video Audience** and **Audience Problem Scenario**; the reason to watch and confirmed **Viewer-Interest Direction**; the selected **Short-Video Trend Mechanism** and evidence; intended takeaway and viewer action; priority product facts; any **Human-Relevance Angle**; material-supported visual direction; excluded claims and risks; and the approved scope of any AI-simulated visuals.
- Production cost versus visual richness is not required **Core Video Brief Information**. Record it only when the user raises it; otherwise the Agent uses available real images efficiently without adding a budget question.
- Language, platform, duration, audience, or other information already supplied by the user must not be asked again.
- The Agent inspects formal knowledge and available image materials itself; it does not ask the user to judge professional material sufficiency or shot feasibility.
- The interview asks only for business intent that the user can reasonably judge; all **Professional Video Decisions** are made by the Agent after the brief is complete.
- **Professional Video Decisions** must be visible in the plan or storyboard and remain revisable through natural-language feedback before paid generation.
- The interview ends only when all **Core Video Brief Information** is resolved or the user explicitly accepts an Agent recommendation for an unresolved item.
- Every unresolved question includes exactly one **Interview Recommendation** with a short reason based on the current request, formal knowledge, available images, platform, audience, and duration.
- The Agent asks whether the current recommendation is confirmed; the user may reply with an ordinary confirmation or directly provide a correction without learning a special command phrase.
- Each **Interview Decision Confirmation** applies only to the current decision; it does not approve unresolved later decisions.
- Every confirmed or corrected decision is recorded in the **Confirmed Video Brief** and summarized in the generated plan.
- Interview questions must not present a long menu of creative options or shift professional planning work back to the user.
- Each user answer and accepted Agent recommendation becomes part of the **Confirmed Video Brief**.
- Completing the interview does not create a separate brief-confirmation gate. The workflow automatically generates the video plan, and `确认策划` confirms both the interpreted brief and the proposed plan.
- The complete interview decisions remain recorded in the run artifacts even though the user is not asked to confirm a separate interview-summary document.
- There is one **Video Creation Interview** per run. After `确认策划`, the workflow generates the **Visual Storyboard** without starting a second storyboard interview.
- The **Visual Storyboard** is designed dynamically from the confirmed plan; fixed five-second shots, fixed shot counts, and fixed role sequences must not substitute for creative reasoning.
- The user confirms the **Visual Storyboard** and **Confirmed Storyboard SRT** together; this is the only user-facing confirmation of shot-level creative execution.
- The **Confirmed Storyboard SRT** is the sole future narration transcript: any later voice generation must read it verbatim, and any narration change requires the SRT and affected **Shot-Subtitle Alignment** to be revised and reconfirmed.
- Only after storyboard-plus-SRT confirmation may the Agent generate the **Dreamina Prompt Artifact** and **Dreamina Shot Plan**; prompt wording is an internal translation and does not require a separate user confirmation.
- If prompt conversion or provider validation cannot faithfully execute the confirmed storyboard, the Agent must surface the exact conflict, propose a storyboard revision, and obtain renewed storyboard-plus-SRT confirmation instead of changing the prompt into a different creative result silently.
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
- Every confirmation gate must provide an **In-Conversation Confirmation View**; persisted Markdown and JSON artifacts support audit, recovery, and downstream execution but are never the primary review surface.
- When exactly one non-paid creative decision is pending, an ordinary reply such as “确认” performs a **Phase-Scoped Confirmation** without requiring `确认策划` or `确认分镜` command memorization.
- A **Phase-Scoped Confirmation** never authorizes a later gate; Dreamina paid-generation approval must explicitly name the paid generation, and real submission remains a separate explicit action after task-plan approval.
- The plan confirmation view shows the confirmed audience problem, viewer-interest direction, trend evidence and sources, core narrative, product facts and risks, target duration, and three to six representative inspected images.
- The storyboard-plus-SRT confirmation view shows every shot's exact timing, purpose, visible action, complete ordered image-reference sequence with inline images, continuity intent, aligned subtitle cue or intentional silence, and blockers or risks.
- The Dreamina paid-generation confirmation view shows every planned task's shot mapping, job type, reference images, duration, estimated credits, provider-capability adaptations, and blockers; users must not open task Markdown to understand what they are authorizing.
- **External Video Generation Skill Internalization** is a bottom-layer enhancement of prompt writing, shot validation, execution reliability, references organization, continuity, and quality gates; it does not create a hidden creative taxonomy.
- `dexhunter/seedance2-skill` is internalized as Seedance/Dreamina prompt grammar and structure, not as a business taxonomy source.
- The **Video Planning Quality Criteria** must be applied to the **Confirmed Video Brief** and carried through plan, storyboard, prompt generation, Dreamina job planning, and quality checks.
- The current upgrade focuses on **Frame Continuity Upgrade** and **Confirmed Storyboard SRT** generation; it intentionally does not add TTS, BGM, subtitle burn-in, or Jianying automation.
- The term "Hyperframes" is treated as a possible implementation inspiration for frame continuity, not as a confirmed dependency, until a specific open-source/free project is selected.
- The workflow order is: identify a quartz-fiber-tape video request; load the current product's published knowledge card and official images; complete the **Video Creation Interview**; convert the confirmed interview decisions into and confirm the formal video plan; generate and confirm the **Visual Storyboard** and **Confirmed Storyboard SRT**; generate the **Dreamina Shot Plan**; hand off paid Dreamina submission; let the operator monitor completion in the Dreamina web interface; then assemble the locally available shot files.
- A formal video plan must not be generated before the **Video Creation Interview** produces a complete **Confirmed Video Brief**.
- After the interview is complete, the workflow generates the formal video plan automatically; the user should not have to issue a separate "生成策划" command unless they explicitly want manual control.
- After the user confirms the formal video plan, the workflow may generate the **Visual Storyboard** automatically; the user should not have to issue a separate "生成分镜" command unless they explicitly want manual control.
- Confirming the **Visual Storyboard** also locks and writes the **Confirmed Storyboard SRT** before the workflow creates the **Dreamina Shot Plan** automatically; the user should not have to issue separate subtitle or task-planning commands.
- Storyboard confirmation is blocked unless **Shot-Subtitle Alignment** is valid: cue text, cue timing, shot purpose, visible action, and supported product facts must agree.
- **Shot-Subtitle Alignment** does not require one cue per shot: a cue may map to one shot or a consecutive same-meaning shot group, and a visually self-explanatory shot may be intentionally silent.
- Every cue-to-shot relationship and every intentional silent shot must remain visible during storyboard-plus-SRT confirmation; a cue must not cross unrelated shot meanings.
- A storyboard revision that changes shot purpose, timing, order, or deletion must regenerate the affected SRT cues and reset storyboard-plus-SRT confirmation before Dreamina task creation.
- Visual descriptions and Dreamina prompt instructions are production language, not audience-facing subtitle copy, and must never be used as fallback SRT text.
- A storyboard shot may use a **Shot Reference Sequence** rather than a single image when multiple references materially improve the intended expression and continuity can be preserved.
- Every image in a **Shot Reference Sequence** must be visually inspected, shown during storyboard review, assigned an explicit role and order, and checked for product identity, scale, environment, lighting, action, and transition continuity.
- Unrelated images must not be grouped merely to increase visual variety; when continuity cannot be defended, the images belong in separate shots.
- One user-visible storyboard shot remains one continuous final video segment and should pass its **Shot Reference Sequence** to one Dreamina task when the selected provider mode genuinely supports ordered multi-image references.
- If the selected Dreamina mode cannot honor the confirmed multi-image sequence, the Agent must not discard references or split the shot silently; it proposes a consecutive-shot revision with updated timing and **Shot-Subtitle Alignment**, then waits for renewed storyboard-plus-SRT confirmation.
- The user-facing video workflow keeps confirmation gates for the plan, visual storyboard plus SRT, and Dreamina paid generation, but has no separate creative-direction confirmation gate.
- The initial workflow supports 15-, 20-, 30-, 45-, 60-, 90-, and 120-second videos; 60 seconds is the default.
- The initial workflow targets YouTube Shorts only; TikTok, standard horizontal YouTube videos, and other platforms are outside the current scope.
- Every run produces one YouTube Shorts 9:16 vertical deliverable and uses YouTube Shorts viewing behavior, trends, and interface-safe composition as its only platform basis.
- The initial video workflow does not generate platform titles, post copy, descriptions, or hashtags; those belong to a later publishing skill.
- Each supported-duration run produces one complete video; the initial workflow does not split longer videos into a series.
- The **Knowledge Producer** supplies formal product knowledge to both the LinkedIn consumer and the **Video Creation Consumer**.
- The LinkedIn consumer and **Video Creation Consumer** are separate application scenarios with separate workflows and outputs.
- The **Video Creation Consumer** must read Chinese and English external product names from published knowledge cards instead of defining them itself.
- The **Video Creation Consumer** uses **Video Creation Context** as its only task-specific knowledge entrypoint.
- **Video Creation Context** supports the full workflow from the **Video Creation Interview** through Dreamina shot generation and shot review.
- **Video Workflow Entrypoint** is the only user-facing video skill.
- The one-question-at-a-time interview method is owned by **Video Workflow Entrypoint** itself; users do not install or invoke a separate `grill-me` skill, and no second Agent owns the video run.
- Dreamina submission is represented as a safe manual handoff when the Agent environment cannot perform paid external submission directly.
- The user should not need to copy internal script parameters; when manual execution is required, the workflow provides a single PowerShell command.
- The working Dreamina CLI submission, manual-submission JSON, and resumable PowerShell handoff remain stable execution infrastructure; automated result-status querying is removed from the current user-facing flow because the operator monitors completion in the Dreamina web interface.
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
- When a user supplies a **Shot Image Override** before storyboard confirmation, the workflow should validate that the file exists, is an image type supported by Dreamina, and does not introduce clear-face or unsupported-claim risk before updating the storyboard and SRT. Any stale Prompt artifact is removed until renewed confirmation.
- Before storyboard confirmation, users may freely replace shot images, delete shots, reorder shots, or revise shot intent; no **Dreamina Shot Plan** exists yet.
- Confirming the **Visual Storyboard** locks its shot structure and image assignments, then creates the **Dreamina Shot Plan** for separate confirmation and submission.
- After real generation, dissatisfaction does not reopen the initial planning or storyboard flow; it enters a **Video Result Improvement Workflow**.
- Text-only video generation is allowed only for environmental or transitional shots that do not depict the specific product.
- Dreamina generation defaults to `seedance2.0_vip` at 1080P because the operating account has premium access.
- Dreamina clips use 9:16 1080 by 1920 pixels unless the user explicitly chooses another supported configuration.
- **Dreamina Shot Plan** review displays estimated credit use before paid submission.
- Generated-shot durations are designed dynamically from the confirmed narrative, may range from four to fifteen seconds, and should normally remain within four to eight seconds for short-form pacing.
- A 60-second run has no fixed shot count or five-second template; shot boundaries follow the confirmed audience-interest mechanism, available evidence, and continuity needs.
- If the user deletes shots before storyboard confirmation, the workflow should show the new estimated total duration before the storyboard can be confirmed.
- Users may intentionally shorten a video below the original duration target by deleting shots. If the new duration materially deviates from the original target, the workflow must surface the new estimated duration and ask whether to accept the shorter target or add replacement shots before paid generation.
- When the **Confirmed Video Brief** requires a viewer action, the plan must include a matching call to action; otherwise the Agent may propose a light call to action for the user to confirm.
- Call-to-action details must come from formal knowledge or project configuration and must not be hard-coded in the video skills.
- Before submission, the user reviews job type, selected image, image thumbnail, duration, and estimated credit use.
- Paid visual-generation jobs are submitted only after the user says `确认即梦生成`.
- After all visual jobs finish, the operator verifies completion in the Dreamina web interface; the current user-facing workflow does not expose a separate automated status-query step.
- After the operator says generation is complete, the workflow performs a **One-Shot Dreamina Download**, maps every real task ID to its expected storyboard shot, and validates file count and readability before assembly.
- The user may accept the generated result for assembly or reject it and start a new task; a separate **Video Result Improvement Workflow** remains future work.
- **Video Result Improvement Workflow** is not implemented in the current release. If the user rejects generated quality, the current workflow records the result as not accepted and stops without changing the original run.
- The **Confirmed Storyboard SRT** is drafted together with the storyboard and becomes locked when both are confirmed; voiceover, BGM, logos, subtitle burn-in, final editing, publishing titles, post copy, descriptions, and hashtags remain outside the current video Agent.
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
> **Domain expert:** "No. Ask the user to choose the Chinese or English **Video Language Version** first. The current Agent generates Dreamina shots and the **Confirmed Storyboard SRT** for that version; voiceover and BGM remain outside this Agent."
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
> **Domain expert:** "Give one justified **Interview Recommendation**, ask whether it is confirmed, and accept either an ordinary confirmation or a correction."
>
> **Dev:** "Should the user confirm the interview summary before planning?"
> **Domain expert:** "No. Generate the plan when the brief is complete, then let `确认策划` confirm the interpreted brief and plan together."
>
> **Dev:** "Do we run another interview before generating the storyboard?"
> **Domain expert:** "No. Generate it after plan confirmation and ask only when a real material, knowledge, or unresolved-choice blocker appears."
>
> **Dev:** "Does confirming the current recommendation authorize every remaining decision?"
> **Domain expert:** "No. An **Interview Decision Confirmation** applies only to the current decision; later unresolved decisions still require their own confirmation."
>
> **Dev:** "Should the interview ask the user how many shots to use or which camera move to choose?"
> **Domain expert:** "No. Those are **Professional Video Decisions** owned by the Agent and reviewed later in the plan and storyboard."
>
> **Dev:** "Can the initial workflow accept an arbitrary video duration?"
> **Domain expert:** "No. Offer a controlled set of short-video durations: 15, 20, 30, 45, 60, 90, or 120 seconds, defaulting to 60 seconds."
>
> **Dev:** "Does the first version need to support TikTok, standard YouTube videos, or LinkedIn?"
> **Domain expert:** "No. Target YouTube Shorts only."
>
> **Dev:** "Should the video workflow also prepare YouTube Shorts titles, descriptions, or post copy?"
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
> **Domain expert:** "No. Preserve the current CLI submission, resumable handoff, and submit-id recording. Remove the user-facing status query only; the operator monitors completion in the Dreamina web interface."
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
> **Dev:** "Should voiceover, BGM, logos, subtitle burn-in, and final editing happen inside this Agent?"
> **Domain expert:** "No. The Agent creates and locks the **Confirmed Storyboard SRT**, but voiceover, BGM, logos, subtitle burn-in, and final editing remain manual or owned by a later workflow."
>
> **Dev:** "Can technically valid Dreamina clips automatically complete the workflow?"
> **Domain expert:** "No. After the operator confirms completion in the Dreamina web interface, the Agent performs one download-and-file-integrity check. The operator still decides whether to assemble or reject the result; there is no separate status-query or `确认镜头` command."
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
