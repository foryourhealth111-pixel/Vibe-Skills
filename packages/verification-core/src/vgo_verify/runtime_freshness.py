from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .policies import (
    GovernanceContext,
    enforce_execution_context,
    file_parity,
    load_governance_context as _load_governance_context,
    merge_runtime_config,
    mirror_topology_targets,
    relative_file_list,
    resolve_packaging_contract,
    utc_now,
    write_text,
)

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


def runtime_config(governance: dict[str, Any]) -> dict[str, Any]:
    return merge_runtime_config(governance, DEFAULT_RUNTIME_CONFIG)


def load_governance_context(script_path: Path, enforce_context: bool = True) -> GovernanceContext:
    return _load_governance_context(script_path, DEFAULT_RUNTIME_CONFIG, enforce_context=enforce_context)


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
        packaging=resolve_packaging_contract(governance, repo_root),
        runtime_config=runtime_config(governance),
        mirror_targets=mirror_topology_targets(governance, repo_root),
    )
    enforce_execution_context(context, script_path)

    packaging = context.packaging
    runtime = context.runtime_config
    ignore_keys = set(packaging["normalized_json_ignore_keys"])
    installed_root = (target_root / runtime["target_relpath"]).resolve()
    receipt_path = (target_root / runtime["receipt_relpath"]).resolve()
    allow_installed_only = set(packaging.get("allow_installed_only") or packaging["allow_bundled_only"])
    generated = (governance.get("packaging") or {}).get("generated_compatibility") or {}
    nested_runtime = generated.get("nested_runtime_root") or {}
    nested_rel = str(nested_runtime.get("relative_path") or "bundled/skills/vibe").strip()
    nested_root = (installed_root / nested_rel).resolve()

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
    parser.add_argument("--target-root", default=str(Path.home() / ".codex"))
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
    except Exception as exc:  # pragma: no cover
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1
    return 0 if gate_pass else 1
