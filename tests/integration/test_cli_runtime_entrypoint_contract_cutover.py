from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SUPPORTED_HOSTS = ("codex", "claude-code", "opencode")
POWERSHELL_CANONICAL_ENTRY = REPO_ROOT / "scripts" / "runtime" / "Invoke-VibeCanonicalEntry.ps1"
POWERSHELL_RUNTIME_ENTRY = REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"
FREEZE_RUNTIME_INPUT_PACKET = REPO_ROOT / "scripts" / "runtime" / "Freeze-RuntimeInputPacket.ps1"


def _resolve_python() -> str:
    python_bin = sys.executable or shutil.which("python") or shutil.which("python3")
    if not python_bin:
        raise RuntimeError("python interpreter not available")
    return python_bin


def _require_powershell() -> None:
    if not (shutil.which("pwsh") or shutil.which("powershell")):
        pytest.skip("PowerShell executable not available in PATH")


def _resolve_powershell() -> str:
    candidate = shutil.which("pwsh") or shutil.which("powershell")
    if not candidate:
        pytest.skip("PowerShell executable not available in PATH")
    return candidate


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _run_powershell_canonical_entry(
    *,
    temp_root: Path,
    workspace_root: Path | None = None,
    artifact_root: Path | None = None,
) -> dict[str, object]:
    run_id = f"pytest-powershell-canonical-{uuid.uuid4().hex[:8]}"
    bridge_output = temp_root / f"{run_id}.json"
    command = [
        _resolve_powershell(),
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(POWERSHELL_CANONICAL_ENTRY),
        "-Task",
        "Validate direct PowerShell canonical workspace isolation. $vibe",
        "-HostId",
        "codex",
        "-EntryId",
        "vibe",
        "-RequestedStageStop",
        "requirement_doc",
        "-RunId",
        run_id,
        "-BridgeOutputJsonPath",
        str(bridge_output),
    ]
    if workspace_root is not None:
        command.extend(["-WorkspaceRoot", str(workspace_root)])
    if artifact_root is not None:
        command.extend(["-ArtifactRoot", str(artifact_root)])

    env = os.environ.copy()
    env.update(
        {
            "VIBE_DISABLE_SERENA_BACKEND": "1",
            "VIBE_DISABLE_RUFLO_BACKEND": "1",
            "VIBE_DISABLE_COGNEE_BACKEND": "1",
            "VIBE_MEMORY_BACKEND_ROOT": str(temp_root / "memory-backends"),
        }
    )
    subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=True,
    )
    return json.loads(bridge_output.read_text(encoding="utf-8"))


def _run_freeze_runtime_input_packet(
    *,
    temp_root: Path,
    workspace_root: Path,
    artifact_root: str | None = None,
) -> dict[str, object]:
    run_id = f"pytest-freeze-runtime-{uuid.uuid4().hex[:8]}"
    arguments = [
        f"-Task {_ps_quote('Validate direct runtime packet storage.')}",
        "-Mode interactive_governed",
        f"-RunId {_ps_quote(run_id)}",
        f"-WorkspaceRoot {_ps_quote(str(workspace_root))}",
        "-RequestedStageStop requirement_doc",
    ]
    if artifact_root is not None:
        arguments.append(f"-ArtifactRoot {_ps_quote(artifact_root)}")
    command = [
        _resolve_powershell(),
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "$ErrorActionPreference = 'Stop'; "
            f"$result = & {_ps_quote(str(FREEZE_RUNTIME_INPUT_PACKET))} "
            + " ".join(arguments)
            + "; $result | ConvertTo-Json -Depth 20"
        ),
    ]
    env = os.environ.copy()
    env.update(
        {
            "VCO_HOST_ID": "codex",
            "VIBE_DISABLE_SERENA_BACKEND": "1",
            "VIBE_DISABLE_RUFLO_BACKEND": "1",
            "VIBE_DISABLE_COGNEE_BACKEND": "1",
            "VIBE_MEMORY_BACKEND_ROOT": str(temp_root / "memory-backends"),
        }
    )
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=True,
    )
    return json.loads(completed.stdout)


def _run_cli_canonical_entry(*, host_id: str, artifact_root: Path) -> dict[str, object]:
    python_bin = _resolve_python()
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [
            str(REPO_ROOT / "apps" / "vgo-cli" / "src"),
            str(REPO_ROOT / "packages" / "runtime-core" / "src"),
            str(REPO_ROOT / "packages" / "contracts" / "src"),
            str(REPO_ROOT / "packages" / "installer-core" / "src"),
        ]
    )
    env["VCO_HOST_ID"] = host_id
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    run_id = f"pytest-cli-canonical-{host_id}-{uuid.uuid4().hex[:8]}"
    command = [
        python_bin,
        "-m",
        "vgo_cli.main",
        "canonical-entry",
        "--repo-root",
        str(REPO_ROOT),
        "--prompt",
        "Validate canonical runtime proof contract for this supported host. $vibe",
        "--requested-stage-stop",
        "requirement_doc",
        "--run-id",
        run_id,
        "--artifact-root",
        str(artifact_root),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=True,
    )
    return json.loads(completed.stdout)


