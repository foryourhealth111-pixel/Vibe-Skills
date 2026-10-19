from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from shutil import copy2
from typing import Any

CONTRACTS_SRC = Path(__file__).resolve().parents[3] / "contracts" / "src"
if CONTRACTS_SRC.is_dir() and str(CONTRACTS_SRC) not in sys.path:
    sys.path.insert(0, str(CONTRACTS_SRC))

from vgo_contracts.live_governance_contract import (  # noqa: E402
    LIVE_GOVERNANCE_CONTRACT_RELPATH,
    LiveGovernanceContract,
    RunArtifactManifest,
    load_live_governance_contract_file,
    normalize_legacy_write_destination,
)


@dataclass(frozen=True, slots=True)
class RuntimeArtifactProjection:
    """Resolved paths for the one live run-artifact contract."""

    contract: LiveGovernanceContract
    workspace_root: Path
    session_root: Path
    run_id: str
    run_root: Path
    artifact_paths: dict[str, Path]
    primary_document_paths: dict[str, Path]
    legacy_run_root: Path
    legacy_projection_enabled: bool

    @property
    def manifest_path(self) -> Path:
        return self.artifact_paths["manifest"]

    @property
    def artifact_sink(self):
        return self.contract.artifact_sink

    def relative_run_root(self) -> str:
        return (Path(self.artifact_sink.root) / self.run_id).as_posix()


def _assert_no_symlink_components(*, root: Path, path: Path, label: str) -> None:
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{label} resolves outside its root: {path}") from exc
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"{label} must not contain symlinks: {current}")


def _load_contract(repo_root: Path) -> LiveGovernanceContract:
    contract_path = repo_root.resolve() / LIVE_GOVERNANCE_CONTRACT_RELPATH
    try:
        return load_live_governance_contract_file(contract_path)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise RuntimeError(
            f"live governance artifact contract is required: {contract_path}: {exc}"
        ) from exc


def _coerce_legacy_write_destination(
    value: object,
    *,
    workspace_root: Path,
    declared_roots: tuple[str, ...],
) -> str:
    """Convert caller paths to the contract's workspace-relative POSIX form."""
    if not isinstance(value, str):
        raise ValueError("legacy compatibility writes must be strings")
    raw = value.strip()
    if not raw:
        raise ValueError("legacy compatibility writes must not contain empty paths")
    candidate = Path(raw).expanduser()
    is_absolute = candidate.is_absolute() or PureWindowsPath(raw).is_absolute()
    if is_absolute:
        resolved_workspace = workspace_root.resolve()
        resolved_candidate = candidate.resolve()
        try:
            raw = resolved_candidate.relative_to(resolved_workspace).as_posix()
        except ValueError as exc:
            raise ValueError(
                "legacy compatibility writes must remain within the workspace "
                f"and use declared legacy compatibility roots: {value}"
            ) from exc
    return normalize_legacy_write_destination(raw, declared_roots)


def load_runtime_artifact_contract(repo_root: str | Path) -> LiveGovernanceContract:
    """Load the exact repo-owned live governance contract or fail closed."""
    return _load_contract(Path(repo_root))


def resolve_runtime_session_receipts_root(
    *,
    repo_root: str | Path,
    artifact_root: str | Path,
) -> Path:
    contract = load_runtime_artifact_contract(repo_root)
    return contract.artifact_sink.session_receipts.resolve_root(artifact_root)


def resolve_runtime_session_root(
    *,
    repo_root: str | Path,
    artifact_root: str | Path,
    run_id: str,
) -> Path:
    contract = load_runtime_artifact_contract(repo_root)
    return contract.artifact_sink.session_receipts.resolve_run_root(
        artifact_root,
        run_id,
    )


