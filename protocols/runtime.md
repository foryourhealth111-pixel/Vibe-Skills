# vibe-runtime Protocol

> **What this protocol does -- plain language overview**
>
> Every time you invoke `/vibe` or `$vibe`, the system runs this 6-stage process.
> You do not need to read this document to use VibeSkills -- it is reference material
> for contributors and advanced users who want to understand the runtime internals.
>
> **The 6 stages in plain terms:**
>
> | Stage | Internal name | What happens |
> |:---:|:---|:---|
> | 1 | `skeleton_check` | Check what is already in your repo before starting |
> | 2 | `deep_interview` | Clarify what you actually want (ask questions or infer) |
> | 3 | `requirement_doc` | Lock the agreed requirements into a document |
> | 4 | `xl_plan` | Write the execution plan |
> | 5 | `plan_execute` | Hand the approved module plan to the current Agent |
> | 6 | `phase_cleanup` | Clean up temp artifacts and produce a final report |
>
> **Key terms used below:**
> - **Agent skill organization**: the Agent splits approved work into modules, searches declared local roots, reads candidate `SKILL.md` files, and freezes `agent_skill_organization` before planning.
> - **Local skill candidate audit**: semantic owner `packages/runtime-core/src/vgo_runtime/router_contract_runtime.py`; compatibility bridge `scripts/router/resolve-pack-route.ps1`. It supplies audit evidence, not task-skill truth.
> - **Root/Child lane**: In multi-agent tasks, "root" is the coordinator; "child" lanes are workers. Only root makes final completion claims.
> - **Frozen requirement/plan**: Once you approve the requirements or plan, they are locked -- the system will not silently change scope.
> - **Proof bundle**: Evidence that a task was actually completed -- test results, output logs, verification commands.
> - **Silent fallback**: Quietly switching to a degraded path without telling the user -- this is explicitly forbidden.


Governed runtime contract for `vibe`.

This protocol defines the user-facing runtime path that all host syntaxes share.
It does not create a second router or second runtime surface.
It defines what must happen after `$vibe` enters the governed runtime.

When you need to explain a run or inspect artifacts, use this reading order:

1. start with `current-runtime-field-contract.md` plus the run's work artifacts such as `work_dossier`, `module_assignments`, `work_results`, and `verification`
2. for most normal runs, stop there and read the work truth rather than a compatibility chain
3. use this protocol to understand stage order and runtime lifecycle
4. read `current-routing-contract.md` only if you still need the compatibility candidate-audit chain

Public proof layers around this protocol stay narrow:

- `installed locally` belongs to install receipt / `check` and stays outside this protocol.
- `runtime coherent` starts only after canonical entry returns a `session_root` and the runtime truth artifacts exist.
- `delivery accepted` is decided by the delivery-acceptance report written during cleanup.

## Runtime Identity

`vibe` is one skill contract across all hosts:

- `/vibe`
- `$vibe`
- agent-invoked `vibe`

These are syntax variants for the same governed runtime, not separate entrypoints.

## Contract Priorities

1. `vibe` runtime authority stays intact.
2. User-facing runtime path stays fixed.
3. `M`, `L`, `XL` are not separate public entry commands; in interactive governed work, L/XL workflow level is a user-visible confirmation before execution planning.
4. Requirement freezing happens before plan execution.
5. Cleanup is mandatory before a phase is considered complete.
6. Silent fallback and silent degradation are forbidden.
7. Fallback success is non-authoritative unless a requirement explicitly approves otherwise.
8. Fake-success behavior is forbidden: the runtime must not swallow errors, emit mock completion, or template a pass result when the primary path failed.
9. New fallback or boundary behavior may exist only when the active requirement explicitly approves it, and it must remain explicit, traceable, and easy to disable.
10. `L` hands off module units serially; `XL` may group only dependency-ready units with disjoint write scopes.

## Official Runtime Modes

### `interactive_governed`

The only supported mode.

- ask direct high-value questions when needed
- freeze a requirement document with user-visible assumptions
- allow approval boundaries before execution

## Runtime Lineage Artifacts

