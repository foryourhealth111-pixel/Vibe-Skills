from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

from tests.runtime_neutral.live_contract_fixtures import (
    seed_live_document_contract as _seed_live_document_contract,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_CORE_SRC = REPO_ROOT / "packages" / "runtime-core" / "src"
if str(RUNTIME_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_CORE_SRC))

COMPAT_DRIVER = REPO_ROOT / "scripts" / "runtime" / "memory_backend_driver.py"
WORKSPACE_DRIVER = REPO_ROOT / "scripts" / "runtime" / "workspace_memory_driver.py"
GOVERNANCE_HELPERS = REPO_ROOT / "scripts" / "common" / "vibe-governance-helpers.ps1"
RUNTIME_COMMON = REPO_ROOT / "scripts" / "runtime" / "VibeRuntime.Common.ps1"
MEMORY_BACKENDS_COMMON = REPO_ROOT / "scripts" / "runtime" / "VibeMemoryBackends.Common.ps1"
WORKSPACE_MEMORY_COMMON = REPO_ROOT / "scripts" / "runtime" / "VibeWorkspaceMemory.Common.ps1"

def _seed_workspace_driver_dependencies(workspace_root: Path) -> None:
    _seed_live_document_contract(workspace_root)
    shutil.copytree(
        REPO_ROOT / "packages" / "contracts",
        workspace_root / "packages" / "contracts",
        dirs_exist_ok=True,
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


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


def run_driver(
    script_path: Path,
    *,
    lane: str,
    action: str,
    payload: dict[str, Any],
    repo_root: Path,
    session_root: Path,
    store_path: Path,
    project_key: str | None = None,
    driver_mode: str | None = None,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> dict[str, Any]:
    payload_path = session_root / f"{script_path.stem}-{lane}-{action}-request.json"
    response_path = session_root / f"{script_path.stem}-{lane}-{action}-response.json"
    _write_json(payload_path, payload)
    response_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        str(script_path),
        "--lane",
        lane,
        "--action",
        action,
        "--repo-root",
        str(repo_root),
        "--session-root",
        str(session_root),
        "--store-path",
        str(store_path),
        "--payload-path",
        str(payload_path),
        "--response-path",
        str(response_path),
    ]
    if project_key:
        command.extend(["--project-key", project_key])
    if driver_mode:
        command.extend(["--driver-mode", driver_mode])

    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=check,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, **(env or {})},
    )
    if not check:
        return {
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "response_path": str(response_path),
        }
    return json.loads(response_path.read_text(encoding="utf-8"))


def run_workspace_memory_common_json(
    command_body: str,
    *,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> object | subprocess.CompletedProcess[str]:
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
            (
                "& { "
                f". {_ps_single_quote(str(GOVERNANCE_HELPERS))}; "
                f". {_ps_single_quote(str(WORKSPACE_MEMORY_COMMON))}; "
                f"{command_body} "
                "}"
            ),
        ],
        cwd=REPO_ROOT,
        check=check,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, **(env or {})},
    )
    if not check:
        return completed

    stdout = completed.stdout.strip()
    if stdout in ("", "null"):
        return None
    return json.loads(stdout)


