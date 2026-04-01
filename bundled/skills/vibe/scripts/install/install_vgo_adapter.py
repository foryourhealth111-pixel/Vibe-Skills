#!/usr/bin/env python3
import argparse
import json
import os
import stat
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

COMMON_DIR = Path(__file__).resolve().parents[1] / "common"
if str(COMMON_DIR) not in sys.path:
    sys.path.insert(0, str(COMMON_DIR))

from runtime_contracts import (
    SKILL_ONLY_ACTIVATION_HOSTS,
    resolve_packaging_contract,
    uses_skill_only_activation,
)

REQUIRED_CORE = [
    "dialectic",
    "local-vco-roles",
    "spec-kit-vibe-compat",
    "superclaude-framework-compat",
    "ralph-loop",
    "cancel-ralph",
    "tdd-guide",
    "think-harder",
]
REQUIRED_WORKFLOW = [
    "brainstorming",
    "writing-plans",
    "subagent-driven-development",
    "systematic-debugging",
]
OPTIONAL_WORKFLOW = [
    "requesting-code-review",
    "receiving-code-review",
    "verification-before-completion",
]
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

ledger_state = {
    "created_paths": set(),
    "owned_tree_roots": set(),
    "managed_json_paths": set(),
    "merged_files": {},
    "template_generated": set(),
    "specialist_wrapper_paths": [],
}


def reset_ledger_state() -> None:
    for key, value in ledger_state.items():
        if isinstance(value, set):
            value.clear()
        elif isinstance(value, list):
            value.clear()
        else:
            ledger_state[key] = type(value)()


def track_created_path(path: Path | str) -> None:
    try:
        resolved = Path(path).resolve()
    except FileNotFoundError:
        resolved = Path(path)
    ledger_state["created_paths"].add(str(resolved))


def record_owned_tree_root(path: Path | str) -> None:
    try:
        resolved = Path(path).resolve()
    except FileNotFoundError:
        resolved = Path(path)
    ledger_state["owned_tree_roots"].add(str(resolved))


def record_managed_json(path: Path) -> None:
    try:
        resolved = path.resolve()
    except FileNotFoundError:
        resolved = path
    ledger_state["managed_json_paths"].add(str(resolved))


def record_merged_file(path: Path, *, created_if_absent: bool) -> None:
    try:
        resolved = path.resolve()
    except FileNotFoundError:
        resolved = path
    ledger_state["merged_files"][str(resolved)] = {
        "path": str(resolved),
        "created_if_absent": bool(created_if_absent),
    }


def record_generated_from_template(path: Path) -> None:
    try:
        resolved = path.resolve()
    except FileNotFoundError:
        resolved = path
    ledger_state["template_generated"].add(str(resolved))


def record_specialist_wrapper(path: Path) -> None:
    try:
        resolved = str(path.resolve())
    except FileNotFoundError:
        resolved = str(path)
    if resolved not in ledger_state["specialist_wrapper_paths"]:
        ledger_state["specialist_wrapper_paths"].append(resolved)

def detect_platform_tag() -> str:
    if os.name == "nt":
        return "windows"
    if sys_platform().startswith("darwin"):
        return "macos"
    return "linux"


def sys_platform() -> str:
    return os.sys.platform.lower()


def load_json(path: Path):
    with path.open("r", encoding="utf-8-sig") as fh:
        return json.load(fh)


