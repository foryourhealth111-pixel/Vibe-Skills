# VCO Team Templates

Predefined team compositions for common XL-grade scenarios.
These are REFERENCE templates and should be adapted to actual task scope.

## Template 1: feature-team

For implementing a new feature end-to-end.

| Role | Native Agent Type | Responsibility |
|------|-------------------|----------------|
| Lead | `default` | Coordination, integration, final review |
| Planner | `default` | Architecture design, task decomposition |
| Implementer-1 | `worker` | Frontend / Module A implementation |
| Implementer-2 | `worker` | Backend / Module B implementation |
| Reviewer | `default` | Continuous code review (bug/risk-first prompt) |

Workflow: Planner designs -> Lead approves -> Implementers build in parallel -> Reviewer checks.

## Template 2: debug-team

For investigating and fixing complex cross-module bugs.

| Role | Native Agent Type | Responsibility |
|------|-------------------|----------------|
| Lead | `default` | Coordination, hypothesis management |
| Investigator-1 | `explorer` | Module A root cause analysis |
| Investigator-2 | `explorer` | Module B root cause analysis |
| Fixer | `worker` | Implement fixes based on findings |

Workflow: Investigators explore in parallel -> Lead synthesizes -> Fixer implements -> Lead verifies.

## Template 3: research-team

For deep research requiring multiple perspectives.

| Role | Native Agent Type | Responsibility |
|------|-------------------|----------------|
| Lead | `default` | Coordination, synthesis |
| Researcher-1 | `explorer` | Codebase analysis |
| Researcher-2 | `explorer` | Documentation / external research |
| Analyst | `default` | Synthesize findings into recommendations |

Workflow: Researchers gather in parallel -> Analyst synthesizes -> Lead presents to user.

## Template 4: review-team

For comprehensive multi-perspective code review.

| Role | Native Agent Type | Responsibility |
|------|-------------------|----------------|
| Lead | `default` | Coordination, final report |
| Security | `default` | Security audit (OWASP/input/secret focus prompt) |
| Quality | `worker` | Code quality review |
| Architect | `default` | Architecture compliance check |

Workflow: All reviewers run in parallel -> Lead aggregates findings by severity.

## Template 5: full-stack-team

For large-scale refactoring or migration projects.

| Role | Native Agent Type | Responsibility |
|------|-------------------|----------------|
| Lead | `default` | Coordination, conflict resolution |
| Planner | `default` | Migration plan, dependency analysis |
| Frontend | `worker` | Frontend changes |
| Backend | `worker` | Backend changes |
| Database | `worker` | Schema / query changes |
| Tester | `worker` | Integration testing |

Workflow: Planner designs -> Lead approves phases -> Parallel implementation -> Tester validates -> Lead integrates.

## Usage Notes

- Templates are starting points; remove unnecessary roles for simpler tasks.
- Always keep a Lead role for coordination and integration.
- Prefer fewer agents when possible because coordination overhead scales quickly.
- Use `explorer` for read/search-heavy investigation and evidence gathering.
- Use `worker` for implementation ownership and code changes.
- Use `default` for planning, synthesis, and integration responsibilities.
- With ruflo available, persist milestones via `memory_store` and formalize workflows via `workflow_create`/`workflow_execute`.
- Without ruflo, keep the same team and coordinate dependencies via lead-managed `send_input` + milestone `wait`.

## Template Add-on: Dispatch Envelope + Shared Memory Keys

For any template, use a consistent "dispatch envelope" when sending tasks via `send_input`. This makes aggregation and failure handling predictable across teams.

Minimum fields to include in every agent prompt:
- `run_id`: shared identifier for this XL execution.
- `phase`: `plan|investigate|implement|verify`.
- `deadline_minutes` + `retry_budget`: reliability contract.
- `deliverable.sections`: stable output shape for lead aggregation.
- `memory.private_key` + `memory.shared_key`: where notes and rollups live.

For the *subtask correctness* contract (goal/scope/DoD/verification/handoff questions), reuse:
- `protocols/team.md` → **Task Contract (Subtask Interface / DoD)**

Example (copy/paste into prompts):

```yaml
run_id: "{yyyy-mm-dd}#{short}"
phase: "investigate"
deadline_minutes: 15
retry_budget: 1
deliverable:
  format: "markdown"
  sections: ["summary", "evidence", "risks", "next_steps"]
memory:
  private_key: "team/{run_id}/agent/{role}/notes"
  shared_key: "team/{run_id}/shared/agents_memory"
```

