from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_verification_runtime_gates_delegate_default_runtime_contract_to_contracts_package() -> None:
    policies = (REPO_ROOT / "packages" / "verification-core" / "src" / "vgo_verify" / "policies.py").read_text(encoding="utf-8")
    repo = (REPO_ROOT / "apps" / "vgo-cli" / "src" / "vgo_cli" / "repo.py").read_text(encoding="utf-8")
    install_gates = (REPO_ROOT / "apps" / "vgo-cli" / "src" / "vgo_cli" / "install_gates.py").read_text(encoding="utf-8")
    coherence_support = (REPO_ROOT / "packages" / "verification-core" / "src" / "vgo_verify" / "runtime_coherence_support.py").read_text(encoding="utf-8")
    coherence_runtime = (REPO_ROOT / "packages" / "verification-core" / "src" / "vgo_verify" / "runtime_coherence_runtime.py").read_text(encoding="utf-8")
    freshness = (REPO_ROOT / "packages" / "verification-core" / "src" / "vgo_verify" / "runtime_freshness.py").read_text(encoding="utf-8")
    coherence = (REPO_ROOT / "packages" / "verification-core" / "src" / "vgo_verify" / "runtime_coherence.py").read_text(encoding="utf-8")
    contract = (REPO_ROOT / "packages" / "contracts" / "src" / "vgo_contracts" / "installed_runtime_contract.py").read_text(encoding="utf-8")

    assert "vgo_contracts.installed_runtime_contract" in policies
    assert "merge_installed_runtime_config" in policies
    assert "default_installed_runtime_config" in repo
    assert "merge_installed_runtime_config" in repo
    assert "default_freshness_runtime_config" in freshness
    assert "default_coherence_runtime_config" in coherence
    assert "DEFAULT_INSTALLED_RUNTIME_FRONTMATTER_GATE" in contract
    assert "DEFAULT_INSTALLED_RUNTIME_NEUTRAL_FRESHNESS_GATE" in contract
    assert "DEFAULT_INSTALLED_RUNTIME_RUNTIME_ENTRYPOINT" in contract
    assert "def default_installed_runtime_config()" in contract
    assert "def merge_installed_runtime_config(" in contract
    assert "neutral_freshness_gate" in install_gates
    assert "neutral_freshness_gate" in coherence_support
    assert "frontmatter_gate" in coherence_runtime

    assert "defaults = {" not in repo
    assert 'runtime = ((governance.get("runtime") or {}).get("installed_runtime")) or {}' not in policies
    assert "DEFAULT_RUNTIME_CONFIG = {" not in freshness
    assert "DEFAULT_RUNTIME_CONFIG = {" not in coherence
