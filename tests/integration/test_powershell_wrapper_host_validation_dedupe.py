from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_powershell_wrappers_delegate_host_validation_to_governance_helpers() -> None:
    install_content = (REPO_ROOT / 'install.ps1').read_text(encoding='utf-8')
    check_content = (REPO_ROOT / 'check.ps1').read_text(encoding='utf-8')
    uninstall_content = (REPO_ROOT / 'uninstall.ps1').read_text(encoding='utf-8')

    hardcoded_validateset = '[ValidateSet("codex", "claude-code", "cursor", "windsurf", "openclaw", "opencode")]'

    assert hardcoded_validateset not in install_content
    assert hardcoded_validateset not in check_content
    assert hardcoded_validateset not in uninstall_content

    assert '$HostId = Resolve-VgoHostId -HostId $HostId' in install_content
    assert '$HostId = Resolve-VgoHostId -HostId $HostId' in check_content
    assert '$HostId = Resolve-VgoHostId -HostId $HostId' in uninstall_content


def test_install_wrapper_rejects_invalid_host_via_shared_helper() -> None:
    result = subprocess.run(
        ['pwsh', '-NoProfile', '-File', './install.ps1', '-HostId', 'invalid-host', '-Profile', 'minimal'],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert 'Unsupported VCO host id' in (result.stdout + result.stderr)


def test_uninstall_wrapper_rejects_invalid_host_via_shared_helper() -> None:
    result = subprocess.run(
        ['pwsh', '-NoProfile', '-File', './uninstall.ps1', '-HostId', 'invalid-host', '-Profile', 'minimal'],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert 'Unsupported VCO host id' in (result.stdout + result.stderr)


def test_check_wrapper_rejects_invalid_host_via_shared_helper() -> None:
    result = subprocess.run(
        ['pwsh', '-NoProfile', '-File', './check.ps1', '-HostId', 'invalid-host', '-Profile', 'minimal'],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert 'Unsupported VCO host id' in (result.stdout + result.stderr)
