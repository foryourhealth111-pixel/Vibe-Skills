import os
from pathlib import Path
import shutil
import subprocess

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
INSTALL_SHIM = REPO_ROOT / 'scripts' / 'install' / 'Install-VgoAdapter.ps1'


def _run_install_shim(repo_root: Path, target_root: Path, *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    pwsh = shutil.which('pwsh')
    if pwsh is None:
        pytest.skip('pwsh is required for the PowerShell installer contract')
    return subprocess.run(
        [
            pwsh,
            '-NoLogo',
            '-NoProfile',
            '-NonInteractive',
            '-File',
            str(INSTALL_SHIM),
            '-RepoRoot',
            str(repo_root),
            '-TargetRoot',
            str(target_root),
            '-HostId',
            'codex',
        ],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        env=env,
        check=False,
    )


def test_powershell_compat_wrappers_delegate_to_package_cores() -> None:
    install_content = INSTALL_SHIM.read_text(encoding='utf-8')
    uninstall_content = (REPO_ROOT / 'scripts' / 'uninstall' / 'Uninstall-VgoAdapter.ps1').read_text(encoding='utf-8')

    assert 'vgo_installer.install_runtime' in install_content
    assert 'vgo_installer.uninstall_runtime' in uninstall_content
    assert 'scripts\\install\\install_vgo_adapter.py' not in install_content
    assert 'scripts\\uninstall\\uninstall_vgo_adapter.py' not in uninstall_content
    assert 'packages\\installer-core\\src' in install_content
    assert 'packages\\installer-core\\src' in uninstall_content


def test_powershell_installer_is_only_a_strict_python_core_delegate() -> None:
    install_content = INSTALL_SHIM.read_text(encoding='utf-8')

    assert 'installer-core is unavailable' in install_content
    assert 'Python 3 is required' in install_content
    assert '-specialist-wrapper.py' not in install_content
    assert '-specialist-wrapper.cmd' not in install_content
    assert '-specialist-wrapper.sh' not in install_content
    assert 'function Copy-DirContent' not in install_content
    assert 'function New-VgoHostSpecialistWrapper' not in install_content


def test_powershell_installer_fails_explicitly_when_installer_core_is_missing(tmp_path: Path) -> None:
    repo_root = tmp_path / 'repo'
    target_root = tmp_path / 'target'
    repo_root.mkdir()

    completed = _run_install_shim(repo_root, target_root)

    assert completed.returncode != 0
    assert 'installer-core is unavailable' in completed.stderr + completed.stdout


def test_powershell_installer_fails_explicitly_when_python_is_missing(tmp_path: Path) -> None:
    repo_root = tmp_path / 'repo'
    target_root = tmp_path / 'target'
    installer_core = repo_root / 'packages' / 'installer-core' / 'src' / 'vgo_installer' / 'install_runtime.py'
    installer_core.parent.mkdir(parents=True)
    installer_core.write_text('# test installer core\n', encoding='utf-8')
    empty_path = tmp_path / 'empty-path'
    empty_path.mkdir()
    env = os.environ.copy()
    env['PATH'] = str(empty_path)

    completed = _run_install_shim(repo_root, target_root, env=env)

    assert completed.returncode != 0
    assert 'Python 3 is required' in completed.stderr + completed.stdout
