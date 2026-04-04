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
        f"- `VCO_INTENT_ADVICE_API_KEY`: `{artifact['settings']['intent_advice_api_key_state']}` via `{artifact['settings']['intent_advice_api_key_source']}`",
        f"- `VCO_INTENT_ADVICE_MODEL`: `{artifact['settings']['intent_advice_model_state']}` via `{artifact['settings']['intent_advice_model_source']}`",
        f"- `VCO_VECTOR_DIFF_API_KEY`: `{artifact['settings']['vector_diff_api_key_state']}` via `{artifact['settings']['vector_diff_api_key_source']}`",
        f"- `VCO_VECTOR_DIFF_MODEL`: `{artifact['settings']['vector_diff_model_state']}` via `{artifact['settings']['vector_diff_model_source']}`",
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

    return build_bootstrap_artifact(
        repo_root=repo_root,
        target_root=target_root,
        settings_path=settings_path,
        settings=settings,
        profile=profile,
        profile_path=profile_path,
        active_mcp_path=active_mcp_path,
        plugins_manifest=load_json(repo_root / "config" / "plugins-manifest.codex.json"),
        servers_template=load_json(repo_root / "mcp" / "servers.template.json"),
        secrets_policy=load_json(repo_root / "config" / "secrets-policy.json"),
        tool_registry=load_json(repo_root / "config" / "tool-registry.json"),
        memory_governance=load_json(repo_root / "config" / "memory-governance.json"),
    )


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
