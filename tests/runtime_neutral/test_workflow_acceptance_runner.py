from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "verify" / "runtime_neutral" / "workflow_acceptance_runner.py"


def load_module():
    spec = importlib.util.spec_from_file_location("runtime_neutral_workflow_acceptance_runner", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class WorkflowAcceptanceRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()

    def _evaluate(self, scenario: dict[str, object]):
        with tempfile.TemporaryDirectory() as tempdir:
            scenario_path = Path(tempdir) / "scenario.json"
            scenario_path.write_text(json.dumps(scenario, indent=2) + "\n", encoding="utf-8")
            return self.module.evaluate(REPO_ROOT, scenario_path)

    @staticmethod
    def _truths(**overrides: str) -> dict[str, dict[str, str]]:
        states = {
            "governance_truth": "passing",
            "engineering_verification_truth": "passing",
            "module_acceptance_truth": "passing",
            "workflow_completion_truth": "passing",
            "code_task_tdd_evidence_truth": "passing",
            "artifact_review_truth": "passing",
            "product_acceptance_truth": "passing",
        }
        states.update(overrides)
        return {name: {"state": state} for name, state in states.items()}

    def test_passing_scenario_allows_completion_language(self) -> None:
        artifact = self._evaluate(
            {
                "scenario_id": "l-grade-feature-complete",
                "task_class": "l_serial_feature_delivery",
                "runtime": {"status": "completed", "readiness_state": "ready"},
                "truths": self._truths(),
            }
        )
        self.assertEqual("PASS", artifact["summary"]["gate_result"])
        self.assertTrue(artifact["summary"]["completion_language_allowed"])
        self.assertEqual(0, artifact["summary"]["forbidden_completion_hit_count"])
        self.assertEqual("passing", artifact["truth_results"]["module_acceptance_truth"]["state"])
        self.assertEqual("passing", artifact["truth_results"]["code_task_tdd_evidence_truth"]["state"])
        self.assertEqual("passing", artifact["truth_results"]["artifact_review_truth"]["state"])
        self.assertNotIn("specialist_decision_truth", artifact["truth_results"])
        self.assertNotIn("specialist_disclosure_truth", artifact["truth_results"])

    def test_manual_review_scenario_blocks_completion_language(self) -> None:
        artifact = self._evaluate(
            {
                "scenario_id": "xl-composite-manual-review",
                "task_class": "xl_composite_module_delivery",
                "runtime": {"status": "completed", "readiness_state": "ready"},
                "truths": self._truths(
                    artifact_review_truth="manual_review_required",
                    product_acceptance_truth="manual_review_required",
                ),
            }
        )
        self.assertEqual("MANUAL_REVIEW_REQUIRED", artifact["summary"]["gate_result"])
        self.assertFalse(artifact["summary"]["completion_language_allowed"])
        self.assertEqual(
            "manual_review_required",
            artifact["truth_results"]["product_acceptance_truth"]["state"],
        )
        self.assertEqual(
            "manual_review_required",
            artifact["truth_results"]["artifact_review_truth"]["state"],
        )
        self.assertEqual("passing", artifact["truth_results"]["code_task_tdd_evidence_truth"]["state"])

    def test_completed_with_failures_is_forbidden_completion_hit(self) -> None:
        artifact = self._evaluate(
            {
                "scenario_id": "partial-completion-blocked",
                "task_class": "runtime_partial_completion",
                "runtime": {"status": "completed_with_failures", "readiness_state": "ready"},
                "truths": self._truths(
                    engineering_verification_truth="partial",
                    module_acceptance_truth="failing",
                    workflow_completion_truth="partial",
                    code_task_tdd_evidence_truth="not_run",
                    artifact_review_truth="not_run",
                    product_acceptance_truth="failing",
                ),
            }
        )
        self.assertEqual("FAIL", artifact["summary"]["gate_result"])
        self.assertFalse(artifact["summary"]["completion_language_allowed"])
        self.assertGreaterEqual(artifact["summary"]["forbidden_completion_hit_count"], 1)
        self.assertIn(
            "product_acceptance_truth",
            artifact["summary"]["incomplete_layers"],
        )
        self.assertIn(
            "code_task_tdd_evidence_truth",
            artifact["summary"]["incomplete_layers"],
        )
        self.assertIn("module_acceptance_truth", artifact["summary"]["incomplete_layers"])

    def test_missing_optional_external_fixture_does_not_change_truth_result(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            (root / "config").mkdir(parents=True, exist_ok=True)
            (root / "config" / "version-governance.json").write_text("{}\n", encoding="utf-8")
            contract_path = REPO_ROOT / "config" / "project-delivery-acceptance-contract.json"
            (root / "config" / "project-delivery-acceptance-contract.json").write_text(
                contract_path.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            (root / "benchmarks" / "demo").mkdir(parents=True, exist_ok=True)
            scenario_path = root / "scenario.json"
            scenario_path.write_text(
                json.dumps(
                    {
                        "scenario_id": "no-benchmark-required",
                        "task_class": "test",
                        "runtime": {"status": "completed", "readiness_state": "ready"},
                        "truths": {
                            "governance_truth": {"state": "passing"},
                            "engineering_verification_truth": {"state": "passing"},
                            "module_acceptance_truth": {"state": "passing"},
                            "workflow_completion_truth": {"state": "passing"},
                            "code_task_tdd_evidence_truth": {"state": "not_applicable"},
                            "artifact_review_truth": {"state": "passing"},
                            "product_acceptance_truth": {"state": "passing"}
                        }
                    },
                    indent=2,
                ) + "\n",
                encoding="utf-8",
            )
            artifact = self.module.evaluate(root, scenario_path)
            self.assertEqual("PASS", artifact["summary"]["gate_result"])
            self.assertTrue(artifact["summary"]["completion_language_allowed"])

    def test_write_artifacts_emits_json_and_markdown(self) -> None:
        artifact = self._evaluate(
            {
                "scenario_id": "l-grade-feature-complete",
                "task_class": "l_serial_feature_delivery",
                "runtime": {"status": "completed", "readiness_state": "ready"},
                "truths": self._truths(),
            }
        )
        with tempfile.TemporaryDirectory() as tempdir:
            self.module.write_artifacts(REPO_ROOT, artifact, tempdir)
            json_path = Path(tempdir) / "vibe-workflow-acceptance-gate.json"
            md_path = Path(tempdir) / "vibe-workflow-acceptance-gate.md"
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual("PASS", payload["summary"]["gate_result"])
            md_text = md_path.read_text(encoding="utf-8")
            self.assertIn("Vibe Workflow Acceptance Gate", md_text)
            self.assertIn("Completion Language Allowed", md_text)

    def test_delivery_contract_uses_module_acceptance_instead_of_specialist_truth_layers(self) -> None:
        contract = json.loads(
            (REPO_ROOT / "config" / "project-delivery-acceptance-contract.json").read_text(encoding="utf-8")
        )
        truth_layers = contract["truth_layers"]
        must_report = contract["report_requirements"]["must_report_fields"]

        self.assertIn("module_acceptance_truth", truth_layers)
        self.assertIn("module_acceptance_truth", must_report)
        self.assertNotIn("specialist_disclosure_truth", truth_layers)
        self.assertNotIn("specialist_decision_truth", truth_layers)
        self.assertNotIn("specialist_disclosure_truth", must_report)
        self.assertNotIn("specialist_decision_truth", must_report)


if __name__ == "__main__":
    unittest.main()
