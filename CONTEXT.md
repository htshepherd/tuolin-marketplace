# Tuolin Marketplace Agent Context

This context describes the business language for Tuolin's local knowledge agents and downstream marketing agents.

## Language

**Automated LinkedIn Prospecting Run**:
A user-authorized workflow that applies confirmed targeting criteria to discover LinkedIn members, review their relevance, and send a bounded number of connection invitations.
_Avoid_: LinkedIn campaign publishing, “adding friends,” claiming the workflow is authorized by LinkedIn

**LinkedIn Discovery Candidate**:
A LinkedIn member whose source post and visible professional information appear plausibly relevant but whose commercial fit remains unconfirmed until human candidate review.
_Avoid_: customer, qualified lead, confirmed competitor

**Connection Invitation**:
An outbound LinkedIn request to connect with one discovery candidate, which remains pending until the recipient accepts it.
_Avoid_: friend addition, confirmed connection, customer acquisition

**Account-Risk Acceptance**:
The current Codex operator's explicit acknowledgement that automated LinkedIn activity may cause platform restrictions and their decision to proceed despite that risk.
_Avoid_: LinkedIn authorization, undetectability guarantee, blanket approval for every future run

**Prospecting Run Authorization**:
The current Codex operator's explicit approval for one prospecting run after reviewing its account, targeting criteria, target type, action limit, and planned external actions.
_Avoid_: standing authorization, approval inherited by a later run, browser login alone

**Prospecting Target Intent**:
The single business purpose of a prospecting run, currently either potential-customer discovery or competitor-intelligence discovery.
_Avoid_: mixing customers and competitors in one run, treating every keyword match as both

**First-Release Evaluation Boundary**:
The first release is evaluated by whether it can complete the agreed LinkedIn discovery and connection workflow, while candidate-fit accuracy and optimization metrics are deferred.
_Avoid_: lead-quality KPIs, acceptance-rate optimization, blocking the first release on targeting precision

**Invitation Dispatch Success**:
The LinkedIn interface has confirmed that one connection invitation was submitted, regardless of whether the recipient later accepts it.
_Avoid_: profile visit, connect-button click without confirmation, accepted connection

**Post-First Prospect Discovery**:
A discovery path that searches LinkedIn posts with confirmed content keywords, inspects people surfaced by those posts, and opens their profiles before considering a connection invitation.
_Avoid_: people-search-first discovery, treating a matching post as proof that its author is a customer

**Direct Category Manufacturer**:
A company visibly manufacturing or directly supplying the same or substitutable base material category expressed by the source keyword phrase.
_Avoid_: treating its promotional post as buyer intent, assuming a manufacturer will source the same material externally

**Same-Category Channel Prospect**:
A brand, distributor, retailer, or private-label seller of a finished category whose visible business may rely on externally sourced products or materials.
_Avoid_: classifying every seller as a manufacturer, asserting external sourcing as fact, excluding an ambiguous channel prospect before human review

**Downstream Material User**:
An installer, contractor, system integrator, fabricator, equipment maker, or project operator that visibly uses the referenced material category in services or finished products.
_Avoid_: requiring a public RFQ, treating direct material suppliers as downstream users, accepting a usage inference without visible business evidence

**Company Contact Resolution**:
The conversion of a qualifying company-authored post into at most one connectable member, prioritized by Owner or Founder, Procurement or Sourcing, Managing Director or General Manager, then Product Manager.
_Avoid_: connecting to a company page, inviting multiple employees from the same company in one run, choosing an arbitrary employee, expanding the role set during a run

**Prospecting Contact Ledger**:
The persistent cross-run record of discovered post, company, and member identities together with invitation state and retry eligibility.
_Avoid_: run-local deduplication only, using display names as identity, treating a page-load failure as a sent invitation

**Prospecting Interview**:
A one-question-at-a-time conversation with the current operator that resolves only the missing business decisions for one prospecting run.
_Avoid_: a fixed form, product or knowledge-base questions, geography unsupported by Posts search, asking implementation questions, inheriting unresolved choices from an earlier run

**Confirmed Prospecting Brief**:
The reviewed output of a prospecting interview containing the run's content keywords, supported post-search criteria, target intent, successful-invitation limit, invitation-note decision, and invitation-dispatch interval.
_Avoid_: standing campaign configuration, an unconfirmed chat summary, implementation settings

**Invitation Note Decision**:
The operator's per-run choice to send no note or to use one explicitly confirmed fixed note for the entire approved candidate batch.
_Avoid_: a permanently hard-coded note policy, unreviewed generated outreach copy, per-candidate variation

**Supported Post Search Criteria**:
The interview decisions that map to controls exposed by LinkedIn post search, including keywords, sort order, publication date, content type, source member or company, publisher relationship, mentioned member or company, author industry, author company, and author-title keywords.
_Avoid_: collecting a criterion the post-search interface cannot apply, browser implementation settings

**Core Post Search Criteria**:
The three post-search decisions always resolved for a run: content keywords, sort order, and publication-date range.
_Avoid_: forcing every optional LinkedIn filter into every interview

**Keyword-Driven Interview Scope**:
The six executable run decisions covering the ordered keyword list, Posts sort, publication range, invitation-note choice, fixed dispatch interval, and maximum invitation count.
_Avoid_: product selection, product category, knowledge-base state, geography, AI keyword recommendations, repeating answers already present in the request

**Ordered Content Keyword List**:
One or more operator-supplied exact post-search phrases processed separately in their stated order, with each discovered candidate retaining its source phrase.
_Avoid_: an unordered keyword set, an arbitrary phrase-count cap or whitelist, AI-generated expansion, merging all phrases into one unreviewed query, losing discovery provenance

**Search Keyword Phrase**:
An exact operator-supplied LinkedIn Posts query that may contain one or more words, such as `Exhaust Wrap` or `Special Fiberglass Exhaust Wrap`.
_Avoid_: assuming every phrase is one word, silently splitting a multi-word phrase, treating comma-separated phrases as one query

**Primary Search Keyword**:
The first phrase in the ordered keyword list, carrying search priority but no distinct LinkedIn filter or execution behavior.
_Avoid_: a separate interview field, a product identity, automatically generating related phrases from it

**Successful Invitation Limit**:
The maximum number of invitation-dispatch successes authorized across all keywords in one prospecting run.
_Avoid_: a per-keyword quota, attempted-click count, a target that permits exceeding the authorization

**Default Run Invitation Limit**:
Ten successful invitation dispatches, presented as the interview recommendation when the operator did not specify a run limit.
_Avoid_: an official LinkedIn safety limit, a quota that must be filled, overriding an explicit operator limit

**Seven-Day Invitation Ceiling**:
The local account-scoped rule that the rolling one-hundred-sixty-eight hours before each proposed dispatch may contain no more than one hundred recorded invitation-dispatch successes across prospecting runs.
_Avoid_: claiming it is a current official LinkedIn limit, resetting it per keyword or per run, claiming manually sent invitations are counted

**Effective Run Invitation Limit**:
The lesser of the operator-requested or default run limit and the remaining skill-recorded capacity under the seven-day invitation ceiling, shown explicitly in the brief.
_Avoid_: silent reduction, exceeding remaining capacity, starting discovery when the effective limit is zero

**Search Exhaustion Completion**:
The normal completion of a run when every confirmed keyword has no remaining eligible candidates, even though the successful-invitation limit was not reached.
_Avoid_: repeating old results, silently loosening filters, inventing new keywords to fill the limit

**Keyword Fallback Progression**:
The ordered discovery rule that advances to the next search keyword phrase only while the current candidate pool remains below the effective run invitation limit.
_Avoid_: searching every phrase after the candidate pool is full, per-keyword quotas, redistributing a full batch across later phrases

**Post Sort Decision**:
The operator's per-run selection of Latest or Most Relevant, with Latest presented as the interview recommendation.
_Avoid_: a hidden fixed sort, changing sort during a run without new authorization

**Candidate Review Card**:
A Codex-visible and run-persisted Markdown-and-JSON pre-dispatch record containing the complete visible source-post text and URL, source keyword phrase, provisional AI relevance reason, post author or company, selected member name, title, company, profile URL, approval state, invitation-note decision, and final dispatch outcome.
_Avoid_: a post summary that hides material context, an unexplained profile URL, presenting AI judgment as confirmed fit, a lead-quality score, sending before the card is shown

**Pre-Dispatch Candidate Review**:
The human confirmation gate in which the operator reads each candidate's complete visible source post and identity evidence before approving or removing the candidate.
_Avoid_: treating run authorization as approval of unseen candidates, confirming after dispatch

**Provisional Candidate Fit**:
The AI's non-final visible-evidence judgment that a post and member are plausible enough to show for human candidate review.
_Avoid_: qualified lead, verified buyer, final customer judgment, hiding uncertainty from the operator

**Unresolved Relevant Lead**:
A plausibly relevant post or company for which no verifiable personal LinkedIn profile with a standard Connect path can be resolved.
_Avoid_: counting it toward the candidate limit, fabricating a contact, presenting it as an actionable candidate

**Approved Candidate Batch**:
The operator-confirmed subset of displayed candidate review cards that may proceed to sequential invitation dispatch in the current run.
_Avoid_: approving undisplayed candidates, adding candidates after confirmation, treating the batch as already contacted

**Invitation Dispatch Interval**:
The operator-confirmed minimum elapsed time enforced between two consecutive invitation submissions in one run, with five minutes presented as the interview recommendation.
_Avoid_: simultaneous dispatch, hidden pacing, claiming an interval guarantees freedom from platform restriction

**Closed Candidate Batch**:
An approved candidate batch whose rejected or skipped members are not replaced by further discovery within the same run.
_Avoid_: automatic backfilling, silently extending the batch, reopening discovery after dispatch begins

**Final Batch Dispatch Authorization**:
The operator's confirmation of the exact LinkedIn account, approved member list, invitation-note decision, and dispatch interval immediately before sequential invitation submission begins.
_Avoid_: per-member repeated prompts, authorization before candidates are known, changing the batch after approval

**Bound LinkedIn Account**:
The authenticated member identity, represented by displayed name and profile URL, that the operator confirms for exactly one prospecting run.
_Avoid_: any logged-in account, credentials as identity, silently continuing after an account switch

**Keyword Post Inspection Limit**:
The fixed first-release ceiling of fifty inspected posts for each content keyword before discovery advances to the next keyword.
_Avoid_: an interview field, unbounded scrolling, counting unopened search-result placeholders as inspected posts

**Verified Infinite-Scroll Exhaustion**:
Evidence that the current LinkedIn Posts result stream produced no new unique post identities across three consecutive bottom-scroll-and-load-wait cycles, rather than a conclusion drawn from a visible footer, advertisement, one stalled load, or a discarded page parameter.
_Avoid_: treating `page=2` as supported pagination, stopping after one scroll, equating currently rendered results with the full result set

**Post Relevance Decision**:
A binary Continue or Skip judgment, based only on the source keyword phrase and visible LinkedIn content, stating whether the post substantively concerns selling, promoting, manufacturing, sourcing, distributing, or commercially applying the referenced category.
_Avoid_: a lead score, unsupported commercial inference, accepting a post from keyword presence alone, continuing a direct same-category manufacturer as a prospective buyer

**Individual Post Author Candidate**:
The member who authored a relevant post and whose profile shows that they represent the related brand, distributor, or retailer.
_Avoid_: replacing every individual author with a higher-ranking colleague, accepting an unrelated personal account

**Standard Connect Eligibility**:
The presence of LinkedIn's ordinary connection-invitation path for a member without requiring guessed email addresses, alternate outreach actions, or extra identity data.
_Avoid_: Follow or Message as a substitute, guessed contact data, bypassing an additional verification step

**Candidate-Local Dispatch Failure**:
An invitation failure attributable to one member's current page or connection state that is recorded before dispatch continues with the next approved member.
_Avoid_: treating an account restriction as local, counting the item as a dispatch success

**Platform-Level Dispatch Stop**:
The immediate termination of the remaining approved batch after an account restriction, security challenge, CAPTCHA, lost authentication, or repeated unexplained dispatch errors.
_Avoid_: continuing after a platform warning, silently treating unexecuted members as failures

**Authorized Dispatch Restart**:
A new prospecting run that rechecks the account and preserved unexecuted candidates and obtains a new final batch dispatch authorization after a prior platform-level stop.
_Avoid_: automatic resume, reusing expired authorization, treating unexecuted members as already approved for a later session

**Prospecting Run Directory**:
The isolated generated report directory that stores one run's confirmed brief, workflow state, candidate review batch, dispatch outcomes, and completion receipt.
_Avoid_: formal knowledge storage, a shared mutable folder for multiple runs, chat-only state

**Operational Prospecting Data**:
LinkedIn discovery and invitation records maintained for run continuity and deduplication without becoming formal market-intelligence knowledge.
_Avoid_: automatic write-back to `knowledge/okf`, approved customer fact, campaign publishing content

**Tuolin LinkedIn Search Skill**:
The dedicated application-layer skill named `tuolin-linkedin-search` that interviews operators, discovers post-based prospects, presents candidate batches, and dispatches authorized connection invitations.
_Avoid_: extending the LinkedIn campaign-publishing skill, formal knowledge maintenance, automatic post publishing

**Hybrid Prospecting Implementation**:
The implementation boundary in which the skill owns interview and browser orchestration, deterministic scripts own run state and ledgers, and Codex's managed browser capability owns visible website interaction.
_Avoid_: chat-only state, scripts making unreviewed external actions, a repository-owned stealth browser daemon

**Codex Chrome Prospecting Surface**:
The official Codex Chrome extension operating a dedicated task tab group inside the operator's existing signed-in Chrome profile.
_Avoid_: the built-in Browser profile for the first release, a repository-launched headless browser, requiring full CDP for ordinary interaction

**Keyword-Driven LinkedIn Search**:
A prospecting run whose discovery scope is defined by an operator-supplied ordered list of exact search keyword phrases and does not require selecting a formal Tuolin product.
_Avoid_: mandatory product binding, knowledge-interface preflight, AI-generated keyword expansion, hard-coding one product category, treating keywords as verified product facts

**AI Invitation Note Draft**:
A short English connection-invitation note grounded in the confirmed keyword scope and search purpose, written without exaggeration or aggressive selling and withheld until the operator confirms or edits it.
_Avoid_: product parameters, certifications, company-capability claims, unsupported facts, per-candidate rewriting, automatic dispatch of draft text

**Invitation Note Availability Conflict**:
The runtime condition in which an authorized batch requires a note but LinkedIn does not expose or permit the Add a note path.
_Avoid_: silently dropping the note, substituting a message or InMail, continuing under stale authorization

**Operator-Started Prospecting Run**:
A prospecting task created by an operator's natural-language request and never by an unattended daily schedule.
_Avoid_: cron-like daily dispatch, standing browser authorization, interpreting a prior daily limit as permission for a later run

**Interrupted Dispatch Recovery**:
The resumption of a non-platform-stopped run after account revalidation, last-action reconciliation, remaining-batch redisplay, and renewed final dispatch authorization.
_Avoid_: blind continuation, new candidate discovery, batch backfilling, reuse after a platform-level stop

**Contact Eligibility Reconciliation**:
The pre-card and pre-dispatch comparison of a normalized member profile identity against the shared contact ledger and the member's live LinkedIn connection state.
_Avoid_: trusting only run-local state, display-name identity, showing pending or connected members as new candidates

**Account-Scoped Active Run Lock**:
The exclusive first-release lock allowing only one active prospecting run for a bound LinkedIn account at a time.
_Avoid_: same-account parallel discovery, independent interval timers, duplicate candidate reservations

**Operator-Supplied Market Search Term**:
A user-confirmed keyword phrase used only for LinkedIn post search and relevance matching.
_Avoid_: promoting the term into an official product name, product fact, or external claim

**Interview Confirmation Reply**:
The operator's plain-language confirmation of the current recommended answer after the Agent asks whether it is confirmed.
_Avoid_: requiring “按推荐”, treating confirmation as approval of later unresolved questions, advancing without an explicit answer

**Sequential Interview Confirmation**:
The rule that every unresolved prospecting decision must be confirmed individually and that no first-release reply can approve all remaining questions at once.
_Avoid_: “剩下都按推荐”, blanket interview completion, skipping unresolved decisions

**Decision-Relevant Interview Question**:
A missing business decision whose answer materially changes a supported search control, candidate-selection boundary, or external invitation action in the current run.
_Avoid_: role verification, effect metrics, fixed internal limits, facts discoverable from code or page state, criteria the LinkedIn interface cannot apply

