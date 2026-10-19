from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .kernel.host_skill_roots import resolve_host_skill_roots
from .kernel.skill_index import (
    CONTROLLER_SKILL_IDS,
    HOST_INSTALLED_SOURCE_KIND,
    is_local_skill_identifier,
    scan_skill_catalog,
)


def skill_root_projection(
    *, repo_root: Path, agent_root: Path, host_id: str, workspace_root: Path | None,
) -> list[dict[str, str]]:
    roots = resolve_host_skill_roots(
        repo_root=repo_root, agent_root=agent_root, host_id=host_id, workspace_root=workspace_root,
    )
    kinds = {"skills_dir": "host_local", "host_default": "host_local", "codex_plugin_cache": "host_plugin_cache"}
    return [{"kind": kinds.get(root.root_key, root.root_key), "path": str(root.path)} for root in roots]


def skill_source_rejection_reason(entry: dict[str, Any]) -> str | None:
    """Check one active scanner snapshot without rescanning or changing source precedence."""
    if entry.get("active") is not True:
        return "inactive_skill_source"
    descriptor = Path(str(entry["resolved_skill_file"])).resolve()
    source_root = Path(str(entry["resolved_source_root"])).resolve()
    if not descriptor.is_relative_to(source_root):
        return "skill_outside_declared_root"
    if descriptor.parent.name.casefold() in CONTROLLER_SKILL_IDS:
        return "controller_entry_excluded"
    if entry.get("enabled") is not True:
        return "skill_disabled"
    return None


def resolve_skill_authority(
    *,
    repo_root: Path,
    agent_root: Path,
    host_id: str,
    workspace_root: Path | None,
    skill_id: str,
    skill_entrypoint: str | None = None,
    require_provided_entrypoint: bool = False,
) -> dict[str, Any]:
    """Resolve an eligible local source; this interface never selects task Skills or writes caches."""
    identity = str(skill_id).strip()
    rejected: dict[str, Any] = {
        "valid": False, "reason": "not_in_local_skill_index", "skill_id": identity,
        "canonical_entrypoint": None,
    }
    if not identity:
        return {**rejected, "reason": "missing_skill_id"}
    if not is_local_skill_identifier(identity):
        return {**rejected, "reason": "invalid_skill_id"}
    normalized = identity.casefold()
    if normalized in CONTROLLER_SKILL_IDS:
        return {**rejected, "reason": "controller_entry_excluded"}

    roots = resolve_host_skill_roots(
        repo_root=repo_root, agent_root=agent_root, host_id=host_id, workspace_root=workspace_root,
    )
    catalog = scan_skill_catalog(agent_root=agent_root, host_roots=tuple(root.path for root in roots))
    active = next((
        row for row in catalog["entries"]
        if row["active"] and row["source_kind"] == HOST_INSTALLED_SOURCE_KIND
        and str(row["skill_id"]).casefold() == normalized
    ), None)
    if active is None:
        diagnostic = next((
            row for row in catalog["discovery_diagnostics"]["invalid_entries"]
            if str(row["skill_id"]).casefold() == normalized
        ), None)
        reason = diagnostic["reason"] if diagnostic is not None else rejected["reason"]
        if reason == "ambiguous_plugin_skill_id":
            reason = "ambiguous_nested_skill_id"
        return {**rejected, "reason": reason}

    descriptor = Path(str(active["resolved_skill_file"])).resolve()
    source_root = Path(str(active["resolved_source_root"])).resolve()
    source_rejection = skill_source_rejection_reason(active)
    if source_rejection is not None:
        return {**rejected, "reason": source_rejection}
    result = {
        "valid": True, "reason": "ok", "skill_id": identity,
        "canonical_entrypoint": str(descriptor), "skill_entrypoint": str(descriptor),
        "skill_root": str(descriptor.parent), "source_root": str(source_root),
        "source_kind": active["source_kind"], "source_priority": active["source_priority"],
        "active": True, "duplicate_state": "active", "enabled": True,
        "description": active["description"], "content_sha256": active["content_sha256"],
    }
    if not skill_entrypoint and require_provided_entrypoint:
        return {**result, "valid": False, "reason": "missing_skill_entrypoint"}
    if skill_entrypoint and Path(skill_entrypoint).resolve() != descriptor:
        return {**result, "valid": False, "reason": "entrypoint_mismatch", "provided_entrypoint": str(Path(skill_entrypoint).resolve())}
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only local Skill source authority")
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--agent-root", type=Path, required=True)
    parser.add_argument("--host-id", required=True)
    parser.add_argument("--workspace-root", type=Path)
    parser.add_argument("--skill-id")
    parser.add_argument("--skill-entrypoint")
    parser.add_argument("--require-provided-entrypoint", action="store_true")
    args = parser.parse_args(argv)
    roots = dict(repo_root=args.repo_root, agent_root=args.agent_root, host_id=args.host_id, workspace_root=args.workspace_root)
    try:
        payload = (
            {"skill_roots": skill_root_projection(**roots)} if args.skill_id is None else
            resolve_skill_authority(
                **roots, skill_id=args.skill_id, skill_entrypoint=args.skill_entrypoint,
                require_provided_entrypoint=args.require_provided_entrypoint,
            )
        )
    except (OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=True))
        return 1
    print(json.dumps(payload, ensure_ascii=True))
    return 0
