---
name: vibe
description: Vibe Code Orchestrator (VCO) routes development tasks by grade and coordinates tool workflows for implementation, debugging, review, and planning.
---

# VCO v2.3 — Vibe Code Orchestrator

Unified entry point: classifies tasks via quick probe + user decision, selects optimal tools, coordinates 6 integrated plugins + Codex native runtime, and uses Codex native agent-team orchestration for XL by default.

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
     "对比方案", "权衡" → dialectic_candidate = true（仅候选信号，不自动触发辩证智囊团）

2. If task mentions code changes, quick Glob/Grep:
   - Count estimated affected files
   - Check if changes span multiple modules/directories

3. Output: { affected_files, needs_design, parallelizable, key_signals }

4. 探测失败处理：Glob/Grep 调用失败或返回空结果时，
   跳过自动分类，进入 Step 2 的 user_confirm 决策流程。
```

### Step 2: Recommend + Confirm

**Low-friction rule**: If probe signals are unambiguous (single module, no design keywords, ≤3 files), skip the question and proceed with M grade directly. 在 ANALYZE 开头以括号注释形式简述分类依据（如 `[M级: 3文件, 单模块, 无设计需求]`），不作为独立输出段落。

Otherwise, present probe results and recommended grade via the runtime-neutral user_confirm interface:

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
| XL | 可并行的独立工作流 | 用户请求 multi-agent OR 结构上可并行 | Codex native team (`spawn_agent`/`send_input`/`wait`/`close_agent`) + ruflo 协作 |

多个信号冲突时，以最高 grade 的信号为准。When in doubt between L and XL, default to L. XL requires explicit user signal or structural necessity.

## 2. Tool Selection (Single Path per Grade×Type)

| Task Type | M Grade | L Grade | XL Grade |
|-----------|---------|---------|----------|
| Planning | sc:design | brainstorming + writing-plans | dialectic-design† / Codex native team |
| Coding | tdd-guide + code-reviewer | subagent-driven-dev | Codex native team |
| Review | code-reviewer + security-reviewer | two-stage review (spec + quality) | Codex native multi-reviewer |
| Debug | systematic-debugging | systematic-debugging + parallel investigation | Codex native debug team |
| Research | sc:research or deep-research | deep-research | Codex native research team |

### Pack Router Overlay (v2.1)

After grade and task-type are decided, VCO applies a pack overlay:

1. Load pack definitions from `config/pack-manifest.json`
2. Score candidate packs using `config/router-thresholds.json`
3. Select skill candidates from the winning pack
4. Resolve legacy names via `config/skill-alias-map.json`
5. If confidence is below threshold, fallback to the legacy Grade×Type matrix above

Pack routing MUST respect grade/task boundaries and Rule 3 command priority.

#### `confirm_required` → White-box Skill Choice

When the router returns `route_mode=confirm_required`, do **NOT** proceed with a silent/opaque auto-route.
Instead, provide a white-box choice so the user can explicitly select the best-fit skill.

Contract:

- `scripts/router/resolve-pack-route.ps1` now emits `confirm_ui` when `route_mode=confirm_required`.
- `confirm_ui.rendered_text` is a ready-to-show menu containing the top relevant skills (name + description).
- User may respond with either:
  - an option number (e.g. `1`), or
  - an explicit skill command (e.g. `$tdd-guide`, `$systematic-debugging`).

Execution rule:

1. Show `confirm_ui.rendered_text` to the user.
2. If the user selects a skill, treat it as an explicit command (Rule 3), and/or re-run the router with `-RequestedSkill <skill>` to lock in the selection.
3. Proceed with the selected skill’s normal workflow (its `SKILL.md`), including quality gates.

Config:

- Policy: `config/confirm-ui-policy.json` (top-k options, descriptions, unattended behavior).

#### Unattended Mode (Skip Confirm)

If the user explicitly requests unattended execution (e.g. “进入无人值守模式”), the router may override `confirm_required` to `pack_overlay` so execution can continue without additional questions.

Supported controls:

- One-shot: call router with `-Unattended`.
- Sticky (default TTL): user prompt contains “进入无人值守模式” / “退出无人值守”；state is stored at `outputs/runtime/confirm-ui-state.json`.

In unattended mode:

- Do not present the white-box menu.
- Still emit evidence in the route output (`unattended_decision`, `unattended_override_applied`, and `route_mode_before_unattended_override`) for observability.

When `config/prompt-overlay.json` is enabled, router emits `prompt_overlay_advice` and may elevate ambiguous prompt-vs-doc requests to `confirm_required` without replacing pack selection.
When `config/data-scale-overlay.json` is enabled, router emits `data_scale_advice` and can adapt spreadsheet skill selection by real file signals (size/rows/format) in a mode-gated, post-route way.
When `config/quality-debt-overlay.json` is enabled, router emits `quality_debt_advice` to expose quality-debt risk and optional analyzer hints in a post-route, advice-first way.
When `config/framework-interop-overlay.json` is enabled, router emits `framework_interop_advice` to expose Ivy-style cross-framework migration guidance in a post-route, advice-first way.
When `config/ml-lifecycle-overlay.json` is enabled, router emits `ml_lifecycle_advice` to expose Made-With-ML lifecycle readiness guidance in a post-route, advice-first way.
When `config/python-clean-code-overlay.json` is enabled, router emits `python_clean_code_advice` to expose Python clean-code guidance with automatic `.py` signal detection in a post-route, advice-first way.
When `config/system-design-overlay.json` is enabled, router emits `system_design_advice` to expose system-design-primer architecture coverage guidance in a post-route, advice-first way.
When `config/cuda-kernel-overlay.json` is enabled, router emits `cuda_kernel_advice` to expose LeetCUDA-inspired CUDA kernel optimization coverage guidance in a post-route, advice-first way.
When `config/deep-discovery-policy.json` is enabled, router runs a prepack Deep Discovery chain (`trigger`/`interview`/`contract`/`filter`), emits `deep_discovery_advice` + `intent_contract`, and may apply capability-based candidate filtering only in mode-gated paths (default shadow remains non-mutating).
When `config/observability-policy.json` is enabled, router writes privacy-safe route telemetry events (`outputs/telemetry/*.jsonl`) for deterministic observability and offline adaptive suggestions; route assignment remains unchanged.
When `config/dialectic-team-policy.json` is enabled, dialectic think-tank activation is gated by explicit request only (`explicit_only`) and blocks implicit team activation.
When `config/daily-dialectic-guard.json` is enabled, router emits `daily_dialectic_advice` as always-on thesis/antithesis/synthesis guardrails in post-route advisory mode.

Specialized agents available at ANY grade (exempt from agent boundary rule):
- build-error-resolver: build-specific errors (compat alias: local `error-resolver`)
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
4. LEARN: continuous-learning-v2 + Context Retro Advisor
   - Trigger Context Retro Advisor when:
     - user explicitly asks for retro/postmortem/复盘/复查,
     - repeated retries or fallback events are observed,
     - context budget pressure appears (large tool outputs, compaction signals),
     - route instability is detected in similar prompts.
   - Retro analysis is guided by Agent-Skills-for-Context-Engineering as an expert knowledge base (advisory mode).
   - Retro output contract uses CER format:
     Pattern → Evidence → Root Cause → Intervention → Guardrail → Confidence.
   - Advisory boundary: Context Retro Advisor does NOT mutate routing/config automatically.
     Any config/rule change still requires explicit user approval.

Behavioral Tone: see protocols/do.md Behavioral Tone section (Conclusion-First, Exploration Budget, No Self-Commentary).
```

### L Grade: Read Protocol → Execute

Read the relevant protocol from `protocols/` before executing:
- Planning/Design/Research → protocols/think.md
- Coding/Debugging → protocols/do.md
- Review/Quality → protocols/review.md

L grade always follows: design → plan → user approval → subagent execution → two-stage review.
When `config/gsd-overlay.json` is enabled and task is planning, apply think.md GSD-Lite preflight hook (post-route only).

### XL Grade: Read protocols/team.md

Full Codex native team orchestration + ruflo collaboration. See protocols/team.md for:
- Primary architecture (`spawn_agent` / `send_input` / `wait` / `close_agent`) + ruflo workflow/memory
- Team templates (references/team-templates.md)
- Staged confirmation points
- Degraded path when ruflo is unavailable (native orchestration only)
- Optional GSD-Lite wave contract hook for planning/coding dependency waves (`config/gsd-overlay.json`)

## 4. Memory Rules (Inline)

1. **state_store (runtime-neutral)** = session state only (default, always available)
2. **Serena memory** = explicit project decisions only (architecture decisions, conventions)
3. **ruflo memory** = short-term session vector cache only (optional MCP enhancement)
4. **Cognee memory** = long-term graph memory and relationship retrieval only (optional)
5. **episodic-memory** = disabled in VCO governance (do not route/use in normal flow)
6. **Everything-CC instincts** = behavioral patterns (out-of-band, auto-run)

Key principle: state_store is the DEFAULT. Serena/ruflo/Cognee are scoped enhancements with non-overlapping roles. System runs fully on state_store + conversation context even if all MCP servers are down.

## 5. Core Quality Gates (Inline)

- **P5**: Evidence-Based Communication — NEVER say "should work", "probably fine". ALWAYS use [Command] [Output] [Claim] format
- **V2**: Completion Gate — IDENTIFY what to verify → RUN verification → READ output → VERIFY correctness → MARK COMPLETE
- **V3**: Quality Pipeline (code tasks) — Build → Types → Lint → Tests → Security → Diff → [READY/NOT READY]

Full always-on patterns (P5, V2, V7) and task-type-specific patterns: see protocols/do.md core tier.
Enhanced tier (XL): see protocols/team.md.

## 6. Conflict Rules (Summary)

3 rules. Full specification: references/conflict-rules.md

**Rule 1 — Agent Boundary**: M=single-agent tools (no subagent spawning; individual skill commands permitted), L=Superpowers subagent, XL=Codex native team (`spawn_agent` family) + optional ruflo collaboration. One system per task.
**Rule 2 — Memory Division**: state_store=session, Serena=explicit decisions, ruflo=short-term vectors, Cognee=long-term graph, episodic-memory=disabled, instincts=behavior.
**Rule 3 — Command Priority**: User explicit command > VCO routing > plugin defaults.

## 7. Tool Detection (Lazy)

Detect availability AFTER routing selects a tool, BEFORE invoking:
- MCP connection error → tool unavailable, use fallback
- Skill not found → plugin missing, use fallback
- XL runtime probe order:
  - Primary: native team tools (`spawn_agent`, `send_input`, `wait`, `close_agent`)
  - Enhancement: ruflo workflow/memory tools when MCP is available
  - If native APIs unavailable: follow XL Level 3 fallback (sequential L-grade)
- build-error-resolver resolution:
  - Try `everything-claude-code:build-error-resolver`
  - If unavailable, use local `build-error-resolver` alias skill (delegates to `error-resolver`)
- Pack router inputs:
  - `config/pack-manifest.json`
  - `config/router-thresholds.json`
  - `config/skill-alias-map.json`
- See references/fallback-chains.md for complete fallback paths

## Protocols (on-demand loading)

| Protocol | File | When |
|----------|------|------|
| vibe-think | protocols/think.md | Planning, design, research (L grade) |
| vibe-do | protocols/do.md | Coding, debugging (L grade) |
| vibe-review | protocols/review.md | Code review, security audit (M/L/XL) |
| vibe-team | protocols/team.md | XL multi-agent coordination |
| vibe-retro | protocols/retro.md | Workflow review, context diagnosis, and learning optimization |

## References

| Document | Purpose |
|----------|---------|
| conflict-rules.md | 3 conflict avoidance rules |
| fallback-chains.md | Error recovery (M/L=2-level, XL=3-level) |
| tool-registry.md | Tool capabilities + verification status |
| team-templates.md | 7 predefined team compositions |
| extending-vco.md | Guide for adding/updating tools |
| docs/context-retro-advisor-design.md | Context Retro Advisor design and rollout guide |
| docs/gsd-vco-overlay-integration.md | GSD-Lite overlay integration (post-route planning hook) |
| docs/memory-governance-integration.md | Memory governance integration (role boundaries + disabled episodic-memory) |
| docs/prompt-overlay-integration.md | prompts.chat prompt-asset overlay integration (post-route ambiguity guard) |
| docs/data-scale-overlay-integration.md | Data-scale overlay integration (real file probe + spreadsheet/xlsx/xan adaptive selection) |
| docs/quality-debt-overlay-integration.md | Quality-debt overlay integration (fuck-u-code inspired post-route advisory) |
| docs/framework-interop-overlay-integration.md | Framework-interop overlay integration (ivy-inspired cross-framework advisory) |
| docs/ml-lifecycle-overlay-integration.md | ML lifecycle overlay integration (Made-With-ML inspired stage/evidence advisory) |
| docs/python-clean-code-overlay-integration.md | Python clean-code overlay integration (clean-code-python inspired post-route advisory) |
| docs/system-design-overlay-integration.md | System-design overlay integration (system-design-primer inspired architecture coverage advisory) |
| docs/cuda-kernel-overlay-integration.md | CUDA kernel overlay integration (LeetCUDA inspired kernel optimization advisory) |
| docs/observability-consistency-governance.md | Observability + consistency governance (lean telemetry + manual rollback confirmation) |
| docs/blackbox-probe-and-enhancement-playbook.md | Blackbox probing + semantic enhancement + threshold tuning unified engineering playbook |
| docs/skills-consolidation-roadmap.md | Pack consolidation phases and gates |
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
- Flow: protocols/team.md → spawn_agent team → send_input coordination + ruflo memory/workflow → wait aggregation → close_agent cleanup

## Maintenance

- Version: 2.3.24
- Updated: 2026-02-27
- Sources: Source code analysis of 6 plugins (2026-02-18) + Agent-Skills-for-Context-Engineering (2026-02-24)
- Changelog: references/changelog.md
- Known limits:
  - Hook execution order between plugins not controllable by VCO
  - Conflict avoidance is behavioral, not technical enforcement
  - Tool availability depends on plugin/MCP state
  - Quick probe accuracy depends on task description quality
  - Quality injection patterns (P1-P6, V1-V7) 通过指令执行，非技术强制；在长对话或高复杂度任务中遵守率可能下降
