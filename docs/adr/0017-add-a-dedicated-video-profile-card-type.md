# Add a dedicated video profile card type

Video source registration and video semantics remain separate formal concepts. The existing `content_asset` card owns the registered source, product relationship, source classification, media type, authorization, and opaque video asset ID. A new `video_profile` card owns the persistent semantic understanding of that one registered video.

Each published profile is projected from one validated domain object into:

- `knowledge/okf/视频档案/{product_slug}/{video_asset_id}.md` for human review;
- `knowledge/okf/视频档案/{product_slug}/{video_asset_id}.json` for complete machine validation and Agent-interface generation.

The pair is written atomically and carries matching profile revision and content digest. Missing or conflicting counterparts invalidate the profile. Analysis frames, analysis clips, verbose logs, and Codex input manifests remain generated artifacts rather than formal knowledge files.
