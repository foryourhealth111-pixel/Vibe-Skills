#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .bootstrap_doctor_runtime import build_bootstrap_artifact
from .bootstrap_doctor_support import (
    load_json,
    resolve_repo_root,
    write_text,
)


def write_artifacts(repo_root: Path, artifact: dict[str, Any], output_directory: str | None) -> None:
    output_root = Path(output_directory) if output_directory else repo_root / "outputs" / "verify"
    write_text(output_root / "vibe-bootstrap-doctor-gate.json", json.dumps(artifact, ensure_ascii=False, indent=2) + "\n")
    lines = [
        "# VCO Bootstrap Doctor Gate",
        "",
        f"- Gate Result: **{artifact['gate_result']}**",
        f"- Install State: **{artifact['install_state']}**",
        f"- Readiness State: **{artifact['summary']['readiness_state']}**",
        f"- Blocking Issues: `{artifact['summary']['blocking_issue_count']}`",
        f"- Manual Actions Pending: `{artifact['summary']['manual_action_count']}`",
        f"- Warnings: `{artifact['summary']['warning_count']}`",
        f"- Target Root: `{artifact['target_root']}`",
        f"- MCP Profile: `{artifact['mcp']['profile']}`",
        f"- MCP Auto-Provision Attempted: `{artifact['mcp']['auto_provision_attempted']}`",
        f"- MCP Active File Exists: `{artifact['mcp']['active_file_exists']}`",
        "",
        "## Settings",
        "",
        f"- Settings Surface Exists: `{artifact['settings']['exists']}`",
        "- Built-in Online Enhancement Config: `not evaluated during public install`",
        "",
    ]
    global_instruction_bootstrap = ((artifact.get("host_runtime") or {}).get("global_instruction_bootstrap") or {})
    if global_instruction_bootstrap:
        lines += [
            "## Global Instruction Bootstrap",
            "",
            f"- Status: `{global_instruction_bootstrap.get('status')}`",
            f"- Applicable: `{global_instruction_bootstrap.get('applicable')}`",
            f"- Healthy: `{global_instruction_bootstrap.get('healthy')}`",
            f"- Target: `{global_instruction_bootstrap.get('target_relpath')}`",
            f"- Receipt Exists: `{global_instruction_bootstrap.get('receipt_exists')}`",
            f"- Duplicate Count: `{global_instruction_bootstrap.get('duplicate_count')}`",
            f"- Corruption: `{global_instruction_bootstrap.get('corruption')}`",
            "",
        ]
    claude_code_global_mcp = ((artifact.get("host_runtime") or {}).get("claude_code_global_mcp") or {})
    if claude_code_global_mcp.get("applicable"):
        schema_issue = claude_code_global_mcp.get("claude_flow_schema_issue") or {}
        lines += [
            "## Claude Code Global MCP",
            "",
            f"- Status: `{claude_code_global_mcp.get('status')}`",
            f"- Config Path: `{claude_code_global_mcp.get('config_path')}`",
            f"- Bare npx Servers: `{', '.join(claude_code_global_mcp.get('windows_bare_npx_servers') or []) or 'none'}`",
            f"- claude-flow MCP Aliases: `{', '.join(claude_code_global_mcp.get('claude_flow_mcp_servers') or []) or 'none'}`",
            f"- Duplicate claude-flow Aliases: `{', '.join(claude_code_global_mcp.get('duplicate_claude_flow_aliases') or []) or 'none'}`",
            f"- Schema Issue Detected: `{schema_issue.get('detected')}`",
            f"- claude-flow Version: `{schema_issue.get('package_version')}`",
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

    profile_path = repo_root / "mcp" / "profiles" / f"{profile}.json"
    active_mcp_path = target_root / "mcp" / "servers.active.json"
    mcp_receipt_path = target_root / ".vibeskills" / "mcp-auto-provision.json"
    mcp_receipt = load_json(mcp_receipt_path) if mcp_receipt_path.exists() else None

    return build_bootstrap_artifact(
        repo_root=repo_root,
        target_root=target_root,
        settings_path=settings_path,
        settings=settings,
        profile=profile,
        profile_path=profile_path,
        active_mcp_path=active_mcp_path,
        mcp_receipt_path=mcp_receipt_path,
        mcp_receipt=mcp_receipt,
        plugins_manifest=load_json(repo_root / "config" / "plugins-manifest.codex.json"),
        servers_template=load_json(repo_root / "mcp" / "servers.template.json"),
        secrets_policy=load_json(repo_root / "config" / "secrets-policy.json"),
        tool_registry=load_json(repo_root / "config" / "tool-registry.json"),
        memory_governance=load_json(repo_root / "config" / "memory-governance.json"),
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Runtime-neutral bootstrap doctor.")
    parser.add_argument("--target-root", default=str(Path.home() / ".vibeskills" / "targets" / "codex"))
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
    for issue in artifact["summary"]["blocking_issues"]:
        print(f"[BLOCK] {issue}")
    for action in artifact["summary"]["manual_actions"]:
        print(f"[ACTION] {action}")
    for warning in artifact["summary"]["warnings"]:
        print(f"[WARN] {warning}")
    return 0 if artifact["gate_result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
