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
        governance_scope: str = "root",
        completion_claim_allowed: bool = True,
        cleanup_mode: str = "bounded_cleanup_executed",
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
        write_text(requirement_doc_path, "\n".join(requirement_lines) + "\n")
        write_text(
            execution_plan_path,
            "# Pytest Plan\n\n## Delivery Acceptance Plan\n- Emit the runtime delivery report.\n",
        )

        write_json(
            execution_manifest_path,
            {
                "status": execution_status,
                "governance_scope": governance_scope,
                "executed_unit_count": 3,
                "failed_unit_count": failed_unit_count,
                "timed_out_unit_count": 0,
            },
        )
        write_json(
            runtime_input_packet_path,
            {
                "authority_flags": {
                    "explicit_runtime_skill": "vibe",
                }
            },
        )
        write_json(
            session_root / "phase-execute.json",
            {
                "requirement_doc_path": str(requirement_doc_path),
                "execution_plan_path": str(execution_plan_path),
                "execution_manifest_path": str(execution_manifest_path),
                "runtime_input_packet_path": str(runtime_input_packet_path),
                "completion_claim_allowed": completion_claim_allowed,
            },
        )
        write_json(
            session_root / "cleanup-receipt.json",
            {
                "cleanup_mode": cleanup_mode,
            },
        )
        return session_root

    def test_runtime_delivery_acceptance_passes_for_clean_root_run(self) -> None:
        session_root = self._build_session()
        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("PASS", report["summary"]["gate_result"])
        self.assertTrue(report["summary"]["completion_language_allowed"])
        self.assertEqual("passing", report["truth_results"]["product_acceptance_truth"]["state"])

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
