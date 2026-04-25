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


def prepare_managed_upgrade_repo_root(repo_root: Path, target_root: Path) -> Path | None:
    if not (repo_root / 'config' / 'version-governance.json').exists():
        return None

    official_repo = get_official_self_repo_metadata(repo_root)
    repo_url = str(official_repo.get('repo_url') or '').strip()
    branch = str(official_repo.get('default_branch') or '').strip() or 'main'
    canonical_root = str(official_repo.get('canonical_root') or '.').strip() or '.'
    if not repo_url:
        raise CliError('Official self repository URL is not configured in version-governance.json.')

    checkout_root = target_root / '.vibeskills' / 'upgrade-source'
    checkout_root.parent.mkdir(parents=True, exist_ok=True)
    if (checkout_root / '.git').exists():
        fetch_result = run_subprocess(['git', 'fetch', '--quiet', repo_url, branch], cwd=checkout_root)
        if fetch_result.returncode != 0:
            raise CliError(fetch_result.stderr.strip() or 'Failed to refresh managed upgrade source checkout.')
    elif checkout_root.exists() and any(checkout_root.iterdir()):
        raise CliError(
            'Managed upgrade source path exists but is not a git checkout: '
            f'{checkout_root}. Remove or rename it before running vibe-upgrade.'
        )
    else:
        clone_result = run_subprocess(
            ['git', 'clone', '--quiet', '--branch', branch, '--single-branch', repo_url, str(checkout_root)],
            cwd=target_root,
        )
        if clone_result.returncode != 0:
            raise CliError(clone_result.stderr.strip() or 'Failed to clone managed upgrade source checkout.')

    candidate_root = (checkout_root / canonical_root).resolve()
    resolved = resolve_canonical_repo_root(candidate_root)
    if resolved is None:
        raise CliError('Managed upgrade source checkout is missing config/version-governance.json.')
    return resolved


def load_recorded_install_status(repo_root: Path, target_root: Path, host_id: str) -> dict[str, object]:
    existing = load_upgrade_status(target_root)
    repo_remote = str(existing.get('repo_remote') or '').strip()
    repo_default_branch = str(existing.get('repo_default_branch') or '').strip()
    if not repo_remote or not repo_default_branch:
        official_repo = get_official_self_repo_metadata(repo_root)
        repo_remote = repo_remote or str(official_repo.get('repo_url') or '').strip()
        repo_default_branch = repo_default_branch or str(official_repo.get('default_branch') or '').strip()
    return merge_upgrade_status(
        existing,
        installed={
            'host_id': host_id,
            'target_root': target_root,
            'repo_remote': repo_remote,
            'repo_default_branch': repo_default_branch,
            'installed_version': existing.get('installed_version'),
            'installed_commit': existing.get('installed_commit'),
            'installed_recorded_at': existing.get('installed_recorded_at'),
        },
    )


def has_recorded_install_truth(status: dict[str, object] | None) -> bool:
    return bool(
        str((status or {}).get('installed_version') or '').strip()
        and str((status or {}).get('installed_commit') or '').strip()
    )


def refresh_installed_status(
    repo_root: Path,
    target_root: Path,
    host_id: str,
    *,
    persist: bool = True,
) -> dict[str, object]:
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
    if persist:
        save_upgrade_status(target_root, merged)
    return merged


def refresh_upstream_status(
    repo_root: Path,
    target_root: Path,
    current_status: dict[str, object],
    *,
    force_refresh: bool = False,
) -> dict[str, object]:
    if not force_refresh and not is_upstream_cache_stale(current_status):
        return current_status

    repo_url = str(current_status.get('repo_remote') or '').strip()
    branch = str(current_status.get('repo_default_branch') or '').strip()
    if not repo_url or not branch:
        official_repo = get_official_self_repo_metadata(repo_root)
        repo_url = repo_url or str(official_repo.get('repo_url') or '').strip()
        branch = branch or str(official_repo.get('default_branch') or '').strip()
    branch = branch or 'main'
    if not repo_url:
        raise CliError('Official self repository URL is not configured in version-governance.json.')

    fetch_result = run_subprocess(['git', 'fetch', '--quiet', repo_url, branch], cwd=repo_root)
    if fetch_result.returncode != 0:
        raise CliError(fetch_result.stderr.strip() or 'Failed to refresh upstream repository state.')

    commit_result = run_subprocess(['git', 'rev-parse', 'FETCH_HEAD'], cwd=repo_root)
    if commit_result.returncode != 0:
        raise CliError(commit_result.stderr.strip() or 'Failed to resolve fetched upstream commit.')
    remote_commit = commit_result.stdout.strip()
    if not remote_commit:
        raise CliError('Failed to resolve fetched upstream commit.')

    release_result = run_subprocess(['git', 'show', f'{remote_commit}:config/version-governance.json'], cwd=repo_root)
    if release_result.returncode != 0:
        raise CliError(release_result.stderr.strip() or 'Failed to read fetched release metadata.')
    release_payload = json.loads(release_result.stdout or '{}')
    release = release_payload.get('release') or {}

    merged = merge_upgrade_status(
        current_status,
        remote={
            'remote_latest_commit': remote_commit,
            'remote_latest_version': str(release.get('version') or '').strip(),
            'remote_latest_checked_at': None,
        },
    )
    save_upgrade_status(target_root, merged)
    return merged


def reset_repo_to_official_head(repo_root: Path, branch: str, target_commit: str | None = None) -> None:
    target_ref = str(target_commit or '').strip() or 'FETCH_HEAD'
    commands = (
        ['git', 'reset', '--hard', 'HEAD'],
        ['git', 'clean', '-fd'],
        ['git', 'checkout', '-B', branch, target_ref],
        ['git', 'reset', '--hard', target_ref],
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
        resolved_repo_root = prepare_managed_upgrade_repo_root(repo_root, target_root)
    if resolved_repo_root is None:
        raise CliError(
            'Upgrade requires a canonical git checkout with config/version-governance.json. '
            'Pass --repo-root pointing at a Vibe-Skills git checkout before invoking the upgrade runtime.'
        )

    before = load_recorded_install_status(resolved_repo_root, target_root, host_id)
    install_truth_present = has_recorded_install_truth(before)
    status = refresh_upstream_status(resolved_repo_root, target_root, before, force_refresh=True)
    if install_truth_present and not bool(status.get('update_available')):
        print(
            'Vibe-Skills already current: '
            f"local={status.get('installed_version') or 'unknown'}@{status.get('installed_commit') or 'unknown'}"
        )
        return {'changed': False, 'before': before, 'after': status}

    branch = str(status.get('repo_default_branch') or 'main').strip() or 'main'
    target_commit = str(status.get('remote_latest_commit') or '').strip() or None
    reset_repo_to_official_head(resolved_repo_root, branch, target_commit)
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