def write_json(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def write_json_file(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
def is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def same_path(left: Path, right: Path) -> bool:
    return left.resolve() == right.resolve()


def copy_dir_replace(src: Path, dst: Path):
    if not src.exists():
        return
    if same_path(src, dst):
        return

    src_resolved = src.resolve()
    dst_resolved = dst.resolve(strict=False)
    requires_staging = is_relative_to(src_resolved, dst_resolved) or is_relative_to(dst_resolved, src_resolved)

    if not requires_staging:
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        track_created_path(dst)
        record_owned_tree_root(dst)
        return

    stage_root = Path(tempfile.mkdtemp(prefix="vgo-copy-tree-"))
    try:
        staged = stage_root / src.name
        shutil.copytree(src, staged)
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(staged, dst)
        track_created_path(dst)
        record_owned_tree_root(dst)
    finally:
        shutil.rmtree(stage_root, ignore_errors=True)


def copy_tree(src: Path, dst: Path):
    if not src.exists():
        return
    children = list(src.iterdir())
    dst.mkdir(parents=True, exist_ok=True)
    track_created_path(dst)
    for child in children:
        target = dst / child.name
        if child.is_dir():
            copy_dir_replace(child, target)
        else:
            if target.exists() and same_path(child, target):
                continue
            shutil.copy2(child, target)
            track_created_path(target)


def copy_skill_roots_without_self_shadow(src: Path, dst: Path, repo_root: Path):
    if not src.exists():
        return
    dst.mkdir(parents=True, exist_ok=True)
    track_created_path(dst)
    for child in sorted(src.iterdir(), key=lambda item: item.name):
        target = dst / child.name
        if same_path(target, repo_root):
            continue
        if child.is_dir():
            copy_dir_replace(child, target)
        else:
            copy_file(child, target)


def copy_file(src: Path, dst: Path):
    if src.exists() and dst.exists() and same_path(src, dst):
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    track_created_path(dst)


def ensure_executable(path: Path):
    current = path.stat().st_mode
    path.chmod(current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def restore_skill_entrypoint_if_needed(skill_root: Path):
    skill_md = skill_root / "SKILL.md"
    mirror_md = skill_root / "SKILL.runtime-mirror.md"
    if skill_md.exists() or not mirror_md.exists():
        return
    mirror_md.rename(skill_md)


def sanitize_skill_entrypoint_for_runtime_mirror(skill_root: Path):
    skill_md = skill_root / "SKILL.md"
    mirror_md = skill_root / "SKILL.runtime-mirror.md"
    if mirror_md.exists():
        if skill_md.exists():
            skill_md.unlink()
        return
    if skill_md.exists():
        skill_md.rename(mirror_md)


def parent_dir(path: Path | None) -> Path | None:
    if path is None:
        return None
    resolved = path.resolve()
    parent = resolved.parent
    if parent == resolved or parent == Path(parent.anchor):
        return None
    return parent


def skill_source_roots(repo_root: Path) -> list[Path]:
    canonical_skills_root = parent_dir(repo_root)
    workspace_root = parent_dir(canonical_skills_root)
    candidates = [
        canonical_skills_root,
        workspace_root / "skills" if workspace_root is not None else None,
        workspace_root / "superpowers" / "skills" if workspace_root is not None else None,
        repo_root / "bundled" / "superpowers-skills",
    ]
    roots: list[Path] = []
    for candidate in candidates:
        if candidate is None or not candidate.exists():
            continue
        if candidate not in roots:
            roots.append(candidate)
    return roots


def embedded_registry():
    return {
        "schema_version": 1,
        "default_adapter_id": "codex",
        "aliases": {"claude": "claude-code"},
        "adapters": [
            {
                "id": "codex",
                "status": "supported-with-constraints",
                "install_mode": "governed",
                "check_mode": "governed",
                "bootstrap_mode": "governed",
                "default_target_root": {"env": "CODEX_HOME", "rel": ".codex", "kind": "host-home"},
                "host_profile": "adapters/codex/host-profile.json",
                "settings_map": "adapters/codex/settings-map.json",
                "closure": "adapters/codex/closure.json",
                "manifest": "dist/host-codex/manifest.json",
            },
            {
                "id": "claude-code",
                "status": "supported-with-constraints",
                "install_mode": "preview-guidance",
                "check_mode": "preview-guidance",
                "bootstrap_mode": "preview-guidance",
                "default_target_root": {"env": "CLAUDE_HOME", "rel": ".claude", "kind": "host-home"},
                "host_profile": "adapters/claude-code/host-profile.json",
                "settings_map": "adapters/claude-code/settings-map.json",
                "closure": "adapters/claude-code/closure.json",
                "manifest": "dist/host-claude-code/manifest.json",
            },
            {
                "id": "cursor",
                "status": "preview",
                "install_mode": "preview-guidance",
                "check_mode": "preview-guidance",
                "bootstrap_mode": "preview-guidance",
                "default_target_root": {"env": "CURSOR_HOME", "rel": ".cursor", "kind": "host-home"},
                "host_profile": "adapters/cursor/host-profile.json",
                "settings_map": "adapters/cursor/settings-map.json",
                "closure": "adapters/cursor/closure.json",
                "manifest": "dist/host-cursor/manifest.json",
            },
            {
                "id": "windsurf",
                "status": "preview",
                "install_mode": "runtime-core",
                "check_mode": "runtime-core",
                "bootstrap_mode": "runtime-core",
                "default_target_root": {"env": "WINDSURF_HOME", "rel": ".codeium/windsurf", "kind": "host-home"},
                "host_profile": "adapters/windsurf/host-profile.json",
                "settings_map": "adapters/windsurf/settings-map.json",
                "closure": "adapters/windsurf/closure.json",
                "manifest": "dist/host-windsurf/manifest.json",
            },
            {
                "id": "openclaw",
                "status": "preview",
                "install_mode": "runtime-core",
                "check_mode": "runtime-core",
                "bootstrap_mode": "runtime-core",
                "default_target_root": {"env": "OPENCLAW_HOME", "rel": ".openclaw", "kind": "host-home"},
                "host_profile": "adapters/openclaw/host-profile.json",
                "settings_map": "adapters/openclaw/settings-map.json",
                "closure": "adapters/openclaw/closure.json",
                "manifest": "dist/host-openclaw/manifest.json",
            },
        ],
    }


def resolve_registry(repo_root: Path):
    current = repo_root.resolve()
    while True:
        registry_path = current / "adapters" / "index.json"
        if registry_path.exists():
            return load_json(registry_path)
        if current.parent == current:
            break
        current = current.parent

    if (repo_root / "config" / "version-governance.json").exists():
        return embedded_registry()

    raise SystemExit(f"VGO adapter registry not found under repo root or ancestors: {repo_root}")


def resolve_adapter(repo_root: Path, host_id: str):
    registry = resolve_registry(repo_root)
    normalized = (host_id or registry.get("default_adapter_id") or "codex").strip().lower()
    normalized = registry.get("aliases", {}).get(normalized, normalized)
    for entry in registry.get("adapters", []):
        if entry.get("id") == normalized:
            return entry
    raise SystemExit(f"Unsupported VGO host id: {host_id}")


def resolve_target_root_for_adapter(adapter: dict, explicit_target_root: Path | None = None) -> Path:
    if explicit_target_root is not None:
        return explicit_target_root.resolve()

    target_spec = adapter.get("default_target_root") or {}
    env_name = target_spec.get("env") or ""
    rel = target_spec.get("rel") or ""
    env_value = os.environ.get(env_name, "").strip() if env_name else ""
    if env_value:
        return Path(env_value).expanduser().resolve()
    if not rel:
        raise SystemExit(f"Adapter '{adapter.get('id')}' does not define default_target_root.rel")
    rel_path = Path(rel)
    if rel_path.is_absolute():
        return rel_path.resolve()
    return (Path.home() / rel_path).expanduser().resolve()


def load_specialist_policy(repo_root: Path):
    return load_json(repo_root / "config" / "native-specialist-execution-policy.json")


def resolve_specialist_policy_entry(repo_root: Path, host_id: str):
    policy = load_specialist_policy(repo_root)
    for entry in policy.get("adapters", []):
        if entry.get("id") == host_id:
            return entry
    return None


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


def materialize_host_specialist_wrapper(target_root: Path, host_id: str, bridge_command: str | None):
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
    ensure_executable(wrapper_py)
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
                "%PY_CMD% \"%SCRIPT_DIR%\\" + wrapper_py.name + "\" %*\r\n"
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
        ensure_executable(launcher)
    record_specialist_wrapper(launcher)

    return {
        "platform": platform_tag,
        "launcher_path": str(launcher.resolve()),
        "script_path": str(wrapper_py.resolve()),
        "ready": bool(bridge_command),
        "bridge_command": bridge_command,
    }


def merge_json_object(path: Path, patch: dict):
    existing = {}
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}
    merged = dict(existing)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(existing.get(key), dict):
            next_value = dict(existing[key])
            next_value.update(value)
            merged[key] = next_value
        else:
            merged[key] = value
    write_json_file(path, merged)


def load_json_object(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Failed to parse JSON settings file: {path} ({exc})") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"Expected JSON object in settings file: {path}")
    return payload


def should_replace_claude_pretooluse_hook_entry(
    entry: dict,
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


def upsert_claude_pretooluse_hook(settings: dict, hook_command: str) -> None:
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


def install_claude_managed_settings(repo_root: Path, target_root: Path) -> list[str]:
    settings_path = target_root / "settings.json"
    created_if_absent = not settings_path.exists()
    settings = load_json_object(settings_path)

    hooks_root = target_root / "hooks"
    hooks_root.mkdir(parents=True, exist_ok=True)
    track_created_path(hooks_root)
    hook_path = hooks_root / "write-guard.js"
    copy_file(repo_root / "hooks" / "write-guard.js", hook_path)

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
    write_json_file(settings_path, settings)
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
        write_json_file(settings_path, next_payload)
        receipt["status"] = "removed-owned-node"
        receipt["preserved_keys"] = sorted(next_payload.keys())
    else:
        settings_path.unlink()
        receipt["status"] = "removed-owned-node-and-deleted-empty-file"
    return receipt


def materialize_host_settings(target_root: Path, adapter: dict, wrapper_info: dict):
    host_id = adapter["id"]
    materialized = []
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
        write_json_file(settings_path, host_settings)
        materialized.append(str(settings_path.resolve()))
        record_managed_json(settings_path)
        track_created_path(settings_path)
    return materialized


def materialize_host_closure(repo_root: Path, target_root: Path, adapter: dict):
    host_id = adapter["id"]
    bridge_command, bridge_source = resolve_bridge_command(host_id)
    wrapper_info = materialize_host_specialist_wrapper(target_root, host_id, bridge_command)
    settings_materialized = materialize_host_settings(target_root, adapter, wrapper_info)
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
    write_json_file(closure_path, closure)
    track_created_path(closure_path)
    return closure_path, closure


def is_closed_ready_required(adapter: dict) -> bool:
    return (adapter.get("install_mode") or "").strip().lower() != "governed"


def sync_vibe_canonical(repo_root: Path, target_root: Path, target_rel: str):
    governance = load_json(repo_root / "config" / "version-governance.json")
    packaging = resolve_packaging_contract(governance, repo_root)
    canonical_root = (repo_root / governance["source_of_truth"]["canonical_root"]).resolve()
    target_vibe_root = target_root / target_rel
    if same_path(canonical_root, target_vibe_root):
        return
    if target_vibe_root.exists():
        shutil.rmtree(target_vibe_root)
    for rel in packaging["mirror"]["files"]:
        src = canonical_root / rel
        if src.exists():
            copy_file(src, target_vibe_root / rel)
    for rel in packaging["mirror"]["directories"]:
        src = canonical_root / rel
        dst = target_vibe_root / rel
        if src.exists():
            copy_dir_replace(src, dst)

def generated_nested_compatibility_suffix(governance: dict) -> Path | None:
    topology = governance.get("mirror_topology") or {}
    targets = topology.get("targets") or []
    bundled_path = None
    nested_path = None
    nested_materialization_mode = None

    for target in targets:
        target_id = str(target.get("id") or "").strip().lower()
        if target_id == "bundled":
            bundled_path = str(target.get("path") or "").strip()
        elif target_id == "nested_bundled":
            nested_path = str(target.get("path") or "").strip()
            nested_materialization_mode = str(target.get("materialization_mode") or "").strip()

    source = governance.get("source_of_truth") or {}
    if not bundled_path:
        bundled_path = str(source.get("bundled_root") or "bundled/skills/vibe").strip()
    if not nested_path:
        nested_path = str(source.get("nested_bundled_root") or "").strip()
    if not nested_path:
        nested_path = f"{bundled_path}/{bundled_path}"
    if not nested_materialization_mode:
        nested_materialization_mode = "release_install_only"
    if nested_materialization_mode != "release_install_only":
        return None

    bundled_norm = bundled_path.replace("\\", "/").strip("/")
    nested_norm = nested_path.replace("\\", "/").strip("/")
    prefix = f"{bundled_norm}/"
    if not nested_norm.startswith(prefix):
        return None

    suffix = nested_norm[len(prefix) :].strip("/")
    if not suffix:
        return None

    return Path(*suffix.split("/"))


def materialize_generated_nested_compatibility(
    governance: dict,
    installed_root: Path,
    managed_skill_names: set[str] | None = None,
):
    suffix = generated_nested_compatibility_suffix(governance)
    if suffix is None:
        return

    nested_root = installed_root / suffix
    if same_path(installed_root, nested_root):
        return

    nested_skills_root = nested_root.parent
    source_skills_root = installed_root.parent

    if nested_skills_root.exists():
        shutil.rmtree(nested_skills_root)

    for skill_dir in sorted(source_skills_root.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name == installed_root.name:
            continue
        if managed_skill_names is not None and skill_dir.name not in managed_skill_names:
            continue
        destination = nested_skills_root / skill_dir.name
        copy_dir_replace(skill_dir, destination)
        sanitize_skill_entrypoint_for_runtime_mirror(destination)

    packaging = resolve_packaging_contract(governance, installed_root)
    for rel in packaging["mirror"]["files"]:
        src = installed_root / rel
        if src.exists():
            copy_file(src, nested_root / rel)
    for rel in packaging["mirror"]["directories"]:
        src = installed_root / rel
        if src.exists():
            copy_dir_replace(src, nested_root / rel)
    sanitize_skill_entrypoint_for_runtime_mirror(nested_root)


def canonical_vibe_target_relpath(packaging: dict) -> str:
    return str(packaging.get("canonical_vibe_mirror", {}).get("target_relpath") or "skills/vibe")


def load_runtime_core_packaging(repo_root: Path, profile: str) -> dict:
    packaging_path = repo_root / "config" / "runtime-core-packaging.json"
    packaging = load_json(packaging_path)
    manifest_map = packaging.get("profile_manifests") or {}
    manifest_rel = manifest_map.get(profile)
    if manifest_rel:
        manifest_path = repo_root / manifest_rel
        if not manifest_path.exists():
            raise SystemExit(f"Runtime-core packaging manifest missing for profile '{profile}': {manifest_path}")
        packaging = load_json(manifest_path)

    packaging.setdefault("profile", profile)
    packaging.setdefault("bundled_skills_source", "bundled/skills")
    packaging.setdefault("skills_allowlist", [])
    packaging.setdefault(
        "copy_bundled_skills",
        any(entry.get("target") == "skills" for entry in packaging.get("copy_directories") or []),
    )
    return packaging


def resolve_bundled_skills_root(repo_root: Path, packaging: dict) -> Path:
    source_rel = str(packaging.get("bundled_skills_source") or "bundled/skills")
    candidates: list[Path] = []

    parent = repo_root.parent
    if parent.name == "skills":
        candidates.append(parent)
    candidates.append(repo_root / source_rel)

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return repo_root / source_rel


def load_existing_install_ledger(target_root: Path) -> dict | None:
    ledger_path = target_root / ".vibeskills" / "install-ledger.json"
    if not ledger_path.exists():
        return None
    return load_json(ledger_path)


def derive_managed_skill_names_from_ledger(target_root: Path, ledger: dict | None) -> set[str]:
    if not isinstance(ledger, dict):
        return set()

    managed = {
        str(name).strip()
        for name in ledger.get("managed_skill_names") or []
        if str(name).strip()
    }

    skills_root = (target_root / "skills").resolve()
    for raw_path in ledger.get("created_paths") or []:
        candidate = Path(str(raw_path)).resolve(strict=False)
        try:
            relative = candidate.relative_to(skills_root)
        except ValueError:
            continue
        if relative.parts:
            managed.add(relative.parts[0])

    canonical_vibe_root = str(ledger.get("canonical_vibe_root") or "").strip()
    if canonical_vibe_root:
        managed.add(Path(canonical_vibe_root).name)

    return managed


def desired_managed_skill_names(repo_root: Path, packaging: dict, profile: str) -> set[str]:
    managed = {
        str(name).strip()
        for name in packaging.get("skills_allowlist") or []
        if str(name).strip()
    }

    bundled_root = resolve_bundled_skills_root(repo_root, packaging)
    if bool(packaging.get("copy_bundled_skills")) and bundled_root.exists():
        managed.update(
            candidate.name
            for candidate in bundled_root.iterdir()
            if candidate.is_dir()
        )

    managed.add(Path(canonical_vibe_target_relpath(packaging)).name)
    managed.update(REQUIRED_CORE)
    managed.update(REQUIRED_WORKFLOW)
    if profile == "full":
        managed.update(OPTIONAL_WORKFLOW)
    return managed


def prune_previously_managed_skill_dirs(
    target_root: Path,
    previous_managed_skill_names: set[str],
    current_managed_skill_names: set[str],
) -> None:
    skills_root = target_root / "skills"
    if not skills_root.exists():
        return

    for name in sorted(previous_managed_skill_names - current_managed_skill_names):
        skill_root = skills_root / name
        if skill_root.is_dir():
            shutil.rmtree(skill_root)


def materialize_allowlisted_skills(repo_root: Path, target_root: Path, packaging: dict) -> None:
    skills_allowlist = list(packaging.get("skills_allowlist") or [])
    if not skills_allowlist:
        return

    bundled_root = resolve_bundled_skills_root(repo_root, packaging)
    if not bundled_root.exists():
        raise SystemExit(f"Bundled skills source missing for allowlisted packaging: {bundled_root}")

    canonical_vibe_rel = str(packaging.get("canonical_vibe_mirror", {}).get("target_relpath") or "skills/vibe")
    canonical_vibe_name = Path(canonical_vibe_rel).name
    for name in sorted({str(value).strip() for value in skills_allowlist if str(value).strip()}):
        if name == canonical_vibe_name:
            continue
        source = bundled_root / name
        if not source.exists():
            raise SystemExit(f"Allowlisted skill packaging source missing: {source}")
        destination = target_root / "skills" / name
        copy_dir_replace(source, destination)
        restore_skill_entrypoint_if_needed(destination)


def build_payload_summary(target_root: Path, ledger: dict) -> dict:
    target_root_resolved = target_root.resolve()
    skills_root = (target_root / "skills").resolve(strict=False)
    managed_skill_names = derive_managed_skill_names_from_ledger(target_root, ledger)
    installed_skill_names = sorted(
        name
        for name in managed_skill_names
        if not name.startswith(".") and (target_root / "skills" / name).is_dir()
    )

    managed_skill_roots = {
        (target_root / "skills" / name).resolve(strict=False)
        for name in managed_skill_names
        if (target_root / "skills" / name).exists()
    }

    owned_files: set[str] = set()

    def is_under_target_root(candidate: Path) -> bool:
        try:
            candidate.relative_to(target_root_resolved)
        except ValueError:
            return False
        return True

    def collect_owned_tree(path_value: str | Path) -> None:
        candidate = Path(path_value).resolve(strict=False)
        if not is_under_target_root(candidate) or not candidate.is_dir():
            return

        for file_path in candidate.rglob("*"):
            if file_path.is_file():
                owned_files.add(str(file_path.resolve(strict=False)))

    def collect_owned_file(path_value: str | Path) -> None:
        candidate = Path(path_value).resolve(strict=False)
        if not is_under_target_root(candidate) or not candidate.is_file():
            return

        owned_files.add(str(candidate))

    for skill_root in managed_skill_roots:
        collect_owned_tree(skill_root)

    for raw_path in ledger.get("owned_tree_roots") or []:
        candidate = Path(str(raw_path)).resolve(strict=False)
        if candidate == target_root_resolved or candidate == skills_root:
            continue
        if candidate.parent == skills_root and candidate.name not in managed_skill_names:
            continue
        collect_owned_tree(candidate)

    for raw_path in ledger.get("created_paths") or []:
        collect_owned_file(raw_path)
    for raw_path in ledger.get("managed_json_paths") or []:
        collect_owned_file(raw_path)
    for raw_path in ledger.get("generated_from_template_if_absent") or []:
        collect_owned_file(raw_path)
    for raw_path in ledger.get("specialist_wrapper_paths") or []:
        collect_owned_file(raw_path)
    for entry in ledger.get("merged_files") or []:
        if isinstance(entry, dict):
            collect_owned_file(str(entry.get("path") or ""))

    installed_file_count = len(owned_files)
    return {
        "installed_skill_count": len(installed_skill_names),
        "installed_skill_names": installed_skill_names,
        "installed_file_count": installed_file_count,
    }


def write_install_ledger(
    repo_root: Path,
    target_root: Path,
    adapter: dict,
    mode: str,
    profile: str,
    canonical_vibe_rel: str,
    external_fallback_used: list[str],
    packaging: dict,
    managed_skill_names: list[str],
):
    ledger_path = target_root / ".vibeskills" / "install-ledger.json"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    track_created_path(ledger_path)
    ledger = {
        "schema_version": 1,
        "host_id": adapter["id"],
        "install_mode": mode,
        "profile": profile,
        "target_root": str(target_root.resolve()),
        "runtime_root": str(target_root.resolve()),
        "canonical_vibe_root": str((target_root / canonical_vibe_rel).resolve()),
        "created_paths": sorted(ledger_state["created_paths"]),
        "owned_tree_roots": sorted(ledger_state["owned_tree_roots"]),
        "managed_json_paths": sorted(ledger_state["managed_json_paths"]),
        "merged_files": [
            ledger_state["merged_files"][path]
            for path in sorted(ledger_state["merged_files"])
        ],
        "generated_from_template_if_absent": sorted(ledger_state["template_generated"]),
        "specialist_wrapper_paths": ledger_state["specialist_wrapper_paths"],
        "external_fallback_used": external_fallback_used,
        "managed_skill_names": managed_skill_names,
        "packaging_manifest": {
            "profile": packaging.get("profile", profile),
            "package_id": packaging.get("package_id"),
            "copy_bundled_skills": bool(packaging.get("copy_bundled_skills")),
        },
        "timestamp": datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ownership_source": "install-ledger",
    }
    ledger["payload_summary"] = build_payload_summary(target_root, ledger)
    write_json_file(ledger_path, ledger)


def refresh_install_ledger(target_root: Path) -> dict:
    ledger_path = target_root / ".vibeskills" / "install-ledger.json"
    if not ledger_path.exists():
        raise SystemExit(f"Install ledger missing for refresh: {ledger_path}")

    ledger = load_json(ledger_path)
    ledger["payload_summary"] = build_payload_summary(target_root, ledger)
    write_json_file(ledger_path, ledger)
    return {
        "ledger_path": str(ledger_path.resolve()),
        "payload_summary": ledger["payload_summary"],
    }


def ensure_skill_present(target_root: Path, name: str, required: bool, allow_fallback: bool, fallback_sources, external_used, missing):
    skill_md = target_root / "skills" / name / "SKILL.md"
    if skill_md.exists():
        return
    if allow_fallback:
        for src in fallback_sources:
            src_path = Path(src)
            if src_path.exists():
                destination = target_root / "skills" / name
                copy_tree(src_path, destination)
                restore_skill_entrypoint_if_needed(destination)
                external_used.add(name)
                break
    if required and not skill_md.exists():
        missing.add(name)


def install_runtime_core(repo_root: Path, target_root: Path, profile: str, allow_fallback: bool, adapter: dict):
    packaging = load_runtime_core_packaging(repo_root, profile)
    governance = load_json(repo_root / "config" / "version-governance.json")
    previous_ledger = load_existing_install_ledger(target_root)
    current_managed_skill_names = desired_managed_skill_names(repo_root, packaging, profile)
    include_command_surfaces = not uses_skill_only_activation(adapter["id"])
    runtime_directories = [
        rel for rel in packaging["directories"]
        if include_command_surfaces or rel != "commands"
    ]
    for rel in runtime_directories:
        (target_root / rel).mkdir(parents=True, exist_ok=True)
        track_created_path(target_root / rel)
    copy_directories = [
        entry for entry in packaging["copy_directories"]
        if include_command_surfaces or entry["target"] != "commands"
    ]
    for entry in copy_directories:
        src_root = repo_root / entry["source"]
        if entry["target"] == "skills" and entry["source"] == str(packaging.get("bundled_skills_source") or "bundled/skills"):
            src_root = resolve_bundled_skills_root(repo_root, packaging)
        dst_root = target_root / entry["target"]
        if entry["target"] == "skills":
            copy_skill_roots_without_self_shadow(src_root, dst_root, repo_root)
        else:
            copy_tree(src_root, dst_root)
        if entry["target"] == "skills":
            for skill_dir in (target_root / "skills").iterdir():
                if skill_dir.is_dir():
                    restore_skill_entrypoint_if_needed(skill_dir)
    for entry in packaging["copy_files"]:
        src = repo_root / entry["source"]
        if not src.exists():
            if entry.get("optional"):
                continue
            raise SystemExit(f"Runtime-core packaging source missing: {src}")
        copy_file(src, target_root / entry["target"])

    target_rel = canonical_vibe_target_relpath(packaging)
    sync_vibe_canonical(repo_root, target_root, target_rel)
    prune_previously_managed_skill_dirs(
        target_root,
        derive_managed_skill_names_from_ledger(target_root, previous_ledger),
        current_managed_skill_names,
    )
    materialize_allowlisted_skills(repo_root, target_root, packaging)
    materialize_generated_nested_compatibility(
        governance,
        target_root / target_rel,
        current_managed_skill_names,
    )

    roots = skill_source_roots(repo_root)

    external_used = set()
    missing = set()

    for name in REQUIRED_CORE:
        ensure_skill_present(
            target_root,
            name,
            True,
            allow_fallback,
            [
                root / name for root in roots
            ],
            external_used,
            missing,
        )
    for name in REQUIRED_WORKFLOW:
        ensure_skill_present(
            target_root,
            name,
            True,
            allow_fallback,
            [
                root / name for root in roots[1:] + roots[:1]
            ],
            external_used,
            missing,
        )
    if profile == "full":
        for name in OPTIONAL_WORKFLOW:
            ensure_skill_present(
                target_root,
                name,
                False,
                allow_fallback,
                [
                    root / name for root in roots[1:] + roots[:1]
                ],
                external_used,
                missing,
            )

    if missing:
        raise SystemExit("Missing required vendored skills: " + ", ".join(sorted(missing)))

    managed_skill_names = sorted(
        name
        for name in current_managed_skill_names
        if (target_root / "skills" / name).is_dir()
    )

    return packaging, sorted(external_used), managed_skill_names


def install_codex_payload(repo_root: Path, target_root: Path):
    copy_tree(repo_root / "rules", target_root / "rules")
    track_created_path(target_root / "rules")
    copy_tree(repo_root / "agents" / "templates", target_root / "agents" / "templates")
    track_created_path(target_root / "agents" / "templates")
    copy_tree(repo_root / "mcp", target_root / "mcp")
    track_created_path(target_root / "mcp")
    (target_root / "config").mkdir(parents=True, exist_ok=True)
    track_created_path(target_root / "config")
    copy_file(repo_root / "config" / "plugins-manifest.codex.json", target_root / "config" / "plugins-manifest.codex.json")
    settings_path = target_root / "settings.json"
    if not settings_path.exists():
        copy_file(repo_root / "config" / "settings.template.codex.json", settings_path)
        record_generated_from_template(settings_path)
    track_created_path(settings_path)
    record_managed_json(settings_path)


def install_claude_guidance_payload(repo_root: Path, target_root: Path):
    install_claude_managed_settings(repo_root, target_root)
    return


def install_opencode_guidance_payload(repo_root: Path, target_root: Path):
    example_config = repo_root / "config" / "opencode" / "opencode.json.example"
    if example_config.exists():
        copy_file(example_config, target_root / "opencode.json.example")

def install_runtime_core_mode_payload(repo_root: Path, target_root: Path, adapter: dict):
    if uses_skill_only_activation(adapter["id"]):
        return
    commands_root = repo_root / "commands"
    if commands_root.exists():
        copy_tree(commands_root, target_root / "global_workflows")
        track_created_path(target_root / "global_workflows")

    mcp_template = repo_root / "mcp" / "servers.template.json"
    mcp_config = target_root / "mcp_config.json"
    if mcp_template.exists() and not mcp_config.exists():
        copy_file(mcp_template, mcp_config)
        record_generated_from_template(mcp_config)
    track_created_path(mcp_config)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root")
    parser.add_argument("--target-root")
    parser.add_argument("--host")
    parser.add_argument("--profile", choices=("minimal", "full"), default="full")
    parser.add_argument("--allow-external-skill-fallback", action="store_true")
    parser.add_argument("--require-closed-ready", action="store_true")
    parser.add_argument("--refresh-install-ledger", action="store_true")
    args = parser.parse_args()

    if args.refresh_install_ledger:
        if not args.target_root:
            parser.error("--target-root is required with --refresh-install-ledger")
        write_json(refresh_install_ledger(Path(args.target_root).resolve()))
        return

    missing_required = [
        name
        for name in ("repo_root", "target_root", "host")
        if not getattr(args, name)
    ]
    if missing_required:
        parser.error(
            "missing required arguments for install mode: "
            + ", ".join(f"--{name.replace('_', '-')}" for name in missing_required)
        )

    reset_ledger_state()

    repo_root = Path(args.repo_root).resolve()
    target_root = Path(args.target_root).resolve()
    target_root.mkdir(parents=True, exist_ok=True)
    track_created_path(target_root)
    adapter = resolve_adapter(repo_root, args.host)
    packaging, external_used, managed_skill_names = install_runtime_core(
        repo_root, target_root, args.profile, args.allow_external_skill_fallback, adapter
    )
    mode = adapter["install_mode"]
    legacy_opencode_config_cleanup = None
    if mode == "governed":
        install_codex_payload(repo_root, target_root)
    elif mode == "preview-guidance":
        if adapter["id"] == "opencode":
            install_opencode_guidance_payload(repo_root, target_root)
        elif adapter["id"] == "claude-code":
            install_claude_guidance_payload(repo_root, target_root)
        elif adapter["id"] == "cursor":
            pass
        else:
            raise SystemExit(f"Unsupported preview-guidance adapter id: {adapter['id']}")
    elif mode == "runtime-core":
        install_runtime_core_mode_payload(repo_root, target_root, adapter)
    else:
        raise SystemExit(f"Unsupported adapter install mode: {mode}")

    closure_path, closure = materialize_host_closure(repo_root, target_root, adapter)
    require_closed_ready_effective = bool(args.require_closed_ready and is_closed_ready_required(adapter))
    if require_closed_ready_effective and closure["host_closure_state"] != "closed_ready":
        raise SystemExit(
            "Host closure for "
            f"'{adapter['id']}' is not closed_ready "
            f"(got '{closure['host_closure_state']}'). "
            "Configure the host specialist bridge command first, then retry install."
        )

    canonical_vibe_rel = canonical_vibe_target_relpath(packaging)
    write_install_ledger(
        repo_root,
        target_root,
        adapter,
        mode,
        args.profile,
        canonical_vibe_rel,
        external_used,
        packaging,
        managed_skill_names,
    )

    write_json(
        {
            "host_id": adapter["id"],
            "install_mode": mode,
            "target_root": str(target_root),
            "external_fallback_used": external_used,
            "host_closure_path": str(closure_path),
            "host_closure_state": closure["host_closure_state"],
            "settings_materialized": closure["settings_materialized"],
            "legacy_opencode_config_cleanup": legacy_opencode_config_cleanup,
            "specialist_wrapper_ready": bool(closure["specialist_wrapper"]["ready"]),
            "require_closed_ready_requested": bool(args.require_closed_ready),
            "require_closed_ready_effective": require_closed_ready_effective,
        }
    )


if __name__ == "__main__":
    main()
