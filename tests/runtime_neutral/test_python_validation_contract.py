from __future__ import annotations

import configparser
import json
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PYTEST_INI = REPO_ROOT / "pytest.ini"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "vco-gates.yml"
TARGETS_FILE = REPO_ROOT / "config" / "python-validation-targets.txt"
PACK_MANIFEST = REPO_ROOT / "config" / "pack-manifest.json"
RESOLVE_PACK_ROUTE = REPO_ROOT / "scripts" / "router" / "resolve-pack-route.ps1"
CONFTEST = REPO_ROOT / "tests" / "conftest.py"
PYTHON_HELPERS = REPO_ROOT / "scripts" / "common" / "python_helpers.sh"
TIMESFM_OUTPUT_ROOT = REPO_ROOT / "bundled" / "skills" / "timesfm-forecasting" / "examples"
EXPECTED_PYTHON_VALIDATION_TARGETS = [
    "tests/contract/test_repo_layout_contract.py",
    "tests/integration/test_runtime_surface_contract_cutover.py",
    "tests/runtime_neutral/test_apps_surface_hygiene.py",
    "tests/runtime_neutral/test_bundled_stage_assistant_freeze.py",
    "tests/runtime_neutral/test_bundled_skill_governance_gate.py",
    "tests/runtime_neutral/test_custom_admission_bridge.py",
    "tests/runtime_neutral/test_docs_readme_encoding.py",
    "tests/runtime_neutral/test_governed_runtime_bridge.py",
    "tests/runtime_neutral/test_install_profile_differentiation.py",
    "tests/runtime_neutral/test_memory_progressive_disclosure.py",
    "tests/runtime_neutral/test_runtime_contract_goldens.py",
    "tests/runtime_neutral/test_python_validation_contract.py",
]


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
        self.assertIn("scripts/common/python_helpers.sh --print-supported-python", text)
        self.assertIn('"${python_bin}" -B -m pytest -q', text)
        self.assertIn("config/python-validation-targets.txt", text)
        self.assertIn('if [ "${#targets[@]}" -eq 0 ]; then', text)
        self.assertIn("canonical python validation target list is empty", text)
        self.assertIn("ubuntu-latest", text)

    def test_shared_shell_python_helper_keeps_python_resolution_policy_canonical(self) -> None:
        self.assertTrue(PYTHON_HELPERS.exists(), "shared shell Python helper should exist")

        text = PYTHON_HELPERS.read_text(encoding="utf-8")
        self.assertIn("for candidate in python3 python; do", text)
        self.assertIn("--print-supported-python", text)
        self.assertIn("requires Python ${PYTHON_MIN_MAJOR}.${PYTHON_MIN_MINOR}+", text)
        self.assertIn("python3 --version", text)

    def test_python_validation_targets_cover_critical_invariants(self) -> None:
        self.assertTrue(TARGETS_FILE.exists(), "canonical Python validation target list should exist")

        targets = [
            line.strip()
            for line in TARGETS_FILE.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]

        self.assertEqual(EXPECTED_PYTHON_VALIDATION_TARGETS, targets)

    def test_conftest_does_not_mutate_repo_owned_bytecode_artifacts_before_hygiene_assertions(self) -> None:
        self.assertTrue(CONFTEST.exists(), "tests/conftest.py should exist")

        text = CONFTEST.read_text(encoding="utf-8")
        self.assertNotIn("shutil.rmtree(", text)
        self.assertNotIn(".unlink(", text)
        self.assertNotIn('rglob("__pycache__")', text)
        self.assertNotIn('rglob("*.pyc")', text)
        self.assertNotIn('rglob("*.pyo")', text)

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

    def test_pack_defaults_do_not_point_to_non_authority_stage_assistants(self) -> None:
        manifest = json.loads(PACK_MANIFEST.read_text(encoding="utf-8-sig"))
        mismatches: dict[str, dict[str, str]] = {}

        for pack in manifest["packs"]:
            authority_source = (
                pack.get("route_authority_candidates")
                if "route_authority_candidates" in pack
                else pack.get("skill_candidates")
            )
            authority = {skill.casefold() for skill in (authority_source or [])}
            if not authority:
                continue

            bad_defaults = {
                task: skill
                for task, skill in (pack.get("defaults_by_task") or {}).items()
                if skill.casefold() not in authority
            }
            if bad_defaults:
                mismatches[pack["id"]] = bad_defaults

        self.assertEqual({}, mismatches)

    def test_pack_route_overrides_stay_inside_authority_ranked_results(self) -> None:
        text = RESOLVE_PACK_ROUTE.read_text(encoding="utf-8-sig")
        normalized_text = re.sub(r"\s+", " ", text)
        authority_lookup = (
            "$overrideTop = $authorityRanked | Where-Object { [string]$_.pack_id -eq $overridePackId } | "
            "Select-Object -First 1"
        )
        ranked_lookup = (
            "$overrideTop = $ranked | Where-Object { [string]$_.pack_id -eq $overridePackId } | "
            "Select-Object -First 1"
        )

        self.assertEqual(2, normalized_text.count(authority_lookup))
        self.assertNotIn(ranked_lookup, normalized_text)
        self.assertIn("ai_rerank_override_block_reason", text)
        self.assertIn("llm_acceleration_override_block_reason", text)
        self.assertIn("route_override_requested", text)


if __name__ == "__main__":
    unittest.main()
