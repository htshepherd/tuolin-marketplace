# Separate LinkedIn prospecting from campaign publishing

Create a dedicated `tuolin-linkedin-search` skill for operator interviews, post-first prospect discovery, candidate review, browser authorization, and connection-invitation dispatch. Do not extend the existing `tuolin-linkedin` skill, whose responsibility remains campaign planning, copy, images, and manual publishing; keeping these boundaries separate prevents external account actions and prospecting state from becoming hidden behavior inside a content-generation workflow.