**Prospecting Interview Question Format**:
The consistent Chinese pattern of a numbered question, with one recommended answer and reason when a concrete recommendation is possible, followed by “是否确认？”.
_Avoid_: option menus, multiple decisions in one question, invented keyword recommendations, special acceptance commands

**Required Keyword Input Question**:
The sole interview question that requests operator-authored search phrases with format guidance but no AI-proposed keyword content.
_Avoid_: guessing the business target, reading product knowledge, asking the operator to confirm an answer they just supplied, auto-expanding the list

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

**Authorized Video Reference**:
A video-asset reference published by the **Knowledge Producer** that permits task-scoped read access to exactly one registered source video without permitting raw-directory browsing.
_Avoid_: raw access, raw scan, arbitrary local video path

**Video Asset ID**:
An opaque stable identifier used by downstream retrieval and runtime extraction to refer to one registered source video without exposing or accepting its raw filesystem path.
_Avoid_: raw path as API contract, user-supplied local path, filename-only identity

**Video Asset Identity Reconciliation**:
The controlled comparison of persistent asset registration, source fingerprint, prior and current path, and concurrent copies used to decide whether a discovered file is a moved asset, a new duplicate asset, or a new source revision.
_Avoid_: path-derived identity, automatic duplicate merge, assuming every same-path file is unchanged

**Video Content Profile**:
A persistent, one-source-video semantic record that describes observable content, time-coded moments, visual usability, and the video's authorized downstream uses without turning visible phenomena into product-performance facts.
_Avoid_: transient task analysis, filename-only metadata, product claim

**Video Profile Card**:
The formal `video_profile` knowledge-card type that owns one video's persistent human-readable semantic profile and is linked one-to-one with its machine-validatable structured representation.
_Avoid_: expanding `content_asset` into a semantic timeline, generated-cache-only profile, independently maintained Markdown and JSON

**Video Profile Title**:
A concise source-video label optimized for catalog scanning and retrieval.
_Avoid_: raw filename alone, full video summary, marketing headline

**Video Profile Summary**:
A two-to-four-sentence whole-video description of the main subject, setting, action flow, and overall visual-use value without replacing time-coded segment detail.
_Avoid_: keyword list, product claim, complete timeline

**Video Segment Description**:
The time-ranged description of one key segment's visible subject, action, state, environment, use capability, audio context, and risks.
_Avoid_: whole-video generalization, fixed storyboard copy

**Segment Product Visibility**:
The time-ranged assessment of whether the product is absent, partially visible, clearly visible, or identity-confirmable, together with size, duration, occlusion, focus, clarity, and supported visual uses.
_Avoid_: whole-video boolean, equating visual clarity with confirmed product identity

**Segment Composition Safety**:
The source-independent description of subject position, action area, crop margins, overlays, and protected visual regions, plus derived suitability for current target aspect ratios.
_Avoid_: one vertical-crop boolean, permanently binding the profile to one platform

**Segment Identifier Risk**:
The time-ranged classification of visible subtitles, watermarks, platform UI, brands, customer or project names, and personal identifiers that may restrict direct reuse.
_Avoid_: generic visual-quality warning, silent removal of provenance or privacy information

**Segment Person Risk**:
The time-ranged record of human visibility, identifiability, age concern, and known authorization status used to control external reuse.
_Avoid_: assuming company possession equals portrait consent, one generic human-face flag

**Candidate Video Evidence Link**:
An automatically proposed relationship between a video profile or segment and a formal evidence source that remains non-authoritative until confirmed.
_Avoid_: automatic proof relationship, external claim support

**Confirmed Video Evidence Link**:
A reviewed relationship showing that a video profile or segment belongs to or is covered by a specific formal evidence source and may use only that source's approved conditions and conclusions.
_Avoid_: product association alone, directory proximity alone, broader claim than the evidence supports

**Segment Editing Suitability**:
The technical reuse assessment of one key segment as ready, adaptable, reference-only, or unusable, separate from the segment's semantic value.
_Avoid_: assuming useful content is directly publishable, one whole-video quality rating

**Video Asset Card**:
The existing content-asset record that identifies one source video, its product relationship, local source, media type, and downstream authorization without describing the video's timeline.
_Avoid_: video summary, key-moment analysis, product claim

**Video Observation**:
A time-coded, confidence-bearing statement about directly visible video content that may guide material selection but does not establish product performance.
_Avoid_: product fact, test conclusion, certification evidence

**Video Claim Interpretation**:
A conclusion about product identity, test success, performance, temperature, safety, certification, or causality inferred from video content and therefore blocked until supported by formal evidence or human review.
_Avoid_: treating visible appearance as proof

**Video Analysis Frame**:
A rebuildable frame sampled by the **Knowledge Producer** to create or refresh a **Video Content Profile** through broad temporal coverage and targeted process-change inspection.
_Avoid_: task-specific shot reference, formal evidence, permanent raw derivative

**Video Representative Frame**:
One of three to six rebuildable preview images selected from a source video's analysis to communicate its main visible content through the Agent interface.
_Avoid_: full analysis-frame set, final storyboard frame, product evidence

**Representative Frame Reference**:
A revision-bound Agent-interface media reference that exposes a representative frame's preview capability and metadata without exposing generated-cache or raw filesystem paths.
_Avoid_: Base64 in every knowledge response, permanent unversioned file path, unrestricted cache-directory access

**Task Video Frame**:
A precise frame extracted through **Runtime Frame Extraction** for one selected source video and one concrete video-creation task.
_Avoid_: reusable knowledge asset, raw derivative archive, automatically published content asset

**Task Video Clip**:
A task-scoped copy of a selected **Video Key Segment** created for direct use in the current storyboard and assembled video.
_Avoid_: modified raw source, formal knowledge asset, AI-regenerated substitute for usable footage

**Video Use Capability**:
A stable, time-ranged description of how visible source-video material may support planning, such as product display, installation step, application context, test process, production process, transition, or before-and-after comparison.
_Avoid_: fixed storyboard shot number, proof claim, task-specific creative decision

**Video Source Classification**:
The human-organized source category and full descendant folder path under a product's fixed material folders, preserved as provenance and an analysis prior rather than proof of visible content.
_Avoid_: observed scene truth, inferred product fact, flattened top-level label

**Video Observed Classification**:
The confidence-bearing categories supported by actual video observations, including the time ranges in which each category is visible.
_Avoid_: copying the source folder label without visual confirmation

**Source Application Scenario**:
A human-maintained application-scenario classification represented by descendant folders beneath the fixed application-material folder.
_Avoid_: visually confirmed application, customer case proof, performance claim

**Video Key Segment**:
A bounded source-video interval that contains one coherent visible action, process stage, state, or change and may be evaluated for direct clip reuse or task-specific frame extraction.
_Avoid_: isolated timestamp, whole-video summary, fixed storyboard shot

**Video Anchor Moment**:
A precise timestamp within a **Video Key Segment** selected for visual verification, representative preview, or exact task-frame extraction.
_Avoid_: replacing the segment's start and end, implied performance result

**Runtime Frame Extraction**:
A controlled read of one **Authorized Video Reference** that copies requested source-video frames into the current **Video Creation Run** without modifying raw or publishing the extracted frames as formal knowledge.
_Avoid_: direct raw access, knowledge-base rebuild, pre-extracting every possible task frame

**Runtime Clip Extraction**:
A controlled read of one **Authorized Video Reference** that copies a selected **Video Key Segment** into the current **Video Creation Run** without modifying the source video.
_Avoid_: editing raw, unrestricted raw access, regenerating usable real footage

**Video Audio Observation**:
A time-coded description or transcript of audible speech, process sound, ambience, noise, or music that may guide editing but does not establish a product fact.
_Avoid_: verified claim, automatic permission to publish a voice or music track

**Video Transcript Detail**:
The complete time-coded source-speech transcription retained in profile detail for audit, with sensitivity and claim-risk annotations.
_Avoid_: catalog payload, verified product knowledge, unrestricted downstream disclosure

**Speech Transcription Adapter**:
A replaceable, local-first interface that converts detected source speech into language-labeled, time-coded transcript items with confidence, speaker segmentation when available, unrecognized intervals, and tool and model provenance.
_Avoid_: hard-coding one ASR vendor, silently uploading enterprise video, treating unavailable transcription as proof that no important speech exists

**Video Analysis Provenance**:
The profile-linked record of the tools, models, policies, prompt-template revision, analyzed media inputs, validation outcome, and human interventions that produced the current video semantics.
_Avoid_: opaque generated profile, embedding full execution logs in the business summary

**Video Profile Amendment**:
A previewed, audited human correction to selected profile fields that preserves the source and original machine proposal while avoiding unnecessary full re-analysis.
_Avoid_: direct untracked file edit, silently overwriting the analysis history, using amendment for systemic sampling failure

**Video Use Exclusion**:
A reviewed, reversible authorization restriction applied to a whole source video or selected key segments without deleting or altering raw media.
_Avoid_: raw deletion, undocumented blacklist, permanent loss of profile history

**Video Profile Migration**:
A deterministic, audited conversion of an older profile representation when every new value can be derived without new media interpretation.
_Avoid_: default-filling new semantic fields, treating migration as re-analysis

**Video Analysis Budget**:
The soft per-source limit on frames, temporal clips, and multimodal inputs that controls processing cost while requiring explicit segmentation or depth escalation rather than silent coverage loss.
_Avoid_: hard truncation presented as complete analysis, unlimited extraction

**Video Analysis Cache Retention**:
The reference-aware lifecycle policy that retains representative media, temporary analysis frames and clips, disputed evidence, and task-local extracts for different periods while never modifying raw source video.
_Avoid_: permanent retention of every temporary frame, extension-based bulk deletion, treating raw media as disposable cache

**Video Analysis Capability Preflight**:
The batch-start gate that verifies required media inspection, extraction, and semantic-analysis capabilities before any source video enters processing and records available optional or degraded capabilities.
_Avoid_: discovering missing mandatory tools halfway through a batch, marking source videos failed because the processing environment was not ready

**Video Batch Impact Scope**:
The set of profiles, source scenarios, or business categories affected by a detected pipeline or acceptance defect and therefore paused or invalidated together.
_Avoid_: always blocking the whole library, always treating defects as isolated

**Video Knowledge-to-Creation Tracer**:
The minimum real end-to-end proof that one unchanged raw source video becomes a validated profile, an Agent-interface retrieval result, an authorized task frame or clip, a confirmed storyboard preview, and a real assembly input.
_Avoid_: schema-only completion, extraction-script demo, mocked downstream use

**Tracer Source Video**:
The low-risk real product video selected to exercise continuous action, key segments, product visibility, runtime frame and clip extraction, storyboard preview, and direct assembly in the first tracer.
_Avoid_: static easiest sample, test-validation footage, corrupt or privacy-heavy source

**Tracer Candidate Inspection Cache**:
The rebuildable, source-fingerprint-scoped temporary media used only to compare product-video candidates before the tracer source is confirmed.
_Avoid_: formal analysis cache, video-creation run asset, published representative frame

**Source Audio Use Policy**:
The profile-level assessment of whether a source segment's original audio may be retained, should be muted, must be muted, or requires human review because of speech, privacy, noise, or music-rights risk.
_Avoid_: assuming every extracted clip may publish its original audio

**Video Profile Revision**:
The source fingerprint, source-classification fingerprint, profile schema version, and analysis-policy version that together prove a **Video Content Profile** still describes its current source video.
_Avoid_: filename-only identity, silently reusing stale semantic analysis

**Video Profile Processing State**:
The per-source-video lifecycle state that distinguishes registered, processing, valid, review-required, failed, excluded, and stale profiles.
_Avoid_: one aggregate success flag for the whole product partition

**Legacy Video Frame Cache**:
Frame files produced by the previous single-point extraction behavior that may remain as historical cache but do not establish a valid current video profile.
_Avoid_: processed-video completion, representative-frame migration without validation

**Visual Observation Scope**:
The usage authorization for a valid video profile that permits retrieval, material selection, visual planning, and editing decisions while forbidding use as proof of product parameters, performance, certification, temperature, or safety.
_Avoid_: external product-fact authorization, evidence-only source existence, unrestricted marketing claim use

**Video Observation State**:
The local state of one observation, segment, classification, transcript item, or reuse recommendation, independent of the overall profile state.
_Avoid_: invalidating the entire profile for every uncertain detail

**Video Observation Confidence**:
An explainable confidence assessment synthesized from traceable source, temporal, visual, audio, quality, and cross-analysis signals.
_Avoid_: opaque model self-rating, confidence without supporting reasons

**Video Segment Group**:
A set of semantically similar key segments within one source video that preserves one preferred segment and ranked alternatives rather than deleting repeated actions.
_Avoid_: frame-level perceptual duplicate set, destructive semantic deduplication

**Video Asset Family**:
A cross-source relationship that distinguishes identical source content, near-duplicate encodes, complementary views of the same event, and semantically similar but separate scenes without modifying any raw file.
_Avoid_: automatic source merge, raw cleanup, treating similar scenarios as one recording

**Video Profile Batch Acceptance**:
The risk-based human review of a completed profile batch that validates pipeline quality and publication safety without converting visual observations into product facts.
_Avoid_: approving every observation as a product claim, skipping first-batch validation, accepting a batch with systemic errors

**Video Profile Batch**:
One explicitly confirmed knowledge-work unit containing either the fixed product-video folder, one canonical source-application-scenario folder, or the final test-validation folder.
_Avoid_: unbounded all-video scan, arbitrary file-count chunk detached from business classification

**Video Profile Checkpoint**:
The source-fingerprint-bound atomic result saved after one video's prepared inputs, Codex semantic review, formal profile draft, representative-frame references, validation outcome, and processing state have been completed.
_Avoid_: waiting until the whole batch to persist work, treating a partial unvalidated draft as published knowledge, reprocessing unchanged successful videos after interruption

**Video Profile Publication Transaction**:
The staged-to-formal promotion, Agent-interface rebuild, and interface verification sequence that makes an accepted video profile available to downstream consumers only when the entire publication sequence succeeds.
_Avoid_: downstream reading staging files, switching to an unverified interface, destroying the last verified interface on publication failure

**Video Batch Maturity**:
The rollout state that determines whether a validated batch requires acceptance before downstream automatic selection or may publish optimistically under monitored sampling.
_Avoid_: treating first-run and stable incremental batches identically

**Video Source Revocation**:
The withdrawal of a previously selectable profile or segment because its batch, source identity, privacy, rights, test interpretation, or analysis validity is no longer trusted.
_Avoid_: deleting task artifacts silently, ignoring a high-risk withdrawal

**Runtime Video Extraction Audit**:
The task-local record of every authorized frame or clip extraction, including run, interface revision, asset and profile revisions, requested time bounds, operation, validation outcome, output, and revocation state.
_Avoid_: unlogged source read, token-only authorization with no task provenance

**Candidate Video Preview**:
A low-cost task-local clip extracted for internal comparison among shortlisted segments before one segment is selected for formal storyboard use.
_Avoid_: final task clip, unlimited exploratory extraction, user-confirmed storyboard material

**Video Material Retrieval**:
The downstream selection process that first applies hard structured constraints to authorized video profiles and segments, then ranks the remaining candidates by semantic relevance to the current confirmed brief or shot need.
_Avoid_: unbounded raw search, semantic similarity without safety filters, fixed-label lookup only

**Representative Frame Visual Index**:
A rebuildable visual-embedding projection of authorized representative frames that remains bound to their asset, profile revision, timestamp, and key segment and is used only after structured authorization and risk filtering.
_Current status_: deferred; not required for the first implementation
_Avoid_: orphan image embeddings, visual similarity as product proof, making an unconfigured embedding model a launch dependency

**Codex Representative Frame Rerank**:
The current visual-ranking step in which structured and textual retrieval produces a small authorized candidate set and Codex inspects the candidates' representative frames before selecting or ordering material.
_Avoid_: scanning the whole image cache, ranking from text alone when visual distinctions matter, claiming that a persistent visual-vector index exists

**Task Video Preview**:
A run-local preview of the exact **Task Video Clip** or **Task Video Frame** proposed for a storyboard shot and shown before storyboard confirmation.
_Avoid_: profile representative frame standing in for a direct clip, hidden source interval, post-confirmation substitution

**Meaning-Preserving Video Adaptation**:
A disclosed technical transformation of a **Task Video Clip** that preserves visible action, chronology, identity, and observational meaning while making the clip usable in the target deliverable.
_Avoid_: changing the apparent test result, reordering actions, undisclosed synthetic alteration

**Video Profile Catalog**:
A lightweight Agent-interface projection of valid video profiles used for structured filtering and semantic ranking without loading every complete profile into a task context.
_Avoid_: full transcript dump, raw file listing, complete profile payload for every video

