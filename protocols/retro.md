# vibe-retro Protocol

> **What this protocol does -- plain language overview**
>
> This is the retrospective protocol. It defines how VibeSkills reviews completed
> work, identifies recurring problems, and proposes improvements to your workflow.
>
> You do not need to read this to use VibeSkills. It activates after `phase_cleanup`
> when you want to reflect on what happened and improve for next time.
>
> **Key terms used below:**
> - **CER (Context Evidence Report)**: A structured output format for what went wrong and how to prevent it. Structure: Pattern -> Evidence -> Root Cause -> Intervention -> Guardrail -> Confidence.
> - **CF-1 to CF-6 (Context Failure classes)**:
>   CF-1 = attention dilution (AI lost track of early context in a long session);
>   CF-2 = context poisoning (stale or contradictory state);
>   CF-3 = observation bloat (tool outputs dominating useful context tokens);
>   CF-4 = memory mismatch (wrong content retrieved);
>   CF-5 = tool contract ambiguity (mismatched tool input/output expectations);
>   CF-6 = evaluation blind spot (no rubric or weak verification).
> - **Proxy-goal drift**: When the system optimizes a visible metric (the proxy) instead of the actual goal. Example: passing all tests by deleting the failing ones.
> - **report_only**: A warning recorded for review purposes that does not automatically block any action on its own.
> - **Context Retro Advisor**: An advisory sub-system that classifies context failures and recommends interventions. It can recommend but cannot change configuration without explicit user approval.


Protocol for structured retrospective -- collaborative analysis of recent projects,
workflow optimization, error pattern detection, context diagnosis, and future improvement planning.

## Scope
Activated when the user wants to:
- Review and reflect on recent project work
- Identify workflow optimization opportunities
- Detect recurring error patterns and design preventive hooks
- Diagnose context quality failures in long-running tasks
- Discover reusable patterns for future projects
- Decide whether to create new skills, agents, MCPs, or hooks
- Conduct a collaborative improvement discussion

## Governed Runtime Position

This protocol is a retrospective and learning surface, not the primary user entrypoint.
It can be invoked after governed execution completes, or used as part of a cleanup and learning pass after runtime stage 6 `phase_cleanup`.

The fixed runtime path remains:

1. `skeleton_check`
2. `deep_interview`
3. `requirement_doc`
4. `xl_plan`
5. `plan_execute`
6. `phase_cleanup`

`retro.md` never replaces those stages.
It consumes their receipts and artifacts to improve future runs.

## Anti-Proxy-Goal-Drift Retro Lens

Retro treats proxy-goal drift as a first-class learning failure mode.
The point is not to punish work after the fact.
The point is to preserve honest completion language, prevent objective/proxy substitution from becoming normalized, and keep specialization distinct from false generalization.

In official `report_only` mode:
- record warning codes, completion-language corrections, and specialization findings,
- do not silently convert those findings into a new hard gate,
- if another approved blocking policy was violated, cite that policy directly.

Core retro questions:
1. What objective did the work claim to serve?
2. Which proxy signals were optimized instead?
3. Did validation material stay outside implementation truth?
4. Was the repair made at the intended abstraction layer?
5. Was the final completion state honest for the actual scope and evidence?
6. Was a bounded specialization preserved honestly, or was it flattened into a generalized claim?

## Context Retro Advisor (Agent-Skills Guided)

VCO uses Agent-Skills-for-Context-Engineering as an expert advisor in retro mode.
This advisor is guidance-only and never auto-mutates runtime configuration.

### Knowledge Sources (preferred)
- context-fundamentals
- context-degradation
- context-compression
- context-optimization
- multi-agent-patterns
- memory-systems
- tool-design
- filesystem-context
- evaluation
- advanced-evaluation
- project-development

### Advisory Boundaries
- The advisor can classify failure modes and recommend interventions.
- The advisor cannot directly change router thresholds, pack manifest, or conflict rules.
- Any config or policy change still requires explicit user approval in Phase 4.

### Fallback if Skills Are Missing
- Fall back to built-in VCO heuristics in this protocol.
- Continue with evidence-backed diagnosis using available session/tool data.

## 5-Phase Architecture

Phase 1: GATHER -> Phase 2: ANALYZE -> Phase 3: DISCUSS -> Phase 4: DECIDE -> Phase 5: ACT