def test_cli_canonical_entry_uses_governed_artifact_root_as_workspace_identity() -> None:
    _require_powershell()
    source_descriptor = REPO_ROOT / ".vibeskills" / "project.json"
    source_descriptor_before = source_descriptor.read_bytes() if source_descriptor.exists() else None

    with tempfile.TemporaryDirectory() as tempdir:
        workspace_root = Path(tempdir) / "workspace"
        workspace_root.mkdir()
        payload = _run_cli_canonical_entry(
            host_id="codex",
            artifact_root=workspace_root,
        )

        runtime_packet = json.loads(
            Path(payload["artifacts"]["runtime_input_packet"]).read_text(encoding="utf-8")
        )
        workspace_sidecar = workspace_root / ".vibeskills"
        descriptor_path = workspace_sidecar / "project.json"
        for storage in (payload["summary"]["storage"], runtime_packet["storage"]):
            assert Path(storage["workspace_root"]).resolve() == workspace_root.resolve()
            assert Path(storage["workspace_sidecar_root"]).resolve() == workspace_sidecar.resolve()
            assert Path(storage["project_descriptor_path"]).resolve() == descriptor_path.resolve()
            assert Path(storage["artifact_root"]).resolve() == workspace_root.resolve()
        assert descriptor_path.exists()

    source_descriptor_after = source_descriptor.read_bytes() if source_descriptor.exists() else None
    assert source_descriptor_after == source_descriptor_before


def test_powershell_canonical_entry_uses_artifact_root_as_workspace_when_workspace_is_omitted() -> None:
    _require_powershell()
    source_descriptor = REPO_ROOT / ".vibeskills" / "project.json"
    source_descriptor_before = source_descriptor.read_bytes() if source_descriptor.exists() else None

    with tempfile.TemporaryDirectory() as tempdir:
        temp_root = Path(tempdir)
        artifact_root = temp_root / "task-workspace"
        try:
            payload = _run_powershell_canonical_entry(
                temp_root=temp_root,
                artifact_root=artifact_root,
            )
            source_descriptor_after = source_descriptor.read_bytes() if source_descriptor.exists() else None
        finally:
            if source_descriptor_before is None:
                source_descriptor.unlink(missing_ok=True)
            else:
                source_descriptor.write_bytes(source_descriptor_before)

        runtime_packet = json.loads(
            Path(payload["summary"]["artifacts"]["runtime_input_packet"]).read_text(
                encoding="utf-8"
            )
        )
        for storage in (payload["summary"]["storage"], runtime_packet["storage"]):
            assert Path(storage["workspace_root"]).resolve() == artifact_root.resolve()
            assert Path(storage["artifact_root"]).resolve() == artifact_root.resolve()
        assert (artifact_root / ".vibeskills" / "project.json").exists()
        assert source_descriptor_after == source_descriptor_before


def test_powershell_canonical_entry_defaults_artifacts_to_the_workspace_sidecar() -> None:
    _require_powershell()
    with tempfile.TemporaryDirectory() as tempdir:
        temp_root = Path(tempdir)
        workspace_root = temp_root / "workspace"
        payload = _run_powershell_canonical_entry(
            temp_root=temp_root,
            workspace_root=workspace_root,
        )

        expected_artifact_root = workspace_root / ".vibeskills"
        storage = payload["summary"]["storage"]
        assert Path(storage["workspace_root"]).resolve() == workspace_root.resolve()
        assert Path(storage["artifact_root"]).resolve() == expected_artifact_root.resolve()
        assert (workspace_root / ".vibeskills" / "project.json").exists()


def test_powershell_canonical_entry_preserves_separate_workspace_and_artifact_roots() -> None:
    _require_powershell()
    with tempfile.TemporaryDirectory() as tempdir:
        temp_root = Path(tempdir)
        workspace_root = temp_root / "workspace"
        artifact_root = temp_root / "artifacts"
        payload = _run_powershell_canonical_entry(
            temp_root=temp_root,
            workspace_root=workspace_root,
            artifact_root=artifact_root,
        )

        storage = payload["summary"]["storage"]
        assert Path(storage["workspace_root"]).resolve() == workspace_root.resolve()
        assert Path(storage["artifact_root"]).resolve() == artifact_root.resolve()
        assert (workspace_root / ".vibeskills" / "project.json").exists()