Official governed entry is runtime-validated with artifact-backed lineage:

- `governance-capsule.json`: root-authored runtime authority capsule for the governed run
- `stage-lineage.json`: ordered stage-transition ledger for the current run
- `host-launch-receipt.json`: host-facing canonical entry receipt that must be `verified` before claiming canonical vibe entry
- `host-stage-disclosure.json`: append-only host-consumption event stream for confirmed module and Skill organization across discussion, planning, and Agent work
- `delegation-envelope.json`: root-authored child startup contract for inherited requirement/plan truth
- `delegation-validation-receipt.json`: child proof that envelope validation passed before bounded execution

These artifacts strengthen the official governed path only.
They do not claim OS-level or arbitrary shell-session enforcement.

Reading `SKILL.md`, wrapper markdown, or bootstrap text alone is not proof of canonical vibe entry.
Canonical claims require `host-launch-receipt.json`, `runtime-input-packet.json`, `governance-capsule.json`, and `stage-lineage.json`.

## Fixed 6-Stage State Machine

### Stage 1: `skeleton_check`

Purpose:

- verify repo skeleton and governed runtime prerequisites
- discover active requirement or plan artifacts
- detect conflicting dirty-state conditions

Required outputs:

- skeleton receipt
- repo-state summary

### Stage 2: `deep_interview`

Purpose:

- transform raw task text into a structured intent contract

Required fields:

- goal
- deliverable
- constraints
- acceptance criteria
- product acceptance criteria
- manual spot checks
- completion language policy
- delivery truth contract
- non-goals
- autonomy mode
- open questions
- inference notes

Required user-visible confirmation gates for L/XL work:

- `workflow_level_confirmation`: explain L versus XL in plain language, recommend one level, and do not ask the user to choose until both options show the task-specific workflow, candidate skill names, and each candidate's responsibility. Candidate names must be labeled as not yet selected or used; formal selection still happens in `agent_skill_organization` after requirement approval.
- `skill_use_confirmation`: after candidate Skills are recommended and before they become approved module assignments, tell the user "我将会在接下来的工作中使用这些 skills，你觉得 OK 吗？" and stop for approval, rejection, or revision.

These gates do not create new runtime entries. They are sub-gates inside the single `vibe` runtime.

### Stage 3: `requirement_doc`

Purpose:

- freeze the single requirement source for the run

Rules:

- write under `docs/requirements/`
- execution and review trace back to this document
- freeze downstream delivery semantics here, including product acceptance criteria, manual spot checks, and completion-language limits
- when the canonical anti-proxy-goal-drift policy is active, governed requirement packets must carry its declared objective, proxy-signal, scope, abstraction, completion, and evidence fields

### Stage 4: `xl_plan`

Purpose:

- generate the execution plan under `docs/plans/`

Required contents:

- internal execution grade
- frozen `agent_skill_organization`
- task modules and per-module candidate skills
- final selected skills with responsibilities and reasons
- uncovered modules
- approved module dependencies, execution modes, work units, write scopes, and acceptance criteria
- every module freezes at least one acceptance criterion object with a unique
  `criterion_id`, non-empty `description`, and `verification_mode` of
  `automated` or `manual`
- L / XL organization difference
- wave or batch structure
- ownership map
- verification commands
- delivery acceptance plan
- completion-language downgrade rules
- rollback strategy
- cleanup expectations
- when the canonical anti-proxy-goal-drift policy is active, governed plans must include the anti-drift control surface used by the canonical template

### Stage 5: `plan_execute`

Purpose:

- compile the frozen module plan into work the current Agent can perform
- stop with Agent control until the complete module result returns through canonical `vibe`

Rules:

