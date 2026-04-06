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
- `canonical_router`
- `host_adapter`
- `route_snapshot`
- `specialist_dispatch`
- `authority_flags`
- `divergence_shadow`
- `provenance`

Required field groups:
- `hierarchy`
  - `governance_scope`
  - `root_run_id`
  - `parent_run_id`
  - `parent_unit_id`
  - `inherited_requirement_doc_path`
  - `inherited_execution_plan_path`
- `canonical_router`
  - `prompt`
  - `task_type`
  - `requested_skill`
  - `host_id`
  - `target_root`
  - `unattended`
  - `route_script_path`
- `host_adapter`
  - `requested_host_id`
  - `effective_host_id`
  - `status`
  - `install_mode`
  - `check_mode`
  - `bootstrap_mode`
  - `target_root`
  - `closure_path`
- `route_snapshot`
  - `selected_pack`
  - `selected_skill`
  - `route_mode`
  - `confirm_required`
  - `truth_level`
  - `degradation_state`
  - `non_authoritative`
  - `fallback_active`
  - `hazard_alert_required`
  - `unattended_override_applied`
  - `custom_admission_status`
- `specialist_dispatch`
  - `approved_dispatch`
  - `local_specialist_suggestions`
  - `blocked`
  - `degraded`
  - `approved_skill_ids`
  - `local_suggestion_skill_ids`
  - `matched_skill_ids`
  - `surfaced_skill_ids`
  - `blocked_skill_ids`
  - `degraded_skill_ids`
  - `ghost_match_skill_ids`
  - `promotion_outcomes`
  - `escalation_required`
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
- `specialist_recommendations`
- `overlay_decisions`

Allowed deprecations:
- None active.

## Execution Manifest

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
- `execution_topology_path`
- `runtime_input_packet_path`
- `generated_at`
- `planned_wave_count`
- `planned_unit_count`
- `executed_unit_count`
- `successful_unit_count`
- `failed_unit_count`
- `timed_out_unit_count`
- `proof_class`
- `promotion_suitable`
- `hierarchy`
- `authority`
- `route_runtime_alignment`
- `execution_topology`
- `plan_shadow`
- `specialist_accounting`
- `dispatch_integrity`
- `status`
- `waves`

Required field groups:
- `authority`
  - `canonical_requirement_write_allowed`
  - `canonical_plan_write_allowed`
  - `global_dispatch_allowed`
  - `completion_claim_allowed`
- `route_runtime_alignment`
  - `router_selected_skill`
  - `runtime_selected_skill`
  - `skill_mismatch`
  - `confirm_required`
  - `requested_host_adapter_id`
  - `effective_host_adapter_id`
- `execution_topology`
  - `delegation_mode`
  - `wave_execution`
  - `step_execution`
  - `unit_execution`
  - `review_mode`
- `specialist_accounting`
  - `recommendation_count`
  - `dispatch_unit_count`
  - `matched_skill_ids`
  - `surfaced_skill_ids`
  - `specialist_skills`
  - `execution_mode`
  - `effective_execution_status`
  - `requested_host_adapter_id`
  - `effective_host_adapter_id`
  - `phase_binding_counts`
  - `promotion_funnel`

Optional compatibility fields:
- `execution_memory_context_path`
- `parallelizable_specialist_unit_count`
- `execution_topology.dispatch_resolution`
- `execution_topology.two_stage_review`
- detailed `specialist_accounting` outcome arrays

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
