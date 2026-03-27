#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def resolve_repo_root(start_path: Path) -> Path:
    current = start_path.resolve()
    if current.is_file():
        current = current.parent
    candidates: list[Path] = []
    while True:
        if (current / "config" / "version-governance.json").exists():
            candidates.append(current)
        if current.parent == current:
            break
        current = current.parent
    if not candidates:
        raise RuntimeError(f"Unable to resolve VCO repo root from: {start_path}")
    git_candidates = [candidate for candidate in candidates if (candidate / ".git").exists()]
    if git_candidates:
        return git_candidates[-1]
    return candidates[-1]


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
    import os

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


def write_artifacts(repo_root: Path, artifact: dict[str, Any], output_directory: str | None) -> None:
    output_root = Path(output_directory) if output_directory else repo_root / "outputs" / "verify"
    write_text(output_root / "vibe-bootstrap-doctor-gate.json", json.dumps(artifact, ensure_ascii=False, indent=2) + "\n")
    lines = [
        "# VCO Bootstrap Doctor Gate",
        "",
        f"- Gate Result: **{artifact['gate_result']}**",
        f"- Readiness State: **{artifact['summary']['readiness_state']}**",
        f"- Blocking Issues: `{artifact['summary']['blocking_issue_count']}`",
        f"- Manual Actions Pending: `{artifact['summary']['manual_action_count']}`",
        f"- Warnings: `{artifact['summary']['warning_count']}`",
        f"- Target Root: `{artifact['target_root']}`",
        f"- MCP Profile: `{artifact['mcp']['profile']}`",
        f"- MCP Active File Exists: `{artifact['mcp']['active_file_exists']}`",
        "",
        "## Settings",
        "",
        f"- `OPENAI_API_KEY`: `{artifact['settings']['openai_api_key_state']}` via `{artifact['settings']['openai_api_key_source']}`",
        f"- `VCO_RUCNLPIR_MODEL`: `{artifact['settings']['vco_rucnlpir_model_state']}` via `{artifact['settings']['vco_rucnlpir_model_source']}`",
        "",
    ]
    if artifact["plugins"]:
        lines += ["## Plugin Readiness", ""]
        for plugin in artifact["plugins"]:
            lines.append(
                f"- `{plugin['name']}`: status=`{plugin['status']}` install_mode=`{plugin['install_mode']}` next_step=`{plugin['next_step']}`"
            )
        lines.append("")
    if artifact["external_tools"]:
        lines += ["## External Tools", ""]
        for tool in artifact["external_tools"]:
            lines.append(
                f"- `{tool['name']}`: present=`{tool['present']}` required_for=`{', '.join(tool['required_for'])}`"
            )
        lines.append("")
    if artifact["enhancement_surfaces"]:
        lines += ["## Enhancement Surfaces", ""]
        for surface in artifact["enhancement_surfaces"]:
            lines.append(
                f"- `{surface['name']}`: role=`{surface['role']}` status=`{surface['status']}` next_step=`{surface['next_step']}`"
            )
        lines.append("")
    if artifact["mcp"]["servers"]:
        lines += ["## MCP Servers", ""]
        for server in artifact["mcp"]["servers"]:
            lines.append(
                f"- `{server['name']}`: mode=`{server['mode']}` status=`{server['status']}` next_step=`{server['next_step']}`"
            )
        lines.append("")
    if artifact["integration_surfaces"]:
        lines += ["## External Integration Surfaces", ""]
        for surface in artifact["integration_surfaces"]:
            lines.append(
                f"- `{surface['name']}`: status=`{surface['status']}` risk=`{surface['risk_tier']}` confirm_required=`{surface['confirm_required']}` next_step=`{surface['next_step']}`"
            )
        lines.append("")
    if artifact["secret_surfaces"]:
        lines += ["## Secret Surfaces", ""]
        for secret in artifact["secret_surfaces"]:
            lines.append(
                f"- `{secret['name']}`: status=`{secret['status']}` storage=`{', '.join(secret['storage'])}`"
            )
        lines.append("")
    write_text(output_root / "vibe-bootstrap-doctor-gate.md", "\n".join(lines) + "\n")


