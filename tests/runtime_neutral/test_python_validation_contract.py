from __future__ import annotations

import configparser
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PYTEST_INI = REPO_ROOT / "pytest.ini"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "vco-gates.yml"
TIMESFM_OUTPUT_ROOT = REPO_ROOT / "bundled" / "skills" / "timesfm-forecasting" / "examples"


class PythonValidationContractTests(unittest.TestCase):
    def test_repo_declares_tests_as_the_default_pytest_collection_surface(self) -> None:
        self.assertTrue(PYTEST_INI.exists(), "pytest.ini should exist at the repo root")

        parser = configparser.ConfigParser()
        parser.read(PYTEST_INI, encoding="utf-8")

        self.assertIn("pytest", parser)
        testpaths = [line.strip() for line in parser["pytest"].get("testpaths", "").splitlines() if line.strip()]
        self.assertEqual(["tests"], testpaths)

    def test_ci_workflow_runs_python_validation(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8-sig")

        self.assertIn("actions/setup-python@v5", text)
        self.assertIn("pytest -q", text)
        self.assertIn("ubuntu-latest", text)

    def test_timesfm_examples_do_not_track_generated_binary_or_web_outputs(self) -> None:
        forbidden_suffixes = {".png", ".gif", ".html"}
        self.assertTrue(TIMESFM_OUTPUT_ROOT.exists(), "TimesFM examples root should exist")
        forbidden_paths = sorted(
            path.relative_to(REPO_ROOT).as_posix()
            for path in TIMESFM_OUTPUT_ROOT.rglob("*")
            if path.is_file()
            and "output" in path.relative_to(TIMESFM_OUTPUT_ROOT).parts
            and path.suffix.lower() in forbidden_suffixes
        )

        self.assertEqual([], forbidden_paths)


if __name__ == "__main__":
    unittest.main()