**Test-Footage Publication Gate**:
The external-use check that permits test footage only when the intended statement is supported by formal evidence or constrained to a reviewed neutral description of what is visibly occurring.
_Avoid_: treating authentic footage as automatic proof, implying a passed test through montage alone

**Video Understanding Pipeline**:
The coordinated use of deterministic media inspection, adaptive sampling, quality and duplicate checks, speech transcription, multimodal interpretation, and structural validation to produce a valid **Video Content Profile**.
_Avoid_: filename-only classification, one-frame interpretation, model-guessed media metadata

**Codex Video Semantic Review**:
The current semantic-analysis execution boundary in which the knowledge-base Agent prepares bounded frames, clips, media facts, source classification, and available transcript evidence for direct inspection and structured judgment by Codex without requiring a user-supplied external-model API key.
_Avoid_: hidden third-party model calls, asking the user to configure a multimodal API, granting Codex unrestricted raw-directory browsing

**Video Analysis Clip**:
A short, low-cost, rebuildable derivative used only to verify motion continuity, action boundaries, change persistence, source stability, or direct-reuse suitability during profile generation.
_Avoid_: downstream task clip, published representative asset, mandatory derivative for every source video

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

- An **Automated LinkedIn Prospecting Run** evaluates zero or more **LinkedIn Discovery Candidates**
- An **Automated LinkedIn Prospecting Run** may send a bounded **Connection Invitation** to a selected **LinkedIn Discovery Candidate**
- **Account-Risk Acceptance** is recorded from the current Codex operator and does not imply authorization from LinkedIn
- Every **Automated LinkedIn Prospecting Run** requires exactly one **Prospecting Run Authorization**, which expires when that run ends
- Every **Automated LinkedIn Prospecting Run** has exactly one **Prospecting Target Intent**
- Potential-customer discovery may produce **Connection Invitations**; competitor-intelligence discovery is a separate workflow and does not send them by default
- The **First-Release Evaluation Boundary** defers candidate-quality optimization without removing the run's confirmed targeting criteria
- Only an **Invitation Dispatch Success** counts toward a run's completed connection-invitation total
- The first release uses **Post-First Prospect Discovery** as its candidate source before profile inspection and invitation dispatch
- A **Direct Category Manufacturer** is skipped as a competitor rather than inferred to be a buyer
- A **Same-Category Channel Prospect** may continue as provisional when visible evidence supports branding, distribution, retail, or private-label activity; an unclear make-versus-source model remains a human-review uncertainty
- A **Downstream Material User** may continue without an explicit RFQ when visible evidence shows installation, integration, fabrication, equipment, or project use of the referenced category
- A qualifying company-authored post requires **Company Contact Resolution** before a **Connection Invitation** can be sent
- **Company Contact Resolution** that finds no member in the confirmed role priority ends with the company skipped, not an arbitrary fallback employee
- The **Prospecting Contact Ledger** deduplicates post URLs, company-page URLs, and member-profile URLs across all runs
- A member with a successful or pending invitation is ineligible for another invitation; a failed candidate is retryable only when no invitation was submitted
- After one member from a company reaches **Invitation Dispatch Success**, other members of that company are ineligible in the first release
- A **Prospecting Interview** produces exactly one **Confirmed Prospecting Brief**
- A **Prospecting Run Authorization** may be granted only after the operator reviews the **Confirmed Prospecting Brief**
- Every **Confirmed Prospecting Brief** includes one **Invitation Note Decision**
- When a note is enabled, the same confirmed note is shown with and applied to every member of the **Approved Candidate Batch**
- A **Confirmed Prospecting Brief** may contain only **Supported Post Search Criteria** for the discovery stage
- Every **Confirmed Prospecting Brief** contains the **Core Post Search Criteria**; other supported filters are included only when the operator requests them or the current goal requires them
- The content-keyword portion of the **Core Post Search Criteria** is an **Ordered Content Keyword List**
- One run processes the **Ordered Content Keyword List** sequentially while the **Prospecting Contact Ledger** deduplicates candidates across keywords
- The **Successful Invitation Limit** applies once to the whole run and stops further external invitation actions immediately when reached
- The **Default Run Invitation Limit** supplies the recommendation only when the operator omitted a limit
- Every run's **Successful Invitation Limit** is additionally bounded by the remaining capacity under the **Seven-Day Invitation Ceiling**
- The **Seven-Day Invitation Ceiling** is recalculated immediately before every invitation submission and never resets on a calendar-week boundary
- The **Seven-Day Invitation Ceiling** counts only dispatch successes recorded by the **Tuolin LinkedIn Search Skill**; the brief must disclose that manual LinkedIn invitations are untracked
- The **Effective Run Invitation Limit** controls candidate-batch capacity and dispatch; an effective limit of zero blocks the run before browser discovery
- A run may finish through **Search Exhaustion Completion** with fewer dispatches than its **Successful Invitation Limit**
- Expanding criteria after **Search Exhaustion Completion** requires a new brief and a new run authorization
- The **Core Post Search Criteria** contains exactly one **Post Sort Decision** shared by all keywords in the run
- Every candidate proposed for invitation must have a **Candidate Review Card** shown during **Pre-Dispatch Candidate Review**
- Every **Candidate Review Card** prints the complete visible source-post text in Codex so the operator can independently judge **Provisional Candidate Fit**
- Plausible but uncertain downstream users with verified personal identity and **Standard Connect Eligibility** enter review as **Provisional Candidate Fit**, with visible supporting evidence and doubts
- An **Unresolved Relevant Lead** is recorded for traceability but does not enter the candidate batch or count toward its effective limit
- A **Connection Invitation** cannot be submitted until its candidate passes **Pre-Dispatch Candidate Review**
- **Pre-Dispatch Candidate Review** produces exactly one **Approved Candidate Batch** for the run
- Members of an **Approved Candidate Batch** are processed sequentially and every consecutive submission must respect the **Invitation Dispatch Interval**
- Every **Confirmed Prospecting Brief** includes exactly one **Invitation Dispatch Interval** shared by the approved batch
- The displayed candidate batch contains no more members than the **Successful Invitation Limit**
- Once reviewed, the batch becomes a **Closed Candidate Batch**; its approved subset is dispatched and any further discovery requires a new run
- Discovery continues only until the provisional candidate-card pool reaches the effective run limit, the current search space reaches a valid stop condition, or all phrases finish; operator removals during review never reopen discovery or trigger backfill
- **Pre-Dispatch Candidate Review** ends only when the operator grants **Final Batch Dispatch Authorization** or rejects the batch
- After **Final Batch Dispatch Authorization**, the approved batch is dispatched sequentially without additional per-member confirmation
- Every **Automated LinkedIn Prospecting Run** has exactly one **Bound LinkedIn Account**, shown before discovery and again at final batch authorization
- Missing authentication, unresolvable identity, or a change to the **Bound LinkedIn Account** blocks the run; credentials and verification codes remain user-entered
- **Post-First Prospect Discovery** inspects no more than the **Keyword Post Inspection Limit** for each keyword and then advances in list order
- Before the effective candidate limit or **Keyword Post Inspection Limit** is reached, a keyword may end as exhausted only with **Verified Infinite-Scroll Exhaustion**
- Advertisements and duplicate post identities do not count toward the **Keyword Post Inspection Limit**
- Reaching every keyword's inspection limit without filling the candidate batch leads to the existing actual-size batch, not broader automatic discovery
- Each inspected post receives one **Post Relevance Decision** before its author or company can become a discovery candidate
- Each **Post Relevance Decision** uses only the source **Search Keyword Phrase** plus visible post, author, and company evidence; product knowledge and a verified knowledge interface are not prerequisites
- News reposts, unrelated homonyms, ordinary consumer sharing, and obvious spam receive a Skip decision in the first release
- An **Individual Post Author Candidate** proceeds directly to candidate review; **Company Contact Resolution** applies only to company-authored posts
- Only a member with **Standard Connect Eligibility** may enter an **Approved Candidate Batch**
- A member without **Standard Connect Eligibility** is skipped with a recorded reason and is not converted to another outreach action
- A **Candidate-Local Dispatch Failure** records the member outcome and allows sequential dispatch to continue
- A **Platform-Level Dispatch Stop** preserves separate lists of successful, skipped, failed, and unexecuted members and prevents all further invitation submissions in the run
- Members left unexecuted by a **Platform-Level Dispatch Stop** may proceed only through an **Authorized Dispatch Restart**
- Every run owns one **Prospecting Run Directory** under generated reports, while the **Prospecting Contact Ledger** is shared across run directories
- **Operational Prospecting Data** remains outside formal knowledge; promotion into market intelligence requires a separate knowledge-base workflow
- The **Tuolin LinkedIn Search Skill** owns prospecting runs and consumes browser and operational-ledger capabilities without changing the existing LinkedIn campaign-publishing boundary
- The **Tuolin LinkedIn Search Skill** uses a **Hybrid Prospecting Implementation** rather than a prompt-only workflow
- The first release performs website interaction through the **Codex Chrome Prospecting Surface** and requires its extension, website access, Chrome session, and bound LinkedIn identity to pass preflight
- Every **Automated LinkedIn Prospecting Run** is a **Keyword-Driven LinkedIn Search** whose search scope comes from an operator-supplied **Ordered Content Keyword List** without requiring formal product selection
- Every item in the **Ordered Content Keyword List** is one exact **Search Keyword Phrase** and is searched separately in the confirmed order
- The **Ordered Content Keyword List** has no business whitelist or fixed phrase-count ceiling; its deduplicated count and complete execution order are shown in the run brief
- A **Primary Search Keyword** is simply the first list item; exact duplicates are removed case-insensitively while the first occurrence keeps its position
- **Keyword Fallback Progression** stops discovery as soon as the candidate pool reaches the effective run invitation limit; later phrases are searched only when earlier phrases do not supply enough eligible candidates
- A **Keyword-Driven LinkedIn Search** requires a writable task workspace for durable run state, candidate cards, the shared contact ledger, and rolling invitation counts, but it does not require or read a knowledge-base Agent interface
- When the **Invitation Note Decision** enables a note, an **AI Invitation Note Draft** must become fixed operator-confirmed text before it enters the brief
- An **AI Invitation Note Draft** may summarize a clear common topic across the confirmed keyword phrases; when no reliable common topic exists, it uses generic industry-connection language instead of inventing a product description
- Dispatch uses the confirmed note byte-for-byte across the approved batch and cannot rewrite it during execution
- An **Invitation Note Availability Conflict** pauses dispatch and requires the operator to authorize no-note dispatch or end the run
- Every first-release run is an **Operator-Started Prospecting Run** and requires its own interview and authorizations
- A non-platform interruption may use **Interrupted Dispatch Recovery**; the same run directory and closed candidate batch remain authoritative
- **Contact Eligibility Reconciliation** runs before a **Candidate Review Card** is created and again immediately before dispatch
- Sent, pending, first-degree-connected, reserved by another unfinished batch, or unresolved-ambiguous members are excluded; only confirmed no-dispatch failures remain retryable
- Candidate cards persist as Markdown and JSON in the run directory; screenshots are retained only for explicit requests or disputed interface state, and browser secrets are never stored
- The **Account-Scoped Active Run Lock** protects candidate reservation, contact-ledger updates, and dispatch pacing until the run completes or terminates
- An **Ordered Content Keyword List** may contain an **Operator-Supplied Market Search Term**, with provenance retained and downstream claim use prohibited
- Each unresolved **Prospecting Interview** question presents one recommendation and reason when the system has a supported default; the **Required Keyword Input Question** instead waits for operator-authored phrases and advances immediately after valid input
- The **Keyword-Driven Interview Scope** limits a new run to six executable decisions and omits any decision already explicit in the initial request
- **Sequential Interview Confirmation** applies until the brief is decision-sufficient; information already explicit in the initial request is not asked again
- A **Prospecting Interview** may ask only a **Decision-Relevant Interview Question** and must render it in the **Prospecting Interview Question Format**
- The system does not determine the operator's organizational role; an explicit confirmation in the current Codex conversation is sufficient

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
- A **Video Creation Context** may contain **Authorized Video References** published by the **Knowledge Producer** for videos explicitly related to its fixed product scope.
- An **Authorized Video Reference** exposes a **Video Asset ID**, profile ID, source revision, allowed operations, and revocation state rather than a raw execution path.
- The knowledge producer privately resolves **Video Asset IDs** to current source paths and validates product scope, profile revision, allowed operation, task identity, timestamp bounds, and revocation before runtime extraction.
- **Runtime Frame Extraction** and **Runtime Clip Extraction** accept an authorized **Video Asset ID** and task-scoped parameters; they must reject arbitrary raw or local paths supplied by the downstream consumer.
- User-facing receipts may show a business-readable relative source location for traceability, but downstream execution does not depend on that path.
- A newly registered source video receives a persisted opaque **Video Asset ID** that is not derived from its filename, directory, or content hash.
- **Video Asset Identity Reconciliation** preserves the existing asset ID when a source is renamed or moved, its prior path has disappeared, and its content fingerprint still matches.
- When identical content exists concurrently at both the prior and newly discovered locations, the new copy receives a distinct asset ID and the two assets are related through an exact-duplicate **Video Asset Family**.
- Replacing the bytes at an already registered path preserves the asset ID as the business identity of that registration but creates a new source revision and immediately invalidates the prior semantic profile.
- When the system cannot reliably distinguish a move from a copy, it must request human reconciliation rather than silently merging registrations.
- Downstream retrieval and extraction continue to use the asset ID after moves or revisions and never receive or submit the private raw-path mapping.
- Each registered source video has one **Video Asset Card** and at most one current **Video Content Profile** published by the **Knowledge Producer**.
- A **Video Asset Card** and its **Video Content Profile** have a one-to-one relationship: the asset card owns identity and authorization, while the profile owns time-coded semantic understanding.
- The existing `content_asset` card type remains responsible for source registration, media type, source classification, related product, authorization identity, and **Video Asset ID**.
- A new formal `video_profile` card type represents the **Video Profile Card** and owns the persistent semantic profile rather than adding the full semantic timeline to `content_asset`.
- Published profile files use `knowledge/okf/视频档案/{product_slug}/{video_asset_id}.md` for the human-readable card and a same-name `.json` file for the complete machine-validatable structure.
- The Markdown and JSON forms are projections of one validated domain object and are written in one **Video Profile Publication Transaction**; they must not be edited or versioned independently.
- A missing counterpart, mismatched profile revision, mismatched content digest, or conflicting semantic value invalidates the profile and prevents interface publication.
- Staged profile pairs use the same relative product and asset layout beneath `generated/staging/video-profiles/{batch_id}/`.
- Analysis frames, analysis clips, tool logs, Codex input manifests, and verbose provenance remain under generated cache or batch-report storage and never become formal profile-card files.
- The Agent interface adds a `video_profile` catalog projection and on-demand detail reader generated from the validated formal profile pair; downstream consumers use profile and asset identifiers rather than either file path.
- Each **Video Content Profile** provides a **Video Profile Title**, one **Video Profile Summary**, and a **Video Segment Description** for every key segment.
- The title supports catalog scanning, the summary supports candidate comparison, and segment descriptions support concrete retrieval, preview, extraction, and storyboard decisions.
- A whole-video summary never substitutes for key-segment time bounds and descriptions.
- Every key segment records **Segment Product Visibility** rather than relying on one whole-video visible/not-visible flag.
- Clear visibility describes appearance quality; identity-confirmable additionally requires enough supported evidence to associate the visible object with the registered product.
- A segment may be useful for action explanation while remaining unsuitable for a product hero, detail, or identity-bearing shot.
- The whole-video profile summarizes the best supported visibility level and the proportion of useful product-visible segments without replacing segment-level assessment.
- Every key segment records **Segment Composition Safety**, including source aspect ratio, subject and action position, crop margins, protected product, tool, and face regions, overlay locations, and whether dynamic subject-following crop would be required.
- The profile derives a current 9:16 suitability of direct, padding-required, dynamic-crop-required, or unsuitable from the general composition record.
- General composition safety remains reusable for future aspect ratios; a platform-specific score does not replace or erase source composition information.
- Every key segment records **Segment Identifier Risk** for Tuolin-owned marks, third-party brands, customer or project names, platform watermarks or UI, vehicle plates, badges, contact details, burned-in subtitles, and unidentified visible marks.
- Current Tuolin-owned marks may normally remain after checking that they are still valid; third-party or customer identifiers require human review.
- Personal identifiers must be cropped, masked, or treated as a blocker before external use.
- Platform watermarks and conflicting burned-in subtitles reduce direct-reuse suitability and should prefer an alternate source when available.
- Masking, blurring, or cropping an identifier is a disclosed adaptation; generative removal must not conceal source provenance or rights risk.
- Every key segment records **Segment Person Risk** separately for visibility and authorization: none, hands-only, unidentifiable back view, blurred face, clearly identifiable face, possible minor, or uncertain.
- Hands-only and unidentifiable back-view footage may remain low-risk candidates after checking badges, tattoos, and other identifiers.
- A clearly identifiable face without recorded authorization cannot enter automatic external selection.
- Possible minors block automatic external use.
- Possession of a company media file does not by itself establish portrait authorization.
- Cropping or masking a person is a disclosed adaptation; generative face replacement or silent person removal is not ordinary **Meaning-Preserving Video Adaptation**.
- The pipeline may propose **Candidate Video Evidence Links** using directory proximity, filenames, dates, identifiers, visible report numbers, speech, and source context.
- A candidate link never supports a product conclusion or passes the **Test-Footage Publication Gate**.
- A link becomes a **Confirmed Video Evidence Link** only through explicit source metadata, a clearly matching report or test identifier, or human review.
- A confirmed link authorizes only the conditions and conclusions actually covered by the linked formal evidence.
- Product-card association defines product scope but does not establish a test-result relationship.
- Conflicting video observations and linked evidence require knowledge review before external use.
- A **Video Content Profile** stores neutral source semantics, observable actions, use capabilities, allowed observation-level expressions, prohibited interpretations, reuse modes, risks, and evidence boundaries.
- The knowledge producer does not persist marketing copy, fixed voiceover, hooks, claims, calls to action, or audience-specific shot wording in a video profile.
- The **Video Creation Consumer** generates task language from the **Confirmed Video Brief**, formal product knowledge, and the selected neutral video semantics.
- Every **Video Key Segment** records **Segment Editing Suitability** independently from its content meaning.
- `ready` segments may be directly extracted without more than routine normalization; `adaptable` segments require disclosed **Meaning-Preserving Video Adaptation**; `reference-only` segments may support task frames or generation references but not direct clip reuse; `unusable` segments are excluded from automatic downstream use.
- Suitability considers resolution, frame rate, compression, stability, exposure, focus, action completeness, useful duration, composition, audio, identifiers, people, and whether required changes exceed meaning-preserving adaptation.
- Whole-video quality summaries may aid catalog ranking but never replace segment-level editing suitability.
- A **Video Content Profile** persists across video-creation tasks so downstream consumers can select a source video without repeating full semantic analysis.
- A **Video Content Profile** contains **Video Observations** and task suitability; any **Video Claim Interpretation** still requires separate formal evidence or human review.
- **Video Analysis Frames** are selected through two stages: uniform temporal coverage for whole-video understanding, followed by targeted sampling around scene, subject, visibility, action, and process-state changes.
- Short videos receive enough broad samples to represent beginning, development, and ending; longer videos are segmented and capped so analysis depth grows by meaningful sections rather than by every elapsed second.
- Installation, test, and production-process videos receive targeted before, action, and after sampling in addition to broad coverage.
- Black, severely blurred, and near-duplicate samples should be replaced or excluded before observations are produced.
- **Video Analysis Frames** support rebuilding the persistent profile; **Runtime Frame Extraction** creates separate task artifacts after a downstream consumer selects a video.
- Each published **Video Content Profile** exposes three to six **Video Representative Frames** with source timestamps and visual descriptions.
- **Video Representative Frames** live in rebuildable generated storage and may be read through the Agent interface for material selection.
- The lightweight **Video Profile Catalog** exposes only thumbnail-sized **Representative Frame References**, source timestamps, short visual summaries, and risk states; it does not inline image bytes or Base64 payloads.
- On-demand profile detail exposes all three to six representative-frame references with dimensions, content fingerprint, source timestamp, related key segment or global-context role, description, and current authorization state.
- A **Representative Frame Reference** is bound to the **Video Asset ID**, profile revision, and Agent-interface revision and becomes unusable when the profile is stale, excluded, or revoked.
- The interface resolves representative images through a controlled local media reference in the current single-machine deployment; a future authorized media endpoint may replace that transport without changing the downstream contract.
- Representative-frame access never exposes the generated-cache directory or the privately mapped raw source path.
- Representative-frame selection prioritizes **Video Anchor Moments** from preferred key segments and covers the source video's main distinct use capabilities.
- A small number of global environment or subject-establishing frames may supplement segment anchors when they add whole-video context.
- Installation and test-process profiles should represent before, action, and after states when those states are visibly available.
- Representative frames must not all come from one repeated action merely because it is visually attractive.
- Each representative frame records its source key segment or is explicitly marked as a global context frame.
- Selecting a **Video Representative Frame** does not make it the final storyboard reference; the consumer creates a **Task Video Frame** at the chosen precise time when the video is used.
- **Task Video Frames** live only inside the current **Video Creation Run** and are not automatically written back to knowledge cards.
- A **Video Content Profile** publishes one or more **Video Use Capabilities** with applicable time ranges, visual clarity, continuity needs, crop suitability, human-presence risk, and supported reuse modes.
- A **Video Use Capability** never assigns a permanent storyboard shot number; the **Video Creation Consumer** maps it to a concrete shot role from the current confirmed brief and plan.
- A **Video Content Profile** preserves both **Video Source Classification** and **Video Observed Classification**.
- **Video Source Classification** includes the fixed top-level material category and the complete relative descendant folder path; descendant folders must not be discarded when the asset is indexed.
- Beneath the fixed application-material folder, descendant folders define **Source Application Scenarios** and therefore carry stronger business meaning than generic storage folders.
- The first descendant folder beneath the fixed application-material folder is the canonical **Source Application Scenario**.
- Deeper descendant folders are preserved in order as source context but do not receive a fixed semantic type until their names and video observations support a role such as action, process stage, source party, batch, or other context.
- A **Source Application Scenario** may guide retrieval and analysis immediately, but the profile must still record whether and when that application is visibly supported by the video.
- Each meaningful time-coded entry in a **Video Content Profile** is a **Video Key Segment** with start and end timestamps, a visible role such as preparation, action, change, completion, or result view, and a statement of whether motion continuity is required.
- A **Video Key Segment** contains one or more **Video Anchor Moments** used for representative frames and later precise runtime extraction.
- A **Video Key Segment** may carry a suggested trim range with small lead-in and lead-out buffers, but the video consumer decides the final task edit.
- A **Video Key Segment** declares whether it supports direct clip reuse, frame-reference reuse, both, or neither.
- A **Video Content Profile** records whether an audio track exists and associates **Video Audio Observations** with relevant **Video Key Segments**.
- Speech may be transcribed with language and timestamps, but spoken parameters, test conclusions, promises, and product identities remain **Video Claim Interpretations** until separately supported.
- Speech transcription is provided through a replaceable **Speech Transcription Adapter** rather than being coupled to one ASR implementation.
- The default adapter policy is local-first; sending enterprise source video or audio to a cloud transcription service requires explicit configuration and authorization.
- Adapter output records detected language, time-coded text, confidence, speaker segments when available, unrecognized intervals, and tool and model version.
- Videos with no detected speech may skip transcription while retaining their non-speech **Video Audio Observations**.
- If clear speech exists but no transcription adapter is available, visual analysis may still produce a valid profile under **Visual Observation Scope**, but the profile and Agent interface must explicitly report that audio understanding is incomplete.
- An ASR-unavailable profile must not imply that the source contains no important speech; its original audio defaults to human-review-required or mute-recommended until reviewed.
- Adding or replacing a transcript for an otherwise current source updates the audio section and provenance, revalidates the profile, and forces a verified Agent-interface refresh without requiring unrelated visual semantics to be regenerated.
- Complete source speech is retained as **Video Transcript Detail** rather than embedded in the lightweight **Video Profile Catalog**.
- Transcript detail annotates personal or customer information, contact details, unsupported parameters, promises, test conclusions, and other sensitive or claim-bearing content.
- Candidate comparison uses transcript summaries; shortlisted segment detail returns only the segment's transcript excerpt with minimal neighboring context.
- Sensitive transcript content is redacted from downstream payloads by default and remains available only to the authorized knowledge-review workflow.
- A transcript is an audio observation and never becomes formal product knowledge without independent evidence and review.
- Every **Video Content Profile** references **Video Analysis Provenance** containing tool and model versions, analysis-policy version, prompt-template version or hash, input frame, clip, and transcript identifiers, source classification, validation result, and human acceptance or modification events.
- The formal profile stores decision-relevant provenance references and revision identifiers; verbose commands, prompts, timings, stdout, stderr, and stage logs remain in generated reports.
- A changed model, prompt template, tool behavior, or analysis policy can select affected profiles for re-analysis through their provenance and **Video Profile Revision**.
- Each material observation or segment can be traced to supporting analysis frames, clips, and transcript ranges without exposing those complete inputs to downstream consumers.
- A **Video Profile Amendment** may correct classification, segment description, small timestamp-boundary errors, risk state, evidence links, and preferred or alternative segment relationships.
- Amendments require a modification preview, target profile and item identity, original machine proposal, revised value, reason, reviewer, and timestamp.
- Applying an amendment revalidates the profile, refreshes and verifies the Agent interface, and invalidates affected downstream contexts.
- Amendments do not modify raw source video or rewrite analysis cache artifacts.
- Source changes, missing primary content caused by inadequate sampling, systemic errors, invalid media metadata, and analysis-policy upgrades require full re-analysis rather than amendment.
- A **Video Use Exclusion** records target scope, restriction scope, reason, reviewer, timestamp, and current status.
- Restriction scope may prohibit all downstream use, external use only, direct clip reuse only, original-audio reuse only, or selected key segments.
- Excluded sources and segments remain in formal knowledge for audit and asset-family relationships but are filtered from prohibited downstream retrieval and extraction.
- Applying or restoring an exclusion refreshes and verifies the Agent interface and triggers **Video Source Revocation** handling for active tasks when applicable.
- Exclusion never deletes, moves, renames, or modifies raw media.
- A **Video Profile Migration** is allowed only for structural changes or new values deterministically derivable from the prior validated profile.
- Migration revalidates the converted profile, preserves the previous revision, and records the migration rule and outcome.
- Any new field requiring visual, temporal, audio, identity, risk, or multimodal judgment makes the prior profile stale and requires re-analysis.
- Missing semantic values must not be filled with defaults that imply the source was newly analyzed.
- A profile that does not satisfy the current downstream contract remains unavailable for automatic selection until migration or re-analysis completes.
- The default **Video Analysis Budget** allows up to twenty-four analysis frames, up to six analysis clips of roughly three to twelve seconds, and three to six representative frames per source video.
- Complete useful speech may be transcribed in chunks rather than truncated, and multimodal inputs are divided by chapter or segment when they exceed one analysis context.
- Complex or long videos automatically segment and escalate analysis depth within the already confirmed batch workflow.
- If the budget cannot provide reliable coverage, the source is marked as requiring deeper analysis rather than silently publishing an incomplete profile.
- Batch receipts disclose every automatic depth escalation and its reason.
- An analysis budget controls cost and execution shape; it never authorizes hiding unobserved portions or claiming processing completeness.
- **Video Analysis Cache Retention** keeps the three to six representative frames referenced by the current valid profile for the lifetime of that profile revision.
- Other analysis frames and **Video Analysis Clips** remain available through batch acceptance and are eligible for automatic cleanup thirty days after acceptance.
- Cache supporting a review-required, failed, disputed, or actively investigated result is retained until that issue is resolved.
- **Task Video Frames**, **Task Video Clips**, and task previews follow the retention policy of their owning **Video Creation Run** rather than the knowledge-analysis cache policy.
- Cleanup operates from an explicit cache manifest containing source fingerprint, profile revision, cache role, creation time, acceptance state, and live references.
- Cleanup must not infer disposability from a directory name or file extension and must skip any artifact referenced by a current profile, unresolved review, or active run.
- Cache cleanup never deletes, moves, renames, rewrites, or recompresses raw source video.
- Every **Video Profile Batch** runs a **Video Analysis Capability Preflight** before processing begins.
- `ffprobe` is mandatory for duration, stream, codec, resolution, frame-rate, rotation, and audio-track inspection.
- `ffmpeg` is mandatory for analysis-frame extraction, **Video Analysis Clips**, and precise runtime frame and clip extraction.
- An available Codex session capable of **Codex Video Semantic Review** is mandatory for publishing descriptions, key actions, visibility, classification, and reuse semantics.
- The current release does not require or accept a user-supplied API key for video semantic analysis and does not silently call a separately configured cloud multimodal model.
- The knowledge-base Agent prepares only the bounded analysis frames, necessary analysis clips, deterministic media facts, folder classification, and available transcript inputs selected by the confirmed batch policy; Codex does not receive general raw-directory browsing authority.
- A **Speech Transcription Adapter** is optional and follows the explicit incomplete-audio rules when unavailable.
- Optional quality, duplicate-detection, or supporting analysis components may use a documented controlled fallback when the fallback still satisfies the profile contract.
- The preflight receipt records tool availability, versions, configured adapters, controlled fallbacks, and unsupported capabilities.
- A missing mandatory capability blocks the batch before source processing, consumes no batch work, and does not mark individual videos failed.
- An unexpected component failure during processing is isolated to the affected source when local; a systemic failure pauses the applicable **Video Batch Impact Scope** and prevents publication of suspect profiles.
- Each reusable **Video Key Segment** has a **Source Audio Use Policy** of retain, mute-recommended, mute-required, or human-review-required.
- Privacy-bearing speech, customer identity, unclear publication consent, and suspected copyrighted music prevent automatic original-audio reuse.
- Every **Video Content Profile** carries a **Video Profile Revision** tied to the source-video content, source classification, profile schema, and analysis policy.
- A changed source-video fingerprint invalidates all prior observations, segments, representative frames, and audio analysis until the profile is rebuilt.
- A changed source path or source-folder classification invalidates source classification and requires classification reconciliation even when video bytes are unchanged.
- A changed profile schema or analysis policy marks older profiles for re-analysis rather than silently treating them as current.
- Missing representative-frame files may be rebuilt from a still-valid source and profile revision; semantic revision mismatch requires full re-analysis.
- An invalid or failed profile may leave its **Video Asset Card** visible as a registered asset, but the Agent interface must not publish its stale semantic content as usable.
- A **Video Creation Run** locks its Agent-interface revision and does not silently switch to a rebuilt profile during the active task.
- Each source video is an atomic profile-processing unit with its own **Video Profile Processing State**.
- One video's bounded analysis inputs, Codex proposal, formal structured profile, representative-frame references, structural validation, and processing state are persisted as a **Video Profile Checkpoint** before the next source begins.
- A valid checkpoint is resumable only when its source fingerprint, source classification, profile schema, analysis policy, and required capability revisions still match.
- After interruption, the batch resumes at the first missing, failed, stale, or invalid checkpoint and does not re-analyze unchanged valid checkpoints.
- A checkpoint preserves completed work but does not bypass the batch's required acceptance or **Video Batch Maturity** publication gate.
- **Video Profile Checkpoints** are written to a batch staging area and remain available to the knowledge-review workflow but invisible to downstream Agent-interface retrieval.
- Accepted profiles enter the formal knowledge layer only through a **Video Profile Publication Transaction**.
- The transaction promotes the allowed staged profiles, rebuilds the Agent interface, and verifies that the new profile and representative-frame references are readable under the expected interface revision.
- If promotion, interface rebuild, or verification fails, the new interface revision is not activated, downstream consumers continue using the last verified revision, and the batch is reported incomplete.
- Failed, review-required, stale, and excluded staging outcomes remain visible to knowledge maintenance while being omitted or filtered from downstream selectable catalog results according to their state.
- Stable optimistic publication still uses one atomic profile promotion plus verified interface activation; it never exposes staging files directly.
- A scoped rollback or revocation removes only the affected publication range and preserves the last unaffected verified knowledge and interface state.
- Video processing completion is determined by a current, structurally valid **Video Content Profile** whose source and analysis revisions match; the existence of extracted images alone is insufficient.
- Existing **Legacy Video Frame Cache** files remain rebuildable historical artifacts and cause every video without a valid profile to report as registered but awaiting profile generation.
- A legacy frame may be reused only when the new pipeline verifies its source revision, timestamp provenance, quality, and relevance; it is never promoted automatically into a representative frame or observation.
- Product and subfolder progress are recalculated from profile states rather than from the presence of any JPG, JPEG, or PNG under the old cache path.
- A failed source video does not roll back other valid profiles; validated profiles may be published incrementally through a verified Agent-interface refresh.
- Failed, incomplete, or stale profiles expose no usable semantic payload to downstream consumers, while their registered **Video Asset Cards** and concrete processing errors remain visible to the knowledge workflow.
- Product-level progress separately reports registered videos, valid profiles, pending profiles, failed profiles, review-required profiles, and explicitly excluded videos.
- A product partition is not “video processing complete” until every registered video has a valid profile or an explicit human exclusion.
- **Video Material Retrieval** is limited to valid **Video Content Profiles** already authorized in the current **Video Creation Context**.
- Structured filtering precedes semantic ranking and may constrain product, source scenario, observed classification, **Video Use Capability**, product visibility, motion continuity, reuse mode, crop suitability, human risk, audio policy, and profile state.
- Semantic ranking currently uses profile summaries, **Video Key Segment** descriptions, action and visual descriptions, audio transcripts, and preserved source-folder context.
- Formal video-profile fields, source-folder classification, actions, visibility, risks, use capabilities, titles, summaries, and segment descriptions are indexed as structured and textual retrieval inputs.
- After structured and textual retrieval produces a bounded authorized candidate set, **Codex Representative Frame Rerank** opens the candidates' representative frames and evaluates composition, action, subject presentation, scenario appearance, clarity, crop suitability, and near-duplicates.
- Structured product, authorization, profile-state, exclusion, and risk filters always run before Codex visual reranking.
- The current interface reports `visual_vector_index_unavailable` and `codex_visual_rerank_available`; it must not claim persistent image-vector search.
- The first implementation does not install a local visual-embedding model and does not request an API key for one.
- A future **Representative Frame Visual Index** may improve initial recall at larger scale, but it remains subject to the same hard filters and cannot independently establish product identity, application truth, test result, or another product fact.
- Adding or replacing a future visual-embedding model rebuilds only that derived index and provenance without changing accepted profile observations or human-review decisions.
- Semantic relevance cannot override a structured blocker, broaden product scope, authorize raw discovery, or convert a **Video Observation** into a product fact.
- Plan review may use **Video Representative Frames**, profile summaries, key-segment ranges, and use-capability descriptions without extracting every candidate clip.
- Before storyboard confirmation, every directly reused **Task Video Clip** must be extracted and presented as a **Task Video Preview** with source asset, exact source range, visible-action description, source-audio policy, and risks.
- A shot that uses a **Task Video Frame** must show the exact extracted image rather than only its profile representative frame.
- A direct-clip shot cannot be confirmed from text or one profile preview image alone, and the clip may not be replaced after confirmation without resetting storyboard confirmation.
- Automatic **Meaning-Preserving Video Adaptation** may trim the selected range, honor source rotation metadata, transcode at high quality, normalize resolution and frame rate, apply the confirmed 9:16 crop or padding, and mute audio according to the **Source Audio Use Policy**.
- Any speed change, stabilization, color or sharpness manipulation, denoising, internal action removal, mirroring, chronology change, frame interpolation, or generative extension must be disclosed and requires confirmation when it could change motion perception or visual authenticity.
- No adaptation may change the apparent action, before-and-after order, product identity, test state, or meaning of a **Video Observation**.
- The storyboard records the source range and every planned adaptation so the confirmed **Task Video Preview** matches the intended task output.
- The Agent interface exposes video semantics in three stages: **Video Profile Catalog**, on-demand **Video Content Profile** detail, and authorized runtime extraction.
- A **Video Profile Catalog** entry includes only decision-relevant summary fields such as source classification, observed classifications, use capabilities, product visibility, reuse modes, risk summary, profile state, and representative-frame references.
- The three-stage image delivery path is catalog thumbnail reference, full-profile representative-frame reference, then run-local exact **Task Video Frame** or **Task Video Clip** after a concrete use is selected.
- Complete key segments, anchor moments, observations, audio transcripts, and detailed risks are loaded only for shortlisted profile IDs.
- Source-video bytes are read only after a concrete segment or anchor is selected for **Runtime Clip Extraction** or **Runtime Frame Extraction**.
- Building a **Video Creation Context** must not inject every complete video profile or transcript into the downstream context.
- **Video Material Retrieval**, candidate comparison, profile-detail loading, reuse-mode choice, and proposed source-segment assignment are **Professional Video Decisions** owned by the **Video Creation Consumer**.
- The user does not complete a separate source-video selection workflow before planning; the plan explains the recommended real-footage strategy, and the storyboard shows the exact **Task Video Previews** and **Task Video Frames**.
- A separate user question is required only when materially different source choices imply different business meaning and the **Confirmed Video Brief** cannot resolve the choice.
- Replacing a proposed video or segment remains available through natural-language plan or storyboard revision.
- Every externally proposed test-process or before-and-after segment passes the **Test-Footage Publication Gate**.
- Formally supported test footage may communicate only the conditions and conclusions covered by its linked evidence.
- Unsupported but clearly identified test footage may be shown only with neutral observation language and explicit review risk; it must not use words or editing that imply passing, proof, certified performance, temperature tolerance, or causality.
- Unclear product identity, unclear test conditions, or ambiguous before-and-after meaning blocks external use.
- Runtime trimming must not hide an adverse result, reorder test states, or manufacture a more favorable comparison.
- Unsupported spoken test conclusions must be muted or excluded from externally reused clips.
- The **Video Understanding Pipeline** obtains duration, resolution, frame rate, rotation, streams, and audio presence from deterministic media inspection rather than model inference.
- Deterministic extraction produces broad samples, change candidates, exact anchor frames, and analysis media without modifying the source video.
- Quality checks identify black, severely blurred, and near-duplicate frames before semantic interpretation.
- Time-coded speech transcription runs only when useful speech is present and remains separate from verified product knowledge.
- **Codex Video Semantic Review** combines source classification, ordered visual evidence, analysis clips when required, and audio observations to propose summaries, segments, observations, classifications, use capabilities, and risks.
- Codex semantic output must conform to the formal profile schema and pass source-link, timestamp-range, required-field, risk, and structural validation before it can be published.
- The original Codex proposal is not itself formal knowledge; only its validated profile representation and accepted human-review state enter the knowledge layer.
- Analysis provenance records the available Codex runtime or model identity, policy and prompt-template revision, bounded media inputs, validation outcome, and human changes when that identity is exposed by the execution environment.
- If Codex cannot inspect the prepared visual inputs in the current environment, **Video Analysis Capability Preflight** blocks the batch rather than falling back to an unknown service or publishing filename-based semantics.
- Structural validation verifies source revision, timestamp bounds, representative-frame existence, segment consistency, required risk fields, and review boundaries before publication.
- Tool failure and semantic uncertainty remain explicit **Video Profile Processing States**; the pipeline must not fabricate missing media facts.
- Ordered **Video Analysis Frames** are the default semantic input for static product views, slow environment views, and frame-reference-only assets.
- The pipeline creates **Video Analysis Clips** only when continuous action, process completion, before-and-after change, rapid motion, inconsistent frame evidence, or likely direct clip reuse requires temporal verification.
- **Video Analysis Clips** are low-cost rebuildable cache artifacts; they are not published through the Agent interface and are distinct from final **Task Video Clips**.
- A **Video Content Profile** has one canonical Chinese semantic description; the system does not maintain separate Chinese and English profile variants.
- Stable classification, role, risk, state, confidence, reuse-mode, and audio-policy codes remain language-independent.
- Source speech transcripts preserve their original language and may include a Chinese interpretation for knowledge maintenance.
- A downstream task translates only the profile excerpts needed for its selected **Video Language Version** and does not write those translations back to the profile.
- The canonical **Video Content Profile** is maintained in the formal knowledge layer because its semantic observations, time ranges, risks, and reuse guidance persist across downstream tasks.
- The formal knowledge layer provides a human-readable profile card and a one-to-one machine-validatable structured profile representation.
- A valid published **Video Content Profile** may be official under **Visual Observation Scope** even when its observations were produced automatically.
- Card validity answers whether the profile is current and structurally usable; **Visual Observation Scope** answers what downstream consumers may do with it; observation confidence answers how certain each visual interpretation is.
- **Visual Observation Scope** permits search, candidate ranking, material selection, storyboard planning, runtime extraction, and editing decisions but never upgrades a **Video Observation** into a verified product fact.
- Each observation, key segment, classification, transcript item, and reuse recommendation has its own **Video Observation State** and confidence.
- Profile publication is blocked only when the source cannot be read, asset identity or product scope is untrustworthy, timestamp bounds are invalid, primary content cannot be understood, all representative frames are unusable, or structural validation fails.
- Local uncertainty such as one dark interval, unclear action, uncertain scenario, partial product visibility, unclear speech, or uninterpretable test outcome remains attached to that item and does not invalidate unrelated usable observations.
- Low-confidence or review-required items remain auditable in profile detail but are excluded from automatic **Video Material Retrieval** and automatic segment assignment.
- Every automatically usable item has **Video Observation Confidence** with a normalized level or score, supporting reasons, and explicit warnings.
- Confidence may incorporate source classification agreement, repeated-frame consistency, analysis-clip support, visible duration and area, temporal continuity, audio-visual agreement, image quality, occlusion, conflicting analysis results, and supported product identity.
- Source-folder agreement may raise confidence but cannot establish visible content by itself.
- A model may interpret evidence but cannot publish an unexplained confidence label without traceable supporting signals.
- Semantically similar **Video Key Segments** within one source video form a **Video Segment Group**.
- Each **Video Segment Group** identifies one preferred segment using product clarity, action completeness, crop suitability, occlusion and face risk, audio risk, stability, and useful duration.
- Non-preferred group members remain available as ranked alternatives with explicit reasons rather than being deleted.
- Frame-level black, blur, and near-duplicate filtering may remove redundant analysis frames, but it must not substitute for semantic segment grouping.
- **Video Material Retrieval** returns preferred group members by default and may expand to alternatives when a task constraint cannot be satisfied.
- Cross-video comparison creates **Video Asset Families** after individual valid profiles exist.
- A **Video Asset Family** distinguishes exact content duplicates, near-duplicate encodes or edits, complementary multi-angle recordings of the same event, and semantically similar but separate scenes.
- Exact and near-duplicate families may identify a preferred source using media quality, completeness, crop suitability, risk, and profile confidence; all registered sources remain traceable.
- Complementary multi-angle family members remain co-preferred when their different views add real planning value.
- Asset-family relationships influence retrieval ranking and duplicate warnings but never merge, move, rename, or delete raw videos automatically.
- Initial profile rollout proceeds in business-verifiable batches rather than one unbounded full-library run.
- The first batch is the fixed product-video folder so identity, product visibility, representative frames, key segments, and direct clip reuse can be validated on a small set.
- Application videos are processed next, one canonical **Source Application Scenario** folder at a time.
- Test and validation videos are processed last because test interpretation, before-and-after observations, evidence linkage, audio handling, and the **Test-Footage Publication Gate** require the most mature pipeline behavior.
- After the initial rollout, only new, changed, stale, or explicitly re-requested profiles are processed.
- The initial product-video batch receives full **Video Profile Batch Acceptance** across all source videos.
- For the first batch of each **Source Application Scenario**, a batch of ten or fewer profiles is reviewed in full; a larger batch reviews at least five profiles covering preferred segments, low-confidence items, long videos, and videos with audio.
- After a scenario's pipeline behavior is stable, later batches review ten percent with a minimum of three profiles.
- Test and validation batches receive full review of external-use risk fields, and every test segment proposed for an external task is reviewed again through the task workflow.
- A systemic sampling, classification, timing, audio, or risk error blocks batch acceptance and requires affected profiles to be rebuilt after the rule is corrected.
- **Video Profile Batch Acceptance** validates semantic extraction quality and risk handling; it does not authorize unsupported product claims.
- Ordinary users start video-profile work through natural language and confirm exactly one proposed **Video Profile Batch** at a time.
- Before confirmation, the knowledge producer shows the batch's source category or scenario, video count, planned outputs, tool use, raw immutability, and acceptance level.
- After confirmation, deterministic inspection, adaptive extraction, semantic analysis, profile validation, representative-frame generation, staging, acceptance, and the required **Video Profile Publication Transaction** run as one batch workflow without per-file user commands.
- Internally, that workflow processes one video at a time and saves a **Video Profile Checkpoint** after each atomic result so the user still manages one batch while execution remains resumable.
- The batch enters acceptance only after every in-scope source has a valid, review-required, failed, stale, or excluded checkpoint outcome.
- Gated batches publish selectable profiles only after unified batch acceptance; stable optimistic batches may follow their previously defined monitored publication rule.
- A systemic defect invalidates or withdraws the affected checkpoints according to **Video Batch Impact Scope**, even when those checkpoints were individually valid.
- A batch completion receipt reports valid, failed, stale, review-required, and excluded profiles; representative frames; detected asset families; the required acceptance sample; and the verified Agent-interface revision.
- A batch completion receipt shows six to twelve overview representative images selected across different source videos, main use capabilities, and notable low-confidence or risk examples.
- Full three-to-six-frame profile previews are shown only when reviewing one selected video profile or its required acceptance sample.
- Test-validation overview imagery prioritizes visibly available before, process, and after examples without implying a test conclusion.
- Users are not required to open profile JSON, analysis logs, or cache directories to perform batch acceptance.
- The next batch is recommended only after the current batch reaches its required acceptance outcome.
- Initial product-video, first-scenario, and test-validation batches have gated **Video Batch Maturity**: their profiles may be inspected through the knowledge workflow but cannot enter downstream automatic selection before required acceptance.
- Stable incremental application batches may publish high-confidence valid profiles optimistically while their prescribed sample is reviewed.
- If monitored sampling finds a systemic defect, every profile from the affected batch is marked unusable, removed from downstream retrieval through a verified Agent-interface refresh, and rebuilt after the rule is corrected.
- Test-validation profiles never enter external automatic selection before their required risk-field acceptance.
- Batch publication state is distinct from individual **Video Profile Processing State** and **Video Observation State**.
- A systemic sampling, timestamp, classification, privacy, rights, or publication-gate defect defines a **Video Batch Impact Scope** and pauses or revokes every affected batch, scenario, or category.
- An isolated corrupt file, local misclassification, or one review item remains confined to the affected profile or segment and does not mechanically block unrelated batches.
- A category-specific defect pauses only the relevant source category when other categories remain demonstrably valid.
- Batch acceptance reports the detected impact scope and the exact work that may continue safely.
- The video-profile model, validation rules, and understanding pipeline are designed to support future knowledge partitions without product-specific schema assumptions.
- The initial business integration processes only videos under the five fixed quartz-fiber-tape product material folders.
- Company, workshop, laboratory, market, customer, and shared-media video integration remains outside the initial rollout and requires its own ownership, authorization, privacy, and downstream-scope decisions.
- The initial **Video Creation Context** continues to authorize only the quartz-fiber-tape product scope even though the underlying profile capability is reusable.
- The first implementation milestone is complete only when a **Video Knowledge-to-Creation Tracer** succeeds with a real product video.
- Implementation begins with one real product-video tracer before building broad batch orchestration.
- After the single-source tracer passes, the same path expands to the complete fixed product-video batch and receives full acceptance.
- Application-scenario batching begins only after the product-video path is accepted; test-validation integration remains last.
- Batch-scale abstractions must be extracted from the proven tracer rather than designed independently of downstream storyboard and assembly needs.
- The **Tracer Source Video** is decodable, contains a meaningful continuous product action with at least two observable stages, includes a clearly visible product interval, and has `ready` or `adaptable` editing potential.
- The tracer source should be roughly fifteen seconds to two minutes when available, may include useful low-risk audio, and avoids clear-face, privacy, rights, and test-interpretation complexity.
- A static product view or test-validation recording is not selected merely because it is easiest to process.
- If no source satisfies every preferred property, the tracer records which capability could not be exercised and schedules that capability in the full product-video batch.
- Before implementation locks the tracer source, the Agent inspects all videos in the fixed product-video folder and recommends one **Tracer Source Video** using actual media facts and visual evidence rather than filenames.
- The recommendation shows source identity, duration, observable action stages, product visibility, audio presence, major risks, and three to six preliminary frames.
- Selecting the tracer source is an explicit implementation-scope confirmation because the sample determines which end-to-end capabilities the first milestone proves.
- Tracer-source inspection does not publish a formal profile or modify the knowledge layer.
- Preliminary tracer-selection frames live in **Tracer Candidate Inspection Cache**, separate from formal profile analysis media and every **Video Creation Run**.
- The cache is organized by source fingerprint, may be reused only when it satisfies the accepted analysis rules, and may otherwise be rebuilt.
- Unselected candidate media may be cleaned without touching raw; the candidate report, recommendation, and user confirmation remain auditable.
- Candidate inspection files do not count as processed video frames in knowledge status and never enter the Agent interface.
- Accepted video-profile decisions must be synchronized across the domain glossary, architecture decisions, product requirements, implementation slices, and test boundaries.
- The PRD explicitly supersedes older statements that knowledge-base videos are unavailable to planning or generation when an authorized valid profile and segment now permit use.
- Vertical implementation slices follow the accepted order: tracer source inspection, one real end-to-end tracer, full product-video batch, application-scenario batches, and final test-validation batches.
- Tests must stop asserting that all video content assets are excluded and instead verify authorized catalog retrieval, profile detail loading, runtime extraction, direct clip reuse, risk gates, revocation, and raw immutability.
- The tracer preserves the raw source hash; creates and validates its asset card, semantic profile, representative frames, revision, and provenance; publishes and retrieves it through the three-stage Agent interface; and performs runtime extraction by **Video Asset ID**.
- The tracer shows the exact task clip and frame, source range, audio policy, risks, and adaptations in storyboard confirmation and uses the real task clip as an assembly input rather than regenerating it.
- The tracer verifies that arbitrary raw paths are rejected, stale profiles are not published as usable, and a high-risk revocation blocks later confirmation or submission.
- Adding an extraction script, cache images, card type, JSON schema, or catalog endpoint without downstream storyboard and assembly use is not completion.
- Runtime-extracted task files remain in their **Video Creation Run** for audit when their source receives **Video Source Revocation**; the system does not silently delete or replace them.
- Plan confirmation, storyboard confirmation, and real external submission recheck the current source-revocation state for every selected profile and segment.
- Before plan confirmation, revoked candidates are re-retrieved; before storyboard confirmation, affected previews are regenerated from approved replacements.
- After storyboard confirmation but before real submission, a revocation blocks submission until the affected material is replaced or an allowed non-high-risk override is explicitly confirmed.
- Product-identity, privacy, test-misrepresentation, and rights-related revocations cannot be overridden inside the video task.
- Completed or already-submitted runs preserve their historical artifacts and record the later revocation rather than rewriting prior state.
- The local single-user workflow authorizes runtime extraction through the combined **Video Creation Run** identity, locked Agent-interface revision, **Video Asset ID**, profile revision, allowed operation, and current revocation check.
- The local workflow does not require short-lived extraction tokens; signed short-lived authorization is reconsidered only if extraction becomes a remote or multi-user service.
- Every attempted runtime extraction writes a **Runtime Video Extraction Audit**, including rejected attempts.
- For one planned visual use, the video consumer may extract at most three **Candidate Video Previews** when profile text and representative frames cannot reliably distinguish shortlisted segments.
- Candidate previews use analysis-quality output and do not receive final crop, encoding, or other delivery adaptations.
- High-cost or delivery-quality **Meaning-Preserving Video Adaptation** runs only after one segment is selected.
- Plan review normally shows the Agent's recommended material; materially different business meanings may require showing alternatives and asking one focused question.
- Unselected candidate previews remain task inspection artifacts and never enter formal knowledge or the confirmed storyboard.
- **Video Analysis Frames** and **Video Analysis Clips** remain rebuildable generated cache artifacts; their selected **Video Representative Frames** are generated files referenced by the formal profile rather than raw evidence files.
- The Agent interface rebuilds its **Video Profile Catalog** and on-demand profile details from the formal profile representation; downstream consumers do not parse knowledge Markdown directly.
- **Video Source Classification** guides sampling and classification but cannot override contradictory or absent visual observations.
- Matching source and observed classifications may increase confidence; a conflict must remain visible to downstream consumers and may require review when it affects product identity or external interpretation.
- Downstream material selection uses the time-ranged **Video Observed Classification** and **Video Use Capabilities**, while retaining source classification as provenance.
- High-confidence **Video Observations** may be published for downstream planning without per-video human approval.
- Ambiguous product identity, uncertain scene classification, and every **Video Claim Interpretation** must enter knowledge review rather than downstream planning facts.
- When the video consumer selects a source video for a concrete shot, it must visually recheck the relevant time-coded **Video Observations** through **Runtime Frame Extraction**.
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
- `raw_access=false` forbids raw-directory discovery and arbitrary file reads; it does not forbid **Runtime Frame Extraction** or **Runtime Clip Extraction** through an **Authorized Video Reference**.
- Runtime extraction must validate the selected video against the current **Video Creation Context**, read the source video without modifying it, and write **Task Video Frames** or **Task Video Clips** only inside the current **Video Creation Run**.
- Frames created by **Runtime Frame Extraction** are task artifacts, not formal knowledge or reusable evidence, unless a later knowledge-producer workflow explicitly reviews and publishes them.
- Clips created by **Runtime Clip Extraction** are task artifacts, not formal knowledge or replacements for their source **Video Content Profiles**.
- Runtime frame selection starts from published **Video Anchor Moments**.
- If an anchor does not satisfy the task composition, the consumer may inspect a bounded neighborhood and then at most five candidate frames within the authorized **Video Key Segment** for that shot.
- Runtime frame exploration cannot cross the authorized key-segment bounds or scan the whole source video.
- The selected **Task Video Frame** must pass the same pixel-level subject, clarity, composition, crop, duplication, identifier, and person-risk checks required for storyboard imagery.
- User-provided wording preferences may influence creative treatment, but task-specific product facts, parameters, performance claims, or promises that are absent from formal knowledge cannot enter a video.
- New product facts must be confirmed and published through the knowledge producer before video creation uses them; the video consumer has no one-run fact exception.
- The video workflow uses formal knowledge-card text, image content assets, and authorized video profiles; usable real source-video segments may be selected for planning and direct clip reuse.
- When real application imagery is unavailable, Dreamina may generate a simulated application scene only for applications confirmed by formal knowledge.
- AI-generated scenes must be identified as generated in the run record and must not be represented as a real customer case, real test record, or product-performance evidence.
- Generated scenes must not introduce unsupported equipment details, parameters, applications, or performance outcomes.
- Shot material selection prefers a suitable real **Task Video Clip**, then a real image or **Task Video Frame** animated into video, then an evidence-safe AI-simulated scene, and finally text-only generated video.
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

