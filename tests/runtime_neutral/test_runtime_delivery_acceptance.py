from __future__ import annotations

import json
import importlib.util
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "verify" / "runtime_neutral" / "runtime_delivery_acceptance.py"
SPEC = importlib.util.spec_from_file_location("runtime_delivery_acceptance", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load runtime delivery acceptance module from {MODULE_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
evaluate = MODULE.evaluate
write_artifacts = MODULE.write_artifacts


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


class RuntimeDeliveryAcceptanceTests(unittest.TestCase):
    def _build_session(
        self,
        *,
        execution_status: str = "completed",
        failed_unit_count: int = 0,
        manual_spot_checks: list[str] | None = None,
        include_product_criteria: bool = True,
        artifact_review_requirements: list[str] | None = None,
        code_task_tdd_evidence_requirements: list[str] | None = None,
        code_task_tdd_exceptions: list[str] | None = None,
        baseline_document_quality_dimensions: list[str] | None = None,
        baseline_ui_quality_dimensions: list[str] | None = None,
        task_specific_acceptance_extensions: list[str] | None = None,
        research_augmentation_sources: list[str] | None = None,
        phase_execute_artifact_review: dict[str, object] | None = None,
        phase_execute_tdd_evidence: dict[str, object] | None = None,
        sidecar_artifact_review: dict[str, object] | None = None,
        sidecar_tdd_evidence: dict[str, object] | None = None,
        artifact_review_path: str | None = None,
        tdd_evidence_path: str | None = None,
        governance_scope: str = "root",
        completion_claim_allowed: bool = True,
        cleanup_mode: str = "bounded_cleanup_executed",
        approved_dispatch: list[dict[str, object]] | None = None,
        phase_execute_specialist_user_disclosure: dict[str, object] | None = None,
        specialist_accounting: dict[str, object] | None = None,
        phase_execute_specialist_decision: dict[str, object] | None = None,
        sidecar_specialist_decision: dict[str, object] | None = None,
        specialist_decision_path: str | None = None,
        omit_default_specialist_decision: bool = False,
    ) -> Path:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        root = Path(tempdir.name)
        session_root = root / "outputs" / "runtime" / "vibe-sessions" / "pytest-runtime-delivery"
        session_root.mkdir(parents=True, exist_ok=True)

        requirement_doc_path = root / "docs" / "requirements" / "pytest.md"
        execution_plan_path = root / "docs" / "plans" / "pytest-plan.md"
        execution_manifest_path = session_root / "execution-manifest.json"
        runtime_input_packet_path = session_root / "runtime-input-packet.json"

        requirement_lines = [
            "# Pytest Delivery Contract",
            "",
            "## Acceptance Criteria",
            "- Runtime smoke passes.",
            "",
        ]
        if include_product_criteria:
            requirement_lines += [
                "## Product Acceptance Criteria",
                "- Deliverable behavior matches the frozen requirement.",
                "",
            ]
        requirement_lines += [
            "## Manual Spot Checks",
        ]
        if manual_spot_checks:
            requirement_lines.extend([f"- {item}" for item in manual_spot_checks])
        else:
            requirement_lines.append(
                "- None required beyond automated verification for this task unless the execution scope expands to a user-visible or interactive flow."
            )
        requirement_lines += [
            "",
            "## Completion Language Policy",
            "- Full completion wording requires passing delivery truth.",
            "",
            "## Delivery Truth Contract",
            "- Governance truth remains distinct from product acceptance truth.",
            "",
        ]
        if artifact_review_requirements:
            requirement_lines += [
                "## Artifact Review Requirements",
                *[f"- {item}" for item in artifact_review_requirements],
                "",
            ]
        if code_task_tdd_evidence_requirements:
            requirement_lines += [
                "## Code Task TDD Evidence Requirements",
                *[f"- {item}" for item in code_task_tdd_evidence_requirements],
                "",
            ]
        if code_task_tdd_exceptions:
            requirement_lines += [
                "## Code Task TDD Exceptions",
                *[f"- {item}" for item in code_task_tdd_exceptions],
                "",
            ]
        if baseline_document_quality_dimensions:
            requirement_lines += [
                "## Baseline Document Quality Dimensions",
                *[f"- {item}" for item in baseline_document_quality_dimensions],
                "",
            ]
        if baseline_ui_quality_dimensions:
            requirement_lines += [
                "## Baseline UI Quality Dimensions",
                *[f"- {item}" for item in baseline_ui_quality_dimensions],
                "",
            ]
        if task_specific_acceptance_extensions:
            requirement_lines += [
                "## Task-Specific Acceptance Extensions",
                *[f"- {item}" for item in task_specific_acceptance_extensions],
                "",
            ]
        if research_augmentation_sources:
            requirement_lines += [
                "## Research Augmentation Sources",
                *[f"- {item}" for item in research_augmentation_sources],
                "",
            ]
        write_text(requirement_doc_path, "\n".join(requirement_lines) + "\n")
        write_text(
            execution_plan_path,
            "# Pytest Plan\n\n## Delivery Acceptance Plan\n- Emit the runtime delivery report.\n",
        )

        execution_manifest_payload = {
            "status": execution_status,
            "governance_scope": governance_scope,
            "executed_unit_count": 3,
            "failed_unit_count": failed_unit_count,
            "timed_out_unit_count": 0,
        }
        approved_dispatch_payload = list(approved_dispatch or [])
        if approved_dispatch is not None or specialist_accounting is not None:
            default_specialist_accounting = {
                "approved_dispatch": approved_dispatch_payload,
                "approved_dispatch_count": len(approved_dispatch_payload),
                "degraded_skill_ids": [],
                "blocked_skill_ids": [],
                "effective_execution_status": "live_native_executed" if approved_dispatch_payload else "none",
            }
            if specialist_accounting:
                default_specialist_accounting.update(specialist_accounting)
            execution_manifest_payload["specialist_accounting"] = default_specialist_accounting
        write_json(execution_manifest_path, execution_manifest_payload)

        runtime_input_packet_payload = {
            "authority_flags": {
                "explicit_runtime_skill": "vibe",
            }
        }
        if approved_dispatch is not None:
            approved_skill_ids = [
                str(item["skill_id"]).strip()
                for item in approved_dispatch_payload
                if str(item.get("skill_id", "")).strip()
            ]
            runtime_input_packet_payload["specialist_dispatch"] = {
                "approved_dispatch": approved_dispatch_payload,
                "local_specialist_suggestions": [],
                "blocked": [],
                "degraded": [],
                "approved_skill_ids": approved_skill_ids,
                "local_suggestion_skill_ids": [],
                "matched_skill_ids": approved_skill_ids,
                "surfaced_skill_ids": approved_skill_ids,
                "blocked_skill_ids": [],
                "degraded_skill_ids": [],
                "ghost_match_skill_ids": [],
                "promotion_outcomes": [],
                "escalation_required": False,
                "escalation_status": "not_required",
                "approval_owner": "root_vibe",
                "status": "auto_promote_when_safe_same_round",
            }
        write_json(runtime_input_packet_path, runtime_input_packet_payload)
        phase_execute_payload = {
            "requirement_doc_path": str(requirement_doc_path),
            "execution_plan_path": str(execution_plan_path),
            "execution_manifest_path": str(execution_manifest_path),
            "runtime_input_packet_path": str(runtime_input_packet_path),
            "completion_claim_allowed": completion_claim_allowed,
            "artifact_review": phase_execute_artifact_review or {},
            "tdd_evidence": phase_execute_tdd_evidence or {},
        }
        if phase_execute_specialist_user_disclosure is not None:
            phase_execute_payload["specialist_user_disclosure"] = phase_execute_specialist_user_disclosure
        if phase_execute_specialist_decision is not None:
            phase_execute_payload["specialist_decision"] = phase_execute_specialist_decision
        elif not omit_default_specialist_decision and sidecar_specialist_decision is None and not specialist_decision_path:
            if approved_dispatch_payload:
                phase_execute_payload["specialist_decision"] = {
                    "decision_state": "approved_dispatch",
                    "resolution_mode": "approved_dispatch",
                    "approved_dispatch_skill_ids": approved_skill_ids,
                    "repo_asset_fallback": {
                        "used": False,
                        "asset_paths": [],
                        "reason": "",
                        "legal_basis": "",
                        "traceability_basis": [],
                    },
                }
            else:
                phase_execute_payload["specialist_decision"] = {
                    "decision_state": "no_specialist_recommendations",
                    "resolution_mode": "no_specialist_needed",
                    "repo_asset_fallback": {
                        "used": False,
                        "asset_paths": [],
                        "reason": "",
                        "legal_basis": "",
                        "traceability_basis": [],
                    },
                }
        if artifact_review_path:
            phase_execute_payload["artifact_review_path"] = artifact_review_path
        if tdd_evidence_path:
            phase_execute_payload["tdd_evidence_path"] = tdd_evidence_path
        if specialist_decision_path:
            phase_execute_payload["specialist_decision_path"] = specialist_decision_path
        write_json(
            session_root / "phase-execute.json",
            phase_execute_payload,
        )
        write_json(
            session_root / "cleanup-receipt.json",
            {
                "cleanup_mode": cleanup_mode,
            },
        )
        if sidecar_artifact_review is not None:
            write_json(session_root / "artifact-review.json", sidecar_artifact_review)
        if sidecar_tdd_evidence is not None:
            write_json(session_root / "tdd-evidence.json", sidecar_tdd_evidence)
        if sidecar_specialist_decision is not None:
            write_json(session_root / "specialist-decision.json", sidecar_specialist_decision)
        return session_root

    def test_runtime_delivery_acceptance_passes_for_clean_root_run(self) -> None:
        session_root = self._build_session(
            phase_execute_specialist_decision={
                "decision_state": "no_specialist_recommendations",
                "resolution_mode": "no_specialist_needed",
                "repo_asset_fallback": {
                    "used": False,
                    "asset_paths": [],
                    "reason": "",
                    "legal_basis": "",
                    "traceability_basis": [],
                },
            }
        )
        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("PASS", report["summary"]["gate_result"])
        self.assertTrue(report["summary"]["completion_language_allowed"])
        self.assertEqual("not_applicable", report["truth_results"]["code_task_tdd_evidence_truth"]["state"])
        self.assertEqual("passing", report["truth_results"]["product_acceptance_truth"]["state"])
        self.assertEqual("not_applicable", report["truth_results"]["specialist_disclosure_truth"]["state"])
        self.assertEqual("passing", report["truth_results"]["specialist_decision_truth"]["state"])

    def test_runtime_delivery_acceptance_requires_explicit_specialist_resolution_when_no_recommendation_exists(self) -> None:
        session_root = self._build_session(omit_default_specialist_decision=True)
        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("MANUAL_REVIEW_REQUIRED", report["summary"]["gate_result"])
        self.assertFalse(report["summary"]["completion_language_allowed"])
        self.assertEqual("manual_review_required", report["truth_results"]["specialist_decision_truth"]["state"])
        self.assertIn(
            "no bounded specialist recommendation path was frozen but no explicit specialist resolution was recorded",
            report["truth_results"]["specialist_decision_truth"]["notes"].lower(),
        )

    def test_runtime_delivery_acceptance_reports_pass_degraded_for_traceable_repo_asset_fallback(self) -> None:
        session_root = self._build_session(
            phase_execute_specialist_decision={
                "decision_state": "no_specialist_recommendations",
                "resolution_mode": "repo_asset_fallback",
                "repo_asset_fallback": {
                    "used": True,
                    "asset_paths": [
                        "outputs/agent-runs/2026-04-14-scheme-a-clean397-paper-report/scripts/plot_style.py"
                    ],
                    "reason": "Reuse the existing paper-report plotting style asset when no dedicated plotting specialist is available.",
                    "legal_basis": "Repo-local plotting asset already present inside governed workspace outputs.",
                    "traceability_basis": [
                        "outputs/agent-runs/2026-04-14-scheme-a-clean397-paper-report/scripts/plot_style.py"
                    ],
                },
            }
        )
        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("PASS_DEGRADED", report["summary"]["gate_result"])
        self.assertFalse(report["summary"]["completion_language_allowed"])
        self.assertEqual("degraded", report["truth_results"]["specialist_decision_truth"]["state"])
        self.assertIn(
            "repo-asset fallback stayed explicit and traceable",
            report["truth_results"]["specialist_decision_truth"]["notes"].lower(),
        )

    def test_runtime_delivery_acceptance_fails_when_repo_asset_fallback_omits_traceability(self) -> None:
        session_root = self._build_session(
            phase_execute_specialist_decision={
                "decision_state": "no_specialist_recommendations",
                "resolution_mode": "repo_asset_fallback",
                "repo_asset_fallback": {
                    "used": True,
                    "asset_paths": [
                        "outputs/agent-runs/2026-04-14-scheme-a-clean397-paper-report/scripts/plot_style.py"
                    ],
                    "reason": "Reuse the repo plotting asset.",
                    "legal_basis": "Repo-local plotting asset already present inside governed workspace outputs.",
                    "traceability_basis": [],
                },
            }
        )
        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("FAIL", report["summary"]["gate_result"])
        self.assertFalse(report["summary"]["completion_language_allowed"])
        self.assertEqual("failing", report["truth_results"]["specialist_decision_truth"]["state"])
        self.assertIn(
            "traceability",
            report["truth_results"]["specialist_decision_truth"]["notes"].lower(),
        )

    def test_runtime_delivery_acceptance_fails_when_approved_dispatch_lacks_disclosure(self) -> None:
        approved_dispatch = [
            {
                "skill_id": "systematic-debugging",
                "native_skill_entrypoint": "/tmp/systematic-debugging/SKILL.md",
            }
        ]
        session_root = self._build_session(
            approved_dispatch=approved_dispatch,
            specialist_accounting={
                "approved_dispatch": approved_dispatch,
                "approved_dispatch_count": 1,
                "effective_execution_status": "live_native_executed",
            },
        )
        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("FAIL", report["summary"]["gate_result"])
        self.assertFalse(report["summary"]["completion_language_allowed"])
        self.assertEqual("failing", report["truth_results"]["specialist_disclosure_truth"]["state"])
        self.assertIn(
            "approved specialist dispatch was present but no specialist user disclosure was recorded",
            report["truth_results"]["specialist_disclosure_truth"]["notes"].lower(),
        )

    def test_runtime_delivery_acceptance_fails_when_disclosure_contradicts_approved_dispatch(self) -> None:
        approved_dispatch = [
            {
                "skill_id": "systematic-debugging",
                "native_skill_entrypoint": "/tmp/systematic-debugging/SKILL.md",
            }
        ]
        session_root = self._build_session(
            approved_dispatch=approved_dispatch,
            phase_execute_specialist_user_disclosure={
                "scope": "approved_dispatch_only",
                "timing": "before_execution",
                "path_source": "native_skill_entrypoint",
                "routed_skills": [
                    {
                        "skill_id": "brainstorming",
                        "native_skill_entrypoint": "/tmp/brainstorming/SKILL.md",
                        "entrypoint_requirement_satisfied": True,
                    }
                ],
            },
            specialist_accounting={
                "approved_dispatch": approved_dispatch,
                "approved_dispatch_count": 1,
                "effective_execution_status": "live_native_executed",
            },
        )
        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("FAIL", report["summary"]["gate_result"])
        self.assertFalse(report["summary"]["completion_language_allowed"])
        self.assertEqual("failing", report["truth_results"]["specialist_disclosure_truth"]["state"])
        self.assertIn(
            "did not match effective approved dispatch",
            report["truth_results"]["specialist_disclosure_truth"]["notes"],
        )

    def test_runtime_delivery_acceptance_requires_manual_review_when_execution_stays_current_session_routed(self) -> None:
        approved_dispatch = [
            {
                "skill_id": "systematic-debugging",
                "native_skill_entrypoint": "/tmp/systematic-debugging/SKILL.md",
            }
        ]
        session_root = self._build_session(
            approved_dispatch=approved_dispatch,
            phase_execute_specialist_user_disclosure={
                "scope": "approved_dispatch_only",
                "timing": "before_execution",
                "path_source": "native_skill_entrypoint",
                "routed_skills": [
                    {
                        "skill_id": "systematic-debugging",
                        "native_skill_entrypoint": "/tmp/systematic-debugging/SKILL.md",
                        "entrypoint_requirement_satisfied": True,
                    }
                ],
            },
            specialist_accounting={
                "approved_dispatch": approved_dispatch,
                "approved_dispatch_count": 1,
                "effective_execution_status": "direct_current_session_routed",
            },
        )
        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("MANUAL_REVIEW_REQUIRED", report["summary"]["gate_result"])
        self.assertFalse(report["summary"]["completion_language_allowed"])
        self.assertEqual("manual_review_required", report["truth_results"]["workflow_completion_truth"]["state"])
        self.assertIn(
            "host continuation is still required",
            report["truth_results"]["workflow_completion_truth"]["notes"].lower(),
        )
        self.assertTrue(report["execution_context"]["specialist_host_continuation_pending"])
        self.assertIn(
            "Approved execution is still waiting on direct current-session host continuation.",
            report["residual_risks"],
        )

    def test_runtime_delivery_acceptance_treats_approved_dispatch_matching_as_order_independent(self) -> None:
        approved_dispatch = [
            {
                "skill_id": "skill-b",
                "native_skill_entrypoint": "/tmp/skill-b/SKILL.md",
            },
            {
                "skill_id": "skill-a",
                "native_skill_entrypoint": "/tmp/skill-a/SKILL.md",
            },
        ]
        session_root = self._build_session(
            approved_dispatch=approved_dispatch,
            phase_execute_specialist_user_disclosure={
                "scope": "approved_dispatch_only",
                "timing": "before_execution",
                "path_source": "native_skill_entrypoint",
                "routed_skills": [
                    {
                        "skill_id": "skill-a",
                        "native_skill_entrypoint": "/tmp/skill-a/SKILL.md",
                        "entrypoint_requirement_satisfied": True,
                    },
                    {
                        "skill_id": "skill-b",
                        "native_skill_entrypoint": "/tmp/skill-b/SKILL.md",
                        "entrypoint_requirement_satisfied": True,
                    },
                ],
            },
            specialist_accounting={
                "approved_dispatch": approved_dispatch,
                "approved_dispatch_count": 2,
                "effective_execution_status": "live_native_executed",
            },
            phase_execute_specialist_decision={
                "decision_state": "approved_dispatch",
                "resolution_mode": "approved_dispatch",
                "approved_dispatch_skill_ids": ["skill-a", "skill-b"],
                "repo_asset_fallback": {
                    "used": False,
                    "asset_paths": [],
                    "reason": "",
                    "legal_basis": "",
                    "traceability_basis": [],
                },
            },
        )
        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("PASS", report["summary"]["gate_result"])
        self.assertEqual("passing", report["truth_results"]["specialist_disclosure_truth"]["state"])
        self.assertEqual("passing", report["truth_results"]["specialist_decision_truth"]["state"])

    def test_runtime_delivery_acceptance_reports_pass_degraded_for_aligned_degraded_specialist_execution(self) -> None:
        approved_dispatch = [
            {
                "skill_id": "systematic-debugging",
                "native_skill_entrypoint": "/tmp/systematic-debugging/SKILL.md",
            }
        ]
        session_root = self._build_session(
            approved_dispatch=approved_dispatch,
            phase_execute_specialist_user_disclosure={
                "scope": "approved_dispatch_only",
                "timing": "before_execution",
                "path_source": "native_skill_entrypoint",
                "routed_skills": [
                    {
                        "skill_id": "systematic-debugging",
                        "native_skill_entrypoint": "/tmp/systematic-debugging/SKILL.md",
                        "entrypoint_requirement_satisfied": True,
                    }
                ],
            },
            specialist_accounting={
                "approved_dispatch": approved_dispatch,
                "approved_dispatch_count": 1,
                "degraded_skill_ids": ["systematic-debugging"],
                "effective_execution_status": "explicitly_degraded",
            },
        )
        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("PASS_DEGRADED", report["summary"]["gate_result"])
        self.assertFalse(report["summary"]["completion_language_allowed"])
        self.assertEqual("degraded", report["truth_results"]["specialist_disclosure_truth"]["state"])
        self.assertGreaterEqual(report["summary"]["degraded_layer_count"], 1)
        self.assertEqual("degraded_but_traceable", report["summary"]["readiness_state"])

    def test_runtime_delivery_acceptance_report_covers_contract_required_fields(self) -> None:
        contract = json.loads(
            (REPO_ROOT / "config" / "project-delivery-acceptance-contract.json").read_text(encoding="utf-8")
        )
        session_root = self._build_session()
        report = evaluate(REPO_ROOT, session_root)

        reported_fields = set(report["truth_results"].keys())
        reported_fields.update(
            {
                "completion_language_allowed",
                "artifact_review_coverage",
                "tdd_evidence_coverage",
                "residual_risks",
                "manual_spot_checks",
            }
        )
        missing_fields = [
            field
            for field in contract["report_requirements"]["must_report_fields"]
            if field not in reported_fields
        ]

        self.assertEqual([], missing_fields)
        self.assertIn("completion_language_allowed", report["summary"])

    def test_runtime_delivery_acceptance_requires_manual_review_when_spot_checks_pending(self) -> None:
        session_root = self._build_session(
            manual_spot_checks=[
                "Open the primary UI flow and confirm the main path works end-to-end."
            ]
        )
        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("MANUAL_REVIEW_REQUIRED", report["summary"]["gate_result"])
        self.assertFalse(report["summary"]["completion_language_allowed"])
        self.assertEqual("manual_actions_pending", report["summary"]["readiness_state"])
        self.assertEqual("manual_review_required", report["truth_results"]["product_acceptance_truth"]["state"])

    def test_runtime_delivery_acceptance_fails_for_completed_with_failures(self) -> None:
        session_root = self._build_session(
            execution_status="completed_with_failures",
            failed_unit_count=1,
        )
        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("FAIL", report["summary"]["gate_result"])
        self.assertFalse(report["summary"]["completion_language_allowed"])
        self.assertGreaterEqual(report["summary"]["forbidden_completion_hit_count"], 1)
        self.assertEqual("partial", report["truth_results"]["engineering_verification_truth"]["state"])

    def test_runtime_delivery_acceptance_requires_manual_review_when_artifact_review_is_missing(self) -> None:
        session_root = self._build_session(
            artifact_review_requirements=[
                "Inspect the delivered artifact directly and confirm the required controls and layout are present."
            ]
        )
        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("MANUAL_REVIEW_REQUIRED", report["summary"]["gate_result"])
        self.assertFalse(report["summary"]["completion_language_allowed"])
        self.assertEqual("manual_review_required", report["truth_results"]["artifact_review_truth"]["state"])
        self.assertEqual("manual_review_required", report["truth_results"]["product_acceptance_truth"]["state"])
        self.assertEqual(
            [
                "Inspect the delivered artifact directly and confirm the required controls and layout are present."
            ],
            report["frozen_requirement_sections"]["artifact_review_requirements"],
        )

    def test_runtime_delivery_acceptance_requires_document_baseline_coverage_when_dimensions_are_frozen(self) -> None:
        session_root = self._build_session(
            artifact_review_requirements=[
                "Inspect the final document artifact directly and confirm the formatting remains intact."
            ],
            baseline_document_quality_dimensions=[
                "Structure Integrity",
                "Formatting Consistency",
            ],
            phase_execute_artifact_review={
                "status": "passing",
                "evidence_paths": [
                    "/tmp/pytest-artifact-review-notes.md"
                ],
                "notes": "Reviewed the document artifact, but did not map frozen document baseline dimensions.",
            },
        )
        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("MANUAL_REVIEW_REQUIRED", report["summary"]["gate_result"])
        self.assertEqual("manual_review_required", report["truth_results"]["artifact_review_truth"]["state"])
        self.assertEqual(
            [
                "Structure Integrity",
                "Formatting Consistency",
            ],
            report["artifact_review_coverage"]["missing_baseline_document_quality_dimensions"],
        )

    def test_runtime_delivery_acceptance_passes_when_document_baseline_coverage_is_explicit(self) -> None:
        session_root = self._build_session(
            artifact_review_requirements=[
                "Inspect the final document artifact directly and confirm the formatting remains intact."
            ],
            baseline_document_quality_dimensions=[
                "Structure Integrity",
                "Formatting Consistency",
            ],
            phase_execute_artifact_review={
                "status": "passing",
                "evidence_paths": [
                    "/tmp/pytest-artifact-review-notes.md"
                ],
                "covered_baseline_document_quality_dimensions": [
                    "Structure Integrity",
                    "Formatting Consistency",
                ],
                "notes": "Reviewed the document artifact against frozen document baseline dimensions.",
            },
        )
        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("PASS", report["summary"]["gate_result"])
        self.assertEqual("passing", report["truth_results"]["artifact_review_truth"]["state"])
        self.assertEqual(
            [
                "Structure Integrity",
                "Formatting Consistency",
            ],
            report["artifact_review_coverage"]["covered_baseline_document_quality_dimensions"],
        )
        self.assertEqual(
            [],
            report["artifact_review_coverage"]["missing_baseline_document_quality_dimensions"],
        )
        self.assertEqual(
            [
                "Structure Integrity",
                "Formatting Consistency",
            ],
            report["frozen_requirement_sections"]["baseline_document_quality_dimensions"],
        )

    def test_runtime_delivery_acceptance_requires_manual_review_when_code_task_tdd_evidence_is_missing(self) -> None:
        requirements = [
            "Record failing-first evidence for the changed behavior before implementation or defect correction.",
            "Record the green rerun that proves the targeted behavior passed after implementation.",
        ]
        session_root = self._build_session(
            code_task_tdd_evidence_requirements=requirements,
        )
        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("MANUAL_REVIEW_REQUIRED", report["summary"]["gate_result"])
        self.assertFalse(report["summary"]["completion_language_allowed"])
        self.assertEqual("manual_review_required", report["truth_results"]["code_task_tdd_evidence_truth"]["state"])
        self.assertEqual("manual_review_required", report["truth_results"]["product_acceptance_truth"]["state"])
        self.assertEqual(
            requirements,
            report["frozen_requirement_sections"]["code_task_tdd_evidence_requirements"],
        )

    def test_runtime_delivery_acceptance_requires_red_and_green_phase_evidence_for_code_tasks(self) -> None:
        requirements = [
            "Record failing-first evidence for the changed behavior before implementation or defect correction.",
            "Record the green rerun that proves the targeted behavior passed after implementation.",
        ]
        session_root = self._build_session(
            code_task_tdd_evidence_requirements=requirements,
            phase_execute_tdd_evidence={
                "status": "passing",
                "evidence_paths": [
                    "/tmp/pytest-tdd-evidence.md"
                ],
                "covered_code_task_tdd_evidence_requirements": requirements,
                "green_phase_evidence_paths": [
                    "/tmp/pytest-tdd-green.txt"
                ],
                "notes": "Recorded only the green phase and omitted the failing-first evidence.",
            },
        )
        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("MANUAL_REVIEW_REQUIRED", report["summary"]["gate_result"])
        self.assertEqual("manual_review_required", report["truth_results"]["code_task_tdd_evidence_truth"]["state"])
        self.assertEqual(
            [],
            report["tdd_evidence_coverage"]["red_phase_evidence_paths"],
        )
        self.assertEqual(
            ["/tmp/pytest-tdd-green.txt"],
            report["tdd_evidence_coverage"]["green_phase_evidence_paths"],
        )

    def test_runtime_delivery_acceptance_passes_when_code_task_tdd_evidence_is_recorded(self) -> None:
        requirements = [
            "Record failing-first evidence for the changed behavior before implementation or defect correction.",
            "Record the green rerun that proves the targeted behavior passed after implementation.",
            "Map the changed behavior to targeted verification evidence; generic suite success alone is insufficient.",
        ]
        session_root = self._build_session(
            code_task_tdd_evidence_requirements=requirements,
            phase_execute_tdd_evidence={
                "status": "passing",
                "evidence_paths": [
                    "/tmp/pytest-tdd-evidence.md"
                ],
                "red_phase_evidence_paths": [
                    "/tmp/pytest-tdd-red.txt"
                ],
                "green_phase_evidence_paths": [
                    "/tmp/pytest-tdd-green.txt"
                ],
                "covered_code_task_tdd_evidence_requirements": requirements,
                "notes": "Captured red/green proof for the targeted behavior.",
            },
        )
        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("PASS", report["summary"]["gate_result"])
        self.assertTrue(report["summary"]["completion_language_allowed"])
        self.assertEqual("passing", report["truth_results"]["code_task_tdd_evidence_truth"]["state"])
        self.assertEqual(
            requirements,
            report["tdd_evidence_coverage"]["covered_code_task_tdd_evidence_requirements"],
        )
        self.assertEqual(
            [],
            report["tdd_evidence_coverage"]["missing_code_task_tdd_evidence_requirements"],
        )

    def test_runtime_delivery_acceptance_requires_full_tdd_evidence_when_exception_is_recorded(self) -> None:
        requirements = [
            "Record failing-first evidence for the changed behavior before implementation or defect correction.",
        ]
        exceptions = [
            "A bounded hotfix exception was approved because failing-first replay would have required production-state mutation."
        ]
        session_root = self._build_session(
            code_task_tdd_evidence_requirements=requirements,
            code_task_tdd_exceptions=exceptions,
            phase_execute_tdd_evidence={
                "status": "passing",
                "evidence_paths": [
                    "/tmp/pytest-tdd-exception.md"
                ],
                "covered_code_task_tdd_exceptions": exceptions,
                "notes": "Recorded the approved exception and bounded fallback evidence.",
            },
        )
        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("MANUAL_REVIEW_REQUIRED", report["summary"]["gate_result"])
        self.assertEqual("manual_review_required", report["truth_results"]["code_task_tdd_evidence_truth"]["state"])
        self.assertEqual(requirements, report["tdd_evidence_coverage"]["missing_code_task_tdd_evidence_requirements"])
        self.assertEqual([], report["tdd_evidence_coverage"]["red_phase_evidence_paths"])
        self.assertEqual([], report["tdd_evidence_coverage"]["green_phase_evidence_paths"])

    def test_runtime_delivery_acceptance_passes_when_code_task_tdd_exception_and_required_evidence_are_recorded(self) -> None:
        requirements = [
            "Record failing-first evidence for the changed behavior before implementation or defect correction.",
        ]
        exceptions = [
            "A bounded hotfix exception was approved because failing-first replay would have required production-state mutation."
        ]
        session_root = self._build_session(
            code_task_tdd_evidence_requirements=requirements,
            code_task_tdd_exceptions=exceptions,
            phase_execute_tdd_evidence={
                "status": "passing",
                "evidence_paths": [
                    "/tmp/pytest-tdd-exception.md"
                ],
                "covered_code_task_tdd_evidence_requirements": requirements,
                "covered_code_task_tdd_exceptions": exceptions,
                "red_phase_evidence_paths": [
                    "/tmp/pytest-tdd-red.txt"
                ],
                "green_phase_evidence_paths": [
                    "/tmp/pytest-tdd-green.txt"
                ],
                "notes": "Recorded the approved exception with requirement and red/green evidence coverage.",
            },
        )
        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("PASS", report["summary"]["gate_result"])
        self.assertEqual("passing", report["truth_results"]["code_task_tdd_evidence_truth"]["state"])
        self.assertEqual(
            exceptions,
            report["tdd_evidence_coverage"]["covered_code_task_tdd_exceptions"],
        )
        self.assertEqual(
            [],
            report["tdd_evidence_coverage"]["missing_code_task_tdd_exceptions"],
        )

    def test_runtime_delivery_acceptance_passes_when_artifact_review_evidence_is_recorded(self) -> None:
        session_root = self._build_session(
            artifact_review_requirements=[
                "Inspect the final deliverable directly and confirm the primary CTA provides visible feedback."
            ],
            task_specific_acceptance_extensions=[
                "The CTA should show a loading state before the success message."
            ],
            research_augmentation_sources=[
                "NN/g feedback visibility heuristics"
            ],
            phase_execute_artifact_review={
                "status": "passing",
                "evidence_paths": [
                    "/tmp/pytest-artifact-review-notes.md"
                ],
                "covered_task_specific_acceptance_extensions": [
                    "The CTA should show a loading state before the success message."
                ],
                "considered_research_augmentation_sources": [
                    "NN/g feedback visibility heuristics"
                ],
                "notes": "Reviewed final artifact against frozen task-specific acceptance.",
            },
        )
        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("PASS", report["summary"]["gate_result"])
        self.assertTrue(report["summary"]["completion_language_allowed"])
        self.assertEqual("passing", report["truth_results"]["artifact_review_truth"]["state"])
        self.assertEqual("passing", report["truth_results"]["product_acceptance_truth"]["state"])
        self.assertEqual(
            ["The CTA should show a loading state before the success message."],
            report["frozen_requirement_sections"]["task_specific_acceptance_extensions"],
        )
        self.assertEqual(
            ["NN/g feedback visibility heuristics"],
            report["frozen_requirement_sections"]["research_augmentation_sources"],
        )

    def test_runtime_delivery_acceptance_requires_task_specific_coverage_when_extensions_are_frozen(self) -> None:
        session_root = self._build_session(
            artifact_review_requirements=[
                "Inspect the final deliverable directly and confirm the primary CTA provides visible feedback."
            ],
            task_specific_acceptance_extensions=[
                "The CTA should show a loading state before the success message."
            ],
            phase_execute_artifact_review={
                "status": "passing",
                "evidence_paths": [
                    "/tmp/pytest-artifact-review-notes.md"
                ],
                "notes": "Reviewed the artifact, but did not record extension coverage.",
            },
        )
        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("MANUAL_REVIEW_REQUIRED", report["summary"]["gate_result"])
        self.assertEqual("manual_review_required", report["truth_results"]["artifact_review_truth"]["state"])
        self.assertEqual(
            ["The CTA should show a loading state before the success message."],
            report["artifact_review_coverage"]["missing_task_specific_acceptance_extensions"],
        )

    def test_runtime_delivery_acceptance_requires_ui_baseline_coverage_when_dimensions_are_frozen(self) -> None:
        session_root = self._build_session(
            artifact_review_requirements=[
                "Inspect the final deliverable directly and confirm the primary CTA provides visible feedback."
            ],
            baseline_ui_quality_dimensions=[
                "Structure and visual hierarchy",
                "Interaction feedback and affordances",
            ],
            phase_execute_artifact_review={
                "status": "passing",
                "evidence_paths": [
                    "/tmp/pytest-artifact-review-notes.md"
                ],
                "notes": "Reviewed the artifact, but did not map frozen UI baseline dimensions.",
            },
        )
        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("MANUAL_REVIEW_REQUIRED", report["summary"]["gate_result"])
        self.assertEqual("manual_review_required", report["truth_results"]["artifact_review_truth"]["state"])
        self.assertEqual(
            [
                "Structure and visual hierarchy",
                "Interaction feedback and affordances",
            ],
            report["artifact_review_coverage"]["missing_baseline_ui_quality_dimensions"],
        )

    def test_runtime_delivery_acceptance_passes_when_ui_baseline_coverage_is_explicit(self) -> None:
        session_root = self._build_session(
            artifact_review_requirements=[
                "Inspect the final deliverable directly and confirm the primary CTA provides visible feedback."
            ],
            baseline_ui_quality_dimensions=[
                "Structure and visual hierarchy",
                "Interaction feedback and affordances",
            ],
            phase_execute_artifact_review={
                "status": "passing",
                "evidence_paths": [
                    "/tmp/pytest-artifact-review-notes.md"
                ],
                "covered_baseline_ui_quality_dimensions": [
                    "Structure and visual hierarchy",
                    "Interaction feedback and affordances",
                ],
                "notes": "Reviewed the artifact against frozen UI baseline dimensions.",
            },
        )
        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("PASS", report["summary"]["gate_result"])
        self.assertTrue(report["summary"]["completion_language_allowed"])
        self.assertEqual("passing", report["truth_results"]["artifact_review_truth"]["state"])
        self.assertEqual(
            [
                "Structure and visual hierarchy",
                "Interaction feedback and affordances",
            ],
            report["artifact_review_coverage"]["covered_baseline_ui_quality_dimensions"],
        )
        self.assertEqual(
            [],
            report["artifact_review_coverage"]["missing_baseline_ui_quality_dimensions"],
        )
        self.assertEqual(
            [
                "Structure and visual hierarchy",
                "Interaction feedback and affordances",
            ],
            report["frozen_requirement_sections"]["baseline_ui_quality_dimensions"],
        )

    def test_runtime_delivery_acceptance_requires_research_source_consideration_when_sources_are_frozen(self) -> None:
        session_root = self._build_session(
            artifact_review_requirements=[
                "Inspect the final deliverable directly and confirm the primary CTA provides visible feedback."
            ],
            research_augmentation_sources=[
                "NN/g feedback visibility heuristics"
            ],
            phase_execute_artifact_review={
                "status": "passing",
                "evidence_paths": [
                    "/tmp/pytest-artifact-review-notes.md"
                ],
                "notes": "Reviewed the artifact, but did not record research-source consideration.",
            },
        )
        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("MANUAL_REVIEW_REQUIRED", report["summary"]["gate_result"])
        self.assertEqual("manual_review_required", report["truth_results"]["artifact_review_truth"]["state"])
        self.assertEqual(
            ["NN/g feedback visibility heuristics"],
            report["artifact_review_coverage"]["missing_research_augmentation_sources"],
        )

    def test_runtime_delivery_acceptance_reports_residual_risks_for_unresolved_ui_task_and_research_reviews(self) -> None:
        session_root = self._build_session(
            baseline_ui_quality_dimensions=[
                "Structure and visual hierarchy",
                "Interaction feedback and affordances",
            ],
            task_specific_acceptance_extensions=[
                "The CTA should show a loading state before the success message."
            ],
            research_augmentation_sources=[
                "NN/g feedback visibility heuristics"
            ],
            phase_execute_artifact_review={
                "status": "passing",
                "evidence_paths": [
                    "/tmp/pytest-artifact-review-notes.md"
                ],
                "notes": "Reviewed artifact, but did not map frozen review dimensions.",
            },
        )
        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("MANUAL_REVIEW_REQUIRED", report["summary"]["gate_result"])
        self.assertEqual("manual_review_required", report["truth_results"]["artifact_review_truth"]["state"])
        self.assertIn("Frozen baseline UI quality dimensions remain unresolved.", report["residual_risks"])
        self.assertIn("Frozen task-specific acceptance extensions remain unresolved.", report["residual_risks"])
        self.assertIn("Frozen research augmentation sources remain unresolved.", report["residual_risks"])

    def test_runtime_delivery_acceptance_accepts_sidecar_artifact_review_evidence(self) -> None:
        session_root = self._build_session(
            artifact_review_requirements=[
                "Inspect the final document artifact directly and confirm the formatting remains intact."
            ],
            sidecar_artifact_review={
                "status": "passing",
                "evidence_paths": [
                    "/tmp/pytest-sidecar-artifact-review.md"
                ],
                "notes": "Sidecar review confirmed the final artifact formatting remained intact.",
            },
        )
        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("PASS", report["summary"]["gate_result"])
        self.assertTrue(report["summary"]["completion_language_allowed"])
        self.assertEqual("passing", report["truth_results"]["artifact_review_truth"]["state"])

    def test_runtime_delivery_acceptance_rejects_explicit_artifact_review_paths_outside_session_root(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as handle:
            json.dump(
                {
                    "status": "passing",
                    "evidence_paths": ["/tmp/pytest-explicit-artifact-review.md"],
                },
                handle,
            )
            explicit_path = handle.name
        self.addCleanup(lambda: Path(explicit_path).unlink(missing_ok=True))

        session_root = self._build_session(
            artifact_review_requirements=[
                "Inspect the final document artifact directly and confirm the formatting remains intact."
            ],
            artifact_review_path=explicit_path,
        )
        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("MANUAL_REVIEW_REQUIRED", report["summary"]["gate_result"])
        self.assertEqual("manual_review_required", report["truth_results"]["artifact_review_truth"]["state"])
        self.assertNotIn(explicit_path, report["truth_results"]["artifact_review_truth"]["evidence"])

    def test_runtime_delivery_acceptance_requires_requirements_and_red_green_when_exception_is_recorded(self) -> None:
        requirements = [
            "Record failing-first evidence for the changed behavior before implementation or defect correction.",
        ]
        exceptions = [
            "A bounded hotfix exception was approved because failing-first replay would have required production-state mutation."
        ]
        session_root = self._build_session(
            code_task_tdd_evidence_requirements=requirements,
            code_task_tdd_exceptions=exceptions,
            phase_execute_tdd_evidence={
                "status": "passing",
                "evidence_paths": [
                    "/tmp/pytest-tdd-exception.md"
                ],
                "covered_code_task_tdd_exceptions": exceptions,
                "notes": "Recorded the approved exception but skipped the remaining TDD proof obligations.",
            },
        )
        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("MANUAL_REVIEW_REQUIRED", report["summary"]["gate_result"])
        self.assertEqual("manual_review_required", report["truth_results"]["code_task_tdd_evidence_truth"]["state"])
        self.assertEqual(requirements, report["tdd_evidence_coverage"]["missing_code_task_tdd_evidence_requirements"])
        self.assertEqual([], report["tdd_evidence_coverage"]["red_phase_evidence_paths"])
        self.assertEqual([], report["tdd_evidence_coverage"]["green_phase_evidence_paths"])

    def test_runtime_delivery_acceptance_surfaces_specific_residual_risks_for_unresolved_artifact_review_sources(self) -> None:
        session_root = self._build_session(
            artifact_review_requirements=[
                "Inspect the final deliverable directly and confirm the primary CTA provides visible feedback."
            ],
            baseline_ui_quality_dimensions=[
                "Structure and visual hierarchy",
            ],
            task_specific_acceptance_extensions=[
                "The CTA should show a loading state before the success message."
            ],
            research_augmentation_sources=[
                "NN/g feedback visibility heuristics",
            ],
            phase_execute_artifact_review={
                "status": "passing",
                "evidence_paths": [
                    "/tmp/pytest-artifact-review-notes.md"
                ],
                "notes": "Reviewed the artifact, but did not record the frozen source coverage.",
            },
        )
        report = evaluate(REPO_ROOT, session_root)

        self.assertIn("Frozen baseline UI quality dimensions remain unresolved.", report["residual_risks"])
        self.assertIn("Frozen task-specific acceptance extensions remain unresolved.", report["residual_risks"])
        self.assertIn("Frozen research augmentation sources remain unresolved.", report["residual_risks"])

    def test_runtime_delivery_acceptance_rejects_explicit_payload_paths_outside_session_root(self) -> None:
        tdd_requirements = [
            "Record failing-first evidence for the changed behavior before implementation or defect correction.",
        ]
        with tempfile.TemporaryDirectory() as tempdir:
            outside_root = Path(tempdir)
            artifact_payload_path = outside_root / "outside-artifact-review.json"
            tdd_payload_path = outside_root / "outside-tdd-evidence.json"
            write_json(
                artifact_payload_path,
                {
                    "status": "passing",
                    "evidence_paths": ["/tmp/outside-artifact-review.md"],
                },
            )
            write_json(
                tdd_payload_path,
                {
                    "status": "passing",
                    "evidence_paths": ["/tmp/outside-tdd-evidence.md"],
                    "covered_code_task_tdd_evidence_requirements": tdd_requirements,
                    "red_phase_evidence_paths": ["/tmp/outside-tdd-red.txt"],
                    "green_phase_evidence_paths": ["/tmp/outside-tdd-green.txt"],
                },
            )
            session_root = self._build_session(
                artifact_review_requirements=[
                    "Inspect the final artifact directly and confirm required controls are present."
                ],
                code_task_tdd_evidence_requirements=tdd_requirements,
                artifact_review_path=str(artifact_payload_path),
                tdd_evidence_path=str(tdd_payload_path),
            )
            self.assertTrue(artifact_payload_path.exists())
            self.assertTrue(tdd_payload_path.exists())

            report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("MANUAL_REVIEW_REQUIRED", report["summary"]["gate_result"])
        self.assertEqual("manual_review_required", report["truth_results"]["artifact_review_truth"]["state"])
        self.assertEqual("manual_review_required", report["truth_results"]["code_task_tdd_evidence_truth"]["state"])
        self.assertEqual("", report["execution_context"]["artifact_review_source_path"])
        self.assertEqual("", report["execution_context"]["tdd_evidence_source_path"])

    def test_runtime_delivery_acceptance_rejects_explicit_specialist_decision_paths_outside_session_root(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            outside_root = Path(tempdir)
            specialist_decision_payload_path = outside_root / "outside-specialist-decision.json"
            write_json(
                specialist_decision_payload_path,
                {
                    "decision_state": "no_specialist_recommendations",
                    "resolution_mode": "repo_asset_fallback",
                    "repo_asset_fallback": {
                        "used": True,
                        "asset_paths": [
                            "outputs/agent-runs/2026-04-14-scheme-a-clean397-paper-report/scripts/plot_style.py"
                        ],
                        "reason": "Reuse the repo plotting asset.",
                        "legal_basis": "Repo-local plotting asset already present inside governed workspace outputs.",
                        "traceability_basis": [
                            "outputs/agent-runs/2026-04-14-scheme-a-clean397-paper-report/scripts/plot_style.py"
                        ],
                    },
                },
            )
            session_root = self._build_session(
                specialist_decision_path=str(specialist_decision_payload_path),
                omit_default_specialist_decision=True,
            )
            self.assertTrue(specialist_decision_payload_path.exists())

            report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("MANUAL_REVIEW_REQUIRED", report["summary"]["gate_result"])
        self.assertEqual("manual_review_required", report["truth_results"]["specialist_decision_truth"]["state"])
        self.assertEqual("", report["execution_context"]["specialist_decision_source_path"])
        self.assertNotIn(
            str(specialist_decision_payload_path),
            report["truth_results"]["specialist_decision_truth"]["evidence"],
        )

    def test_runtime_delivery_acceptance_report_surfaces_frozen_sections_and_coverage(self) -> None:
        session_root = self._build_session(
            artifact_review_requirements=[
                "Inspect the final deliverable directly and confirm the primary CTA provides visible feedback."
            ],
            code_task_tdd_evidence_requirements=[
                "Record failing-first evidence for the changed behavior before implementation or defect correction.",
                "Record the green rerun that proves the targeted behavior passed after implementation.",
            ],
            baseline_document_quality_dimensions=[
                "Structure Integrity",
                "Formatting Consistency",
            ],
            task_specific_acceptance_extensions=[
                "The CTA should show a loading state before the success message."
            ],
            baseline_ui_quality_dimensions=[
                "Structure and visual hierarchy",
                "Interaction feedback and affordances",
            ],
            research_augmentation_sources=[
                "NN/g feedback visibility heuristics"
            ],
            phase_execute_artifact_review={
                "status": "passing",
                "evidence_paths": [
                    "/tmp/pytest-artifact-review-notes.md"
                ],
                "covered_task_specific_acceptance_extensions": [
                    "The CTA should show a loading state before the success message."
                ],
                "covered_baseline_document_quality_dimensions": [
                    "Structure Integrity",
                    "Formatting Consistency",
                ],
                "covered_baseline_ui_quality_dimensions": [
                    "Structure and visual hierarchy",
                    "Interaction feedback and affordances",
                ],
                "considered_research_augmentation_sources": [
                    "NN/g feedback visibility heuristics"
                ],
                "notes": "Reviewed final artifact against frozen task-specific acceptance.",
            },
            phase_execute_tdd_evidence={
                "status": "passing",
                "evidence_paths": [
                    "/tmp/pytest-tdd-evidence.md"
                ],
                "red_phase_evidence_paths": [
                    "/tmp/pytest-tdd-red.txt"
                ],
                "green_phase_evidence_paths": [
                    "/tmp/pytest-tdd-green.txt"
                ],
                "covered_code_task_tdd_evidence_requirements": [
                    "Record failing-first evidence for the changed behavior before implementation or defect correction.",
                    "Record the green rerun that proves the targeted behavior passed after implementation.",
                ],
                "notes": "Captured red/green TDD evidence for the code change.",
            },
        )
        artifact = evaluate(REPO_ROOT, session_root)

        with tempfile.TemporaryDirectory() as tempdir:
            output_root = Path(tempdir)
            write_artifacts(artifact, output_root)
            md_text = (output_root / "delivery-acceptance-report.md").read_text(encoding="utf-8")
            self.assertIn("Frozen Baseline Document Quality Dimensions", md_text)
            self.assertIn("Frozen Code Task TDD Evidence Requirements", md_text)
            self.assertIn("Frozen Baseline UI Quality Dimensions", md_text)
            self.assertIn("Frozen Task-Specific Acceptance Extensions", md_text)
            self.assertIn("Frozen Research Augmentation Sources", md_text)
            self.assertIn("Code Task TDD Evidence Coverage", md_text)
            self.assertIn("Artifact Review Coverage", md_text)
            self.assertIn("Covered baseline document quality dimension: Structure Integrity", md_text)
            self.assertIn("Covered code-task TDD evidence requirement: Record failing-first evidence for the changed behavior before implementation or defect correction.", md_text)
            self.assertIn("Covered baseline UI quality dimension: Structure and visual hierarchy", md_text)
            self.assertIn("NN/g feedback visibility heuristics", md_text)
