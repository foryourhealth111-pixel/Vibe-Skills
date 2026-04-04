from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_python_packaging_contract_consumers_delegate_to_shared_contract_owner() -> None:
    runtime_contracts = (REPO_ROOT / "scripts" / "common" / "runtime_contracts.py").read_text(encoding="utf-8")
    policies = (REPO_ROOT / "packages" / "verification-core" / "src" / "vgo_verify" / "policies.py").read_text(encoding="utf-8")

    assert "vgo_contracts.runtime_surface_contract" in runtime_contracts
    assert "vgo_contracts.runtime_surface_contract" in policies

    assert "DEFAULT_PACKAGING_FILES = (" not in runtime_contracts
    assert "DEFAULT_PACKAGING_FILES = (" not in policies
    assert "def is_ignored_runtime_artifact(" not in policies
    assert "def resolve_packaging_contract(" not in policies