- the approved `module-work-plan.json` workflow level controls topology and is the only work authority after plan approval
- `plan_execute` compiles `module-work-plan.json` into `agent-execution-handoff.json`, marks the handoff `agent_action_required`, and gives control to the current Agent
- every handoff unit names its unit, module, assigned Skill, `skill_entrypoint`, responsibility, expected outputs, verification, dependencies, and write scope
- the current Agent performs `L` units serially; for `XL`, it may group only dependency-ready units with disjoint write scopes
- official entry writes a governance capsule before stage-lineage validation proceeds
- later stages must append a matching lineage entry for the same governed run
- spawned subagent prompts must end with `$vibe`
- milestone evidence must be written before phase completion
- the handoff may contain only work units from the approved `module-work-plan.json`; packet projections and route audit fields cannot add work
- route candidates are compatibility audit evidence only; they must not auto-promote into approved handoff units or block governed stage progression
- Vibe does not execute module Skills or create completion results, stdout/stderr, or success receipts on the Agent's behalf
- `agent-execution-handoff.json.result_contract` is only the exact `module_execution_v1` submission schema and frozen source-run, plan-digest, unit-binding, and module-binding contract; it is not execution evidence or a module result
- the Agent must copy `result_contract.submission_template`, preserve every frozen binding, fill the unit and module result fields, and keep the exact planned criterion ids; `criterion_results` states are `passing`, `failing`, or `blocked`
- when the handoff includes a code-task `tdd_evidence` contract, the Agent fills it inside the same `module-execution.json`; a separate `tdd-evidence.json` sidecar is not part of the Agent return contract
- The current Agent reads every assigned `skill_entrypoint`, follows that `SKILL.md`, does the real module work, writes the complete result to `module-execution.json`, and returns it through canonical `vibe` re-entry for acceptance
- canonical re-entry validates the source run, approved-plan digest, complete work-unit and module bindings, criterion result set, and terminal states before `phase_cleanup`; a rejected format leaves the run at `plan_execute`, so the Agent corrects the same `module-execution.json` and reuses the same return command instead of creating another handoff
- every returned unit keeps its module id, work-unit id, role, dependency stage, write scope, and review mode
- a `blocked_gap` module must retain its approved `gap_reason`; cleanup must name both the blocked module and that reason
- runtime-selected skill stays `vibe`; task-skill truth comes from Agent-confirmed organization, not route output
- a Skill counts as used only when its assigned work unit is completed in `module-execution.json`; selection, planning, handoff, and generic manifests do not prove use
- incomplete, failed, or blocked required modules cannot enter successful cleanup or support a completion claim
- child-governed lanes inherit root-frozen requirement/plan context and must not open second canonical requirement or plan truth surfaces
- child-governed startup requires a root-authored `delegation-envelope.json`
- child-governed startup must emit `delegation-validation-receipt.json` before bounded work
- dangerous bulk deletion and blind recursive wipe commands against managed roots are forbidden by default during governed execution
- destructive removal must be narrowed to explicit unique paths, surfaced with a standalone hazard alert, and recorded in receipts rather than hidden behind convenience cleanup
- the run must emit a downstream delivery-acceptance report during closure so process success is not silently relabeled as project-delivery success

### Stage 6: `phase_cleanup`

Purpose:

- close the phase in a clean, auditable way

Minimum actions:

- accept the complete, plan-matched `module-execution.json` before successful cleanup
- temp artifact cleanup
- repo hygiene pass
- node audit or cleanup
- cleanup receipt write
- destructive cleanup, when exceptionally allowed, must remain path-bounded and receipt-backed; no blanket recursive wipe of managed roots
- delivery-acceptance report write with completion-language allowance or downgrade

## Protocol Delegation

The runtime may delegate stage internals to existing protocols:

- `think.md` for analysis, planning, and research
- `do.md` for execution, debugging, and verification
- `review.md` for quality review
- `team.md` for XL orchestration
- `retro.md` for retrospective learning after work closure

Delegation must not bypass the fixed stage order.

## Local Skill Candidate Audit Rules

- candidate-audit semantic owner remains `packages/runtime-core/src/vgo_runtime/router_contract_runtime.py`
- Python direct-first is the current path for local installed candidate discovery
- retained PowerShell callers still enter through compatibility bridge `scripts/router/resolve-pack-route.ps1`
- candidate scores, rankings, and `confirm_required` are compatibility audit metadata only
- candidate audit must not populate `agent_skill_organization`, add approved work, or block stage progression
- provider-backed intelligence remains advice-only
- fallback or degraded paths must emit an explicit hazard alert rather than a silent warning
- fallback or degraded paths must downgrade runtime truth to `non_authoritative`

