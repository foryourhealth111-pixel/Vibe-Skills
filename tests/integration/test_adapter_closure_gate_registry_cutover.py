from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_adapter_closure_gate_reads_registry_directly() -> None:
    content = (REPO_ROOT / 'scripts' / 'verify' / 'vgo-adapter-closure-gate.ps1').read_text(encoding='utf-8')

    assert r'scripts\common\Resolve-VgoAdapter.ps1' not in content
    assert r'config\adapter-registry.json' in content
    assert r'adapters\index.json' in content
