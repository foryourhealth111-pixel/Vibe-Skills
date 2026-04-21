from __future__ import annotations

from pathlib import Path
from typing import Any

from vgo_contracts.host_runtime_readiness import evaluate_host_runtime_readiness

from .bootstrap_doctor_support import (
    command_present,
    inspect_claude_code_global_mcp_config,
    inspect_global_instruction_bootstrap,
    load_json,
    os_environ,
    resolved_setting_state,
    setting_state,
    utc_now,
)


def collect_plugins(plugins_manifest: dict[str, Any]) -> list[dict[str, Any]]:
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
    return plugins


def collect_external_tools() -> list[dict[str, Any]]:
    return [
        {"name": "git", "present": command_present("git"), "required_for": ["bootstrap"]},
        {"name": "npm", "present": command_present("npm"), "required_for": ["claude-flow", "ralph-wiggum"]},
        {"name": "python", "present": command_present("python") or command_present("python3"), "required_for": ["default-mcp:scrapling", "ivy"]},
        {"name": "claude-flow", "present": command_present("claude-flow"), "required_for": ["mcp:claude-flow"]},
        {"name": "scrapling", "present": command_present("scrapling"), "required_for": ["default-full-profile-mcp:scrapling"]},
        {"name": "xan", "present": command_present("xan"), "required_for": ["csv-acceleration"]},
    ]


def collect_mcp_servers(profile_object: dict[str, Any], servers_template: dict[str, Any]) -> list[dict[str, Any]]:
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
            if command_present(command_name):
                status = "local_tool_present"
                next_step = "Register the stdio server in the host active MCP surface."
            else:
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
    return mcp_servers


