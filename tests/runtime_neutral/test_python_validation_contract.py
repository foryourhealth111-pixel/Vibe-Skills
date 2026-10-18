from __future__ import annotations

import configparser
import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PYTEST_INI = REPO_ROOT / "pytest.ini"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "vco-gates.yml"
OPTIONAL_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "vco-optional-audits.yml"
RELEASE_PROOF_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "vco-release-proof.yml"
TARGETS_FILE = REPO_ROOT / "config" / "python-validation-targets.txt"
DOCS_INDEX = REPO_ROOT / "docs" / "README.md"
TRACKED_CURRENT_STATE = REPO_ROOT / "docs" / "status" / "current-state.md"
PACK_MANIFEST = REPO_ROOT / "config" / "pack-manifest.json"
LIVE_DOCUMENT_CONTRACT = REPO_ROOT / "config" / "live-document-contract.json"
RESOLVE_PACK_ROUTE = REPO_ROOT / "scripts" / "router" / "resolve-pack-route.ps1"
CONFTEST = REPO_ROOT / "tests" / "conftest.py"
PYTHON_HELPERS = REPO_ROOT / "scripts" / "common" / "python_helpers.sh"
TIMESFM_OUTPUT_ROOT = REPO_ROOT / "bundled" / "skills" / "timesfm-forecasting" / "examples"
EXPECTED_PYTHON_VALIDATION_TARGETS = [
    "tests/runtime_neutral/test_install_profile_differentiation.py",
    "tests/runtime_neutral/test_governed_runtime_bridge.py",
    "tests/runtime_neutral/test_runtime_delivery_acceptance.py",
    "tests/runtime_neutral/test_custom_admission_bridge.py",
    "tests/runtime_neutral/test_router_authority_safe_fallback.py",
    "tests/runtime_neutral/test_live_document_contract_gate.py",
    "tests/integration/test_shared_run_artifact_contract.py",
    "tests/runtime_neutral/test_test_baseline_audit.py",
    "tests/runtime_neutral/test_python_validation_contract.py",
    "tests/runtime_neutral/test_release_surface.py",
]