> **Dev:** "When the search finds someone whose profile mentions exhaust wrap, have we found a customer?"
> **Domain expert:** "No. We have a **LinkedIn Discovery Candidate**; the workflow still needs evidence-based relevance checks before considering a **Connection Invitation**."

> **Dev:** "Does the owner's **Account-Risk Acceptance** mean LinkedIn has authorized the automation?"
> **Domain expert:** "No. It records the owner's business decision and account risk only; it is not platform permission or a guarantee against restriction."

> **Dev:** "Can yesterday's browser approval authorize today's prospecting run?"
> **Domain expert:** "No. Each **Automated LinkedIn Prospecting Run** needs a new **Prospecting Run Authorization** tied to its reviewed scope and action limit."

> **Dev:** "Can one run search for customers and competitors with the same rules?"
> **Domain expert:** "No. Choose one **Prospecting Target Intent**; the first release supports potential-customer discovery and keeps competitor intelligence separate."

> **Dev:** "Must the first release prove lead quality with acceptance and error-rate metrics?"
> **Domain expert:** "No. Under the **First-Release Evaluation Boundary**, first make the agreed connection workflow work; optimize candidate fit in a later version."

> **Dev:** "Does a run wait until the recipient accepts the invitation?"
> **Domain expert:** "No. The first release completes that item at **Invitation Dispatch Success**, when LinkedIn confirms the invitation was submitted."

