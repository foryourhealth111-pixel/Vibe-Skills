# vibe-team Protocol

Protocol for XL-grade multi-agent tasks requiring coordination.

## Scope
Activated for XL grade tasks that require:
- Multiple agents working in parallel
- Workflow-based execution with phases
- Swarm or hive-mind coordination
- Long-running iterative tasks

## Hybrid Architecture: Codex Native Team + ruflo Collaboration

Codex native agent APIs manage lifecycle + task assignment (primary path).
ruflo remains optional for workflow/memory enhancements.

### Role Division

| Concern | Provider | Tool |
|---------|----------|------|
| Agent spawning | Codex native | `spawn_agent` |
| Task assignment & follow-up | Codex native | `send_input` |
| Agent synchronization | Codex native | `wait` |
| Agent shutdown | Codex native | `close_agent` |
| Workflow definition (optional) | ruflo | `workflow_create`, `workflow_execute` |
| Vector memory (optional) | ruflo | `memory_store`, `memory_search` |
| Session persistence (optional) | ruflo | `session_save`, `session_restore` |
| Consensus algorithms (optional) | ruflo | `hive-mind_consensus` |

## Orchestration Options

### Option A: Codex Native Team + ruflo Collaboration (Preferred)
1. Define decomposition plan (owners + interfaces + deliverables)
2. Spawn agents via `spawn_agent` with role-specific prompts
3. Assign work and clarifications via `send_input`
4. Store intermediate state via ruflo `memory_store` (milestone summaries, handoff artifacts)
5. Use ruflo `workflow_create` / `workflow_execute` when explicit step orchestration is needed
6. Synchronize via `wait` at each milestone
7. Use ruflo `hive-mind_consensus` when formal consensus is required
8. Aggregate and reconcile outputs in lead agent/context
9. Close agents via `close_agent`

### Option B: Codex Native Team Only (When ruflo Unavailable)
1. Run native lifecycle only: `spawn_agent` → `send_input` → `wait` → `close_agent`
2. Use runtime-neutral state_store + conversation context for milestone state
3. Keep the same staged confirmations and validation gates

### Option C: Ralph-loop (Iterative Tasks)
When task requires repeated iteration on same prompt:
1. User explicitly invokes /ralph-loop
2. Define completion promise (exit condition)
3. Set max iterations (safety limit)

IMPORTANT: Ralph-loop is MUTUALLY EXCLUSIVE with active team orchestration.

## Agent Type Selection

| Role | Native Agent Type | Notes |
|------|-------------------|-------|
| Researcher | `explorer` | Read/search-heavy investigation |
| Planner | `default` | Planning + decomposition |
| Implementer | `worker` | Implementation ownership with isolated scope |
| Reviewer | `worker` or `default` | Review prompt enforces bug/risk-first output |
| Security | `worker` or `default` | Security-focused prompt and checklist |

## Team Templates
See references/team-templates.md for 7 predefined compositions:
- feature-team, debug-team, research-team, review-team, full-stack-team, dialectic-design

If `local-vco-roles` is installed, you may also use:
- local-vco-dialectic-review (Template 7)
- Role prompts sourced from `~/.codex/skills/local-vco-roles/references/role-prompts/`

## Staged Confirmation
Always confirm with user at these points:
1. After workflow definition (before spawning agents)
2. After each major phase completion
3. Before final integration of results
4. Before committing changes

## Quality Injection: Enhanced Tier (XL Default)

In addition to Core Tier (P5, V2, V7 + task-type-specific from vibe-do):

### Additional Enhanced Patterns
- **P2**: Effort Allocation. 验证阶段的投入应与执行阶段相当，不可跳过。顺序：理解 → 规划 → 执行 → 验证，每阶段都应有明确产出。
- **P6**: PDCA Cycle. Plan -> Do -> Check -> Act. Never retry without understanding WHY it failed.
- **V4**: Red Flags Self-Check. REJECT: "Quick fix for now", "Just try changing X", "Might work".
- **V5**: Rationalization Blocker. "Should work now" -> demand verification. "I am confident" -> confidence != evidence.
- **V6**: Agent Trust-But-Verify. After agent returns: check VCS diff independently, run verification, compare claim vs evidence.

### XL Injection Matrix

| Task Type | Pre-Injection | Post-Validation |
|-----------|--------------|-----------------|
| Planning | P3, P5, P6 | V2, V5, V6, V7 |
| Coding | P5, P6 | V2, V3, V5, V6, V7 |
| Review | P3, P5 | V2, V5, V6, V7 |
| Debug | P1, P4, P5, P6 | V2, V4, V5, V6, V7 |
| Research | P2, P3, P5, P6 | V1, V2, V5, V6, V7 |

