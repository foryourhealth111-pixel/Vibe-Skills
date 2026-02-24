# vibe-do Protocol

Protocol for coding, implementation, debugging, and testing tasks.

## Scope
Activated when the task requires writing or modifying code:
- Feature implementation
- Bug fixing and debugging
- Code refactoring
- Test writing

## Tool Orchestration by Grade

### M Grade
1. Pre-implementation: Everything-CC tdd-guide agent
   - Write tests first (RED)
   - Implement to pass (GREEN)
   - Refactor (IMPROVE)
2. Implementation: Claude Code native tools
3. Post-implementation: Everything-CC code-reviewer auto-triggers
4. If security-relevant: Everything-CC security-reviewer

### L Grade
1. Ensure design exists (from vibe-think protocol)
2. Invoke Superpowers subagent-driven-development
   - Fresh subagent per task
   - Two-stage review: spec compliance + code quality
   - Sequential execution to avoid conflicts
3. Use runtime-neutral state_store to track progress across tasks
4. Final review with Superpowers verification-before-completion

### XL Grade
Defer to vibe-team protocol (Codex native team orchestration + optional ruflo collaboration).

## Debug Mode

| Grade | Approach | Tool |
|-------|----------|------|
| M | Structured debugging | superpowers:systematic-debugging (4-phase root cause) |
| L | Parallel investigation | systematic-debugging + dispatching-parallel-agents |
| Any | Build-specific errors | everything-claude-code:build-error-resolver* |

*If unavailable, fall back to local build-error-resolver alias skill (delegates to error-resolver).

## Browser Testing
When UI testing is needed:
- Primary: Claude-code-settings Chrome MCP (chrome-devtools-mcp)
- Alternative: Playwright MCP (if available)

## Quality Injection: Core Tier (L/XL Default)

### Always-On Patterns
- **P5**: Evidence-Based Communication. NEVER say "should work", "probably fine". ALWAYS use [Command] [Output] [Claim] format.
- **V2**: Completion Gate. IDENTIFY what to verify -> RUN verification -> READ output -> VERIFY correctness -> MARK COMPLETE.
- **V7**: Learning Capture. Routing decision + injection effectiveness + improvements.

### Task-Type-Specific Core Patterns

| Task Type | Additional Patterns | Reason |
|-----------|-------------------|--------|
| Debug | P1 (Root Cause Discipline) + P4 (Scientific Method) | Prevents blind fix attempts |
| Coding | V3 (6-Phase Quality Pipeline) | Ensures code quality gates |
| Research | V1 (Evidence Chain: every claim links to a verifiable source) | Ensures cited sources |
| Planning | P3 (Structured Analysis: decompose into sub-problems, evaluate each systematically) | Systematic decomposition |

### V3: 6-Phase Quality Pipeline (Coding Tasks)
Build -> Types -> Lint -> Tests -> Security -> Diff -> [READY / NOT READY]

### P1: Root Cause Discipline (Debug Tasks)
Iron Law: NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST.
Complete Phase 1 (root cause investigation) before proposing fixes.
If 3+ fix attempts fail, STOP and question the architecture.

### P4: Scientific Method (Debug Tasks)
Form SINGLE hypothesis. State clearly: I think X because Y.
Make SMALLEST possible change to test. One variable at a time.

### Context Budget Fallback
- Normal: Full core tier
- 对话明显变长（多轮工具调用、大量代码输出）: P5 + V2 + V7 only
- 接近上下文极限（收到 compaction 提示或输出被截断）: Skip injection, note in V7 feedback

### Behavioral Tone (All Grades)

- **Conclusion-First Output**: 先交付结论/结果，再以 P5 格式提供证据链。
  用户看到的第一行是答案，不是过程。
- **Exploration Budget**: 面对未知问题，连续探索性工具调用（Glob/Grep/Read/WebSearch）
  不超过 8 次。超出后：总结已知信息 → 向用户请求方向指引。
- **No Self-Commentary**: 不解释困难程度，不自我评价。直接交付工程结果。

## Quality Gates
Before marking code task complete:
1. All tests pass
2. Code review completed
3. No security vulnerabilities (for user-facing code)
4. No console.log left in production code

## Conflict Avoidance
- Do NOT use ruflo agent_spawn for M/L coding tasks
- Do NOT use SuperClaude sc:implement (use VCO flow)
- Everything-CC hooks always run -- do not disable
- For L grade, use Superpowers subagent system, NOT Everything-CC agents. Fallback provision: when Superpowers is unavailable, strictly follow fallback-chains.md defined degradation path
