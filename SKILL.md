---
name: vibe
description: Vibe Code Orchestrator (VCO) routes development tasks by grade and coordinates tool workflows for implementation, debugging, review, and planning.
---

# VCO v2.0 — Vibe Code Orchestrator

Unified entry point: classifies tasks via quick probe + user decision, selects optimal tools, coordinates 6 integrated plugins.

## When to Use

- User starts a development task needing tool coordination
- User types `/vibe` + task description
- Task spans multiple tools or requires plugin coordination
- User unsure which tool/command to use
- NOT for trivial tasks (typo fix, single-line change, answering questions) — not invoking /vibe = implicit S-grade, zero overhead

## Boundaries

- Routes TO individual tool skills, does not replace them
- Does not modify plugin source code or hooks
- User's explicit tool choice overrides VCO (e.g., `/sc:design` → use directly)
- If task description is ambiguous, ask: "What is the expected outcome?"

## Superpowers Integration

1. Superpowers SessionStart hook → skill checking → VCO activation
2. VCO classifies and routes the task
3. VCO respects Superpowers HARD-GATEs: L/XL planning MUST brainstorm before implementation

## 1. Quick Probe + User Decision

### Step 1: Quick Probe (lightweight, no code writing)

最多 2 次 Glob/Grep 调用，不读取文件内容，不写代码。

Gather objective signals before classification:

```
1. Parse task description:
   - Design signals: "design", "architect", "refactor", "migrate", "redesign",
     "new system", "设计", "架构", "重构", "迁移", "重新设计", "新系统" → needs_design = true
   - Parallel signals: "frontend + backend", "parallel", "multi-agent",
     "前后端", "并行", "多智能体",
     multiple independent modules → parallelizable = true
   - Dialectic signals: "辩证", "dialectic", "多视角", "think-tank",
     "对比方案", "权衡" → needs_dialectic = true

2. If task mentions code changes, quick Glob/Grep:
   - Count estimated affected files
   - Check if changes span multiple modules/directories

3. Output: { affected_files, needs_design, parallelizable, key_signals }

4. 探测失败处理：Glob/Grep 调用失败或返回空结果时，
   跳过自动分类，进入 Step 2 的 AskUserQuestion 流程。
```

### Step 2: Recommend + Confirm

**Low-friction rule**: If probe signals are unambiguous (single module, no design keywords, ≤3 files), skip the question and proceed with M grade directly. 在 ANALYZE 开头以括号注释形式简述分类依据（如 `[M级: 3文件, 单模块, 无设计需求]`），不作为独立输出段落。

Otherwise, present probe results and recommended grade via AskUserQuestion:

```
探测结果：预计影响 {N} 文件，检测到 {signals}。
推荐：{grade} 级 — {reason}

选项：
1. {推荐级别} (Recommended) — {执行模式简述}
2. {备选级别} — {执行模式简述}
3. 跳过 VCO — 直接开始，不走框架流程
```

### Grade Definitions

| Grade | When Appropriate | Key Signal | Execution Mode |
|-------|-----------------|------------|----------------|
| M | 实现路径清晰，无需设计决策 | ≤5 files + 无 design 关键词 + 单模块 | Single agent: analyze + execute + review |
| L | 需要设计决策或跨模块协调 | design 关键词 OR >5 files OR 多模块依赖 | Design first → plan → subagent → two-stage review |
| XL | 可并行的独立工作流 | 用户请求 multi-agent OR 结构上可并行 | TeamCreate team coordination |

多个信号冲突时，以最高 grade 的信号为准。When in doubt between L and XL, default to L. XL requires explicit user signal or structural necessity.

## 2. Tool Selection (Single Path per Grade×Type)

| Task Type | M Grade | L Grade | XL Grade |
|-----------|---------|---------|----------|
| Planning | sc:design | brainstorming + writing-plans | dialectic-design† / TeamCreate team |
| Coding | tdd-guide + code-reviewer | subagent-driven-dev | TeamCreate team |
| Review | code-reviewer + security-reviewer | two-stage review (spec + quality) | TeamCreate multi-reviewer |
| Debug | systematic-debugging | systematic-debugging + parallel investigation | TeamCreate debug team |
| Research | sc:research or deep-research | deep-research | TeamCreate research team |

Specialized agents available at ANY grade (exempt from agent boundary rule):
- build-error-resolver: build-specific errors
- security-reviewer: security audits
- dialectic-design: multi-perspective design analysis (see team.md Dialectic Mode)

Excluded tools (do NOT use for VCO-routed tasks):
- sc:implement — use VCO coding flow (tdd-guide / subagent-driven-dev) instead

## 3. Execution Flows

### M Grade: 4 Steps

```
Overview: ANALYZE → EXECUTE → REVIEW → LEARN（各步骤工具见下方）

1. ANALYZE: think-harder (4-phase structured analysis)
   - Skip if probe shows straightforward task (≤2 files, clear intent)
   - Compound task? Use planner agent to decompose
2. EXECUTE: Per type from tool selection matrix:
   - Scope check: 如果执行中需要修改 probe 未识别的模块/目录，或实际修改文件数明显超出预估，暂停并告知用户 — 建议以 L 级重新启动。
   - Coding: tdd-guide (RED → GREEN → REFACTOR)
   - Debug: systematic-debugging (4-phase root cause)
   - Planning: sc:design
   - Research: sc:research or deep-research
   - Review: code-reviewer
3. REVIEW: Auto-trigger code-reviewer for any code changes
   If security-relevant: also invoke security-reviewer
4. LEARN: continuous-learning-v2 (instinct extraction)

Behavioral Tone: see protocols/do.md Behavioral Tone section (Conclusion-First, Exploration Budget, No Self-Commentary).
```