## Template 6: dialectic-design

For multi-perspective design analysis via structured dialectical workflow.
Use only when the user explicitly requests dialectic think-tank mode.

### Team Structure

2 isolated groups x 2 agents. Information flows only within groups.

| Role | Native Agent Type | Group | Responsibility |
|------|-------------------|-------|----------------|
| Thinker-A1 | `default` | A | Independent analysis from perspective A |
| Thinker-A2 | `default` | A | Independent analysis from perspective A |
| Thinker-B1 | `default` | B | Independent analysis from perspective B |
| Thinker-B2 | `default` | B | Independent analysis from perspective B |

### Perspective Assignment

Lead selects one perspective pair based on question type:

| Question Type | Group A Perspective | Group B Perspective |
|--------------|--------------------|--------------------|
| Architecture | Top-down (user-facing API -> internals) | Bottom-up (data storage -> API surface) |
| Technology selection | Ecosystem maturity + community | Performance + scalability |
| Refactoring | Minimal change (preserve existing) | Ideal architecture (greenfield) |
| Feature design | User experience first | Technical feasibility first |
| General | Focus on constraints | Focus on possibilities |

If the question does not fit any type, use "General".

### Workflow (per group, 6 phases)

Phase 1 - Propose: Each agent independently proposes a solution.  
Phase 2 - Reflect: Each agent critiques own proposal (3 weaknesses with failure scenarios).  
Phase 3 - Synthesize: Each agent improves proposal based on self-critique -> `send_input` to partner.  
Phase 4 - Compare: After receiving partner synthesis, analyze differences.  
Phase 5 - Reflect on comparison: Why did we diverge? What did partner see that I missed?  
Phase 6 - Final synthesis: Produce final proposal incorporating partner insights -> `send_input` to Lead.

### Communication Rules

- Within group: `send_input` between partners (A1<->A2, B1<->B2).
- Cross group: NONE (groups are isolated).
- To Lead: only Phase 6 final synthesis.
- Max rounds: 1 (no multi-round debate).

Workflow: Lead prepares context + perspectives -> 4 agents run 6-phase workflow in parallel -> Lead collects 4 syntheses -> extract consensus + divergence -> present to user.

## Template 7: local-vco-dialectic-review (local-vco-roles adapter)

For users who installed `local-vco-roles` and want stable role prompts aligned with VCO dialectic flow.

### Role Mapping

| Role | Native Agent Type | Prompt Source |
|---|---|---|
| team-lead | `default` | `~/.codex/skills/local-vco-roles/references/role-prompts/team-lead.md` |
| bug-analyst | `explorer` | `~/.codex/skills/local-vco-roles/references/role-prompts/bug-analyst.md` |
| arch-critic | `default` | `~/.codex/skills/local-vco-roles/references/role-prompts/arch-critic.md` |
| integration-analyst | `worker` | `~/.codex/skills/local-vco-roles/references/role-prompts/integration-analyst.md` |
| usability-analyst | `default` | `~/.codex/skills/local-vco-roles/references/role-prompts/usability-analyst.md` |

### Usage Constraints

1. Respect VCO grade boundary.
   M/L: no forced XL orchestration.
   XL: full role orchestration allowed.
2. Maintain severity order: `CRITICAL > HIGH > MEDIUM > LOW`.
3. Keep decision output format: `keep / simplify / remove`.
4. User explicit command overrides this template.

## Template 8: supervisor-scatter-gather

For Agent-Squad-style "SupervisorAgent" coordination (agent-as-tools) where you need parallel specialist work, then one coherent synthesis.

| Role | Native Agent Type | Responsibility |
|------|-------------------|----------------|
| Lead (Supervisor) | `default` | Single entry point, fan-out/fan-in, final synthesis |
| Specialist-1 | `explorer` | Evidence gathering / codebase reading |
| Specialist-2 | `explorer` | Alternative perspective / risk analysis |
| Specialist-3 | `worker` | Implementation-ready recommendations (or patch) |

Workflow:
1. Lead defines milestone + dispatch envelope + task contract.
2. Fan-out via parallel `send_input` calls (one per specialist).
3. Fan-in via a single `wait` barrier.
4. Lead gathers into `<agents_memory>` (milestone-only updates), resolves contradictions with evidence-first rules, then delivers.

Constraints:
- Specialists do NOT talk to each other (Lead is the only intermediary).
- Prefer bounded history: keep per-specialist context small; roll forward via `<agents_memory>` instead of long threads.
