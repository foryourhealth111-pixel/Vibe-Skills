#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import uuid
from pathlib import Path

COMMON_DIR = Path(__file__).resolve().parents[1] / "common"
if str(COMMON_DIR) not in sys.path:
    sys.path.insert(0, str(COMMON_DIR))

from runtime_contracts import uses_skill_only_activation


def load_json(path: Path):
    with path.open("r", encoding="utf-8-sig") as fh:
        return json.load(fh)


def write_json(data: object):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def write_json_file(path: Path, data: object):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_relpath(value: str | Path | None) -> str | None:
    if value is None:
        return None
    text = str(value).replace("\\", "/").strip()
    if not text:
        return None
    normalized = Path(text).as_posix().lstrip("./")
    if normalized == ".":
        return None
    return normalized


def relativize_to_target(value: str | Path | None, target_root: Path) -> str | None:
    if value is None:
        return None
    candidate = Path(str(value))
    if candidate.is_absolute():
        try:
            relative = candidate.resolve().relative_to(target_root.resolve()).as_posix()
            return None if relative == "." else relative
        except ValueError:
            return None
    return normalize_relpath(candidate)


def is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def collect_file_inventory(source_root: Path, target_prefix: str) -> set[str]:
    inventory: set[str] = set()
    if not source_root.exists():
        return inventory
    if source_root.is_file():
        normalized = normalize_relpath(target_prefix)
        if normalized:
            inventory.add(normalized)
        return inventory
    for candidate in source_root.rglob("*"):
        if candidate.is_file() or candidate.is_symlink():
            rel = candidate.relative_to(source_root).as_posix()
            inventory.add(f"{normalize_relpath(target_prefix)}/{rel}")
    return inventory


