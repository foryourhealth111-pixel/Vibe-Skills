from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path
from typing import Any

from ._io import load_json, utc_now, write_text
from ._repo import resolve_repo_root


END_MANAGED_BLOCK = "<!-- VIBESKILLS:END managed-block -->"
BEGIN_MANAGED_BLOCK = re.compile(
    r"^<!-- VIBESKILLS:BEGIN managed-block host=(?P<host>\S+) block=(?P<block>\S+) version=(?P<version>\d+) hash=(?P<hash>[a-f0-9]+) -->$",
    re.MULTILINE,
)
END_MANAGED_BLOCK_PATTERN = re.compile(r"^<!-- VIBESKILLS:END managed-block -->$", re.MULTILINE)
HOST_GLOBAL_INSTRUCTION_TARGETS = {
    "codex": {"relpath": "AGENTS.md", "documented_path": "~/.codex/AGENTS.md"},
    "claude-code": {"relpath": "CLAUDE.md", "documented_path": "~/.claude/CLAUDE.md"},
    "opencode": {"relpath": "AGENTS.md", "documented_path": "~/.config/opencode/AGENTS.md"},
}
IS_WINDOWS = os.name == "nt"
WINDOWS_NPX_COMMANDS = {"npx", "npx.cmd", "npx.exe", "npx.ps1"}
WINDOWS_CMD_COMMANDS = {"cmd", "cmd.exe"}
CLAUDE_FLOW_COMMANDS = {"claude-flow", "claude-flow.cmd", "claude-flow.exe", "claude-flow.ps1"}


def setting_value(settings: dict[str, Any] | None, name: str) -> str | None:
    if not isinstance(settings, dict):
        return None
    env = settings.get("env")
    if not isinstance(env, dict):
        return None
    value = env.get(name)
    if value is None:
        return None
    return str(value)


def placeholder_value(value: str | None) -> bool:
    if not value:
        return False
    trimmed = value.strip()
    return trimmed.startswith("<") and trimmed.endswith(">")


def setting_state(settings: dict[str, Any] | None, name: str) -> str:
    value = setting_value(settings, name)
    if value is None or not value.strip():
        return "missing"
    if placeholder_value(value):
        return "placeholder"
    return "configured"


def os_environ(name: str) -> str | None:
    value = os.environ.get(name)
    if value is None or not str(value).strip():
        return None
    return str(value)


def resolved_setting_state(settings: dict[str, Any] | None, name: str) -> tuple[str, str]:
    env_value = os_environ(name)
    if env_value:
        if placeholder_value(env_value):
            return "placeholder", "env"
        return "configured", "env"

    setting_value_text = setting_value(settings, name)
    if setting_value_text is None or not setting_value_text.strip():
        return "missing", "missing"
    if placeholder_value(setting_value_text):
        return "placeholder", "settings"
    return "configured", "settings"


def command_present(name: str) -> bool:
    return shutil.which(name) is not None


def _command_basename(command: str | None) -> str:
    if command is None:
        return ""
    value = str(command).strip().strip('"').strip("'")
    if not value:
        return ""
    return Path(value).name.lower()


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _is_windows_cmd_wrapped_npx(command: str | None, args: list[str]) -> bool:
    if _command_basename(command) not in WINDOWS_CMD_COMMANDS:
        return False
    if len(args) < 2:
        return False
    return str(args[0]).lower() == "/c" and _command_basename(args[1]) in WINDOWS_NPX_COMMANDS


def _looks_like_bare_windows_npx(command: str | None, args: list[str]) -> bool:
    return IS_WINDOWS and _command_basename(command) in WINDOWS_NPX_COMMANDS and not _is_windows_cmd_wrapped_npx(command, args)


def _looks_like_claude_flow_mcp_server(command: str | None, args: list[str]) -> bool:
    if _command_basename(command) not in CLAUDE_FLOW_COMMANDS:
        return False
    return len(args) >= 2 and args[0] == "mcp" and args[1] == "start"