def collect_mcp_servers_from_receipt(mcp_receipt: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(mcp_receipt, dict):
        return []
    servers: list[dict[str, Any]] = []
    for server in mcp_receipt.get("mcp_results") or []:
        if not isinstance(server, dict):
            continue
        servers.append(
            {
                "name": str(server.get("name") or ""),
                "mode": str(server.get("provision_path") or "unknown"),
                "status": str(server.get("status") or "unknown"),
                "next_step": str(server.get("next_step") or "none"),
            }
        )
    return servers


def load_active_mcp_servers(active_mcp_path: Path) -> dict[str, dict[str, Any]]:
    if not active_mcp_path.exists():
        return {}
    try:
        payload = load_json(active_mcp_path)
    except Exception:
        return {}
    servers = payload.get("servers") if isinstance(payload, dict) else None
    if not isinstance(servers, dict):
        return {}
    return {
        str(name): dict(config)
        for name, config in servers.items()
        if isinstance(config, dict)
    }


def reconcile_mcp_servers_with_active_surface(
    mcp_servers: list[dict[str, Any]],
    *,
    active_mcp_path: Path,
) -> list[dict[str, Any]]:
    active_servers = load_active_mcp_servers(active_mcp_path)
    reconciled: list[dict[str, Any]] = []
    for server in mcp_servers:
        next_server = dict(server)
        name = str(next_server.get("name") or "")
        status = str(next_server.get("status") or "")
        active_entry = active_servers.get(name)
        mode = str(next_server.get("mode") or "")
        command_name = ""
        if isinstance(active_entry, dict):
            command_name = str(active_entry.get("command") or "")
            if not mode or mode == "unknown":
                mode = str(active_entry.get("mode") or mode or "unknown")
                next_server["mode"] = mode
        if mode == "scripted_cli":
            mode = "stdio"
            next_server["mode"] = mode
        if mode == "stdio" and status == "local_tool_present" and active_entry is not None:
            if command_name and command_present(command_name):
                next_server["status"] = "ready"
                next_server["next_step"] = "none"
        reconciled.append(next_server)
    return reconciled


def collect_host_runtime(repo_root: Path, target_root: Path) -> dict[str, Any]:
    """Collect the host runtime state surfaced by bootstrap doctor."""
    runtime_skill_entry = target_root / "skills" / "vibe" / "SKILL.md"
    commands_root = target_root / "commands"
    host_closure_path = target_root / ".vibeskills" / "host-closure.json"
    settings_path = target_root / "settings.json"
    host_settings_path = target_root / ".vibeskills" / "host-settings.json"
    settings_surface_exists = settings_path.exists() or host_settings_path.exists()
    settings_surface_path = settings_path if settings_path.exists() else host_settings_path
    settings_surface_kind = (
        "settings.json"
        if settings_path.exists()
        else "host-settings.json"
        if host_settings_path.exists()
        else "missing"
    )

    host_closure_payload: dict[str, Any] = {}
    host_closure_valid = False
    host_id = ""
    if host_closure_path.exists():
        try:
            loaded = load_json(host_closure_path)
        except Exception:
            loaded = None
        if isinstance(loaded, dict):
            host_closure_payload = loaded
            host_closure_valid = True
            host_id = str(host_closure_payload.get("host_id") or "").strip()
    specialist_wrapper = host_closure_payload.get("specialist_wrapper") if host_closure_valid else None
    specialist_wrapper_ready = bool(specialist_wrapper.get("ready")) if isinstance(specialist_wrapper, dict) else False
    runtime_readiness = evaluate_host_runtime_readiness(
        repo_root,
        host_id or None,
        specialist_wrapper_ready=specialist_wrapper_ready,
    )

    runtime_skill_entry_path = str(runtime_skill_entry.resolve())
    commands_root_path = str(commands_root.resolve())
    host_closure_runtime_matches = (
        host_closure_valid
        and str(host_closure_payload.get("runtime_skill_entry") or "").strip() == runtime_skill_entry_path
    )
    host_closure_commands_match = (
        host_closure_valid
        and str(host_closure_payload.get("commands_root") or "").strip() == commands_root_path
    )
    host_closure_commands_materialized = bool(host_closure_payload.get("commands_materialized")) if host_closure_valid else False
    host_closure_state = str(host_closure_payload.get("host_closure_state") or "").strip() if host_closure_valid else ""
    vibe_host_ready = (
        runtime_skill_entry.exists()
        and commands_root.exists()
        and settings_surface_exists
        and host_closure_valid
        and host_closure_runtime_matches
        and host_closure_commands_match
        and host_closure_commands_materialized
        and bool(runtime_readiness["effective_runtime_ready"])
    )
    global_instruction_bootstrap = inspect_global_instruction_bootstrap(
        target_root,
        host_id=str(runtime_readiness.get("host_id") or host_id or "").strip() or None,
    )
    claude_code_global_mcp = (
        inspect_claude_code_global_mcp_config(target_root)
        if (str(runtime_readiness.get("host_id") or host_id or "").strip() == "claude-code")
        else {"applicable": False}
    )
    return {
        "host_id": str(runtime_readiness.get("host_id") or host_id or "").strip() or None,
        "entry_mode": str(runtime_readiness["entry_mode"]),
        "readiness_driver": str(runtime_readiness["readiness_driver"]),
        "effective_runtime_ready": bool(runtime_readiness["effective_runtime_ready"]),
        "host_closure_state": host_closure_state,
        "runtime_skill_entry_path": runtime_skill_entry_path,
        "runtime_skill_entry_exists": runtime_skill_entry.exists(),
        "commands_root_path": commands_root_path,
        "commands_root_exists": commands_root.exists(),
        "host_closure_path": str(host_closure_path),
        "host_closure_exists": host_closure_path.exists(),
        "host_closure_valid": host_closure_valid,
        "host_closure_runtime_matches": host_closure_runtime_matches,
        "host_closure_commands_match": host_closure_commands_match,
        "host_closure_commands_materialized": host_closure_commands_materialized,
        "specialist_wrapper_ready": specialist_wrapper_ready,
        "settings_surface_path": str(settings_surface_path),
        "settings_surface_exists": settings_surface_exists,
        "settings_surface_kind": settings_surface_kind,
        "vibe_host_ready": vibe_host_ready,
        "direct_runtime": dict(runtime_readiness["direct_runtime"]),
        "global_instruction_bootstrap": global_instruction_bootstrap,
        "claude_code_global_mcp": claude_code_global_mcp,
    }


def collect_secret_surfaces(secrets_policy: dict[str, Any]) -> list[dict[str, Any]]:
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
    return secret_surfaces


def collect_enhancement_surfaces(memory_governance: dict[str, Any]) -> list[dict[str, Any]]:
    cognee_boundary = ((memory_governance.get("role_boundaries") or {}).get("cognee") or {})
    task_defaults = memory_governance.get("defaults_by_task") or {}
    total_task_defaults = sum(1 for config in task_defaults.values() if isinstance(config, dict))
    cognee_default_count = sum(
        1 for config in task_defaults.values() if isinstance(config, dict) and str(config.get("long_term") or "") == "cognee"
    )
    return [
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


def collect_integration_surfaces(tool_registry: dict[str, Any], secret_status_by_name: dict[str, str]) -> list[dict[str, Any]]:
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
    return integration_surfaces


def build_summary(
    *,
    settings_path: Path,
    active_mcp_path: Path,
    settings: dict[str, Any] | None,
    install_state: str,
    host_runtime: dict[str, Any],
    plugins: list[dict[str, Any]],
    mcp_servers: list[dict[str, Any]],
    external_tools: list[dict[str, Any]],
    global_instruction_bootstrap: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build the user-facing summary for bootstrap doctor results."""
    blocking_issues: list[str] = []
    manual_actions: list[str] = []
    warnings: list[str] = []

    if not settings_path.exists():
        blocking_issues.append("settings.json is missing in target root.")
    if isinstance(global_instruction_bootstrap, dict) and bool(global_instruction_bootstrap.get("applicable")):
        if not bool(global_instruction_bootstrap.get("healthy")):
            status = str(global_instruction_bootstrap.get("status") or "unhealthy")
            blocking_issues.append(
                f"global instruction bootstrap is unhealthy ({status})"
            )
    claude_code_global_mcp = host_runtime.get("claude_code_global_mcp") if isinstance(host_runtime, dict) else None
    if isinstance(claude_code_global_mcp, dict) and bool(claude_code_global_mcp.get("applicable")):
        repair_hint = "Run scripts/setup/repair-claude-code-global-mcp.ps1 or fix ~/.claude.json manually."
        if str(claude_code_global_mcp.get("status") or "") == "parse_failed":
            warnings.append("Claude Code global MCP config exists but could not be parsed; inspect ~/.claude.json manually.")
        bare_npx_servers = [str(item) for item in claude_code_global_mcp.get("windows_bare_npx_servers") or []]
        if bare_npx_servers:
            manual_actions.append(
                "Claude Code global MCP config uses bare npx entries on Windows for: "
                + ", ".join(bare_npx_servers)
                + f". {repair_hint}"
            )
        duplicate_aliases = [str(item) for item in claude_code_global_mcp.get("duplicate_claude_flow_aliases") or []]
        if duplicate_aliases:
            warnings.append(
                "Claude Code global MCP config registers multiple claude-flow MCP aliases: "
                + ", ".join(duplicate_aliases)
                + ". Keep at most one alias."
            )
        schema_issue = claude_code_global_mcp.get("claude_flow_schema_issue") or {}
        if isinstance(schema_issue, dict) and bool(schema_issue.get("detected")):
            package_version = str(schema_issue.get("package_version") or "unknown")
            manual_actions.append(
                "Installed claude-flow "
                + package_version
                + " emits an invalid MCP schema for hooks_intelligence_learn.trajectoryIds. "
                + "Disable/remove global claude-flow/ruflo MCP entries or upgrade claude-flow. "
                + repair_hint
            )
    if install_state != "installed_locally":
        warnings.append(f"Install state is '{install_state}'; verify the local install receipt.")
    if isinstance(host_runtime, dict) and not bool(host_runtime.get("vibe_host_ready")):
        readiness_driver = str(host_runtime.get("readiness_driver") or "")
        effective_runtime_ready = bool(host_runtime.get("effective_runtime_ready"))
        if readiness_driver == "direct_runtime":
            if not effective_runtime_ready:
                direct_runtime = host_runtime.get("direct_runtime")
                if isinstance(direct_runtime, dict):
                    env_name = str(direct_runtime.get("executable_env") or "").strip()
                    command = str(direct_runtime.get("command") or "codex").strip()
                    if env_name:
                        manual_actions.append(
                            f"Direct runtime executable is not ready. Resolve '{command}' on PATH or via {env_name}."
                        )
                    else:
                        manual_actions.append(
                            f"Direct runtime executable is not ready. Resolve '{command}' on PATH and re-run check."
                        )
            else:
                manual_actions.append(
                    "Direct runtime is available, but the local install surfaces are incomplete. Re-run installation to refresh host closure, commands, and managed settings."
                )
        else:
            if effective_runtime_ready:
                manual_actions.append(
                    "Bridged host wrapper is available, but the local install surfaces are incomplete. Re-run installation to refresh host closure, commands, and managed settings."
                )
            else:
                manual_actions.append("Host runtime is not fully ready; complete the specialist bridge setup and re-run check.")
    intent_advice_api_key_state, intent_advice_api_key_source = resolved_setting_state(settings, "VCO_INTENT_ADVICE_API_KEY")
    intent_advice_model_state, intent_advice_model_source = resolved_setting_state(settings, "VCO_INTENT_ADVICE_MODEL")
    vector_diff_api_key_state, vector_diff_api_key_source = resolved_setting_state(settings, "VCO_VECTOR_DIFF_API_KEY")
    vector_diff_model_state, vector_diff_model_source = resolved_setting_state(settings, "VCO_VECTOR_DIFF_MODEL")

    if intent_advice_api_key_state != "configured":
        manual_actions.append("VCO_INTENT_ADVICE_API_KEY must be configured for built-in intent advice readiness.")
    if intent_advice_model_state != "configured":
        manual_actions.append("VCO_INTENT_ADVICE_MODEL must be configured for built-in intent advice readiness.")
    if vector_diff_api_key_state != "configured" or vector_diff_model_state != "configured":
        warnings.append("Vector diff embeddings are not fully configured; large-diff retrieval will degrade gracefully.")
    if not active_mcp_path.exists():
        manual_actions.append("MCP active profile has not been materialized yet (servers.active.json missing).")
    for plugin in plugins:
        if plugin["status"] == "platform_plugin_required" and plugin["required"]:
            manual_actions.append(f"Required host plugin pending: {plugin['name']}")
    for server in mcp_servers:
        if server["status"] != "ready":
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
        "readiness_state": readiness_state,
        "blocking_issue_count": len(blocking_issues),
        "manual_action_count": len(manual_actions),
        "warning_count": len(warnings),
        "blocking_issues": blocking_issues,
        "manual_actions": manual_actions,
        "warnings": warnings,
        "intent_advice_api_key_state": intent_advice_api_key_state,
        "intent_advice_api_key_source": intent_advice_api_key_source,
        "intent_advice_model_state": intent_advice_model_state,
        "intent_advice_model_source": intent_advice_model_source,
        "vector_diff_api_key_state": vector_diff_api_key_state,
        "vector_diff_api_key_source": vector_diff_api_key_source,
        "vector_diff_model_state": vector_diff_model_state,
        "vector_diff_model_source": vector_diff_model_source,
    }


def build_bootstrap_artifact(
    *,
    repo_root: Path,
    target_root: Path,
    settings_path: Path,
    settings: dict[str, Any] | None,
    profile: str,
    profile_path: Path,
    active_mcp_path: Path,
    mcp_receipt_path: Path,
    mcp_receipt: dict[str, Any] | None,
    plugins_manifest: dict[str, Any],
    servers_template: dict[str, Any],
    secrets_policy: dict[str, Any],
    tool_registry: dict[str, Any],
    memory_governance: dict[str, Any],
) -> dict[str, Any]:
    plugins = collect_plugins(plugins_manifest)
    external_tools = collect_external_tools()
    profile_object = {"profile": profile, "enabled_servers": []}
    if profile_path.exists():
        with profile_path.open("r", encoding="utf-8-sig") as handle:
            import json

            profile_object = json.load(handle)
    receipt = mcp_receipt if isinstance(mcp_receipt, dict) else {}
    mcp_servers = collect_mcp_servers_from_receipt(receipt)
    if not mcp_servers:
        mcp_servers = collect_mcp_servers(profile_object, servers_template)
    mcp_servers = reconcile_mcp_servers_with_active_surface(mcp_servers, active_mcp_path=active_mcp_path)
    install_state = str(receipt.get("install_state") or "unknown")
    auto_provision_attempted = bool(receipt.get("mcp_auto_provision_attempted"))
    secret_surfaces = collect_secret_surfaces(secrets_policy)
    secret_status_by_name = {item["name"]: item["status"] for item in secret_surfaces}
    enhancement_surfaces = collect_enhancement_surfaces(memory_governance)
    integration_surfaces = collect_integration_surfaces(tool_registry, secret_status_by_name)
    host_runtime = collect_host_runtime(repo_root, target_root)
    summary = build_summary(
        settings_path=settings_path,
        active_mcp_path=active_mcp_path,
        settings=settings,
        install_state=install_state,
        host_runtime=host_runtime,
        plugins=plugins,
        mcp_servers=mcp_servers,
        external_tools=external_tools,
        global_instruction_bootstrap=host_runtime.get("global_instruction_bootstrap"),
    )

    return {
        "gate": "vibe-bootstrap-doctor-gate",
        "generated_at": utc_now(),
        "repo_root": str(repo_root),
        "target_root": str(target_root.resolve()),
        "install_state": install_state,
        "gate_result": "PASS" if not summary["blocking_issues"] else "FAIL",
        "settings": {
            "path": str(settings_path),
            "exists": settings_path.exists(),
            "intent_advice_api_key_state": summary["intent_advice_api_key_state"],
            "intent_advice_api_key_source": summary["intent_advice_api_key_source"],
            "intent_advice_base_url_state": setting_state(settings, "VCO_INTENT_ADVICE_BASE_URL"),
            "intent_advice_model_state": summary["intent_advice_model_state"],
            "intent_advice_model_source": summary["intent_advice_model_source"],
            "vector_diff_api_key_state": summary["vector_diff_api_key_state"],
            "vector_diff_api_key_source": summary["vector_diff_api_key_source"],
            "vector_diff_base_url_state": setting_state(settings, "VCO_VECTOR_DIFF_BASE_URL"),
            "vector_diff_model_state": summary["vector_diff_model_state"],
            "vector_diff_model_source": summary["vector_diff_model_source"],
        },
        "host_runtime": host_runtime,
        "plugins": plugins,
        "external_tools": external_tools,
        "enhancement_surfaces": enhancement_surfaces,
        "mcp": {
            "profile": profile,
            "profile_path": str(profile_path.relative_to(repo_root)) if profile_path.exists() else None,
            "active_file_path": str(active_mcp_path),
            "active_file_exists": active_mcp_path.exists(),
            "auto_provision_attempted": auto_provision_attempted,
            "receipt_path": str(mcp_receipt_path),
            "receipt_exists": mcp_receipt_path.exists(),
            "servers": mcp_servers,
        },
        "integration_surfaces": integration_surfaces,
        "secret_surfaces": secret_surfaces,
        "summary": {
            "readiness_state": summary["readiness_state"],
            "blocking_issue_count": summary["blocking_issue_count"],
            "manual_action_count": summary["manual_action_count"],
            "warning_count": summary["warning_count"],
            "blocking_issues": summary["blocking_issues"],
            "manual_actions": summary["manual_actions"],
            "warnings": summary["warnings"],
        },
    }
