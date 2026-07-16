# Prefer authorized real video segments over regeneration

When a profiled source-video segment satisfies a confirmed storyboard need, the video consumer extracts a task-scoped clip from the authorized source and uses the real footage instead of recreating it through image-to-video or text-to-video generation. The same authorized segment may also supply task frames when still-image reference is useful. Both outputs remain inside the current video-creation run, and raw source videos are never modified.
