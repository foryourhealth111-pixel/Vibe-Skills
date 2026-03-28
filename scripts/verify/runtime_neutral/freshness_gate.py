#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_MIRROR_FILES = [
    "SKILL.md",
    "check.ps1",
    "check.sh",
    "install.ps1",
    "install.sh",
]

DEFAULT_MIRROR_DIRECTORIES = [
    "config",
    "protocols",
    "references",
    "docs",
    "scripts",
]

DEFAULT_IGNORE_JSON_KEYS = ["updated", "generated_at"]

DEFAULT_RUNTIME_CONFIG = {
    "target_relpath": "skills/vibe",
    "receipt_relpath": "skills/vibe/outputs/runtime-freshness-receipt.json",
    "post_install_gate": "scripts/verify/vibe-installed-runtime-freshness-gate.ps1",
    "required_runtime_markers": [
        "SKILL.md",
        "config/version-governance.json",
        "scripts/router/resolve-pack-route.ps1",
        "scripts/common/vibe-governance-helpers.ps1",
    ],
    "require_nested_bundled_root": False,
    "receipt_contract_version": 1,
}


@dataclass
class GovernanceContext:
    repo_root: Path
    governance_path: Path
    governance: dict[str, Any]
    canonical_root: Path
    packaging: dict[str, Any]
    runtime_config: dict[str, Any]
    mirror_targets: list[dict[str, Any]]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def to_posix(path: Path | str) -> str:
    return Path(path).as_posix()


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def remove_ignored_keys(node: Any, ignore_keys: set[str]) -> Any:
    if isinstance(node, dict):
        return {
            key: remove_ignored_keys(value, ignore_keys)
            for key, value in sorted(node.items())
            if key not in ignore_keys
        }
    if isinstance(node, list):
        return [remove_ignored_keys(item, ignore_keys) for item in node]
    return node


def normalized_json_hash(path: Path, ignore_keys: set[str]) -> str:
    normalized = remove_ignored_keys(load_json(path), ignore_keys)
    payload = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_parity(reference: Path, candidate: Path, ignore_json_keys: set[str]) -> bool:
    if not reference.exists() or not candidate.exists():
        return False
    if reference.suffix.lower() == ".json" and candidate.suffix.lower() == ".json":
        return normalized_json_hash(reference, ignore_json_keys) == normalized_json_hash(candidate, ignore_json_keys)
    return file_hash(reference) == file_hash(candidate)


