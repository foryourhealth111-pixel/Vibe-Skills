from __future__ import annotations

import json
import os
import shutil
import stat
from pathlib import Path
from typing import Any, Callable

from ._bootstrap import ensure_contracts_src_on_path

ensure_contracts_src_on_path()

from vgo_contracts.runtime_surface_contract import uses_skill_only_activation

HOST_BRIDGE_COMMAND_CANDIDATES = {
    "claude-code": ["claude", "claude-code"],
    "cursor": ["cursor-agent", "cursor"],
    "windsurf": ["windsurf", "codeium"],
    "openclaw": ["openclaw"],
    "opencode": ["opencode"],
}
HOST_BRIDGE_COMMAND_ENV = {
    "claude-code": "VGO_CLAUDE_CODE_SPECIALIST_BRIDGE_COMMAND",
    "cursor": "VGO_CURSOR_SPECIALIST_BRIDGE_COMMAND",
    "windsurf": "VGO_WINDSURF_SPECIALIST_BRIDGE_COMMAND",
    "openclaw": "VGO_OPENCLAW_SPECIALIST_BRIDGE_COMMAND",
    "opencode": "VGO_OPENCODE_SPECIALIST_BRIDGE_COMMAND",
}

TrackCreatedPath = Callable[[Path | str], None]
RecordManagedJson = Callable[[Path], None]
RecordSpecialistWrapper = Callable[[Path], None]


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


def _copy_file(src: Path, dst: Path, *, track_created_path: TrackCreatedPath) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    track_created_path(dst)