def _workflow_step_block(text: str, step_name: str) -> str:
    marker = f"      - name: {step_name}\n"
    start = text.index(marker)
    end = text.find("\n      - name: ", start + len(marker))
    return text[start:] if end == -1 else text[start:end]


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
        self.assertIn("windows-latest", text)
        self.assertIn("test-baseline-audit.py --run-layer integration_host_boundary", text)
        self.assertIn("scripts/verify/live-document-gate.py", text)
        self.assertIn('git cat-file -e "${BASE_SHA}^{commit}"', text)
        self.assertIn("running workspace-only validation", text)
        self.assertIn("scripts/verify/publish-proof.py", text)
        self.assertIn("actions/upload-artifact@v4", text)
        self.assertIn("retention-days:", text)
        self.assertIn("vibe-developer-entry-gate.ps1", text)
        self.assertNotIn("vibe-current-routing-contract-scan.ps1", text)
        self.assertNotIn("test_retired_agent_execution_surfaces.py", text)
        self.assertNotIn("vibe-pack-regression-matrix.ps1", text)
        self.assertNotIn("vibe-offline-skills-gate.ps1", text)

    def test_optional_audit_workflow_keeps_heavier_checks_outside_default_lane(self) -> None:
        text = OPTIONAL_WORKFLOW.read_text(encoding="utf-8-sig")

        self.assertIn("workflow_dispatch:", text)
        self.assertIn("audit_suite:", text)
        self.assertIn("capability_baseline", text)
        self.assertIn("packaging_release", text)
        self.assertIn("host_boundary", text)
        self.assertIn("history_surface", text)
        self.assertIn("touched_packaging_release", text)
        self.assertIn("integration_host_boundary", text)
        self.assertIn("touched_historical_governance", text)
        self.assertIn("persist-credentials: false", text)
        self.assertNotIn("pull_request:", text)
        self.assertNotIn("push:", text)

    def test_release_workflow_attaches_generated_proof_to_github_release(self) -> None:
        text = RELEASE_PROOF_WORKFLOW.read_text(encoding="utf-8-sig")
        formal_proof = _workflow_step_block(text, "Generate formal release proof")
        retained_proof = _workflow_step_block(text, "Retain formal release proof")
        release_upload = _workflow_step_block(text, "Attach proof to GitHub Release")
        proof_enforcement = _workflow_step_block(text, "Enforce formal release proof")

        self.assertIn("release:", text)
        self.assertIn("types: [published]", text)
        self.assertIn("contents: write", text)
        self.assertIn("scripts/verify/publish-proof.py", text)
        self.assertIn("scripts/release/build_release_bundle.py", text)
        self.assertIn("proof-bundle.json", text)
        self.assertIn("current-state.json", text)
        self.assertIn("current-state.md", text)
        self.assertIn("gh release upload", text)
        self.assertIn("actions/upload-artifact@v4", text)
        self.assertIn("retention-days: 90", text)
        self.assertIn("persist-credentials: false", text)
        self.assertIn('if [ "${#targets[@]}" -eq 0 ]; then', text)
        self.assertIn("canonical python validation target list is empty", text)
        self.assertIn("id: formal-proof", formal_proof)
        self.assertIn("if: always()", formal_proof)
        self.assertIn("if: always()", retained_proof)
        self.assertIn("actions/upload-artifact@v4", retained_proof)
        self.assertIn("outputs/release-proof", retained_proof)
        self.assertIn("dist/release", retained_proof)
        self.assertNotIn("if: always()", release_upload)
        self.assertIn("gh release upload", release_upload)
        for step_id in (
            "release-contract",
            "release-validation",
            "distribution",
            "release-bundle",
            "formal-proof",
        ):
            outcome_guard = f"steps.{step_id}.outcome == 'success'"
            self.assertIn(outcome_guard, release_upload)
            self.assertIn(f"steps.{step_id}.outcome", proof_enforcement)

    def test_default_docs_entry_uses_live_state_sources(self) -> None:
        docs_text = DOCS_INDEX.read_text(encoding="utf-8-sig")

        self.assertFalse(TRACKED_CURRENT_STATE.exists())
        self.assertNotIn("status/current-state.md", docs_text)
        self.assertIn("actions/workflows/vco-gates.yml", docs_text)
        self.assertIn("releases/latest", docs_text)
        self.assertIn("check.ps1", docs_text)

    def test_workflow_retention_matches_the_live_document_contract(self) -> None:
        contract = json.loads(LIVE_DOCUMENT_CONTRACT.read_text(encoding="utf-8"))
        retention = contract["proof_retention"]
        default_workflow = WORKFLOW.read_text(encoding="utf-8-sig")
        release_workflow = RELEASE_PROOF_WORKFLOW.read_text(encoding="utf-8-sig")

        self.assertIn(
            f"&& {retention['pull_request_days']} || {retention['main_and_scheduled_days']}",
            default_workflow,
        )
        self.assertIn(
            f"retention-days: {retention['main_and_scheduled_days']}",
            release_workflow,
        )
        self.assertEqual("github_release", retention["formal_release"])
        self.assertIn("gh release upload", release_workflow)

    def test_shared_shell_python_helper_keeps_python_resolution_policy_canonical(self) -> None:
        self.assertTrue(PYTHON_HELPERS.exists(), "shared shell Python helper should exist")

        text = PYTHON_HELPERS.read_text(encoding="utf-8")
        self.assertIn("for candidate in python3 python; do", text)
        self.assertIn("--print-supported-python", text)
        self.assertIn("requires Python ${PYTHON_MIN_MAJOR}.${PYTHON_MIN_MINOR}+", text)
        self.assertIn("python3 --version", text)

    def test_router_entrypoint_forces_utf8_console_output_for_unicode_prompts(self) -> None:
        self.assertTrue(RESOLVE_PACK_ROUTE.exists(), "router entrypoint should exist")

        text = RESOLVE_PACK_ROUTE.read_text(encoding="utf-8")
        self.assertIn("[Console]::OutputEncoding = [System.Text.Encoding]::UTF8", text)
        self.assertIn("$OutputEncoding = [System.Text.Encoding]::UTF8", text)

    def test_python_validation_targets_cover_default_capability_invariants(self) -> None:
        self.assertTrue(TARGETS_FILE.exists(), "canonical Python validation target list should exist")

        targets = [
            line.strip()
            for line in TARGETS_FILE.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]

        self.assertEqual(EXPECTED_PYTHON_VALIDATION_TARGETS, targets)

    def test_python_validation_targets_skip_touched_packaging_release_only_checks(self) -> None:
        targets = {
            line.strip()
            for line in TARGETS_FILE.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }

        self.assertNotIn("tests/runtime_neutral/test_release_truth_gate.py", targets)
        self.assertNotIn("tests/runtime_neutral/test_pack_manifest_role_contract.py", targets)

    def test_python_validation_targets_skip_optional_audits(self) -> None:
        targets = {
            line.strip()
            for line in TARGETS_FILE.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }

        self.assertNotIn("tests/contract/test_repo_layout_contract.py", targets)
        self.assertNotIn("tests/runtime_neutral/test_docs_readme_encoding.py", targets)
        self.assertNotIn("tests/runtime_neutral/test_memory_progressive_disclosure.py", targets)
        self.assertNotIn("tests/runtime_neutral/test_bundled_skill_governance_gate.py", targets)
        self.assertNotIn("tests/runtime_neutral/test_runtime_contract_goldens.py", targets)

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

    def test_pack_defaults_point_to_unified_skill_candidates(self) -> None:
        manifest = json.loads(PACK_MANIFEST.read_text(encoding="utf-8-sig"))
        mismatches: dict[str, dict[str, str]] = {}

        for pack in manifest["packs"]:
            skill_candidates = {skill.casefold() for skill in (pack.get("skill_candidates") or [])}
            if not skill_candidates:
                continue

            bad_defaults = {
                task: skill
                for task, skill in (pack.get("defaults_by_task") or {}).items()
                if skill.casefold() not in skill_candidates
            }
            if bad_defaults:
                mismatches[pack["id"]] = bad_defaults

        self.assertEqual({}, mismatches)

    def test_router_entrypoint_delegates_to_python_local_skill_router(self) -> None:
        text = RESOLVE_PACK_ROUTE.read_text(encoding="utf-8-sig")

        expected_tokens = [
            "'-m', 'vgo_cli.main'",
            "'route'",
            "'--output-json-path'",
            "'--force-runtime-neutral'",
            "'--host-id'",
            "'--target-root'",
            "$env:PYTHONUTF8 = '1'",
            "$env:PYTHONIOENCODING = 'utf-8'",
        ]
        for token in expected_tokens:
            self.assertIn(token, text)

        retired_pack_override_tokens = [
            "$selectableRanked",
            "$selectionPool",
            "$overrideTop",
            "ai_rerank_override_block_reason",
            "llm_acceleration_override_block_reason",
            "route_override_requested",
        ]
        for token in retired_pack_override_tokens:
            self.assertNotIn(token, text)


if __name__ == "__main__":
    unittest.main()
