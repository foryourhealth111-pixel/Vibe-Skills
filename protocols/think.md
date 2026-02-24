# vibe-think Protocol

Pre-routing analysis and post-routing planning/design/research protocol.

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

Note: If user requested dialectical analysis, skip B2 Self-Check and route to
team.md Dialectic Mode instead.

### B3: Plan Documentation
Tool: superpowers:writing-plans
- Generates plan at docs/plans/YYYY-MM-DD-<topic>.md
- Output: Actionable implementation plan with phases

### B4: Deep Research (if needed)
Tool: claude-code-settings:deep-research
- Multi-agent parallel research workflow
- Output: Research findings with sources

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
