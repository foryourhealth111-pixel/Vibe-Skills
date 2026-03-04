# vibe-think Protocol

Pre-routing analysis and post-routing planning/design/research protocol.

## Closure-First Preflight (2 Probes + 1 Verify)

Even in planning/research, the primary failure mode is **stalling** (dead-air).
So we run a minimal closed loop early: probe context → locate evidence → verify assumptions.

### Contract (No Code Writing)
Within the first 3 actions, do:
1. **Probe #1 (glob, fast):** inspect repo shape / available docs.
   - Example: `Get-ChildItem -Force | Select-Object Name`
2. **Probe #2 (rg, targeted):** search for the most relevant keyword(s) and existing plans/specs.
   - Example: `rg -n -F -e '<keyword>' docs .`
3. **Verify #1:** before final recommendations, validate at least 1 key assumption against an artifact:
   - Repo evidence (README/config/code), or
   - 2 independent external sources for factual claims (research).

### Router Hints (When Available)
If VCO router output includes:
- `closure_advice`: follow `closure_advice.contract.probes` + `closure_advice.contract.verify` (prefer verbatim).
- `exploration_advice`: use `exploration_advice.recommended_execution_mode` to pace analysis, but **still do probes early**.

## Scope

### Phase A: Pre-Execution Analysis (L grade, before implementation)

Activated when L-grade task needs structured analysis before execution:
- Task could be classified as multiple types → clarify via analysis
- User explicitly asks to "analyze", "think through", or "evaluate"
- Compound task requiring decomposition into phases

### Phase B: Planning & Design Execution (L grade)

Activated for L-grade planning, design, and research tasks:
- Requirements analysis and discovery
- Architecture and system design
- Research and investigation
- Option evaluation and comparison

## Phase A: Pre-Execution Analysis

### A1: Problem Framing
Tool: None (Claude native reasoning)
- What exactly is being asked? What are the constraints?
- Is this a single task or compound task?

### A2: Structured Analysis (by estimated grade)

| Estimated Grade | Tool | Source |
|----------------|------|--------|
| M | claude-code-settings:think-harder | 4-phase analysis |
| L | claude-code-settings:think-ultra | 7-phase analysis |
| XL | superpowers:brainstorming | Socratic dialogue |
| Any | sc:analyze | Code-focused analysis |

### A3: Classification Decision
Based on analysis output, determine:
- Final grade (may differ from initial estimate)
- Task type (plan/code/review/debug/research)
- Compound task? -> decompose (see below)

### Compound Task Decomposition

| Grade | Tool | Source |
|-------|------|--------|
| M | everything-claude-code:planner agent | Everything-CC |
| L | superpowers:writing-plans | Superpowers |
| XL | ruflo workflow_create | Claude-flow |

Output: ordered phases, each with protocol, quality gate, and handoff context.

### Example: "Design and implement user auth"

```
Phase 1: Requirements (vibe-think)
  Tool: superpowers:brainstorming
  Gate: Requirements document approved by user

Phase 2: Architecture (vibe-think)
  Tool: sc:design
  Gate: Architecture diagram approved

Phase 3: Implementation (vibe-do)
  Tool: superpowers:subagent-driven-development
  Gate: All tests pass, code reviewed

Phase 4: Security Review (vibe-review)
  Tool: everything-claude-code:security-reviewer
  Gate: No CRITICAL findings
```

## Phase B: Planning & Design Execution (L Grade)

### B1: Requirements Discovery
Tool: superpowers:brainstorming
- Socratic dialogue pattern
- HARD-GATE: No implementation until design is approved
- Output: Clarified requirements, user stories, acceptance criteria

### B2: Architecture Design (if needed)
Tool: sc:design
- Cognitive personas (architect, security, frontend, backend)
- Output: Architecture diagrams, component design, data flow

### B2 Self-Check (All Design Tasks)

After generating initial design (via sc:design or brainstorming):
1. List 3 ways this design could fail in production
2. If any failure mode suggests a fundamentally different approach → generate alternative
3. If alternative is equally viable → present both to user with trade-off comparison
4. If no viable alternative → proceed with original + document failure modes as risks

Note: If user explicitly requested dialectic think-tank mode, skip B2 Self-Check and route to
team.md Dialectic Mode instead.

### B3: Plan Documentation
Tool: superpowers:writing-plans
- Generates plan at docs/plans/YYYY-MM-DD-<topic>.md
- Output: Actionable implementation plan with phases

### B4: Deep Research (if needed)
Tool: claude-code-settings:deep-research
- Multi-agent parallel research workflow
- Output: Research findings with sources

### B5: GSD-Lite Preflight Hook (Optional, L/XL Planning Only)
Policy source: `config/gsd-overlay.json`

Run this hook only when all conditions are met:
1. `enabled=true` and `mode != off`
2. Current task type is `planning`
3. Current grade is in `grade_allow` (default: `L`, `XL`)

Hard boundaries:
- Post-route governance only. Never re-run grade/task/pack routing.
- Do not introduce `/gsd:*` command flow.
- Do not create a second source-of-truth state tree.

Hook steps:
1. **Brownfield context snapshot** (when `brownfield_context.enabled=true`)
   - Build or refresh a light snapshot under `docs/vco-context/`:
     - `STACK.md`
     - `ARCHITECTURE.md`
     - `CONVENTIONS.md`
     - `CONCERNS.md`
   - If snapshot is missing or stale, mark advisory warning and continue.
2. **Assumption preflight**
   - Produce a concise assumptions list before writing the final plan.
   - Persist assumptions to the active planning artifact (or `assumptions.md` when configured).
3. **Confirm policy by mode**
   - `shadow`: record advice only, no blocking.
   - `soft`: require confirm only for grades in `assumption_gate.confirm_required_for`.
   - `strict`: require confirm for all in-scope grades.
4. **Handoff**
   - Carry assumptions + brownfield context into B3 output.

On hook failure, follow `references/fallback-chains.md` GSD-Lite fallback and continue standard B1-B4 flow.

## Research Mode
When task is purely research (no implementation):
1. Skip B1 unless scope is unclear
2. Go directly to B4 (deep-research)
3. Optionally use sc:research for web research
4. Store findings in ruflo memory (or state_store if unavailable)

## Conflict Avoidance
- Do NOT write code during this protocol (respect HARD-GATE)
- Do NOT invoke both brainstorming systems simultaneously
- think-harder/think-ultra = problem analysis, brainstorming = requirements discovery
- Analysis (Phase A) completes BEFORE implementation begins, not in parallel with execution

## Transition to Implementation
After design is approved:
1. L grade: Switch to vibe-do with Superpowers subagent-driven-dev
2. XL grade: Switch to vibe-team protocol (Codex native team + optional ruflo collaboration)
3. Always carry the plan document forward as context
