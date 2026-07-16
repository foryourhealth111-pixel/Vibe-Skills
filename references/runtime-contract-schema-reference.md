# Runtime Contract Schema Reference

This reference documents the currently supported public runtime contract surfaces emitted by governed `vibe` runs.

It is intentionally conservative:

- it records the current public fields
- it distinguishes required fields from compatibility-only fields
- it does not authorize silent field removal

## Scope

This reference covers:

- `runtime input packet`
- `execution manifest`
- `runtime summary`

It does not redefine:

- router contract ownership
- delivery acceptance report schema
- memory activation report schema

## Field Status Vocabulary

| Status | Meaning |
|---|---|
| `required` | public field that current runtime/tests/gates rely on |
| `optional_compatibility` | field that may be absent or `null` in some compatibility lanes but must not silently change meaning |
| `derived_summary` | summary field derived from deeper runtime artifacts |

## Deprecation Policy

- No field listed here is approved for silent removal.
- A future deprecation must first preserve a compatibility alias and characterization coverage.
- A deprecation proposal must state the replacement field, compatibility window, and rollback rule before removal.

## Runtime Input Packet

### Required fields

| Field | Status | Notes |
|---|---|---|
| `stage` | `required` | current value is `runtime_input_freeze` |
| `run_id` | `required` | per-run identifier |
| `governance_scope` | `required` | `root` or `child` |
| `task` | `required` | frozen input task |
| `generated_at` | `required` | packet emission timestamp |
| `runtime_mode` | `required` | effective mode after normalization |
| `internal_grade` | `required` | selected execution grade |
| `hierarchy` | `required` | shared hierarchy projection |
| `host_adapter` | `required` | requested/effective host adapter projection |
| `module_assignments` | `required` | kernel-facing bounded work truth |
| `agent_skill_organization` | `required` | Agent-confirmed module and local Skill organization used to freeze the plan |
| `agent_skill_organization.modules[].acceptance_criteria[]` | `required` | At least one object per module; each object has a unique `criterion_id`, non-empty `description`, and `verification_mode` of `automated` or `manual` |
| `skill_search_guide` | `required` | local Skill discovery and disclosure instructions for the Agent |
| `authority_flags` | `required` | runtime authority projection |
| `provenance` | `required` | proof/source-of-truth metadata |
| `canonical_router` | `optional_compatibility` | historical router-entry mirror; current bounded-work truth no longer depends on it |
| `route_snapshot` | `optional_compatibility` | compatibility control summary; current bounded-work truth lives elsewhere |
| `skill_routing` | `optional_compatibility` | compatibility mirror of selected bounded skills |
| `custom_admission` | `optional_compatibility` | may be `null` when no custom manifests participate |
| `divergence_shadow` | `optional_compatibility` | router/runtime mismatch observability shadow |

### Optional compatibility fields

| Field | Status | Notes |
|---|---|---|
| `continuation_context` | `optional_compatibility` | may be `null` when no bounded re-entry context is present |
| `host_decision` | `optional_compatibility` | structured host decision mirror when present |
| `code_task_tdd_decision` | `optional_compatibility` | code-task TDD decision mirror when present |
| `host_skill_execution_decision` | `optional_compatibility` | host curation decision mirror when present |
| `storage` | `derived_summary` | workspace and artifact-root projection for runtime surfaces |

## Execution Manifest

Current work authority flows through `module-work-plan.json`,
`agent-execution-handoff.json`, and `module-execution.json`.

### Required fields

| Field | Status | Notes |
|---|---|---|
| `stage` | `required` | current value is `plan_execute` |
| `run_id` | `required` | per-run identifier |
| `governance_scope` | `required` | root/child execution lane |
| `mode` | `required` | effective governed mode |
| `internal_grade` | `required` | execution grade |
| `scheduler_kind` | `required` | scheduler profile kind |
| `profile_id` | `required` | execution policy profile |
| `requirement_doc_path` | `required` | canonical requirement path |
| `execution_plan_path` | `required` | canonical plan path |
| `runtime_input_packet_path` | `required` | frozen packet path |
| `generated_at` | `required` | manifest timestamp |
| `module_work_plan_path` | `required` | approved module work authority |
| `module_execution_path` | `required after re-entry` | Agent module result |
| `completed_unit_count` | `required after re-entry` | completed module work count |
| `failed_unit_count` | `required` | failure count |
| `blocked_unit_count` | `required` | blocked module work count |
| `proof_class` | `required` | current class is `runtime` |
| `promotion_suitable` | `required` | proof promotion posture |
| `hierarchy` | `required` | shared hierarchy projection |
| `authority` | `required` | execution authority projection |
| `module_handoff` | `required` | Agent handoff status and host alignment |
| `dispatch_integrity` | `required` | dispatch proof summary |
| `status` | `required` | execution result |
| `waves` | `required` | per-wave receipts |

### Optional compatibility fields

| Field | Status | Notes |
|---|---|---|
| `execution_memory_context_path` | `optional_compatibility` | may be `null` if no memory context artifact is emitted |

## Runtime Summary

### Required fields

| Field | Status | Notes |
|---|---|---|
| `run_id` | `required` | per-run identifier |
| `governance_scope` | `required` | root/child summary lane |
| `mode` | `required` | effective governed mode |
| `task` | `required` | top-level task text |
| `generated_at` | `required` | summary timestamp |
| `artifact_root` | `required` | artifact base root |
| `session_root` | `required` | session directory |
| `session_root_relative` | `required` | artifact-root-relative session path |
| `hierarchy` | `required` | hierarchy projection |
| `stage_order` | `required` | six-stage governed lifecycle |
| `artifacts` | `required` | absolute artifact paths |
| `memory_activation` | `derived_summary` | derived from memory activation report |
| `delivery_acceptance` | `derived_summary` | derived from delivery acceptance report |
| `artifacts_relative` | `required` | artifact-root-relative path map |

### Optional compatibility fields

| Field | Status | Notes |
|---|---|---|
| `memory_activation` value | `optional_compatibility` | field remains present but value may be `null` if no report exists |
| `delivery_acceptance` value | `optional_compatibility` | field remains present but value may be `null` if no report exists |
