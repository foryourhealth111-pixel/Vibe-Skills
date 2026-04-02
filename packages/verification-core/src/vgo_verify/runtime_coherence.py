from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .policies import load_json, merge_runtime_config, read_text_if_exists, resolve_repo_root, utc_now, write_text

DEFAULT_RUNTIME_CONFIG = {
    "target_relpath": "skills/vibe",
    "receipt_relpath": "skills/vibe/outputs/runtime-freshness-receipt.json",
    "post_install_gate": "scripts/verify/vibe-installed-runtime-freshness-gate.ps1",
    "coherence_gate": "scripts/verify/vibe-release-install-runtime-coherence-gate.ps1",
    "receipt_contract_version": 1,
    "shell_degraded_behavior": "warn_and_skip_authoritative_runtime_gate",
    "required_runtime_markers": [
        "SKILL.md",
        "config/version-governance.json",
        "install.ps1",
        "check.ps1",
        "scripts/common/vibe-governance-helpers.ps1",
        "scripts/verify/vibe-installed-runtime-freshness-gate.ps1",
        "scripts/verify/vibe-release-install-runtime-coherence-gate.ps1",
        "scripts/router/resolve-pack-route.ps1",
    ],
}


def runtime_config(governance: dict[str, Any]) -> dict[str, Any]:
    return merge_runtime_config(governance, DEFAULT_RUNTIME_CONFIG)


def content_contains(path: Path, pattern: str) -> bool:
    return pattern in read_text_if_exists(path)


def freshness_gate_sources(repo_root: Path, runtime: dict[str, Any]) -> list[Path]:
    candidates = [
        repo_root / "packages" / "verification-core" / "src" / "vgo_verify" / "runtime_freshness.py",
        repo_root / "scripts" / "verify" / "runtime_neutral" / "freshness_gate.py",
    ]
    gate_rel = str(runtime.get("post_install_gate") or "").strip()
    if gate_rel:
        candidates.append(repo_root / gate_rel)
    return candidates


def authoritative_gate_contains(repo_root: Path, runtime: dict[str, Any], pattern: str) -> bool:
    return any(content_contains(path, pattern) for path in freshness_gate_sources(repo_root, runtime))


def write_artifacts(repo_root: Path, artifact: dict[str, Any]) -> None:
    output_dir = repo_root / "outputs" / "verify"
    write_text(output_dir / "vibe-release-install-runtime-coherence-gate.json", json.dumps(artifact, ensure_ascii=False, indent=2) + "\n")
    lines = [
        "# VCO Release / Install / Runtime Coherence Gate",
        "",
        f"- Gate Result: **{artifact['gate_result']}**",
        f"- Repo Root: `{artifact['repo_root']}`",
        f"- Target Root: `{artifact['target_root']}`",
        f"- Assertion Failures: {artifact['summary']['failures']}",
        f"- Warnings: {artifact['summary']['warnings']}",
        "",
    ]
    if artifact["assertions"]:
        lines += ["## Assertions", ""]
        for item in artifact["assertions"]:
            lines.append(f"- [{'PASS' if item['ok'] else 'FAIL'}] {item['message']}")
        lines.append("")
    if artifact["warnings"]:
        lines += ["## Warnings", ""]
        for item in artifact["warnings"]:
            lines.append(f"- {item}")
        lines.append("")
    write_text(output_dir / "vibe-release-install-runtime-coherence-gate.md", "\n".join(lines) + "\n")


