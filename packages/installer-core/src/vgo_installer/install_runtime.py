#!/usr/bin/env python3
import argparse
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from ._bootstrap import ensure_contracts_src_on_path, ensure_repo_src_on_path
from ._io import load_json, write_json, write_json_file

ensure_contracts_src_on_path()

from vgo_contracts.canonical_vibe_contract import uses_skill_only_activation

from .adapter_registry import resolve_adapter
from .host_closure import (
    install_claude_managed_settings,
    is_closed_ready_required,
    materialize_host_closure,
)
from .global_instruction_service import materialize_global_instruction_bootstrap
from .install_plan import build_install_plan
from .ledger_service import (
    MaterializationLedgerState,
    derive_managed_skill_names_from_ledger,
    load_existing_install_ledger,
    refresh_install_ledger,
    write_install_ledger,
)
from .materializer import (
    canonical_vibe_target_relpath,
    compatibility_projection_names,
    copy_dir_replace,
    copy_file,
    copy_skill_roots_without_self_shadow,
    copy_tree,
    ensure_skill_present,
    excluded_bundled_skill_names,
    install_codex_payload,
    install_opencode_guidance_payload,
    install_runtime_core_mode_payload,
    materialize_allowlisted_skills,
    materialize_host_visible_wrappers,
    materialize_internal_skill_corpus,
    resolve_bundled_skills_root,
    restore_skill_entrypoint_if_needed,
    sync_vibe_canonical,
)
from .profile_inventory import load_managed_skill_inventory
from .runtime_packaging import resolve_runtime_core_packaging


def attach_local_catalog_descriptor(repo_root: Path, packaging: dict) -> dict:
    catalog_src = ensure_repo_src_on_path(repo_root, "packages/skill-catalog/src")
    if not catalog_src.exists():
        return packaging

    from vgo_catalog.exporter import describe_local_catalog

    descriptor = describe_local_catalog()
    enriched = dict(packaging)
    enriched.setdefault("catalog_owner", str(descriptor.get("owner") or "skill-catalog"))
    enriched.setdefault("catalog_root", str(descriptor.get("catalog_root") or ""))
    enriched.setdefault("profiles_manifest", str(descriptor.get("profiles_manifest") or ""))
    enriched.setdefault("groups_manifest", str(descriptor.get("groups_manifest") or ""))
    enriched.setdefault("metadata_manifest", str(descriptor.get("metadata_manifest") or ""))
    enriched.setdefault("skill_source_root", str(descriptor.get("skill_source_root") or ""))
    return enriched