def evaluate(repo_root: Path, target_root: Path) -> dict[str, Any]:
    settings_path = target_root / "settings.json"
    settings = load_json(settings_path) if settings_path.exists() else None
    profile = "full"
    if isinstance(settings, dict):
        vco = settings.get("vco")
        if isinstance(vco, dict) and vco.get("mcp_profile"):
            profile = str(vco["mcp_profile"])

    plugins_manifest = load_json(repo_root / "config" / "plugins-manifest.codex.json")
    servers_template = load_json(repo_root / "mcp" / "servers.template.json")
    secrets_policy = load_json(repo_root / "config" / "secrets-policy.json")
    tool_registry = load_json(repo_root / "config" / "tool-registry.json")
    memory_governance = load_json(repo_root / "config" / "memory-governance.json")
    profile_path = repo_root / "mcp" / "profiles" / f"{profile}.json"
    profile_object = load_json(profile_path) if profile_path.exists() else {"profile": profile, "enabled_servers": []}
    active_mcp_path = target_root / "mcp" / "servers.active.json"

    plugins: list[dict[str, Any]] = []
    for plugin in list(plugins_manifest.get("core") or []) + list(plugins_manifest.get("optional") or []):
        if not plugin:
            continue
        install_mode = str(plugin.get("install_mode") or "unknown")
        if install_mode == "manual-codex":
            status = "platform_plugin_required"
        elif install_mode == "scripted" and "claude-flow" in str(plugin.get("install") or ""):
            status = "ready" if command_present("claude-flow") else "auto_installable_missing"
        elif install_mode == "scripted":
            status = "scripted_unknown_probe"
        else:
            status = "unknown"
        if status == "platform_plugin_required":
            next_step = str(plugin.get("install_hint") or "Provision in Codex host runtime.")
        elif status == "auto_installable_missing":
            next_step = str(plugin.get("install") or "Install via documented package manager.")
        else:
            next_step = "none"
        plugins.append(
            {
                "name": str(plugin.get("name") or ""),
                "install_mode": install_mode,
                "status": status,
                "required": bool(plugin.get("required")),
                "next_step": next_step,
            }
        )

    external_tools = [
        {"name": "git", "present": command_present("git"), "required_for": ["bootstrap"]},
        {"name": "npm", "present": command_present("npm"), "required_for": ["claude-flow", "ralph-wiggum"]},
        {"name": "python", "present": command_present("python") or command_present("python3"), "required_for": ["default-mcp:scrapling", "ivy"]},
        {"name": "claude-flow", "present": command_present("claude-flow"), "required_for": ["mcp:claude-flow"]},
        {"name": "scrapling", "present": command_present("scrapling"), "required_for": ["default-full-profile-mcp:scrapling"]},
        {"name": "xan", "present": command_present("xan"), "required_for": ["csv-acceleration"]},
    ]

    template_servers = servers_template.get("servers") or {}
    mcp_servers: list[dict[str, Any]] = []
    for server_name in profile_object.get("enabled_servers") or []:
        server = template_servers.get(server_name)
        if server is None:
            mcp_servers.append(
                {
                    "name": str(server_name),
                    "mode": "unknown",
                    "status": "missing_from_template",
                    "next_step": "Fix mcp/profile definition mismatch.",
                }
            )
            continue
        mode = str(server.get("mode") or "unknown")
        status = "ready"
        next_step = "none"
        if mode == "plugin":
            status = "platform_plugin_required"
            next_step = "Provision the corresponding Codex plugin in the host runtime."
        elif mode == "stdio":
            command_name = str(server.get("command") or "")
            if not command_present(command_name):
                status = "manual_action_required"
                next_step = str(server.get("note") or f"Install command '{command_name}' and register the MCP server in the host.")
        mcp_servers.append(
            {
                "name": str(server_name),
                "mode": mode,
                "status": status,
                "next_step": next_step,
            }
        )

    secret_surfaces: list[dict[str, Any]] = []
    for secret in secrets_policy.get("allowed_secret_refs") or []:
        name = str(secret.get("name") or "")
        env_value = os_environ(name)
        if name == "COMPOSIO_SESSION_MCP_URL":
            status = "runtime_present" if env_value else "runtime_not_set"
        else:
            status = "configured_in_env" if env_value else "not_configured"
        secret_surfaces.append(
            {
                "name": name,
                "scope": str(secret.get("scope") or ""),
                "storage": [str(item) for item in secret.get("storage") or []],
                "status": status,
            }
        )

    secret_status_by_name = {item["name"]: item["status"] for item in secret_surfaces}

    cognee_boundary = ((memory_governance.get("role_boundaries") or {}).get("cognee") or {})
    task_defaults = memory_governance.get("defaults_by_task") or {}
    total_task_defaults = sum(1 for config in task_defaults.values() if isinstance(config, dict))
    cognee_default_count = sum(
        1 for config in task_defaults.values() if isinstance(config, dict) and str(config.get("long_term") or "") == "cognee"
    )
    enhancement_surfaces = [
        {
            "name": "cognee",
            "role": "default_long_term_graph_memory_owner",
            "status": (
                "declared_default_owner"
                if str(cognee_boundary.get("status") or "") == "active"
                and total_task_defaults > 0
                and cognee_default_count == total_task_defaults
                else "governance_review_required"
            ),
            "task_default_coverage": f"{cognee_default_count}/{total_task_defaults}" if total_task_defaults else "0/0",
            "next_step": "Optional enhancement lane. Enable Cognee only when you want governed cross-session graph memory; keep state_store as the session truth-source.",
        }
    ]

    integration_surfaces: list[dict[str, Any]] = []
    for tool in tool_registry.get("tools") or []:
        tool_id = str(tool.get("tool_id") or "")
        if tool_id not in {"activepieces-mcp", "composio-tool-router"}:
            continue
        secret_refs = [str(item) for item in tool.get("secret_refs") or []]
        secret_states = {name: secret_status_by_name.get(name, "not_configured") for name in secret_refs}
        ready_states = {"configured_in_env", "runtime_present"}
        status = (
            "ready_for_host_registration"
            if secret_refs and all(state in ready_states for state in secret_states.values())
            else "prewired_setup_required"
        )
        if tool_id == "activepieces-mcp":
            next_step = "Set ACTIVEPIECES_MCP_TOKEN, replace the placeholder project endpoint, and enable the MCP surface only when you need governed external automation."
        else:
            next_step = "Set COMPOSIO_API_KEY, create a session-scoped COMPOSIO_SESSION_MCP_URL, and keep Composio actions confirm-gated."
        integration_surfaces.append(
            {
                "name": str(tool.get("display_name") or tool_id),
                "tool_id": tool_id,
                "status": status,
                "risk_tier": str(tool.get("risk_tier") or "unknown"),
                "confirm_required": bool(((tool.get("human_confirmation") or {}).get("per_action_required"))),
                "enable_required": bool(((tool.get("human_confirmation") or {}).get("enable_required"))),
                "secret_refs": secret_refs,
                "secret_states": secret_states,
                "next_step": next_step,
            }
        )

    blocking_issues: list[str] = []
    manual_actions: list[str] = []
    warnings: list[str] = []

    if not settings_path.exists():
        blocking_issues.append("settings.json is missing in target root.")
    openai_api_key_state, openai_api_key_source = resolved_setting_state(settings, "OPENAI_API_KEY")
    governance_model_state, governance_model_source = resolved_setting_state(settings, "VCO_RUCNLPIR_MODEL")

    if openai_api_key_state != "configured":
        manual_actions.append("OPENAI_API_KEY must be configured for full online Codex usage.")
    if governance_model_state != "configured":
        manual_actions.append("VCO_RUCNLPIR_MODEL must be configured for built-in governance advice readiness.")
    if not active_mcp_path.exists():
        manual_actions.append("MCP active profile has not been materialized yet (servers.active.json missing).")
    for plugin in plugins:
        if plugin["status"] == "platform_plugin_required" and plugin["required"]:
            manual_actions.append(f"Required host plugin pending: {plugin['name']}")
    for server in mcp_servers:
        if server["status"] in {"platform_plugin_required", "manual_action_required", "missing_from_template"}:
            manual_actions.append(f"MCP server pending: {server['name']}")
    for tool in external_tools:
        if not tool["present"] and tool["name"] in {"npm", "claude-flow"}:
            warnings.append(f"Optional external tool missing: {tool['name']}")

    readiness_state = (
        "core_install_incomplete"
        if blocking_issues
        else "manual_actions_pending"
        if manual_actions
        else "fully_ready"
    )

    return {
        "gate": "vibe-bootstrap-doctor-gate",
        "generated_at": utc_now(),
        "repo_root": str(repo_root),
        "target_root": str(target_root.resolve()),
        "gate_result": "PASS" if not blocking_issues else "FAIL",
        "settings": {
            "path": str(settings_path),
            "exists": settings_path.exists(),
            "openai_api_key_state": openai_api_key_state,
            "openai_api_key_source": openai_api_key_source,
            "openai_base_url_state": setting_state(settings, "OPENAI_BASE_URL"),
            "vco_rucnlpir_model_state": governance_model_state,
            "vco_rucnlpir_model_source": governance_model_source,
        },
        "plugins": plugins,
        "external_tools": external_tools,
        "enhancement_surfaces": enhancement_surfaces,
        "mcp": {
            "profile": profile,
            "profile_path": str(profile_path.relative_to(repo_root)) if profile_path.exists() else None,
            "active_file_path": str(active_mcp_path),
            "active_file_exists": active_mcp_path.exists(),
            "servers": mcp_servers,
        },
        "integration_surfaces": integration_surfaces,
        "secret_surfaces": secret_surfaces,
        "summary": {
            "readiness_state": readiness_state,
            "blocking_issue_count": len(blocking_issues),
            "manual_action_count": len(manual_actions),
            "warning_count": len(warnings),
            "blocking_issues": blocking_issues,
            "manual_actions": manual_actions,
            "warnings": warnings,
        },
    }

def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Runtime-neutral bootstrap doctor.")
    parser.add_argument("--target-root", default=str(Path.home() / ".codex"))
    parser.add_argument("--write-artifacts", action="store_true")
    parser.add_argument("--output-directory")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    script_path = Path(__file__)
    try:
        repo_root = resolve_repo_root(script_path)
        artifact = evaluate(repo_root, Path(args.target_root))
        if args.write_artifacts:
            write_artifacts(repo_root, artifact, args.output_directory)
    except Exception as exc:  # pragma: no cover
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1
    print(f"[INFO] readiness_state={artifact['summary']['readiness_state']}")
    return 0 if artifact["gate_result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
