from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

from ._bootstrap import ensure_contracts_src_on_path

ensure_contracts_src_on_path()

from vgo_contracts.canonical_vibe_contract import uses_skill_only_activation
from vgo_contracts.host_runtime_readiness import evaluate_host_runtime_readiness

TrackCreatedPath = Callable[[Path | str], None]
RecordManagedJson = Callable[[Path], None]


def detect_platform_tag() -> str:
    if os.name == "nt":
        return "windows"
    if os.sys.platform.lower().startswith("darwin"):
        return "macos"
    return "linux"


def _write_json_file(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Failed to parse JSON settings file: {path} ({exc})") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"Expected JSON object in settings file: {path}")
    return payload


def install_claude_managed_settings(
    repo_root: Path,
    target_root: Path,
    *,
    track_created_path: TrackCreatedPath,
    record_managed_json: RecordManagedJson,
    record_merged_file: Callable[..., None],
) -> list[str]:
    settings_path = target_root / "settings.json"
    created_if_absent = not settings_path.exists()
    settings = _load_json_object(settings_path)
    settings["vibeskills"] = {
        "managed": True,
        "host_id": "claude-code",
        "skills_root": str((target_root / "skills").resolve()),
        "runtime_skill_entry": str((target_root / "skills" / "vibe" / "SKILL.md").resolve()),
        "explicit_vibe_skill_invocation": ["/vibe", "$vibe"],
    }
    _write_json_file(settings_path, settings)
    if created_if_absent:
        track_created_path(settings_path)
    record_managed_json(settings_path)
    record_merged_file(settings_path, created_if_absent=created_if_absent)
    return [str(settings_path.resolve())]


def path_points_inside_target_root(value: object, target_root: Path) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    candidate = Path(value.strip()).expanduser()
    if not candidate.is_absolute():
        candidate = target_root / candidate
    try:
        candidate.resolve(strict=False).relative_to(target_root.resolve())
        return True
    except ValueError:
        return False


def is_owned_legacy_opencode_vibeskills_node(node: object, target_root: Path) -> bool:
    if not isinstance(node, dict):
        return False
    host_id = str(node.get("host_id") or "").strip().lower()
    if host_id and host_id != "opencode":
        return False
    if bool(node.get("managed", False)):
        return True
    for key in (
        "commands_root",
        "command_root_compat",
        "agents_root",
        "agent_root_compat",
        "specialist_wrapper",
    ):
        if path_points_inside_target_root(node.get(key), target_root):
            return True
    return False


def sanitize_legacy_opencode_config(target_root: Path) -> dict[str, object]:
    settings_path = target_root / "opencode.json"
    receipt: dict[str, object] = {
        "path": str(settings_path.resolve()),
        "status": "not-present",
    }
    if not settings_path.exists():
        return receipt

    try:
        payload = json.loads(settings_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        receipt["status"] = "parse-failed"
        return receipt

    if not isinstance(payload, dict):
        receipt["status"] = "non-object"
        return receipt

    vibeskills_node = payload.get("vibeskills")
    if vibeskills_node is None:
        receipt["status"] = "already-clean"
        return receipt
    if not is_owned_legacy_opencode_vibeskills_node(vibeskills_node, target_root):
        receipt["status"] = "foreign-node-preserved"
        return receipt

    next_payload = dict(payload)
    del next_payload["vibeskills"]
    if next_payload:
        _write_json_file(settings_path, next_payload)
        receipt["status"] = "removed-owned-node"
        receipt["preserved_keys"] = sorted(next_payload.keys())
    else:
        settings_path.unlink()
        receipt["status"] = "removed-owned-node-and-deleted-empty-file"
    return receipt


def materialize_host_settings(
    target_root: Path,
    adapter: dict[str, Any],
    *,
    track_created_path: TrackCreatedPath,
    record_managed_json: RecordManagedJson,
) -> list[str]:
    host_id = adapter["id"]
    materialized: list[str] = []
    if uses_skill_only_activation(host_id):
        settings_path = target_root / ".vibeskills" / "host-settings.json"
        host_settings = {
            "schema_version": 1,
            "host_id": host_id,
            "managed": True,
            "skills_root": str((target_root / "skills").resolve()),
            "runtime_skill_entry": str((target_root / "skills" / "vibe" / "SKILL.md").resolve()),
            "explicit_vibe_skill_invocation": ["$vibe", "/vibe"],
            "specialist_execution": {
                "mode": "same_session_path_only",
                "path_source": "native_skill_entrypoint",
                "hidden_subprocess_removed": True,
            },
        }
        commands_root = target_root / "commands"
        agents_root = target_root / "agents"
        workflow_root = target_root / "global_workflows"
        mcp_config = target_root / "mcp_config.json"
        if commands_root.exists():
            host_settings["commands_root"] = str(commands_root.resolve())
        if agents_root.exists():
            host_settings["agents_root"] = str(agents_root.resolve())
        if workflow_root.exists():
            host_settings["workflow_root"] = str(workflow_root.resolve())
        if mcp_config.exists():
            host_settings["mcp_config"] = str(mcp_config.resolve())
        _write_json_file(settings_path, host_settings)
        materialized.append(str(settings_path.resolve()))
        record_managed_json(settings_path)
        track_created_path(settings_path)
    return materialized


def materialize_host_closure(
    repo_root: Path,
    target_root: Path,
    adapter: dict[str, Any],
    *,
    track_created_path: TrackCreatedPath,
    record_managed_json: RecordManagedJson,
) -> tuple[Path, dict[str, Any]]:
    """Materialize host-closure metadata using live runtime readiness checks."""
    host_id = adapter["id"]
    settings_materialized = materialize_host_settings(
        target_root,
        adapter,
        track_created_path=track_created_path,
        record_managed_json=record_managed_json,
    )
    commands_root = target_root / "commands"
    bridge_runtime_ready = bool(settings_materialized) or commands_root.exists()
    runtime_readiness = evaluate_host_runtime_readiness(
        repo_root,
        host_id,
        bridge_runtime_ready=bridge_runtime_ready,
    )
    closure_state = str(runtime_readiness["recommended_host_closure_state"])
    closure = {
        "schema_version": 1,
        "host_id": host_id,
        "platform": detect_platform_tag(),
        "target_root": str(target_root.resolve()),
        "install_mode": adapter["install_mode"],
        "entry_mode": runtime_readiness["entry_mode"],
        "host_closure_driver": runtime_readiness["readiness_driver"],
        "effective_runtime_ready": bool(runtime_readiness["effective_runtime_ready"]),
        "skills_root": str((target_root / "skills").resolve()),
        "runtime_skill_entry": str((target_root / "skills" / "vibe" / "SKILL.md").resolve()),
        "commands_root": str(commands_root.resolve()),
        "global_workflows_root": str((target_root / "global_workflows").resolve()),
        "mcp_config_path": str((target_root / "mcp_config.json").resolve()),
        "host_closure_state": closure_state,
        "commands_materialized": commands_root.exists(),
        "settings_materialized": settings_materialized,
        "direct_runtime": dict(runtime_readiness["direct_runtime"]),
        "bridge_runtime": dict(runtime_readiness["bridge_runtime"]),
        "specialist_execution": {
            "mode": "same_session_path_only",
            "path_source": "native_skill_entrypoint",
            "hidden_subprocess_removed": True,
        },
        "specialist_wrapper": {
            "ready": False,
            "removed": True,
            "removal_reason": "same_session_path_only",
        },
    }
    closure_path = target_root / ".vibeskills" / "host-closure.json"
    _write_json_file(closure_path, closure)
    track_created_path(closure_path)
    return closure_path, closure


def is_closed_ready_required(adapter: dict[str, Any]) -> bool:
    return (adapter.get("install_mode") or "").strip().lower() != "governed"