def resolve_runtime_artifact_projection(
    *,
    agent_root: Path,
    workspace_root: Path | None,
    session_artifact_root: Path | None = None,
    run_id: str,
    repo_root: Path,
) -> RuntimeArtifactProjection:
    resolved_agent_root = agent_root.resolve()
    resolved_workspace_root = (
        workspace_root.resolve() if workspace_root is not None else resolved_agent_root
    )
    resolved_session_artifact_root = (
        session_artifact_root.resolve()
        if session_artifact_root is not None
        else resolved_workspace_root
    )
    normalized_run_id = str(run_id).strip()
    contract = _load_contract(repo_root.resolve())
    sink = contract.artifact_sink
    normalized_workspace = (
        "/" + resolved_workspace_root.as_posix().strip("/").casefold() + "/"
    )
    if any(
        "/" + legacy_root.replace("\\", "/").strip("/").casefold() + "/"
        in normalized_workspace
        for legacy_root in sink.legacy_documentation_roots
    ):
        raise ValueError(
            "historical documentation roots cannot be used as the artifact workspace"
        )
    run_root = sink.resolve_run_root(resolved_workspace_root, normalized_run_id)
    session_root = sink.session_receipts.resolve_run_root(
        resolved_session_artifact_root,
        normalized_run_id,
    )
    artifact_paths = sink.resolve_run_artifact_paths(
        resolved_workspace_root,
        normalized_run_id,
    )
    primary_document_paths = sink.resolve_run_primary_document_paths(
        resolved_workspace_root,
        normalized_run_id,
    )
    legacy_run_root = (
        resolved_agent_root / Path(sink.legacy_projection_root) / normalized_run_id
    )
    _assert_no_symlink_components(
        root=resolved_agent_root,
        path=legacy_run_root,
        label="legacy run path",
    )
    return RuntimeArtifactProjection(
        contract=contract,
        workspace_root=resolved_workspace_root,
        session_root=session_root,
        run_id=normalized_run_id,
        run_root=run_root,
        artifact_paths=artifact_paths,
        primary_document_paths=primary_document_paths,
        legacy_run_root=legacy_run_root,
        # Calls that omit workspace_root are the pre-contract Python API. Keep
        # a marked read-compatible projection until that API is removed.
        legacy_projection_enabled=(
            workspace_root is None and sink.legacy_write_mode != "disabled"
        ),
    )


def _write_json(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def _write_primary_document(
    path: Path,
    *,
    kind: str,
    run_id: str,
    schema_version: int,
    payload: dict[str, Any],
) -> Path:
    payload_text = json.dumps(payload, ensure_ascii=False, indent=2)
    fence = "```"
    while fence in payload_text:
        fence += "`"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            (
                f"# Run {kind.title()}",
                "",
                f"- Run ID: `{run_id}`",
                f"- Schema version: `{schema_version}`",
                "",
                "## Payload",
                "",
                f"{fence}json",
                payload_text,
                fence,
                "",
            )
        ),
        encoding="utf-8",
    )
    return path