## Dialectic Mode

Structured multi-perspective design analysis. Activated when `needs_dialectic = true` in Quick Probe or user explicitly requests dialectical/multi-perspective analysis.

### When to Use

- Multiple viable architectural approaches with unclear trade-offs
- High-stakes design decisions where blind spots are costly
- User explicitly requests "辩证", "dialectic", "多视角", "权衡"

### Not For

- Implementation tasks (use standard coding flow)
- Single correct answer questions (use sc:research)
- Trivial design choices (use think.md B2 Self-Check instead)
- Debugging (use debug-team template)

### XL Execution (Codex Native Team)

Uses dialectic-design template from team-templates.md.

**Step 1 — Prepare context**
Lead reads relevant code/docs, formulates the design question, selects perspective pair from team-templates.md Perspective Assignment table.

**Step 2 — Create team**
```
spawn_agent × 4: one per thinker agent
```

**Step 3 — Send role prompt template**
Each agent receives this prompt (Lead fills `{placeholders}`):

```
你是 {role} ({group} 组)。

设计问题：{question}

你的分析视角：{perspective}
上下文材料：{context_slice}

执行 6 阶段工作流：
1. Propose: 基于你的视角，独立提出一个完整方案（含架构、关键决策、风险）
2. Reflect: 列出你方案的 3 个最可能的生产环境失败模式
3. Synthesize: 基于自我批判改进方案 → 通过 send_input 发给组内伙伴
4. Compare: 收到伙伴方案后，分析两个方案的核心分歧点
5. Reflect on comparison: 伙伴看到了什么你遗漏的？为什么会产生分歧？
6. Final synthesis: 整合伙伴洞察，产出最终方案 → 通过 send_input 发给 Lead

输出格式（Phase 6）：
- 方案摘要（≤200字）
- 关键决策 + 理由（列表）
- 已知风险 + 缓解策略
- 从伙伴方案吸收的要素
```

**Step 4 — Context isolation**
Group A receives context slice emphasizing perspective A's concerns.
Group B receives context slice emphasizing perspective B's concerns.
Groups do NOT share context or communicate cross-group.

**Step 5 — Execute**
4 agents run 6-phase workflow. Intra-group communication via `send_input` (A1↔A2, B1↔B2). Max 1 round.

**Step 6 — Collect**
Lead waits for 4 Phase-6 outputs.

**Step 7 — Timeout handling**
If any agent does not respond within reasonable time:
- Send reminder via `send_input`
- If still no response: proceed with available outputs (minimum 2 from different groups)
- If <2 outputs: abort dialectic, fall back to think.md B2 Self-Check

**Step 8 — Output processing**
Lead analyzes 4 final syntheses:

```
1. Extract consensus: 所有方案一致同意的决策点
2. Extract divergence: 方案间的核心分歧 + 每方的论据
3. Identify blind spots: 某组发现而另一组完全未提及的风险/机会
4. Synthesize: 产出综合方案（consensus 为基础 + divergence 中选择最优 + blind spots 纳入风险清单）
5. Present to user:
   - 综合方案
   - 关键分歧点 + 各方论据（供用户决策）
   - 风险清单（含 blind spot 来源标注）
```

**Step 9 — User decision**
Present synthesis to user. User may:
- Accept synthesis as-is → proceed to implementation
- Choose one group's approach → proceed with that direction
- Request deeper analysis on specific divergence point

**Step 10 — Shutdown**
Close all 4 agents via `close_agent`.

### L-Grade Adaptation

L grade does not run XL team orchestration. Use 2 native agents sequentially:

```
1. Agent-A: spawn_agent(agent_type="default" or "worker", prompt="{question} 从 {perspective_A} 视角分析")
2. Agent-B: spawn_agent(agent_type="default" or "worker", prompt="{question} 从 {perspective_B} 视角分析")
3. Lead synthesizes both outputs using the same output processing algorithm (Step 8)
```

Limitations vs XL: no intra-group dialogue (only 1 agent per perspective), no Phase 3-5 refinement. Suitable for moderate-complexity design decisions.

### Integration with think.md

- If `needs_dialectic = true` AND grade = L/XL → skip think.md B2 Self-Check, use Dialectic Mode instead
- If `needs_dialectic = true` AND grade = M → use think.md B2 Self-Check (dialectic is overkill for M)
- Dialectic Mode output feeds into writing-plans as the design foundation

## Conflict Avoidance
- Do NOT use Everything-CC agents as the primary XL executor (use Codex native team)
- Do NOT use Superpowers subagent-driven-dev for XL tasks
- Ralph-loop and active team orchestration are mutually exclusive
- Only one team active per project at a time
- Prefer native agent communication via `send_input`