> **Dev:** "Does the first release search member profiles directly with product keywords?"
> **Domain expert:** "No. Use **Post-First Prospect Discovery**: search relevant content first, then inspect the people surfaced by those posts."

> **Dev:** "Should a company visibly manufacturing the same insulation material be inferred to be a buyer?"
> **Domain expert:** "No. Treat it as a **Direct Category Manufacturer** and skip it unless visible evidence establishes a distinct downstream-use role."

> **Dev:** "Should a brand selling a finished exhaust wrap be excluded merely because it sells the same category?"
> **Domain expert:** "No. Treat it as a provisional **Same-Category Channel Prospect** when it may brand, distribute, retail, or private-label externally sourced goods, and expose uncertainty for human review."

> **Dev:** "Must an installer or fabricator publish an RFQ before it can continue?"
> **Domain expert:** "No. A **Downstream Material User** may continue when its visible services or finished products plausibly consume the referenced material category."

> **Dev:** "Can the workflow connect directly to a company page or invite several of its employees?"
> **Domain expert:** "No. Use **Company Contact Resolution** to select at most one prioritized member from that company in the current run."

> **Dev:** "May the workflow pick any employee when none of the prioritized roles exist?"
> **Domain expert:** "No. Skip that company; changing the eligible role set belongs to a later version or newly scoped run."