class WorkspaceSharedMemoryPlaneTests(unittest.TestCase):
    def test_relocated_workspace_keeps_memory_writes_local(self) -> None:
        for move in (False, True):
            with self.subTest(move=move), tempfile.TemporaryDirectory() as tempdir:
                root = Path(tempdir)
                original = root / "original"
                relocated = root / "relocated"
                session = root / "session"
                original.mkdir()
                _seed_live_document_contract(original)
                original_write = run_driver(
                    WORKSPACE_DRIVER, lane="serena", action="write",
                    payload={"decisions": [{"summary": "Synthetic fixture: original architecture decision."}]},
                    repo_root=original, session_root=session, store_path=root / "unused.jsonl",
                    project_key="relocation-fixture",
                )
                original_plane = Path(original_write["store_path"])
                original_content = original_plane.read_bytes()
                if move:
                    original.rename(relocated)
                else:
                    shutil.copytree(original, relocated)
                result = run_driver(
                    WORKSPACE_DRIVER, lane="serena", action="write",
                    payload={"decisions": [{"summary": "Synthetic fixture: relocated architecture decision."}]},
                    repo_root=relocated, session_root=session, store_path=root / "unused.jsonl",
                    project_key="relocation-fixture",
                )
                expected_plane = relocated / ".vibeskills/memory/workspace-memory-plane.jsonl"
                self.assertEqual("backend_write", result["status"])
                self.assertEqual(expected_plane.resolve(), Path(result["store_path"]).resolve())
                descriptor = json.loads((relocated / ".vibeskills/project.json").read_text(encoding="utf-8"))
                self.assertEqual(str(relocated.resolve()), descriptor["workspace_root"])
                self.assertEqual(str((relocated / ".vibeskills").resolve()), descriptor["default_artifact_root"])
                if move:
                    self.assertFalse(original.exists())
                else:
                    self.assertEqual(original_content, original_plane.read_bytes())
                read = run_driver(
                    WORKSPACE_DRIVER, lane="serena", action="read",
                    payload={"task": "relocated architecture decision", "top_k": 5},
                    repo_root=relocated, session_root=session, store_path=root / "unused.jsonl",
                    project_key="relocation-fixture",
                )
                self.assertTrue(any("relocated architecture decision" in item for item in read["items"]))

    def test_compatibility_shell_hard_fails_when_workspace_broker_is_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            repo_root = temp_root / "workspace"
            session_root = temp_root / "session"
            repo_root.mkdir(parents=True, exist_ok=True)
            session_root.mkdir(parents=True, exist_ok=True)

            isolated_driver_root = temp_root / "isolated-runtime"
            isolated_driver_root.mkdir(parents=True, exist_ok=True)
            isolated_driver = isolated_driver_root / "memory_backend_driver.py"
            isolated_driver.write_text(COMPAT_DRIVER.read_text(encoding="utf-8"), encoding="utf-8")

            result = run_driver(
                isolated_driver,
                lane="serena",
                action="write",
                payload={
                    "decisions": [
                        {
                            "summary": "Approved decision: workspace broker failure must not fall back to legacy storage.",
                            "evidence_paths": ["docs/design/workspace-memory-plane.md"],
                            "keywords": ["approved", "decision", "workspace", "broker", "hard-fail"],
                        }
                    ]
                },
                repo_root=repo_root,
                session_root=session_root,
                store_path=temp_root / "legacy-serena.jsonl",
                project_key="workspace-plane-contract",
                check=False,
            )

            self.assertNotEqual(0, result["returncode"])
            self.assertFalse(Path(result["response_path"]).exists())
            self.assertFalse((temp_root / "legacy-serena.jsonl").exists())

    def test_compatibility_shell_rejects_explicit_legacy_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            repo_root = temp_root / "workspace"
            session_root = temp_root / "session"
            repo_root.mkdir(parents=True, exist_ok=True)
            session_root.mkdir(parents=True, exist_ok=True)

            result = run_driver(
                COMPAT_DRIVER,
                lane="serena",
                action="write",
                payload={
                    "decisions": [
                        {
                            "summary": "Approved decision: explicit legacy mode is forbidden under workspace memory governance.",
                            "evidence_paths": ["docs/design/workspace-memory-plane.md"],
                            "keywords": ["approved", "decision", "legacy", "forbidden"],
                        }
                    ]
                },
                repo_root=repo_root,
                session_root=session_root,
                store_path=temp_root / "legacy-serena.jsonl",
                project_key="workspace-plane-contract",
                driver_mode="legacy",
                check=False,
            )

            self.assertNotEqual(0, result["returncode"])
            self.assertFalse(Path(result["response_path"]).exists())
            self.assertFalse((temp_root / "legacy-serena.jsonl").exists())

    def test_compatibility_shell_rejects_configured_legacy_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            repo_root = temp_root / "workspace"
            session_root = temp_root / "session"
            repo_root.mkdir(parents=True, exist_ok=True)
            session_root.mkdir(parents=True, exist_ok=True)

            result = run_driver(
                COMPAT_DRIVER,
                lane="serena",
                action="write",
                payload={
                    "decisions": [
                        {
                            "summary": "Approved decision: configured legacy compatibility mode is forbidden under workspace memory governance.",
                            "evidence_paths": ["docs/design/workspace-memory-plane.md"],
                            "keywords": ["approved", "decision", "legacy", "forbidden", "env"],
                        }
                    ]
                },
                repo_root=repo_root,
                session_root=session_root,
                store_path=temp_root / "legacy-serena.jsonl",
                project_key="workspace-plane-contract",
                env={"VIBE_MEMORY_BACKEND_DRIVER_MODE": "legacy"},
                check=False,
            )

            self.assertNotEqual(0, result["returncode"])
            self.assertFalse(Path(result["response_path"]).exists())
            self.assertFalse((temp_root / "legacy-serena.jsonl").exists())

    def test_powershell_workspace_bridge_routes_through_compatibility_shell(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            raise unittest.SkipTest("PowerShell executable not available in PATH")

        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            repo_root = temp_root / "workspace"
            session_root = temp_root / "session"
            repo_root.mkdir(parents=True, exist_ok=True)
            session_root.mkdir(parents=True, exist_ok=True)
            _seed_workspace_driver_dependencies(repo_root)
            runtime_script_root = repo_root / "scripts" / "runtime"
            runtime_script_root.mkdir(parents=True, exist_ok=True)
            (runtime_script_root / "memory_backend_driver.py").write_text(
                COMPAT_DRIVER.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            (runtime_script_root / "workspace_memory_driver.py").write_text(
                WORKSPACE_DRIVER.read_text(encoding="utf-8"),
                encoding="utf-8",
            )

            runtime_payload = {
                "repo_root": str(repo_root),
                "memory_backend_adapters": {
                    **json.loads((REPO_ROOT / "config" / "memory-backend-adapters.json").read_text(encoding="utf-8")),
                    "driver": {
                        "command": sys.executable,
                        "script_path": "scripts/runtime/memory_backend_driver.py",
                        "transport": "payload_file",
                    },
                },
            }
            payload = {
                "decisions": [
                    {
                        "summary": "Approved decision: PowerShell bridge must route through the compatibility shell into the workspace broker.",
                        "evidence_paths": ["docs/design/workspace-memory-plane.md"],
                        "keywords": ["approved", "decision", "powershell", "workspace", "broker"],
                    }
                ]
            }

            command = [
                shell,
                "-NoLogo",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                (
                    "& { "
                    f". {_ps_single_quote(str(GOVERNANCE_HELPERS))}; "
                    f". {_ps_single_quote(str(RUNTIME_COMMON))}; "
                    f". {_ps_single_quote(str(MEMORY_BACKENDS_COMMON))}; "
                    f". {_ps_single_quote(str(WORKSPACE_MEMORY_COMMON))}; "
                    f"$env:SERENA_PROJECT_KEY = {_ps_single_quote('workspace-plane-contract')}; "
                    f"$runtime = {_ps_single_quote(json.dumps(runtime_payload, ensure_ascii=False))} | ConvertFrom-Json -Depth 20; "
                    f"$payload = {_ps_single_quote(json.dumps(payload, ensure_ascii=False))} | ConvertFrom-Json -Depth 20; "
                    "$result = Invoke-VibeWorkspaceMemoryAction "
                    "-Runtime $runtime "
                    "-LaneId 'serena' "
                    "-Action 'write' "
                    "-Payload $payload "
                    f"-SessionRoot {_ps_single_quote(str(session_root))}; "
                    "$result | ConvertTo-Json -Depth 20 }"
                ),
            ]

            completed = subprocess.run(
                command,
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            result = json.loads(completed.stdout)
            self.assertEqual("backend_write", result["status"])
            self.assertEqual(1, result["capsule_count"])
            self.assertTrue(Path(result["artifact_path"]).exists())

            backend_response = json.loads(Path(result["artifact_path"]).read_text(encoding="utf-8"))
            self.assertEqual("compatibility_shell", backend_response["driver_mode"])
            self.assertEqual(1, backend_response["capsule_count"])

    def test_powershell_workspace_bridge_defaults_driver_when_runtime_driver_config_is_missing(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            raise unittest.SkipTest("PowerShell executable not available in PATH")

        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            repo_root = temp_root / "workspace"
            session_root = temp_root / "session"
            repo_root.mkdir(parents=True, exist_ok=True)
            session_root.mkdir(parents=True, exist_ok=True)
            _seed_workspace_driver_dependencies(repo_root)
            runtime_script_root = repo_root / "scripts" / "runtime"
            runtime_script_root.mkdir(parents=True, exist_ok=True)
            (runtime_script_root / "workspace_memory_driver.py").write_text(
                WORKSPACE_DRIVER.read_text(encoding="utf-8"),
                encoding="utf-8",
            )

            runtime_payload = {
                "repo_root": str(repo_root),
                "memory_backend_adapters": {
                    key: value
                    for key, value in json.loads(
                        (REPO_ROOT / "config" / "memory-backend-adapters.json").read_text(encoding="utf-8")
                    ).items()
                    if key != "driver"
                },
            }
            payload = {
                "decisions": [
                    {
                        "summary": "Approved decision: missing runtime driver config should still use the workspace broker defaults.",
                        "evidence_paths": ["docs/design/workspace-memory-plane.md"],
                        "keywords": ["approved", "decision", "workspace", "broker", "defaults"],
                    }
                ]
            }

            completed = subprocess.run(
                [
                    shell,
                    "-NoLogo",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    (
                        "& { "
                        f". {_ps_single_quote(str(GOVERNANCE_HELPERS))}; "
                        f". {_ps_single_quote(str(RUNTIME_COMMON))}; "
                        f". {_ps_single_quote(str(MEMORY_BACKENDS_COMMON))}; "
                        f". {_ps_single_quote(str(WORKSPACE_MEMORY_COMMON))}; "
                        f"$env:SERENA_PROJECT_KEY = {_ps_single_quote('workspace-plane-defaults')}; "
                        f"$runtime = {_ps_single_quote(json.dumps(runtime_payload, ensure_ascii=False))} | ConvertFrom-Json -Depth 20; "
                        f"$payload = {_ps_single_quote(json.dumps(payload, ensure_ascii=False))} | ConvertFrom-Json -Depth 20; "
                        "$result = Invoke-VibeWorkspaceMemoryAction "
                        "-Runtime $runtime "
                        "-LaneId 'serena' "
                        "-Action 'write' "
                        "-Payload $payload "
                        f"-SessionRoot {_ps_single_quote(str(session_root))}; "
                        "$result | ConvertTo-Json -Depth 20 }"
                    ),
                ],
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            result = json.loads(completed.stdout)

            self.assertEqual("backend_write", result["status"])
            self.assertEqual(1, result["capsule_count"])
            self.assertIn("workspace_id", result["workspace_memory_plane"])
            self.assertTrue(Path(result["workspace_memory_plane"]["plane_path"]).exists())

    def test_workspace_memory_common_guards_missing_nested_driver_properties_under_strict_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            repo_root = Path(tempdir) / "workspace"
            repo_root.mkdir(parents=True, exist_ok=True)

            result = run_workspace_memory_common_json(
                f"""
                $runtime = [pscustomobject]@{{
                    repo_root = {_ps_single_quote(str(repo_root))}
                }}
                $commandSpec = Resolve-VibeWorkspaceMemoryCommandSpec -Runtime $runtime
                $result = [pscustomobject]@{{
                    path = Get-VibeWorkspaceMemoryDriverScriptPath -Runtime $runtime
                    host_path = $commandSpec.host_path
                }}
                $result | ConvertTo-Json -Depth 10
                """,
                env={"VGO_PYTHON": sys.executable},
            )

        assert isinstance(result, dict)
        self.assertEqual(
            str((repo_root / "scripts" / "runtime" / "workspace_memory_driver.py").resolve()),
            result["path"],
        )
        self.assertEqual(sys.executable, result["host_path"])

    def test_compatibility_shell_accepts_workspace_driver_mode_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            repo_root = temp_root / "workspace"
            session_root = temp_root / "session"
            repo_root.mkdir(parents=True, exist_ok=True)
            session_root.mkdir(parents=True, exist_ok=True)
            _seed_live_document_contract(repo_root)

            result = run_driver(
                COMPAT_DRIVER,
                lane="serena",
                action="write",
                payload={
                    "decisions": [
                        {
                            "summary": "Approved decision: compatibility shell must accept explicit workspace broker mode.",
                            "evidence_paths": ["docs/design/workspace-memory-plane.md"],
                            "keywords": ["approved", "decision", "compatibility", "workspace", "broker"],
                        }
                    ]
                },
                repo_root=repo_root,
                session_root=session_root,
                store_path=temp_root / "legacy-serena.jsonl",
                project_key="workspace-plane-contract",
                driver_mode="workspace_broker",
            )

            self.assertEqual("backend_write", result["status"])
            self.assertEqual("compatibility_shell", result["driver_mode"])
            self.assertEqual(1, result["capsule_count"])

    def test_compatibility_shell_routes_multiple_lanes_to_single_workspace_plane(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            repo_root = temp_root / "workspace"
            session_root = temp_root / "session"
            repo_root.mkdir(parents=True, exist_ok=True)
            session_root.mkdir(parents=True, exist_ok=True)
            _seed_live_document_contract(repo_root)

            serena_write = run_driver(
                COMPAT_DRIVER,
                lane="serena",
                action="write",
                payload={
                    "decisions": [
                        {
                            "summary": "Approved decision: keep compatibility shell around the workspace broker.",
                            "evidence_paths": ["docs/requirements/frozen.md"],
                            "keywords": ["approved", "decision", "compatibility", "workspace"],
                        }
                    ]
                },
                repo_root=repo_root,
                session_root=session_root,
                store_path=temp_root / "legacy-serena.jsonl",
                project_key="workspace-plane-contract",
            )
            self.assertEqual("backend_write", serena_write["status"])
            self.assertEqual("compatibility_shell", serena_write["driver_mode"])
            self.assertIn("workspace_memory_plane", serena_write)
            self.assertIn("capsules", serena_write)
            self.assertTrue(Path(serena_write["workspace_memory_plane"]["plane_path"]).exists())
            self.assertEqual(1, serena_write["capsule_count"])

            cognee_write = run_driver(
                COMPAT_DRIVER,
                lane="cognee",
                action="write",
                payload={
                    "relations": [
                        {
                            "source": "workspace-memory-plane",
                            "relation": "implemented_in",
                            "target": "compatibility-shell",
                            "evidence_paths": ["docs/design/workspace-memory-plane.md"],
                            "keywords": ["workspace", "broker", "compatibility"],
                        }
                    ]
                },
                repo_root=repo_root,
                session_root=session_root,
                store_path=temp_root / "legacy-cognee.jsonl",
                project_key="workspace-plane-contract",
            )
            self.assertEqual("backend_write", cognee_write["status"])
            self.assertEqual(
                serena_write["workspace_memory_plane"]["plane_path"],
                cognee_write["workspace_memory_plane"]["plane_path"],
            )

            serena_read = run_driver(
                COMPAT_DRIVER,
                lane="serena",
                action="read",
                payload={"task": "compatibility shell decision reuse", "top_k": 3},
                repo_root=repo_root,
                session_root=session_root,
                store_path=temp_root / "legacy-serena.jsonl",
                project_key="workspace-plane-contract",
            )
            self.assertEqual("backend_read", serena_read["status"])
            self.assertGreaterEqual(serena_read["capsule_count"], 1)
            self.assertIn("Serena decision:", " ".join(serena_read["items"]))
            self.assertEqual(
                serena_write["workspace_memory_plane"]["workspace_id"],
                serena_read["workspace_memory_plane"]["workspace_id"],
            )

            cognee_read = run_driver(
                COMPAT_DRIVER,
                lane="cognee",
                action="read",
                payload={"task": "graph relation for workspace broker", "top_k": 3},
                repo_root=repo_root,
                session_root=session_root,
                store_path=temp_root / "legacy-cognee.jsonl",
                project_key="workspace-plane-contract",
            )
            self.assertEqual("backend_read", cognee_read["status"])
            self.assertGreaterEqual(cognee_read["capsule_count"], 1)
            self.assertIn("Cognee relation:", " ".join(cognee_read["items"]))

    def test_workspace_driver_hides_legacy_store_path_behind_broker_plane(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            repo_root = temp_root / "workspace"
            session_root = temp_root / "session"
            repo_root.mkdir(parents=True, exist_ok=True)
            session_root.mkdir(parents=True, exist_ok=True)
            _seed_live_document_contract(repo_root)
            legacy_store_path = temp_root / "legacy-ruflo.jsonl"

            result = run_driver(
                WORKSPACE_DRIVER,
                lane="ruflo",
                action="write",
                payload={
                    "run_id": "run-shared-plane-01",
                    "task": "handoff card for workspace-memory continuity",
                    "cards": [
                        {
                            "scope": "xl",
                            "summary": "XL handoff keeps workspace-memory continuity.",
                            "items": ["execution_status:completed"],
                            "evidence_paths": ["outputs/runtime/vibe-sessions/run-shared-plane-01/execution-manifest.json"],
                            "keywords": ["handoff", "workspace", "continuity"],
                        }
                    ],
                },
                repo_root=repo_root,
                session_root=session_root,
                store_path=legacy_store_path,
                project_key="workspace-plane-contract",
            )

            self.assertEqual("backend_write", result["status"])
            self.assertIn("workspace_memory_plane", result)
            self.assertNotEqual(str(legacy_store_path), result["workspace_memory_plane"]["plane_path"])
            self.assertEqual(result["workspace_memory_plane"]["plane_path"], result["store_path"])
            self.assertEqual("workspace_plane", result["project_key_source"])

    def test_workspace_driver_reconciles_descriptor_with_memory_plane_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            repo_root = temp_root / "workspace"
            session_root = temp_root / "session"
            repo_root.mkdir(parents=True, exist_ok=True)
            session_root.mkdir(parents=True, exist_ok=True)
            _seed_live_document_contract(repo_root)

            run_driver(
                WORKSPACE_DRIVER,
                lane="serena",
                action="write",
                payload={
                    "decisions": [
                        {
                            "summary": "Approved decision: broker-first workspace initialization must preserve descriptor contract.",
                            "evidence_paths": ["docs/design/workspace-memory-plane.md"],
                            "keywords": ["approved", "decision", "workspace", "descriptor"],
                        }
                    ]
                },
                repo_root=repo_root,
                session_root=session_root,
                store_path=temp_root / "legacy-serena.jsonl",
                project_key="workspace-plane-contract",
            )

            descriptor = json.loads((repo_root / ".vibeskills" / "project.json").read_text(encoding="utf-8"))
            memory_plane = descriptor["memory_plane"]
            expected_identity_root = str((repo_root / ".vibeskills" / "project.json").resolve())

            self.assertEqual(expected_identity_root, memory_plane["identity_root"])
            self.assertEqual("workspace", memory_plane["identity_scope"])
            self.assertEqual("workspace_shared_memory_v1", memory_plane["driver_contract"])
            self.assertEqual(["state_store", "serena", "ruflo", "cognee"], memory_plane["logical_owners"])


class CodexMemoryUserSimulationTests(unittest.TestCase):
    def test_codex_follow_up_surfaces_only_relevant_serena_memory(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            repo_root = temp_root / "workspace"
            session_root = temp_root / "session"
            repo_root.mkdir(parents=True, exist_ok=True)
            session_root.mkdir(parents=True, exist_ok=True)
            _seed_live_document_contract(repo_root)

            run_driver(
                COMPAT_DRIVER,
                lane="serena",
                action="write",
                payload={
                    "decisions": [
                        {
                            "summary": "Approved decision: keep api worker runtime continuity for planner handoffs.",
                            "evidence_paths": ["docs/requirements/api-runtime.md"],
                            "keywords": ["approved", "decision", "api", "worker", "continuity", "planner"],
                        },
                        {
                            "summary": "Approved decision: use watercolor poster palette for onboarding mural composition.",
                            "evidence_paths": ["docs/design/onboarding-poster.md"],
                            "keywords": ["approved", "decision", "watercolor", "poster", "palette", "mural"],
                        },
                    ]
                },
                repo_root=repo_root,
                session_root=session_root,
                store_path=temp_root / "legacy-serena.jsonl",
                project_key="codex-sim-relevance",
            )

            follow_up = run_driver(
                COMPAT_DRIVER,
                lane="serena",
                action="read",
                payload={"task": "Codex follow-up: api worker continuity review for planner handoffs", "top_k": 3},
                repo_root=repo_root,
                session_root=session_root,
                store_path=temp_root / "legacy-serena.jsonl",
                project_key="codex-sim-relevance",
            )

            self.assertEqual("backend_read", follow_up["status"])
            self.assertEqual(1, follow_up["item_count"])
            self.assertEqual(1, follow_up["capsule_count"])
            joined = " ".join(follow_up["items"]).lower()
            self.assertIn("api worker runtime continuity", joined)
            self.assertNotIn("watercolor poster palette", joined)

    def test_codex_unrelated_follow_up_returns_empty_memory_context(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            repo_root = temp_root / "workspace"
            session_root = temp_root / "session"
            repo_root.mkdir(parents=True, exist_ok=True)
            session_root.mkdir(parents=True, exist_ok=True)
            _seed_live_document_contract(repo_root)

            run_driver(
                COMPAT_DRIVER,
                lane="serena",
                action="write",
                payload={
                    "decisions": [
                        {
                            "summary": "Approved decision: keep api worker runtime continuity for planner handoffs.",
                            "evidence_paths": ["docs/requirements/api-runtime.md"],
                            "keywords": ["approved", "decision", "api", "worker", "continuity", "planner"],
                        }
                    ]
                },
                repo_root=repo_root,
                session_root=session_root,
                store_path=temp_root / "legacy-serena.jsonl",
                project_key="codex-sim-empty",
            )

            unrelated = run_driver(
                COMPAT_DRIVER,
                lane="serena",
                action="read",
                payload={"task": "Codex user asks for watercolor poster palette composition", "top_k": 3},
                repo_root=repo_root,
                session_root=session_root,
                store_path=temp_root / "legacy-serena.jsonl",
                project_key="codex-sim-empty",
            )

            self.assertEqual("backend_read_empty", unrelated["status"])
            self.assertEqual(0, unrelated["item_count"])
            self.assertEqual(0, unrelated["capsule_count"])
            self.assertEqual([], unrelated["items"])

    def test_cross_host_follow_up_shares_workspace_memory_identity_and_payload(self) -> None:
        from vgo_runtime.workspace_memory import build_workspace_memory_identity

        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            repo_root = temp_root / "workspace"
            codex_session_root = temp_root / "codex-session"
            claude_session_root = temp_root / "claude-session"
            repo_root.mkdir(parents=True, exist_ok=True)
            codex_session_root.mkdir(parents=True, exist_ok=True)
            claude_session_root.mkdir(parents=True, exist_ok=True)
            _seed_live_document_contract(repo_root)

            codex_identity = build_workspace_memory_identity(workspace_root=repo_root, host_id="codex").model_dump()
            claude_identity = build_workspace_memory_identity(workspace_root=repo_root, host_id="claude-code").model_dump()

            self.assertEqual(codex_identity["workspace_id"], claude_identity["workspace_id"])
            self.assertEqual(codex_identity["identity_root"], claude_identity["identity_root"])

            run_driver(
                COMPAT_DRIVER,
                lane="serena",
                action="write",
                payload={
                    "decisions": [
                        {
                            "summary": "Approved decision: codex and claude-code must share workspace continuity via one broker plane.",
                            "evidence_paths": ["docs/design/workspace-memory-plane.md"],
                            "keywords": ["approved", "decision", "codex", "claude-code", "workspace", "continuity"],
                        }
                    ]
                },
                repo_root=repo_root,
                session_root=codex_session_root,
                store_path=temp_root / "legacy-serena.jsonl",
                project_key="codex-cross-host",
            )

            follow_up = run_driver(
                COMPAT_DRIVER,
                lane="serena",
                action="read",
                payload={"task": "Claude Code follow-up asks about workspace continuity and broker sharing", "top_k": 3},
                repo_root=repo_root,
                session_root=claude_session_root,
                store_path=temp_root / "legacy-serena.jsonl",
                project_key="codex-cross-host",
            )

            self.assertEqual("backend_read", follow_up["status"])
            self.assertEqual(1, follow_up["item_count"])
            self.assertIn("workspace continuity", " ".join(follow_up["items"]).lower())

    def test_codex_workspace_isolation_blocks_same_project_key_from_other_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            workspace_a = temp_root / "workspace-a"
            workspace_b = temp_root / "workspace-b"
            session_a = temp_root / "session-a"
            session_b = temp_root / "session-b"
            workspace_a.mkdir(parents=True, exist_ok=True)
            workspace_b.mkdir(parents=True, exist_ok=True)
            session_a.mkdir(parents=True, exist_ok=True)
            session_b.mkdir(parents=True, exist_ok=True)
            _seed_live_document_contract(workspace_a)
            _seed_live_document_contract(workspace_b)

            run_driver(
                COMPAT_DRIVER,
                lane="serena",
                action="write",
                payload={
                    "decisions": [
                        {
                            "summary": "Approved decision: workspace A keeps api continuity memory private to its broker plane.",
                            "evidence_paths": ["docs/requirements/workspace-a.md"],
                            "keywords": ["approved", "decision", "workspace", "api", "continuity"],
                        }
                    ]
                },
                repo_root=workspace_a,
                session_root=session_a,
                store_path=temp_root / "legacy-serena-a.jsonl",
                project_key="shared-project-key",
            )

            workspace_b_follow_up = run_driver(
                COMPAT_DRIVER,
                lane="serena",
                action="read",
                payload={"task": "Codex follow-up: api continuity review", "top_k": 3},
                repo_root=workspace_b,
                session_root=session_b,
                store_path=temp_root / "legacy-serena-b.jsonl",
                project_key="shared-project-key",
            )

            self.assertEqual("backend_read_empty", workspace_b_follow_up["status"])
            self.assertEqual(0, workspace_b_follow_up["item_count"])
            self.assertEqual(0, workspace_b_follow_up["capsule_count"])


if __name__ == "__main__":
    unittest.main()
