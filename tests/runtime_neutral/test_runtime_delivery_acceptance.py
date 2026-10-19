from __future__ import annotations

import importlib.util
import hashlib
import json
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
    def test_phase_cleanup_runs_delivery_acceptance_before_any_cleanup_action(self) -> None:
        source = (REPO_ROOT / "scripts" / "runtime" / "Invoke-PhaseCleanup.ps1").read_text(
            encoding="utf-8"
        )

        acceptance_index = source.index("runtime_delivery_acceptance.py")
        governance_cleanup_index = source.index("phase-end-cleanup.ps1")
        process_cleanup_index = source.index("Invoke-NodeZombieCleanup.ps1")

        self.assertLess(acceptance_index, governance_cleanup_index)
        self.assertLess(acceptance_index, process_cleanup_index)
        self.assertIn("delivery_acceptance_not_passed", source)

    def _build_session(
        self,
        *,
        manual_spot_checks: list[str] | None = None,
        artifact_review_requirements: list[str] | None = None,
        code_task_tdd_evidence_requirements: list[str] | None = None,
        phase_execute_artifact_review: dict[str, object] | None = None,
        phase_execute_tdd_evidence: dict[str, object] | None = None,
        artifact_review_path: str | None = None,
        tdd_evidence_path: str | None = None,
        module_assignments: dict[str, object] | None = None,
        module_execution: dict[str, object] | None = None,
        module_execution_tdd_evidence: dict[str, object] | None = None,
        module_work_plan: dict[str, object] | None = None,
        skill_routing: dict[str, object] | None = None,
        include_module_truth: bool = True,
        session_name: str = "pytest-runtime-delivery",
    ) -> Path:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        root = Path(tempdir.name)
        session_root = root / "outputs" / "runtime" / "vibe-sessions" / session_name
        session_root.mkdir(parents=True, exist_ok=True)

        requirement_doc_path = root / "docs" / "requirements" / "pytest.md"
        execution_plan_path = root / "docs" / "plans" / "pytest-plan.md"
        execution_manifest_path = session_root / "execution-manifest.json"
        runtime_input_packet_path = session_root / "runtime-input-packet.json"

        requirement_lines = [
            "# Pytest Delivery Contract",
            "",
            "## Product Acceptance Criteria",
            "- Deliverable behavior matches the frozen requirement.",
            "",
            "## Manual Spot Checks",
        ]
        if manual_spot_checks:
            requirement_lines.extend([f"- {item}" for item in manual_spot_checks])
        else:
            requirement_lines.append("- None required beyond automated verification for this task.")
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
        write_text(requirement_doc_path, "\n".join(requirement_lines) + "\n")
        write_text(
            execution_plan_path,
            "# Pytest Plan\n\n## Delivery Acceptance Plan\n- Emit the runtime delivery report.\n",
        )

        execution_manifest_payload = {
            "run_id": "pytest-runtime-delivery-run",
            "status": "completed",
            "governance_scope": "root",
            "completed_unit_count": 3,
            "failed_unit_count": 0,
            "blocked_unit_count": 0,
        }
        write_json(execution_manifest_path, execution_manifest_payload)

        runtime_input_packet_payload: dict[str, object] = {
            "authority_flags": {
                "explicit_runtime_skill": "vibe",
            }
        }
        if module_assignments is not None:
            runtime_input_packet_payload["module_assignments"] = module_assignments
        if skill_routing is not None:
            runtime_input_packet_payload["skill_routing"] = skill_routing
        if include_module_truth and module_execution is None:
            module_execution = {
                "schema_version": "module_execution_v1",
                "source_run_id": "pytest-runtime-delivery-run",
                "units": [
                    {
                        "unit_id": "delivery--agent--owner",
                        "module_id": "delivery",
                        "skill_id": None,
                        "role": "owner",
                        "state": "completed",
                        "result_summary": "Completed the direct delivery module.",
                        "evidence_paths": [],
                    }
                ],
                "modules": [
                    {
                        "module_id": "delivery",
                        "required": True,
                        "state": "completed",
                        "criterion_results": [
                            {"criterion_id": "delivery-result", "state": "passing"}
                        ],
                    }
                ],
            }
        if module_execution is not None:
            if module_execution_tdd_evidence is not None:
                module_execution["tdd_evidence"] = module_execution_tdd_evidence
            module_work_plan_path = session_root / "module-work-plan.json"
            planned_modules = []
            for module in module_execution.get("modules", []):
                planned_module = dict(module)
                planned_module["acceptance_criteria"] = [
                    {
                        "criterion_id": result.get("criterion_id"),
                        "description": "Verify the planned module result.",
                        "verification_mode": "automated",
                    }
                    for result in module.get("criterion_results", [])
                    if isinstance(result, dict) and result.get("criterion_id")
                ]
                if not planned_module["acceptance_criteria"]:
                    planned_module["acceptance_criteria"] = [
                        {
                            "criterion_id": f"{planned_module.get('module_id', 'module')}-result",
                            "description": "Verify the planned module result.",
                            "verification_mode": "automated",
                        }
                    ]
                planned_modules.append(planned_module)
            write_json(
                module_work_plan_path,
                module_work_plan or {
                    "schema_version": "module_work_plan_v1",
                    "source_run_id": "pytest-runtime-delivery-run",
                    "modules": planned_modules,
                    "work_units": module_execution.get("units", []),
                },
            )
            module_execution.setdefault(
                "module_work_plan_digest",
                hashlib.sha256(module_work_plan_path.read_bytes()).hexdigest(),
            )
            write_json(session_root / "module-execution.json", module_execution)
        write_json(runtime_input_packet_path, runtime_input_packet_payload)

        phase_execute_payload: dict[str, object] = {
            "run_id": "pytest-runtime-delivery-run",
            "requirement_doc_path": str(requirement_doc_path),
            "execution_plan_path": str(execution_plan_path),
            "execution_manifest_path": str(execution_manifest_path),
            "runtime_input_packet_path": str(runtime_input_packet_path),
            "completion_claim_allowed": True,
            "artifact_review": phase_execute_artifact_review or {},
            "tdd_evidence": phase_execute_tdd_evidence or {},
        }
        if artifact_review_path:
            phase_execute_payload["artifact_review_path"] = artifact_review_path
        if tdd_evidence_path:
            phase_execute_payload["tdd_evidence_path"] = tdd_evidence_path
        write_json(session_root / "phase-execute.json", phase_execute_payload)
        write_json(session_root / "cleanup-receipt.json", {"cleanup_mode": "bounded_cleanup_executed"})
        return session_root

    def test_delivery_acceptance_passes_for_clean_root_run(self) -> None:
        session_root = self._build_session()

        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("PASS", report["summary"]["gate_result"])
        self.assertTrue(report["summary"]["completion_language_allowed"])
        self.assertEqual("passing", report["truth_results"]["product_acceptance_truth"]["state"])
        self.assertNotIn("specialist_decision_truth", report["truth_results"])
        self.assertNotIn("specialist_disclosure_truth", report["truth_results"])

    def test_retired_specialist_evidence_cannot_replace_module_execution_truth(self) -> None:
        session_root = self._build_session(include_module_truth=False)
        execute_receipt_path = session_root / "phase-execute.json"
        execute_receipt = json.loads(execute_receipt_path.read_text(encoding="utf-8"))
        execute_receipt["specialist_decision"] = {
            "decision_state": "no_specialist_recommendations",
            "resolution_mode": "no_specialist_needed",
        }
        execute_receipt["specialist_user_disclosure"] = {
            "scope": "module_skill_dispatch_only",
            "timing": "before_execution",
            "path_source": "skill_md_path",
            "routed_skills": [],
        }
        write_json(execute_receipt_path, execute_receipt)

        report = evaluate(REPO_ROOT, session_root)
        serialized_report = json.dumps(report, ensure_ascii=False)

        self.assertEqual("FAIL", report["summary"]["gate_result"])
        self.assertEqual("failing", report["truth_results"]["module_acceptance_truth"]["state"])
        self.assertNotIn("specialist_decision", serialized_report)
        self.assertNotIn("specialist_user_disclosure", serialized_report)
        self.assertNotIn("skill_execution", serialized_report)

    def test_delivery_acceptance_blocks_task_while_required_module_is_working(self) -> None:
        session_root = self._build_session(
            module_execution={
                "schema_version": "module_execution_v1",
                "source_run_id": "pytest-runtime-delivery-run",
                "units": [
                    {
                        "unit_id": "module-a--owner-a--owner",
                        "module_id": "module-a",
                        "skill_id": "owner-a",
                        "role": "owner",
                        "state": "working",
                        "evidence_paths": [],
                    }
                ],
                "modules": [
                    {
                        "module_id": "module-a",
                        "required": True,
                        "state": "working",
                        "criterion_results": [],
                    }
                ],
            }
        )

        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("MANUAL_REVIEW_REQUIRED", report["summary"]["gate_result"])
        self.assertFalse(report["summary"]["completion_language_allowed"])
        self.assertEqual(
            "manual_review_required",
            report["truth_results"]["module_acceptance_truth"]["state"],
        )
        self.assertEqual([], report["completed_module_work"])

    def test_delivery_acceptance_passes_when_required_module_is_completed(self) -> None:
        session_root = self._build_session(
            module_execution={
                "schema_version": "module_execution_v1",
                "source_run_id": "pytest-runtime-delivery-run",
                "units": [
                    {
                        "unit_id": "module-a--owner-a--owner",
                        "module_id": "module-a",
                        "skill_id": "owner-a",
                        "role": "owner",
                        "state": "completed",
                        "result_summary": "Produced the module result.",
                        "evidence_paths": ["module-a-result.txt"],
                    }
                ],
                "modules": [
                    {
                        "module_id": "module-a",
                        "required": True,
                        "state": "completed",
                        "criterion_results": [
                            {"criterion_id": "module-a-result", "state": "passing"}
                        ],
                    }
                ],
            }
        )
        write_text(session_root / "module-a-result.txt", "module result\n")

        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("PASS", report["summary"]["gate_result"])
        self.assertEqual("passing", report["truth_results"]["module_acceptance_truth"]["state"])
        self.assertEqual(
            [
                {
                    "skill_id": "owner-a",
                    "unit_id": "module-a--owner-a--owner",
                    "module_id": "module-a",
                }
            ],
            report["completed_module_work"],
        )
        self.assertNotIn("specialist_decision_truth", report["truth_results"])
        self.assertNotIn("specialist_disclosure_truth", report["truth_results"])

    def test_delivery_acceptance_rejects_required_module_without_acceptance_criteria(self) -> None:
        module_execution = {
            "schema_version": "module_execution_v1",
            "source_run_id": "pytest-runtime-delivery-run",
            "units": [
                {
                    "unit_id": "module-a--owner-a--owner",
                    "module_id": "module-a",
                    "skill_id": "owner-a",
                    "role": "owner",
                    "state": "completed",
                    "result_summary": "Produced the module result.",
                    "evidence_paths": ["module-a-result.txt"],
                }
            ],
            "modules": [
                {
                    "module_id": "module-a",
                    "required": True,
                    "state": "completed",
                    "criterion_results": [],
                }
            ],
        }
        session_root = self._build_session(
            module_execution=module_execution,
            module_work_plan={
                "schema_version": "module_work_plan_v1",
                "source_run_id": "pytest-runtime-delivery-run",
                "modules": [
                    {
                        "module_id": "module-a",
                        "required": True,
                        "execution_mode": "skill_assigned",
                        "acceptance_criteria": [],
                    }
                ],
                "work_units": module_execution["units"],
            },
        )
        write_text(session_root / "module-a-result.txt", "module result\n")

        with self.assertRaisesRegex(ValueError, "must include acceptance_criteria"):
            evaluate(REPO_ROOT, session_root)

    def test_delivery_acceptance_rejects_non_object_acceptance_criteria(self) -> None:
        module_execution = {
            "schema_version": "module_execution_v1",
            "source_run_id": "pytest-runtime-delivery-run",
            "units": [],
            "modules": [],
        }
        session_root = self._build_session(
            module_execution=module_execution,
            module_work_plan={
                "schema_version": "module_work_plan_v1",
                "source_run_id": "pytest-runtime-delivery-run",
                "modules": [
                    {
                        "module_id": "module-a",
                        "required": True,
                        "execution_mode": "agent_direct",
                        "acceptance_criteria": ["The result exists."],
                    }
                ],
                "work_units": [],
            },
        )

        with self.assertRaisesRegex(ValueError, "must contain objects"):
            evaluate(REPO_ROOT, session_root)

    def test_delivery_acceptance_waits_for_each_approved_module_criterion(self) -> None:
        module_execution = {
            "schema_version": "module_execution_v1",
            "source_run_id": "pytest-runtime-delivery-run",
            "units": [
                {
                    "unit_id": "module-a--owner-a--owner",
                    "module_id": "module-a",
                    "skill_id": "owner-a",
                    "role": "owner",
                    "state": "completed",
                    "result_summary": "Produced the module result.",
                    "evidence_paths": ["module-a-result.txt"],
                }
            ],
            "modules": [
                {
                    "module_id": "module-a",
                    "required": True,
                    "state": "completed",
                    "criterion_results": [],
                }
            ],
        }
        session_root = self._build_session(
            module_execution=module_execution,
            module_work_plan={
                "schema_version": "module_work_plan_v1",
                "source_run_id": "pytest-runtime-delivery-run",
                "modules": [
                    {
                        "module_id": "module-a",
                        "required": True,
                        "execution_mode": "skill_assigned",
                        "acceptance_criteria": [
                            {
                                "criterion_id": "human-review",
                                "description": "A person approves the result.",
                                "verification_mode": "manual",
                            }
                        ],
                    }
                ],
                "work_units": module_execution["units"],
            },
        )
        write_text(session_root / "module-a-result.txt", "module result\n")

        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("MANUAL_REVIEW_REQUIRED", report["summary"]["gate_result"])
        self.assertIn(
            "Approved acceptance criteria remain incomplete",
            report["truth_results"]["module_acceptance_truth"]["notes"],
        )

    def test_optional_module_failure_does_not_block_required_module_acceptance(self) -> None:
        session_root = self._build_session(
            module_execution={
                "schema_version": "module_execution_v1",
                "source_run_id": "pytest-runtime-delivery-run",
                "units": [
                    {
                        "unit_id": "required--owner-a--owner",
                        "module_id": "required",
                        "skill_id": "owner-a",
                        "role": "owner",
                        "state": "completed",
                        "result_summary": "Produced the required result.",
                        "evidence_paths": ["required-result.txt"],
                    },
                    {
                        "unit_id": "optional--owner-b--owner",
                        "module_id": "optional",
                        "skill_id": "owner-b",
                        "role": "owner",
                        "state": "failed",
                        "result_summary": "",
                        "evidence_paths": [],
                    },
                ],
                "modules": [
                    {
                        "module_id": "required",
                        "required": True,
                        "state": "completed",
                        "criterion_results": [
                            {"criterion_id": "required-result", "state": "passing"}
                        ],
                    },
                    {
                        "module_id": "optional",
                        "required": False,
                        "state": "failed",
                        "criterion_results": [
                            {"criterion_id": "optional-result", "state": "failing"}
                        ],
                    },
                ],
            }
        )
        write_text(session_root / "required-result.txt", "required result\n")

        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("PASS", report["summary"]["gate_result"])
        self.assertEqual("passing", report["truth_results"]["module_acceptance_truth"]["state"])
        self.assertIn(
            "Optional modules did not complete: optional",
            report["truth_results"]["module_acceptance_truth"]["notes"],
        )

    def test_required_failed_or_blocked_module_is_a_task_failure(self) -> None:
        for module_state in ("failed", "blocked"):
            with self.subTest(module_state=module_state):
                session_root = self._build_session(
                    module_execution={
                        "schema_version": "module_execution_v1",
                        "source_run_id": "pytest-runtime-delivery-run",
                        "units": [],
                        "modules": [
                            {
                                "module_id": "required",
                                "required": True,
                                "state": module_state,
                                "criterion_results": [
                                    {"criterion_id": "required-result", "state": "passing"}
                                ],
                            }
                        ],
                    }
                )

                report = evaluate(REPO_ROOT, session_root)

                self.assertEqual("FAIL", report["summary"]["gate_result"])
                self.assertFalse(report["summary"]["completion_language_allowed"])
                self.assertFalse(report["execution_context"]["completion_claim_allowed"])
                self.assertEqual([], report["completed_module_work"])
                self.assertIn(
                    "Required modules failed or are blocked: required",
                    report["truth_results"]["module_acceptance_truth"]["notes"],
                )

    def test_delivery_acceptance_rejects_module_accepted_without_required_verifier(self) -> None:
        session_root = self._build_session(
            module_execution={
                "schema_version": "module_execution_v1",
                "source_run_id": "pytest-runtime-delivery-run",
                "units": [
                    {
                        "unit_id": "module-a--owner-a--owner",
                        "module_id": "module-a",
                        "skill_id": "owner-a",
                        "role": "owner",
                        "state": "completed",
                        "result_summary": "Produced the primary module result.",
                        "evidence_paths": ["module-a-result.txt"],
                    },
                    {
                        "unit_id": "module-a--verifier-a--verifier",
                        "module_id": "module-a",
                        "skill_id": "verifier-a",
                        "role": "verifier",
                        "state": "working",
                        "result_summary": "",
                        "evidence_paths": [],
                    },
                ],
                "modules": [
                    {
                        "module_id": "module-a",
                        "required": True,
                        "state": "completed",
                        "criterion_results": [
                            {"criterion_id": "module-a-verified", "state": "passing"}
                        ],
                    }
                ],
            }
        )
        write_text(session_root / "module-a-result.txt", "module result\n")

        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("MANUAL_REVIEW_REQUIRED", report["summary"]["gate_result"])
        self.assertIn(
            "required verifier work is incomplete",
            report["truth_results"]["module_acceptance_truth"]["notes"],
        )

    def test_delivery_acceptance_rejects_module_self_accepted_without_owner_evidence(self) -> None:
        session_root = self._build_session(
            module_execution={
                "schema_version": "module_execution_v1",
                "source_run_id": "pytest-runtime-delivery-run",
                "units": [
                    {
                        "unit_id": "module-a--owner-a--owner",
                        "module_id": "module-a",
                        "skill_id": "owner-a",
                        "role": "owner",
                        "state": "completed",
                        "result_summary": "",
                        "evidence_paths": ["missing-result.txt"],
                    }
                ],
                "modules": [
                    {
                        "module_id": "module-a",
                        "required": True,
                        "state": "completed",
                        "criterion_results": [
                            {"criterion_id": "module-a-result", "state": "passing"}
                        ],
                    }
                ],
            }
        )

        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("MANUAL_REVIEW_REQUIRED", report["summary"]["gate_result"])
        notes = report["truth_results"]["module_acceptance_truth"]["notes"]
        self.assertIn("owner work lacks an observable result", notes)
        self.assertIn("module-a", notes)

    def test_delivery_acceptance_rejects_module_with_nonpassing_criterion(self) -> None:
        session_root = self._build_session(
            module_execution={
                "schema_version": "module_execution_v1",
                "source_run_id": "pytest-runtime-delivery-run",
                "units": [
                    {
                        "unit_id": "module-a--owner-a--owner",
                        "module_id": "module-a",
                        "skill_id": "owner-a",
                        "role": "owner",
                        "state": "completed",
                        "result_summary": "Produced the module result.",
                        "evidence_paths": ["module-a-result.txt"],
                    }
                ],
                "modules": [
                    {
                        "module_id": "module-a",
                        "required": True,
                        "state": "completed",
                        "criterion_results": [
                            {"criterion_id": "module-a-result", "state": "failing"}
                        ],
                    }
                ],
            }
        )
        write_text(session_root / "module-a-result.txt", "module result\n")

        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("FAIL", report["summary"]["gate_result"])
        self.assertEqual("failing", report["truth_results"]["module_acceptance_truth"]["state"])

    def test_delivery_acceptance_rejects_module_execution_from_stale_plan(self) -> None:
        session_root = self._build_session(
            module_execution={
                "schema_version": "module_execution_v1",
                "source_run_id": "pytest-runtime-delivery-run",
                "module_work_plan_digest": "0" * 64,
                "units": [],
                "modules": [
                    {
                        "module_id": "module-a",
                        "required": True,
                        "state": "completed",
                        "criterion_results": [
                            {"criterion_id": "module-a-result", "state": "passing"}
                        ],
                    }
                ],
            }
        )

        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("FAIL", report["summary"]["gate_result"])
        self.assertIn(
            "module work plan digest",
            report["truth_results"]["module_acceptance_truth"]["notes"],
        )

    def test_delivery_acceptance_rejects_changed_module_work_binding(self) -> None:
        module_execution = {
            "schema_version": "module_execution_v1",
            "source_run_id": "pytest-runtime-delivery-run",
            "units": [
                {
                    "unit_id": "module-a--owner-a--owner",
                    "module_id": "module-a",
                    "skill_id": "unapproved-skill",
                    "role": "owner",
                    "state": "completed",
                    "result_summary": "Produced the module result.",
                    "evidence_paths": [],
                }
            ],
            "modules": [
                {
                    "module_id": "module-a",
                    "required": True,
                    "state": "completed",
                    "criterion_results": [
                        {"criterion_id": "module-a-result", "state": "passing"}
                    ],
                }
            ],
        }
        session_root = self._build_session(
            module_execution=module_execution,
            module_work_plan={
                "schema_version": "module_work_plan_v1",
                "source_run_id": "pytest-runtime-delivery-run",
                "modules": [
                    {
                        "module_id": "module-a",
                        "required": True,
                        "execution_mode": "skill_assigned",
                        "acceptance_criteria": [
                            {
                                "criterion_id": "module-a-result",
                                "description": "Verify the planned module result.",
                                "verification_mode": "automated",
                            }
                        ],
                    }
                ],
                "work_units": [
                    {
                        "unit_id": "module-a--owner-a--owner",
                        "module_id": "module-a",
                        "skill_id": "owner-a",
                        "role": "owner",
                    }
                ],
            },
        )

        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("FAIL", report["summary"]["gate_result"])
        self.assertEqual([], report["completed_module_work"])
        self.assertIn(
            "work-unit bindings",
            report["truth_results"]["module_acceptance_truth"]["notes"],
        )

    def test_delivery_acceptance_rejects_downgraded_required_module(self) -> None:
        module_execution = {
            "schema_version": "module_execution_v1",
            "source_run_id": "pytest-runtime-delivery-run",
            "units": [
                {
                    "unit_id": "module-a--owner-a--owner",
                    "module_id": "module-a",
                    "skill_id": "owner-a",
                    "role": "owner",
                    "state": "completed",
                    "result_summary": "Produced the module result.",
                    "evidence_paths": [],
                }
            ],
            "modules": [
                {
                    "module_id": "module-a",
                    "required": False,
                    "state": "failed",
                    "criterion_results": [
                        {"criterion_id": "module-a-result", "state": "passing"}
                    ],
                }
            ],
        }
        session_root = self._build_session(
            module_execution=module_execution,
            module_work_plan={
                "schema_version": "module_work_plan_v1",
                "source_run_id": "pytest-runtime-delivery-run",
                "modules": [
                    {
                        "module_id": "module-a",
                        "required": True,
                        "execution_mode": "skill_assigned",
                        "acceptance_criteria": [
                            {
                                "criterion_id": "module-a-result",
                                "description": "Verify the planned module result.",
                                "verification_mode": "automated",
                            }
                        ],
                    }
                ],
                "work_units": module_execution["units"],
            },
        )

        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("FAIL", report["summary"]["gate_result"])
        self.assertIn(
            "module records",
            report["truth_results"]["module_acceptance_truth"]["notes"],
        )

    def test_delivery_acceptance_ignores_retired_route_selected_mirror(self) -> None:
        session_root = self._build_session(
            module_assignments={
                "schema_version": "runtime_module_assignments_v1",
                "source": "agent_skill_organization",
                "unit_count": 0,
                "status": "projected_from_agent_skill_organization",
                "units": [],
            },
            skill_routing={"selected": [{"skill_id": "retired-route-choice"}]},
        )

        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual([], report["completed_module_work"])
        self.assertNotIn("retired-route-choice", json.dumps(report, ensure_ascii=False))

    def test_delivery_acceptance_does_not_fallback_to_retired_manifest_accounting(self) -> None:
        session_root = self._build_session(
            module_assignments={
                "schema_version": "runtime_module_assignments_v1",
                "source": "agent_skill_organization",
                "unit_count": 0,
                "status": "projected_from_agent_skill_organization",
                "units": [],
            },
        )
        execution_manifest_path = session_root / "execution-manifest.json"
        execution_manifest = json.loads(execution_manifest_path.read_text(encoding="utf-8"))
        execution_manifest["specialist_accounting"] = {
            "module_skill_dispatch": [{"skill_id": "retired-manifest-choice"}],
            "module_skill_dispatch_count": 1,
        }
        write_json(execution_manifest_path, execution_manifest)

        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual([], report["completed_module_work"])
        self.assertNotIn("retired-manifest-choice", json.dumps(report, ensure_ascii=False))

    def test_delivery_acceptance_requires_manual_review_when_spot_checks_pending(self) -> None:
        session_root = self._build_session(
            manual_spot_checks=["Open the primary UI flow and confirm the main path works end-to-end."]
        )

        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("MANUAL_REVIEW_REQUIRED", report["summary"]["gate_result"])
        self.assertEqual("manual_actions_pending", report["summary"]["readiness_state"])
        self.assertEqual("manual_review_required", report["truth_results"]["product_acceptance_truth"]["state"])

    def test_delivery_acceptance_requires_tdd_evidence_for_code_tasks(self) -> None:
        requirements = [
            "Record failing-first evidence for the changed behavior before implementation or defect correction.",
            "Record the green rerun that proves the targeted behavior passed after implementation.",
        ]
        session_root = self._build_session(
            code_task_tdd_evidence_requirements=requirements,
        )

        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("MANUAL_REVIEW_REQUIRED", report["summary"]["gate_result"])
        self.assertEqual("manual_review_required", report["truth_results"]["code_task_tdd_evidence_truth"]["state"])
        self.assertEqual(requirements, report["frozen_requirement_sections"]["code_task_tdd_evidence_requirements"])

    def test_delivery_acceptance_reads_tdd_evidence_from_module_execution(self) -> None:
        requirements = [
            "Record failing-first evidence for the changed behavior before implementation or defect correction.",
            "Record the green rerun that proves the targeted behavior passed after implementation.",
        ]
        session_root = self._build_session(
            code_task_tdd_evidence_requirements=requirements,
            module_execution_tdd_evidence={
                "status": "passing",
                "evidence_paths": ["test_pricing.py", "pricing.py"],
                "red_phase_evidence_paths": ["test_pricing.py"],
                "green_phase_evidence_paths": ["test_pricing.py", "pricing.py"],
                "refactor_phase_evidence_paths": [],
                "covered_code_task_tdd_evidence_requirements": requirements,
                "covered_code_task_tdd_exceptions": [],
                "notes": "The same focused command failed before the repair and passed afterward.",
            },
        )

        write_text(session_root / "test_pricing.py", "assert True\n")
        write_text(session_root / "pricing.py", "PRICE = 1\n")
        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("PASS", report["summary"]["gate_result"])
        self.assertEqual(
            str(session_root / "module-execution.json"),
            report["execution_context"]["tdd_evidence_source_path"],
        )
        self.assertFalse((session_root / "tdd-evidence.json").exists())

    def test_delivery_acceptance_rejects_explicit_payload_paths_outside_session_root(self) -> None:
        requirements = [
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
                    "covered_code_task_tdd_evidence_requirements": requirements,
                    "red_phase_evidence_paths": ["/tmp/outside-tdd-red.txt"],
                    "green_phase_evidence_paths": ["/tmp/outside-tdd-green.txt"],
                },
            )
            session_root = self._build_session(
                artifact_review_requirements=[
                    "Inspect the final artifact directly and confirm required controls are present."
                ],
                code_task_tdd_evidence_requirements=requirements,
                artifact_review_path=str(artifact_payload_path),
                tdd_evidence_path=str(tdd_payload_path),
            )

            report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("MANUAL_REVIEW_REQUIRED", report["summary"]["gate_result"])
        self.assertEqual("", report["execution_context"]["artifact_review_source_path"])
        self.assertEqual("", report["execution_context"]["tdd_evidence_source_path"])

    def test_delivery_acceptance_markdown_report_surfaces_frozen_sections_and_coverage(self) -> None:
        requirements = [
            "Record failing-first evidence for the changed behavior before implementation or defect correction.",
            "Record the green rerun that proves the targeted behavior passed after implementation.",
        ]
        session_root = self._build_session(
            artifact_review_requirements=[
                "Inspect the final deliverable directly and confirm the primary CTA provides visible feedback."
            ],
            code_task_tdd_evidence_requirements=requirements,
            phase_execute_artifact_review={
                "status": "passing",
                "evidence_paths": ["/tmp/pytest-artifact-review-notes.md"],
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
                "considered_research_augmentation_sources": ["NN/g feedback visibility heuristics"],
                "notes": "Reviewed final artifact against frozen acceptance coverage.",
            },
            phase_execute_tdd_evidence={
                "status": "passing",
                "evidence_paths": ["/tmp/pytest-tdd-evidence.md"],
                "red_phase_evidence_paths": ["/tmp/pytest-tdd-red.txt"],
                "green_phase_evidence_paths": ["/tmp/pytest-tdd-green.txt"],
                "covered_code_task_tdd_evidence_requirements": requirements,
                "notes": "Captured red/green TDD evidence for the code change.",
            },
            module_execution={
                "schema_version": "module_execution_v1",
                "source_run_id": "pytest-runtime-delivery-run",
                "units": [
                    {
                        "unit_id": "analysis--scanpy--owner",
                        "module_id": "analysis",
                        "skill_id": "scanpy",
                        "role": "owner",
                        "state": "completed",
                        "result_summary": "Completed the planned analysis module.",
                        "evidence_paths": ["scanpy-result.txt"],
                    }
                ],
                "modules": [
                    {
                        "module_id": "analysis",
                        "required": True,
                        "state": "completed",
                        "criterion_results": [
                            {"criterion_id": "analysis-result", "state": "passing"}
                        ],
                    }
                ],
            },
        )
        write_text(session_root / "scanpy-result.txt", "analysis result\n")
        artifact = evaluate(REPO_ROOT, session_root)

        with tempfile.TemporaryDirectory() as tempdir:
            output_root = Path(tempdir)
            write_artifacts(artifact, output_root)
            md_text = (output_root / "delivery-acceptance-report.md").read_text(encoding="utf-8")

        self.assertIn("Frozen Artifact Review Requirements", md_text)
        self.assertIn("Frozen Code Task TDD Evidence Requirements", md_text)
        self.assertIn("Code Task TDD Evidence Coverage", md_text)
        self.assertIn("Artifact Review Coverage", md_text)
        self.assertIn("Completed Module Work", md_text)
        self.assertIn("scanpy", md_text)
        self.assertNotIn("Selected Skill Truth", md_text)
        self.assertNotIn("Runtime packet selected skill source", md_text)
        self.assertIn("Covered code-task TDD evidence requirement", md_text)

    def test_file_delivery_requires_current_readable_evidence(self) -> None:
        for evidence_kind in ("missing", "directory", "directory_child", "empty", "unrelated", "literal_brackets", "valid"):
            with self.subTest(evidence_kind=evidence_kind):
                session = self._build_session()
                expected = session / ("report[1].md" if evidence_kind == "literal_brackets" else "report.md")
                plan_path = session / "module-work-plan.json"
                plan = json.loads(plan_path.read_text(encoding="utf-8"))
                plan["work_units"][0]["expected_outputs"] = [str(expected)]
                write_json(plan_path, plan)
                result_path = session / "module-execution.json"
                payload = json.loads(result_path.read_text(encoding="utf-8"))
                payload["module_work_plan_digest"] = hashlib.sha256(plan_path.read_bytes()).hexdigest()
                if evidence_kind in {"valid", "literal_brackets", "empty", "unrelated"}:
                    write_text(expected, "Verified report.\n")
                elif evidence_kind in {"directory", "directory_child"}:
                    expected.mkdir()
                evidence = expected
                if evidence_kind == "directory_child":
                    evidence = expected / "inner.md"
                    write_text(evidence, "A different file inside a directory.\n")
                if evidence_kind == "unrelated":
                    evidence = session / "other.md"
                    write_text(evidence, "Different output.\n")
                payload["units"][0]["evidence_paths"] = [] if evidence_kind == "empty" else [str(evidence)]
                write_json(result_path, payload)
                report = evaluate(REPO_ROOT, session)
                self.assertEqual(evidence_kind in {"valid", "literal_brackets"}, report["summary"]["completion_language_allowed"])

    def test_evidence_paths_use_frozen_workspace_and_explicit_session_roots(self) -> None:
        session = self._build_session()
        workspace = session.parents[3]
        packet_path = session / "runtime-input-packet.json"
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        packet["storage"] = {"workspace_root": str(workspace)}
        write_json(packet_path, packet)
        write_text(workspace / "outputs/report.md", "Verified report.\n")
        write_text(session / "check.log", "1 passed\n")
        plan_path = session / "module-work-plan.json"
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        plan["work_units"][0]["expected_outputs"] = ["outputs/report.md"]
        write_json(plan_path, plan)
        result_path = session / "module-execution.json"
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        payload["module_work_plan_digest"] = hashlib.sha256(plan_path.read_bytes()).hexdigest()
        payload["units"][0]["evidence_paths"] = ["outputs/report.md", "session:check.log"]
        write_json(result_path, payload)
        self.assertTrue(evaluate(REPO_ROOT, session)["summary"]["completion_language_allowed"])
        (workspace / "outputs/report.md").unlink()
        write_text(session / "outputs/report.md", "Different root.\n")
        self.assertFalse(evaluate(REPO_ROOT, session)["summary"]["completion_language_allowed"])

    def test_tdd_evidence_requires_existing_red_and_green_files(self) -> None:
        requirements = ["Record the failing-first run and the passing rerun."]
        for existing in (False, True):
            with self.subTest(existing=existing):
                session = self._build_session(code_task_tdd_evidence_requirements=requirements)
                red, green = session / "red.log", session / "green.log"
                if existing:
                    write_text(red, "1 failed\n")
                    write_text(green, "1 passed\n")
                result_path = session / "module-execution.json"
                payload = json.loads(result_path.read_text(encoding="utf-8"))
                payload["tdd_evidence"] = {
                    "state": "passing", "evidence_paths": [str(red), str(green)],
                    "red_phase_evidence_paths": [str(red)], "green_phase_evidence_paths": [str(green)],
                    "refactor_phase_evidence_paths": [],
                    "covered_code_task_tdd_evidence_requirements": requirements,
                    "covered_code_task_tdd_exceptions": [],
                }
                write_json(result_path, payload)
                self.assertEqual(existing, evaluate(REPO_ROOT, session)["summary"]["completion_language_allowed"])

    def test_explicit_session_and_bare_glob_outputs_require_file_evidence(self) -> None:
        for output in ("session:README", "*", "./README"):
            for include_evidence in (False, True):
                with self.subTest(output=output, include_evidence=include_evidence):
                    session = self._build_session()
                    expected = session / "README"
                    write_text(expected, "The approved output.\n")
                    plan_path = session / "module-work-plan.json"
                    plan = json.loads(plan_path.read_text(encoding="utf-8"))
                    plan["work_units"][0]["expected_outputs"] = [output]
                    write_json(plan_path, plan)
                    result_path = session / "module-execution.json"
                    payload = json.loads(result_path.read_text(encoding="utf-8"))
                    payload["module_work_plan_digest"] = hashlib.sha256(plan_path.read_bytes()).hexdigest()
                    if output == "*":
                        files = [str(path) for path in session.iterdir() if path.is_file()]
                    else:
                        files = [str(expected)]
                    payload["units"][0]["evidence_paths"] = files if include_evidence else []
                    write_json(result_path, payload)
                    self.assertEqual(include_evidence, evaluate(REPO_ROOT, session)["summary"]["completion_language_allowed"])

    def test_explicit_paths_with_spaces_require_their_file_evidence(self) -> None:
        for scope in ("relative", "session", "absolute"):
            for include_evidence in (False, True):
                with self.subTest(scope=scope, include_evidence=include_evidence):
                    session = self._build_session()
                    expected = session / "my reports" / "final report.md"
                    write_text(expected, "The approved report.\n")
                    output = str(expected) if scope == "absolute" else ("session:" if scope == "session" else "./") + "my reports/final report.md"
                    plan_path = session / "module-work-plan.json"
                    plan = json.loads(plan_path.read_text(encoding="utf-8"))
                    plan["work_units"][0]["expected_outputs"] = [output]
                    write_json(plan_path, plan)
                    result_path = session / "module-execution.json"
                    payload = json.loads(result_path.read_text(encoding="utf-8"))
                    payload["module_work_plan_digest"] = hashlib.sha256(plan_path.read_bytes()).hexdigest()
                    payload["units"][0]["evidence_paths"] = [str(expected)] if include_evidence else []
                    write_json(result_path, payload)
                    self.assertEqual(include_evidence, evaluate(REPO_ROOT, session)["summary"]["completion_language_allowed"])

    def test_descriptive_reply_outputs_with_path_words_remain_supported(self) -> None:
        for output in (
            "Compare input/output behavior.", "Explain report.md in the reply", "Describe the findings.",
            "Explain report.md", "Summarize the changes to src/report.py",
        ):
            with self.subTest(output=output):
                session = self._build_session()
                plan_path = session / "module-work-plan.json"
                plan = json.loads(plan_path.read_text(encoding="utf-8"))
                plan["work_units"][0].update({"write_scope": "module:delivery", "expected_outputs": [output]})
                write_json(plan_path, plan)
                result_path = session / "module-execution.json"
                payload = json.loads(result_path.read_text(encoding="utf-8"))
                payload["module_work_plan_digest"] = hashlib.sha256(plan_path.read_bytes()).hexdigest()
                write_json(result_path, payload)
                self.assertTrue(evaluate(REPO_ROOT, session)["summary"]["completion_language_allowed"])

    def test_relative_frozen_workspace_root_is_rejected(self) -> None:
        session = self._build_session()
        packet_path = session / "runtime-input-packet.json"
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        packet["storage"] = {"workspace_root": "relative-workspace"}
        write_json(packet_path, packet)
        with self.assertRaisesRegex(ValueError, "workspace_root must be absolute"):
            evaluate(REPO_ROOT, session)

    def test_glob_outputs_preserve_literal_workspace_and_session_roots(self) -> None:
        for scope in ("workspace", "session", "absolute", "absolute_session"):
            with self.subTest(scope=scope):
                session = self._build_session(session_name="session[330]")
                workspace = session.parents[3] if scope == "absolute_session" else session.parent / "workspace[330]"
                workspace.mkdir(exist_ok=True)
                output_root = session if scope in {"session", "absolute_session"} else workspace
                expected = output_root / "outputs" / "report.md"
                write_text(expected, "The approved report.\n")
                packet_path = session / "runtime-input-packet.json"
                packet = json.loads(packet_path.read_text(encoding="utf-8"))
                packet["storage"] = {"workspace_root": str(workspace)}
                write_json(packet_path, packet)
                output = "session:outputs/*.md" if scope == "session" else "outputs/*.md"
                if scope in {"absolute", "absolute_session"}:
                    output = str(output_root / "outputs" / "*.md")
                plan_path = session / "module-work-plan.json"
                plan = json.loads(plan_path.read_text(encoding="utf-8"))
                plan["work_units"][0]["expected_outputs"] = [output]
                write_json(plan_path, plan)
                result_path = session / "module-execution.json"
                payload = json.loads(result_path.read_text(encoding="utf-8"))
                payload["module_work_plan_digest"] = hashlib.sha256(plan_path.read_bytes()).hexdigest()
                payload["units"][0]["evidence_paths"] = [str(expected)]
                write_json(result_path, payload)
                self.assertTrue(evaluate(REPO_ROOT, session)["summary"]["completion_language_allowed"])

    def test_read_only_conversational_result_needs_no_file_delivery(self) -> None:
        session = self._build_session()
        plan_path = session / "module-work-plan.json"
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        plan["work_units"][0].update({"write_scope": "no task-file writes", "expected_outputs": ["Explain the report.md format in the reply."]})
        write_json(plan_path, plan)
        result_path = session / "module-execution.json"
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        payload["module_work_plan_digest"] = hashlib.sha256(plan_path.read_bytes()).hexdigest()
        write_json(result_path, payload)
        self.assertTrue(evaluate(REPO_ROOT, session)["summary"]["completion_language_allowed"])


    def test_required_tdd_cannot_be_disabled_by_submission_state(self) -> None:
        requirements = ["Record the failing-first run and the passing rerun."]
        for state, status in (("passing", "not_applicable"), ("not_applicable", None), (None, "not_applicable")):
            with self.subTest(state=state, status=status):
                session = self._build_session(code_task_tdd_evidence_requirements=requirements)
                result_path = session / "module-execution.json"
                payload = json.loads(result_path.read_text(encoding="utf-8"))
                payload["tdd_evidence"] = {
                    "evidence_paths": [str(session / "missing-red.log"), str(session / "missing-green.log")],
                    "red_phase_evidence_paths": [str(session / "missing-red.log")],
                    "green_phase_evidence_paths": [str(session / "missing-green.log")],
                    "refactor_phase_evidence_paths": [],
                    "covered_code_task_tdd_evidence_requirements": requirements,
                    "covered_code_task_tdd_exceptions": [],
                }
                if state is not None:
                    payload["tdd_evidence"]["state"] = state
                if status is not None:
                    payload["tdd_evidence"]["status"] = status
                write_json(result_path, payload)
                report = evaluate(REPO_ROOT, session)
                self.assertFalse(report["summary"]["completion_language_allowed"])
                self.assertNotEqual("not_applicable", report["truth_results"]["code_task_tdd_evidence_truth"]["state"])


    def test_matching_tdd_state_fields_and_legacy_status_preserve_valid_evidence(self) -> None:
        requirements = ["Record the failing-first run and the passing rerun."]
        for state, status in (("passing", "PASSING"), (None, "passed"), ("passing", [])):
            with self.subTest(state=state, status=status):
                session = self._build_session(code_task_tdd_evidence_requirements=requirements)
                red, green = session / "red.log", session / "green.log"
                write_text(red, "1 failed\n")
                write_text(green, "1 passed\n")
                result_path = session / "module-execution.json"
                payload = json.loads(result_path.read_text(encoding="utf-8"))
                payload["tdd_evidence"] = {
                    "status": status,
                    "evidence_paths": [str(red), str(green)],
                    "red_phase_evidence_paths": [str(red)], "green_phase_evidence_paths": [str(green)],
                    "refactor_phase_evidence_paths": [],
                    "covered_code_task_tdd_evidence_requirements": requirements,
                    "covered_code_task_tdd_exceptions": [],
                }
                if state is not None:
                    payload["tdd_evidence"]["state"] = state
                write_json(result_path, payload)
                report = evaluate(REPO_ROOT, session)
                self.assertEqual(isinstance(status, str), report["summary"]["completion_language_allowed"])


if __name__ == "__main__":
    unittest.main()