def evaluate(repo_root: Path, target_root: Path) -> dict[str, Any]:
    governance = load_json(repo_root / "config" / "version-governance.json")
    runtime = runtime_config(governance)
    assertions: list[dict[str, Any]] = []
    warnings: list[str] = []

    def add_assertion(condition: bool, message: str) -> None:
        print(f"[{'PASS' if condition else 'FAIL'}] {message}")
        assertions.append({"ok": condition, "message": message})

    def add_warning(message: str) -> None:
        print(f"[WARN] {message}")
        warnings.append(message)

    version_doc = repo_root / "docs" / "version-packaging-governance.md"
    runtime_doc = repo_root / "docs" / "runtime-freshness-install-sop.md"
    install_ps1 = repo_root / "install.ps1"
    install_sh = repo_root / "install.sh"
    check_ps1 = repo_root / "check.ps1"
    check_sh = repo_root / "check.sh"
    runtime_gate_path = repo_root / str(runtime["post_install_gate"])
    coherence_gate_path = repo_root / str(runtime["coherence_gate"])
    frontmatter_gate_path = repo_root / "scripts" / "verify" / "vibe-bom-frontmatter-gate.ps1"
    receipt_path = target_root / str(runtime["receipt_relpath"])

    print("=== VCO Release / Install / Runtime Coherence Gate ===")
    print(f"Repo root  : {repo_root}")
    print(f"Target root: {target_root}")
    print()

    add_assertion(bool(runtime["target_relpath"]), "[runtime] target_relpath is declared")
    add_assertion(bool(runtime["receipt_relpath"]), "[runtime] receipt_relpath is declared")
    add_assertion(
        str(runtime["receipt_relpath"]).replace("\\", "/").startswith(str(runtime["target_relpath"]).replace("\\", "/") + "/"),
        "[runtime] receipt_relpath stays under target_relpath",
    )
    add_assertion(runtime_gate_path.exists(), "[runtime] post-install freshness gate script exists")
    add_assertion(coherence_gate_path.exists(), "[runtime] coherence gate script exists")
    add_assertion(frontmatter_gate_path.exists(), "[runtime] BOM/frontmatter gate script exists")
    add_assertion(str(runtime["post_install_gate"]) in list(runtime["required_runtime_markers"]), "[runtime] required_runtime_markers includes post-install freshness gate")
    add_assertion(str(runtime["coherence_gate"]) in list(runtime["required_runtime_markers"]), "[runtime] required_runtime_markers includes coherence gate")
    add_assertion(int(runtime["receipt_contract_version"]) >= 1, "[runtime] receipt_contract_version is declared and >= 1")
    add_assertion(
        str(runtime["shell_degraded_behavior"]) == "warn_and_skip_authoritative_runtime_gate",
        "[runtime] shell_degraded_behavior declares warn-and-skip semantics",
    )

    add_assertion(version_doc.exists(), "[docs] version-packaging-governance.md exists")
    add_assertion(runtime_doc.exists(), "[docs] runtime-freshness-install-sop.md exists")
    add_assertion(content_contains(version_doc, "release only governs repo parity"), "[docs] version governance doc defines release boundary")
    add_assertion(content_contains(version_doc, "execution-context lock"), "[docs] version governance doc documents execution-context lock")
    add_assertion(content_contains(runtime_doc, "receipt contract"), "[docs] runtime SOP documents receipt contract")
    add_assertion(content_contains(runtime_doc, "shell degraded behavior"), "[docs] runtime SOP documents shell degraded behavior")

    add_assertion(content_contains(install_ps1, "Invoke-InstalledRuntimeFreshnessGate"), "[install.ps1] install flow invokes runtime freshness gate")
    add_assertion(content_contains(install_sh, "run_runtime_freshness_gate"), "[install.sh] shell install flow invokes runtime freshness gate")
    add_assertion(content_contains(check_ps1, "Invoke-RuntimeFreshnessCheck"), "[check.ps1] check flow invokes runtime freshness gate")
    add_assertion(content_contains(check_ps1, "Invoke-RuntimeCoherenceCheck"), "[check.ps1] check flow invokes coherence gate")
    add_assertion(content_contains(check_sh, "run_runtime_freshness_gate"), "[check.sh] shell check flow invokes runtime freshness gate")
    add_assertion(content_contains(check_sh, "run_runtime_coherence_gate"), "[check.sh] shell check flow invokes coherence gate")
    add_assertion(
        content_contains(check_sh, "runtime-neutral") or content_contains(check_sh, "pwsh is not installed"),
        "[check.sh] shell check documents a degraded or runtime-neutral gate path",
    )

    add_assertion(authoritative_gate_contains(repo_root, runtime, "receipt_version"), "[receipt] installed runtime freshness gate emits receipt_version")
    add_assertion(authoritative_gate_contains(repo_root, runtime, "gate_result"), "[receipt] installed runtime freshness gate writes gate_result")

    if receipt_path.exists():
        try:
            receipt = load_json(receipt_path)
            add_assertion(str(receipt.get("gate_result")) == "PASS", "[receipt] installed runtime receipt gate_result is PASS")
            add_assertion(int(receipt.get("receipt_version", 0)) >= int(runtime["receipt_contract_version"]), "[receipt] installed runtime receipt version satisfies contract")
        except Exception as exc:
            add_assertion(False, f"[receipt] installed runtime receipt parses cleanly -> {exc}")
    else:
        add_warning(f"runtime receipt not found at {receipt_path}; repo contract validated without installed-runtime evidence.")

    failures = sum(1 for item in assertions if not item["ok"])
    return {
        "gate": "vibe-release-install-runtime-coherence-gate",
        "repo_root": str(repo_root),
        "target_root": str(target_root.resolve()),
        "generated_at": utc_now(),
        "gate_result": "PASS" if failures == 0 else "FAIL",
        "assertions": assertions,
        "warnings": warnings,
        "contract": {
            "target_relpath": str(runtime["target_relpath"]),
            "receipt_relpath": str(runtime["receipt_relpath"]),
            "post_install_gate": str(runtime["post_install_gate"]),
            "coherence_gate": str(runtime["coherence_gate"]),
            "receipt_contract_version": int(runtime["receipt_contract_version"]),
            "shell_degraded_behavior": str(runtime["shell_degraded_behavior"]),
        },
        "summary": {
            "failures": failures,
            "warnings": len(warnings),
        },
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Runtime-neutral release/install/runtime coherence gate.")
    parser.add_argument("--target-root", default=str(Path.home() / ".codex"))
    parser.add_argument("--write-artifacts", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        repo_root = resolve_repo_root(Path(__file__))
        artifact = evaluate(repo_root, Path(args.target_root))
        if args.write_artifacts:
            write_artifacts(repo_root, artifact)
    except Exception as exc:  # pragma: no cover
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1
    return 0 if artifact["gate_result"] == "PASS" else 1
