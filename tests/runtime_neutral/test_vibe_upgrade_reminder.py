from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import textwrap

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_SRC = REPO_ROOT / 'apps' / 'vgo-cli' / 'src'
if str(CLI_SRC) not in sys.path:
    sys.path.insert(0, str(CLI_SRC))

from vgo_cli.version_reminder import build_update_reminder


def test_build_update_reminder_refreshes_stale_cache_and_emits_advisory(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(
        'vgo_cli.version_reminder.load_recorded_install_status',
        lambda repo_root, target_root, host_id: {
            'installed_version': '3.0.0',
            'installed_commit': 'old',
            'repo_default_branch': 'main',
        },
    )
    monkeypatch.setattr('vgo_cli.version_reminder.has_recorded_install_truth', lambda status: True)
    monkeypatch.setattr('vgo_cli.version_reminder.is_upstream_cache_stale', lambda status: True)

    def fake_refresh(repo_root, target_root, current_status):
        calls.append('refresh')
        return {
            **current_status,
            'remote_latest_version': '3.0.1',
            'remote_latest_commit': 'new',
            'update_available': True,
        }

    monkeypatch.setattr('vgo_cli.version_reminder.refresh_upstream_status', fake_refresh)

    message = build_update_reminder(REPO_ROOT, REPO_ROOT / '.tmp-target', 'codex')

    assert calls == ['refresh']
    assert 'update available' in message.lower()
    assert 'local=3.0.0@old' in message
    assert 'latest=3.0.1@new' in message
    assert message.endswith('Run vibe-upgrade --host=codex.')


def test_build_update_reminder_uses_fresh_cache_without_refresh(monkeypatch) -> None:
    monkeypatch.setattr(
        'vgo_cli.version_reminder.load_recorded_install_status',
        lambda repo_root, target_root, host_id: {
            'installed_version': '3.0.0',
            'installed_commit': 'old',
            'remote_latest_version': '3.0.1',
            'remote_latest_commit': 'new',
            'remote_latest_checked_at': '2026-04-09T00:00:00Z',
            'update_available': True,
        },
    )
    monkeypatch.setattr('vgo_cli.version_reminder.has_recorded_install_truth', lambda status: True)
    monkeypatch.setattr('vgo_cli.version_reminder.is_upstream_cache_stale', lambda status: False)
    monkeypatch.setattr(
        'vgo_cli.version_reminder.refresh_upstream_status',
        lambda repo_root, target_root, current_status: (_ for _ in ()).throw(AssertionError('should not refresh')),
    )

    message = build_update_reminder(REPO_ROOT, REPO_ROOT / '.tmp-target', 'codex')

    assert 'latest=3.0.1@new' in message
    assert message.endswith('Run vibe-upgrade --host=codex.')


def test_build_update_reminder_returns_none_when_no_update_is_available(monkeypatch) -> None:
    monkeypatch.setattr(
        'vgo_cli.version_reminder.load_recorded_install_status',
        lambda repo_root, target_root, host_id: {
            'installed_version': '3.0.1',
            'installed_commit': 'same',
            'remote_latest_version': '3.0.1',
            'remote_latest_commit': 'same',
            'update_available': False,
        },
    )
    monkeypatch.setattr('vgo_cli.version_reminder.has_recorded_install_truth', lambda status: True)
    monkeypatch.setattr('vgo_cli.version_reminder.is_upstream_cache_stale', lambda status: False)

    assert build_update_reminder(REPO_ROOT, REPO_ROOT / '.tmp-target', 'codex') is None


def test_build_update_reminder_swallows_refresh_failures(monkeypatch) -> None:
    monkeypatch.setattr(
        'vgo_cli.version_reminder.load_recorded_install_status',
        lambda repo_root, target_root, host_id: {
            'installed_version': '3.0.0',
            'installed_commit': 'old',
            'repo_default_branch': 'main',
        },
    )
    monkeypatch.setattr('vgo_cli.version_reminder.has_recorded_install_truth', lambda status: True)
    monkeypatch.setattr('vgo_cli.version_reminder.is_upstream_cache_stale', lambda status: True)
    monkeypatch.setattr(
        'vgo_cli.version_reminder.refresh_upstream_status',
        lambda repo_root, target_root, current_status: (_ for _ in ()).throw(RuntimeError('network down')),
    )

    assert build_update_reminder(REPO_ROOT, REPO_ROOT / '.tmp-target', 'codex') is None


def test_build_update_reminder_returns_none_when_target_install_truth_is_missing(monkeypatch) -> None:
    monkeypatch.setattr(
        'vgo_cli.version_reminder.load_recorded_install_status',
        lambda repo_root, target_root, host_id: {
            'installed_version': '',
            'installed_commit': '',
            'remote_latest_version': '3.0.3',
            'remote_latest_commit': 'new',
            'update_available': True,
        },
    )
    monkeypatch.setattr('vgo_cli.version_reminder.has_recorded_install_truth', lambda status: False)
    monkeypatch.setattr('vgo_cli.version_reminder.is_upstream_cache_stale', lambda status: True)
    monkeypatch.setattr(
        'vgo_cli.version_reminder.refresh_upstream_status',
        lambda repo_root, target_root, current_status: (_ for _ in ()).throw(AssertionError('should not refresh')),
    )

    assert build_update_reminder(REPO_ROOT, REPO_ROOT / '.tmp-target', 'codex') is None


def test_powershell_upgrade_reminder_uses_python_command_spec(tmp_path: Path) -> None:
    powershell = shutil.which('pwsh') or shutil.which('pwsh.exe')
    if powershell is None:
        pytest.skip('PowerShell not available')
    runtime_common = REPO_ROOT / 'scripts' / 'runtime' / 'VibeRuntime.Common.ps1'
    if 'Get-VibeUpgradeReminder' not in runtime_common.read_text(encoding='utf-8'):
        pytest.skip('PowerShell upgrade reminder helper is not part of the current runtime contract')

    repo_root = tmp_path / 'repo'
    script_dir = repo_root / 'apps' / 'vgo-cli' / 'src' / 'vgo_cli'
    script_dir.mkdir(parents=True, exist_ok=True)
    (script_dir / 'version_reminder.py').write_text(
        'print("REMINDER: update available")\n',
        encoding='utf-8',
    )

    fake_target_root = tmp_path / 'target-root'
    fake_target_root.mkdir(parents=True, exist_ok=True)
    harness_path = tmp_path / 'invoke-reminder.ps1'
    harness_path.write_text(
        textwrap.dedent(
                f"""
                Set-StrictMode -Version Latest
                $ErrorActionPreference = 'Stop'
                . '{runtime_common.as_posix()}'
            function Resolve-VibeHostTargetRoot {{
                param([object]$HostAdapter)
                return '{fake_target_root.as_posix()}'
            }}
            function Get-VibeHostAdapterIdentityProjection {{
                param([object]$HostAdapter)
                return [pscustomobject]@{{ id = 'codex'; requested_id = 'codex' }}
            }}
            function Get-VgoPythonCommand {{
                return [pscustomobject]@{{ host_path = '{Path(sys.executable).as_posix()}'; prefix_arguments = @() }}
            }}
            $result = Get-VibeUpgradeReminder -RepoRoot '{repo_root.as_posix()}' -HostAdapter ([pscustomobject]@{{}})
            if ($null -eq $result) {{
                throw 'expected reminder output'
            }}
            Write-Output $result
            """
        ).strip()
        + '\n',
        encoding='utf-8',
    )

    completed = subprocess.run(
        [powershell, '-NoLogo', '-NoProfile', '-File', str(harness_path)],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == 'REMINDER: update available'
