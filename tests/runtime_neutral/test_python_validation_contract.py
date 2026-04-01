from __future__ import annotations

import configparser
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PYTEST_INI = REPO_ROOT / "pytest.ini"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "vco-gates.yml"
CHECK_SH = REPO_ROOT / "check.sh"
CHECK_PS1 = REPO_ROOT / "check.ps1"
PY_INSTALLER = REPO_ROOT / "scripts" / "install" / "install_vgo_adapter.py"
PS_INSTALLER = REPO_ROOT / "scripts" / "install" / "Install-VgoAdapter.ps1"
CATALOG_GATE = REPO_ROOT / "scripts" / "verify" / "vibe-skill-catalog-profile-gate.ps1"
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

    def test_ci_and_local_checks_invoke_catalog_profile_gate_separately_from_runtime_gates(self) -> None:
        workflow_text = WORKFLOW.read_text(encoding="utf-8-sig")
        check_sh_text = CHECK_SH.read_text(encoding="utf-8-sig")
        check_ps1_text = CHECK_PS1.read_text(encoding="utf-8-sig")

        self.assertIn("vibe-skill-catalog-profile-gate.ps1", workflow_text)
        self.assertIn("run_skill_catalog_profile_gate", check_sh_text)
        self.assertIn("Invoke-SkillCatalogProfileCheck", check_ps1_text)
        self.assertIn("run_runtime_freshness_gate", check_sh_text)
        self.assertIn("run_runtime_coherence_gate", check_sh_text)
        self.assertIn("Invoke-RuntimeFreshnessCheck", check_ps1_text)
        self.assertIn("Invoke-RuntimeCoherenceCheck", check_ps1_text)

    def test_catalog_manifest_indirection_is_consumed_by_installers_and_gate(self) -> None:
        py_installer_text = PY_INSTALLER.read_text(encoding="utf-8-sig")
        ps_installer_text = PS_INSTALLER.read_text(encoding="utf-8-sig")
        catalog_gate_text = CATALOG_GATE.read_text(encoding="utf-8-sig")

        self.assertIn("catalog_packaging_manifest", py_installer_text)
        self.assertIn("resolve_catalog_packaging_manifest_path", py_installer_text)
        self.assertIn("catalog_packaging_manifest", ps_installer_text)
        self.assertIn("Get-VgoSkillCatalogPackagingPath", ps_installer_text)
        self.assertIn("catalog_packaging_manifest", catalog_gate_text)
        self.assertIn("Resolve-CatalogPackagingPath", catalog_gate_text)

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
