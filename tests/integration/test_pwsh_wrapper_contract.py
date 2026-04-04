from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_powershell_wrappers_delegate_to_vgo_cli() -> None:
    install_content = (REPO_ROOT / 'install.ps1').read_text(encoding='utf-8')
    uninstall_content = (REPO_ROOT / 'uninstall.ps1').read_text(encoding='utf-8')

    assert 'vgo_cli.main' in install_content
    assert 'vgo_cli.main' in uninstall_content
    assert 'scripts\\install\\Install-VgoAdapter.ps1' not in install_content
    assert 'scripts\\uninstall\\Uninstall-VgoAdapter.ps1' not in uninstall_content
    assert 'no longer falls back to legacy installer scripts' in install_content
    assert 'no longer falls back to legacy uninstall scripts' in uninstall_content


def test_powershell_install_wrapper_keeps_codex_payload_contract_anchor() -> None:
    install_content = (REPO_ROOT / 'install.ps1').read_text(encoding='utf-8')

    assert 'plugins-manifest.codex.json' in install_content
