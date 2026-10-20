from __future__ import annotations

import json
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_SRC = REPO_ROOT / "packages" / "contracts" / "src"
RUNTIME_SRC = REPO_ROOT / "packages" / "runtime-core" / "src"
RUNTIME_INVOCATION_TIMEOUT_SECONDS = 120
for source_root in (CONTRACTS_SRC, RUNTIME_SRC):
    if str(source_root) not in sys.path:
        sys.path.insert(0, str(source_root))

from vgo_runtime.artifact_contract import (  # noqa: E402
    resolve_runtime_artifact_projection,
    resolve_runtime_session_root,
    sync_session_receipts_to_run_artifact_sink,
    write_runtime_artifact_bundle,
)
from vgo_contracts.live_governance_contract import (  # noqa: E402
    LiveGovernanceContract,
)


def _powershell() -> str:
    executable = shutil.which("pwsh") or shutil.which("powershell")
    if executable is None:
        pytest.skip("PowerShell executable not available")
    return executable


def _ps_quote(value: str | Path) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _run_powershell_json(script: str) -> dict[str, object]:
    completed = subprocess.run(
        [
            _powershell(),
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
        timeout=RUNTIME_INVOCATION_TIMEOUT_SECONDS,
    )
    payload = json.loads(completed.stdout)
    assert isinstance(payload, dict)
    return payload


def _dot_source_common() -> str:
    common = REPO_ROOT / "scripts" / "runtime" / "VibeRuntime.Common.ps1"
    return f"$ErrorActionPreference = 'Stop'; . {_ps_quote(common)}; "


def _write_contract_repository(
    root: Path,
    *,
    legacy_write_mode: str,
) -> Path:
    payload = json.loads(
        (REPO_ROOT / "config" / "live-document-contract.json").read_text(
            encoding="utf-8"
        )
    )
    payload["artifact_sink"]["legacy_write_mode"] = legacy_write_mode
    contract_path = root / "config" / "live-document-contract.json"
    contract_path.parent.mkdir(parents=True)
    contract_path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    return root


def test_python_and_powershell_resolve_the_same_run_artifact_paths(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    run_id = "artifact-path-parity"
    python_projection = resolve_runtime_artifact_projection(
        agent_root=workspace,
        workspace_root=workspace,
        run_id=run_id,
        repo_root=REPO_ROOT,
    )
    powershell_projection = _run_powershell_json(
        _dot_source_common()
        + "$result = Get-VibeArtifactContractDescriptor "
        + f"-RepoRoot {_ps_quote(REPO_ROOT)} -RunId {_ps_quote(run_id)} "
        + f"-ArtifactRoot {_ps_quote(workspace)}; "
        + "$result | ConvertTo-Json -Depth 20"
    )

    expected_root = workspace / ".vibeskills" / "runs" / run_id
    assert python_projection.run_root == expected_root.resolve()
    assert python_projection.session_root == (
        workspace / "outputs" / "runtime" / "vibe-sessions" / run_id
    ).resolve()
    assert Path(str(powershell_projection["artifact_root"])) == expected_root.resolve()
    assert Path(str(powershell_projection["session_root"])) == (
        workspace / "outputs" / "runtime" / "vibe-sessions" / run_id
    ).resolve()
    for kind in (
        "requirement",
        "plan",
        "status",
        "proof",
        "manifest",
        "legacy_compatibility",
    ):
        assert Path(str(powershell_projection["paths"][kind])) == python_projection.artifact_paths[kind]
    for kind in ("requirement", "plan"):
        assert Path(
            str(powershell_projection["paths"][f"primary_{kind}"])
        ) == python_projection.primary_document_paths[kind]


def test_python_and_powershell_normalize_run_ids_once(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    raw_run_id = "  normalized-run-id  "
    python_projection = resolve_runtime_artifact_projection(
        agent_root=workspace,
        workspace_root=workspace,
        run_id=raw_run_id,
        repo_root=REPO_ROOT,
    )
    powershell_projection = _run_powershell_json(
        _dot_source_common()
        + "$result = Get-VibeArtifactContractDescriptor "
        + f"-RepoRoot {_ps_quote(REPO_ROOT)} -RunId {_ps_quote(raw_run_id)} "
        + f"-ArtifactRoot {_ps_quote(workspace)}; "
        + "$result | ConvertTo-Json -Depth 20"
    )

    expected_root = (workspace / ".vibeskills" / "runs" / "normalized-run-id").resolve()
    assert python_projection.run_id == "normalized-run-id"
    assert python_projection.run_root == expected_root
    assert python_projection.legacy_run_root == (
        workspace / "vibe" / "runs" / "normalized-run-id"
    ).resolve()
    assert powershell_projection["run_id"] == "normalized-run-id"
    assert Path(str(powershell_projection["artifact_root"])) == expected_root
    assert powershell_projection["artifact_root_relative"] == (
        ".vibeskills/runs/normalized-run-id"
    )


def test_python_and_powershell_keep_session_root_on_the_artifact_base(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    artifact_base = workspace / ".vibeskills"
    workspace.mkdir()
    run_id = "session-artifact-base"
    python_projection = resolve_runtime_artifact_projection(
        agent_root=workspace,
        workspace_root=workspace,
        session_artifact_root=artifact_base,
        run_id=run_id,
        repo_root=REPO_ROOT,
    )
    powershell_projection = _run_powershell_json(
        _dot_source_common()
        + "$result = Get-VibeArtifactContractDescriptor "
        + f"-RepoRoot {_ps_quote(REPO_ROOT)} -RunId {_ps_quote(run_id)} "
        + f"-WorkspaceRoot {_ps_quote(workspace)} -ArtifactRoot {_ps_quote(artifact_base)}; "
        + "$result | ConvertTo-Json -Depth 20"
    )

    expected_session_root = (
        artifact_base / "outputs" / "runtime" / "vibe-sessions" / run_id
    ).resolve()
    assert python_projection.session_root == expected_session_root
    assert Path(str(powershell_projection["session_root"])) == expected_session_root


def test_python_and_powershell_follow_custom_contract_paths(tmp_path: Path) -> None:
    contract_repo = tmp_path / "contract-repo"
    workspace = tmp_path / "workspace"
    (contract_repo / "config").mkdir(parents=True)
    workspace.mkdir()
    payload = json.loads(
        (REPO_ROOT / "config" / "live-document-contract.json").read_text(
            encoding="utf-8"
        )
    )
    payload["artifact_sink"]["artifact_paths"] = {
        "requirement": "records/requirement.json",
        "plan": "records/plan.json",
        "status": "records/status.json",
        "proof": "records/proof.json",
    }
    payload["artifact_sink"]["primary_document_paths"] = {
        "requirement": "documents/requirement.md",
        "plan": "documents/plan.md",
    }
    payload["artifact_sink"]["manifest_path"] = "metadata/manifest.json"
    payload["artifact_sink"]["legacy_compatibility_path"] = (
        "metadata/legacy-compatibility.json"
    )
    payload["artifact_sink"]["legacy_projection_root"] = "compatibility/runs"
    (contract_repo / "config" / "live-document-contract.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    run_id = "custom-contract-paths"

    python_projection = resolve_runtime_artifact_projection(
        agent_root=workspace,
        workspace_root=workspace,
        run_id=run_id,
        repo_root=contract_repo,
    )
    powershell_projection = _run_powershell_json(
        _dot_source_common()
        + "$result = Get-VibeArtifactContractDescriptor "
        + f"-RepoRoot {_ps_quote(contract_repo)} -RunId {_ps_quote(run_id)} "
        + f"-ArtifactRoot {_ps_quote(workspace)}; "
        + "$result | ConvertTo-Json -Depth 20"
    )

    for kind in (
        "requirement",
        "plan",
        "status",
        "proof",
        "manifest",
        "legacy_compatibility",
    ):
        assert Path(str(powershell_projection["paths"][kind])) == (
            python_projection.artifact_paths[kind]
        )
    for kind in ("requirement", "plan"):
        assert Path(
            str(powershell_projection["paths"][f"primary_{kind}"])
        ) == python_projection.primary_document_paths[kind]
    assert python_projection.legacy_run_root == (
        workspace / "compatibility" / "runs" / run_id
    ).resolve()
    assert powershell_projection["legacy_projection_root"] == "compatibility/runs"


def test_session_receipt_contract_controls_the_runtime_path_and_boundary(
    tmp_path: Path,
) -> None:
    contract_repo = tmp_path / "contract-repo"
    workspace = tmp_path / "workspace"
    (contract_repo / "config").mkdir(parents=True)
    workspace.mkdir()
    payload = json.loads(
        (REPO_ROOT / "config" / "live-document-contract.json").read_text(
            encoding="utf-8"
        )
    )
    payload["artifact_sink"]["session_receipts"]["root"] = (
        "runtime/session-receipts"
    )
    (contract_repo / "config" / "live-document-contract.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    contract = LiveGovernanceContract.model_validate(payload)
    python_path = resolve_runtime_session_root(
        repo_root=contract_repo,
        artifact_root=workspace,
        run_id="session-boundary",
    )

    powershell_result = _run_powershell_json(
        _dot_source_common()
        + "$contract = Get-VibeLiveGovernanceContract "
        + f"-RepoRoot {_ps_quote(contract_repo)}; "
        + "$path = Get-VibeSessionRoot "
        + f"-RepoRoot {_ps_quote(contract_repo)} -RunId 'session-boundary' "
        + f"-ArtifactRoot {_ps_quote(workspace)}; "
        + "[pscustomobject]@{ path = $path; boundary = $contract.artifact_sink.session_receipts } "
        + "| ConvertTo-Json -Depth 10"
    )

    expected_path = (
        workspace / "runtime" / "session-receipts" / "session-boundary"
    ).resolve()
    assert python_path == expected_path
    assert Path(str(powershell_result["path"])) == expected_path
    assert powershell_result["boundary"] == contract.artifact_sink.session_receipts.model_dump()
    assert powershell_result["boundary"] == {
        "root": "runtime/session-receipts",
        "owner": "runtime",
        "retention": "workspace_local",
        "copy_to_artifact_sink": True,
    }


def test_repository_contract_overrides_a_conflicting_workspace_copy(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    config_root = workspace / "config"
    config_root.mkdir(parents=True)
    payload = json.loads(
        (REPO_ROOT / "config" / "live-document-contract.json").read_text(
            encoding="utf-8"
        )
    )
    payload["artifact_sink"]["root"] = ".workspace-contract/runs"
    (config_root / "live-document-contract.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    projection = resolve_runtime_artifact_projection(
        agent_root=workspace,
        workspace_root=workspace,
        run_id="repo-contract-authority",
        repo_root=REPO_ROOT,
    )
    powershell_projection = _run_powershell_json(
        _dot_source_common()
        + "$result = Get-VibeArtifactContractDescriptor "
        + f"-RepoRoot {_ps_quote(REPO_ROOT)} -RunId 'repo-contract-authority' "
        + f"-WorkspaceRoot {_ps_quote(workspace)}; "
        + "$result | ConvertTo-Json -Depth 20"
    )

    expected_root = (
        workspace / ".vibeskills" / "runs" / "repo-contract-authority"
    ).resolve()
    assert projection.run_root == expected_root
    assert Path(str(powershell_projection["artifact_root"])) == expected_root


def test_python_and_powershell_emit_manifest_and_artifact_envelope_parity(tmp_path: Path) -> None:
    run_id = "artifact-payload-parity"
    python_workspace = tmp_path / "python"
    powershell_workspace = tmp_path / "powershell"
    python_workspace.mkdir()
    powershell_workspace.mkdir()
    payloads = {
        "requirement": {"task": "verify artifact parity"},
        "plan": {"status": "ready"},
        "status": {"status": "ready_for_execution"},
        "proof": {"status": "pending"},
    }
    projection = resolve_runtime_artifact_projection(
        agent_root=python_workspace,
        workspace_root=python_workspace,
        run_id=run_id,
        repo_root=REPO_ROOT,
    )
    python_manifest = write_runtime_artifact_bundle(
        projection,
        repo_root=REPO_ROOT,
        host_id="codex",
        **payloads,
    ).model_dump()
    powershell_result = _run_powershell_json(
        _dot_source_common()
        + "Remove-Item Env:OS -ErrorAction SilentlyContinue; "
        + "$result = Write-VibeRunArtifactBundle "
        + f"-RepoRoot {_ps_quote(REPO_ROOT)} -RunId {_ps_quote(run_id)} "
        + f"-ArtifactRoot {_ps_quote(powershell_workspace)} -HostId 'codex' "
        + "-Requirement ([pscustomobject]@{ task = 'verify artifact parity' }) "
        + "-Plan ([pscustomobject]@{ status = 'ready' }) "
        + "-Status ([pscustomobject]@{ status = 'ready_for_execution' }) "
        + "-Proof ([pscustomobject]@{ status = 'pending' }); "
        + "$result | ConvertTo-Json -Depth 20"
    )
    powershell_manifest = powershell_result["manifest"]

    for field in ("schema_version", "run_id", "artifact_root", "artifacts", "commit_sha"):
        assert powershell_manifest[field] == python_manifest[field]
    assert powershell_manifest["execution_environment"]["os"] == python_manifest[
        "execution_environment"
    ]["os"]
    assert powershell_manifest["execution_environment"]["host_id"] == "codex"
    assert python_manifest["execution_environment"]["host_id"] == "codex"
    assert powershell_manifest["execution_environment"]["runtime"] == "powershell"
    assert python_manifest["execution_environment"]["runtime"] == "python"
    assert powershell_manifest["execution_environment"]["runtime_version"]
    assert python_manifest["execution_environment"]["runtime_version"]
    assert powershell_manifest["legacy_compatibility"] == python_manifest["legacy_compatibility"]
    assert powershell_manifest["artifacts"] == projection.artifact_sink.artifact_path_map

    for kind in ("requirement", "plan"):
        primary_document = projection.primary_document_paths[kind]
        assert primary_document.is_file()
        primary_text = primary_document.read_text(encoding="utf-8")
        assert primary_text.startswith(f"# Run {kind.title()}\n")
        assert json.dumps(payloads[kind], ensure_ascii=False, indent=2) in primary_text

    for kind in ("requirement", "plan", "status", "proof"):
        python_payload = json.loads(projection.artifact_paths[kind].read_text(encoding="utf-8"))
        powershell_path = Path(str(powershell_result["descriptor"]["paths"][kind]))
        powershell_payload = json.loads(powershell_path.read_text(encoding="utf-8"))
        assert powershell_payload == python_payload

    python_compatibility = json.loads(
        (projection.run_root / "legacy-compatibility.json").read_text(
            encoding="utf-8"
        )
    )
    powershell_compatibility = json.loads(
        Path(
            str(powershell_result["descriptor"]["paths"]["legacy_compatibility"])
        ).read_text(encoding="utf-8")
    )
    assert powershell_compatibility == python_compatibility


def test_python_and_powershell_normalize_compatibility_write_records(
    tmp_path: Path,
) -> None:
    run_id = "compatibility-write-normalization"
    raw_legacy_write = r"  docs\requirements\legacy.md  "
    expected_legacy_write = "docs/requirements/legacy.md"
    python_workspace = tmp_path / "python"
    powershell_workspace = tmp_path / "powershell"
    contract_repo = _write_contract_repository(
        tmp_path / "contract-repo",
        legacy_write_mode="dual_write",
    )
    python_workspace.mkdir()
    powershell_workspace.mkdir()

    projection = resolve_runtime_artifact_projection(
        agent_root=python_workspace,
        workspace_root=python_workspace,
        run_id=run_id,
        repo_root=contract_repo,
    )
    python_manifest = write_runtime_artifact_bundle(
        projection,
        requirement={"status": "pending"},
        plan={"status": "pending"},
        status={"status": "pending"},
        proof={"status": "pending"},
        repo_root=contract_repo,
        legacy_writes=[raw_legacy_write],
    ).model_dump()
    python_compatibility = json.loads(
        (projection.run_root / "legacy-compatibility.json").read_text(
            encoding="utf-8"
        )
    )

    powershell_result = _run_powershell_json(
        _dot_source_common()
        + "$result = Write-VibeRunArtifactBundle "
        + f"-RepoRoot {_ps_quote(contract_repo)} -RunId {_ps_quote(run_id)} "
        + f"-ArtifactRoot {_ps_quote(powershell_workspace)} "
        + f"-LegacyWrites @({_ps_quote(raw_legacy_write)}); "
        + "$result | ConvertTo-Json -Depth 20"
    )
    powershell_manifest = powershell_result["manifest"]
    powershell_compatibility = json.loads(
        Path(
            str(powershell_result["descriptor"]["paths"]["legacy_compatibility"])
        ).read_text(encoding="utf-8")
    )

    expected_compatibility = {
        "mode": "dual_write",
        "removal_release": "4.1.0",
        "documentation_roots": ["docs/requirements", "docs/plans"],
        "writes": [expected_legacy_write],
        "write_records": [
            {
                "destination": expected_legacy_write,
                "mode": "dual_write",
                "removal_release": "4.1.0",
            }
        ],
        "observable": True,
    }
    assert python_manifest["legacy_compatibility"] == expected_compatibility
    assert powershell_manifest["legacy_compatibility"] == expected_compatibility
    assert python_compatibility == {
        "run_id": run_id,
        "artifact_root": ".vibeskills/runs/" + run_id,
        **expected_compatibility,
    }
    assert powershell_compatibility == python_compatibility


@pytest.mark.parametrize(
    "legacy_relative",
    [
        "docs/requirements",
        "docs/requirements/nested",
        "docs/plans/archive",
    ],
)
def test_historical_documentation_roots_are_rejected_as_artifact_workspaces(
    tmp_path: Path,
    legacy_relative: str,
) -> None:
    legacy_root = tmp_path / legacy_relative
    legacy_root.mkdir(parents=True)

    with pytest.raises(ValueError, match="historical documentation roots"):
        resolve_runtime_artifact_projection(
            agent_root=tmp_path,
            workspace_root=legacy_root,
            run_id="reject-legacy-root",
            repo_root=REPO_ROOT,
        )

    completed = subprocess.run(
        [
            _powershell(),
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            _dot_source_common()
            + "Get-VibeRunArtifactRoot "
            + f"-RepoRoot {_ps_quote(REPO_ROOT)} -RunId 'reject-legacy-root' "
            + f"-ArtifactRoot {_ps_quote(legacy_root)}",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=RUNTIME_INVOCATION_TIMEOUT_SECONDS,
    )
    assert completed.returncode != 0
    assert "historical documentation roots" in completed.stderr


def test_python_disabled_compatibility_rejects_writes_before_creating_artifacts(
    tmp_path: Path,
) -> None:
    contract_repo = tmp_path / "contract-repo"
    workspace = tmp_path / "workspace"
    (contract_repo / "config").mkdir(parents=True)
    workspace.mkdir()
    payload = json.loads(
        (REPO_ROOT / "config" / "live-document-contract.json").read_text(
            encoding="utf-8"
        )
    )
    payload["artifact_sink"]["legacy_write_mode"] = "disabled"
    (contract_repo / "config" / "live-document-contract.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    projection = resolve_runtime_artifact_projection(
        agent_root=workspace,
        workspace_root=workspace,
        run_id="disabled-before-write",
        repo_root=contract_repo,
    )

    with pytest.raises(ValueError, match="disabled legacy compatibility"):
        write_runtime_artifact_bundle(
            projection,
            requirement={"status": "pending"},
            plan={"status": "pending"},
            status={"status": "pending"},
            proof={"status": "pending"},
            repo_root=contract_repo,
            legacy_writes=["docs/requirements/should-not-write.md"],
        )

    assert not projection.run_root.exists()


def test_powershell_disabled_compatibility_rejects_writes_before_creating_artifacts(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    payload = json.loads(
        (REPO_ROOT / "config" / "live-document-contract.json").read_text(
            encoding="utf-8"
        )
    )
    payload["artifact_sink"]["legacy_write_mode"] = "disabled"
    contract_root = tmp_path / "contract-repo"
    (contract_root / "config").mkdir(parents=True)
    (contract_root / "config" / "live-document-contract.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    result = _run_powershell_json(
        _dot_source_common()
        + "$errorMessage = ''; "
        + "try { Write-VibeRunArtifactBundle "
        + f"-RepoRoot {_ps_quote(contract_root)} -RunId 'disabled-before-write' "
        + f"-ArtifactRoot {_ps_quote(workspace)} "
        + "-LegacyWrites @('docs/requirements/legacy.md') | Out-Null } "
        + "catch { $errorMessage = $_.Exception.Message }; "
        + "$runRoot = Join-Path "
        + f"({_ps_quote(workspace)}) '.vibeskills/runs/disabled-before-write'; "
        + "[pscustomobject]@{ error = $errorMessage; run_root_exists = "
        + "(Test-Path -LiteralPath $runRoot) } | ConvertTo-Json"
    )

    assert "disabled legacy compatibility" in result["error"]
    assert result["run_root_exists"] is False


def test_python_disabled_compatibility_disables_the_legacy_projection(
    tmp_path: Path,
) -> None:
    contract_repo = tmp_path / "contract-repo"
    workspace = tmp_path / "workspace"
    (contract_repo / "config").mkdir(parents=True)
    workspace.mkdir()
    payload = json.loads(
        (REPO_ROOT / "config" / "live-document-contract.json").read_text(
            encoding="utf-8"
        )
    )
    payload["artifact_sink"]["legacy_write_mode"] = "disabled"
    (contract_repo / "config" / "live-document-contract.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    projection = resolve_runtime_artifact_projection(
        agent_root=workspace,
        workspace_root=None,
        run_id="disabled-projection",
        repo_root=contract_repo,
    )

    assert projection.legacy_projection_enabled is False


def test_python_legacy_projection_is_always_reported_as_a_compatibility_write(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    contract_repo = _write_contract_repository(
        tmp_path / "contract-repo",
        legacy_write_mode="dual_write",
    )
    workspace.mkdir()
    projection = resolve_runtime_artifact_projection(
        agent_root=workspace,
        workspace_root=None,
        run_id="observable-legacy-projection",
        repo_root=contract_repo,
    )

    manifest = write_runtime_artifact_bundle(
        projection,
        requirement={"status": "pending"},
        plan={"status": "pending"},
        status={"status": "pending"},
        proof={"status": "pending"},
        repo_root=contract_repo,
    ).model_dump()

    destination = "vibe/runs/observable-legacy-projection"
    assert projection.legacy_run_root.is_dir()
    assert manifest["legacy_compatibility"]["writes"] == [destination]
    assert manifest["legacy_compatibility"]["write_records"] == [
        {
            "destination": destination,
            "mode": "dual_write",
            "removal_release": "4.1.0",
        }
    ]


def test_python_and_powershell_reject_undeclared_compatibility_destinations_before_write(
    tmp_path: Path,
) -> None:
    python_workspace = tmp_path / "python"
    powershell_workspace = tmp_path / "powershell"
    python_workspace.mkdir()
    powershell_workspace.mkdir()
    projection = resolve_runtime_artifact_projection(
        agent_root=python_workspace,
        workspace_root=python_workspace,
        run_id="invalid-compatibility-write",
        repo_root=REPO_ROOT,
    )

    with pytest.raises(ValueError, match="declared legacy compatibility roots"):
        write_runtime_artifact_bundle(
            projection,
            requirement={"status": "pending"},
            plan={"status": "pending"},
            status={"status": "pending"},
            proof={"status": "pending"},
            repo_root=REPO_ROOT,
            legacy_writes=["outputs/random.md"],
        )

    powershell_result = _run_powershell_json(
        _dot_source_common()
        + "$runRoot = Get-VibeRunArtifactRoot "
        + f"-RepoRoot {_ps_quote(REPO_ROOT)} -RunId 'invalid-compatibility-write' "
        + f"-ArtifactRoot {_ps_quote(powershell_workspace)}; "
        + "$errorMessage = ''; "
        + "try { Write-VibeRunArtifactBundle "
        + f"-RepoRoot {_ps_quote(REPO_ROOT)} -RunId 'invalid-compatibility-write' "
        + f"-ArtifactRoot {_ps_quote(powershell_workspace)} "
        + "-LegacyWrites @('outputs/random.md') | Out-Null } "
        + "catch { $errorMessage = $_.Exception.Message }; "
        + "[pscustomobject]@{ error = $errorMessage; run_root_exists = "
        + "(Test-Path -LiteralPath $runRoot) } | ConvertTo-Json"
    )

    assert not projection.run_root.exists()
    assert "declared legacy compatibility roots" in powershell_result["error"]
    assert powershell_result["run_root_exists"] is False


def test_powershell_primary_documents_use_only_the_run_sink(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    run_id = "artifact-document-cutover"
    host_decision = {
        "agent_skill_organization": {
            "schema_version": "agent_skill_organization_v1",
            "derived_by": "agent",
            "workflow_level": "L",
            "modules": [
                {
                    "module_id": "direct_module",
                    "goal": "Produce the approved run artifacts.",
                    "candidate_skill_ids": [],
                    "required": True,
                    "depends_on": [],
                    "execution_mode": "agent_direct",
                    "write_scope": "outputs/direct/**",
                    "expected_outputs": ["outputs/direct/result.md"],
                    "verification": ["Check the frozen artifact contract."],
                    "acceptance_criteria": [
                        {
                            "criterion_id": "artifact-contract",
                            "description": "The run artifact contract is complete.",
                            "verification_mode": "automated",
                        }
                    ],
                }
            ],
            "selected_skills": [],
            "uncovered_modules": [],
            "workflow_level_contract": {
                "L": "Run the approved module serially.",
                "XL": "Use bounded waves for independent modules.",
            },
        }
    }
    env = os.environ.copy()
    env.update(
        {
            "VCO_HOST_ID": "codex",
            "VIBE_DISABLE_SERENA_BACKEND": "1",
            "VIBE_DISABLE_RUFLO_BACKEND": "1",
            "VIBE_DISABLE_COGNEE_BACKEND": "1",
            "VIBE_MEMORY_BACKEND_ROOT": str(tmp_path / "memory-backends"),
        }
    )
    subprocess.run(
        [
            _powershell(),
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"),
            "-Task",
            "Verify the shared run artifact document cutover.",
            "-Mode",
            "interactive_governed",
            "-RunId",
            run_id,
            "-WorkspaceRoot",
            str(workspace),
            "-RequestedStageStop",
            "xl_plan",
            "-HostDecisionJson",
            json.dumps(host_decision, separators=(",", ":")),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=True,
        timeout=RUNTIME_INVOCATION_TIMEOUT_SECONDS,
    )

    run_root = workspace / ".vibeskills" / "runs" / run_id
    session_root = (
        workspace
        / ".vibeskills"
        / "outputs"
        / "runtime"
        / "vibe-sessions"
        / run_id
    )
    summary = json.loads(
        (session_root / "runtime-summary.json").read_text(encoding="utf-8")
    )
    requirement_receipt = json.loads(
        (session_root / "requirement-doc-receipt.json").read_text(encoding="utf-8")
    )
    plan_receipt = json.loads(
        (session_root / "execution-plan-receipt.json").read_text(encoding="utf-8")
    )
    primary_requirement = run_root / "requirement.md"
    primary_plan = run_root / "plan.md"
    assert Path(summary["artifacts"]["requirement_doc"]) == primary_requirement
    assert Path(summary["artifacts"]["execution_plan"]) == primary_plan
    assert summary["artifacts"]["legacy_requirement_doc"] == ""
    assert summary["artifacts"]["legacy_execution_plan"] == ""
    assert Path(requirement_receipt["requirement_doc_path"]) == primary_requirement
    assert requirement_receipt["legacy_requirement_doc_path"] is None
    assert Path(plan_receipt["requirement_doc_path"]) == primary_requirement
    assert Path(plan_receipt["execution_plan_path"]) == primary_plan
    assert plan_receipt["legacy_execution_plan_path"] is None
    assert not (workspace / "docs" / "requirements").exists()
    assert not (workspace / "docs" / "plans").exists()

    manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["legacy_compatibility"] == {
        "mode": "disabled",
        "removal_release": "4.1.0",
        "documentation_roots": ["docs/requirements", "docs/plans"],
        "writes": [],
        "write_records": [],
        "observable": True,
    }
    requirement_artifact = json.loads(
        (run_root / "requirement.json").read_text(encoding="utf-8")
    )
    plan_artifact = json.loads((run_root / "plan.json").read_text(encoding="utf-8"))
    assert requirement_artifact["requirement_doc_path"] == str(primary_requirement)
    assert plan_artifact["execution_plan_path"] == str(primary_plan)

    assert primary_requirement.is_file()
    assert primary_plan.is_file()
    module_work_plan = json.loads(
        (run_root / "module-work-plan.json").read_text(encoding="utf-8")
    )
    assert module_work_plan["requirement_digest"] == hashlib.sha256(
        primary_requirement.read_bytes()
    ).hexdigest()


def test_invalid_run_id_is_rejected_before_the_session_directory_is_created(
    tmp_path: Path,
) -> None:
    artifact_root = tmp_path / "artifacts"
    result = _run_powershell_json(
        _dot_source_common()
        + f"$artifactRoot = {_ps_quote(artifact_root)}; "
        + "$runId = '../escape'; "
        + "$unsafePath = [System.IO.Path]::GetFullPath((Join-Path $artifactRoot "
        + "('outputs\\runtime\\vibe-sessions\\{0}' -f $runId))); "
        + "$errorMessage = ''; "
        + "try { Ensure-VibeSessionRoot "
        + f"-RepoRoot {_ps_quote(REPO_ROOT)} -RunId $runId "
        + "-ArtifactRoot $artifactRoot | Out-Null } "
        + "catch { $errorMessage = $_.Exception.Message }; "
        + "[pscustomobject]@{ "
        + "error = $errorMessage; "
        + "unsafe_path_exists = (Test-Path -LiteralPath $unsafePath) "
        + "} | ConvertTo-Json"
    )

    assert result["error"] == "run id must be a safe path segment."
    assert result["unsafe_path_exists"] is False


def test_session_artifact_sync_rejects_overlapping_roots(tmp_path: Path) -> None:
    session_root = tmp_path / "session"
    run_root = session_root / "nested-run"
    result = _run_powershell_json(
        _dot_source_common()
        + f"$sessionRoot = {_ps_quote(session_root)}; "
        + f"$runRoot = {_ps_quote(run_root)}; "
        + "New-Item -ItemType Directory -Path $sessionRoot -Force | Out-Null; "
        + "Set-Content -LiteralPath (Join-Path $sessionRoot 'source.txt') "
        + "-Value 'source'; "
        + "$descriptor = [pscustomobject]@{ "
        + "paths = [pscustomobject]@{}; "
        + "session_root = $sessionRoot; artifact_root = $runRoot }; "
        + "Sync-VibeSessionArtifactsToRunRoot "
        + "-SessionRoot $sessionRoot -RunArtifactRoot $runRoot "
        + "-ArtifactDescriptor $descriptor; "
        + "[pscustomobject]@{ destination_exists = "
        + "(Test-Path -LiteralPath (Join-Path $runRoot 'source.txt')) } "
        + "| ConvertTo-Json"
    )

    assert result["destination_exists"] is False


def test_python_session_artifact_sync_rejects_undeclared_source_root(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    projection = resolve_runtime_artifact_projection(
        agent_root=workspace,
        workspace_root=workspace,
        run_id="session-source-boundary",
        repo_root=REPO_ROOT,
    )
    foreign_root = tmp_path / "foreign-session"
    foreign_root.mkdir()

    with pytest.raises(ValueError, match="contract-declared run root"):
        sync_session_receipts_to_run_artifact_sink(
            projection,
            session_root=foreign_root,
        )


def test_powershell_session_artifact_sync_rejects_undeclared_source_root(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    declared_session = workspace / "outputs" / "runtime" / "vibe-sessions" / "session-source-boundary"
    foreign_session = tmp_path / "foreign-session"
    declared_session.mkdir(parents=True)
    foreign_session.mkdir()
    result = _run_powershell_json(
        _dot_source_common()
        + "$descriptor = Get-VibeArtifactContractDescriptor "
        + f"-RepoRoot {_ps_quote(REPO_ROOT)} -RunId 'session-source-boundary' "
        + f"-WorkspaceRoot {_ps_quote(workspace)}; "
        + "$errorMessage = ''; "
        + "try { Sync-VibeSessionArtifactsToRunRoot "
        + f"-SessionRoot {_ps_quote(foreign_session)} "
        + f"-RunArtifactRoot {_ps_quote(workspace / '.vibeskills' / 'runs' / 'session-source-boundary')} "
        + "-ArtifactDescriptor $descriptor } catch { $errorMessage = $_.Exception.Message }; "
        + "[pscustomobject]@{ error = $errorMessage } | ConvertTo-Json"
    )
    assert "contract-declared run root" in result["error"]


def test_powershell_session_artifact_sync_rejects_undeclared_destination_root(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    run_id = "session-destination-boundary"
    declared_session = (
        workspace / "outputs" / "runtime" / "vibe-sessions" / run_id
    )
    declared_session.mkdir(parents=True)
    foreign_run_root = tmp_path / "foreign-run-root"
    result = _run_powershell_json(
        _dot_source_common()
        + "$descriptor = Get-VibeArtifactContractDescriptor "
        + f"-RepoRoot {_ps_quote(REPO_ROOT)} -RunId {_ps_quote(run_id)} "
        + f"-WorkspaceRoot {_ps_quote(workspace)} -ArtifactRoot {_ps_quote(workspace)}; "
        + "$errorMessage = ''; "
        + "try { Sync-VibeSessionArtifactsToRunRoot "
        + f"-SessionRoot {_ps_quote(declared_session)} "
        + f"-RunArtifactRoot {_ps_quote(foreign_run_root)} "
        + "-ArtifactDescriptor $descriptor } catch { $errorMessage = $_.Exception.Message }; "
        + "[pscustomobject]@{ error = $errorMessage; destination_exists = "
        + f"(Test-Path -LiteralPath {_ps_quote(foreign_run_root)}) "
        + "} | ConvertTo-Json"
    )

    assert "contract-declared run artifact root" in result["error"]
    assert result["destination_exists"] is False


@pytest.mark.parametrize(
    "field",
    [
        "artifact_paths",
        "primary_document_paths",
        "manifest_path",
        "legacy_compatibility_path",
        "session_receipts",
        "legacy_projection_root",
        "legacy_documentation_roots",
        "legacy_removal_release",
        "legacy_write_mode",
    ],
)
def test_python_and_powershell_reject_incomplete_artifact_contracts(
    tmp_path: Path,
    field: str,
) -> None:
    payload = json.loads(
        (REPO_ROOT / "config" / "live-document-contract.json").read_text(
            encoding="utf-8"
        )
    )
    payload["artifact_sink"].pop(field)
    malformed_repo = tmp_path / field
    config_root = malformed_repo / "config"
    config_root.mkdir(parents=True)
    (config_root / "live-document-contract.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=field):
        LiveGovernanceContract.model_validate(payload)

    completed = subprocess.run(
        [
            _powershell(),
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            _dot_source_common()
            + "Get-VibeLiveGovernanceContract "
            + f"-RepoRoot {_ps_quote(malformed_repo)}",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=os.environ.copy(),
        check=False,
        timeout=RUNTIME_INVOCATION_TIMEOUT_SECONDS,
    )
    assert completed.returncode != 0
    assert field in completed.stderr


def test_python_and_powershell_report_a_stable_diagnostic_for_invalid_json(
    tmp_path: Path,
) -> None:
    malformed_repo = tmp_path / "malformed-json"
    config_root = malformed_repo / "config"
    config_root.mkdir(parents=True)
    contract_path = config_root / "live-document-contract.json"
    contract_path.write_text('{"artifact_sink":', encoding="utf-8")

    with pytest.raises(RuntimeError, match="live governance artifact contract is required"):
        resolve_runtime_artifact_projection(
            agent_root=malformed_repo,
            workspace_root=malformed_repo,
            run_id="malformed-json",
            repo_root=malformed_repo,
        )

    completed = subprocess.run(
        [
            _powershell(),
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            _dot_source_common()
            + "Get-VibeLiveGovernanceContract "
            + f"-RepoRoot {_ps_quote(malformed_repo)}",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=RUNTIME_INVOCATION_TIMEOUT_SECONDS,
    )
    assert completed.returncode != 0
    assert "live governance artifact contract is required" in completed.stderr


def test_python_and_powershell_report_a_stable_diagnostic_for_invalid_field_types(
    tmp_path: Path,
) -> None:
    payload = json.loads(
        (REPO_ROOT / "config" / "live-document-contract.json").read_text(
            encoding="utf-8"
        )
    )
    payload["artifact_sink"]["schema_version"] = {"invalid": "type"}
    malformed_repo = tmp_path / "malformed-field-type"
    config_root = malformed_repo / "config"
    config_root.mkdir(parents=True)
    (config_root / "live-document-contract.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="live governance artifact contract is required"):
        resolve_runtime_artifact_projection(
            agent_root=malformed_repo,
            workspace_root=malformed_repo,
            run_id="malformed-field-type",
            repo_root=malformed_repo,
        )

    completed = subprocess.run(
        [
            _powershell(),
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            _dot_source_common()
            + "Get-VibeLiveGovernanceContract "
            + f"-RepoRoot {_ps_quote(malformed_repo)}",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=RUNTIME_INVOCATION_TIMEOUT_SECONDS,
    )
    assert completed.returncode != 0
    assert "live governance artifact contract is required" in completed.stderr


@pytest.mark.parametrize(
    ("mutation", "field_name"),
    [
        ("artifact_sink_object", "artifact_sink"),
        ("proof_retention_object", "proof_retention"),
        ("artifact_paths_object", "artifact_paths"),
        ("primary_document_paths_object", "primary_document_paths"),
        ("session_receipts_object", "session_receipts"),
        ("proof_retention_integer", "proof retention pull_request_days"),
        ("session_receipt_boolean", "copy_to_artifact_sink"),
    ],
)
def test_python_and_powershell_reject_nested_contract_type_mismatches(
    tmp_path: Path,
    mutation: str,
    field_name: str,
) -> None:
    payload = json.loads(
        (REPO_ROOT / "config" / "live-document-contract.json").read_text(
            encoding="utf-8"
        )
    )
    if mutation == "artifact_sink_object":
        payload["artifact_sink"] = []
    elif mutation == "proof_retention_object":
        payload["proof_retention"] = []
    elif mutation == "artifact_paths_object":
        payload["artifact_sink"]["artifact_paths"] = []
    elif mutation == "primary_document_paths_object":
        payload["artifact_sink"]["primary_document_paths"] = 1
    elif mutation == "session_receipts_object":
        payload["artifact_sink"]["session_receipts"] = "runtime/session-receipts"
    elif mutation == "proof_retention_integer":
        payload["proof_retention"]["pull_request_days"] = 30.0
    elif mutation == "session_receipt_boolean":
        payload["artifact_sink"]["session_receipts"]["copy_to_artifact_sink"] = "true"
    else:  # pragma: no cover - protects this test's mutation table
        raise AssertionError(mutation)

    malformed_repo = tmp_path / mutation
    config_root = malformed_repo / "config"
    config_root.mkdir(parents=True)
    (config_root / "live-document-contract.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="live governance artifact contract is required"):
        resolve_runtime_artifact_projection(
            agent_root=malformed_repo,
            workspace_root=malformed_repo,
            run_id=f"nested-type-{mutation}",
            repo_root=malformed_repo,
        )

    completed = subprocess.run(
        [
            _powershell(),
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            _dot_source_common()
            + "Get-VibeLiveGovernanceContract "
            + f"-RepoRoot {_ps_quote(malformed_repo)}",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=RUNTIME_INVOCATION_TIMEOUT_SECONDS,
    )
    assert completed.returncode != 0
    assert field_name in completed.stderr


def test_python_and_powershell_require_exact_contract_property_names(
    tmp_path: Path,
) -> None:
    payload = json.loads(
        (REPO_ROOT / "config" / "live-document-contract.json").read_text(
            encoding="utf-8"
        )
    )
    payload["Artifact_Sink"] = payload.pop("artifact_sink")
    malformed_repo = tmp_path / "case-sensitive-property"
    config_root = malformed_repo / "config"
    config_root.mkdir(parents=True)
    (config_root / "live-document-contract.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="live governance artifact contract is required"):
        resolve_runtime_artifact_projection(
            agent_root=malformed_repo,
            workspace_root=malformed_repo,
            run_id="case-sensitive-property",
            repo_root=malformed_repo,
        )

    completed = subprocess.run(
        [
            _powershell(),
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            _dot_source_common()
            + "Get-VibeLiveGovernanceContract "
            + f"-RepoRoot {_ps_quote(malformed_repo)}",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=RUNTIME_INVOCATION_TIMEOUT_SECONDS,
    )
    assert completed.returncode != 0
    assert "artifact_sink" in completed.stderr


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("documents", []),
        ("stable_entry_links", []),
        ("proof_retention", {}),
    ],
)
def test_python_and_powershell_reject_malformed_top_level_live_contract_fields(
    tmp_path: Path,
    field: str,
    invalid_value: object,
) -> None:
    payload = json.loads(
        (REPO_ROOT / "config" / "live-document-contract.json").read_text(
            encoding="utf-8"
        )
    )
    payload[field] = invalid_value
    malformed_repo = tmp_path / field
    config_root = malformed_repo / "config"
    config_root.mkdir(parents=True)
    (config_root / "live-document-contract.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="live governance artifact contract is required"):
        resolve_runtime_artifact_projection(
            agent_root=malformed_repo,
            workspace_root=malformed_repo,
            run_id=f"invalid-{field}",
            repo_root=malformed_repo,
        )

    completed = subprocess.run(
        [
            _powershell(),
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            _dot_source_common()
            + "Get-VibeLiveGovernanceContract "
            + f"-RepoRoot {_ps_quote(malformed_repo)}",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=RUNTIME_INVOCATION_TIMEOUT_SECONDS,
    )
    assert completed.returncode != 0
    assert "live governance artifact contract is required" in completed.stderr
    assert field in completed.stderr


def test_python_and_powershell_require_the_contract_at_the_explicit_repo_root(
    tmp_path: Path,
) -> None:
    parent_repo = tmp_path / "parent"
    child_repo = parent_repo / "child"
    (parent_repo / "config").mkdir(parents=True)
    child_repo.mkdir()
    shutil.copy2(
        REPO_ROOT / "config" / "live-document-contract.json",
        parent_repo / "config" / "live-document-contract.json",
    )

    with pytest.raises(RuntimeError, match="live governance artifact contract is required"):
        resolve_runtime_artifact_projection(
            agent_root=child_repo,
            workspace_root=child_repo,
            run_id="explicit-repo-root",
            repo_root=child_repo,
        )

    completed = subprocess.run(
        [
            _powershell(),
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            _dot_source_common()
            + "Get-VibeLiveGovernanceContract "
            + f"-RepoRoot {_ps_quote(child_repo)}",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=RUNTIME_INVOCATION_TIMEOUT_SECONDS,
    )
    assert completed.returncode != 0
    assert "live governance artifact contract is required" in completed.stderr


@pytest.mark.parametrize(
    "artifact_root",
    [
        "docs/requirements",
        "docs/requirements/runs",
        "docs/plans/archive",
    ],
)
def test_python_and_powershell_reject_artifact_sinks_in_historical_roots(
    tmp_path: Path,
    artifact_root: str,
) -> None:
    payload = json.loads(
        (REPO_ROOT / "config" / "live-document-contract.json").read_text(
            encoding="utf-8"
        )
    )
    payload["artifact_sink"]["root"] = artifact_root
    malformed_repo = tmp_path / "historical-sink"
    config_root = malformed_repo / "config"
    config_root.mkdir(parents=True)
    (config_root / "live-document-contract.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="historical documentation roots"):
        LiveGovernanceContract.model_validate(payload)

    completed = subprocess.run(
        [
            _powershell(),
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            _dot_source_common()
            + "Get-VibeLiveGovernanceContract "
            + f"-RepoRoot {_ps_quote(malformed_repo)}",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=RUNTIME_INVOCATION_TIMEOUT_SECONDS,
    )
    assert completed.returncode != 0
    assert "historical documentation roots" in completed.stderr


@pytest.mark.parametrize(
    "required_metadata",
    [
        ["commit_sha", "execution_environment", "commit_sha"],
        ["commit_sha", "execution_environment", ""],
    ],
)
def test_python_and_powershell_reject_invalid_required_metadata(
    tmp_path: Path,
    required_metadata: list[str],
) -> None:
    payload = json.loads(
        (REPO_ROOT / "config" / "live-document-contract.json").read_text(
            encoding="utf-8"
        )
    )
    payload["artifact_sink"]["required_metadata"] = required_metadata
    malformed_repo = tmp_path / "invalid-required-metadata"
    config_root = malformed_repo / "config"
    config_root.mkdir(parents=True)
    (config_root / "live-document-contract.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="required_metadata"):
        LiveGovernanceContract.model_validate(payload)

    completed = subprocess.run(
        [
            _powershell(),
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            _dot_source_common()
            + "Get-VibeLiveGovernanceContract "
            + f"-RepoRoot {_ps_quote(malformed_repo)}",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=os.environ.copy(),
        check=False,
        timeout=RUNTIME_INVOCATION_TIMEOUT_SECONDS,
    )
    assert completed.returncode != 0
    assert "required_metadata" in completed.stderr


def test_python_and_powershell_reject_unsupported_artifact_kinds(
    tmp_path: Path,
) -> None:
    payload = json.loads(
        (REPO_ROOT / "config" / "live-document-contract.json").read_text(
            encoding="utf-8"
        )
    )
    payload["artifact_sink"]["required_artifacts"].append("audit")
    payload["artifact_sink"]["artifact_paths"]["audit"] = "audit.json"
    malformed_repo = tmp_path / "unsupported-artifact-kind"
    config_root = malformed_repo / "config"
    config_root.mkdir(parents=True)
    (config_root / "live-document-contract.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unsupported artifact kinds"):
        LiveGovernanceContract.model_validate(payload)

    completed = subprocess.run(
        [
            _powershell(),
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            _dot_source_common()
            + "Get-VibeLiveGovernanceContract "
            + f"-RepoRoot {_ps_quote(malformed_repo)}",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=os.environ.copy(),
        check=False,
        timeout=RUNTIME_INVOCATION_TIMEOUT_SECONDS,
    )
    assert completed.returncode != 0
    assert "unsupported" in completed.stderr


@pytest.mark.parametrize("has_commit,runtime_layout", [
    (False, "checkout"), (True, "checkout"), (True, "worktree"),
    (False, "nested-install"), (True, "nested-install"),
    (False, "invalid-marker"), (True, "invalid-marker"),
])
@pytest.mark.parametrize("redirected_git", [False, True])
def test_commit_sha_uses_only_a_successful_git_revision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, has_commit: bool, runtime_layout: str,
    redirected_git: bool,
) -> None:
    git_env = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
    repository = tmp_path / "provenance-repository"
    subprocess.run(["git", "init", "--quiet", str(repository)], env=git_env, check=True)
    fallback = "source-commit-fallback"
    monkeypatch.setenv("VGO_COMMIT_SHA", fallback)
    expected = fallback
    if has_commit:
        subprocess.run(["git", "-C", str(repository), "-c", "user.email=test@example.com",
                        "-c", "user.name=Vibe Tests", "-c", "commit.gpgsign=false", "commit",
                        "--allow-empty", "--quiet", "-m", "test provenance"], env=git_env, check=True)
        expected = subprocess.check_output(
            ["git", "-C", str(repository), "rev-parse", "HEAD"], env=git_env, text=True,
        ).strip()
    if redirected_git:
        foreign_repository = tmp_path / "caller-repository"
        subprocess.run(["git", "init", "--quiet", str(foreign_repository)], env=git_env, check=True)
        subprocess.run(
            ["git", "-C", str(foreign_repository), "-c", "user.email=test@example.com",
             "-c", "user.name=Vibe Tests", "-c", "commit.gpgsign=false", "commit",
             "--allow-empty", "--quiet", "-m", "caller provenance"], env=git_env, check=True,
        )
        monkeypatch.setenv("GIT_DIR", str(foreign_repository / ".git"))
        monkeypatch.setenv("GIT_COMMON_DIR", str(foreign_repository / ".git"))
        monkeypatch.setenv("GIT_WORK_TREE", str(foreign_repository))
    caller_git_environment = {key: value for key, value in os.environ.items() if key.upper().startswith("GIT_")}
    runtime_root = repository
    if runtime_layout == "worktree":
        runtime_root = tmp_path / "runtime worktree"
        subprocess.run(
            ["git", "-C", str(repository), "worktree", "add", "--quiet", "--detach", str(runtime_root), "HEAD"],
            env=git_env, check=True,
        )
    elif runtime_layout in {"nested-install", "invalid-marker"}:
        runtime_root = repository / "installed-vibe"
        expected = fallback
        if runtime_layout == "invalid-marker":
            (runtime_root / ".git").mkdir(parents=True)
    _write_contract_repository(runtime_root, legacy_write_mode="disabled")
    python_workspace = tmp_path / "python-workspace"
    python_workspace.mkdir()
    projection = resolve_runtime_artifact_projection(
        agent_root=python_workspace, workspace_root=python_workspace,
        run_id="commit-provenance", repo_root=runtime_root,
    )
    python_manifest = write_runtime_artifact_bundle(
        projection, repo_root=runtime_root,
        requirement={}, plan={}, status={}, proof={},
    ).model_dump()
    powershell_result = _run_powershell_json(
        _dot_source_common()
        + "$callerGitEnvironment = [Environment]::GetEnvironmentVariable('GIT_DIR', 'Process'); "
        + "$result = Write-VibeRunArtifactBundle "
        + f"-RepoRoot {_ps_quote(runtime_root)} -RunId 'commit-provenance' "
        + f"-ArtifactRoot {_ps_quote(tmp_path / 'powershell-workspace')} "
        + "-Requirement ([pscustomobject]@{}) -Plan ([pscustomobject]@{}) "
        + "-Status ([pscustomobject]@{}) -Proof ([pscustomobject]@{}); "
        + "if ([Environment]::GetEnvironmentVariable('GIT_DIR', 'Process') -cne $callerGitEnvironment) "
        + "{ throw 'Caller Git environment changed' }; "
        + "$result | ConvertTo-Json -Depth 20"
    )
    assert {key: value for key, value in os.environ.items() if key.upper().startswith("GIT_")} == caller_git_environment
    assert (python_manifest["commit_sha"], powershell_result["manifest"]["commit_sha"]) == (expected, expected)