## Authority Boundary Contract

The ecosystem may carry multiple helpful layers, but runtime authority must stay single-owner.

Layer ownership is:

- VCO governed runtime: public entry, stage order, requirement freeze, plan traceability, Agent handoff, module-result acceptance, cleanup receipts
- local skill candidate audit: compatibility evidence inside the governed runtime
- host bridge: hidden governance context attachment and host-hook wiring only
- process-method layers: workflow discipline only, never a second runtime surface

Explicitly forbidden:

- a second visible runtime entry ritual
- a second routing authority layer
- a second requirement truth surface
- a second plan truth surface

Process-discipline layers may require that a workflow be followed.
They may not replace, shadow, or duplicate governed runtime truth.

## Root/Child Hierarchy Contract

During XL Agent work, delegation is hierarchical rather than recursive top-level governance:

- `root_governed` lane:
  - owns canonical requirement freeze
  - owns canonical plan freeze
  - owns the frozen `agent_skill_organization` and its Agent handoff projection
  - owns final completion claim for the full task
- `child_governed` lane:
  - inherits root-frozen requirement and plan context
  - performs bounded delegated units
  - returns bounded module results and escalation requests only

Child-governed lanes are required to keep `$vibe` discipline but are forbidden from creating second canonical truth surfaces.

Explicitly forbidden for child-governed lanes:

- writing a second canonical requirement document under `docs/requirements/`
- writing a second canonical execution plan under `docs/plans/`
- issuing final completion claims for the root-governed task
- changing the frozen `agent_skill_organization` without root approval

Agent handoff semantics under hierarchy:

- `agent-execution-handoff.json`: carries Skill-assigned work units from the root-approved module plan to the current Agent
- child module work must preserve module id, work-unit dependencies, write scope, and review mode
- child-surfaced candidate suggestions remain audit or escalation evidence until a user-approved plan revision freezes a new organization

## Artifact Contract

Expected runtime artifacts:

- `outputs/runtime/vibe-sessions/<run-id>/skeleton-receipt.json`
- `outputs/runtime/vibe-sessions/<run-id>/intent-contract.json`
- `outputs/runtime/vibe-sessions/<run-id>/runtime-input-packet.json` with first-class `agent_skill_organization` and its `module_assignments` projection when bounded skill help exists
- requirement document
- execution plan
- `outputs/runtime/vibe-sessions/<run-id>/module-work-plan.json`
- `outputs/runtime/vibe-sessions/<run-id>/agent-execution-handoff.json` while Agent work is required
- `outputs/runtime/vibe-sessions/<run-id>/module-execution.json` after the Agent returns terminal module results
- phase receipts
- cleanup receipt
- runtime-input packet Agent-confirmed skill organization when bounded skill help is available
- workflow-level confirmation and plan approval records for the frozen Agent organization
- hierarchy-scoped authority markers indicating `root_governed` versus `child_governed` lane
- explicit escalation artifacts when child-governed lanes propose non-approved module work
- delivery-acceptance report proving whether full downstream completion language is allowed

## Success Criteria

The governed runtime is considered healthy only when:

- the 6-stage sequence is preserved
- requirement and plan artifacts exist
- accepted Agent module results trace back to the approved plan and handoff
- cleanup is recorded
- no success claim is made without verification evidence
- anti-proxy-goal-drift completion semantics are not silently bypassed in governed packets
- downstream delivery truth is evaluated separately from runtime/process truth before full completion wording is allowed
- no fallback or degraded path is presented as equivalent success
- any fallback or degraded path emits a standalone hazard alert
- no run claims canonical vibe entry without verified `host-launch-receipt.json`, `runtime-input-packet.json`, `governance-capsule.json`, and `stage-lineage.json`
- a plan-approved handoff stop requires digest-bound `module-work-plan.json` plus `agent-execution-handoff.json`; successful closure additionally requires accepted `module-execution.json`