> **Dev:** "Can tomorrow's run process the same profile under a different keyword?"
> **Domain expert:** "No. Consult the **Prospecting Contact Ledger**; skip successful and pending invitations across runs, and retry only when no invitation was actually submitted."

> **Dev:** "Does the first release always send invitations without a note?"
> **Domain expert:** "No. The current operator makes an **Invitation Note Decision** during the **Prospecting Interview**, and reviews it in the **Confirmed Prospecting Brief** before authorizing the run."

> **Dev:** "May the workflow rewrite the invitation note for each candidate?"
> **Domain expert:** "No. The first release uses either no note or one fixed, operator-confirmed note for the whole **Approved Candidate Batch**."

> **Dev:** "Should the interview ask which customer region to search?"
> **Domain expert:** "Not in the first release. Geography does not map to the post-search controls, so collect only **Supported Post Search Criteria**."

> **Dev:** "Must the operator answer every filter shown by LinkedIn before a run can start?"
> **Domain expert:** "No. Resolve the **Core Post Search Criteria** every time and ask about other supported filters only when they are relevant."

> **Dev:** "Can one run search exhaust wrap and silencer wrap?"
> **Domain expert:** "Yes. Put them in an **Ordered Content Keyword List**, search them sequentially, and retain the source keyword on every discovered candidate."

> **Dev:** "If a run has three keywords and a limit of ten, may it send thirty invitations?"
> **Domain expert:** "No. The **Successful Invitation Limit** is global; stop after ten confirmed dispatches across all keywords."

> **Dev:** "What invitation limit should the interview recommend when the operator gives none?"
> **Domain expert:** "Recommend the **Default Run Invitation Limit** of ten, while still enforcing the separate **Seven-Day Invitation Ceiling**."

> **Dev:** "Does the one-hundred-invitation ceiling reset every Monday?"
> **Domain expert:** "No. Recalculate the **Seven-Day Invitation Ceiling** over the rolling one-hundred-sixty-eight hours before each dispatch."

> **Dev:** "Does the local seven-day count include invitations an employee sent manually?"
> **Domain expert:** "No. The first release counts only skill-recorded dispatch successes and discloses that manual invitations remain outside the count."

> **Dev:** "May a requested ten-person run proceed when only four local seven-day slots remain?"
> **Domain expert:** "Only after the brief shows an **Effective Run Invitation Limit** of four and the operator confirms that explicit reduction."

> **Dev:** "Must the workflow loosen filters until it fills the invitation limit?"
> **Domain expert:** "No. Use **Search Exhaustion Completion** and report the actual dispatch count; broader criteria require a newly authorized run."

> **Dev:** "Which post ordering should the interview recommend?"
> **Domain expert:** "Recommend Latest in the **Post Sort Decision** to favor active same-category sellers, while allowing the operator to choose Most Relevant."

> **Dev:** "May the workflow send invitations immediately after it finds a matching post?"
> **Domain expert:** "No. Print a **Candidate Review Card** in Codex and wait at the **Pre-Dispatch Candidate Review** gate before any invitation is submitted."

> **Dev:** "Can the Agent present a plausible installer as a confirmed potential customer?"
> **Domain expert:** "No. Record only **Provisional Candidate Fit**, print the complete source post and identity evidence, and let the operator make the final batch decision."

> **Dev:** "Should a relevant company without a verifiable connectable member consume one of ten candidate slots?"
> **Domain expert:** "No. Record an **Unresolved Relevant Lead** and continue scrolling for an actionable candidate."

> **Dev:** "Does approving ten candidates mean ten invitations may be submitted at once?"
> **Domain expert:** "No. The **Approved Candidate Batch** is dispatched sequentially, with the confirmed **Invitation Dispatch Interval** between submissions."

> **Dev:** "Is the invitation interval hidden or permanently fixed by the program?"
> **Domain expert:** "No. The operator confirms it for every run, with five minutes shown as the recommendation in the **Prospecting Interview**."

> **Dev:** "If the operator rejects three of ten candidates, should the run find three replacements?"
> **Domain expert:** "No. Use a **Closed Candidate Batch**, dispatch only the approved remainder, and create a new run for further discovery."

> **Dev:** "Must the operator confirm again before every approved member is contacted?"
> **Domain expert:** "No. **Final Batch Dispatch Authorization** covers the exact displayed batch, account, note decision, and interval; then dispatch proceeds sequentially."

> **Dev:** "Can the run use whichever LinkedIn account happens to be logged in?"
> **Domain expert:** "No. Confirm one **Bound LinkedIn Account** by name and profile URL, and block if authentication is missing or the account changes."

> **Dev:** "Should the workflow scroll indefinitely until it fills the candidate batch?"
> **Domain expert:** "No. Apply the **Keyword Post Inspection Limit** of fifty opened posts, then advance to the next keyword or finish with the candidates found."

> **Dev:** "Does a matching hashtag automatically make the post a prospect source?"
> **Domain expert:** "No. Record a **Post Relevance Decision** from the visible content and continue only when the post concerns commercial activity around the target category."

> **Dev:** "Should a relevant individual author be replaced by a higher-ranking employee from the same company?"
> **Domain expert:** "No. Use the verified **Individual Post Author Candidate** directly; search employees only when the post author is a company page."

> **Dev:** "May the workflow guess an email when LinkedIn requires one before connecting?"
> **Domain expert:** "No. That member lacks **Standard Connect Eligibility** for the first release; record the reason and skip."

> **Dev:** "Should one missing Connect button terminate the whole batch?"
> **Domain expert:** "No. Record a **Candidate-Local Dispatch Failure** and continue; terminate only for a **Platform-Level Dispatch Stop** signal."

> **Dev:** "May dispatch resume automatically after the operator completes a security check?"
> **Domain expert:** "No. End the current run as incomplete and require an **Authorized Dispatch Restart** with fresh account and batch confirmation."

> **Dev:** "Should a discovered LinkedIn profile be written directly into the formal potential-customer knowledge folder?"
> **Domain expert:** "No. Keep it as **Operational Prospecting Data** in generated reports; formal market-intelligence write-back belongs to the knowledge-base workflow."

> **Dev:** "Should post-based prospect discovery be added to the existing LinkedIn campaign skill?"
> **Domain expert:** "No. Keep publishing manual and create the dedicated **Tuolin LinkedIn Search Skill** for browser-based discovery and authorized invitations."

> **Dev:** "Should the skill keep its workflow state only in chat or launch its own hidden browser daemon?"
> **Domain expert:** "Neither. Use the **Hybrid Prospecting Implementation**: scripts persist deterministic state while Codex's managed browser performs visible, authorized page interaction."

> **Dev:** "Should the first release sign in again inside the built-in Browser profile?"
> **Domain expert:** "No. Use the **Codex Chrome Prospecting Surface** to operate a dedicated task tab group in the already signed-in Chrome profile."

> **Dev:** "Must `tuolin-linkedin-search` resolve a formal product before it can start?"
> **Domain expert:** "No. Start a **Keyword-Driven LinkedIn Search** from the exact **Search Keyword Phrases** supplied by the operator."

> **Dev:** "Does a keyword-only run still require a verified knowledge-base Agent interface?"
> **Domain expert:** "No. It needs durable task storage for audit, recovery, deduplication, and invitation limits, but no product knowledge preflight."

> **Dev:** "May AI add synonyms that the operator did not provide?"
> **Domain expert:** "No. Search only the exact phrases in the confirmed **Ordered Content Keyword List**."

> **Dev:** "Should every confirmed phrase still be searched after the candidate pool reaches the run limit?"
> **Domain expert:** "No. Use **Keyword Fallback Progression**: later phrases supplement earlier ones only while the batch remains below its effective limit."

> **Dev:** "May the Agent personalize the invitation note while dispatching each candidate?"
> **Domain expert:** "No. Confirm or edit one **AI Invitation Note Draft** before the brief is finalized, then use that fixed text for the whole approved batch."