def _git_commit_sha(repo_root: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return str(os.environ.get("VGO_COMMIT_SHA") or "unknown").strip() or "unknown"
    return completed.stdout.strip() or "unknown"


def execution_environment(*, repo_root: Path, host_id: str | None = None) -> dict[str, str]:
    del repo_root
    return {
        "os": platform.system().lower() or "unknown",
        "runtime": "python",
        "runtime_version": platform.python_version(),
        "host_id": str(host_id or "unknown").strip() or "unknown",
    }


def _envelope(*, kind: str, run_id: str, payload: dict[str, Any], schema_version: int) -> dict[str, Any]:
    return {
        **payload,
        "schema_version": schema_version,
        "artifact_kind": kind,
        "run_id": run_id,
        "payload": payload,
    }


def write_runtime_artifact_bundle(
    projection: RuntimeArtifactProjection,
    *,
    requirement: dict[str, Any],
    plan: dict[str, Any],
    status: dict[str, Any],
    proof: dict[str, Any],
    repo_root: Path,
    host_id: str | None = None,
    legacy_writes: list[str] | None = None,
) -> RunArtifactManifest:
    """Write the required artifacts and validate the manifest before returning."""
    sink = projection.artifact_sink
    payloads = {
        "requirement": requirement,
        "plan": plan,
        "status": status,
        "proof": proof,
    }
    declared_legacy_roots = (
        *sink.legacy_documentation_roots,
        sink.legacy_projection_root,
    )
    requested_legacy_writes = [
        _coerce_legacy_write_destination(
            destination,
            workspace_root=projection.workspace_root,
            declared_roots=declared_legacy_roots,
        )
        for destination in (legacy_writes or [])
    ]
    if projection.legacy_projection_enabled:
        requested_legacy_writes.append(
            (Path(sink.legacy_projection_root) / projection.run_id).as_posix()
        )
    resolved_legacy_writes = []
    seen_legacy_writes: set[str] = set()
    for destination in requested_legacy_writes:
        folded_destination = destination.casefold()
        if folded_destination not in seen_legacy_writes:
            seen_legacy_writes.add(folded_destination)
            resolved_legacy_writes.append(destination)
    if sink.legacy_write_mode == "disabled" and resolved_legacy_writes:
        raise ValueError("disabled legacy compatibility cannot declare writes")
    compatibility = {
        "mode": sink.legacy_write_mode,
        "removal_release": sink.legacy_removal_release,
        "documentation_roots": list(sink.legacy_documentation_roots),
        "writes": resolved_legacy_writes,
        "write_records": [
            {
                "destination": destination,
                "mode": sink.legacy_write_mode,
                "removal_release": sink.legacy_removal_release,
            }
            for destination in resolved_legacy_writes
        ],
        "observable": True,
    }
    manifest_payload = {
        "schema_version": sink.schema_version,
        "run_id": projection.run_id,
        "artifact_root": projection.relative_run_root(),
        "artifacts": {
            kind: sink.artifact_path_map[kind] for kind in sink.required_artifacts
        },
        "commit_sha": _git_commit_sha(repo_root.resolve()),
        "execution_environment": execution_environment(
            repo_root=repo_root,
            host_id=host_id,
        ),
        "legacy_compatibility": compatibility,
    }
    manifest = projection.contract.validate_run_artifact_manifest(manifest_payload)
    for kind in sink.required_artifacts:
        path = projection.artifact_paths[kind]
        _write_json(
            path,
            _envelope(
                kind=kind,
                run_id=projection.run_id,
                payload=payloads[kind],
                schema_version=sink.schema_version,
            ),
        )
    for kind, path in projection.primary_document_paths.items():
        _write_primary_document(
            path,
            kind=kind,
            run_id=projection.run_id,
            schema_version=sink.schema_version,
            payload=payloads[kind],
        )
    _write_json(projection.manifest_path, manifest.model_dump())
    _write_json(
        projection.artifact_paths["legacy_compatibility"],
        {
            "run_id": projection.run_id,
            "artifact_root": projection.relative_run_root(),
            **compatibility,
        },
    )
    if projection.legacy_projection_enabled:
        _mirror_legacy_projection(projection)
    return manifest


def _validated_run_tree_files(root: Path) -> list[Path]:
    if root.is_symlink():
        raise ValueError(f"run artifact trees must not contain symlinks: {root}")
    if not root.exists():
        return []
    resolved_root = root.resolve(strict=True)
    files: list[Path] = []
    for entry in root.rglob("*"):
        if entry.is_symlink():
            raise ValueError(
                f"run artifact trees must not contain symlinks: {entry}"
            )
        if not entry.is_file():
            continue
        if not entry.resolve(strict=True).is_relative_to(resolved_root):
            raise ValueError(f"run artifact entry resolves outside its root: {entry}")
        files.append(entry)
    return files


def _copy_run_tree(
    *,
    source_root: Path,
    destination_root: Path,
    reserved_destinations: set[Path] | None = None,
) -> None:
    source_files = _validated_run_tree_files(source_root)
    _validated_run_tree_files(destination_root)
    destination_root.mkdir(parents=True, exist_ok=True)
    resolved_destination_root = destination_root.resolve(strict=True)
    resolved_reserved_destinations = {
        path.resolve(strict=False) for path in (reserved_destinations or set())
    }
    for source in source_files:
        destination = destination_root / source.relative_to(source_root)
        if not destination.resolve(strict=False).is_relative_to(
            resolved_destination_root
        ):
            raise ValueError(
                f"run artifact copy path resolves outside its root: {destination}"
            )
        if destination.resolve(strict=False) in resolved_reserved_destinations:
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        _assert_no_symlink_components(
            root=destination_root,
            path=destination,
            label="run artifact copy path",
        )
        if destination.is_symlink():
            raise ValueError(
                f"run artifact trees must not contain symlinks: {destination}"
            )
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".vibe-receipt-", suffix=".tmp", dir=destination.parent,
        )
        os.close(descriptor)
        temporary_path = Path(temporary_name)
        try:
            copy2(source, temporary_path)
            _assert_no_symlink_components(
                root=destination_root, path=destination, label="run artifact copy path",
            )
            os.replace(temporary_path, destination)
        finally:
            temporary_path.unlink(missing_ok=True)


