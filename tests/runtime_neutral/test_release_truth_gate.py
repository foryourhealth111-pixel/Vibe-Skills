from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "verify" / "runtime_neutral" / "release_truth_gate.py"


def load_module():
    spec = importlib.util.spec_from_file_location("runtime_neutral_release_truth_gate", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ReleaseTruthGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()

    def _write_report(self, tempdir: Path, name: str, gate_result: str, completion_language_allowed: bool) -> Path:
        path = tempdir / f"{name}.json"
        path.write_text(
            json.dumps(
                {
                    "summary": {
                        "scenario_id": name,
                        "task_class": "test",
                        "gate_result": gate_result,
                        "completion_language_allowed": completion_language_allowed,
                    }
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return path

    def test_all_passing_reports_allow_release_truth(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            report_a = self._write_report(root, "a", "PASS", True)
            report_b = self._write_report(root, "b", "PASS", True)
            artifact = self.module.evaluate(REPO_ROOT, [report_a, report_b])
            self.assertEqual("PASS", artifact["summary"]["gate_result"])
            self.assertTrue(artifact["summary"]["completion_language_allowed"])

    def test_manual_review_report_blocks_release_truth(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            report_a = self._write_report(root, "a", "PASS", True)
            report_b = self._write_report(root, "b", "MANUAL_REVIEW_REQUIRED", False)
            artifact = self.module.evaluate(REPO_ROOT, [report_a, report_b])
            self.assertEqual("MANUAL_REVIEW_REQUIRED", artifact["summary"]["gate_result"])
            self.assertFalse(artifact["summary"]["completion_language_allowed"])

    def test_failing_report_fails_release_truth(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            report_a = self._write_report(root, "a", "PASS", True)
            report_b = self._write_report(root, "b", "FAIL", False)
            artifact = self.module.evaluate(REPO_ROOT, [report_a, report_b])
            self.assertEqual("FAIL", artifact["summary"]["gate_result"])
            self.assertEqual(1, artifact["summary"]["failing_report_count"])

    def test_write_artifacts_emits_json_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            report_a = self._write_report(root, "a", "PASS", True)
            artifact = self.module.evaluate(REPO_ROOT, [report_a])
            self.module.write_artifacts(REPO_ROOT, artifact, tempdir)
            json_path = Path(tempdir) / "vibe-release-truth-gate.json"
            md_path = Path(tempdir) / "vibe-release-truth-gate.md"
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual("PASS", payload["summary"]["gate_result"])


if __name__ == "__main__":
    unittest.main()