> **Dev:** "May the note use product facts when the run has no bound product?"
> **Domain expert:** "No. Ground it only in the confirmed keyword scope; if those phrases have no safe common topic, use a generic industry-connection note."

> **Dev:** "May dispatch silently omit the note when LinkedIn no longer offers Add a note?"
> **Domain expert:** "No. Treat it as an **Invitation Note Availability Conflict** and obtain a new explicit decision before further dispatch."

> **Dev:** "Should yesterday's task automatically start again today?"
> **Domain expert:** "No. The first release uses an **Operator-Started Prospecting Run** created through a new natural-language request each time."

> **Dev:** "Can a disconnected Chrome session blindly continue with the next invitation?"
> **Domain expert:** "No. Use **Interrupted Dispatch Recovery** to reconcile the last action and reauthorize the exact remaining batch first."

> **Dev:** "Can a profile found under a new keyword appear again after an invitation was sent yesterday?"
> **Domain expert:** "No. **Contact Eligibility Reconciliation** excludes it through the shared ledger and the live Pending or connected state before any candidate card is created."

> **Dev:** "Can two tasks dispatch for the same LinkedIn account at the same time?"
> **Domain expert:** "No. The first release uses an **Account-Scoped Active Run Lock** so one account has at most one active run."

> **Dev:** "Must exhaust wrap already be an official knowledge-card term before it can be searched?"
> **Domain expert:** "No. It may be an **Operator-Supplied Market Search Term**, but search provenance does not make it an official product name or claim."

> **Dev:** "Must an operator type 按推荐 to accept the current interview answer?"
> **Domain expert:** "No. Ask whether the recommendation is confirmed and accept a plain **Interview Confirmation Reply** for that question only."

> **Dev:** "May the operator approve every unresolved interview question with one reply?"
> **Domain expert:** "No. The first release requires **Sequential Interview Confirmation** for every missing decision."

> **Dev:** "Should the interview ask whether the person using Codex is the boss or an employee?"
> **Domain expert:** "No. That is not a **Decision-Relevant Interview Question**; accept the current Codex operator's explicit confirmation."

> **Dev:** "How should each unresolved question be presented?"
> **Domain expert:** "Use the **Prospecting Interview Question Format**: one numbered question and, when a supported default exists, one recommendation with reason followed by 是否确认？"

> **Dev:** "Should the missing-keyword question invent a recommended list?"
> **Domain expert:** "No. Use the **Required Keyword Input Question** to explain the accepted separators and wait for the operator's exact phrases."

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
> **Domain expert:** "Yes, when an authorized **Video Content Profile** identifies a suitable segment. Prefer a real **Task Video Clip** over regenerating usable footage, and use **Task Video Frames** when still-image reference is needed."
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

> **Dev:** "Can the video consumer browse raw to find a useful moment in a source video?"
> **Domain expert:** "No. It may request **Runtime Frame Extraction** only from an **Authorized Video Reference** already present in the current **Video Creation Context**."

> **Dev:** "Can the runtime extractor accept a raw path from the video consumer?"
> **Domain expert:** "No. It accepts a **Video Asset ID** and validates the current authorized mapping internally."

> **Dev:** "Should moving a source video create a new asset, or should copying it reuse the same ID?"
> **Domain expert:** "Neither by path alone. **Video Asset Identity Reconciliation** preserves identity for a verified move, assigns a new ID to a concurrent copy, and routes ambiguity to human review."

> **Dev:** "Can the video consumer use frame extraction to browse the entire source video again?"
> **Domain expert:** "No. Start from **Video Anchor Moments** and explore only a bounded number of frames inside the authorized **Video Key Segment**."

> **Dev:** "Should every catalog response embed all representative images, or return their cache paths?"
> **Domain expert:** "Neither. Return revision-bound **Representative Frame References** and load only the images needed for candidate or profile inspection."

> **Dev:** "Should every new video task re-analyze the whole source video?"
> **Domain expert:** "No. The **Knowledge Producer** publishes one persistent **Video Content Profile** per source video; the task uses it for selection and performs only task-specific frame extraction."

> **Dev:** "Should the full video timeline be added to `content_asset`, or kept only as generated JSON?"
> **Domain expert:** "Neither. Add a formal `video_profile` **Video Profile Card** with atomic human-readable Markdown and machine-validatable JSON projections linked to the existing asset identity."

> **Dev:** "Is one paragraph saying what the video is about enough?"
> **Domain expert:** "No. Use a short **Video Profile Title**, a whole-video **Video Profile Summary**, and time-coded **Video Segment Descriptions**."

> **Dev:** "If the woven tape is sharp and fills the frame, is its product identity automatically confirmed?"
> **Domain expert:** "No. **Segment Product Visibility** separates clear appearance from identity-confirmable evidence."

> **Dev:** "Should the long-lived profile store only whether a frame crops well to 9:16?"
> **Domain expert:** "No. Store general **Segment Composition Safety** and derive the current 9:16 suitability from it."

> **Dev:** "Can the Agent silently remove a third-party watermark to make a clip usable?"
> **Domain expert:** "No. Record the **Segment Identifier Risk**, prefer another source, and disclose any allowed crop or mask; never erase provenance or rights concerns silently."

> **Dev:** "Can a source clip with a clear employee face be used because it is stored in the company knowledge library?"
> **Domain expert:** "No. **Segment Person Risk** separates identifiability from authorization; a clear face needs recorded authorization before automatic external selection."

> **Dev:** "Can a test video inherit a report's conclusions because both files are in the same folder?"
> **Domain expert:** "No. Directory proximity creates only a **Candidate Video Evidence Link**; external support requires a **Confirmed Video Evidence Link**."

> **Dev:** "Should a profile say 'easy installation improves insulation performance' because it shows wrapping?"
> **Domain expert:** "No. Record the visible wrapping action and its use capability; task-specific marketing language belongs to the video consumer and must use formal knowledge."

> **Dev:** "If a segment shows a valuable action, is it automatically suitable for direct editing?"
> **Domain expert:** "No. Evaluate its separate **Segment Editing Suitability**; useful content may still be reference-only or unusable."

> **Dev:** "Should the existing content-asset card contain the whole video timeline?"
> **Domain expert:** "No. The **Video Asset Card** owns source identity and authorization; its one-to-one **Video Content Profile** owns the video's semantic timeline."

> **Dev:** "If a flame-test video ends with the tape still looking intact, can the profile say the product passed?"
> **Domain expert:** "No. It may record the visible before-and-after appearance as **Video Observations**; passing the test is a **Video Claim Interpretation** that requires formal evidence or human review."

> **Dev:** "Should video analysis sample every fixed number of seconds?"
> **Domain expert:** "No. Use uniform coverage to establish the whole-video structure, then add **Video Analysis Frames** around meaningful scene, subject, visibility, action, and process-state changes."

> **Dev:** "Should downstream planning receive every sampled frame?"
> **Domain expert:** "No. Publish three to six **Video Representative Frames** for preview, then extract a precise **Task Video Frame** from the selected source video when a concrete shot needs it."

> **Dev:** "Can all representative frames come from the most attractive five seconds?"
> **Domain expert:** "No. Prefer key-segment anchors and cover the video's distinct main content; use only a few global context frames when needed."

> **Dev:** "Should the knowledge producer label a source segment as 'shot 03'?"
> **Domain expert:** "No. Publish a stable **Video Use Capability** and time range; the video consumer assigns the concrete storyboard role for each task."

> **Dev:** "If a video is stored under the fixed test-material folder, does that prove the visible segment is a test?"
> **Domain expert:** "No. Preserve the complete **Video Source Classification** as provenance and an analysis prior, then publish the actual time-ranged **Video Observed Classification** separately."

> **Dev:** "Does a child folder under application materials have business meaning?"
> **Domain expert:** "Yes. It defines a human-maintained **Source Application Scenario**, but the video profile must still distinguish that assigned scenario from what is visibly confirmed in the footage."

> **Dev:** "Do all nested folders under an application scenario define more scenarios?"
> **Domain expert:** "No. Only the first descendant folder is the canonical **Source Application Scenario**; deeper folders remain ordered source context until analysis assigns a supported meaning."

> **Dev:** "Is one timestamp enough to describe an installation action?"
> **Domain expert:** "No. Record the complete action as a **Video Key Segment** and include **Video Anchor Moments** for representative preview and precise frame extraction."

> **Dev:** "If a real source-video segment already satisfies the shot, should the Agent regenerate it from a frame?"
> **Domain expert:** "No. Create a **Task Video Clip** through **Runtime Clip Extraction** and use the real footage; generate a replacement only when the source segment cannot satisfy the confirmed shot."

> **Dev:** "Can a directly reused source clip always keep its original audio?"
> **Domain expert:** "No. Read its **Source Audio Use Policy**; speech, privacy, noise, and music-rights risk may require muting or human review."

> **Dev:** "Should every downstream context receive the complete source transcript?"
> **Domain expert:** "No. Retain **Video Transcript Detail** for audit and disclose only the selected segment's redacted excerpt when needed."

> **Dev:** "If no ASR tool is installed, can the profile say the video has no important speech?"
> **Domain expert:** "No. Publish the visual scope only, expose the audio-analysis gap, and keep original-audio reuse under review until a **Speech Transcription Adapter** or a human resolves it."

> **Dev:** "Should a future maintainer have to guess which model and frames produced a segment classification?"
> **Domain expert:** "No. Link every profile to **Video Analysis Provenance** and keep verbose execution logs separately in generated reports."

> **Dev:** "Must one mislabeled segment force the whole source video through analysis again?"
> **Domain expert:** "No. Use a previewed **Video Profile Amendment** for a local correction; reserve full re-analysis for source, sampling, metadata, or systemic-policy problems."

> **Dev:** "Does excluding a risky customer video mean deleting it from raw?"
> **Domain expert:** "No. Apply a scoped **Video Use Exclusion**, preserve the source and audit history, and remove only the prohibited authorization."

> **Dev:** "Can a new visual-risk field be populated with 'none' during schema migration?"
> **Domain expert:** "No. If the value requires viewing the source, migration cannot invent it; mark the profile stale and re-analyze."

> **Dev:** "Can a long video be called complete after silently dropping frames to stay under budget?"
> **Domain expert:** "No. Use the **Video Analysis Budget** to trigger segmentation or explicit deeper analysis, not silent coverage loss."

> **Dev:** "Can cleanup delete every JPEG thirty days after analysis?"
> **Domain expert:** "No. Follow the **Video Analysis Cache Retention** manifest and live references; current representative frames and unresolved review material remain, and raw media is never cache."

> **Dev:** "Should a batch begin and mark videos failed before discovering that ffmpeg or the semantic analyzer is unavailable?"
> **Domain expert:** "No. **Video Analysis Capability Preflight** blocks an unready environment before processing and distinguishes environment failure from source-video failure."

> **Dev:** "Can a video profile remain usable after the source file is replaced under the same filename?"
> **Domain expert:** "No. Its **Video Profile Revision** no longer matches, so downstream semantic use is blocked until the profile is rebuilt."

> **Dev:** "Should one corrupt video prevent every successfully analyzed video from reaching downstream consumers?"
> **Domain expert:** "No. Process each video atomically and publish valid profiles incrementally, while the product remains visibly incomplete until failures are resolved or explicitly excluded."

> **Dev:** "If Codex stops after six videos, must the batch restart from the first one?"
> **Domain expert:** "No. Resume from the first incomplete **Video Profile Checkpoint** when earlier checkpoints and their source and policy revisions still match."

> **Dev:** "Can downstream Agents read a validated checkpoint before batch acceptance and interface verification finish?"
> **Domain expert:** "No. A checkpoint remains staged until a **Video Profile Publication Transaction** promotes it and activates a verified Agent-interface revision."

> **Dev:** "Does an old zero-second frame mean a video remains processed after the upgrade?"
> **Domain expert:** "No. A **Legacy Video Frame Cache** does not count as completion; only a current validated profile does."

> **Dev:** "Should the video consumer find source footage through tags alone or unrestricted semantic search?"
> **Domain expert:** "Neither. **Video Material Retrieval** first applies structured product, state, visibility, reuse, and risk constraints, then semantically ranks only the authorized candidates."

> **Dev:** "Can a visually similar representative frame establish that a video shows the same product or a successful test?"
> **Domain expert:** "No. The **Representative Frame Visual Index** improves ranking only after hard filters; identity and claims still require profile evidence and review."

> **Dev:** "Must the first release deploy a visual-vector model before downstream Agents can find useful video?"
> **Domain expert:** "No. Use structured and textual recall followed by **Codex Representative Frame Rerank**; report the vector index as unavailable rather than inventing one."

> **Dev:** "Can a storyboard confirm direct use of a source segment from its profile summary and one representative frame?"
> **Domain expert:** "No. Extract the exact segment into the run and show its **Task Video Preview** before storyboard confirmation."

> **Dev:** "Can runtime extraction silently speed up or enhance a real test clip?"
> **Domain expert:** "No. Automatic **Meaning-Preserving Video Adaptation** is limited to technical normalization; any change that may alter motion perception or authenticity must be disclosed and confirmed."

> **Dev:** "Should the video context include every full profile and transcript for all registered videos?"
> **Domain expert:** "No. Search the **Video Profile Catalog**, load details only for shortlisted profiles, and read source bytes only for authorized runtime extraction."

> **Dev:** "Must an employee browse and choose source videos before the Agent creates a plan?"
> **Domain expert:** "No. Source selection is a **Professional Video Decision**; explain the recommendation in the plan and show the exact extracted material during storyboard confirmation."

> **Dev:** "Is authentic test footage automatically safe for an external product video?"
> **Domain expert:** "No. Apply the **Test-Footage Publication Gate**: use linked evidence for conclusions, or keep the presentation strictly neutral and visibly under review."

> **Dev:** "Can a model infer a video's duration, key actions, and audio content from one extracted image?"
> **Domain expert:** "No. Use the **Video Understanding Pipeline** so deterministic tools establish media facts and multimodal analysis interprets ordered visual and audio evidence."

> **Dev:** "Must the operator configure a third-party multimodal API key before video profiles can be created?"
> **Domain expert:** "No. The current release uses **Codex Video Semantic Review** directly; the knowledge Agent prepares bounded inputs and validates the result without hidden external-model configuration."

> **Dev:** "Must every source video be transcoded into analysis clips before it can be understood?"
> **Domain expert:** "No. Start with ordered frames and create **Video Analysis Clips** only when temporal behavior or direct-reuse suitability cannot be assessed reliably from stills."

> **Dev:** "Should each source video maintain separate Chinese and English semantic profiles?"
> **Domain expert:** "No. Keep one canonical Chinese profile with language-independent codes, then translate selected excerpts inside the downstream task."

> **Dev:** "Do video observations belong only in generated cache because they were model-produced?"
> **Domain expert:** "No. Persist the validated semantic profile in the formal knowledge layer; keep only the analysis media in rebuildable generated storage."

> **Dev:** "Does an official video profile mean its visible content proves product performance?"
> **Domain expert:** "No. Its **Visual Observation Scope** authorizes visual-use decisions only; product facts still require separate evidence and publication authority."

> **Dev:** "Should one uncertain test result make every clear installation segment in the same video unusable?"
> **Domain expert:** "No. Keep the profile valid and block only the uncertain item's **Video Observation State** from automatic downstream use."

> **Dev:** "Can the multimodal model simply label an observation 'high confidence'?"
> **Domain expert:** "No. Publish **Video Observation Confidence** only with traceable supporting reasons and warnings from the source, timeline, visual, audio, quality, and consistency signals."

> **Dev:** "Should repeated installation actions inside one video be deleted as duplicates?"
> **Domain expert:** "No. Create a **Video Segment Group**, prefer the best segment, and retain the others as explained alternatives."

> **Dev:** "Should two nearly identical source videos be merged or deleted?"
> **Domain expert:** "No. Relate them through a **Video Asset Family**, rank a preferred source when appropriate, and preserve every raw file."

> **Dev:** "Should the first run analyze every registered video at once?"
> **Domain expert:** "No. Validate product videos first, process application scenarios folder by folder, and leave test-validation videos until the observation and publication gates are mature."

> **Dev:** "Does accepting a profile batch mean every observation becomes an approved product fact?"
> **Domain expert:** "No. **Video Profile Batch Acceptance** validates pipeline quality and publication boundaries; product facts still require their own evidence and knowledge review."

> **Dev:** "Should an employee run frame-extraction and analysis commands for every source video?"
> **Domain expert:** "No. Confirm one business-scoped **Video Profile Batch** in natural language; the knowledge producer runs and verifies the internal pipeline."

