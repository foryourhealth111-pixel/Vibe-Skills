from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


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


class RuntimeEntrypointHelperTests(unittest.TestCase):
    def test_repo_root_resolution_prefers_nearest_governed_git_root_for_worktree_like_layout(self) -> None:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell not available")

        with tempfile.TemporaryDirectory() as tempdir:
            outer_root = Path(tempdir) / "outer-repo"
            worktree_root = outer_root / ".worktrees" / "feature-a"
            common_dir = worktree_root / "scripts" / "common"
            common_dir.mkdir(parents=True, exist_ok=True)
            (common_dir / "vibe-governance-helpers.ps1").write_text(
                (REPO_ROOT / "scripts" / "common" / "vibe-governance-helpers.ps1").read_text(encoding="utf-8"),
                encoding="utf-8",
                newline="\n",
            )

            (outer_root / "config").mkdir(parents=True, exist_ok=True)
            (worktree_root / "config").mkdir(parents=True, exist_ok=True)
            (outer_root / "config" / "version-governance.json").write_text("{}", encoding="utf-8", newline="\n")
            (worktree_root / "config" / "version-governance.json").write_text("{}", encoding="utf-8", newline="\n")
            (outer_root / ".git").mkdir(parents=True, exist_ok=True)
            (worktree_root / ".git").write_text("gitdir: /tmp/fake-worktree-git\n", encoding="utf-8", newline="\n")

            script_path = worktree_root / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"
            script_path.parent.mkdir(parents=True, exist_ok=True)
            script_path.write_text("Write-Host 'runtime'\n", encoding="utf-8", newline="\n")

            ps_script = (
                "& { "
                f". '{common_dir / 'vibe-governance-helpers.ps1'}'; "
                f"$resolved = Resolve-VgoRepoRoot -StartPath '{script_path}'; "
                "[pscustomobject]@{ resolved = $resolved } | ConvertTo-Json -Depth 5 }"
            )

            completed = subprocess.run(
                [powershell, "-NoLogo", "-NoProfile", "-Command", ps_script],
                cwd=worktree_root,
                capture_output=True,
                text=True,
                check=True,
            )

            payload = json.loads(completed.stdout)
            self.assertEqual(str(worktree_root.resolve()), payload["resolved"])

    def test_helper_resolves_contract_default_runtime_entrypoint_when_effective_config_is_absent(self) -> None:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell not available")

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            common_dir = root / "scripts" / "common"
            common_dir.mkdir(parents=True, exist_ok=True)
            (common_dir / "vibe-governance-helpers.ps1").write_text(
                (REPO_ROOT / "scripts" / "common" / "vibe-governance-helpers.ps1").read_text(encoding="utf-8"),
                encoding="utf-8",
                newline="\n",
            )
            (common_dir / "runtime_contracts.py").write_text(
                (REPO_ROOT / "scripts" / "common" / "runtime_contracts.py").read_text(encoding="utf-8"),
                encoding="utf-8",
                newline="\n",
            )

            ps_script = (
                "& { "
                f". '{common_dir / 'vibe-governance-helpers.ps1'}'; "
                f"$resolved = Get-VgoRuntimeEntrypointPath -RepoRoot '{root}' -RuntimeConfig $null; "
                "[pscustomobject]@{ resolved = $resolved } | ConvertTo-Json -Depth 5 }"
            )

            completed = subprocess.run(
                [powershell, "-NoLogo", "-NoProfile", "-Command", ps_script],
                cwd=root,
                capture_output=True,
                text=True,
                check=True,
            )

            payload = json.loads(completed.stdout)
            self.assertEqual(
                str((root / "scripts" / "runtime" / "invoke-vibe-runtime.ps1").resolve()),
                payload["resolved"],
            )

    def test_helper_uses_emergency_fallback_when_contract_bridge_is_missing(self) -> None:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell not available")

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            common_dir = root / "scripts" / "common"
            common_dir.mkdir(parents=True, exist_ok=True)
            (common_dir / "vibe-governance-helpers.ps1").write_text(
                (REPO_ROOT / "scripts" / "common" / "vibe-governance-helpers.ps1").read_text(encoding="utf-8"),
                encoding="utf-8",
                newline="\n",
            )

            ps_script = (
                "& { "
                f". '{common_dir / 'vibe-governance-helpers.ps1'}'; "
                "$fallback = Get-VgoInstalledRuntimeFallbackDefaults; "
                f"$resolved = Get-VgoRuntimeEntrypointPath -RepoRoot '{root}' -RuntimeConfig $null; "
                "[pscustomobject]@{ markers = @($fallback.required_runtime_markers); resolved = $resolved } | ConvertTo-Json -Depth 5 }"
            )

            completed = subprocess.run(
                [powershell, "-NoLogo", "-NoProfile", "-Command", ps_script],
                cwd=root,
                capture_output=True,
                text=True,
                check=True,
            )

            payload = json.loads(completed.stdout)
            self.assertEqual(
                [
                    "SKILL.md",
                    "config/version-governance.json",
                    "scripts/common/vibe-governance-helpers.ps1",
                    "scripts/runtime/invoke-vibe-runtime.ps1",
                    "scripts/router/resolve-pack-route.ps1",
                ],
                payload["markers"],
            )
            self.assertEqual(
                str((root / "scripts" / "runtime" / "invoke-vibe-runtime.ps1").resolve()),
                payload["resolved"],
            )

    def test_helper_resolves_runtime_entrypoint_override_from_effective_runtime_config(self) -> None:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell not available")

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            common_dir = root / "scripts" / "common"
            common_dir.mkdir(parents=True, exist_ok=True)
            (common_dir / "vibe-governance-helpers.ps1").write_text(
                (REPO_ROOT / "scripts" / "common" / "vibe-governance-helpers.ps1").read_text(encoding="utf-8"),
                encoding="utf-8",
                newline="\n",
            )
            (common_dir / "runtime_contracts.py").write_text(
                (REPO_ROOT / "scripts" / "common" / "runtime_contracts.py").read_text(encoding="utf-8"),
                encoding="utf-8",
                newline="\n",
            )

            ps_script = (
                "& { "
                f". '{common_dir / 'vibe-governance-helpers.ps1'}'; "
                "$governance = [pscustomobject]@{ runtime = [pscustomobject]@{ installed_runtime = [pscustomobject]@{ runtime_entrypoint = 'scripts/runtime/custom-entry.ps1' } } }; "
                "$runtimeConfig = Get-VgoInstalledRuntimeConfig -Governance $governance; "
                f"$resolved = Get-VgoRuntimeEntrypointPath -RepoRoot '{root}' -RuntimeConfig $runtimeConfig; "
                "[pscustomobject]@{ runtime_entrypoint = $runtimeConfig.runtime_entrypoint; resolved = $resolved } | ConvertTo-Json -Depth 5 }"
            )

            completed = subprocess.run(
                [powershell, "-NoLogo", "-NoProfile", "-Command", ps_script],
                cwd=root,
                capture_output=True,
                text=True,
                check=True,
            )

            payload = json.loads(completed.stdout)
            self.assertEqual("scripts/runtime/custom-entry.ps1", payload["runtime_entrypoint"])
            self.assertEqual(str((root / "scripts" / "runtime" / "custom-entry.ps1").resolve()), payload["resolved"])

    def test_path_within_root_requires_directory_boundary(self) -> None:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell not available")

        helper_path = REPO_ROOT / "scripts" / "runtime" / "VibeRuntime.Common.ps1"
        root = str((REPO_ROOT / "dist" / "host-codex").resolve())
        inside_candidate = str((REPO_ROOT / "dist" / "host-codex" / "bundled" / "skills" / "pdf" / "SKILL.md").resolve())
        sibling_candidate = str((REPO_ROOT / "dist" / "host-codex-shadow" / "bundled" / "skills" / "pdf" / "SKILL.md").resolve())

        ps_script = (
            "& { "
            f". '{helper_path}'; "
            f"$inside = Test-VibePathWithinRoot -RootPath '{root}' -CandidatePath '{inside_candidate}'; "
            f"$sibling = Test-VibePathWithinRoot -RootPath '{root}' -CandidatePath '{sibling_candidate}'; "
            "[pscustomobject]@{ inside = $inside; sibling = $sibling } | ConvertTo-Json -Depth 5 }"
        )

        completed = subprocess.run(
            [powershell, "-NoLogo", "-NoProfile", "-Command", ps_script],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )

        payload = json.loads(completed.stdout)
        self.assertTrue(payload["inside"])
        self.assertFalse(payload["sibling"])


if __name__ == "__main__":
    unittest.main()