ledger_state = {
    "created_paths": set(),
    "owned_tree_roots": set(),
    "managed_json_paths": set(),
    "merged_files": {},
    "template_generated": set(),
    "specialist_wrapper_paths": [],
    "bridge_launcher_paths": [],
    "runtime_roots": set(),
    "compatibility_roots": set(),
    "sidecar_roots": set(),
    "config_rollbacks": [],
    "legacy_cleanup_candidates": set(),
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
    record_config_rollback(path, created_if_absent=False)


def record_merged_file(path: Path, *, created_if_absent: bool, managed_block_id: str | None = None) -> None:
    try:
        resolved = path.resolve()
    except FileNotFoundError:
        resolved = path
    entry = {
        "path": str(resolved),
        "created_if_absent": bool(created_if_absent),
    }
    if managed_block_id:
        entry["managed_block_id"] = str(managed_block_id)
    ledger_state["merged_files"][str(resolved)] = entry
    if not managed_block_id:
        record_config_rollback(path, created_if_absent=created_if_absent)


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


def record_bridge_launcher(path: Path) -> None:
    try:
        resolved = str(path.resolve())
    except FileNotFoundError:
        resolved = str(path)
    if resolved not in ledger_state["bridge_launcher_paths"]:
        ledger_state["bridge_launcher_paths"].append(resolved)


def record_runtime_root(path: Path | str) -> None:
    try:
        resolved = Path(path).resolve()
    except FileNotFoundError:
        resolved = Path(path)
    ledger_state["runtime_roots"].add(str(resolved))


def record_compatibility_root(path: Path | str) -> None:
    try:
        resolved = Path(path).resolve()
    except FileNotFoundError:
        resolved = Path(path)
    ledger_state["compatibility_roots"].add(str(resolved))


def record_sidecar_root(path: Path | str) -> None:
    try:
        resolved = Path(path).resolve()
    except FileNotFoundError:
        resolved = Path(path)
    ledger_state["sidecar_roots"].add(str(resolved))


def record_config_rollback(path: Path | str, *, created_if_absent: bool, managed_key: str = "vibeskills") -> None:
    try:
        resolved = Path(path).resolve()
    except FileNotFoundError:
        resolved = Path(path)
    entry = {
        "path": str(resolved),
        "created_if_absent": bool(created_if_absent),
        "managed_key": managed_key,
    }
    if entry not in ledger_state["config_rollbacks"]:
        ledger_state["config_rollbacks"].append(entry)


def record_legacy_cleanup_candidate(path: Path | str) -> None:
    try:
        resolved = Path(path).resolve()
    except FileNotFoundError:
        resolved = Path(path)
    ledger_state["legacy_cleanup_candidates"].add(str(resolved))


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


def materialization_state_from_ledger_state() -> MaterializationLedgerState:
    return MaterializationLedgerState(
        created_paths=set(ledger_state["created_paths"]),
        owned_tree_roots=set(ledger_state["owned_tree_roots"]),
        managed_json_paths=set(ledger_state["managed_json_paths"]),
        merged_files=dict(ledger_state["merged_files"]),
        generated_from_template_if_absent=set(ledger_state["template_generated"]),
        specialist_wrapper_paths=list(ledger_state["specialist_wrapper_paths"]),
        bridge_launcher_paths=list(ledger_state["bridge_launcher_paths"]),
        runtime_roots=set(ledger_state["runtime_roots"]),
        compatibility_roots=set(ledger_state["compatibility_roots"]),
        sidecar_roots=set(ledger_state["sidecar_roots"]),
        config_rollbacks=list(ledger_state["config_rollbacks"]),
        legacy_cleanup_candidates=set(ledger_state["legacy_cleanup_candidates"]),
    )


def desired_managed_skill_names(repo_root: Path, packaging: dict) -> set[str]:
    inventory = load_managed_skill_inventory(packaging)
    managed = set(inventory.desired_managed_skill_names)
    excluded_names = excluded_bundled_skill_names(packaging)

    bundled_root = resolve_bundled_skills_root(repo_root, packaging)
    if bool(packaging.get("copy_bundled_skills")) and bundled_root.exists():
        managed.update(
            candidate.name
            for candidate in bundled_root.iterdir()
            if candidate.is_dir() and candidate.name not in excluded_names
        )

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


def prune_legacy_public_skill_dirs(
    target_root: Path,
    managed_skill_names: set[str],
    projected_skill_names: set[str],
) -> None:
    skills_root = target_root / "skills"
    if not skills_root.exists():
        return
    for name in sorted(managed_skill_names - projected_skill_names - {"vibe"}):
        skill_root = skills_root / name
        if skill_root.is_dir():
            record_legacy_cleanup_candidate(skill_root)
            shutil.rmtree(skill_root)


def install_runtime_core(repo_root: Path, target_root: Path, profile: str, allow_fallback: bool, adapter: dict):
    packaging = attach_local_catalog_descriptor(repo_root, resolve_runtime_core_packaging(repo_root, profile))
    excluded_skill_names = excluded_bundled_skill_names(packaging)
    previous_ledger = load_existing_install_ledger(target_root)
    skill_inventory = load_managed_skill_inventory(packaging)
    current_managed_skill_names = desired_managed_skill_names(repo_root, packaging)
    projected_skill_names = set(compatibility_projection_names(packaging, host_id=adapter["id"]))
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
            copy_skill_roots_without_self_shadow(
                src_root,
                dst_root,
                repo_root,
                excluded_skill_names,
                track_created_path=track_created_path,
                record_owned_tree_root=record_owned_tree_root,
            )
        else:
            copy_tree(
                src_root,
                dst_root,
                track_created_path=track_created_path,
                record_owned_tree_root=record_owned_tree_root,
            )
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
        destination = target_root / entry["target"]
        copy_file(src, destination, track_created_path=track_created_path)
    target_rel = canonical_vibe_target_relpath(packaging)
    canonical_vibe_name = Path(target_rel).name
    sync_vibe_canonical(
        repo_root,
        target_root,
        target_rel,
        copy_file_fn=lambda src, dst: copy_file(src, dst, track_created_path=track_created_path),
        copy_dir_replace_fn=lambda src, dst: copy_dir_replace(
            src,
            dst,
            track_created_path=track_created_path,
            record_owned_tree_root=record_owned_tree_root,
        ),
    )
    record_runtime_root(target_root / target_rel)
    corpus_target = materialize_internal_skill_corpus(
        repo_root,
        target_root,
        packaging,
        copy_dir_replace_fn=lambda src, dst: copy_dir_replace(
            src,
            dst,
            track_created_path=track_created_path,
            record_owned_tree_root=record_owned_tree_root,
        ),
    )
    record_runtime_root(corpus_target)
    materialize_allowlisted_skills(
        repo_root,
        target_root,
        packaging,
        host_id=adapter["id"],
        copy_dir_replace_fn=lambda src, dst: copy_dir_replace(
            src,
            dst,
            track_created_path=track_created_path,
            record_owned_tree_root=record_owned_tree_root,
        ),
    )
    prune_previously_managed_skill_dirs(
        target_root,
        derive_managed_skill_names_from_ledger(target_root, previous_ledger),
        projected_skill_names | {"vibe"},
    )
    prune_legacy_public_skill_dirs(target_root, current_managed_skill_names, projected_skill_names)
    for name in projected_skill_names:
        projected_root = target_root / "skills" / name
        if projected_root.exists():
            record_compatibility_root(projected_root)

    roots = skill_source_roots(repo_root)

    external_used = set()
    missing: set[str] = set()
    for name in skill_inventory.required_runtime_skills:
        if name == canonical_vibe_name:
            continue
        ensure_skill_present(
            target_root,
            name,
            True,
            allow_fallback,
            [root / name for root in roots],
            external_used,
            missing,
            destination_root=corpus_target,
            hidden_entrypoints=True,
            copy_tree_fn=lambda src, dst: copy_tree(
                src,
                dst,
                track_created_path=track_created_path,
                record_owned_tree_root=record_owned_tree_root,
            ),
        )
    for name in skill_inventory.required_workflow_skills:
        ensure_skill_present(
            target_root,
            name,
            True,
            allow_fallback,
            [root / name for root in roots[1:] + roots[:1]],
            external_used,
            missing,
            destination_root=corpus_target,
            hidden_entrypoints=True,
            copy_tree_fn=lambda src, dst: copy_tree(
                src,
                dst,
                track_created_path=track_created_path,
                record_owned_tree_root=record_owned_tree_root,
            ),
        )
    for name in skill_inventory.optional_workflow_skills:
        ensure_skill_present(
            target_root,
            name,
            False,
            allow_fallback,
            [root / name for root in roots[1:] + roots[:1]],
            external_used,
            missing,
            destination_root=corpus_target,
            hidden_entrypoints=True,
            copy_tree_fn=lambda src, dst: copy_tree(
                src,
                dst,
                track_created_path=track_created_path,
                record_owned_tree_root=record_owned_tree_root,
            ),
        )
    if missing:
        raise SystemExit("Missing required vendored skills: " + ", ".join(sorted(missing)))

    managed_skill_names = sorted(
        name for name in current_managed_skill_names
    )

    return packaging, sorted(external_used), managed_skill_names


def install_claude_guidance_payload(repo_root: Path, target_root: Path):
    install_claude_managed_settings(
        repo_root,
        target_root,
        track_created_path=track_created_path,
        record_managed_json=record_managed_json,
        record_merged_file=record_merged_file,
    )
    return


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root")
    parser.add_argument("--target-root")
    parser.add_argument("--host")
    parser.add_argument("--profile", choices=("minimal", "full"), default="full")
    parser.add_argument("--allow-external-skill-fallback", action="store_true")
    parser.add_argument("--require-closed-ready", action="store_true")
    parser.add_argument("--refresh-install-ledger", action="store_true")
    args = parser.parse_args(argv)

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
        install_codex_payload(
            repo_root,
            target_root,
            copy_tree_fn=lambda src, dst: copy_tree(
                src,
                dst,
                track_created_path=track_created_path,
                record_owned_tree_root=record_owned_tree_root,
            ),
            copy_file_fn=lambda src, dst: copy_file(src, dst, track_created_path=track_created_path),
            track_created_path=track_created_path,
            record_generated_from_template=record_generated_from_template,
            record_managed_json=record_managed_json,
        )
    elif mode == "preview-guidance":
        if adapter["id"] == "opencode":
            install_opencode_guidance_payload(
                repo_root,
                target_root,
                copy_tree_fn=lambda src, dst: copy_tree(
                    src,
                    dst,
                    track_created_path=track_created_path,
                    record_owned_tree_root=record_owned_tree_root,
                ),
                copy_file_fn=lambda src, dst: copy_file(src, dst, track_created_path=track_created_path),
            )
        elif adapter["id"] == "claude-code":
            install_claude_guidance_payload(repo_root, target_root)
        elif adapter["id"] == "cursor":
            pass
        else:
            raise SystemExit(f"Unsupported preview-guidance adapter id: {adapter['id']}")
    elif mode == "runtime-core":
        install_runtime_core_mode_payload(
            repo_root,
            target_root,
            adapter,
            copy_tree_fn=lambda src, dst: copy_tree(
                src,
                dst,
                track_created_path=track_created_path,
                record_owned_tree_root=record_owned_tree_root,
            ),
            copy_file_fn=lambda src, dst: copy_file(src, dst, track_created_path=track_created_path),
            track_created_path=track_created_path,
            record_generated_from_template=record_generated_from_template,
        )
    else:
        raise SystemExit(f"Unsupported adapter install mode: {mode}")

    wrapper_paths = materialize_host_visible_wrappers(
        repo_root=repo_root,
        target_root=target_root,
        host_id=adapter["id"],
        surface=dict(packaging.get("public_skill_surface") or {}),
    )
    discoverable_entry_surface = str((packaging.get("public_skill_surface") or {}).get("discoverable_entry_surface") or "").strip()
    if discoverable_entry_surface and adapter.get("discoverable_entries") and not wrapper_paths:
        raise SystemExit(
            "Discoverable wrapper projection for "
            f"'{adapter['id']}' produced no host-visible entries."
        )
    for wrapper_path in wrapper_paths:
        track_created_path(wrapper_path)
        record_specialist_wrapper(wrapper_path)

    closure_path, closure = materialize_host_closure(
        target_root,
        adapter,
        track_created_path=track_created_path,
        record_managed_json=record_managed_json,
        record_bridge_launcher=record_bridge_launcher,
    )
    global_instruction_bootstrap = materialize_global_instruction_bootstrap(
        repo_root,
        target_root,
        adapter,
        track_created_path=track_created_path,
        record_merged_file=record_merged_file,
    )
    record_sidecar_root(target_root / ".vibeskills")
    require_closed_ready_effective = bool(args.require_closed_ready and is_closed_ready_required(adapter))
    if require_closed_ready_effective and closure["host_closure_state"] != "closed_ready":
        raise SystemExit(
            "Host closure for "
            f"'{adapter['id']}' is not closed_ready "
            f"(got '{closure['host_closure_state']}'). "
            "Configure the host specialist bridge command first, then retry install."
        )

    canonical_vibe_rel = canonical_vibe_target_relpath(packaging)
    install_plan = build_install_plan(
        profile=args.profile,
        host_id=adapter["id"],
        target_root=target_root,
        install_mode=mode,
        canonical_vibe_rel=canonical_vibe_rel,
        managed_skill_names=managed_skill_names,
        packaging_manifest={
            "profile": packaging.get("profile", args.profile),
            "package_id": packaging.get("package_id"),
            "copy_bundled_skills": bool(packaging.get("copy_bundled_skills")),
            "copy_directories": list(packaging.get("copy_directories") or []),
            "copy_files": list(packaging.get("copy_files") or []),
            "public_skill_surface": dict(packaging.get("public_skill_surface") or {}),
            "internal_skill_corpus": dict(packaging.get("internal_skill_corpus") or {}),
            "compatibility_skill_projections": dict(packaging.get("compatibility_skill_projections") or {}),
        },
    )
    ledger_path = target_root / ".vibeskills" / "install-ledger.json"
    track_created_path(ledger_path)
    record_sidecar_root(target_root / ".vibeskills")
    write_install_ledger(
        plan=install_plan,
        state=materialization_state_from_ledger_state(),
        external_fallback_used=external_used,
        timestamp=datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"),
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
            "global_instruction_bootstrap_receipt": (
                str(global_instruction_bootstrap["receipt_path"])
                if isinstance(global_instruction_bootstrap, dict) and global_instruction_bootstrap.get("receipt_path")
                else None
            ),
            "legacy_opencode_config_cleanup": legacy_opencode_config_cleanup,
            "specialist_wrapper_ready": bool(closure["specialist_wrapper"]["ready"]),
            "require_closed_ready_requested": bool(args.require_closed_ready),
            "require_closed_ready_effective": require_closed_ready_effective,
        }
    )


if __name__ == "__main__":
    main()