> **Dev:** "Should a batch receipt show every representative frame from every profile?"
> **Domain expert:** "No. Show six to twelve cross-profile overview images, then show a profile's complete representative set only during focused review."

> **Dev:** "Should the first product-video batch become automatically selectable immediately after model analysis?"
> **Domain expert:** "No. Its **Video Batch Maturity** requires acceptance first; only stable incremental batches may publish optimistically under monitored sampling."

> **Dev:** "Should one bad file stop every later application-scenario batch?"
> **Domain expert:** "No. Use **Video Batch Impact Scope**: isolate local defects and pause only the range affected by systemic ones."

> **Dev:** "Should the first rollout scan company and workshop videos because the pipeline is technically reusable?"
> **Domain expert:** "No. Keep the capability generic but integrate only the fixed quartz-fiber-tape product folders until other domain boundaries are decided."

> **Dev:** "Is the chain complete when a keyframe JSON file can be generated?"
> **Domain expert:** "No. Complete the **Video Knowledge-to-Creation Tracer** through retrieval, authorized extraction, storyboard confirmation, and real clip assembly."

> **Dev:** "Should the team build the 164-video batch framework before connecting one real video to storyboard and assembly?"
> **Domain expert:** "No. Prove one real tracer, expand it to all product videos, then generalize the accepted path into application-scenario batches."

> **Dev:** "Should the tracer use the shortest static product video because it is easiest?"
> **Domain expert:** "No. Choose a **Tracer Source Video** that proves continuous-action understanding and real clip reuse without introducing test or high-risk privacy complexity."

> **Dev:** "Can the tracer source be chosen from filenames alone?"
> **Domain expert:** "No. Inspect every product-video candidate, recommend one with actual frames and media facts, and wait for explicit sample confirmation."

> **Dev:** "Should tracer-selection frames count as completed knowledge-base video processing?"
> **Domain expert:** "No. Keep them in **Tracer Candidate Inspection Cache**; only the accepted formal pipeline can produce a valid profile."

> **Dev:** "Is updating only the glossary enough to prevent the old image-only behavior from returning?"
> **Domain expert:** "No. Synchronize the PRD, vertical implementation slices, and tests, and explicitly supersede the old video-exclusion rules."

> **Dev:** "Should a later source revocation delete a task's already extracted preview?"
> **Domain expert:** "No. Preserve it for audit, but recheck **Video Source Revocation** at each confirmation and submission gate and block high-risk material."

> **Dev:** "Does a local extraction need a one-time token for every frame?"
> **Domain expert:** "No. Bind it to the run and locked revisions, validate the authorized asset and operation, and write a **Runtime Video Extraction Audit**."

> **Dev:** "Can the Agent compare several source clips before choosing one?"
> **Domain expert:** "Yes, but cap **Candidate Video Previews** at three per planned use and create delivery-quality output only for the selected segment."

## Flagged Ambiguities

- “加好友” was used for sending a request and establishing a relationship. Resolved: use **Connection Invitation** for the outbound request; a connection exists only after acceptance.
- “找到客户” could mean a keyword match, a commercially relevant lead, or an existing buyer. Resolved for discovery: use **LinkedIn Discovery Candidate** until later qualification evidence supports a stronger classification.
- “用户授权浏览器操作” could be read as platform authorization. Resolved: **Account-Risk Acceptance** records the account owner's decision only and does not imply LinkedIn authorization.
- “授权后继续重复” could mean one approval covers recurring daily automation. Resolved: **Prospecting Run Authorization** applies to exactly one reviewed run and cannot be reused by later runs.
- “同行或者客户” was treated as one interchangeable target group. Resolved: they are different **Prospecting Target Intents**; one run cannot mix them, and the first release prioritizes potential customers.
- “有效” was expanded into lead-quality and conversion metrics. Resolved for the first release: apply the **First-Release Evaluation Boundary** and defer those metrics until after the connection workflow works.
- “能加上人” could mean either submitting an invitation or becoming a first-degree connection. Resolved for the first release: completion means **Invitation Dispatch Success** and does not wait for recipient acceptance.
- “关键词搜索” could mean searching posts, people, or companies. Resolved for the first release: use **Post-First Prospect Discovery** with content keywords; direct people search is not the primary discovery entrypoint.
- “同行”和“潜在客户” were previously allowed to overlap without distinguishing business models. Resolved: a **Direct Category Manufacturer** is skipped; a **Same-Category Channel Prospect** or **Downstream Material User** may continue provisionally, with unclear make-versus-source evidence left for human review.
- “贴文作者” could be either a member or a company page. Resolved: a company-authored match must use **Company Contact Resolution** to find one prioritized personal account before invitation dispatch.
- Company contact fallback was undefined. Resolved: if **Company Contact Resolution** finds none of the confirmed priority roles, skip the company instead of choosing another employee.
- “重复处理” could mean only duplicates inside the current search page. Resolved: the **Prospecting Contact Ledger** provides cross-run deduplication for posts, companies, members, invitation state, and retry eligibility.
- Invitation-note behavior was considered a fixed first-release rule. Resolved: it is an **Invitation Note Decision** made by the actual operator for each run together with supported search criteria and the invitation limit.
- Invitation-note personalization was unspecified. Resolved: one run uses no note or one fixed confirmed note for every approved candidate; per-candidate generation is out of scope.
- “目标地区” was proposed as an interview field even though standard post search cannot apply it. Resolved for the first release: remove it and restrict discovery decisions to **Supported Post Search Criteria**.
- “基于搜索条件访谈” could mean forcing every visible filter into a fixed form. Resolved: always collect the three **Core Post Search Criteria** and add other supported filters only when relevant.
- “组合关键词” could mean one merged query, Boolean composition, or multiple phrases. Resolved: use an **Ordered Content Keyword List** in which every comma- or line-separated **Search Keyword Phrase** is searched independently and intact, while preserving per-candidate phrase provenance.
- “关键词数量” could be confused with the number of Posts returned for one phrase. Resolved: the operator's phrase list has no fixed count ceiling, while each phrase independently follows candidate, inspection, and verified-exhaustion stop conditions.
- “主词” could imply a separate required field or special query behavior. Resolved: it is only the **Primary Search Keyword**, meaning the first phrase searched; it is not collected separately and duplicate occurrences are removed.
- “每天加多少个” could mean a quota per keyword or one authorization ceiling. Resolved: use one run-wide **Successful Invitation Limit** counted only by confirmed invitation dispatches.
- The default run size and weekly pacing policy were unspecified. Resolved: recommend the **Default Run Invitation Limit** of ten and enforce a local **Seven-Day Invitation Ceiling** of one hundred per bound account.
- “7 天” could mean a calendar week or a rolling duration. Resolved: use the rolling one-hundred-sixty-eight hours before each dispatch.
- The seven-day ceiling could imply complete account-wide activity tracking. Resolved: count only skill-recorded successes and disclose that manual invitations are not included.
- A requested run limit could exceed remaining seven-day capacity. Resolved: compute and confirm the **Effective Run Invitation Limit**, and block before discovery when it is zero.
- An invitation limit could be mistaken for a quota the system must fill. Resolved: it is a ceiling, and **Search Exhaustion Completion** is a valid result below that ceiling.
- Multiple keyword phrases could imply that all phrases must always be searched. Resolved: use **Keyword Fallback Progression** and stop discovery once the candidate pool reaches the effective run limit.
- Post ordering was unspecified. Resolved: make it a per-run **Post Sort Decision**, recommend Latest, and preserve the operator's ability to choose Most Relevant.
- Run authorization could be interpreted as approval to contact candidates the operator has never seen. Resolved: require a **Candidate Review Card** and **Pre-Dispatch Candidate Review** before invitation submission.
- AI screening could be mistaken for final prospect qualification. Resolved: every included member has only **Provisional Candidate Fit** until the operator reviews the complete visible post and identity evidence in the **Candidate Review Card**.
- A relevant post without a resolvable personal account could be counted as a candidate. Resolved: record an **Unresolved Relevant Lead** without consuming the candidate limit, and continue discovery.
- Candidate review mode was briefly considered one-at-a-time. Resolved: review an **Approved Candidate Batch** in Codex, then dispatch its invitations sequentially with an **Invitation Dispatch Interval**.
- Invitation pacing was unspecified. Resolved: include one operator-confirmed **Invitation Dispatch Interval** in every run brief and recommend five minutes without claiming it prevents platform restrictions.
- Batch approval could trigger automatic replacement discovery for rejected candidates. Resolved: the reviewed list is a **Closed Candidate Batch** and further discovery requires a new task.
- “找够 10 个” could mean refilling after human rejection. Resolved: discovery may produce up to ten reviewable cards, but operator removals are not backfilled and the final approved batch may be smaller.
- Candidate approval and final send permission were treated as separate possible prompts. Resolved: the explicit batch confirmation is the **Final Batch Dispatch Authorization**, after which no per-member prompt is required.
- “账号必须已登录” did not identify which member account was authorized. Resolved: bind each run to one displayed **Bound LinkedIn Account** and block on missing, unknown, or changed identity.
- Search exhaustion had no finite inspection boundary. Resolved: inspect at most fifty posts per keyword through the fixed **Keyword Post Inspection Limit**, which is not an interview question.
- LinkedIn's infinite result stream could be mistaken for six total results after one stalled load or a visible footer. Resolved: neither a footer, advertisement, nor discarded `page=2` parameter proves exhaustion; require **Verified Infinite-Scroll Exhaustion** before ending a keyword below its candidate and inspection limits.
- A keyword match could be mistaken for sufficient candidate evidence. Resolved: require a binary **Post Relevance Decision** with one reason before inspecting the author or company.
- Removing product binding could leave relevance dependent on hidden product knowledge. Resolved: judge relevance only from the source **Search Keyword Phrase** and visible LinkedIn content, skipping incidental mentions, reposted news, ordinary consumer content, homonyms, and spam.
- Candidate resolution for personal and company-authored posts was conflated. Resolved: keep a verified **Individual Post Author Candidate** directly, and use **Company Contact Resolution** only for company-authored posts.
- A missing ordinary Connect action could trigger alternate outreach or guessed data. Resolved: require **Standard Connect Eligibility** and skip rather than substitute Follow, Message, email guesses, or bypass attempts.
- Dispatch failure handling was undifferentiated. Resolved: continue after a **Candidate-Local Dispatch Failure**, but stop the entire run immediately on a **Platform-Level Dispatch Stop**.
- A stopped batch could silently resume after a platform challenge cleared. Resolved: automatic resume is forbidden; remaining members require an **Authorized Dispatch Restart**.
- Prospecting records could be confused with formal market intelligence. Resolved: each task uses a **Prospecting Run Directory**, shares only the operational ledger, and does not write directly to `knowledge/okf`.
- LinkedIn publishing and prospecting were considered one skill. Resolved: create the independent **Tuolin LinkedIn Search Skill** named `tuolin-linkedin-search` and preserve the existing publishing skill's manual boundary.
- Skill implementation could be prompt-only or a repository-owned browser bot. Resolved: use the **Hybrid Prospecting Implementation** with persisted scripts and Codex-managed browser interaction.
- The managed browser surface was undecided. Resolved: the first release requires the official **Codex Chrome Prospecting Surface** and does not use the built-in Browser profile.
- “完全由关键词驱动的通用 skill” previously meant generic only across formally resolved Tuolin products. Superseded: a **Keyword-Driven LinkedIn Search** requires no product selection and uses only operator-supplied phrases.
- Product selection was previously mandatory. Superseded: formal product resolution and the `linkedin_search` knowledge context are not prerequisites for prospect search.
- A verified knowledge-base Agent interface was previously a run-creation gate. Superseded: keyword-only prospect search requires durable writable task storage but does not require or consume the knowledge interface.
- Existing product-bound run compatibility was considered during the test phase. Resolved: no migration or resume compatibility is required; after the keyword-driven change, testing starts from newly created runs.
- AI-generated search expansion was previously allowed after review. Superseded: the operator supplies the complete **Ordered Content Keyword List** and the skill does not add synonyms automatically.
- Invitation-note drafting was undefined. Resolved: when notes are enabled, AI proposes one restrained English **AI Invitation Note Draft** that the operator must confirm or edit before the brief is complete.
- Removing product binding could tempt the note generator to invent product or company facts. Resolved: use only the confirmed keyword scope and search purpose, falling back to generic industry-connection language when no common topic is reliable.
- Note availability can change between brief confirmation and dispatch. Resolved: an **Invitation Note Availability Conflict** pauses the batch and forbids silently downgrading to no-note invitations.
- “每天加多少个” could imply unattended daily scheduling. Resolved: the first release has no scheduler; every task is an **Operator-Started Prospecting Run** with a run-wide invitation limit.
- Session interruption and platform restriction were conflated. Resolved: ordinary disconnection uses **Interrupted Dispatch Recovery**, while a **Platform-Level Dispatch Stop** requires a new task.
- Candidate review data could remain chat-only or include browser secrets. Resolved: persist review cards as Markdown and JSON, keep screenshots exceptional, and never store cookies, passwords, or browser session data.
- Cross-task deduplication could rely only on a stale local URL list. Resolved: use **Contact Eligibility Reconciliation** against both the shared ledger and the live LinkedIn profile state before review and dispatch.
- Same-account parallel tasks could race on deduplication and pacing. Resolved: enforce an **Account-Scoped Active Run Lock** in the first release.
- A dedicated product knowledge context was previously required for every search run. Superseded: keyword-only prospect search does not consume product knowledge or campaign outputs.
- Search keywords were at risk of being treated as formal product language. Resolved: allow an **Operator-Supplied Market Search Term** for discovery while forbidding automatic knowledge or claim promotion.
- Interview acceptance was proposed as the command “按推荐”. Resolved: ask “是否确认？” and accept plain confirmation for the current question only.
- Bulk acceptance of all remaining interview recommendations was considered. Resolved: the first release requires **Sequential Interview Confirmation** and does not support a blanket reply.
- Authorization-role verification was considered. Resolved: do not infer or validate boss-versus-employee roles; explicit confirmation by the current Codex operator is sufficient.
- Interview depth could be measured by question count. Resolved: ask only a **Decision-Relevant Interview Question** and use the consistent **Prospecting Interview Question Format**.
- Removing product binding could still leave product, category, knowledge-base, or geography questions in the interview. Resolved: use the six-decision **Keyword-Driven Interview Scope** and skip every answer already explicit in the initial request.
- The interview format previously required a concrete recommendation for every question. Superseded for keywords: the **Required Keyword Input Question** provides only format guidance because all search phrases must come from the operator.

- "审阅" was used for both marketing campaign quality review and knowledge-base fact review. Resolved: use **Marketing Plan Review** for LinkedIn campaign planning and **Knowledge Review** for formal knowledge-base review items.
- “母版” previously referred inconsistently to silent and narrated outputs. Resolved: remove the term and use **Video Language Version**.
- “创意方向” was previously modeled as 16 fixed categories with primary and supporting selections. Resolved: remove that taxonomy and use a **Video Creation Interview** to produce a **Confirmed Video Brief**.
- Product external names were considered as video-workflow constants. Resolved: they are knowledge owned by the **Knowledge Producer**, not by the video consumer.
- `video_script` was initially retained as the video task-context name. Resolved: rename it to `video_creation` to match the complete production responsibility.
- “下游反向从 raw 实时截帧” could mean unrestricted raw access. Resolved: use **Runtime Frame Extraction** from an **Authorized Video Reference**; the consumer still cannot browse or scan raw.
- “视频关键信息” could mean a temporary analysis performed inside each video task. Resolved: persist it as one **Video Content Profile** per source video and publish it through the Agent interface.
- “视频知识卡” could mean expanding the existing content-asset card. Resolved: keep the **Video Asset Card** for identity and add a separate one-to-one **Video Content Profile** for semantic content.
- “测试结果或前后变化” mixed visible change with performance conclusions. Resolved: visible changes are **Video Observations**; test success and performance meaning are **Video Claim Interpretations** requiring evidence or review.
- Folder-based video classification was previously flattened into one asset category. Resolved: preserve the fixed top-level category and complete descendant path as **Video Source Classification**, separate from visually derived **Video Observed Classification**.
- Application-material child folders were considered generic path metadata. Resolved: they are human-maintained **Source Application Scenarios**, while visible application content remains separately observed and time-ranged.
- All nested application-material folders could have been treated as equal scenario labels. Resolved: only the first descendant folder defines the **Source Application Scenario**; deeper levels remain ordered source context until analyzed.
- Source videos were previously treated as information or frame sources only. Resolved: an authorized usable **Video Key Segment** may become a real **Task Video Clip**, and real footage is preferred over regenerating the same content.
