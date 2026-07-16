# Keep runtime video frame extraction behind authorized references

The video consumer remains `raw_access=false` and cannot browse or scan raw. The knowledge producer publishes an authorized reference for each usable source video, and the video consumer may request read-only frame extraction only for a referenced video selected from its current task context; extracted images are written into the current video-creation run rather than raw or the formal knowledge layer. This preserves the knowledge boundary while avoiding the cost and rigidity of pre-generating every task-specific frame.