def sync_session_receipts_to_run_artifact_sink(
    projection: RuntimeArtifactProjection,
    *,
    session_root: str | Path,
) -> None:
    """Copy runtime-owned workspace-local session files into the run sink."""
    if not projection.artifact_sink.session_receipts.copy_to_artifact_sink:
        return
    resolved_session_root = Path(session_root).resolve()
    declared_session_root = projection.session_root.resolve()
    if resolved_session_root != declared_session_root:
        raise ValueError(
            "session receipt source must match the contract-declared run root: "
            f"{resolved_session_root} != {declared_session_root}"
        )
    resolved_run_root = projection.run_root.resolve()
    session_prefix = resolved_session_root.parts
    run_prefix = resolved_run_root.parts
    if (
        resolved_session_root == resolved_run_root
        or session_prefix[: len(run_prefix)] == run_prefix
        or run_prefix[: len(session_prefix)] == session_prefix
    ):
        return
    reserved_destinations = {
        *projection.artifact_paths.values(),
        *projection.primary_document_paths.values(),
    }
    _copy_run_tree(
        source_root=resolved_session_root,
        destination_root=resolved_run_root,
        reserved_destinations=reserved_destinations,
    )


def _mirror_legacy_projection(projection: RuntimeArtifactProjection) -> None:
    if projection.legacy_run_root == projection.run_root:
        return
    _copy_run_tree(
        source_root=projection.run_root,
        destination_root=projection.legacy_run_root,
    )


def seed_canonical_run_from_legacy_if_needed(
    projection: RuntimeArtifactProjection,
) -> bool:
    """Copy a pre-contract run into the canonical sink before resuming it."""
    if (
        not projection.legacy_projection_enabled
        or projection.run_root.exists()
        or not projection.legacy_run_root.is_dir()
    ):
        return False
    _copy_run_tree(
        source_root=projection.legacy_run_root,
        destination_root=projection.run_root,
    )
    return True


def mirror_legacy_run_if_needed(projection: RuntimeArtifactProjection) -> None:
    """Refresh the compatibility tree after later work-unit writes."""
    if projection.legacy_projection_enabled:
        _mirror_legacy_projection(projection)


def load_runtime_artifact_manifest(
    projection: RuntimeArtifactProjection,
    *,
    path: Path | None = None,
) -> dict[str, Any]:
    path = path or projection.manifest_path
    if not path.is_file():
        raise ValueError(f"missing run artifact manifest: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"run artifact manifest must be an object: {path}")
    projection.contract.validate_run_artifact_manifest(payload)
    return payload


__all__ = [
    "RuntimeArtifactProjection",
    "execution_environment",
    "load_runtime_artifact_contract",
    "load_runtime_artifact_manifest",
    "mirror_legacy_run_if_needed",
    "resolve_runtime_artifact_projection",
    "resolve_runtime_session_receipts_root",
    "resolve_runtime_session_root",
    "seed_canonical_run_from_legacy_if_needed",
    "sync_session_receipts_to_run_artifact_sink",
    "write_runtime_artifact_bundle",
]
