from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_SRC = REPO_ROOT / 'apps' / 'vgo-cli' / 'src'
if str(CLI_SRC) not in sys.path:
    sys.path.insert(0, str(CLI_SRC))

from vgo_cli.repo import (
    get_installed_runtime_config,
    get_local_release_metadata,
    get_repo_head_commit,
    get_official_self_repo_metadata,
    resolve_canonical_repo_root,
)
from vgo_cli import repo as cli_repo


def test_get_installed_runtime_config_merges_defaults_with_governance_overrides(tmp_path: Path) -> None:
    repo_root = tmp_path / 'repo'
    (repo_root / 'config').mkdir(parents=True)
    (repo_root / 'config' / 'version-governance.json').write_text(
        '{"runtime": {"installed_runtime": {"post_install_gate": "scripts/verify/custom-gate.ps1"}}}',
        encoding='utf-8',
    )

    payload = get_installed_runtime_config(repo_root)

    assert payload['post_install_gate'] == 'scripts/verify/custom-gate.ps1'
    assert payload['receipt_relpath'] == 'skills/vibe/.vibeskills/install-receipt.json'
    assert payload['frontmatter_gate'] == 'scripts/verify/vibe-bom-frontmatter-gate.ps1'
    assert payload['coherence_gate'] == 'scripts/verify/vibe-release-install-runtime-coherence-gate.ps1'
    assert payload['runtime_entrypoint'] == 'scripts/runtime/invoke-vibe-runtime.ps1'


def test_resolve_canonical_repo_root_prefers_outer_git_root_with_governance(tmp_path: Path) -> None:
    repo_root = tmp_path / 'outer'
    nested = repo_root / 'apps' / 'vgo-cli' / 'src'
    nested.mkdir(parents=True)
    (repo_root / '.git').mkdir()
    (repo_root / 'config').mkdir()
    (repo_root / 'config' / 'version-governance.json').write_text('{}', encoding='utf-8')

    assert resolve_canonical_repo_root(nested) == repo_root
    assert resolve_canonical_repo_root(tmp_path) is None


def test_get_official_self_repo_metadata_reads_explicit_governance_source(tmp_path: Path) -> None:
    repo_root = tmp_path / 'repo'
    (repo_root / 'config').mkdir(parents=True)
    (repo_root / 'config' / 'version-governance.json').write_text(
        (
            '{"source_of_truth": {"canonical_root": ".", "official_self_repo": '
            '{"repo_url": "https://example.com/Vibe-Skills.git", "default_branch": "main"}}}'
        ),
        encoding='utf-8',
    )

    payload = get_official_self_repo_metadata(repo_root)

    assert payload == {
        'repo_url': 'https://example.com/Vibe-Skills.git',
        'default_branch': 'main',
        'canonical_root': '.',
    }


def test_real_version_governance_declares_official_self_repo_metadata() -> None:
    payload = get_official_self_repo_metadata(REPO_ROOT)


def test_get_official_self_repo_metadata_defaults_branch_to_main_when_missing(tmp_path: Path) -> None:
    repo_root = tmp_path / 'repo'
    (repo_root / 'config').mkdir(parents=True)
    (repo_root / 'config' / 'version-governance.json').write_text(
        '{"source_of_truth": {"canonical_root": "."}}',
        encoding='utf-8',
    )

    payload = get_official_self_repo_metadata(repo_root)

    assert payload == {
        'repo_url': '',
        'default_branch': 'main',
        'canonical_root': '.',
    }


def test_get_official_self_repo_metadata_falls_back_to_git_origin_url(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_root = tmp_path / 'repo'
    (repo_root / 'config').mkdir(parents=True)
    (repo_root / 'config' / 'version-governance.json').write_text(
        '{"source_of_truth": {"canonical_root": "."}}',
        encoding='utf-8',
    )

    def fake_run(
        command: list[str],
        *,
        cwd: Path | None = None,
        capture_output: bool,
        text: bool,
        check: bool = False,
        timeout: int | None = None,
    ) -> subprocess.CompletedProcess[str]:
        if command == ['git', '-C', str(repo_root), 'config', '--get', 'remote.origin.url']:
            return subprocess.CompletedProcess(command, 0, stdout='https://github.com/foryourhealth111-pixel/Vibe-Skills.git\n', stderr='')
        if command == ['git', '-C', str(repo_root), 'symbolic-ref', 'refs/remotes/origin/HEAD']:
            return subprocess.CompletedProcess(command, 1, stdout='', stderr='missing ref')
        raise AssertionError(f'unexpected command: {command}')

    monkeypatch.setattr('vgo_cli.repo.subprocess.run', fake_run)

    payload = get_official_self_repo_metadata(repo_root)

    assert payload == {
        'repo_url': 'https://github.com/foryourhealth111-pixel/Vibe-Skills.git',
        'default_branch': 'main',
        'canonical_root': '.',
    }


def test_get_local_release_metadata_reads_release_block(tmp_path: Path) -> None:
    repo_root = tmp_path / 'repo'
    (repo_root / 'config').mkdir(parents=True)
    (repo_root / 'config' / 'version-governance.json').write_text(
        '{"release": {"version": "3.0.1", "updated": "2026-04-09", "channel": "stable"}}',
        encoding='utf-8',
    )

    payload = get_local_release_metadata(repo_root)

    assert payload == {
        'version': '3.0.1',
        'updated': '2026-04-09',
        'channel': 'stable',
    }


def test_get_repo_head_commit_reads_git_rev_parse(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_root = tmp_path / 'repo'
    repo_root.mkdir(parents=True)

    def fake_run(
        command: list[str],
        *,
        cwd: Path | None = None,
        capture_output: bool,
        text: bool,
        check: bool = False,
        timeout: int | None = None,
    ) -> subprocess.CompletedProcess[str]:
        assert command == ['git', '-C', str(repo_root), 'rev-parse', 'HEAD']
        assert cwd is None
        assert capture_output is True
        assert text is True
        assert timeout == cli_repo._GIT_CAPTURE_TIMEOUT_SECONDS
        return subprocess.CompletedProcess(command, 0, stdout='deadbeef\n', stderr='')

    monkeypatch.setattr('vgo_cli.repo.subprocess.run', fake_run)

    assert get_repo_head_commit(repo_root) == 'deadbeef'


def test_get_repo_head_commit_returns_empty_when_git_executable_is_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo_root = tmp_path / 'repo'
    repo_root.mkdir(parents=True)

    def fake_run(
        command: list[str],
        *,
        cwd: Path | None = None,
        capture_output: bool,
        text: bool,
        check: bool = False,
        timeout: int | None = None,
    ) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError(command[0])

    monkeypatch.setattr('vgo_cli.repo.subprocess.run', fake_run)

    assert get_repo_head_commit(repo_root) == ''


def test_get_repo_head_commit_returns_empty_when_git_command_times_out(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo_root = tmp_path / 'repo'
    repo_root.mkdir(parents=True)

    def fake_run(
        command: list[str],
        *,
        capture_output: bool,
        text: bool,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(command, 5)

    monkeypatch.setattr(cli_repo.subprocess, 'run', fake_run)

    assert get_repo_head_commit(repo_root) == ''
