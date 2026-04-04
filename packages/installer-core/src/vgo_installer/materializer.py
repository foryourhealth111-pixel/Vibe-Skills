from __future__ import annotations

from collections.abc import Callable, Iterable
import json
from pathlib import Path
import shutil
import stat
import tempfile
from typing import Any

from ._bootstrap import ensure_contracts_src_on_path

ensure_contracts_src_on_path()

from vgo_contracts.runtime_surface_contract import (
    is_ignored_runtime_artifact,
    resolve_packaging_contract,
    uses_skill_only_activation,
)
from vgo_contracts.mirror_topology_contract import (
    resolve_canonical_mirror_relpath,
    resolve_generated_nested_compatibility_suffix,
)

from .ledger_service import MaterializationLedgerState

TrackCreatedPath = Callable[[Path | str], None]
RecordOwnedTreeRoot = Callable[[Path | str], None]
RecordGeneratedFromTemplate = Callable[[Path], None]
RecordManagedJson = Callable[[Path], None]


def empty_materialization_state() -> MaterializationLedgerState:
    return MaterializationLedgerState()


def _noop_path(_: Path | str) -> None:
    return


def _noop_file(_: Path) -> None:
    return


def is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def same_path(left: Path, right: Path) -> bool:
    return left.resolve() == right.resolve()


def _filtered_directory_children(src: Path) -> list[Path]:
    children: list[Path] = []
    for child in sorted(src.iterdir(), key=lambda item: item.name):
        if is_ignored_runtime_artifact(Path(child.name)):
            continue
        children.append(child)
    return children


def _copytree_runtime_filtered(src: Path, dst: Path) -> None:
    def _ignore(dirpath: str, names: list[str]) -> set[str]:
        base = Path(dirpath)
        ignored: set[str] = set()
        for name in names:
            candidate = base / name
            if is_ignored_runtime_artifact(candidate.relative_to(src)):
                ignored.add(name)
        return ignored

    shutil.copytree(src, dst, ignore=_ignore)


def copy_dir_replace(
    src: Path,
    dst: Path,
    *,
    track_created_path: TrackCreatedPath = _noop_path,
    record_owned_tree_root: RecordOwnedTreeRoot = _noop_path,
) -> None:
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
        _copytree_runtime_filtered(src, dst)
        track_created_path(dst)
        record_owned_tree_root(dst)
        return

    stage_root = Path(tempfile.mkdtemp(prefix="vgo-copy-tree-"))
    try:
        staged = stage_root / src.name
        _copytree_runtime_filtered(src, staged)
        if dst.exists():
            shutil.rmtree(dst)
        _copytree_runtime_filtered(staged, dst)
        track_created_path(dst)
        record_owned_tree_root(dst)
    finally:
        shutil.rmtree(stage_root, ignore_errors=True)


def copy_file(src: Path, dst: Path, *, track_created_path: TrackCreatedPath = _noop_path) -> None:
    if src.exists() and dst.exists() and same_path(src, dst):
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    track_created_path(dst)


def copy_tree(
    src: Path,
    dst: Path,
    *,
    track_created_path: TrackCreatedPath = _noop_path,
    record_owned_tree_root: RecordOwnedTreeRoot = _noop_path,
) -> None:
    if not src.exists():
        return
    children = _filtered_directory_children(src)
    dst.mkdir(parents=True, exist_ok=True)
    track_created_path(dst)
    for child in children:
        target = dst / child.name
        if child.is_dir():
            copy_dir_replace(
                child,
                target,
                track_created_path=track_created_path,
                record_owned_tree_root=record_owned_tree_root,
            )
        else:
            copy_file(child, target, track_created_path=track_created_path)


def copy_skill_roots_without_self_shadow(
    src: Path,
    dst: Path,
    repo_root: Path,
    excluded_skill_names: set[str] | None = None,
    *,
    track_created_path: TrackCreatedPath = _noop_path,
    record_owned_tree_root: RecordOwnedTreeRoot = _noop_path,
) -> None:
    if not src.exists():
        return
    dst.mkdir(parents=True, exist_ok=True)
    track_created_path(dst)
    for child in sorted(src.iterdir(), key=lambda item: item.name):
        if excluded_skill_names and child.name in excluded_skill_names:
            continue
        target = dst / child.name
        if same_path(target, repo_root):
            continue
        if child.is_dir():
            copy_dir_replace(
                child,
                target,
                track_created_path=track_created_path,
                record_owned_tree_root=record_owned_tree_root,
            )
        else:
            copy_file(child, target, track_created_path=track_created_path)