def _resolve_claude_flow_package_root(command: str | None) -> Path | None:
    candidates: list[Path] = []
    command_text = str(command or "").strip().strip('"').strip("'")
    if command_text:
        command_path = Path(command_text)
        if command_path.is_absolute() or command_path.drive:
            candidates.append(command_path.resolve(strict=False).parent / "node_modules" / "claude-flow")
    resolved = shutil.which("claude-flow")
    if resolved:
        candidates.append(Path(resolved).resolve(strict=False).parent / "node_modules" / "claude-flow")
    appdata = os.environ.get("APPDATA")
    if appdata:
        candidates.append(Path(appdata) / "npm" / "node_modules" / "claude-flow")
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate.exists():
            return candidate
    return None


def _inspect_claude_flow_package(command: str | None) -> dict[str, Any]:
    package_root = _resolve_claude_flow_package_root(command)
    if package_root is None:
        return {
            "package_root": None,
            "package_version": None,
            "hooks_schema_issue_detected": False,
            "hooks_schema_issue": None,
        }

    package_version = None
    package_json_path = package_root / "package.json"
    if package_json_path.exists():
        try:
            package_payload = json.loads(package_json_path.read_text(encoding="utf-8"))
        except Exception:
            package_payload = None
        if isinstance(package_payload, dict):
            version_value = package_payload.get("version")
            if version_value is not None:
                package_version = str(version_value)

    hooks_tools_path = package_root / "v3" / "@claude-flow" / "cli" / "dist" / "src" / "mcp-tools" / "hooks-tools.js"
    hooks_schema_issue_detected = False
    hooks_schema_issue = None
    if hooks_tools_path.exists():
        hooks_text = hooks_tools_path.read_text(encoding="utf-8", errors="ignore")
        if re.search(
            r"trajectoryIds:\s*\{(?P<body>[^{}]*type:\s*['\"]array['\"][^{}]*)\}",
            hooks_text,
        ) and "items" not in hooks_text.split("trajectoryIds:", 1)[1].split("}", 1)[0]:
            hooks_schema_issue_detected = True
        if hooks_schema_issue_detected:
            hooks_schema_issue = "hooks_intelligence_learn.trajectoryIds array schema missing items"

    return {
        "package_root": str(package_root.resolve(strict=False)),
        "package_version": package_version,
        "hooks_schema_issue_detected": hooks_schema_issue_detected,
        "hooks_schema_issue": hooks_schema_issue,
    }


def inspect_claude_code_global_mcp_config(target_root: Path) -> dict[str, Any]:
    global_config_path = Path.home() / ".claude.json"
    result: dict[str, Any] = {
        "applicable": True,
        "config_path": str(global_config_path.resolve(strict=False)),
        "exists": global_config_path.exists(),
        "parseable": False,
        "status": "not_present",
        "windows_bare_npx_servers": [],
        "claude_flow_mcp_servers": [],
        "duplicate_claude_flow_aliases": [],
        "claude_flow_schema_issue": {
            "detected": False,
            "detail": None,
            "package_version": None,
            "package_root": None,
        },
    }
    if not global_config_path.exists():
        return result

    try:
        payload = json.loads(global_config_path.read_text(encoding="utf-8"))
    except Exception:
        result["status"] = "parse_failed"
        return result

    result["parseable"] = True
    server_tables: list[tuple[str, dict[str, Any]]] = []
    mcp_servers = payload.get("mcpServers") if isinstance(payload, dict) else None
    if isinstance(mcp_servers, dict):
        server_tables.append(("global", mcp_servers))
    projects = payload.get("projects") if isinstance(payload, dict) else None
    if isinstance(projects, dict):
        for project_name, project in projects.items():
            if not isinstance(project, dict):
                continue
            project_mcp_servers = project.get("mcpServers")
            if isinstance(project_mcp_servers, dict):
                server_tables.append((f"project:{project_name}", project_mcp_servers))
    if not server_tables:
        result["status"] = "no_mcp_servers"
        return result

    bare_npx_servers: list[str] = []
    claude_flow_mcp_servers: list[str] = []
    claude_flow_command = None
    for scope, table in server_tables:
        for name, config in table.items():
            if not isinstance(config, dict):
                continue
            scoped_name = f"{scope}:{name}"
            command = str(config.get("command") or "")
            args = _string_list(config.get("args"))
            if _looks_like_bare_windows_npx(command, args):
                bare_npx_servers.append(scoped_name)
            if _looks_like_claude_flow_mcp_server(command, args):
                claude_flow_mcp_servers.append(scoped_name)
                if claude_flow_command is None:
                    claude_flow_command = command

    claude_flow_schema_issue = {
        "detected": False,
        "detail": None,
        "package_version": None,
        "package_root": None,
    }
    if claude_flow_mcp_servers:
        package_inspection = _inspect_claude_flow_package(claude_flow_command)
        claude_flow_schema_issue = {
            "detected": bool(package_inspection["hooks_schema_issue_detected"]),
            "detail": package_inspection["hooks_schema_issue"],
            "package_version": package_inspection["package_version"],
            "package_root": package_inspection["package_root"],
        }

    duplicate_claude_flow_aliases = claude_flow_mcp_servers if len(claude_flow_mcp_servers) > 1 else []
    issue_count = 0
    if bare_npx_servers:
        issue_count += 1
    if duplicate_claude_flow_aliases:
        issue_count += 1
    if claude_flow_schema_issue["detected"]:
        issue_count += 1

    result.update(
        {
            "status": "issues_detected" if issue_count else "healthy",
            "windows_bare_npx_servers": bare_npx_servers,
            "claude_flow_mcp_servers": claude_flow_mcp_servers,
            "duplicate_claude_flow_aliases": duplicate_claude_flow_aliases,
            "claude_flow_schema_issue": claude_flow_schema_issue,
            "issue_count": issue_count,
        }
    )
    return result


