from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_router_contract_gate_uses_frozen_fixture_instead_of_legacy_router() -> None:
    gate = (REPO_ROOT / 'scripts' / 'verify' / 'vibe-router-contract-gate.ps1').read_text(encoding='utf-8')

    assert 'router-contract-gate-golden.json' in gate
    assert 'resolve-pack-route.legacy.ps1' not in gate
