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

    def test_passing_scenario_allows_completion_language(self) -> None:
        scenario_path = REPO_ROOT / "tests" / "scenarios" / "project_delivery" / "l-grade-feature-complete.json"
        artifact = self.module.evaluate(REPO_ROOT, scenario_path)
        self.assertEqual("PASS", artifact["summary"]["gate_result"])
        self.assertTrue(artifact["summary"]["completion_language_allowed"])
        self.assertEqual(0, artifact["summary"]["forbidden_completion_hit_count"])
        self.assertTrue(artifact["summary"]["benchmark_repo_exists"])
        self.assertTrue(artifact["summary"]["benchmark_manifest_exists"])
        self.assertEqual("todo-webapp", artifact["benchmark"]["manifest"]["benchmark_id"])

    def test_manual_review_scenario_blocks_completion_language(self) -> None:
        scenario_path = REPO_ROOT / "tests" / "scenarios" / "project_delivery" / "xl-composite-manual-review.json"
        artifact = self.module.evaluate(REPO_ROOT, scenario_path)
        self.assertEqual("MANUAL_REVIEW_REQUIRED", artifact["summary"]["gate_result"])
        self.assertFalse(artifact["summary"]["completion_language_allowed"])
        self.assertEqual(
            "manual_review_required",
            artifact["truth_results"]["product_acceptance_truth"]["state"],
        )

    def test_completed_with_failures_is_forbidden_completion_hit(self) -> None:
        scenario_path = REPO_ROOT / "tests" / "scenarios" / "project_delivery" / "partial-completion-blocked.json"
        artifact = self.module.evaluate(REPO_ROOT, scenario_path)
        self.assertEqual("FAIL", artifact["summary"]["gate_result"])
        self.assertFalse(artifact["summary"]["completion_language_allowed"])
        self.assertGreaterEqual(artifact["summary"]["forbidden_completion_hit_count"], 1)
        self.assertIn(
            "product_acceptance_truth",
            artifact["summary"]["incomplete_layers"],
        )

    def test_missing_benchmark_manifest_downgrades_to_manual_review(self) -> None:
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
                        "scenario_id": "missing-benchmark-manifest",
                        "task_class": "test",
                        "benchmark_repo": "benchmarks/demo",
                        "runtime": {"status": "completed", "readiness_state": "ready"},
                        "truths": {
                            "governance_truth": {"state": "passing"},
                            "engineering_verification_truth": {"state": "passing"},
                            "workflow_completion_truth": {"state": "passing"},
                            "product_acceptance_truth": {"state": "passing"}
                        }
                    },
                    indent=2,
                ) + "\n",
                encoding="utf-8",
            )
            artifact = self.module.evaluate(root, scenario_path)
            self.assertEqual("MANUAL_REVIEW_REQUIRED", artifact["summary"]["gate_result"])
            self.assertFalse(artifact["summary"]["completion_language_allowed"])

    def test_write_artifacts_emits_json_and_markdown(self) -> None:
        scenario_path = REPO_ROOT / "tests" / "scenarios" / "project_delivery" / "l-grade-feature-complete.json"
        artifact = self.module.evaluate(REPO_ROOT, scenario_path)
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


if __name__ == "__main__":
    unittest.main()
