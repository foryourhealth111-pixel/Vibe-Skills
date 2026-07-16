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
    update_ps1 = repo_root / "update.ps1"
    update_sh = repo_root / "update.sh"
    uninstall_ps1 = repo_root / "uninstall.ps1"
    uninstall_sh = repo_root / "uninstall.sh"
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
    add_assertion(
        str(runtime["receipt_relpath"]).replace("\\", "/") == "skills/vibe/.vibeskills/install-receipt.json",
        "[runtime] receipt_relpath uses simplified install receipt",
    )
    add_assertion(runtime_gate_path.exists(), "[runtime] post-install freshness gate script exists")
    add_assertion(coherence_gate_path.exists(), "[runtime] coherence gate script exists")
    add_assertion(frontmatter_gate_path.exists(), "[runtime] BOM/frontmatter gate script exists")
    add_assertion(
        int(runtime["receipt_contract_version"]) >= 1,
        "[runtime] receipt_contract_version is declared and >= 1",
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
        content_contains(runtime_doc, "does not require the installed folder to be a full repository mirror"),
        "[docs] runtime SOP limits freshness to the receipt-owned payload",
    )

    ps_wrappers = (
        ("install.ps1", install_ps1, "install"),
        ("check.ps1", check_ps1, "check"),
        ("update.ps1", update_ps1, "update"),
        ("uninstall.ps1", uninstall_ps1, "uninstall"),
    )
    sh_wrappers = (
        ("install.sh", install_sh, "install"),
        ("check.sh", check_sh, "check"),
        ("update.sh", update_sh, "update"),
        ("uninstall.sh", uninstall_sh, "uninstall"),
    )
    legacy_ps_tokens = ("HostId", "Profile", "TargetRoot")
    legacy_sh_tokens = ("--host", "--profile", "--target-root")

    for label, path, command in ps_wrappers:
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        add_assertion(path.is_file(), f"[{label}] simplified wrapper exists")
        add_assertion("SkillsDir" in text, f"[{label}] exposes skills directory semantics")
        add_assertion("vgo_cli.main" in text and f"'{command}'" in text, f"[{label}] calls vgo-cli {command}")
        add_assertion("--skills-dir" in text, f"[{label}] forwards explicit skills directory")
        add_assertion(
            not any(token in text for token in legacy_ps_tokens),
            f"[{label}] does not expose legacy host/profile/target-root install options",
        )

    for label, path, command in sh_wrappers:
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        add_assertion(path.is_file(), f"[{label}] simplified wrapper exists")
        add_assertion(f"vgo_cli.main {command}" in text, f"[{label}] calls vgo-cli {command}")
        add_assertion('"$@"' in text, f"[{label}] forwards CLI arguments including --skills-dir")
        add_assertion(
            not any(token in text for token in legacy_sh_tokens),
            f"[{label}] does not expose legacy host/profile/target-root install options",
        )

    if receipt_path.exists():
        try:
            receipt = load_json(receipt_path)
            add_assertion(
                str(receipt.get("receipt_kind")) == "vibe-skill-install",
                "[receipt] install receipt declares simplified install kind",
            )
            add_assertion(
                str(receipt.get("skill_id")) == "vibe",
                "[receipt] install receipt belongs to vibe skill",
            )
        except Exception as exc:
            add_assertion(False, f"[receipt] install receipt parses cleanly -> {exc}")
    else:
        add_warning(
            f"install receipt not found at {receipt_path}; repo contract validated without installed-runtime evidence."
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
        },
        "summary": {
            "failures": failures,
            "warnings": len(warnings),
        },
    }