### L Grade: Read Protocol → Execute

Read the relevant protocol from `protocols/` before executing:
- Planning/Design/Research → protocols/think.md
- Coding/Debugging → protocols/do.md
- Review/Quality → protocols/review.md

L grade always follows: design → plan → user approval → subagent execution → two-stage review.

### XL Grade: Read protocols/team.md

Full TeamCreate orchestration. See protocols/team.md for:
- Hybrid architecture (TeamCreate + ruflo)
- Team templates (references/team-templates.md)
- Staged confirmation points
- Agent lifecycle management

## 4. Memory Rules (Inline)

1. **TodoWrite** = default state storage (always available, zero dependency)
2. **ruflo memory** = optional enhancement — vector search for intermediate results (when MCP available)
3. **Serena memory** = project knowledge persistence — architecture decisions, conventions (when MCP available)
4. **Everything-CC instincts** = behavioral patterns — auto-run, no manual action needed

Key principle: TodoWrite is the DEFAULT. ruflo/Serena are ENHANCEMENTS. System runs fully on TodoWrite + conversation context even if all MCP servers are down.

## 5. Core Quality Gates (Inline)

- **P5**: Evidence-Based Communication — NEVER say "should work", "probably fine". ALWAYS use [Command] [Output] [Claim] format
- **V2**: Completion Gate — IDENTIFY what to verify → RUN verification → READ output → VERIFY correctness → MARK COMPLETE
- **V3**: Quality Pipeline (code tasks) — Build → Types → Lint → Tests → Security → Diff → [READY/NOT READY]

Full always-on patterns (P5, V2, V7) and task-type-specific patterns: see protocols/do.md core tier.
Enhanced tier (XL): see protocols/team.md.

## 6. Conflict Rules (Summary)

3 rules. Full specification: references/conflict-rules.md

**Rule 1 — Agent Boundary**: M=single-agent tools (no subagent spawning; individual skill commands permitted), L=Superpowers subagent, XL=TeamCreate. One system per task.
**Rule 2 — Memory Division**: TodoWrite=state, ruflo=vectors, Serena=project, instincts=behavior.
**Rule 3 — Command Priority**: User explicit command > VCO routing > plugin defaults.

## 7. Tool Detection (Lazy)

Detect availability AFTER routing selects a tool, BEFORE invoking:
- MCP connection error → tool unavailable, use fallback
- Skill not found → plugin missing, use fallback
- TeamCreate + TodoWrite = always available (native tools)
- See references/fallback-chains.md for complete fallback paths

## Protocols (on-demand loading)

| Protocol | File | When |
|----------|------|------|
| vibe-think | protocols/think.md | Planning, design, research (L grade) |
| vibe-do | protocols/do.md | Coding, debugging (L grade) |
| vibe-review | protocols/review.md | Code review, security audit (M/L/XL) |
| vibe-team | protocols/team.md | XL multi-agent coordination |
| vibe-retro | protocols/retro.md | Workflow review and improvement |

## References

| Document | Purpose |
|----------|---------|
| conflict-rules.md | 3 conflict avoidance rules |
| fallback-chains.md | Error recovery (M/L=2-level, XL=3-level) |
| tool-registry.md | Tool capabilities + verification status |
| team-templates.md | 6 predefined team compositions |
| extending-vco.md | Guide for adding/updating tools |
| changelog.md | Version history |
| index.md | Navigation index |

## Examples

### Example 1: New Feature (M Grade)
- Input: "Add form validation to the signup page"
- Probe: ~3 files, no design keywords → M (auto, skip question)
- Flow: think-harder → tdd-guide (RED→GREEN→REFACTOR) → code-reviewer → instinct extraction

### Example 2: Architecture Design (L Grade)
- Input: "Design a new user authentication system"
- Probe: design keyword detected, >5 files → L recommended → user confirms
- Flow: protocols/think.md → brainstorming → sc:design → writing-plans → user approval → subagent-driven-dev

### Example 3: Large-Scale Refactoring (XL Grade)
- Input: "Refactor the entire data layer"
- Probe: cross-module, parallelizable → XL recommended → user confirms
- Flow: protocols/team.md → TeamCreate → spawn agents → coordinate → shutdown

## Maintenance

- Version: 2.0.6
- Updated: 2026-02-22
- Sources: Source code analysis of 6 plugins (2026-02-18)
- Changelog: references/changelog.md
- Known limits:
  - Hook execution order between plugins not controllable by VCO
  - Conflict avoidance is behavioral, not technical enforcement
  - Tool availability depends on plugin/MCP state
  - Quick probe accuracy depends on task description quality
  - Quality injection patterns (P1-P6, V1-V7) 通过指令执行，非技术强制；在长对话或高复杂度任务中遵守率可能下降
