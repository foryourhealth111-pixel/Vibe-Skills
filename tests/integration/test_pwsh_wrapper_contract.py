from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_powershell_wrappers_delegate_to_vgo_cli() -> None:
    install_content = (REPO_ROOT / 'install.ps1').read_text(encoding='utf-8')
    uninstall_content = (REPO_ROOT / 'uninstall.ps1').read_text(encoding='utf-8')

    assert 'vgo_cli.main' in install_content
    assert 'vgo_cli.main' in uninstall_content
    assert 'falling back to legacy PowerShell installer dispatch' in install_content
    assert 'falling back to legacy PowerShell uninstall dispatch' in uninstall_content
