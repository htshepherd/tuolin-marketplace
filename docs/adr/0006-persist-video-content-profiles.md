# Persist one semantic profile per source video

The knowledge producer maintains one current video content profile for each registered source video and publishes it through the Agent interface. Video-creation tasks use that persistent profile to understand and select videos, then perform only task-specific runtime frame extraction; this avoids repeated full-video analysis while keeping observable video semantics separate from verified product-performance facts.