def relative_file_list(root: Path) -> list[str]:
    if not root.exists():
        return []
    return sorted(
        to_posix(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file()
    )


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


def mirror_topology_targets(governance: dict[str, Any], repo_root: Path) -> list[dict[str, Any]]:
    topology = governance.get("mirror_topology") or {}
    targets = topology.get("targets") or []
    if not targets:
        source = governance.get("source_of_truth") or {}
        bundled_root = source.get("bundled_root") or "bundled/skills/vibe"
        nested_root = source.get("nested_bundled_root") or f"{bundled_root}/{bundled_root}"
        targets = [
            {
                "id": "canonical",
                "path": source.get("canonical_root") or ".",
                "role": "canonical",
            },
            {
                "id": "bundled",
                "path": bundled_root,
                "role": "mirror",
            },
            {
                "id": "nested_bundled",
                "path": nested_root,
                "role": "mirror",
            },
        ]

    normalized: list[dict[str, Any]] = []
    for target in targets:
        rel = str(target.get("path") or "").strip()
        if not rel:
            continue
        full_path = (repo_root / rel).resolve()
        normalized.append(
            {
                "id": str(target.get("id") or ""),
                "path": rel.replace("\\", "/"),
                "full_path": full_path,
                "role": str(target.get("role") or "mirror"),
                "is_canonical": str(target.get("role") or "mirror") == "canonical",
            }
        )
    return normalized


def packaging_contract(governance: dict[str, Any]) -> dict[str, Any]:
    packaging = governance.get("packaging") or {}
    mirror = packaging.get("mirror") or {}
    return {
        "mirror": {
            "files": list(mirror.get("files") or DEFAULT_MIRROR_FILES),
            "directories": list(mirror.get("directories") or DEFAULT_MIRROR_DIRECTORIES),
        },
        "allow_bundled_only": list(packaging.get("allow_bundled_only") or []),
        "normalized_json_ignore_keys": list(
            packaging.get("normalized_json_ignore_keys") or DEFAULT_IGNORE_JSON_KEYS
        ),
    }


def runtime_config(governance: dict[str, Any]) -> dict[str, Any]:
    runtime = ((governance.get("runtime") or {}).get("installed_runtime")) or {}
    merged = dict(DEFAULT_RUNTIME_CONFIG)
    for key, value in runtime.items():
        if value is None:
            continue
        merged[key] = value
    merged["required_runtime_markers"] = list(
        runtime.get("required_runtime_markers") or DEFAULT_RUNTIME_CONFIG["required_runtime_markers"]
    )
    return merged


def installed_runtime_materialized(repo_root: Path, runtime_cfg: dict[str, Any]) -> bool:
    required_markers = list(runtime_cfg.get("required_runtime_markers") or [])
    if not required_markers:
        return False
    return all((repo_root / marker).exists() for marker in required_markers)


def enforce_execution_context(context: GovernanceContext, script_path: Path) -> None:
    policy = context.governance.get("execution_context_policy") or {}
    require_outer_git_root = bool(policy.get("require_outer_git_root", True))
    fail_if_under_mirror = bool(policy.get("fail_if_script_path_is_under_mirror_root", True))
    if (
        require_outer_git_root
        and not (context.repo_root / ".git").exists()
        and not installed_runtime_materialized(context.repo_root, context.runtime_config)
    ):
        raise RuntimeError(
            f"Execution-context lock failed: resolved repo root is not the outer git root -> {context.repo_root}"
        )
    if not fail_if_under_mirror:
        return
    resolved_script = script_path.resolve()
    for target in context.mirror_targets:
        if target["is_canonical"]:
            continue
        try:
            resolved_script.relative_to(target["full_path"])
        except ValueError:
            continue
        raise RuntimeError(
            "Execution-context lock failed: governance/verify scripts must run from the canonical repo tree, "
            f"not from mirror targets. target={target['id']} script={resolved_script} repoRoot={context.repo_root}"
        )


def load_governance_context(script_path: Path, enforce_context: bool = True) -> GovernanceContext:
    repo_root = resolve_repo_root(script_path)
    governance_path = repo_root / "config" / "version-governance.json"
    if not governance_path.exists():
        raise RuntimeError(f"version-governance config not found: {governance_path}")
    governance = load_json(governance_path)
    targets = mirror_topology_targets(governance, repo_root)
    canonical_target_id = (governance.get("mirror_topology") or {}).get("canonical_target_id") or "canonical"
    canonical = next((target for target in targets if target["id"] == canonical_target_id), None)
    if canonical is None:
        canonical = next((target for target in targets if target["is_canonical"]), None)
    if canonical is None:
        raise RuntimeError("mirror topology does not define a canonical target.")
    context = GovernanceContext(
        repo_root=repo_root,
        governance_path=governance_path,
        governance=governance,
        canonical_root=Path(canonical["full_path"]),
        packaging=packaging_contract(governance),
        runtime_config=runtime_config(governance),
        mirror_targets=targets,
    )
    if enforce_context:
        enforce_execution_context(context, script_path)
    return context


def evaluate_freshness(
    repo_root: Path,
    governance: dict[str, Any],
    canonical_root: Path,
    target_root: Path,
    script_path: Path,
    write_artifacts: bool = False,
    write_receipt: bool = False,
) -> tuple[bool, dict[str, Any]]:
    context = GovernanceContext(
        repo_root=repo_root,
        governance_path=repo_root / "config" / "version-governance.json",
        governance=governance,
        canonical_root=canonical_root,
        packaging=packaging_contract(governance),
        runtime_config=runtime_config(governance),
        mirror_targets=mirror_topology_targets(governance, repo_root),
    )
    enforce_execution_context(context, script_path)

    packaging = context.packaging
    runtime = context.runtime_config
    ignore_keys = set(packaging["normalized_json_ignore_keys"])
    installed_root = (target_root / runtime["target_relpath"]).resolve()
    receipt_path = (target_root / runtime["receipt_relpath"]).resolve()
    allow_installed_only = set(packaging["allow_bundled_only"])
    nested_root = (installed_root / "bundled" / "skills" / "vibe").resolve()

    results: dict[str, Any] = {
        "target_root": str(target_root.resolve()),
        "installed_root": str(installed_root),
        "receipt_path": str(receipt_path),
        "release": {
            "version": str((governance.get("release") or {}).get("version") or ""),
            "updated": str((governance.get("release") or {}).get("updated") or ""),
        },
        "files": [],
        "directories": [],
        "runtime_markers": [],
        "nested": {
            "required": bool(runtime.get("require_nested_bundled_root")),
            "path": str(nested_root),
            "exists": nested_root.exists(),
        },
    }

    assertions: list[bool] = []

    def log(condition: bool, message: str) -> None:
        prefix = "[PASS]" if condition else "[FAIL]"
        print(f"{prefix} {message}")
        assertions.append(condition)

    print("=== VCO Installed Runtime Freshness Gate ===")
    print(f"Repo root    : {repo_root}")
    print(f"Target root  : {target_root}")
    print(f"Installed root: {installed_root}")

    installed_exists = installed_root.exists()
    log(installed_exists, "[runtime] installed vibe root exists")
    if runtime.get("require_nested_bundled_root"):
        log(nested_root.exists(), "[runtime] nested bundled root exists")

    for rel in packaging["mirror"]["files"]:
        canonical_path = (canonical_root / rel).resolve()
        installed_path = (installed_root / rel).resolve()
        canonical_exists = canonical_path.exists()
        installed_file_exists = installed_path.exists()
        parity = canonical_exists and installed_file_exists and file_parity(canonical_path, installed_path, ignore_keys)
        log(canonical_exists, f"[file:{rel}] canonical exists")
        log(installed_file_exists, f"[file:{rel}] installed exists")
        if canonical_exists and installed_file_exists:
            log(parity, f"[file:{rel}] parity")
        results["files"].append(
            {
                "path": rel,
                "canonical_exists": canonical_exists,
                "installed_exists": installed_file_exists,
                "parity": parity,
            }
        )

    for rel in packaging["mirror"]["directories"]:
        canonical_dir = (canonical_root / rel).resolve()
        installed_dir = (installed_root / rel).resolve()
        canonical_exists = canonical_dir.exists()
        installed_dir_exists = installed_dir.exists()
        log(canonical_exists, f"[dir:{rel}] canonical exists")
        log(installed_dir_exists, f"[dir:{rel}] installed exists")
        only_main: list[str] = []
        only_installed: list[str] = []
        diff_files: list[str] = []
        if canonical_exists and installed_dir_exists:
            canonical_files = relative_file_list(canonical_dir)
            installed_files = relative_file_list(installed_dir)
            installed_set = set(installed_files)
            canonical_set = set(canonical_files)
            only_main = sorted(canonical_set - installed_set)
            only_installed = sorted(
                path
                for path in installed_set - canonical_set
                if f"{rel}/{path}" not in allow_installed_only
            )
            for file_rel in sorted(canonical_set & installed_set):
                if not file_parity(canonical_dir / file_rel, installed_dir / file_rel, ignore_keys):
                    diff_files.append(file_rel)
        log(len(only_main) == 0, f"[dir:{rel}] no files missing in installed runtime")
        log(len(only_installed) == 0, f"[dir:{rel}] no unexpected installed-only files")
        log(len(diff_files) == 0, f"[dir:{rel}] file parity")
        results["directories"].append(
            {
                "path": rel,
                "only_in_canonical": only_main,
                "only_in_installed": only_installed,
                "diff_files": diff_files,
            }
        )

    for rel in runtime["required_runtime_markers"]:
        canonical_path = (canonical_root / rel).resolve()
        installed_path = (installed_root / rel).resolve()
        canonical_exists = canonical_path.exists()
        installed_marker_exists = installed_path.exists()
        parity = canonical_exists and installed_marker_exists and file_parity(canonical_path, installed_path, ignore_keys)
        log(canonical_exists, f"[marker:{rel}] canonical exists")
        log(installed_marker_exists, f"[marker:{rel}] installed exists")
        if canonical_exists and installed_marker_exists:
            log(parity, f"[marker:{rel}] parity")
        results["runtime_markers"].append(
            {
                "path": rel,
                "canonical_exists": canonical_exists,
                "installed_exists": installed_marker_exists,
                "parity": parity,
            }
        )

    total = len(assertions)
    passed = sum(1 for assertion in assertions if assertion)
    failed = total - passed
    gate_pass = failed == 0

    print()
    print("=== Summary ===")
    print(f"Total assertions: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Gate Result: {'PASS' if gate_pass else 'FAIL'}")

    artifact = {
        "generated_at": utc_now(),
        "gate_result": "PASS" if gate_pass else "FAIL",
        "assertions": {
            "total": total,
            "passed": passed,
            "failed": failed,
        },
        "results": results,
    }

    if write_artifacts:
        output_dir = repo_root / "outputs" / "verify"
        write_text(output_dir / "vibe-installed-runtime-freshness-gate.json", json.dumps(artifact, ensure_ascii=False, indent=2) + "\n")
        markdown = "\n".join(
            [
                "# VCO Installed Runtime Freshness Gate",
                "",
                f"- Gate Result: **{artifact['gate_result']}**",
                f"- Assertions: total={total}, passed={passed}, failed={failed}",
                f"- Target root: `{target_root.resolve()}`",
                f"- Installed root: `{installed_root}`",
                f"- release.version: `{results['release']['version']}`",
                f"- release.updated: `{results['release']['updated']}`",
            ]
        )
        write_text(output_dir / "vibe-installed-runtime-freshness-gate.md", markdown + "\n")

    if write_receipt:
        if gate_pass:
            receipt = {
                "generated_at": utc_now(),
                "gate_result": "PASS",
                "release": results["release"],
                "target_root": str(target_root.resolve()),
                "installed_root": str(installed_root),
                "receipt_version": int(runtime.get("receipt_contract_version", 1)),
            }
            write_text(receipt_path, json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
        elif receipt_path.exists():
            receipt_path.unlink()

    return gate_pass, artifact


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Runtime-neutral installed runtime freshness gate.")
    default_target = Path.home() / ".codex"
    parser.add_argument("--target-root", default=str(default_target))
    parser.add_argument("--write-artifacts", action="store_true")
    parser.add_argument("--write-receipt", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    script_path = Path(__file__)
    try:
        context = load_governance_context(script_path, enforce_context=True)
        gate_pass, _ = evaluate_freshness(
            repo_root=context.repo_root,
            governance=context.governance,
            canonical_root=context.canonical_root,
            target_root=Path(args.target_root),
            script_path=script_path,
            write_artifacts=args.write_artifacts,
            write_receipt=args.write_receipt,
        )
    except Exception as exc:  # pragma: no cover - CLI guard
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1
    return 0 if gate_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