def load_adapter_resolver(repo_root: Path):
    import importlib.util
    import sys

    module_path = repo_root / "scripts" / "common" / "resolve_vgo_adapter.py"
    spec = importlib.util.spec_from_file_location("vgo_resolve_adapter", module_path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Unable to load adapter resolver: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def resolve_adapter(repo_root: Path, host_id: str):
    resolver = load_adapter_resolver(repo_root)
    return resolver.resolve_adapter(repo_root, host_id)


def generated_nested_compatibility_suffix(governance: dict) -> Path | None:
    packaging = governance.get("packaging") or {}
    generated = packaging.get("generated_compatibility") or {}
    nested_runtime = generated.get("nested_runtime_root") or {}
    relative_path = str(nested_runtime.get("relative_path") or "").strip()
    materialization_mode = str(nested_runtime.get("materialization_mode") or "").strip()
    if relative_path:
        if not materialization_mode:
            materialization_mode = "install_only"
        if materialization_mode not in {"install_only", "release_install_only"}:
            return None
        return Path(*relative_path.replace("\\", "/").strip("/").split("/"))

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


def runtime_core_inventory(repo_root: Path) -> set[str]:
    packaging = load_json(repo_root / "config" / "runtime-core-packaging.json")
    governance = load_json(repo_root / "config" / "version-governance.json")
    inventory: set[str] = set()
    exclude_bundled_skill_names = {
        str(name).strip()
        for name in packaging.get("exclude_bundled_skill_names") or []
        if str(name).strip()
    }

    for entry in packaging.get("copy_directories", []):
        source_root = repo_root / entry["source"]
        target_prefix = normalize_relpath(entry["target"])
        if target_prefix == "skills" and source_root.exists() and exclude_bundled_skill_names:
            for candidate in source_root.iterdir():
                if candidate.name in exclude_bundled_skill_names:
                    continue
                inventory.update(collect_file_inventory(candidate, f"{target_prefix}/{candidate.name}"))
            continue
        inventory.update(collect_file_inventory(source_root, entry["target"]))
    for entry in packaging.get("copy_files", []):
        inventory.add(normalize_relpath(entry["target"]))

    target_rel = normalize_relpath(
        (packaging.get("canonical_vibe_payload") or {}).get("target_relpath")
        or (packaging.get("canonical_vibe_mirror") or {}).get("target_relpath")
        or "skills/vibe"
    ) or "skills/vibe"
    runtime_payload = (governance.get("packaging") or {}).get("runtime_payload") or (governance.get("packaging") or {}).get("mirror") or {}
    for rel in runtime_payload.get("files", []):
        inventory.add(f"{target_rel}/{normalize_relpath(rel)}")
    for rel in runtime_payload.get("directories", []):
        inventory.update(collect_file_inventory(repo_root / rel, f"{target_rel}/{normalize_relpath(rel)}"))

    nested_suffix = generated_nested_compatibility_suffix(governance)
    if nested_suffix is not None:
        nested_root = f"{target_rel}/{nested_suffix.as_posix()}"
        for rel in runtime_payload.get("files", []):
            inventory.add(f"{nested_root}/{normalize_relpath(rel)}")
        for rel in runtime_payload.get("directories", []):
            inventory.update(collect_file_inventory(repo_root / rel, f"{nested_root}/{normalize_relpath(rel)}"))

    return {entry for entry in inventory if entry}


def host_inventory(repo_root: Path, host_id: str) -> set[str]:
    inventory = runtime_core_inventory(repo_root)
    if host_id == "codex":
        inventory.update(collect_file_inventory(repo_root / "rules", "rules"))
        inventory.update(collect_file_inventory(repo_root / "agents" / "templates", "agents/templates"))
        inventory.update(collect_file_inventory(repo_root / "mcp", "mcp"))
        inventory.add("config/plugins-manifest.codex.json")
    elif host_id == "opencode":
        inventory.update(collect_file_inventory(repo_root / "config" / "opencode" / "commands", "commands"))
        inventory.update(collect_file_inventory(repo_root / "config" / "opencode" / "commands", "command"))
        inventory.update(collect_file_inventory(repo_root / "config" / "opencode" / "agents", "agents"))
        inventory.update(collect_file_inventory(repo_root / "config" / "opencode" / "agents", "agent"))
        inventory.add("opencode.json.example")
    elif host_id in {"windsurf", "openclaw"}:
        inventory.update(collect_file_inventory(repo_root / "commands", "global_workflows"))
    if uses_skill_only_activation(host_id):
        inventory.add(".vibeskills/host-settings.json")
        inventory.add(".vibeskills/host-closure.json")
    return {entry for entry in inventory if entry}


def path_matches_template(path: Path, template_path: Path) -> bool:
    if not path.exists() or not template_path.exists():
        return False
    return path.read_text(encoding="utf-8") == template_path.read_text(encoding="utf-8")


def parse_path_list(values: object, target_root: Path) -> set[str]:
    result: set[str] = set()
    if not isinstance(values, list):
        return result
    for entry in values:
        normalized = None
        if isinstance(entry, dict):
            normalized = relativize_to_target(entry.get("path"), target_root)
        else:
            normalized = relativize_to_target(entry, target_root)
        if normalized:
            result.add(normalized)
    return result


def parse_managed_json_paths(values: object, target_root: Path) -> dict[str, dict[str, object]]:
    managed: dict[str, dict[str, object]] = {}
    if not isinstance(values, list):
        return managed
    for entry in values:
        if isinstance(entry, str):
            rel = relativize_to_target(entry, target_root)
            if rel:
                managed[rel] = {"managed_key": "vibeskills", "created_if_absent": False}
            continue
        if not isinstance(entry, dict):
            continue
        rel = relativize_to_target(entry.get("path"), target_root)
        if rel:
            managed[rel] = {
                "managed_key": entry.get("managed_key", "vibeskills"),
                "created_if_absent": bool(entry.get("created_if_absent", False)),
            }
    return managed


def parse_managed_skill_names(ledger: object) -> set[str]:
    if not isinstance(ledger, dict):
        return set()

    return {
        str(name).strip()
        for key in ("managed_skill_names", "managed_runtime_skill_names", "managed_catalog_skill_names")
        for name in ledger.get(key) or []
        if str(name).strip() and "/" not in str(name) and "\\" not in str(name) and str(name).strip() not in {".", ".."}
    }


def parse_merged_files(values: object, target_root: Path) -> dict[str, dict[str, object]]:
    merged: dict[str, dict[str, object]] = {}
    if not isinstance(values, list):
        return merged
    for entry in values:
        if isinstance(entry, str):
            rel = relativize_to_target(entry, target_root)
            if rel:
                merged[rel] = {"created_if_absent": False}
            continue
        if not isinstance(entry, dict):
            continue
        rel = relativize_to_target(entry.get("path"), target_root)
        if rel:
            merged[rel] = {"created_if_absent": bool(entry.get("created_if_absent", False))}
    return merged


def remove_vibeskills_node(
    path: Path,
    *,
    allow_delete_empty: bool,
    relpath: str,
    warnings: list[str],
    mutated_json_paths: list[str],
    deleted_paths: list[str],
    preview: bool,
) -> None:
    if not path.exists():
        return
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        warnings.append(f"shared JSON parse failed: {relpath}")
        return
    if not isinstance(payload, dict) or "vibeskills" not in payload:
        return

    next_payload = dict(payload)
    del next_payload["vibeskills"]
    mutated_json_paths.append(relpath)

    if not preview:
        if not next_payload and allow_delete_empty:
            path.unlink()
            deleted_paths.append(relpath)
            return
        write_json_file(path, next_payload)


def collect_foreign_paths(
    target_root: Path,
    managed_files: set[str],
    deleted_dirs: set[str],
    protected_relpaths: set[str],
) -> list[str]:
    top_level_roots = {entry.split("/", 1)[0] for entry in managed_files | deleted_dirs}
    foreign: set[str] = set()

    for root_name in sorted(top_level_roots):
        root_path = target_root / root_name
        if not root_path.exists() or not root_path.is_dir():
            continue
        for candidate in root_path.rglob("*"):
            if not candidate.is_file() and not candidate.is_symlink():
                continue
            rel = candidate.relative_to(target_root).as_posix()
            if rel in managed_files or rel in protected_relpaths:
                continue
            if any(rel == entry or rel.startswith(f"{entry}/") for entry in deleted_dirs):
                continue
            foreign.add(rel)
    return sorted(foreign)


def purge_empty_dirs(target_root: Path) -> list[str]:
    removed: list[str] = []
    if not target_root.exists():
        return removed
    for candidate in sorted((path for path in target_root.rglob("*") if path.is_dir()), key=lambda item: len(item.parts), reverse=True):
        if candidate == target_root:
            continue
        try:
            next(candidate.iterdir())
        except StopIteration:
            candidate.rmdir()
            removed.append(candidate.relative_to(target_root).as_posix())
    return removed


def plan_uninstall(repo_root: Path, target_root: Path, adapter: dict) -> dict[str, object]:
    host_id = adapter["id"]
    managed_files = host_inventory(repo_root, host_id)
    deleted_dirs: set[str] = set()
    protected_relpaths: set[str] = set()
    warnings: list[str] = []
    ownership_source: list[str] = []

    ledger_path = target_root / ".vibeskills" / "install-ledger.json"
    ledger = load_json(ledger_path) if ledger_path.exists() else None
    if ledger is not None:
        ownership_source.append("ledger")
        for rel in sorted(parse_path_list(ledger.get("created_paths"), target_root)):
            candidate = target_root / rel
            if rel == ".vibeskills" and candidate.exists():
                deleted_dirs.add(rel)
                continue
            if candidate.exists() and candidate.is_dir() and not candidate.is_symlink():
                normalized_rel = rel.replace("\\", "/")
                if normalized_rel.startswith("skills/") and len([part for part in normalized_rel.split("/") if part]) == 2:
                    deleted_dirs.add(rel)
                continue
            managed_files.add(rel)
        for name in sorted(parse_managed_skill_names(ledger)):
            skill_rel = f"skills/{name}"
            candidate = target_root / skill_rel
            if candidate.exists() and candidate.is_dir() and not candidate.is_symlink():
                deleted_dirs.add(skill_rel)
        for rel in sorted(parse_path_list(ledger.get("specialist_wrapper_paths"), target_root)):
            candidate = target_root / rel
            if candidate.exists() and candidate.is_dir() and not candidate.is_symlink():
                continue
            managed_files.add(rel)
        protected_relpaths.update(parse_path_list(ledger.get("generated_from_template_if_absent"), target_root))

    closure_path = target_root / ".vibeskills" / "host-closure.json"
    closure = load_json(closure_path) if closure_path.exists() else None
    if closure is not None:
        ownership_source.append("host-closure")

    if ownership_source and (target_root / ".vibeskills").exists():
        deleted_dirs.add(".vibeskills")

    if not ownership_source:
        ownership_source.append("legacy")

    template_candidates: list[str] = []
    if host_id == "codex":
        settings_template = repo_root / "config" / "settings.template.codex.json"
        if path_matches_template(target_root / "settings.json", settings_template):
            template_candidates.append("settings.json")
    if host_id in {"windsurf", "openclaw"}:
        mcp_template = repo_root / "mcp" / "servers.template.json"
        if path_matches_template(target_root / "mcp_config.json", mcp_template):
            template_candidates.append("mcp_config.json")

    managed_json_paths = parse_managed_json_paths(ledger.get("managed_json_paths") if isinstance(ledger, dict) else None, target_root)
    merged_files = parse_merged_files(ledger.get("merged_files") if isinstance(ledger, dict) else None, target_root)

    return {
        "managed_files": {entry for entry in managed_files if entry and not any(entry == deleted or entry.startswith(f"{deleted}/") for deleted in deleted_dirs)},
        "deleted_dirs": deleted_dirs,
        "managed_json_paths": managed_json_paths,
        "merged_files": merged_files,
        "template_candidates": template_candidates,
        "warnings": warnings,
        "ownership_source": ownership_source,
        "protected_relpaths": protected_relpaths,
    }


def apply_uninstall(
    repo_root: Path,
    target_root: Path,
    adapter: dict,
    *,
    preview: bool,
    purge_empty: bool,
) -> dict[str, object]:
    plan = plan_uninstall(repo_root, target_root, adapter)
    deleted_paths: list[str] = []
    mutated_json_paths: list[str] = []
    warnings = list(plan["warnings"])

    managed_files = sorted(plan["managed_files"])
    deleted_dirs = sorted(plan["deleted_dirs"])
    managed_json_paths = dict(plan["managed_json_paths"])
    merged_files = dict(plan["merged_files"])
    protected_relpaths = set(plan["protected_relpaths"])

    for rel in plan["template_candidates"]:
        if rel not in managed_json_paths and (target_root / rel).exists():
            managed_files.append(rel)

    managed_files = sorted(set(managed_files))
    skipped_foreign_paths = collect_foreign_paths(target_root, set(managed_files), set(deleted_dirs), protected_relpaths)

    for rel in managed_files:
        path = target_root / rel
        if not path.exists():
            continue
        if preview:
            deleted_paths.append(rel)
            continue
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()
        deleted_paths.append(rel)

    for rel in deleted_dirs:
        path = target_root / rel
        if not path.exists():
            continue
        if preview:
            deleted_paths.append(rel)
            continue
        shutil.rmtree(path)
        deleted_paths.append(rel)

    for rel, config in managed_json_paths.items():
        created_if_absent = bool(config.get("created_if_absent", False))
        if rel in merged_files:
            created_if_absent = created_if_absent or bool(merged_files[rel].get("created_if_absent", False))
        if rel in protected_relpaths:
            created_if_absent = True
        remove_vibeskills_node(
            target_root / rel,
            allow_delete_empty=created_if_absent,
            relpath=rel,
            warnings=warnings,
            mutated_json_paths=mutated_json_paths,
            deleted_paths=deleted_paths,
            preview=preview,
        )

    empty_dirs_removed: list[str] = []
    if purge_empty and not preview:
        empty_dirs_removed = purge_empty_dirs(target_root)

    run_id = uuid.uuid4().hex
    receipt_path = target_root / "outputs" / "runtime" / "uninstall" / run_id / "uninstall-receipt.json"
    receipt = {
        "schema_version": 1,
        "gate_result": "PASS",
        "host_id": adapter["id"],
        "install_mode": adapter["install_mode"],
        "target_root": str(target_root.resolve()),
        "mode": "preview" if preview else "apply",
        "deleted_paths": deleted_paths,
        "mutated_json_paths": mutated_json_paths,
        "skipped_foreign_paths": skipped_foreign_paths,
        "warnings": warnings,
        "empty_dirs_removed": empty_dirs_removed,
        "ownership_source": plan["ownership_source"],
        "completion_language_allowed": True,
    }
    write_json_file(receipt_path, receipt)

    return {
        **receipt,
        "receipt_path": str(receipt_path.resolve()),
        "preview": preview,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--target-root", required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--profile", choices=("minimal", "full"), default="full")
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--purge-empty-dirs", action="store_true")
    parser.add_argument("--strict-owned-only", action="store_true", default=True)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    target_root = Path(args.target_root).resolve()
    target_root.mkdir(parents=True, exist_ok=True)
    adapter = resolve_adapter(repo_root, args.host)
    payload = apply_uninstall(
        repo_root,
        target_root,
        adapter,
        preview=bool(args.preview),
        purge_empty=bool(args.purge_empty_dirs),
    )
    write_json(payload)


if __name__ == "__main__":
    main()
