# vibe-team Protocol

Protocol for XL-grade multi-agent tasks requiring coordination.

## Scope
Activated for XL grade tasks that require:
- Multiple agents working in parallel
- Workflow-based execution with phases
- Swarm or hive-mind coordination
- Long-running iterative tasks

## Hybrid Architecture: TeamCreate + ruflo

TeamCreate manages agent lifecycle + task assignment.
ruflo manages workflow definitions + vector memory + advanced coordination.
Both are complementary -- ruflo unavailable means TeamCreate runs independently.

### Role Division

| Concern | Provider | Tool |
|---------|----------|------|
| Agent spawning | TeamCreate | `Task` tool with `team_name` |
| Task list & assignment | TeamCreate | `TaskCreate`, `TaskUpdate`, `TaskList` |
| Agent messaging | TeamCreate | `SendMessage` (DM/broadcast) |
| Agent shutdown | TeamCreate | `SendMessage` type=shutdown_request |
| Workflow definition | ruflo | `workflow_create`, `workflow_execute` |
| Vector memory | ruflo | `memory_store`, `memory_search` |
| Session persistence | ruflo | `session_save`, `session_restore` |
| Consensus algorithms | ruflo | `hive-mind_consensus` |

## Orchestration Options

### Option A: Full Hybrid (TeamCreate + ruflo) -- Preferred
0. Load ruflo tools: `ToolSearch` to load required ruflo tools (workflow, memory, hive-mind) before first use — ruflo tools are deferred and unavailable until loaded
1. Define workflow: ruflo `workflow_create`
2. Create team: `TeamCreate` with descriptive `team_name`
3. Create tasks: `TaskCreate` for each workflow step
4. Spawn agents: `Task` tool with `team_name` + `subagent_type` per role
5. Assign tasks: `TaskUpdate` with `owner`
6. Coordinate: `SendMessage` for inter-agent communication
7. Store state: ruflo `memory_store` for intermediate results
8. Monitor: `TaskList` for progress
9. Consensus: ruflo `hive-mind_consensus` when agents need to agree
10. Shutdown: `SendMessage` type=shutdown_request, then `TeamDelete`

### Option B: TeamCreate Only (ruflo unavailable)
1. Create team: `TeamCreate`
2. Create tasks: `TaskCreate` with dependencies via `addBlockedBy`
3. Spawn agents: `Task` tool with `team_name` + appropriate `subagent_type`
4. Assign tasks: `TaskUpdate` with `owner`
5. Coordinate: `SendMessage` for DMs, broadcast for team-wide
6. Monitor: `TaskList` for progress tracking
7. Shutdown: `SendMessage` type=shutdown_request, then `TeamDelete`

Note: Without ruflo, use TodoWrite for state tracking.

### Option C: Ralph-loop (Iterative Tasks)
When task requires repeated iteration on same prompt:
1. User explicitly invokes /ralph-loop
2. Define completion promise (exit condition)
3. Set max iterations (safety limit)

IMPORTANT: Ralph-loop is MUTUALLY EXCLUSIVE with TeamCreate/ruflo.

## Agent Type Selection

| Role | subagent_type | Tools Available |
|------|--------------|-----------------|
| Researcher | `Explore` | Read-only: Glob, Grep, Read, WebSearch |
| Planner | `Plan` | Read-only: Glob, Grep, Read |
| Implementer | `general-purpose` | Full: Edit, Write, Bash, all tools |
| Reviewer | `everything-claude-code:code-reviewer` | Read + Bash |
| Security | `everything-claude-code:security-reviewer` | Read + Bash |

## Team Templates
See references/team-templates.md for 6 predefined compositions:
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

### XL Execution (TeamCreate)

Uses dialectic-design template from team-templates.md.

**Step 1 — Prepare context**
Lead reads relevant code/docs, formulates the design question, selects perspective pair from team-templates.md Perspective Assignment table.

**Step 2 — Create team**
```
TeamCreate: team_name = "dialectic-{topic}"
TaskCreate × 4: one per thinker agent
```

**Step 3 — Spawn agents with prompt template**
Each agent receives this prompt (Lead fills `{placeholders}`):

```
你是 {role} ({group} 组)。

设计问题：{question}

你的分析视角：{perspective}
上下文材料：{context_slice}

执行 6 阶段工作流：
1. Propose: 基于你的视角，独立提出一个完整方案（含架构、关键决策、风险）
2. Reflect: 列出你方案的 3 个最可能的生产环境失败模式
3. Synthesize: 基于自我批判改进方案 → SendMessage 给组内伙伴
4. Compare: 收到伙伴方案后，分析两个方案的核心分歧点
5. Reflect on comparison: 伙伴看到了什么你遗漏的？为什么会产生分歧？
6. Final synthesis: 整合伙伴洞察，产出最终方案 → SendMessage 给 Lead

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
4 agents run 6-phase workflow. Intra-group communication via SendMessage (A1↔A2, B1↔B2). Max 1 round.

**Step 6 — Collect**
Lead waits for 4 Phase-6 outputs.

**Step 7 — Timeout handling**
If any agent does not respond within reasonable time:
- Send reminder via SendMessage
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
SendMessage type=shutdown_request to all 4 agents → TeamDelete.

### L-Grade Adaptation

L grade cannot use TeamCreate (Rule 1). Instead, use Task tool to spawn 2 general-purpose agents sequentially (Plan agents are read-only and cannot execute Phase 3-5 interactions):

```
1. Agent-A: Task(subagent_type="general-purpose", prompt="{question} 从 {perspective_A} 视角分析")
2. Agent-B: Task(subagent_type="general-purpose", prompt="{question} 从 {perspective_B} 视角分析")
3. Lead synthesizes both outputs using the same output processing algorithm (Step 8)
```

Limitations vs XL: no intra-group dialogue (only 1 agent per perspective), no Phase 3-5 refinement. Suitable for moderate-complexity design decisions.

### Integration with think.md

- If `needs_dialectic = true` AND grade = L/XL → skip think.md B2 Self-Check, use Dialectic Mode instead
- If `needs_dialectic = true` AND grade = M → use think.md B2 Self-Check (dialectic is overkill for M)
- Dialectic Mode output feeds into writing-plans as the design foundation

## Conflict Avoidance
- Do NOT use Everything-CC agents for XL tasks (use TeamCreate agents)
- Do NOT use Superpowers subagent-driven-dev for XL tasks
- Ralph-loop and TeamCreate/ruflo are mutually exclusive
- Only one team active per project at a time
- TeamCreate agents communicate via SendMessage, NOT via ruflo agent_spawn
