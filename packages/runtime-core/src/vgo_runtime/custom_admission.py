from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .router_contract_support import RepoContext, resolve_skill_md_path


STANDARD_TASK_TYPES = ("planning", "coding", "review", "debug", "research")
PREFERRED_STAGE_TO_DISPATCH_PHASE = {
    "skeleton_check": "pre_execution",
    "deep_interview": "pre_execution",
    "requirement_doc": "pre_execution",
    "xl_plan": "pre_execution",
    "plan_execute": "in_execution",
    "phase_cleanup": "post_execution",
    "pre_execution": "pre_execution",
    "in_execution": "in_execution",
    "post_execution": "post_execution",
    "verification": "verification",
}


def _normalize_text(value: Any) -> str:
    return str(value or "").strip().casefold()


def _normalize_list(values: list[Any] | None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        token = _normalize_text(value)
        if not token or token in seen:
            continue
        normalized.append(token)
        seen.add(token)
    return normalized


def _load_optional_json(path: Path) -> tuple[Any | None, str | None]:
    if not path.exists():
        return None, None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig")), None
    except Exception as exc:  # pragma: no cover - defensive path
        return None, str(exc)


def _path_within(base: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def _resolve_skill_md(path: Path) -> Path:
    return path / "SKILL.md" if path.suffix.lower() != ".md" else path


def _read_skill_description(skill_md_path: Path | None) -> str | None:
    if skill_md_path is None or not skill_md_path.exists():
        return None
    lines = skill_md_path.read_text(encoding="utf-8-sig").splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:20]:
        stripped = line.strip()
        if stripped == "---":
            break
        if stripped.lower().startswith("description:"):
            return stripped.split(":", 1)[1].strip()
    return None


def _resolve_dependency_path(repo_root: Path, target_root: Path, skill_id: str) -> Path | None:
    repo = RepoContext(
        repo_root=repo_root,
        config_root=repo_root / "config",
        bundled_skills_root=repo_root / "bundled" / "skills",
    )
    return resolve_skill_md_path(repo, skill_id, str(target_root))


def _derive_task_allow(entry: dict[str, Any]) -> list[str]:
    explicit = _normalize_list(entry.get("task_allow"))
    if explicit:
        return [item for item in explicit if item in STANDARD_TASK_TYPES] or list(STANDARD_TASK_TYPES)

    intent_tags = set(_normalize_list(entry.get("intent_tags")))
    task_allow = [task for task in STANDARD_TASK_TYPES if task in intent_tags]
    return task_allow or list(STANDARD_TASK_TYPES)


def _derive_dispatch_phase(preferred_stages: list[str]) -> str:
    for stage in preferred_stages:
        phase = PREFERRED_STAGE_TO_DISPATCH_PHASE.get(stage)
        if phase:
            return phase
    return "in_execution"


def _route_authority_eligible(trigger_mode: str, requested_canonical: str | None, skill_id: str) -> bool:
    if trigger_mode == "auto":
        return True
    if requested_canonical and _normalize_text(requested_canonical) == _normalize_text(skill_id):
        return True
    return False


def _build_admitted_candidate(
    *,
    manifest_kind: str,
    entry: dict[str, Any],
    target_root: Path,
    repo_root: Path,
    requested_canonical: str | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    skill_id = _normalize_text(entry.get("id"))
    relative_path = str(entry.get("path") or "").strip()
    keywords = _normalize_list(entry.get("keywords"))
    intent_tags = _normalize_list(entry.get("intent_tags"))
    non_goals = _normalize_list(entry.get("non_goals"))
    requires = _normalize_list(entry.get("requires"))
    preferred_stages = _normalize_list(entry.get("preferred_stages"))

    missing_fields = [
        field
        for field, value in (
            ("id", skill_id),
            ("path", relative_path),
            ("keywords", keywords),
            ("intent_tags", intent_tags),
            ("non_goals", non_goals),
            ("requires", requires),
        )
        if not value
    ]
    if missing_fields:
        return None, {
            "manifest_kind": manifest_kind,
            "entry_id": skill_id or None,
            "reason": "missing_required_fields",
            "missing_fields": missing_fields,
        }

    raw_path = (target_root / relative_path).resolve()
    if not _path_within(target_root, raw_path):
        return None, {
            "manifest_kind": manifest_kind,
            "entry_id": skill_id,
            "reason": "path_outside_target_root",
            "path": relative_path,
        }

    skill_md_path = _resolve_skill_md(raw_path)
    if not skill_md_path.exists():
        return None, {
            "manifest_kind": manifest_kind,
            "entry_id": skill_id,
            "reason": "skill_md_missing",
            "path": relative_path,
            "skill_md_path": str(skill_md_path),
        }

    missing_dependencies = [dependency for dependency in requires if _resolve_dependency_path(repo_root, target_root, dependency) is None]
    if missing_dependencies:
        return None, {
            "manifest_kind": manifest_kind,
            "entry_id": skill_id,
            "reason": "custom_dependencies_missing",
            "missing_dependencies": missing_dependencies,
        }

    trigger_mode = _normalize_text(entry.get("trigger_mode")) or "advisory"
    if trigger_mode not in {"explicit_only", "advisory", "auto"}:
        trigger_mode = "advisory"

    priority = entry.get("priority")
    try:
        normalized_priority = max(0, min(89, int(priority if priority is not None else 60)))
    except (TypeError, ValueError):
        normalized_priority = 60

    task_allow = _derive_task_allow(entry)
    dispatch_phase = _derive_dispatch_phase(preferred_stages)
    description = _read_skill_description(skill_md_path)
    admitted = {
        "skill_id": skill_id,
        "manifest_kind": manifest_kind,
        "pack_id": f"custom-{manifest_kind}-{skill_id}",
        "path": relative_path,
        "skill_md_path": str(skill_md_path),
        "description": description,
        "enabled": bool(entry.get("enabled", True)),
        "trigger_mode": trigger_mode,
        "priority": normalized_priority,
        "keywords": keywords,
        "intent_tags": intent_tags,
        "non_goals": non_goals,
        "requires": requires,
        "task_allow": task_allow,
        "preferred_stages": preferred_stages,
        "dispatch_phase": dispatch_phase,
        "binding_profile": manifest_kind,
        "lane_policy": "bounded_native_custom_skill",
        "parallelizable_in_root_xl": bool(entry.get("parallelizable_in_root_xl", False)),
        "native_usage_required": True,
        "must_preserve_workflow": True,
        "route_authority_eligible": _route_authority_eligible(trigger_mode, requested_canonical, skill_id),
    }
    custom_summary = {
        "skill_id": admitted["skill_id"],
        "manifest_kind": admitted["manifest_kind"],
        "pack_id": admitted["pack_id"],
        "trigger_mode": admitted["trigger_mode"],
        "dispatch_phase": admitted["dispatch_phase"],
        "binding_profile": admitted["binding_profile"],
        "lane_policy": admitted["lane_policy"],
        "parallelizable_in_root_xl": admitted["parallelizable_in_root_xl"],
        "native_usage_required": admitted["native_usage_required"],
        "must_preserve_workflow": admitted["must_preserve_workflow"],
        "route_authority_eligible": admitted["route_authority_eligible"],
        "skill_md_path": admitted["skill_md_path"],
        "description": admitted["description"],
    }
    admitted["pack"] = {
        "id": admitted["pack_id"],
        "priority": admitted["priority"],
        "grade_allow": ["M", "L", "XL"],
        "task_allow": task_allow,
        "trigger_keywords": keywords,
        "skill_candidates": [skill_id],
        "defaults_by_task": {task: skill_id for task in task_allow},
        "custom_admission": custom_summary,
    }
    return admitted, None


def load_custom_admission(
    *,
    repo_root: Path,
    target_root: Path | None,
    requested_canonical: str | None,
) -> dict[str, Any]:
    resolved_target_root = target_root.resolve() if target_root else None
    result: dict[str, Any] = {
        "enabled": resolved_target_root is not None,
        "target_root": str(resolved_target_root) if resolved_target_root else None,
        "manifest_paths": {},
        "manifests_present": {},
        "invalid_entries": [],
        "dependency_failures": [],
        "admitted_candidates": [],
        "admitted_packs": [],
        "skill_index": {},
    }
    if resolved_target_root is None:
        result["status"] = "target_root_unavailable"
        return result

    manifests = [
        ("workflow", resolved_target_root / "config" / "custom-workflows.json", "workflows"),
        ("skill", resolved_target_root / "config" / "custom-skills.json", "skills"),
    ]

    for manifest_kind, manifest_path, top_level_key in manifests:
        result["manifest_paths"][manifest_kind] = str(manifest_path)
        data, error = _load_optional_json(manifest_path)
        result["manifests_present"][manifest_kind] = manifest_path.exists()
        if error:
            result["invalid_entries"].append(
                {
                    "manifest_kind": manifest_kind,
                    "entry_id": None,
                    "reason": "manifest_parse_error",
                    "message": error,
                }
            )
            continue
        if data is None:
            continue

        rows = data.get(top_level_key)
        if not isinstance(rows, list):
            result["invalid_entries"].append(
                {
                    "manifest_kind": manifest_kind,
                    "entry_id": None,
                    "reason": "manifest_missing_collection",
                    "expected_key": top_level_key,
                }
            )
            continue

        for entry in rows:
            if not isinstance(entry, dict) or not entry.get("enabled", True):
                continue
            admitted, failure = _build_admitted_candidate(
                manifest_kind=manifest_kind,
                entry=entry,
                target_root=resolved_target_root,
                repo_root=repo_root,
                requested_canonical=requested_canonical,
            )
            if failure:
                if failure["reason"] == "custom_dependencies_missing":
                    result["dependency_failures"].append(failure)
                else:
                    result["invalid_entries"].append(failure)
                continue
            if admitted is None:
                continue
            result["admitted_candidates"].append(admitted)
            result["admitted_packs"].append(admitted["pack"])
            result["skill_index"][admitted["skill_id"]] = admitted

    if result["invalid_entries"]:
        result["status"] = "custom_manifest_invalid"
    elif result["dependency_failures"]:
        result["status"] = "custom_dependencies_missing"
    elif result["admitted_candidates"]:
        result["status"] = "admitted"
    else:
        result["status"] = "no_custom_manifests"
    return result
