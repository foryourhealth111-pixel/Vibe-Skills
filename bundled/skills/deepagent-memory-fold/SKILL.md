---
name: deepagent-memory-fold
description: "DeepAgent-style memory folding for VCO sessions: compress long context into structured working/tool memory without using episodic-memory."
---

# DeepAgent Memory Fold (VCO)

## When to use

Use this skill when:

- The task is long-horizon and context is getting large
- You need to “take a breath” and restart reasoning from a compact state
- You see repeated retries / route instability / losing track of decisions
- You need to hand off to another agent or start a new session

## Governance constraints (must follow)

- VCO memory governance **disables** `episodic-memory`.
- Use **state_store** (session) by default.
- Only write to Serena memory when the user explicitly approves a **project decision**.

## Runtime (Upstream vendoring)

DeepAgent upstream is vendored (optional/advanced):

- `C:\Users\羽裳\.codex\_external\ruc-nlpir\DeepAgent\`

Runtime config + preflight (no secrets stored/printed):

- `C:\Users\羽裳\.codex\skills\vibe\config\ruc-nlpir-runtime.json`
- validate your local runtime environment manually before enabling vendored DeepAgent helpers

## Output contract (structured fold)

Produce a “folded memory” object with these sections:

1. **Working memory**
   - Current goal
   - Current sub-goal
   - Current blockers
   - Next 3 actions
2. **Tool memory**
   - Tools/skills used
   - What worked / what failed
   - Availability notes (keys required, deps missing)
3. **Evidence memory**
   - Top 5 evidence anchors (file:line or URLs)
4. **Decision log**
   - Only decisions actually made (no speculation)
5. **Resume prompt**
   - A compact prompt that can be pasted into a new session

## Where to store it

- Default: write to `outputs/runtime/memory-fold.json` (or similar session output)
- If user requests: also write a human-readable `memory-fold.md`

## Minimal template (copy/paste)

```json
{
  "working_memory": {
    "goal": "",
    "sub_goal": "",
    "blockers": [],
    "next_actions": []
  },
  "tool_memory": {
    "used": [],
    "worked": [],
    "failed": [],
    "availability": []
  },
  "evidence_memory": {
    "anchors": []
  },
  "decision_log": [],
  "resume_prompt": ""
}
```
