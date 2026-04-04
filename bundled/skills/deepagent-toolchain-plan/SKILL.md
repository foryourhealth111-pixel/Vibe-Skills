---
name: deepagent-toolchain-plan
description: "DeepAgent-style tool discovery for VCO: propose a minimal skill/tool chain (with verification points) and reduce confirm_required friction."
---

# DeepAgent Toolchain Plan (VCO)

## When to use

Use this skill when:

- VCO router returns `route_mode=confirm_required` and you want a **better, evidence-backed choice**
- The task spans multiple domains/tools and you need a **skill chain**, not a single skill
- The user asks “用什么工具/技能最好？” / “怎么编排这套技能？”
- The conversation is long or messy and you need to **re-anchor** on goal → toolchain → verification

## Non-goals (avoid redundancy)

- This is **not** a replacement for VCO routing. It is an *augmentation* that proposes a chain.
- This is **not** GitNexus. For code dependency/impact, use GitNexus overlays.
- This does **not** introduce long-term episodic memory (VCO governance disables it).

## Runtime (Upstream vendoring)

DeepAgent upstream is vendored for reference / optional advanced runs:

- `C:\Users\羽裳\.codex\_external\ruc-nlpir\DeepAgent\`

VCO-managed runtime config and self-check scripts (no secrets stored/printed):

- `C:\Users\羽裳\.codex\skills\vibe\config\ruc-nlpir-runtime.json`
- validate your local runtime environment manually before enabling vendored DeepAgent helpers

## Core output (must)

Return a toolchain with:

1. **Goal + deliverable** (1–2 lines)
2. **Chain steps** (3–8 steps, each: skill/tool + why + expected artifact)
3. **Verification points** (at least 1 falsifiable check)
4. **Fallbacks** (what to do if a tool is unavailable)

## Workflow

### Step 1: Capture the task in a contract

- Goal (one sentence)
- Deliverable (code / plan / report / dataset / etc.)
- Constraints (time, no heavy deps, offline-only, etc.)

### Step 2: Ask VCO router for a white-box view (recommended)

Run the router script in probe mode to get candidates + overlays in a machine-readable form:

- `pwsh C:\Users\羽裳\.codex\skills\vibe\scripts\router\resolve-pack-route.ps1 -Prompt "<PROMPT>" -Grade L -TaskType planning -Probe -ProbeLabel "toolchain" -ProbeOutputDir outputs/runtime/router-probes`

Then use the emitted `confirm_ui` + overlay advice to decide the chain.

### Step 3: Build a minimal chain (DeepAgent principle)

Prefer a chain that:

- Starts with **evidence acquisition** (local docs / web / code graph)
- Then **planning**
- Then **execution**
- Ends with **verification + review**

### Step 4: Guardrails

- If the chain requires web browsing, explicitly choose between:
  - `web.run` (fast structured browse)
  - `playwright` / `turix-cua` (dynamic/interactive)
- If the chain requires heavy model hosting (vLLM), provide a Lite alternative.

## Suggested chains (templates)

### A) “Research → report”

1. `webthinker-deep-research` (Lite) → `outputs/webthinker/.../report.md`
2. `flashrag-evidence` (local protocol checks) → citeable snippets
3. `code-reviewer` (if code changes) or `verification-quality-assurance` (if routing changes)

### B) “VCO enhancement work (config/skills)”

1. `flashrag-evidence` (locate existing policy/overlays)  
2. `writing-plans` (implementation plan with file paths + verify steps)
3. `verification-before-completion` (run check + router probe)
