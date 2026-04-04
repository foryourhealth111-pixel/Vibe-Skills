from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_bootstrap_entrypoints_resolve_adapter_metadata_from_registry_surface() -> None:
    shell_content = (REPO_ROOT / 'scripts' / 'bootstrap' / 'one-shot-setup.sh').read_text(encoding='utf-8')
    powershell_content = (REPO_ROOT / 'scripts' / 'bootstrap' / 'one-shot-setup.ps1').read_text(encoding='utf-8')

    assert 'scripts/common/resolve_vgo_adapter.py' not in shell_content
    assert r'scripts\common\Resolve-VgoAdapter.ps1' not in powershell_content
    assert 'scripts/common/adapter_registry_query.py' in shell_content
    assert '--bootstrap-choice-lines' in shell_content
    assert '--supported-hosts' in shell_content
    assert 'Get-VgoBootstrapHostChoices' in powershell_content
    assert 'Get-VgoSupportedHostHint' in powershell_content
    assert r'config\adapter-registry.json' not in powershell_content
    assert r'adapters\index.json' not in powershell_content
    assert 'Pass --host codex|claude-code|cursor|windsurf|openclaw|opencode' not in shell_content
    assert 'Pass -HostId codex|claude-code|cursor|windsurf|openclaw|opencode' not in powershell_content
