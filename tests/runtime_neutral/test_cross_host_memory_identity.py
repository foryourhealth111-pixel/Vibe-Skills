from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_CORE_SRC = REPO_ROOT / "packages" / "runtime-core" / "src"
if str(RUNTIME_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_CORE_SRC))

RUNTIME_COMMON = REPO_ROOT / "scripts" / "runtime" / "VibeRuntime.Common.ps1"


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


def _ps_single_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def run_ps_json(body: str) -> dict[str, object] | list[dict[str, object]]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    completed = subprocess.run(
        [shell, "-NoLogo", "-NoProfile", "-Command", body],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return json.loads(completed.stdout)


class CrossHostMemoryIdentityTests(unittest.TestCase):
    def test_runtime_core_workspace_memory_identity_is_host_agnostic(self) -> None:
        from vgo_runtime.workspace_memory import build_workspace_memory_identity

        with tempfile.TemporaryDirectory() as tempdir:
            workspace_root = Path(tempdir) / "workspace"
            workspace_root.mkdir(parents=True, exist_ok=True)
            expected_identity_root = str((workspace_root / ".vibeskills" / "project.json").resolve())

            codex_identity = build_workspace_memory_identity(
                workspace_root=workspace_root,
                host_id="codex",
            ).model_dump()
            claude_identity = build_workspace_memory_identity(
                workspace_root=workspace_root,
                host_id="claude-code",
            ).model_dump()

        self.assertEqual(expected_identity_root, codex_identity["identity_root"])
        self.assertEqual(expected_identity_root, claude_identity["identity_root"])
        self.assertEqual(codex_identity["workspace_id"], claude_identity["workspace_id"])
        self.assertEqual(codex_identity["identity_root"], claude_identity["identity_root"])

    def test_runtime_core_workspace_memory_identity_changes_with_workspace(self) -> None:
        from vgo_runtime.workspace_memory import build_workspace_memory_identity

        with tempfile.TemporaryDirectory() as tempdir:
            base = Path(tempdir)
            workspace_a = base / "workspace-a"
            workspace_b = base / "workspace-b"
            workspace_a.mkdir(parents=True, exist_ok=True)
            workspace_b.mkdir(parents=True, exist_ok=True)

            identity_a = build_workspace_memory_identity(workspace_root=workspace_a, host_id="codex").model_dump()
            identity_b = build_workspace_memory_identity(workspace_root=workspace_b, host_id="codex").model_dump()

        self.assertNotEqual(identity_a["workspace_id"], identity_b["workspace_id"])
        self.assertNotEqual(identity_a["identity_root"], identity_b["identity_root"])

    def test_workspace_artifact_projection_keeps_identity_root_stable_across_hosts(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            workspace_root = Path(tempdir) / "workspace"
            host_a_root = Path(tempdir) / "host-a"
            host_b_root = Path(tempdir) / "host-b"
            workspace_root.mkdir(parents=True, exist_ok=True)
            host_a_root.mkdir(parents=True, exist_ok=True)
            host_b_root.mkdir(parents=True, exist_ok=True)
            workspace_root_text = str(workspace_root.resolve())

            payload = run_ps_json(
                "& { "
                f". {_ps_single_quote(str(RUNTIME_COMMON))}; "
                "$runtimeA = [pscustomobject]@{ host_settings = [pscustomobject]@{ "
                f"target_root = {_ps_single_quote(str(host_a_root.resolve()))} "
                "} }; "
                "$runtimeB = [pscustomobject]@{ host_settings = [pscustomobject]@{ "
                f"target_root = {_ps_single_quote(str(host_b_root.resolve()))} "
                "} }; "
                "$first = New-VibeWorkspaceArtifactProjection "
                f"-RepoRoot {_ps_single_quote(workspace_root_text)} "
                "-Runtime $runtimeA "
                "-ArtifactRoot ''; "
                "$second = New-VibeWorkspaceArtifactProjection "
                f"-RepoRoot {_ps_single_quote(workspace_root_text)} "
                "-Runtime $runtimeB "
                "-ArtifactRoot ''; "
                "@($first, $second) | ConvertTo-Json -Depth 10 }"
            )

        expected_identity_root = f"{workspace_root_text}/.vibeskills/project.json"
        self.assertEqual(expected_identity_root, payload[0]["workspace_memory_identity_root"])
        self.assertEqual(expected_identity_root, payload[1]["workspace_memory_identity_root"])
        self.assertEqual(payload[0]["workspace_memory_identity_scope"], payload[1]["workspace_memory_identity_scope"])
        self.assertEqual(
            payload[0]["workspace_memory_driver_contract"],
            payload[1]["workspace_memory_driver_contract"],
        )
        self.assertNotEqual(payload[0]["host_sidecar_root"], payload[1]["host_sidecar_root"])

    def test_workspace_driver_projection_matches_runtime_core_identity_contract(self) -> None:
        from vgo_runtime.workspace_memory import build_workspace_memory_identity

        spec = importlib.util.spec_from_file_location(
            "workspace_memory_driver_contract",
            REPO_ROOT / "scripts" / "runtime" / "workspace_memory_driver.py",
        )
        if spec is None or spec.loader is None:
            raise AssertionError("unable to load workspace_memory_driver.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as tempdir:
            workspace_root = Path(tempdir) / "workspace"
            workspace_root.mkdir(parents=True, exist_ok=True)

            runtime_identity = build_workspace_memory_identity(workspace_root=workspace_root).model_dump()
            descriptor = module.ensure_workspace_descriptor(workspace_root)
            driver_projection = module.workspace_memory_projection(
                descriptor,
                module.resolve_plane_path(descriptor),
            )

        self.assertEqual(runtime_identity["workspace_id"], driver_projection["workspace_id"])


if __name__ == "__main__":
    unittest.main()
