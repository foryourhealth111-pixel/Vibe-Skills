from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_powershell_install_and_uninstall_wrappers_delegate_to_vgo_cli() -> None:
    install_content = (REPO_ROOT / 'install.ps1').read_text(encoding='utf-8')
    check_content = (REPO_ROOT / 'check.ps1').read_text(encoding='utf-8')
    uninstall_content = (REPO_ROOT / 'uninstall.ps1').read_text(encoding='utf-8')

    assert 'vgo_cli.main' in install_content
    assert 'vgo_cli.main' in uninstall_content
    assert 'scripts\\install\\Install-VgoAdapter.ps1' not in install_content
    assert 'scripts\\check\\Check-VgoAdapter.ps1' not in check_content
    assert 'scripts\\uninstall\\Uninstall-VgoAdapter.ps1' not in uninstall_content
    assert 'no longer falls back to legacy installer scripts' in install_content
    assert 'no longer falls back to legacy uninstall scripts' in uninstall_content


def test_powershell_install_wrapper_keeps_codex_payload_contract_anchor() -> None:
    install_content = (REPO_ROOT / 'install.ps1').read_text(encoding='utf-8')

    assert 'plugins-manifest.codex.json' in install_content


def test_powershell_install_and_check_wrappers_define_explicit_help_path() -> None:
    install_content = (REPO_ROOT / 'install.ps1').read_text(encoding='utf-8')
    check_content = (REPO_ROOT / 'check.ps1').read_text(encoding='utf-8')

    for content in (install_content, check_content):
        assert "[Alias('?')]" in content
        assert 'Show-WrapperUsage' in content
        assert 'if ($Help)' in content


def test_check_wrapper_only_rewrites_launcher_paths_on_windows_hosts() -> None:
    check_content = (REPO_ROOT / 'check.ps1').read_text(encoding='utf-8')

    assert 'function Resolve-LocalPathForCheck' in check_content
    assert "[System.IO.Path]::DirectorySeparatorChar -ne '\\'" in check_content
