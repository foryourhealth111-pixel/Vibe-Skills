from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_powershell_compat_wrappers_delegate_to_package_cores() -> None:
    install_content = (REPO_ROOT / 'scripts' / 'install' / 'Install-VgoAdapter.ps1').read_text(encoding='utf-8')
    uninstall_content = (REPO_ROOT / 'scripts' / 'uninstall' / 'Uninstall-VgoAdapter.ps1').read_text(encoding='utf-8')

    assert 'vgo_installer.install_runtime' in install_content
    assert 'vgo_installer.uninstall_runtime' in uninstall_content
    assert 'scripts\\install\\install_vgo_adapter.py' not in install_content
    assert 'scripts\\uninstall\\uninstall_vgo_adapter.py' not in uninstall_content
    assert 'packages\\installer-core\\src' in install_content
    assert 'packages\\installer-core\\src' in uninstall_content
