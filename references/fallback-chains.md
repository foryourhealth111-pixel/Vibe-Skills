# VCO Fallback Chains

Degradation paths when primary tools are unavailable or fail.
All fallback targets are existing tools from the 6 integrated plugins.

## Principle

- M/L grade: 2-level fallback (Primary -> Fallback -> Direct reasoning)
- XL grade: 3-level fallback (Primary -> Degraded XL -> L-grade sequential -> Direct reasoning)

Fallback triggers:
- MCP server not running (ruflo, Serena, Cognee)
- Agent timeout or error
- Tool produces no useful output
- Plugin not installed
- Pack router confidence below configured threshold

## M/L Grade Fallback Chains (2-Level)

### Planning Tasks

| Grade | Primary | Fallback |
|-------|---------|----------|
| M | sc:design | everything-claude-code:planner agent |
| L | superpowers:brainstorming + writing-plans | sc:brainstorm + sc:workflow |

### Coding Tasks

| Grade | Primary | Fallback |
|-------|---------|----------|
| M | everything-claude-code:tdd-guide | superpowers:test-driven-development |
| L | superpowers:subagent-driven-dev | everything-claude-code:planner + tdd-guide |

### Review Tasks

| Grade | Primary | Fallback |
|-------|---------|----------|
| M | everything-claude-code:code-reviewer | superpowers:requesting-code-review |
| L | superpowers:requesting-code-review (two-stage) | everything-claude-code:code-reviewer + security-reviewer |

### Debug Tasks

| Grade | Primary | Fallback |
|-------|---------|----------|
| M | superpowers:systematic-debugging | systematic-debugging with exact failing command and stderr/stdout |
| L | systematic-debugging + dispatching-parallel-agents | systematic-debugging (single) |

### Research Tasks

| Grade | Primary | Fallback |
|-------|---------|----------|
| M | sc:research | claude-code-settings:deep-research |
| L | claude-code-settings:deep-research | sc:research |

### Analysis (Pre-routing)

| Grade | Primary | Fallback |
|-------|---------|----------|
| M | claude-code-settings:think-harder | sc:analyze |
| L | claude-code-settings:think-ultra | claude-code-settings:think-harder |

If both levels fail: fall back to direct Claude reasoning (no tool).

## Pack Router Overlay Fallback

```
Pack scoring success + confidence >= threshold
  -> route by selected pack skill candidates
Pack scoring success + confidence < threshold
  -> fallback to legacy Grade×Type matrix
Pack config missing/invalid
  -> fallback to legacy Grade×Type matrix
```

## Web Scraping Pack Fallback (scrapling)

When pack `web-scraping` is selected:

- Primary: `scrapling` (external CLI / optional MCP server) for fast targeted extraction (CSS/XPath).
- Fallback: `playwright` for pages requiring real browser interaction, JS execution, login flows, or when `scrapling` is missing/blocked.
- Last resort: direct Claude reasoning after obtaining an HTML/text dump from the user.

## GSD-Lite Overlay Fallback (Planning Hook Layer)

Overlay policy source: `config/gsd-overlay.json` (and bundled mirror).

```
Overlay disabled/off
  -> bypass hook, run standard protocol
Overlay enabled + config missing/parse error
  -> advisory warning, bypass hook
Brownfield snapshot failure
  -> skip snapshot artifact, continue planning flow
Assumption gate generation failure
  -> skip confirm escalation, continue standard B1-B4
Wave contract generation failure
  -> revert to standard Option A/B team orchestration
```

Rules:
1. Overlay fallback never changes selected grade/task/pack.
2. Overlay fallback never blocks core VCO execution path unless strict policy explicitly requires it.
3. Overlay artifacts are advisory unless mode/policy marks them required.

## XL Grade Fallback Chain (3-Level)

```
Level 1: Codex native team + ruflo collaboration (preferred)
  |
  v (ruflo unavailable, native APIs still available)
Level 1 (degraded): Codex native team only (state_store + conversation state)
  |
  v (native team APIs unavailable or orchestration failure)
Level 2: Sequential L-grade execution (Superpowers subagent system)
  |
  v (all multi-agent fails)
Direct: Single-agent execution with direct Claude reasoning
```

### XL Task-Specific Chains

