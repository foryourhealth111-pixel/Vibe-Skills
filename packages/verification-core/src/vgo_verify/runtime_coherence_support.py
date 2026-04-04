from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .policies import read_text_if_exists, write_text


def content_contains(path: Path, pattern: str) -> bool:
    return pattern in read_text_if_exists(path)


def freshness_gate_sources(repo_root: Path, runtime: dict[str, Any]) -> list[Path]:
    candidates = [
        repo_root / "packages" / "verification-core" / "src" / "vgo_verify" / "runtime_freshness.py",
        repo_root / "packages" / "verification-core" / "src" / "vgo_verify" / "runtime_freshness_support.py",
        repo_root / str(runtime.get("neutral_freshness_gate") or ""),
    ]
    gate_rel = str(runtime.get("post_install_gate") or "").strip()
    if gate_rel:
        candidates.append(repo_root / gate_rel)
    return [path for path in candidates if str(path).strip()]


def authoritative_gate_contains(repo_root: Path, runtime: dict[str, Any], pattern: str) -> bool:
    return any(content_contains(path, pattern) for path in freshness_gate_sources(repo_root, runtime))


def write_artifacts(repo_root: Path, artifact: dict[str, Any]) -> None:
    output_dir = repo_root / "outputs" / "verify"
    write_text(
        output_dir / "vibe-release-install-runtime-coherence-gate.json",
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
    )
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
    write_text(
        output_dir / "vibe-release-install-runtime-coherence-gate.md",
        "\n".join(lines) + "\n",
    )
