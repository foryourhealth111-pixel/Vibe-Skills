from __future__ import annotations

import json
from pathlib import Path
import subprocess

from .core_bridge import run_installer_core
from .errors import CliError
from .external import maybe_install_external_dependencies
from .hosts import install_mode_for_host
from .install_support import reconcile_install_postconditions
from .output import parse_json_output
from .process import run_powershell_file, run_subprocess
from .repo import (
    get_local_release_metadata,
    get_official_self_repo_metadata,
    get_repo_head_commit,
    resolve_canonical_repo_root,
)
from .upgrade_state import load_upgrade_status, merge_upgrade_status, save_upgrade_status, is_upstream_cache_stale


def resolve_upgrade_repo_root(repo_root: Path) -> Path | None:
    return resolve_canonical_repo_root(repo_root)


def refresh_installed_status(repo_root: Path, target_root: Path, host_id: str) -> dict[str, object]:
    official_repo = get_official_self_repo_metadata(repo_root)
    release = get_local_release_metadata(repo_root)
    merged = merge_upgrade_status(
        load_upgrade_status(target_root),
        installed={
            'host_id': host_id,
            'target_root': target_root,
            'repo_remote': official_repo.get('repo_url'),
            'repo_default_branch': official_repo.get('default_branch'),
            'installed_version': release.get('version'),
            'installed_commit': get_repo_head_commit(repo_root),
            'installed_recorded_at': None,
        },
    )
    save_upgrade_status(target_root, merged)
    return merged


def refresh_upstream_status(repo_root: Path, target_root: Path, current_status: dict[str, object]) -> dict[str, object]:
    if not is_upstream_cache_stale(current_status):
        return current_status

    repo_url = str(current_status.get('repo_remote') or '').strip()
    branch = str(current_status.get('repo_default_branch') or 'main').strip() or 'main'
    fetch_result = run_subprocess(['git', 'fetch', '--quiet', repo_url, branch], cwd=repo_root)
    if fetch_result.returncode != 0:
        raise CliError(fetch_result.stderr.strip() or 'Failed to refresh upstream repository state.')

    commit_result = run_subprocess(['git', 'rev-parse', 'FETCH_HEAD'], cwd=repo_root)
    if commit_result.returncode != 0:
        raise CliError(commit_result.stderr.strip() or 'Failed to resolve fetched upstream commit.')

    release_result = run_subprocess(['git', 'show', 'FETCH_HEAD:config/version-governance.json'], cwd=repo_root)
    if release_result.returncode != 0:
        raise CliError(release_result.stderr.strip() or 'Failed to read fetched release metadata.')
    release_payload = json.loads(release_result.stdout or '{}')
    release = release_payload.get('release') or {}

    merged = merge_upgrade_status(
        current_status,
        remote={
            'remote_latest_commit': commit_result.stdout.strip(),
            'remote_latest_version': str(release.get('version') or '').strip(),
            'remote_latest_checked_at': None,
        },
    )
    save_upgrade_status(target_root, merged)
    return merged


def reset_repo_to_official_head(repo_root: Path, branch: str) -> None:
    commands = (
        ['git', 'reset', '--hard', 'HEAD'],
        ['git', 'clean', '-fd'],
        ['git', 'checkout', '-B', branch, 'FETCH_HEAD'],
        ['git', 'reset', '--hard', 'FETCH_HEAD'],
    )
    for command in commands:
        result = run_subprocess(command, cwd=repo_root)
        if result.returncode != 0:
            raise CliError(result.stderr.strip() or f'Failed to reset repository to official {branch} state.')


