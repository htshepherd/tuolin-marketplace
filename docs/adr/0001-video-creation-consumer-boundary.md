# Keep video creation behind one consumer workflow

The quartz-fiber-tape video agent is an application-layer consumer that reads the product card and explicitly related content assets only through the `video_creation` Agent context. `tuolin-video-workflow` is the sole user-facing entrypoint; Dreamina generation, narration, music, subtitles, quality checks, and assembly remain internal replaceable capabilities so ordinary users never scan raw materials, invoke runners, copy run paths, or depend on a specific media provider.
