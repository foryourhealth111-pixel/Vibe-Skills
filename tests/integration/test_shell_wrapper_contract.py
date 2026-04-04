from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_shell_wrappers_delegate_to_vgo_cli() -> None:
    install_content = (REPO_ROOT / 'install.sh').read_text(encoding='utf-8')
    uninstall_content = (REPO_ROOT / 'uninstall.sh').read_text(encoding='utf-8')

    assert 'vgo_cli.main' in install_content
    assert 'vgo_cli.main' in uninstall_content
    assert 'scripts/install/install_vgo_adapter.py' not in install_content
    assert 'scripts/uninstall/uninstall_vgo_adapter.py' not in uninstall_content
    assert 'no longer falls back to legacy installer scripts' in install_content
    assert 'no longer falls back to legacy uninstall scripts' in uninstall_content
