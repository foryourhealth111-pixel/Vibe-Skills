from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
INSTALL_SCRIPT_PS1 = REPO_ROOT / "install.ps1"
RUNTIME_TASK = "Debug installed runtime remap behavior before proposing fixes. $vibe"
HOST_HOME_ENV = {
    "claude-code": "VIBE_AGENTS_HOME",
}


def resolve_powershell() -> str | None:
    candidates = [
        shutil.which("pwsh"),
        shutil.which("pwsh.exe"),
        r"C:\Program Files\PowerShell\7\pwsh.exe",
        r"C:\Program Files\PowerShell\7-preview\pwsh.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))
    return None


def ps_quote(value: object) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def agent_direct_host_decision_json() -> str:
    return json.dumps(
        {
            "agent_skill_organization": {
                "schema_version": "agent_skill_organization_v1",
                "derived_by": "agent",
                "workflow_level": "XL",
                "modules": [
                    {
                        "module_id": "installed_policy_remap",
                        "goal": "Verify installed-runtime verification unit remapping.",
                        "candidate_skill_ids": [],
                        "execution_mode": "agent_direct",
                        "write_scope": "outputs/installed-policy-remap/**",
                        "expected_outputs": ["outputs/installed-policy-remap/verification.json"],
                        "verification": ["Check the installed-runtime policy remap and record the result."],
                        "acceptance_criteria": [
                            {
                                "criterion_id": "policy-remap-result",
                                "description": "The installed-runtime policy remap is verified.",
                                "verification_mode": "automated",
                            }
                        ],
                    }
                ],
                "selected_skills": [],
                "uncovered_modules": [],
                "workflow_level_contract": {
                    "L": "Use one serial governed lane.",
                    "XL": "Use bounded waves when the approved organization needs them.",
                },
            }
        }
    )


def install_claude_runtime(target_root: Path, env: dict[str, str]) -> Path:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    subprocess.run(
        [
            shell,
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(INSTALL_SCRIPT_PS1),
            "-SkillsDir",
            str(target_root / "skills"),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
        env=env,
    )
    return target_root / "skills" / "vibe"


def run_installed_runtime(installed_root: Path, *, artifact_root: Path, env: dict[str, str]) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    run_id = f"pytest-installed-remap-{uuid.uuid4().hex[:8]}"
    host_decision_json = agent_direct_host_decision_json()
    command = [
        shell,
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "& { "
            f"$result = & {ps_quote(installed_root / 'scripts' / 'runtime' / 'invoke-vibe-runtime.ps1')} "
            f"-Task {ps_quote(RUNTIME_TASK)} "
            "-Mode interactive_governed "
            f"-RunId {ps_quote(run_id)} "
            f"-ArtifactRoot {ps_quote(artifact_root)} "
            f"-HostDecisionJson {ps_quote(host_decision_json)}; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=installed_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=True,
    )
    stdout = completed.stdout.strip()
    if stdout in ("", "null"):
        raise AssertionError(f"installed invoke-vibe-runtime returned null payload. stderr={completed.stderr.strip()}")
    return json.loads(stdout)


class InstalledRuntimePolicyRemapTests(unittest.TestCase):
    def test_claude_installed_runtime_hands_off_without_retired_policy_units(self) -> None:
        sandbox_root = REPO_ROOT.parent / ".pytest-tmp-installed-runtime"
        sandbox_root.mkdir(parents=True, exist_ok=True)
        tempdir = tempfile.TemporaryDirectory(dir=str(sandbox_root))
        self.addCleanup(tempdir.cleanup)
        root = Path(tempdir.name)
        target_root = root / "claude-home"
        target_root.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        env[HOST_HOME_ENV["claude-code"]] = str(target_root)

        installed_root = install_claude_runtime(target_root, env)
        payload = run_installed_runtime(
            installed_root,
            artifact_root=target_root / ".vibeskills" / "simulated-remap",
            env={
                **env,
                "VCO_HOST_ID": "claude-code",
            },
        )

        execution_manifest_path = Path(payload["summary"]["artifacts"]["execution_manifest"])
        execution_manifest = json.loads(execution_manifest_path.read_text(encoding="utf-8"))
        unit_ids = {
            str(unit["unit_id"])
            for unit in execution_manifest["module_handoff"]["work_units"]
        }

        self.assertEqual("plan_execute", payload["summary"]["terminal_stage"])
        self.assertEqual("agent_action_required", execution_manifest["status"])
        self.assertEqual({"installed_policy_remap--agent--owner"}, unit_ids)
        self.assertIsNone(payload["summary"]["artifacts"]["cleanup_receipt"])
        self.assertIsNone(payload["summary"]["artifacts"]["memory_activation_report"])
        self.assertNotIn("installed-runtime-freshness-gate", unit_ids)
        self.assertNotIn("runtime-neutral-freshness-gate-tests", unit_ids)
        self.assertNotIn("release-install-runtime-coherence-gate", unit_ids)


if __name__ == "__main__":
    unittest.main()