| Task Type | Level 1 | Level 2 | Level 3 |
|-----------|---------|---------|---------|
| Planning | Codex native planning team + ruflo workflow/memory | Codex native planning team only | superpowers:writing-plans |
| Coding | Codex native implementer team + ruflo handoff memory | Codex native implementer team only | superpowers:subagent-driven-dev |
| Review | Codex native multi-reviewer + optional ruflo consensus | Codex native multi-reviewer only | superpowers:dispatching-parallel-agents |
| Research | Codex native research team + ruflo memory | Codex native research team only | claude-code-settings:deep-research |

## Ralph-loop Engine Fallback

When user explicitly uses `/ralph-loop`:

| Primary | Fallback | Last resort |
|---------|----------|-------------|
| `ralph-loop --engine open` (external open-ralph-wiggum) | `ralph-loop --engine compat` (local state loop) | direct manual iteration without loop wrapper |

Notes:
- `open` engine is optional and depends on external `ralph` CLI availability.
- `compat` engine is always the stability baseline inside VCO.
- `cancel-ralph` only affects `compat` engine local state.
- Wave B upstream review (2026-03-17): latest upstream fixes reduce false exit / quota-exhaustion behavior in the optional open backend, but do not change fallback order or compat-baseline policy.

## Memory System Fallbacks

| System | Primary | Fallback |
|--------|---------|----------|
| Session state | state_store | conversation context |
| Explicit project decisions | Serena MCP write_memory | state_store decision log |
| Short-term semantic cache | ruflo memory_store | state_store keyed snapshots |
| Long-term graph retrieval | Cognee graph retrieval (optional) | Serena indexed summaries |
| episodic-memory | disabled | use Cognee/Serena by role boundary |

## Retro Context Expert Fallback

When running `vibe-retro` with Context Retro Advisor:

1. Primary: Agent-Skills-for-Context-Engineering guidance (context diagnosis playbook)
2. Fallback A: `context-fundamentals` + VCO retro heuristics
3. Fallback B: VCO retro heuristics only (evidence-based manual diagnosis)

Notes:
- Retro advisor is guidance-only and does not auto-modify config.
- If advisor sources are partially missing, continue with available evidence and mark confidence scope explicitly.

## Fallback Detection

1. MCP not running: Tool call returns connection error or timeout
2. Agent failure: Task agent returns error or empty result
3. Quality failure: Output doesn't address the task (requires judgment)
4. Plugin missing: Skill invocation returns "skill not found"
5. Native team failure: spawn/send/wait/close orchestration fails

## Build Failure Compatibility

Resolution order for build-specific debugging:
1. Use `superpowers:systematic-debugging` as the local route authority.
2. Capture the exact failing command and full stderr/stdout.
3. Classify dependency/setup, compile/type/lint, env/config, or test/runtime failure.
4. Re-run the original failing command after the smallest root-cause fix.

## Fallback Protocol

```
1. Attempt primary tool
2. If failure detected:
   a. Log the failure reason (for instinct system learning)
   b. Inform user: "Primary tool [X] unavailable, falling back to [Y]"
   c. Attempt fallback
3. If fallback also fails:
   a. M/L: Use direct Claude reasoning, inform user of limitations
   b. XL: Try next level in 3-level chain
4. If all levels fail:
   a. Use direct Claude reasoning (no tool)
   b. Inform user of limitations
```

### Anti-Silent Guard (runtime)

When `config/router-thresholds.json -> safety.enforce_confirm_on_legacy_fallback=true`:

1. Any computed `route_mode=legacy_fallback` is upgraded to `route_mode=confirm_required`.
2. `route_reason` is set to `legacy_fallback_guard`.
3. Original fallback reason is preserved in `legacy_fallback_original_reason`.

This makes fallback visible to operators instead of silently continuing.

## Context Budget Awareness

| Situation | Tool | Source |
|-----------|------|--------|
| Context getting large | everything-claude-code:strategic-compact | Everything-CC |
| Preserve state before compact | ruflo session_save (or state_store) | Claude-flow |
| Resume after compact | ruflo session_restore (or re-read state_store) | Claude-flow |
| Store intermediate results | ruflo memory_store (or state_store) | Claude-flow |

### Context Budget Rules
1. L+ 任务开始前，评估任务复杂度与当前对话长度
2. L 任务中对话明显变长时：考虑 strategic-compact
3. XL 任务中多 agent 返回大量结果时：保存状态后 compact
4. 收到 compaction 提示时：立即保存关键决策到 state_store（必要时写入 Serena）
5. Always store key decisions BEFORE compaction