def ensure_executable(path: Path) -> None:
    current = path.stat().st_mode
    path.chmod(current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def restore_skill_entrypoint_if_needed(skill_root: Path) -> None:
    skill_md = skill_root / "SKILL.md"
    mirror_md = skill_root / "SKILL.runtime-mirror.md"
    if skill_md.exists() or not mirror_md.exists():
        return
    mirror_md.rename(skill_md)


def sanitize_skill_entrypoint_for_runtime_mirror(skill_root: Path) -> None:
    skill_md = skill_root / "SKILL.md"
    mirror_md = skill_root / "SKILL.runtime-mirror.md"
    if mirror_md.exists():
        if skill_md.exists():
            skill_md.unlink()
        return
    if skill_md.exists():
        skill_md.rename(mirror_md)


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as fh:
        return json.load(fh)


def sync_vibe_canonical(
    repo_root: Path,
    target_root: Path,
    target_rel: str,
    *,
    copy_file_fn: Callable[[Path, Path], None],
    copy_dir_replace_fn: Callable[[Path, Path], None],
) -> None:
    governance = _load_json(repo_root / "config" / "version-governance.json")
    packaging = resolve_packaging_contract(governance, repo_root)
    canonical_root = (repo_root / resolve_canonical_mirror_relpath(governance)).resolve()
    target_vibe_root = target_root / target_rel
    if same_path(canonical_root, target_vibe_root):
        return
    if target_vibe_root.exists():
        shutil.rmtree(target_vibe_root)
    for rel in packaging["mirror"]["files"]:
        src = canonical_root / rel
        if src.exists():
            copy_file_fn(src, target_vibe_root / rel)
    for rel in packaging["mirror"]["directories"]:
        src = canonical_root / rel
        if src.exists():
            copy_dir_replace_fn(src, target_vibe_root / rel)


def generated_nested_compatibility_suffix(governance: dict[str, Any]) -> Path | None:
    return resolve_generated_nested_compatibility_suffix(governance)


def materialize_generated_nested_compatibility(
    governance: dict[str, Any],
    installed_root: Path,
    managed_skill_names: set[str] | None = None,
    *,
    copy_file_fn: Callable[[Path, Path], None],
    copy_dir_replace_fn: Callable[[Path, Path], None],
) -> None:
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
        copy_dir_replace_fn(skill_dir, destination)
        sanitize_skill_entrypoint_for_runtime_mirror(destination)

    packaging = resolve_packaging_contract(governance, installed_root)
    for rel in packaging["mirror"]["files"]:
        src = installed_root / rel
        if src.exists():
            copy_file_fn(src, nested_root / rel)
    for rel in packaging["mirror"]["directories"]:
        src = installed_root / rel
        if src.exists():
            copy_dir_replace_fn(src, nested_root / rel)
    sanitize_skill_entrypoint_for_runtime_mirror(nested_root)


def canonical_vibe_target_relpath(packaging: dict[str, Any]) -> str:
    return str(
        packaging.get("canonical_vibe_payload", {}).get("target_relpath")
        or packaging.get("canonical_vibe_mirror", {}).get("target_relpath")
        or "skills/vibe"
    )


def excluded_bundled_skill_names(packaging: dict[str, Any]) -> set[str]:
    configured = {
        str(name).strip()
        for name in packaging.get("exclude_bundled_skill_names") or []
        if str(name).strip()
    }
    configured.add(Path(canonical_vibe_target_relpath(packaging)).name)
    return configured


def resolve_bundled_skills_root(repo_root: Path, packaging: dict[str, Any]) -> Path:
    source_rel = str(packaging.get("bundled_skills_source") or "bundled/skills")
    candidates: list[Path] = []

    skill_source_root = str(packaging.get("skill_source_root") or "").strip()
    if skill_source_root:
        candidates.append(Path(skill_source_root).expanduser())

    catalog_root = str(packaging.get("catalog_root") or "").strip()
    if catalog_root:
        candidates.append(Path(catalog_root).expanduser() / "skills")

    parent = repo_root.parent
    if parent.name == "skills":
        candidates.append(parent)
    candidates.append(repo_root / source_rel)

    seen: list[Path] = []
    for candidate in candidates:
        resolved = candidate.resolve() if candidate.exists() else candidate
        if resolved in seen:
            continue
        seen.append(resolved)
        if candidate.exists():
            return candidate

    return Path(skill_source_root).expanduser() if skill_source_root else repo_root / source_rel


def materialize_allowlisted_skills(
    repo_root: Path,
    target_root: Path,
    packaging: dict[str, Any],
    *,
    copy_dir_replace_fn: Callable[[Path, Path], None],
) -> None:
    skills_allowlist = list(packaging.get("skills_allowlist") or [])
    if not skills_allowlist:
        return

    bundled_root = resolve_bundled_skills_root(repo_root, packaging)
    if not bundled_root.exists():
        raise SystemExit(f"Bundled skills source missing for allowlisted packaging: {bundled_root}")

    canonical_vibe_rel = canonical_vibe_target_relpath(packaging)
    canonical_vibe_name = Path(canonical_vibe_rel).name
    for name in sorted({str(value).strip() for value in skills_allowlist if str(value).strip()}):
        if name == canonical_vibe_name:
            continue
        source = bundled_root / name
        if not source.exists():
            raise SystemExit(f"Allowlisted skill packaging source missing: {source}")
        destination = target_root / "skills" / name
        copy_dir_replace_fn(source, destination)
        restore_skill_entrypoint_if_needed(destination)


def ensure_skill_present(
    target_root: Path,
    name: str,
    required: bool,
    allow_fallback: bool,
    fallback_sources: Iterable[Path],
    external_used: set[str],
    missing: set[str],
    *,
    copy_tree_fn: Callable[[Path, Path], None],
) -> None:
    skill_md = target_root / "skills" / name / "SKILL.md"
    if skill_md.exists():
        return
    if allow_fallback:
        for src_path in fallback_sources:
            if src_path.exists():
                destination = target_root / "skills" / name
                copy_tree_fn(src_path, destination)
                restore_skill_entrypoint_if_needed(destination)
                external_used.add(name)
                break
    if required and not skill_md.exists():
        missing.add(name)


def install_codex_payload(
    repo_root: Path,
    target_root: Path,
    *,
    copy_tree_fn: Callable[[Path, Path], None],
    copy_file_fn: Callable[[Path, Path], None],
    track_created_path: TrackCreatedPath,
    record_generated_from_template: RecordGeneratedFromTemplate,
    record_managed_json: RecordManagedJson,
) -> None:
    copy_tree_fn(repo_root / "rules", target_root / "rules")
    track_created_path(target_root / "rules")
    copy_tree_fn(repo_root / "agents" / "templates", target_root / "agents" / "templates")
    track_created_path(target_root / "agents" / "templates")
    copy_tree_fn(repo_root / "mcp", target_root / "mcp")
    track_created_path(target_root / "mcp")
    (target_root / "config").mkdir(parents=True, exist_ok=True)
    track_created_path(target_root / "config")
    copy_file_fn(repo_root / "config" / "plugins-manifest.codex.json", target_root / "config" / "plugins-manifest.codex.json")
    settings_path = target_root / "settings.json"
    if not settings_path.exists():
        copy_file_fn(repo_root / "config" / "settings.template.codex.json", settings_path)
        record_generated_from_template(settings_path)
    track_created_path(settings_path)
    record_managed_json(settings_path)


def install_opencode_guidance_payload(
    repo_root: Path,
    target_root: Path,
    *,
    copy_file_fn: Callable[[Path, Path], None],
) -> None:
    example_config = repo_root / "config" / "opencode" / "opencode.json.example"
    if example_config.exists():
        copy_file_fn(example_config, target_root / "opencode.json.example")


def install_runtime_core_mode_payload(
    repo_root: Path,
    target_root: Path,
    adapter: dict[str, Any],
    *,
    copy_tree_fn: Callable[[Path, Path], None],
    copy_file_fn: Callable[[Path, Path], None],
    track_created_path: TrackCreatedPath,
    record_generated_from_template: RecordGeneratedFromTemplate,
) -> None:
    if uses_skill_only_activation(adapter["id"]):
        return
    commands_root = repo_root / "commands"
    if commands_root.exists():
        copy_tree_fn(commands_root, target_root / "global_workflows")
        track_created_path(target_root / "global_workflows")

    mcp_template = repo_root / "mcp" / "servers.template.json"
    mcp_config = target_root / "mcp_config.json"
    if mcp_template.exists() and not mcp_config.exists():
        copy_file_fn(mcp_template, mcp_config)
        record_generated_from_template(mcp_config)
    track_created_path(mcp_config)