def test_direct_powershell_runtime_uses_artifact_root_as_workspace_when_workspace_is_omitted() -> None:
    _require_powershell()
    with tempfile.TemporaryDirectory() as tempdir:
        temp_root = Path(tempdir)
        artifact_root = temp_root / "task-workspace"
        run_id = f"pytest-direct-runtime-{uuid.uuid4().hex[:8]}"
        env = os.environ.copy()
        env.update(
            {
                "VIBE_DISABLE_SERENA_BACKEND": "1",
                "VIBE_DISABLE_RUFLO_BACKEND": "1",
                "VIBE_DISABLE_COGNEE_BACKEND": "1",
                "VIBE_MEMORY_BACKEND_ROOT": str(temp_root / "memory-backends"),
            }
        )
        subprocess.run(
            [
                _resolve_powershell(),
                "-NoLogo",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(POWERSHELL_RUNTIME_ENTRY),
                "-Task",
                "Validate artifact-only workspace isolation for a direct runtime call.",
                "-Mode",
                "interactive_governed",
                "-RunId",
                run_id,
                "-ArtifactRoot",
                str(artifact_root),
                "-RequestedStageStop",
                "requirement_doc",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            check=True,
        )

        summary_path = (
            artifact_root
            / "outputs"
            / "runtime"
            / "vibe-sessions"
            / run_id
            / "runtime-summary.json"
        )
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        assert Path(summary["storage"]["workspace_root"]).resolve() == artifact_root.resolve()
        assert Path(summary["storage"]["artifact_root"]).resolve() == artifact_root.resolve()
        assert (artifact_root / ".vibeskills" / "project.json").exists()


def test_direct_runtime_packet_freeze_defaults_artifacts_to_the_workspace_sidecar() -> None:
    _require_powershell()
    with tempfile.TemporaryDirectory() as tempdir:
        temp_root = Path(tempdir)
        workspace_root = temp_root / "workspace"
        payload = _run_freeze_runtime_input_packet(
            temp_root=temp_root,
            workspace_root=workspace_root,
        )
        run_id = str(payload["run_id"])
        expected_session = workspace_root / ".vibeskills" / "outputs" / "runtime" / "vibe-sessions" / run_id
        unexpected_session = REPO_ROOT / ".vibeskills" / "outputs" / "runtime" / "vibe-sessions" / run_id
        try:
            assert Path(payload["session_root"]).resolve() == expected_session.resolve()
            assert Path(payload["packet_path"]).resolve() == (expected_session / "runtime-input-packet.json").resolve()
            assert Path(payload["packet"]["storage"]["workspace_root"]).resolve() == workspace_root.resolve()
            assert Path(payload["packet"]["storage"]["artifact_root"]).resolve() == (
                workspace_root / ".vibeskills"
            ).resolve()
            assert not unexpected_session.exists()
        finally:
            shutil.rmtree(unexpected_session, ignore_errors=True)


def test_direct_runtime_packet_freeze_resolves_relative_artifacts_from_the_workspace() -> None:
    _require_powershell()
    with tempfile.TemporaryDirectory() as tempdir:
        temp_root = Path(tempdir)
        workspace_root = temp_root / "workspace"
        relative_artifact_root = f"packet-artifacts-{uuid.uuid4().hex[:8]}"
        payload = _run_freeze_runtime_input_packet(
            temp_root=temp_root,
            workspace_root=workspace_root,
            artifact_root=relative_artifact_root,
        )
        run_id = str(payload["run_id"])
        expected_artifact_root = workspace_root / relative_artifact_root
        expected_session = expected_artifact_root / "outputs" / "runtime" / "vibe-sessions" / run_id
        unexpected_root = REPO_ROOT / relative_artifact_root
        try:
            assert Path(payload["session_root"]).resolve() == expected_session.resolve()
            assert Path(payload["packet_path"]).resolve() == (expected_session / "runtime-input-packet.json").resolve()
            assert Path(payload["packet"]["storage"]["workspace_root"]).resolve() == workspace_root.resolve()
            assert Path(payload["packet"]["storage"]["artifact_root"]).resolve() == expected_artifact_root.resolve()
            assert not unexpected_root.exists()
        finally:
            shutil.rmtree(unexpected_root, ignore_errors=True)


def test_powershell_artifact_helper_resolves_relative_roots_from_runtime_workspace() -> None:
    _require_powershell()
    common = REPO_ROOT / "scripts" / "runtime" / "VibeRuntime.Common.ps1"
    with tempfile.TemporaryDirectory() as tempdir:
        workspace_root = Path(tempdir) / "workspace"
        expected_artifact_root = workspace_root / "relative-artifacts"
        command = [
            _resolve_powershell(),
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            (
                "$ErrorActionPreference = 'Stop'; "
                f". {_ps_quote(str(common))}; "
                "$runtime = [pscustomobject]@{"
                f"repo_root = {_ps_quote(str(REPO_ROOT))}; "
                f"workspace_root = {_ps_quote(str(workspace_root))}"
                "}; "
                "$result = Get-VibeArtifactRoot "
                f"-RepoRoot {_ps_quote(str(REPO_ROOT))} "
                "-Runtime $runtime -ArtifactRoot 'relative-artifacts'; "
                "[Console]::Out.Write($result)"
            ),
        ]
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )

        assert Path(completed.stdout.strip()).resolve() == expected_artifact_root.resolve()


