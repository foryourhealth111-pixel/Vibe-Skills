# VCO Team Templates

Predefined team compositions for common XL-grade scenarios.
These are REFERENCE templates -- adapt roles and count based on actual task needs.

## Template 1: feature-team

For implementing a new feature end-to-end.

| Role | subagent_type | Responsibility |
|------|--------------|----------------|
| Lead | general-purpose | Coordination, integration, final review |
| Planner | Plan | Architecture design, task decomposition |
| Implementer-1 | general-purpose | Frontend / Module A implementation |
| Implementer-2 | general-purpose | Backend / Module B implementation |
| Reviewer | everything-claude-code:code-reviewer | Continuous code review |

Workflow: Planner designs -> Lead approves -> Implementers build in parallel -> Reviewer checks

## Template 2: debug-team

For investigating and fixing complex cross-module bugs.

| Role | subagent_type | Responsibility |
|------|--------------|----------------|
| Lead | general-purpose | Coordination, hypothesis management |
| Investigator-1 | Explore | Module A root cause analysis |
| Investigator-2 | Explore | Module B root cause analysis |
| Fixer | general-purpose | Implement fixes based on findings |

Workflow: Investigators explore in parallel -> Lead synthesizes -> Fixer implements -> Lead verifies

## Template 3: research-team

For deep research requiring multiple perspectives.

| Role | subagent_type | Responsibility |
|------|--------------|----------------|
| Lead | general-purpose | Coordination, synthesis |
| Researcher-1 | Explore | Codebase analysis |
| Researcher-2 | Explore | Documentation / external research |
| Analyst | Plan | Synthesize findings into recommendations |

Workflow: Researchers gather in parallel -> Analyst synthesizes -> Lead presents to user

## Template 4: review-team

For comprehensive multi-perspective code review.

| Role | subagent_type | Responsibility |
|------|--------------|----------------|
| Lead | general-purpose | Coordination, final report |
| Security | everything-claude-code:security-reviewer | Security audit |
| Quality | everything-claude-code:code-reviewer | Code quality review |
| Architect | Plan | Architecture compliance check |

Workflow: All reviewers run in parallel -> Lead aggregates findings by severity

## Template 5: full-stack-team

For large-scale refactoring or migration projects.

| Role | subagent_type | Responsibility |
|------|--------------|----------------|
| Lead | general-purpose | Coordination, conflict resolution |
| Planner | Plan | Migration plan, dependency analysis |
| Frontend | general-purpose | Frontend changes |
| Backend | general-purpose | Backend changes |
| Database | general-purpose | Schema / query changes |
| Tester | general-purpose | Integration testing |

Workflow: Planner designs -> Lead approves phases -> Parallel implementation -> Tester validates -> Lead integrates

## Usage Notes

- Templates are starting points. Remove unnecessary roles for simpler tasks.
- Always have a Lead role for coordination.
- Prefer fewer agents when possible -- each agent adds coordination overhead.
- Use `Explore` (read-only) for investigation roles to prevent accidental edits.
- Use `general-purpose` for roles that need to write code.
- With ruflo available: use workflow_create to formalize the workflow steps.
- Without ruflo: use TaskCreate with addBlockedBy to enforce ordering.

## Template 6: dialectic-design

For multi-perspective design analysis via structured dialectical workflow.
Use when: user requests dialectical thinking, or multiple viable approaches need evaluation.

### Team Structure

2 isolated groups × 2 agents. Information flows only within groups.

| Role | subagent_type | Group | Responsibility |
|------|--------------|-------|----------------|
| Thinker-A1 | general-purpose | A | Independent analysis from perspective A |
| Thinker-A2 | general-purpose | A | Independent analysis from perspective A |
| Thinker-B1 | general-purpose | B | Independent analysis from perspective B |
| Thinker-B2 | general-purpose | B | Independent analysis from perspective B |

### Perspective Assignment

Lead selects 1 perspective pair based on question type:

| Question Type | Group A Perspective | Group B Perspective |
|--------------|--------------------|--------------------|
| Architecture | Top-down (user-facing API → internals) | Bottom-up (data storage → API surface) |
| Technology selection | Ecosystem maturity + community | Performance + scalability |
| Refactoring | Minimal change (preserve existing) | Ideal architecture (greenfield) |
| Feature design | User experience first | Technical feasibility first |
| General | Focus on constraints | Focus on possibilities |

If question doesn't fit any type, use "General" row.

### Workflow (per group, 6 phases)

Phase 1 — Propose: Each agent independently proposes a solution
Phase 2 — Reflect: Each agent critiques own proposal (3 weaknesses with failure scenarios)
Phase 3 — Synthesize: Each agent improves proposal based on self-critique → SendMessage to partner
Phase 4 — Compare: After receiving partner's synthesis, analyze differences
Phase 5 — Reflect on comparison: Why did we diverge? What did partner see that I missed?
Phase 6 — Final synthesis: Produce final proposal incorporating partner's insights → SendMessage to Lead

### Communication Rules

- Within group: SendMessage between partners (A1↔A2, B1↔B2)
- Cross group: NONE (groups are isolated)
- To Lead: Only Phase 6 final synthesis
- Max rounds: 1 (no multi-round debate)

Workflow: Lead prepares context + perspectives → 4 agents run 6-phase workflow in parallel → Lead collects 4 syntheses → extract consensus + divergence → present to user

## Template 7: local-vco-dialectic-review (local-vco-roles adapter)

For users who installed `local-vco-roles` and want stable role prompts aligned with VCO dialectic flow.

### Role Mapping

| Role | subagent_type | Prompt Source |
|---|---|---|
| team-lead | general-purpose | `~/.codex/skills/local-vco-roles/references/role-prompts/team-lead.md` |
| bug-analyst | general-purpose | `~/.codex/skills/local-vco-roles/references/role-prompts/bug-analyst.md` |
| arch-critic | general-purpose | `~/.codex/skills/local-vco-roles/references/role-prompts/arch-critic.md` |
| integration-analyst | general-purpose | `~/.codex/skills/local-vco-roles/references/role-prompts/integration-analyst.md` |
| usability-analyst | general-purpose | `~/.codex/skills/local-vco-roles/references/role-prompts/usability-analyst.md` |

### Compatibility Constraints

1. Respect VCO grade boundary:
- M/L: no forced TeamCreate orchestration.
- XL: full role orchestration allowed.
2. Maintain severity order: `CRITICAL > HIGH > MEDIUM > LOW`.
3. Keep decision output format: `keep / simplify / remove`.
4. User explicit command overrides this template.
