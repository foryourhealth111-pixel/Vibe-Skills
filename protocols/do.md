# vibe-do Protocol

> **What this protocol does -- plain language overview**
>
> This is the execution protocol. It governs how VibeSkills writes code, fixes bugs,
> and runs tests -- specifically during Stage 5 (`plan_execute`) of the runtime.
>
> You do not need to read this to use VibeSkills. It is reference material for advanced
> users and contributors who want to understand how execution decisions are made.
>
> **Key terms used below:**
> - **M / L / XL grade**: Task complexity level. M = quick task, L = multi-step task, XL = large parallel task.
> - **Closure-First Contract**: The principle of reaching a working state quickly before expanding scope. Specifically: two probe steps + one verification step early in any task.
> - **Proxy-goal drift**: When the system optimizes a visible metric instead of the actual goal. Example: making all tests pass by deleting the failing tests, not fixing the code.
> - **P5 pattern**: "Evidence-Based Communication" -- never say "should work"; always show [Command] -> [Output] -> [Claim].
> - **V2 pattern**: "Completion Gate" -- identify what to verify, run it, read the output, confirm correctness, then mark complete.
> - **V7 pattern**: "Learning Capture" -- record what routing decision was made and how effective it was.


Protocol for coding, implementation, debugging, and testing tasks.

## Governed Runtime Position

This protocol is the execution surface for runtime stage 5 `plan_execute`.
It does not replace the governed runtime entry or skip the earlier planning stages defined in `protocols/runtime.md`.

The governed runtime path remains:

1. `skeleton_check`
2. `deep_interview`
3. `requirement_doc`
4. `xl_plan`
5. `plan_execute`
6. `phase_cleanup`

`do.md` assumes stages 1 through 4 have already produced:

- a frozen requirement document
- an execution plan
- an internal execution grade
- a frozen downstream delivery-acceptance contract

The job here is to execute, verify, and hand off cleanly to `phase_cleanup`.

## Runtime Mode Behavior

### `interactive_governed`

- may pause for explicit confirmation when execution scope materially changes
- should surface requirement or plan drift before continuing

## Anti-Drift Execution Guardrails

During execution:
- do not optimize a visible proxy signal while quietly abandoning the frozen objective,
- do not absorb validation material, sample text, or current failing examples into product truth without explicit approval,
- do not relabel a bounded fix as generalized completion unless the proof bundle supports that claim,
- do preserve valid specialization when the requirement or plan intentionally scoped the work that way.

These are execution guardrails and completion-language rules.
They are not a standalone blocking layer beyond the approved requirement, plan, and existing hard gates.

## Scope
Activated when the task requires writing or modifying code:
- Feature implementation
- Bug fixing and debugging
- Code refactoring
- Test writing

## Closure-First Contract (2 Probes + 1 Verify)

Primary objective for execution tasks: **avoid dead-air** and reach a **minimal closed loop** quickly.
This contract applies even if routing/pack selection is imperfect.

### Contract
Within the first 3 actions of an execution task, do:
1. **Probe #1 (glob, fast):** establish repo shape and likely entry points.
   - Example: `Get-ChildItem -Force | Select-Object Name`
2. **Probe #2 (rg, targeted):** search the most relevant keyword(s) from the user prompt.
   - Example: `rg -n -F -e '<keyword>' .`
3. **Verify #1 (smallest relevant):** pick 1 verification command that can falsify your change.
   - Coding: run the narrowest test (`pytest -q`, `npm test`, `pnpm test`, etc.)
   - Debug: reproduce the bug / run the failing test / run the minimal build step

### Router Hints (When Available)
If VCO router output includes:
- `closure_advice`: follow `closure_advice.contract.probes` + `closure_advice.contract.verify` (prefer verbatim).
- `exploration_advice`: use `exploration_advice.recommended_execution_mode`:
  - `analysis_first`: allow brief analysis first, but **do not skip probes**.
  - `direct_execution`: go straight to Probe #1 → Probe #2 → Verify.

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
2. Execute planned units in native serial order
   - Sequence-first execution from the frozen plan
   - No blanket multi-agent fan-out
3. Optional delegated units must remain bounded and explicitly planned
   - If subagents are spawned, prompts must end with `$vibe`
   - Child lane specialist ideas stay advisory in the frozen packet; execute may same-round auto-absorb only under root-governed approval logic
4. Use runtime-neutral state_store to track progress across tasks
5. Final review with Superpowers verification-before-completion

If subagents are spawned under the governed runtime, their prompts must end with `$vibe`.

### XL Grade
Defer to vibe-team protocol (wave-sequential orchestration + step-level bounded parallel units + optional ruflo collaboration).

## Debug Mode

| Grade | Approach | Tool |
|-------|----------|------|
| M | Structured debugging | superpowers:systematic-debugging (4-phase root cause) |
| L | Parallel investigation | systematic-debugging + dispatching-parallel-agents |
| Any | Build-specific errors | superpowers:systematic-debugging* |

*If an external build-error specialist is unavailable, keep build failures in the local systematic-debugging root-cause flow.

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
5. Delivery-acceptance evidence is sufficient for the claimed completion wording
6. A handoff bundle exists for runtime stage 6 `phase_cleanup`

## Required Handoff To `phase_cleanup`

Execution is not complete at the last passing test.
Before leaving this protocol, write or preserve the evidence needed for cleanup:

- verification commands and results
- changed artifact list
- temp artifact list
- node or process cleanup notes when relevant
- manual spot-check status when the frozen requirement declared them
- completion-language downgrade notes when delivery truth is not fully passing
- open risks or deferred follow-ups

`phase_cleanup` is mandatory and owns the final closure receipt.

## Conflict Avoidance
- Do NOT use ruflo agent_spawn for M/L coding tasks
- Do NOT use SuperClaude sc:implement (use VCO flow)
- Everything-CC hooks always run -- do not disable
- For L grade, use Superpowers subagent system, NOT Everything-CC agents.
- If the preferred orchestration stack is unavailable, do not silently downgrade. Follow `fallback-chains.md` only as an explicit degraded path, emit a standalone hazard alert, and record that the resulting execution is non-authoritative.
- Do not self-introduce new fallback logic during implementation unless the active requirement document explicitly approves fallback-related changes.
- Do not convert primary-path failure into fake success by swallowing exceptions, returning template-only success text, or leaving mock / simulation placeholders in production behavior.
- Prefer explicit failure exposure over convenience recovery: if the real path fails, keep the failure visible in logs, receipts, verification output, or downgraded closure wording.
- If a requirement explicitly permits fallback or degraded behavior, keep it explicit, document the trigger and non-authoritative status, and make the path easy to disable or remove later.
