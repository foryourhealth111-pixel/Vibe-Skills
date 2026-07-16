# Runtime Contract Field Contract

Date: 2026-03-30

This contract freezes the public fields that downstream tests and later migration waves rely on across the governed runtime artifacts.

## Scope

Artifacts covered by this contract:

- `runtime input packet`
- `execution manifest`
- `runtime summary`

This is a field contract, not a full payload dump. It freezes the public surface that later waves must preserve while internal construction logic continues to converge onto shared helpers.

## Required Fields

### Runtime Input Packet

Required top-level fields:

- `stage`
- `run_id`
- `governance_scope`
- `runtime_mode`
- `internal_grade`
- `hierarchy`
- `host_adapter`
- `authority_flags`
- `provenance`

Required nested fields:

- `hierarchy.governance_scope`
- `hierarchy.root_run_id`
- `host_adapter.requested_host_id`
- `host_adapter.effective_host_id`
- `authority_flags.explicit_runtime_skill`
- `authority_flags.allow_requirement_freeze`
- `authority_flags.allow_plan_freeze`
- `authority_flags.allow_global_dispatch`
- `authority_flags.allow_completion_claim`

Optional compatibility nested fields:

- `route_snapshot.selected_skill`
- `route_snapshot.task_type`
- `route_snapshot.route_mode`
- `route_snapshot.confirm_required`

### Execution Manifest

The current authority chain is `module-work-plan.json` ->
`agent-execution-handoff.json` -> `module-execution.json`.

Required top-level fields:

- `stage`
- `run_id`
- `governance_scope`
- `mode`
- `internal_grade`
- `hierarchy`
- `authority`
- `module_handoff`
- `status`
- `proof_class`

Required nested fields:

- `hierarchy.governance_scope`
- `hierarchy.root_run_id`
- `authority.canonical_requirement_write_allowed`
- `authority.canonical_plan_write_allowed`
- `authority.global_dispatch_allowed`
- `authority.completion_claim_allowed`
- `module_handoff.status`
- `module_handoff.control_owner`
- `module_handoff.workflow_level`
- `module_handoff.requested_host_adapter_id`
- `module_handoff.effective_host_adapter_id`

### Runtime Summary

Required top-level fields:

- `run_id`
- `governance_scope`
- `mode`
- `task`
- `artifact_root`
- `session_root`
- `session_root_relative`
- `hierarchy`
- `stage_order`
- `artifacts`
- `artifacts_relative`

Required nested/runtime-summary block fields:

- `hierarchy.root_run_id`
- `artifacts.runtime_input_packet`
- `artifacts.execution_manifest`
- `artifacts.cleanup_receipt`
- `artifacts_relative.runtime_input_packet`
- `artifacts_relative.execution_manifest`
- `artifacts_relative.cleanup_receipt`

Conditional required blocks:

- when a memory activation report exists:
  - `memory_activation.policy_mode`
  - `memory_activation.routing_contract`
  - `memory_activation.fallback_event_count`
  - `memory_activation.artifact_count`
  - `memory_activation.budget_guard_respected`
- when a delivery acceptance report exists:
  - `delivery_acceptance.gate_result`
  - `delivery_acceptance.completion_language_allowed`
  - `delivery_acceptance.readiness_state`

## Optional Compatibility Fields

These fields remain public and compatibility-preserved, but later waves may continue to centralize how they are constructed:

- runtime input packet:
  - `canonical_router`
  - `custom_admission`
  - `specialist_recommendations`
  - `specialist_dispatch`
  - `divergence_shadow`
- execution manifest:
  - `dispatch_integrity`
  - `module_handoff`
  - `execution_memory_context_path`
- runtime summary:
  - `memory_activation`
  - `delivery_acceptance`
  - `host_stage_disclosure`
  - `host_user_briefing`

Compatibility rule:

- public field names remain stable
- helper extraction is allowed
- value derivation may be centralized
- public meaning must not silently drift

## Allowed Deprecations

Current public-field deprecations allowed by this contract: none.

Allowed internal deprecations:

- removal of local duplicate field-construction logic after a shared helper replacement is verified
- movement of path-normalization helpers from local script scope to shared common runtime scope

Not allowed in the current compatibility window:

- dropping public fields
- renaming public fields
- converting required fields into optional ones
- changing `artifacts` absolute paths into relative paths
- changing `artifacts_relative` relative paths into absolute paths

## Curated Golden Policy

Curated golden fixtures may freeze normalized subsets of runtime artifacts.

Normalization requirements:

- replace run-specific ids with placeholders such as `<run_id>`
- replace machine-specific host paths with placeholders such as `<host_target_root>` and `<host_closure_path>`
- do not freeze timestamps
- do not freeze temporary artifact-root-dependent absolute paths unless the test explicitly normalizes them

## Maintenance Rule

Any new public runtime artifact field introduced in later waves must update this contract in the same change.
