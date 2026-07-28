# Video Planner Workflow Contract

## Dedicated reads

Use these functions from `tuolin_marketplace.agent_specific_interfaces`:

- `read_video_planner_manifest`
- `read_video_planner_products`
- `read_video_planner_card` / `search_video_planner_cards`
- `read_video_planner_video_catalog` / `search_video_planner_video_catalog`
- `read_video_planner_video_detail`
- `resolve_video_planner_representative_media`

Do not read `generated/agent-interface/contexts` or raw knowledge sources.

## Decision sufficiency

A complete brief resolves audience, audience problem/scenario, viewing motivation, viewer-interest direction, intended takeaway, desired action, priority messages, exclusions, and AI-simulation scope. These are semantic completion criteria, not a fixed questionnaire order.

Fact-bearing intended takeaways, priority product messages, and AI application boundaries require formal-card evidence. Audience and creative recommendations may use clearly marked model inference.

## State sequence

```text
interview
  -> ready_for_shot_plan
  -> awaiting_shot_plan_confirmation
  -> completed
```

There are no trend, plan-summary-confirmation, SRT-confirmation, provider, generation, download, assembly, or publishing states.

## Run files

- `requirements.md`
- `interview.json`
- `workflow_state.json`
- `change_log.md`
- `material-previews/`
- `video_profile_authorizations.json` when needed
- `video_asset_audit.json` when needed
- `shot_plan.md`
- `shot_plan.json`
- `storyboard.srt` only after confirmation
- `revisions/revision_NNNN/` for immutable confirmed deliveries

The current SRT is always derived from the current confirmed narration. It is never edited as an independent source of truth.