def test_direct_powershell_runtime_writes_relative_artifacts_under_the_workspace() -> None:
    _require_powershell()
    with tempfile.TemporaryDirectory() as tempdir:
        temp_root = Path(tempdir)
        workspace_root = temp_root / "workspace"
        relative_artifact_root = f"runtime-artifacts-{uuid.uuid4().hex[:8]}"
        run_id = f"pytest-direct-runtime-{uuid.uuid4().hex[:8]}"
        env = os.environ.copy()
        env.update(
            {
                "VIBE_DISABLE_SERENA_BACKEND": "1",
                "VIBE_DISABLE_RUFLO_BACKEND": "1",
                "VIBE_DISABLE_COGNEE_BACKEND": "1",
                "VIBE_MEMORY_BACKEND_ROOT": str(temp_root / "memory-backends"),
            }
        )
        command = [
            _resolve_powershell(),
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(POWERSHELL_RUNTIME_ENTRY),
            "-Task",
            "Validate relative artifact placement for a direct runtime call.",
            "-Mode",
            "interactive_governed",
            "-RunId",
            run_id,
            "-WorkspaceRoot",
            str(workspace_root),
            "-ArtifactRoot",
            relative_artifact_root,
            "-RequestedStageStop",
            "requirement_doc",
        ]
        subprocess.run(
            command,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            check=True,
        )

        expected_summary = (
            workspace_root
            / relative_artifact_root
            / "outputs"
            / "runtime"
            / "vibe-sessions"
            / run_id
            / "runtime-summary.json"
        )
        unexpected_summary = (
            REPO_ROOT
            / relative_artifact_root
            / "outputs"
            / "runtime"
            / "vibe-sessions"
            / run_id
            / "runtime-summary.json"
        )
        assert expected_summary.exists()
        assert not unexpected_summary.exists()
        summary = json.loads(expected_summary.read_text(encoding="utf-8"))
        assert Path(summary["storage"]["workspace_root"]).resolve() == workspace_root.resolve()
        assert Path(summary["storage"]["artifact_root"]).resolve() == (
            workspace_root / relative_artifact_root
        ).resolve()


def test_cli_canonical_entry_proves_runtime_backed_truth_for_supported_hosts() -> None:
    _require_powershell()
    for host_id in SUPPORTED_HOSTS:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = _run_cli_canonical_entry(
                host_id=host_id,
                artifact_root=Path(tempdir) / "canonical-entry-cutover",
            )

            receipt_path = Path(payload["host_launch_receipt_path"])
            assert receipt_path.exists(), host_id
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            assert receipt["host_id"] == host_id, host_id
            assert receipt["entry_id"] == "vibe", host_id
            assert receipt["launch_status"] == "verified", host_id

            artifacts = payload.get("artifacts") or {}
            runtime_packet_path = Path(artifacts["runtime_input_packet"])
            governance_capsule_path = Path(artifacts["governance_capsule"])
            stage_lineage_path = Path(artifacts["stage_lineage"])
            assert runtime_packet_path.exists(), host_id
            assert governance_capsule_path.exists(), host_id
            assert stage_lineage_path.exists(), host_id

            runtime_packet = json.loads(runtime_packet_path.read_text(encoding="utf-8"))
            governance_capsule = json.loads(governance_capsule_path.read_text(encoding="utf-8"))
            assert governance_capsule["runtime_selected_skill"] == "vibe", host_id
            assert "module_assignments" in runtime_packet, host_id
            assert "specialist_decision" not in runtime_packet, host_id
            assert "specialist_dispatch" not in runtime_packet, host_id
            assert "specialist_recommendations" not in runtime_packet, host_id
            organization = runtime_packet.get("agent_skill_organization") or {}
            selected_rows = organization.get("selected_skills") or []
            selected_skill_ids = sorted(
                row.get("skill_id")
                for row in selected_rows
                if isinstance(row, dict) and row.get("skill_id")
            )
            bound_units = (runtime_packet.get("module_assignments") or {}).get("units") or []
            bound_skill_ids = sorted(
                unit.get("bound_skill")
                for unit in bound_units
                if isinstance(unit, dict) and unit.get("bound_skill")
            )
            assert bound_skill_ids == selected_skill_ids, host_id
            assert "selected" not in (runtime_packet.get("skill_routing") or {}), host_id
