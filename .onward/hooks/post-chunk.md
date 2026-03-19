---
id: HOOK-post-chunk
type: hook
trigger: chunk.completed
model: gpt-5
executor: ralph
scope: repo
---

# Purpose
Capture chunk-level completion and recommend plan updates.

# Inputs
- Completed chunk
- Child task outcomes

# Instructions
1. Verify the chunk completion criteria.
2. Summarize major outputs and known risks.
3. Suggest next chunk ordering.

# Required output
- Chunk completion status
- Risks and recommended next actions