Each phase uses existing tools from the integrated plugins.

---

## Phase 1: GATHER (Data Collection)

### 1.1 Conversation History Retrieval
Tool: Cognee graph retrieval (optional) + session file scan
- Query long-term relationship graph for target project/topic context (if Cognee available)
- Read recent session files for short-horizon execution trace
- Fallback: session files only (do not use episodic-memory in VCO governance mode)

### 1.2 Session Activity Review
Tool: Read ~/.claude/sessions/ files
- Read recent session files
- Extract: tasks performed, files modified, tools used

### 1.3 Instinct Status Check
Tool: everything-claude-code:instinct-status
- Show learned instincts grouped by domain
- Check confidence scores and recent updates
- Fallback: Skip if instinct system not active

### 1.4 Project Memory Retrieval
Tool: Serena MCP list_memories + read_memory
- List project-related memories
- Read key decisions, architecture notes
- Fallback: Skip if Serena not available

### 1.5 Error Log Collection
Tool: git log + session/ruflo trace synthesis
- git log --oneline -20 (recent commits, especially fix/revert)
- Search session traces/ruflo memory for error, fix, bug, revert

### 1.6 Context Signal Collection
Tool: session/tool trace synthesis
- Count retries, fallback frequency, and compaction events
- Measure large-output tool calls and repeated low-value observations
- Detect route instability (same intent, different route outcomes)
- Collect review language, closure wording, and any report-only anti-drift warnings emitted during execution

#### Default Trigger Thresholds

Use these defaults unless project policy defines stricter thresholds:

| Signal | Metric | Default Threshold | Trigger Meaning |
|--------|--------|-------------------|-----------------|
| Retry spike | `retry_count_10m` | `>= 3` | Execution stuck in retry loop |
| Fallback frequency | `fallback_rate` | `>= 0.20` | Primary path reliability degraded |
| Context pressure | `context_pressure` | `>= 0.75` | Context budget at risk |
| Route instability (pack) | `route_stability_pack` | `< 0.80` | Same intent routes to different packs |
| Route instability (skill) | `route_stability_skill` | `< 0.70` | Skill selection jitter inside pack |
| Route ambiguity | `top1_top2_gap` | `< 0.03` | Weak route separability |

Where:
- `fallback_rate = fallback_count / total_attempts`
- `context_pressure = observation_chars_total / context_budget_chars`
- `route_stability_pack = most_common_pack / total_probe_runs`
- `route_stability_skill = most_common_skill / total_probe_runs`

Present structured data collection report before proceeding.

---

## Phase 2: ANALYZE (Structured Analysis)

### 2.1 Session Reflection
Tool: claude-code-settings:reflection-harder (or everything-claude-code:deep-reflector agent)
Fallback: claude-code-settings:think-harder
- Analyze recent sessions for problems solved, patterns established

### 2.2 Problem Pattern Detection
Tool: hookify:conversation-analyzer agent
Fallback: Manual scan of session traces and commit history
- Scan for user frustration signals, repeated errors, tool misuse
- Severity categorization (high/medium/low)

### 2.3 Workflow Frequency Analysis
Tool: Analyze session files + ruflo short-term memory
- Most frequently used tool combinations
- Repeated multi-step workflows (automation candidates)

### 2.4 Cross-Session Trend Analysis
Tool: claude-code-settings:think-ultra (7-phase analysis), or think-harder (4-phase) for M grade
Fallback: Direct Claude reasoning synthesis
- Synthesize data from 2.1-2.3
- Error trends, activity domains, time sinks

### 2.5 Context Failure Typing (Context Retro Advisor)
Classify failures into one or more classes:
- CF-1 Attention dilution / lost-in-middle
- CF-2 Context poisoning (stale or contradictory state)
- CF-3 Observation bloat (tool outputs dominate useful tokens)
- CF-4 Memory mismatch (retrieval irrelevant/missing)
- CF-5 Tool contract ambiguity (tool schema/intent mismatch)
- CF-6 Evaluation blind spot (no rubric, weak verification)

### 2.6 Intervention Design
Map each failure class to interventions:
- Compaction strategy update (what to compress, when)
- Observation masking rules (what to retain vs reference)
- Context partitioning for XL tasks (agent boundary refinement)
- Memory indexing/persistence policy adjustments
- Evaluation rubric and verification gate hardening

