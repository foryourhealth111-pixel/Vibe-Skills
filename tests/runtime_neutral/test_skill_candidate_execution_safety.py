from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ROUTE_SCRIPT = REPO_ROOT / "scripts" / "router" / "resolve-pack-route.ps1"
HELPER_SCRIPT = REPO_ROOT / "scripts" / "common" / "vibe-governance-helpers.ps1"
EXECUTION_SAFETY_POLICY_PATH = REPO_ROOT / "config" / "skill-execution-safety-policy.json"
ML_PROMPT = (
    "Please use scikit-learn to prototype a tabular classification baseline, "
    "run feature selection, and compare cross-validation metrics."
)
SAFE_EDIT_PROMPT = "Remove dead imports and replace a mock in tests."
DESTRUCTIVE_PROMPT = (
    "Please use scikit-learn to prototype a tabular classification baseline, "
    "then delete old generated artifacts and overwrite install settings."
)
WINDOWS_DESTRUCTIVE_PROMPT = r"delete C:\tmp\build"
POWERSHELL_SUBPROCESS_TIMEOUT_SECONDS = 120


def resolve_powershell() -> str | None:
    candidates = [
        shutil.which("pwsh"),
        shutil.which("pwsh.exe"),
        r"C:\Program Files\PowerShell\7\pwsh.exe",
        r"C:\Program Files\PowerShell\7-preview\pwsh.exe",
        shutil.which("powershell"),
        shutil.which("powershell.exe"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))
    return None


def run_route(prompt: str, *, repo_root: Path = REPO_ROOT, target_root: Path | None = None) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    route_script = repo_root / "scripts" / "router" / "resolve-pack-route.ps1"
    command = [
        shell,
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(route_script),
        "-Prompt",
        prompt,
        "-Grade",
        "M",
        "-TaskType",
        "coding",
    ]
    if target_root is not None:
        command.extend(["-HostId", "codex", "-TargetRoot", str(target_root)])

    completed = subprocess.run(
        command,
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=POWERSHELL_SUBPROCESS_TIMEOUT_SECONDS,
        check=True,
    )
    return json.loads(completed.stdout)


def write_installed_skill(target_root: Path, skill_id: str) -> Path:
    skill_path = target_root / "skills" / skill_id / "SKILL.md"
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text(
        (
            "---\n"
            f"name: {skill_id}\n"
            f"description: Installed {skill_id} test skill.\n"
            "---\n"
        ),
        encoding="utf-8",
    )
    return skill_path


def run_helper_json(script_body: str) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    completed = subprocess.run(
        [
            shell,
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script_body,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=POWERSHELL_SUBPROCESS_TIMEOUT_SECONDS,
        check=True,
    )
    return json.loads(completed.stdout)


def as_list(value: object) -> list[object]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def copy_repo_fixture(target_root: Path) -> Path:
    fixture_root = target_root / "repo-copy"
    shutil.copytree(
        REPO_ROOT,
        fixture_root,
        ignore=shutil.ignore_patterns(".git", ".worktrees", "outputs", "__pycache__", ".pytest_cache"),
    )
    return fixture_root


class SkillCandidateExecutionSafetyTests(unittest.TestCase):
    def test_non_destructive_ml_prompt_routes_to_local_installed_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir) / ".agents"
            skill_path = write_installed_skill(target_root, "scikit-learn")
            route = run_route(ML_PROMPT, target_root=target_root)

        selected = route["candidate_focus"]
        self.assertEqual("local-skill-index", selected["pack_id"])
        self.assertEqual("local_skill_index", selected["candidate_source"])
        self.assertEqual("scikit-learn", selected["skill"])
        self.assertEqual(str(skill_path), selected["skill_entrypoint"])
        self.assertEqual("local_installed", selected["authority"]["tier"])
        self.assertTrue(selected["authority"]["eligible"])
        self.assertNotIn("promotion_eligible", selected)
        self.assertNotIn("confirm_ui", route)

    def test_destructive_prompt_keeps_router_metadata_local_only(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir) / ".agents"
            skill_path = write_installed_skill(target_root, "scikit-learn")
            route = run_route(DESTRUCTIVE_PROMPT, target_root=target_root)

        selected = route["candidate_focus"]
        self.assertEqual("scikit-learn", selected["skill"])
        self.assertEqual(str(skill_path), selected["skill_entrypoint"])
        self.assertEqual("local_skill_index", selected["candidate_source"])
        self.assertNotIn("destructive", selected)
        self.assertNotIn("recommended_promotion_action", selected)

    def test_routine_edit_prompt_is_not_classified_as_destructive(self) -> None:
        assessment = run_helper_json(
            (
                "& { "
                f". '{HELPER_SCRIPT}'; "
                f"$result = Get-VgoDestructiveIntentAssessment -Prompt '{SAFE_EDIT_PROMPT}'; "
                "$result | ConvertTo-Json -Depth 20 }"
            )
        )

        self.assertFalse(assessment["destructive"])
        self.assertEqual([], as_list(assessment["destructive_reason_codes"]))
        self.assertFalse(assessment["rollback_possible"])
        self.assertFalse(assessment["snapshot_required"])

    def test_windows_style_path_prompt_is_classified_as_destructive(self) -> None:
        assessment = run_helper_json(
            (
                "& { "
                f". '{HELPER_SCRIPT}'; "
                f"$policy = Get-Content -LiteralPath '{EXECUTION_SAFETY_POLICY_PATH}' -Raw -Encoding UTF8 | ConvertFrom-Json; "
                f"$result = Get-VgoDestructiveIntentAssessment -Prompt '{WINDOWS_DESTRUCTIVE_PROMPT}' -ExecutionSafetyPolicy $policy; "
                "$result | ConvertTo-Json -Depth 20 }"
            )
        )

        self.assertTrue(assessment["destructive"])
        self.assertGreaterEqual(len(as_list(assessment["destructive_reason_codes"])), 1)
        self.assertTrue(assessment["rollback_possible"])
        self.assertTrue(assessment["snapshot_required"])

    def test_blank_contract_entries_do_not_count_as_complete(self) -> None:
        completeness = run_helper_json(
            (
                "& { "
                f". '{HELPER_SCRIPT}'; "
                "$result = Get-VgoSkillContractCompleteness "
                "-SkillMdPath '/tmp/skill.md' "
                "-Description 'desc' "
                "-RequiredInputs @('   ') "
                "-ExpectedOutputs @('') "
                "-VerificationExpectation 'verify'; "
                "$result | ConvertTo-Json -Depth 20 }"
            )
        )

        self.assertFalse(completeness["complete"])
        self.assertIn("required_inputs", as_list(completeness["missing_fields"]))
        self.assertIn("expected_outputs", as_list(completeness["missing_fields"]))

    def test_route_does_not_read_execution_safety_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            repo_copy = copy_repo_fixture(Path(tempdir))
            (repo_copy / "config" / "skill-execution-safety-policy.json").write_text(
                "{ invalid json",
                encoding="utf-8",
            )
            target_root = Path(tempdir) / ".agents"
            write_installed_skill(target_root, "scikit-learn")
            route = run_route(ML_PROMPT, repo_root=repo_copy, target_root=target_root)

        self.assertEqual("local-skill-index", route["candidate_focus"]["pack_id"])
