# vibe canonical instruction

Use `vibe` when the task needs the governed runtime across planning, coding, debugging, review, or multi-agent execution.

Canonical rules:

- pass the current user task verbatim to canonical-entry as the task specification; unrelated chat history may be excluded. Do not summarize, rewrite, or reduce it to keywords. Preserve exact input paths, input immutability constraints, exact output roots, synthetic-data evidence boundaries, module dependencies and safe parallel boundaries, and acceptance criteria
- `vibe` remains the runtime authority; the internal specialist recommender only suggests bounded specialist help
- the user-facing runtime path is fixed to skeleton_check -> deep_interview -> requirement_doc -> xl_plan -> plan_execute -> phase_cleanup
- `/vibe`, `$vibe`, and agent-invoked `vibe` are the same runtime contract
- discoverable wrapper labels may request an earlier terminal stage, but they never create a second runtime authority
- `M`, `L`, and `XL` are internal execution grades, not user-facing entry branches
- provider-assisted intelligence may advise but must not replace `vibe` runtime authority
- explicit user tool choice overrides routing
- at `requirement_doc`, the host must reuse the runtime skill-search guide and workflow-level confirmation from `host_user_briefing` in the same field order: explain that the Agent will split the task into modules, search local skills per module, read candidate `SKILL.md`, organize both L/XL plans, disclose uncovered modules honestly, and not surface shortlist or selected-skill rankings
- the host must not ask the user to choose L or XL until it has explained each task-specific workflow and named the task-specific candidate skill names for both options, explicitly saying those skills are not yet selected or used
- after requirement approval, the Agent must split the approved work into modules, search every declared local skill root for each module, and read each retained candidate's `SKILL.md`
- if one selected Skill owns multiple modules, include one `module_assignments` entry per module with the exact module id, an `owner`, `support`, or `verifier` role, module-specific responsibility, one concrete write scope, expected outputs, and verification
- role order is executable: `support` runs before and feeds the `owner`; `verifier` runs only after the `owner`. A post-owner review or minimality check must use `verifier`, not `support`
- An `agent_direct` module must declare its own concrete `write_scope`, `expected_outputs`, and `verification`; the runtime must not replace them with a generic module label or restated goal. A task work scope must not claim canonical runtime artifacts such as `module-execution.json`; use a stable task-owned output scope or `no task-file writes` for read-only work
- A plan revision that changes modules, Skills, roles, dependencies, write scopes, outputs, verification, or workflow level must resubmit the complete updated `agent_skill_organization`; `revision_delta` alone records text and does not mutate the frozen organization
- before entering `xl_plan`, the host must put the validated organization in `HostDecisionJson.agent_skill_organization`; compatibility route candidates must not populate it
- Module acceptance criteria must be satisfiable before canonical module-result re-entry. They must not require cleanup receipts, delivery acceptance, or completion-language permission, because canonical `phase_cleanup` creates those only after `module-execution.json` is accepted
- Verify ordinary modules from their actual deliverables and normal command or test output. Do not invent task-specific hashes, receipts, ledgers, matrices, scans, or proof files solely to prove execution order, Skill use, or file scope. Only require an extra evidence artifact when the user or domain contract needs that artifact
- after plan approval, reuse the frozen `agent_skill_organization`, use `module-work-plan.json` as the only dispatch authority, and bind every execution result to its digest in `module-execution.json`; copy `result_contract.submission_template`, preserve every frozen binding, and fill only the result fields. `criterion_results` states must be exactly `passing`, `failing`, or `blocked`; if canonical rejects the format before cleanup, correct the same `module-execution.json` and reuse the same return command instead of creating another handoff; do not rerun procedural skill selection, silently add skills, or hide declared gaps
- Code-task TDD evidence belongs inside the same `module-execution.json` when the handoff template includes `tdd_evidence`; fill that structured section before canonical return and do not create a separate `tdd-evidence.json` sidecar
- `stage_order` records dependency depth, not permission to run in parallel; L still emits one-unit sequential waves even when independent units share a dependency stage. XL may place at most two dependency-ready units in one wave, and nested or overlapping write scopes must remain serial
- report progress and cleanup by module first; required module failure, blocking, missing evidence, or pending human review must prevent complete-task wording
- keep selected, loaded, executed, contributed, and accepted as separate states; only module-bound observable contribution evidence may establish actual skill use
- XL execution may use multi-agent orchestration, but must preserve requirement freeze, review, cleanup, and no-regression discipline