### 2.7 Anti-Drift Classification
For governed retros, also classify whether the run showed:
- objective / proxy substitution,
- validation-material contamination,
- abstraction-layer mismatch,
- completion-state overclaim,
- specialization erasure.

Each classification must end in one of these dispositions:
- `aligned`
- `report_only_warning`
- `completion_language_corrected`
- `specialization_confirmed`
- `escalate_via_existing_policy`

---

## Phase 3: DISCUSS (Interactive Discussion)

### Interaction Style: Pedagogical Advisory

**Proactive Engagement:**
- Actively identify improvement opportunities
- Use guiding questions to surface insights
- For each finding, provide concrete improvement path

**Data-Grounded Suggestions:**
- Every suggestion references specific evidence from Phase 2
- When uncertain, acknowledge uncertainty explicitly

**Discussion Topics:**
- Workflow review: automation candidates, efficiency improvements
- Error prevention: hooks, pre-commit checks
- Context quality: compression policy, masking policy, partitioning strategy
- Tool effectiveness: routing accuracy, fallback frequency
- Future planning: templates, skills, new tools
- Completion honesty: whether the reported end-state matched objective, scope, and proof
- Specialization boundaries: whether bounded wins were preserved honestly rather than generalized by habit

**Respectful Autonomy:**
- User makes all final decisions
- Explicitly ask for confirmation before Phase 4

---

## Phase 4: DECIDE (Decisions)

### Decision Categories