def reinstall_runtime(
    *,
    repo_root: Path,
    target_root: Path,
    host_id: str,
    profile: str,
    frontend: str,
    install_external: bool,
    strict_offline: bool,
    require_closed_ready: bool,
    allow_external_skill_fallback: bool,
    skip_runtime_freshness_gate: bool,
) -> None:
    install_mode = install_mode_for_host(host_id)
    command = [
        '--repo-root', str(repo_root),
        '--target-root', str(target_root),
        '--host', host_id,
        '--profile', profile,
    ]
    if require_closed_ready:
        command.append('--require-closed-ready')
    if allow_external_skill_fallback:
        command.append('--allow-external-skill-fallback')

    install_result = run_installer_core(repo_root, command)
    payload = parse_json_output(install_result)
    external_fallback_used = list(payload.get('external_fallback_used') or [])

    if install_external:
        maybe_install_external_dependencies(
            repo_root,
            str(payload.get('install_mode') or install_mode),
            strict_offline=bool(strict_offline),
        )

    reconcile_install_postconditions(
        repo_root,
        target_root,
        host_id,
        profile=profile,
        install_external=bool(install_external),
        frontend=frontend,
        external_fallback_used=external_fallback_used,
        strict_offline=bool(strict_offline),
        skip_runtime_freshness_gate=bool(skip_runtime_freshness_gate),
        include_frontmatter=frontend == 'powershell',
    )


def run_upgrade_check(*, repo_root: Path, target_root: Path, host_id: str, profile: str, frontend: str) -> subprocess.CompletedProcess[str]:
    if frontend == 'powershell':
        return run_powershell_file(
            repo_root / 'check.ps1',
            '-HostId',
            host_id,
            '-Profile',
            profile,
            '-TargetRoot',
            str(target_root),
        )
    return run_subprocess(
        [
            'bash',
            str(repo_root / 'check.sh'),
            '--host',
            host_id,
            '--profile',
            profile,
            '--target-root',
            str(target_root),
        ]
    )


def upgrade_runtime(
    *,
    repo_root: Path,
    target_root: Path,
    host_id: str,
    profile: str,
    frontend: str,
    install_external: bool,
    strict_offline: bool,
    require_closed_ready: bool,
    allow_external_skill_fallback: bool,
    skip_runtime_freshness_gate: bool,
) -> dict[str, object]:
    resolved_repo_root = resolve_upgrade_repo_root(repo_root)
    if resolved_repo_root is None:
        raise CliError(
            'Upgrade requires a canonical git checkout with config/version-governance.json. '
            'Pass --repo-root pointing at a Vibe-Skills git checkout before invoking the upgrade runtime.'
        )

    before = refresh_installed_status(resolved_repo_root, target_root, host_id)
    status = refresh_upstream_status(resolved_repo_root, target_root, before)
    if not bool(status.get('update_available')):
        print(
            'Vibe-Skills already current: '
            f"local={status.get('installed_version') or 'unknown'}@{status.get('installed_commit') or 'unknown'}"
        )
        return {'changed': False, 'before': before, 'after': status}

    branch = str(status.get('repo_default_branch') or 'main').strip() or 'main'
    reset_repo_to_official_head(resolved_repo_root, branch)
    reinstall_runtime(
        repo_root=resolved_repo_root,
        target_root=target_root,
        host_id=host_id,
        profile=profile,
        frontend=frontend,
        install_external=install_external,
        strict_offline=strict_offline,
        require_closed_ready=require_closed_ready,
        allow_external_skill_fallback=allow_external_skill_fallback,
        skip_runtime_freshness_gate=skip_runtime_freshness_gate,
    )
    check_result = run_upgrade_check(
        repo_root=resolved_repo_root,
        target_root=target_root,
        host_id=host_id,
        profile=profile,
        frontend=frontend,
    )
    if check_result.returncode != 0:
        raise CliError(check_result.stderr.strip() or check_result.stdout.strip() or 'Upgrade check failed.')

    after = refresh_installed_status(resolved_repo_root, target_root, host_id)
    print(
        'Vibe-Skills upgraded: '
        f"before={before.get('installed_version') or 'unknown'}@{before.get('installed_commit') or 'unknown'} "
        f"after={after.get('installed_version') or 'unknown'}@{after.get('installed_commit') or 'unknown'}"
    )
    return {'changed': True, 'before': before, 'after': after}
