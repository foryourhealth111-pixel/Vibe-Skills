# VCO Fallback Chains

Degradation paths when primary tools are unavailable or fail.
All fallback targets are existing tools from the 6 integrated plugins.

## Principle

- M/L grade: 2-level fallback (Primary -> Fallback -> Direct reasoning)
- XL grade: 3-level fallback (Primary -> Degraded XL -> L-grade sequential -> Direct reasoning)

Fallback triggers:
- MCP server not running (ruflo, Serena, episodic-memory)
- Agent timeout or error
- Tool produces no useful output
- Plugin not installed

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
| M | superpowers:systematic-debugging | everything-claude-code:build-error-resolver (or local build-error-resolver -> error-resolver alias) |
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

## Memory System Fallbacks

| System | Primary | Fallback |
|--------|---------|----------|
| Session state | ruflo memory_store | state_store + conversation context |
| Cross-session | episodic-memory:search | Serena MCP read_memory |
| Pattern learning | continuous-learning-v2 | episodic-memory (manual notes) |
| Project knowledge | Serena MCP write_memory | ruflo memory_store with "project" tag |

## Fallback Detection

1. MCP not running: Tool call returns connection error or timeout
2. Agent failure: Task agent returns error or empty result
3. Quality failure: Output doesn't address the task (requires judgment)
4. Plugin missing: Skill invocation returns "skill not found"
5. Native team failure: spawn/send/wait/close orchestration fails

## build-error-resolver Compatibility

Resolution order for build-specific debugging:
1. `everything-claude-code:build-error-resolver`
2. local `build-error-resolver` alias skill
3. `error-resolver` skill

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
4. 收到 compaction 提示时：立即保存关键决策到 state_store/ruflo
5. Always store key decisions BEFORE compaction