| Category | Action Type | Tool |
|----------|------------|------|
| Recurring workflow | Create skill | superpowers:writing-skills |
| Recurring workflow | Create command | claude-code-settings:command-creator |
| Error prevention | Create hook | hookify:hookify |
| Behavioral pattern | Create/update instinct | continuous-learning-v2 |
| Context quality | Update retro policy/playbook | Edit protocols/retro.md + docs |
| Completion honesty correction | Update review / CER / closure wording | Edit protocols/templates/docs |
| Routing improvement | Update VCO config | Edit SKILL.md / config/*.json |
| Knowledge capture | Persist memory | Serena write_memory + Cognee ingest (optional) |
| Complex automation | Create agent | Manual design + writing-skills |

### User Confirmation Gate
Present all decisions as prioritized list.
User approves, modifies, or rejects each before Phase 5.

---

## Phase 5: ACT (Execute Improvements)

### 5.1 Create Hooks
Tool: hookify:hookify
- Define trigger, matcher, action
- Create .local.md rule file

### 5.2 Create Skills/Commands
Tool: superpowers:writing-skills or claude-code-settings:command-creator
- Define skill name, description, trigger
- Write SKILL.md with proper frontmatter

### 5.3 Create/Update Instincts
Tool: everything-claude-code:continuous-learning-v2
- Create .md in ~/.claude/homunculus/instincts/personal/
- Set confidence score (start at 0.5)

### 5.4 Update VCO Configuration
Tool: Direct file edits to SKILL.md, conflict-rules.md, fallback-chains.md, router config

### 5.5 Persist Knowledge
Tool: Serena write_memory + Cognee ingest (optional) + CLAUDE.md updates if globally applicable
- Serena: persist explicit project decisions only
- Cognee: persist long-term entities/relations for cross-session retrieval

### 5.6 Generate CER Report (Markdown + JSON)
Generate both artifacts from templates:
- `templates/cer-report.md.template`
- `templates/cer-report.json.template`

Store outputs under:
- `outputs/retro/YYYY-MM-DD-<topic>-cer.md`
- `outputs/retro/YYYY-MM-DD-<topic>-cer.json`

### 5.7 Persist CER for Comparison
Store summary via Serena write_memory:
- key: `retro/YYYY-MM-DD/<topic>/cer-summary`
- include: failure classes, key interventions, guardrails, confidence

Optionally keep full JSON in local artifact store for trend analytics.

### 5.8 Update Context Playbook (Optional)
Update docs/design/context-retro-advisor-design.md if policy-level changes are accepted.

### 5.9 Run Retro Regression Checks (Optional but recommended)
Tool: `scripts/verify/vibe-retro-context-regression-matrix.ps1`
- Validate trigger threshold logic with fixed metric cases
- Validate CF-1..CF-6 classification stability with bilingual fixed evidence cases

### 5.10 Compare CER Across Iterations (Optional but recommended)
Tool: `scripts/verify/cer-compare.ps1`
- Compare baseline and current CER JSON reports
- Output machine-readable and human-readable delta summaries
- Track trend fields: pattern delta, fallback_rate delta, stability delta, context_pressure delta

---

## Context Evidence Report (CER) Output Contract

Every Context Retro Advisor analysis MUST output this schema:

1. Pattern: failure class tags (CF-1..CF-6)
2. Evidence: concrete observations (commands, outputs, events)
3. Root Cause: why the pattern occurred
4. Intervention: concrete change proposal
5. Guardrail: validation check preventing recurrence
6. Confidence: high/medium/low with scope limits

No recommendation should be emitted without Evidence.

Every governed CER should also preserve the shared anti-drift vocabulary:
- `governance_mode`
- `anti_proxy_goal_drift_tier`
- `completion_state`
- `primary_objective`
- `non_objective_proxy_signals`
- `validation_material_role`
- `intended_scope`
- `specialization_assessment`
- `generalization_evidence_bundle`
- `report_only_warning_codes`
- `completion_honesty_notes`

`report_only_warning_codes` are governance evidence, not a hidden hard stop.
If a retro recommends blocking action, it must name the separate approved policy or hard gate that justifies the block.

### CER JSON Validation
- Validate generated JSON against `templates/cer-report.schema.json` when available.
- If schema validation fails, mark report status as `invalid` and do not use it for trend comparison.

---

## Tool Composition Map

| Phase | Primary Tool | Source Plugin | Fallback |
|-------|-------------|--------------|----------|
| 1.1 History | Cognee graph retrieval + session files | Cognee + runtime | Read session files |
| 1.2 Activity | Read ~/.claude/sessions/ | Everything-CC | git log |
| 1.3 Instincts | instinct-status | Everything-CC | Skip |
| 1.4 Memory | Serena list/read_memory | Serena MCP | Skip |
| 1.5 Errors | git log + session/ruflo trace search | Git + ruflo | Manual review |
| 1.6 Context signals | session/tool trace synthesis | Runtime-neutral | Manual synthesis |
| 2.1 Reflection | reflection-harder | Claude-code-settings | deep-reflector agent / think-harder |
| 2.2 Problems | conversation-analyzer | Hookify | Manual scan |
| 2.3 Workflows | Session file + ruflo analysis | Everything-CC + ruflo | session-only analysis |
| 2.4 Trends | think-ultra / think-harder | Claude-code-settings | Direct reasoning |
| 2.5 Context typing | Agent-Skills context guidance | Agent-Skills | VCO heuristics |
| 3.x Discussion | brainstorming methodology | Superpowers | Direct dialogue |
| 4.x Decisions | user_confirm interface | Runtime-neutral | Direct dialogue |
| 5.1 Hooks | hookify | Hookify | Manual creation |
| 5.2 Skills | writing-skills | Superpowers | Manual creation |
| 5.3 Instincts | continuous-learning-v2 | Everything-CC | Manual creation |
| 5.4 Config | Direct edit | VCO | Manual edit |
| 5.5 Knowledge | Serena write_memory + Cognee ingest | Serena MCP + Cognee | state_store decision log |
| 5.6 CER output | CER templates | VCO templates | manual structure |
| 5.9 Regression check | vibe-retro-context-regression-matrix.ps1 | VCO verify | manual checklist |
| 5.10 CER compare | cer-compare.ps1 | VCO verify | manual comparison |

---

## Grade Adaptation

| Grade | Scope | Phases Used | Depth |
|-------|-------|-------------|-------|
| M | Single project retro | 1 + 2 + 3 + 4 | Full analysis, selective action |
| L | Multi-project retro | All 5 phases | Full analysis + implementation |
| XL | System-wide retro | All 5 + parallel agents | Deep analysis + major changes |

## Conflict Avoidance
- Phase 2 analysis agents run sequentially to avoid mutual exclusion.
- Exception: XL grade uses Codex native team for parallel analysis.
- hookify conversation-analyzer is an analysis tool -- safe at any grade.
- deep-reflector is a diagnostic agent -- exempt from Rule 1.
- Context Retro Advisor is advisory and can run at any grade.
- Phase 5 actions are sequential: hooks first, then skills, then config.
- Router or threshold changes require explicit user confirmation.