def _load_bootstrap_receipts(target_root: Path) -> list[dict[str, Any]]:
    sidecar_root = target_root / ".vibeskills"
    receipts: list[dict[str, Any]] = []
    seen: set[Path] = set()
    for path in sorted(sidecar_root.glob("global-instruction-bootstrap*.json")):
        if path in seen:
            continue
        seen.add(path)
        try:
            loaded = load_json(path)
        except Exception:
            loaded = None
        if isinstance(loaded, dict):
            receipts.append({"path": path, "receipt": loaded})
    return receipts


def _parse_bootstrap_blocks(text: str) -> tuple[list[dict[str, str]], bool]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    begin_matches = list(BEGIN_MANAGED_BLOCK.finditer(normalized))
    if not begin_matches:
        return [], False

    blocks: list[dict[str, str]] = []
    search_from = 0
    for index, match in enumerate(begin_matches):
        if match.start() < search_from:
            return [], True
        next_begin_start = begin_matches[index + 1].start() if index + 1 < len(begin_matches) else None
        end_match = None
        for candidate in END_MANAGED_BLOCK_PATTERN.finditer(normalized, match.end()):
            if next_begin_start is not None and candidate.start() > next_begin_start:
                break
            end_match = candidate
            break
        if end_match is None:
            return [], True
        search_from = end_match.end()
        blocks.append(
            {
                "host_id": str(match.group("host") or "").strip(),
                "block_id": str(match.group("block") or "").strip(),
            }
        )
    return blocks, False


def _select_receipt(
    receipts: list[dict[str, Any]],
    *,
    host_id: str | None,
    target_relpath: str | None,
) -> dict[str, Any] | None:
    for entry in receipts:
        receipt = entry["receipt"]
        receipt_host = str(receipt.get("host") or "").strip()
        receipt_target_relpath = str(receipt.get("target_relpath") or "").strip()
        if host_id and receipt_host and receipt_host != host_id:
            continue
        if target_relpath and receipt_target_relpath and receipt_target_relpath != target_relpath:
            continue
        return entry
    return None


def _safe_int(value: object, default: int = 0) -> tuple[int, bool]:
    try:
        return int(value or default), False
    except (TypeError, ValueError):
        return default, True


