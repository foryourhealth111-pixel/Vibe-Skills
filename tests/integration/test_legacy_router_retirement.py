from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_legacy_router_is_retired_from_active_runtime_surfaces() -> None:
    legacy = REPO_ROOT / 'scripts' / 'router' / 'legacy' / 'resolve-pack-route.legacy.ps1'
    assert not legacy.exists()

    policy = (REPO_ROOT / 'config' / 'official-runtime-main-chain-policy.json').read_text(encoding='utf-8')
    gate = (REPO_ROOT / 'scripts' / 'verify' / 'vibe-router-contract-gate.ps1').read_text(encoding='utf-8')

    assert 'resolve-pack-route.legacy.ps1' not in policy
    assert 'resolve-pack-route.legacy.ps1' not in gate
