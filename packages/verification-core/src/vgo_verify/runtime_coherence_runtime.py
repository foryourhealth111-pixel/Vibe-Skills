from __future__ import annotations

from pathlib import Path
from typing import Any

from .runtime_coherence_support import authoritative_gate_contains, content_contains
from .policies import load_json, utc_now


def evaluate_runtime_coherence(repo_root: Path, target_root: Path, runtime: dict[str, Any]) -> dict[str, Any]:
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
    frontmatter_gate_path = repo_root / str(runtime["frontmatter_gate"])
    receipt_path = target_root / str(runtime["receipt_relpath"])

    print("=== VCO Release / Install / Runtime Coherence Gate ===")
    print(f"Repo root  : {repo_root}")
    print(f"Target root: {target_root}")
    print()

    add_assertion(bool(runtime["target_relpath"]), "[runtime] target_relpath is declared")
    add_assertion(bool(runtime["receipt_relpath"]), "[runtime] receipt_relpath is declared")
    add_assertion(
        str(runtime["receipt_relpath"]).replace("\\", "/").startswith(
            str(runtime["target_relpath"]).replace("\\", "/") + "/"
        ),
        "[runtime] receipt_relpath stays under target_relpath",
    )
    add_assertion(runtime_gate_path.exists(), "[runtime] post-install freshness gate script exists")
    add_assertion(coherence_gate_path.exists(), "[runtime] coherence gate script exists")
    add_assertion(frontmatter_gate_path.exists(), "[runtime] BOM/frontmatter gate script exists")
    add_assertion(
        str(runtime["post_install_gate"]) in list(runtime["required_runtime_markers"]),
        "[runtime] required_runtime_markers includes post-install freshness gate",
    )
    add_assertion(
        str(runtime["coherence_gate"]) in list(runtime["required_runtime_markers"]),
        "[runtime] required_runtime_markers includes coherence gate",
    )
    add_assertion(
        int(runtime["receipt_contract_version"]) >= 1,
        "[runtime] receipt_contract_version is declared and >= 1",
    )
    add_assertion(
        str(runtime["shell_degraded_behavior"]) == "warn_and_skip_authoritative_runtime_gate",
        "[runtime] shell_degraded_behavior declares warn-and-skip semantics",
    )

    add_assertion(version_doc.exists(), "[docs] version-packaging-governance.md exists")
    add_assertion(runtime_doc.exists(), "[docs] runtime-freshness-install-sop.md exists")
    add_assertion(
        content_contains(version_doc, "release only governs repo parity"),
        "[docs] version governance doc defines release boundary",
    )
    add_assertion(
        content_contains(version_doc, "execution-context lock"),
        "[docs] version governance doc documents execution-context lock",
    )
    add_assertion(
        content_contains(runtime_doc, "receipt contract"),
        "[docs] runtime SOP documents receipt contract",
    )
    add_assertion(
        content_contains(runtime_doc, "shell degraded behavior"),
        "[docs] runtime SOP documents shell degraded behavior",
    )

    add_assertion(
        content_contains(install_ps1, "Invoke-InstalledRuntimeFreshnessGate"),
        "[install.ps1] install flow invokes runtime freshness gate",
    )
    add_assertion(
        content_contains(install_sh, "run_runtime_freshness_gate"),
        "[install.sh] shell install flow invokes runtime freshness gate",
    )
    add_assertion(
        content_contains(check_ps1, "Invoke-RuntimeFreshnessCheck"),
        "[check.ps1] check flow invokes runtime freshness gate",
    )
    add_assertion(
        content_contains(check_ps1, "Invoke-RuntimeCoherenceCheck"),
        "[check.ps1] check flow invokes coherence gate",
    )
    add_assertion(
        content_contains(check_sh, "run_runtime_freshness_gate"),
        "[check.sh] shell check flow invokes runtime freshness gate",
    )
    add_assertion(
        content_contains(check_sh, "run_runtime_coherence_gate"),
        "[check.sh] shell check flow invokes coherence gate",
    )
    add_assertion(
        content_contains(check_sh, "runtime-neutral") or content_contains(check_sh, "pwsh is not installed"),
        "[check.sh] shell check documents a degraded or runtime-neutral gate path",
    )

    add_assertion(
        authoritative_gate_contains(repo_root, runtime, "receipt_version"),
        "[receipt] installed runtime freshness gate emits receipt_version",
    )
    add_assertion(
        authoritative_gate_contains(repo_root, runtime, "gate_result"),
        "[receipt] installed runtime freshness gate writes gate_result",
    )

    if receipt_path.exists():
        try:
            receipt = load_json(receipt_path)
            add_assertion(
                str(receipt.get("gate_result")) == "PASS",
                "[receipt] installed runtime receipt gate_result is PASS",
            )
            add_assertion(
                int(receipt.get("receipt_version", 0)) >= int(runtime["receipt_contract_version"]),
                "[receipt] installed runtime receipt version satisfies contract",
            )
        except Exception as exc:
            add_assertion(False, f"[receipt] installed runtime receipt parses cleanly -> {exc}")
    else:
        add_warning(
            f"runtime receipt not found at {receipt_path}; repo contract validated without installed-runtime evidence."
        )

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
            "frontmatter_gate": str(runtime["frontmatter_gate"]),
            "neutral_freshness_gate": str(runtime["neutral_freshness_gate"]),
            "receipt_contract_version": int(runtime["receipt_contract_version"]),
            "shell_degraded_behavior": str(runtime["shell_degraded_behavior"]),
        },
        "summary": {
            "failures": failures,
            "warnings": len(warnings),
        },
    }
