# Runtime Contract Schema

## Objective

This document records the governed runtime's current public artifact contract for:

- `runtime input packet`
- `execution manifest`
- `runtime summary`

It describes the current shipped baseline. It is not a proposal surface.

## Scope Rules

- Required fields are part of the current public artifact contract and must remain stable unless a governed migration is explicitly approved.
- Optional compatibility fields may remain during extraction/refactor waves to preserve downstream readers.
- Allowed deprecations are fields that may be retired only after a compatibility window and proof-backed migration.

## Runtime Input Packet

Artifact:
- `outputs/runtime/vibe-sessions/<run-id>/runtime-input-packet.json`

Required fields:
- `stage`
- `run_id`
- `governance_scope`
- `task`
- `generated_at`
- `runtime_mode`
- `internal_grade`
- `hierarchy`
- `host_adapter`
- `module_assignments`
- `agent_skill_organization`
  - every module includes at least one structured `acceptance_criteria` item
  - each item requires a unique `criterion_id`, a non-empty `description`, and
    `verification_mode` set to `automated` or `manual`
- `skill_search_guide`
- `authority_flags`
- `provenance`

Required field groups:
- `hierarchy`
  - `governance_scope`
  - `root_run_id`
  - `parent_run_id`
  - `parent_unit_id`
  - `inherited_requirement_doc_path`
  - `inherited_execution_plan_path`
- `route_snapshot`
  - compatibility candidate audit only; it is not work or Skill-use truth
- `host_adapter`
  - `requested_host_id`
  - `effective_host_id`
  - `status`
  - `install_mode`
  - `check_mode`
  - `bootstrap_mode`
  - `target_root`
  - `closure_path`
- `module_assignments`
  - `task_id` or packet-level task binding identity
  - `units`
- `agent_skill_organization`
  - `schema_version`
  - `workflow_level`
  - `modules`
  - `selected_skills`
  - `uncovered_modules`
- `skill_search_guide`
  - `schema_version`
  - `skill_roots`
  - `search_protocol`
  - `selection_rules`
  - `disclosure_rules`
  - `escalation_status`
  - `approval_owner`
  - `status`
- `authority_flags`
  - `runtime_entry`
  - `explicit_runtime_skill`
  - `router_truth_level`
  - `shadow_only`
  - `non_authoritative`
  - `allow_requirement_freeze`
  - `allow_plan_freeze`
  - `allow_global_dispatch`
  - `allow_completion_claim`

Optional compatibility fields:
- `host_adapter.requested_id`
- `host_adapter.id`
- `custom_admission`
- `canonical_router`
- `route_snapshot`
- `skill_routing`
- `divergence_shadow`

Allowed deprecations:
- None active.

## Execution Manifest

The approved Agent work chain is `module-work-plan.json` ->
`agent-execution-handoff.json` -> `module-execution.json`.

Artifact:
- `outputs/runtime/vibe-sessions/<run-id>/execution-manifest.json`

Required fields:
- `stage`
- `run_id`
- `governance_scope`
- `mode`
- `internal_grade`
- `scheduler_kind`
- `profile_id`
- `requirement_doc_path`
- `execution_plan_path`
- `runtime_input_packet_path`
- `generated_at`
- `module_work_plan_path`
- `module_execution_path`
- `completed_unit_count`
- `failed_unit_count`
- `blocked_unit_count`
- `proof_class`
- `promotion_suitable`
- `hierarchy`
- `authority`
- `module_handoff`
- `dispatch_integrity`
- `status`
- `waves`

Required field groups:
- `authority`
  - `canonical_requirement_write_allowed`
  - `canonical_plan_write_allowed`
  - `global_dispatch_allowed`
  - `completion_claim_allowed`
- `module_handoff`
  - `status`
  - `control_owner`
  - `workflow_level`
  - `work_units`
  - `waves`
  - `requested_host_adapter_id`
  - `effective_host_adapter_id`
  - `effective_host_adapter_id`
  - `phase_binding_counts`
  - `dispatch_funnel`

Optional execution context field:
- `execution_memory_context_path`

Promotion funnel fields:
- `matched`
- `surfaced`
- `dispatched`
- `executed`
- `blocked_due_to_destructive`
- `degraded_due_to_missing_contract`
- `ghost_match`
- `executed_per_matched`
- `executed_rate`

Allowed deprecations:
- None active.

## Runtime Summary

Artifact:
- `outputs/runtime/vibe-sessions/<run-id>/runtime-summary.json`

Required fields:
- `run_id`
- `governance_scope`
- `mode`
- `task`
- `generated_at`
- `artifact_root`
- `session_root`
- `session_root_relative`
- `hierarchy`
- `stage_order`
- `artifacts`
- `memory_activation`
- `delivery_acceptance`
- `artifacts_relative`

Required summary blocks:
- `hierarchy`
  - same field names as runtime packet hierarchy projection
- `artifacts`
  - canonical absolute artifact paths emitted by the runtime
- `artifacts_relative`
  - artifact-root-relative counterparts for every `artifacts` entry
- `memory_activation`
  - `policy_mode`
  - `routing_contract`
  - `fallback_event_count`
  - `artifact_count`
  - `budget_guard_respected`
- `delivery_acceptance`
  - `gate_result`
  - `completion_language_allowed`
  - `readiness_state`
  - `manual_review_layer_count`
  - `failing_layer_count`

Optional compatibility fields:
- None active beyond nullability when a downstream report is unavailable.

Allowed deprecations:
- None active.

## Golden Snapshot Guidance

Curated runtime contract goldens must:

- freeze only stable semantic subsets
- normalize dynamic values such as:
  - `run_id`
  - `generated_at`
  - host-specific absolute paths
  - artifact output paths
- avoid full JSON parity assertions for large runtime artifacts
- keep packet and manifest goldens aligned with current public contract, not internal helper layout