def _ensure_executable(path: Path) -> None:
    current = path.stat().st_mode
    path.chmod(current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def should_replace_claude_pretooluse_hook_entry(
    entry: dict[str, Any],
    *,
    managed_description: str,
    hook_command: str,
) -> bool:
    existing_hooks = entry.get("hooks")
    existing_command = ""
    if isinstance(existing_hooks, list) and existing_hooks:
        first_hook = existing_hooks[0]
        if isinstance(first_hook, dict):
            existing_command = str(first_hook.get("command") or "").strip()
    if existing_command:
        return existing_command == hook_command
    description = str(entry.get("description") or "").strip()
    return bool(description) and description == managed_description


def upsert_claude_pretooluse_hook(settings: dict[str, Any], hook_command: str) -> None:
    managed_description = "VibeSkills managed write guard"
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        hooks = {}
    pre_tool_use = hooks.get("PreToolUse")
    if not isinstance(pre_tool_use, list):
        pre_tool_use = []

    managed_entry = {
        "matcher": "Write",
        "hooks": [
            {
                "type": "command",
                "command": hook_command,
            }
        ],
        "description": managed_description,
    }

    next_pre_tool_use = []
    replaced = False
    for entry in pre_tool_use:
        if not isinstance(entry, dict):
            next_pre_tool_use.append(entry)
            continue
        if should_replace_claude_pretooluse_hook_entry(
            entry,
            managed_description=managed_description,
            hook_command=hook_command,
        ):
            if not replaced:
                next_pre_tool_use.append(managed_entry)
                replaced = True
            continue
        next_pre_tool_use.append(entry)

    if not replaced:
        next_pre_tool_use.append(managed_entry)

    hooks["PreToolUse"] = next_pre_tool_use
    settings["hooks"] = hooks


def resolve_bridge_command(host_id: str) -> tuple[str | None, str | None]:
    env_name = HOST_BRIDGE_COMMAND_ENV.get(host_id)
    if env_name:
        env_value = os.environ.get(env_name, "").strip()
        if env_value:
            candidate = shutil.which(env_value)
            if candidate:
                return candidate, f"env:{env_name}"
            path_candidate = Path(env_value).expanduser()
            if path_candidate.exists():
                return str(path_candidate.resolve()), f"env:{env_name}"

    for candidate_name in HOST_BRIDGE_COMMAND_CANDIDATES.get(host_id, []):
        resolved = shutil.which(candidate_name)
        if resolved:
            return resolved, f"path:{candidate_name}"

    return None, None


def materialize_host_specialist_wrapper(
    target_root: Path,
    host_id: str,
    bridge_command: str | None,
    *,
    track_created_path: TrackCreatedPath,
    record_specialist_wrapper: RecordSpecialistWrapper,
) -> dict[str, Any]:
    tools_root = target_root / ".vibeskills" / "bin"
    tools_root.mkdir(parents=True, exist_ok=True)
    track_created_path(tools_root)

    wrapper_py = tools_root / f"{host_id}-specialist-wrapper.py"
    embedded_command = json.dumps(bridge_command or "")
    bridge_env_name = f"VGO_{host_id.upper().replace('-', '_')}_SPECIALIST_BRIDGE_COMMAND"
    wrapper_py.write_text(
        (
            "#!/usr/bin/env python3\n"
            "import os\n"
            "import subprocess\n"
            "import sys\n\n"
            f"HOST_ID = {json.dumps(host_id)}\n"
            f"TARGET_COMMAND = {embedded_command}\n\n"
            "def main() -> int:\n"
            f"    command = TARGET_COMMAND or os.environ.get({json.dumps(bridge_env_name)}, '').strip()\n"
            "    if not command:\n"
            "        sys.stderr.write(f'host specialist bridge command unavailable for {HOST_ID}\\n')\n"
            "        return 3\n"
            "    return subprocess.run([command, *sys.argv[1:]], check=False).returncode\n\n"
            "if __name__ == '__main__':\n"
            "    raise SystemExit(main())\n"
        ),
        encoding="utf-8",
    )
    _ensure_executable(wrapper_py)
    record_specialist_wrapper(wrapper_py)

    platform_tag = detect_platform_tag()
    if platform_tag == "windows":
        launcher = tools_root / f"{host_id}-specialist-wrapper.cmd"
        launcher.write_text(
            (
                "@echo off\r\n"
                "setlocal\r\n"
                "set SCRIPT_DIR=%~dp0\r\n"
                "if exist \"%LocalAppData%\\Programs\\Python\\Python311\\python.exe\" (\r\n"
                "  set PY_CMD=%LocalAppData%\\Programs\\Python\\Python311\\python.exe\r\n"
                ") else if exist \"%ProgramFiles%\\Python311\\python.exe\" (\r\n"
                "  set PY_CMD=%ProgramFiles%\\Python311\\python.exe\r\n"
                ") else (\r\n"
                "  set PY_CMD=py -3\r\n"
                ")\r\n"
                "%PY_CMD% \"%SCRIPT_DIR%\\"
                + wrapper_py.name
                + "\" %*\r\n"
            ),
            encoding="utf-8",
        )
    else:
        launcher = tools_root / f"{host_id}-specialist-wrapper.sh"
        launcher.write_text(
            (
                "#!/usr/bin/env sh\n"
                "set -eu\n"
                "SCRIPT_DIR=$(CDPATH= cd -- \"$(dirname -- \"$0\")\" && pwd)\n"
                "if command -v python3 >/dev/null 2>&1; then\n"
                "  PYTHON_BIN=python3\n"
                "elif command -v python >/dev/null 2>&1; then\n"
                "  PYTHON_BIN=python\n"
                "else\n"
                "  echo 'python runtime unavailable for host specialist wrapper' >&2\n"
                "  exit 127\n"
                "fi\n"
                f"exec \"$PYTHON_BIN\" \"$SCRIPT_DIR/{wrapper_py.name}\" \"$@\"\n"
            ),
            encoding="utf-8",
        )
        _ensure_executable(launcher)
    record_specialist_wrapper(launcher)

    return {
        "platform": platform_tag,
        "launcher_path": str(launcher.resolve()),
        "script_path": str(wrapper_py.resolve()),
        "ready": bool(bridge_command),
        "bridge_command": bridge_command,
    }


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

    hooks_root = target_root / "hooks"
    hooks_root.mkdir(parents=True, exist_ok=True)
    track_created_path(hooks_root)
    hook_path = hooks_root / "write-guard.js"
    _copy_file(repo_root / "hooks" / "write-guard.js", hook_path, track_created_path=track_created_path)

    hook_command = f"node {hook_path.resolve()}"
    settings["vibeskills"] = {
        "managed": True,
        "host_id": "claude-code",
        "skills_root": str((target_root / "skills").resolve()),
        "runtime_skill_entry": str((target_root / "skills" / "vibe" / "SKILL.md").resolve()),
        "hooks_root": str(hooks_root.resolve()),
        "managed_hook_command": hook_command,
        "managed_hook_description": "VibeSkills managed write guard",
        "explicit_vibe_skill_invocation": ["/vibe", "$vibe"],
    }
    upsert_claude_pretooluse_hook(settings, hook_command)
    _write_json_file(settings_path, settings)
    if created_if_absent:
        track_created_path(settings_path)
    record_managed_json(settings_path)
    record_merged_file(settings_path, created_if_absent=created_if_absent)
    return [str(settings_path.resolve()), str(hook_path.resolve())]


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
    wrapper_info: dict[str, Any],
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
            "specialist_wrapper": {
                "launcher_path": wrapper_info["launcher_path"],
                "script_path": wrapper_info["script_path"],
                "ready": wrapper_info["ready"],
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
    target_root: Path,
    adapter: dict[str, Any],
    *,
    track_created_path: TrackCreatedPath,
    record_managed_json: RecordManagedJson,
    record_specialist_wrapper: RecordSpecialistWrapper,
) -> tuple[Path, dict[str, Any]]:
    host_id = adapter["id"]
    bridge_command, bridge_source = resolve_bridge_command(host_id)
    wrapper_info = materialize_host_specialist_wrapper(
        target_root,
        host_id,
        bridge_command,
        track_created_path=track_created_path,
        record_specialist_wrapper=record_specialist_wrapper,
    )
    settings_materialized = materialize_host_settings(
        target_root,
        adapter,
        wrapper_info,
        track_created_path=track_created_path,
        record_managed_json=record_managed_json,
    )
    commands_root = target_root / "commands"
    closure_state = "closed_ready" if wrapper_info["ready"] else "configured_offline_unready"
    closure = {
        "schema_version": 1,
        "host_id": host_id,
        "platform": detect_platform_tag(),
        "target_root": str(target_root.resolve()),
        "install_mode": adapter["install_mode"],
        "skills_root": str((target_root / "skills").resolve()),
        "runtime_skill_entry": str((target_root / "skills" / "vibe" / "SKILL.md").resolve()),
        "commands_root": str(commands_root.resolve()),
        "global_workflows_root": str((target_root / "global_workflows").resolve()),
        "mcp_config_path": str((target_root / "mcp_config.json").resolve()),
        "host_closure_state": closure_state,
        "commands_materialized": commands_root.exists(),
        "settings_materialized": settings_materialized,
        "specialist_wrapper": {
            "launcher_path": wrapper_info["launcher_path"],
            "script_path": wrapper_info["script_path"],
            "ready": wrapper_info["ready"],
            "bridge_command": bridge_command,
            "bridge_source": bridge_source,
        },
    }
    closure_path = target_root / ".vibeskills" / "host-closure.json"
    _write_json_file(closure_path, closure)
    track_created_path(closure_path)
    return closure_path, closure


def is_closed_ready_required(adapter: dict[str, Any]) -> bool:
    return (adapter.get("install_mode") or "").strip().lower() != "governed"
