from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_frontmatter_gate_consumes_effective_runtime_contract_paths() -> None:
    content = (REPO_ROOT / "scripts" / "verify" / "vibe-bom-frontmatter-gate.ps1").read_text(encoding="utf-8")

    assert "context.runtimeConfig.post_install_gate" in content
    assert "$installedFreshnessGateRel = [string]$context.runtimeConfig.post_install_gate" in content
    assert "Join-Path $context.repoRoot 'scripts\verify\vibe-installed-runtime-freshness-gate.ps1'" not in content
    assert "effective runtime config exists for runtime closure" in content
