# VCO Conflict Avoidance Rules

3 rules for preventing conflicts between the 6 integrated tools.
VCO 通过指令约束（非代码强制）防止冲突。这些是规则而非建议——Claude 应严格遵守，但用户应知晓违反时不会有技术层面的阻断。
All existing hooks remain active. VCO controls which MCP tools are actively invoked.

## Rule 1: Agent Boundary

NEVER use multiple agent systems for the same task.

| Grade | Agent System | Reason |
|-------|-------------|--------|
| M | Single-agent tools (Everything-CC agents as primary; individual skill commands like sc:design, systematic-debugging permitted — no subagent spawning) | Lightweight, focused |
| L | Superpowers subagent-driven-dev | Two-stage review (spec + quality) |
| XL | Codex native team (`spawn_agent` family) + ruflo collaboration | Primary multi-agent orchestration |
| XL (degraded) | Codex native team (`spawn_agent` family) only | When ruflo unavailable |

Exceptions (specialized diagnostic agents may cross grade boundaries):
- build-error-resolver: May be used at any grade for build failures (if unavailable, use local build-error-resolver -> error-resolver alias)
- security-reviewer: May be used at any grade for security audits

Fallback provision: 当某 grade 的主 agent 系统不可用时，严格按 references/fallback-chains.md 定义的路径降级，不视为违反 Rule 1。不得自行选择降级目标。

### Contextual Notes

**Brainstorming deconfliction:**
- Requirements discovery -> Superpowers brainstorming (HARD-GATE)
- Architecture design -> SuperClaude sc:design (persona system)
- Implementation planning -> Superpowers writing-plans
- Never invoke both brainstorming systems simultaneously

**Review deconfliction:**
- M -> Everything-CC code-reviewer (lightweight, auto-triggered)
- L -> Superpowers two-stage review (spec + quality)
- XL -> Codex native multi-agent review (parallel perspectives)
- Security review -> Everything-CC security-reviewer (any grade, exempt)

**Hook coexistence:**
- All hooks from all plugins run. VCO does not disable any hooks.
- Superpowers SessionStart: always runs, VCO respects skill-checking mandate
- Everything-CC PreToolUse/PostToolUse: always runs, VCO leverages quality guards
- Claude-flow hooks: run passively, VCO calls ruflo only for XL enhancement
- Ralph-loop Stop: only activates when user explicitly starts /ralph-loop
- Codex native team tools are runtime primitives (no plugin hooks)

## Rule 2: Memory Division

Each memory system has a specific role. Do not cross boundaries.

| Memory System | Scope | Use For |
|--------------|-------|---------|
| state_store (runtime-neutral) | Session-level (default) | Task state, intermediate results |
| ruflo memory_store | Current project, session | Vector search, enhanced state (when available) |
| Serena MCP write_memory | Project knowledge | Architecture decisions, conventions |
| episodic-memory | Cross-session, long-term | Searching past conversations |
| Everything-CC instincts | Behavioral patterns | Auto-applying learned patterns |

Key principle: state_store is the DEFAULT, not the fallback.
ruflo/Serena are ENHANCEMENTS. System runs fully on state_store + conversation context even if all MCP servers are down.

## Rule 3: Command Priority

Priority order:
1. User explicit command (highest) -- e.g., /sc:design, /ralph-loop -> bypass VCO
2. VCO protocol instructions
3. Individual plugin default behaviors (lowest)

Exception: If user explicitly invokes a specific tool command, bypass VCO routing and use that tool directly.

## Adding New Rules

When a new conflict is discovered:
1. Document the conflict scenario
2. Define the resolution strategy
3. Add to the appropriate rule section or contextual notes
4. Update SKILL.md conflict summary if the rule is frequently needed