def inspect_global_instruction_bootstrap(
    target_root: Path,
    *,
    host_id: str | None,
) -> dict[str, Any]:
    receipts = _load_bootstrap_receipts(target_root)
    ordered_hosts = [str(host_id).strip()] if host_id else list(HOST_GLOBAL_INSTRUCTION_TARGETS)

    def build_result(
        *,
        candidate_host: str,
        candidate_surface: dict[str, str],
    ) -> dict[str, Any]:
        target_relpath = str(candidate_surface["relpath"])
        target_path = (target_root / target_relpath).resolve(strict=False) if target_relpath else None
        file_exists = bool(target_path and target_path.exists())
        text = target_path.read_text(encoding="utf-8") if target_path is not None and file_exists else ""
        blocks, corruption = _parse_bootstrap_blocks(text) if file_exists else ([], False)
        receipt_entry = _select_receipt(receipts, host_id=candidate_host or None, target_relpath=str(candidate_surface["relpath"]))
        if receipt_entry is None:
            receipt_entry = _select_receipt(receipts, host_id=None, target_relpath=str(candidate_surface["relpath"]))
        receipt = receipt_entry["receipt"] if isinstance(receipt_entry, dict) else None
        receipt_path = receipt_entry["path"] if isinstance(receipt_entry, dict) else target_root / ".vibeskills" / "global-instruction-bootstrap.json"
        receipt_host = str(receipt.get("host") or "").strip() if isinstance(receipt, dict) else ""
        effective_host = receipt_host or candidate_host
        effective_surface = HOST_GLOBAL_INSTRUCTION_TARGETS.get(effective_host, candidate_surface)
        documented_path = (
            str(receipt.get("documented_path") or "").strip()
            if isinstance(receipt, dict)
            else str(effective_surface["documented_path"])
        )
        target_relpath = (
            str(receipt.get("target_relpath") or "").strip()
            if isinstance(receipt, dict) and str(receipt.get("target_relpath") or "").strip()
            else str(effective_surface["relpath"])
        )
        managed_blocks = [
            block
            for block in blocks
            if block.get("block_id") == "global-vibe-bootstrap"
            and str(block.get("host_id") or "").strip() == effective_host
        ]
        duplicate_count = len(managed_blocks)
        applicable = bool(receipt or managed_blocks or corruption)
        block_id = str(receipt.get("block_id") or "global-vibe-bootstrap").strip() if isinstance(receipt, dict) else "global-vibe-bootstrap"
        template_version, receipt_invalid = _safe_int(receipt.get("template_version") if isinstance(receipt, dict) else 0)
        content_hash = str(receipt.get("content_hash") or "").strip() if isinstance(receipt, dict) else ""
        healthy = applicable and bool(receipt) and file_exists and not corruption and not receipt_invalid and duplicate_count == 1
        if not applicable:
            status = "not_applicable"
        elif healthy:
            status = "healthy"
        elif corruption:
            status = "corrupt"
        elif duplicate_count > 1:
            status = "duplicate"
        elif not file_exists:
            status = "missing_target"
        elif not receipt:
            status = "missing_receipt"
        else:
            status = "unhealthy"

        return {
            "applicable": applicable,
            "status": status,
            "healthy": healthy,
            "host_id": effective_host or None,
            "target_relpath": target_relpath or None,
            "documented_path": documented_path or None,
            "target_file": str(target_path) if target_path is not None else None,
            "exists": file_exists,
            "receipt_exists": isinstance(receipt, dict),
            "receipt_path": str(receipt_path.resolve(strict=False)),
            "receipt": receipt,
            "block_id": block_id,
            "template_version": template_version,
            "content_hash": content_hash or None,
            "duplicate_count": duplicate_count,
            "corruption": corruption,
        }

    for candidate_host in ordered_hosts:
        surface = HOST_GLOBAL_INSTRUCTION_TARGETS.get(candidate_host)
        if surface is None:
            continue
        result = build_result(candidate_host=candidate_host, candidate_surface=surface)
        if result["applicable"]:
            return result

    if receipts:
        first_receipt = receipts[0]["receipt"]
        receipt_host = str(first_receipt.get("host") or "").strip()
        surface = HOST_GLOBAL_INSTRUCTION_TARGETS.get(receipt_host or "", {"relpath": str(first_receipt.get("target_relpath") or ""), "documented_path": str(first_receipt.get("documented_path") or "")})
        return build_result(candidate_host=receipt_host, candidate_surface=surface)

    return {
        "applicable": False,
        "status": "not_applicable",
        "healthy": False,
        "host_id": str(host_id or "").strip() or None,
        "target_relpath": None,
        "documented_path": None,
        "target_file": None,
        "exists": False,
        "receipt_exists": False,
        "receipt_path": str((target_root / ".vibeskills" / "global-instruction-bootstrap.json").resolve(strict=False)),
        "receipt": None,
        "block_id": "global-vibe-bootstrap",
        "template_version": 0,
        "content_hash": None,
        "duplicate_count": 0,
        "corruption": False,
    }
