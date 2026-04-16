from __future__ import annotations

import argparse
from pathlib import Path

from .core_bridge import run_canonical_entry_core, run_installer_core, run_router_core, run_uninstaller_core
from .errors import CliError
from .external import maybe_install_external_dependencies
from .hosts import (
    assert_target_root_matches_host_intent,
    install_mode_for_host,
    normalize_host_id,
    resolve_target_root,
)
from .install_support import reconcile_install_postconditions
from .output import parse_json_output, print_install_banner, print_install_completion_hint
from .process import print_process_output, run_powershell_file, run_subprocess
from .repo import get_installed_runtime_config
from .upgrade_service import upgrade_runtime


def install_command(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    host_id = normalize_host_id(args.host)
    target_root = resolve_target_root(host_id, args.target_root)
    assert_target_root_matches_host_intent(target_root, host_id)
    target_root.mkdir(parents=True, exist_ok=True)

    install_mode = install_mode_for_host(host_id)
    print_install_banner(host_id, install_mode, args.profile, target_root, args)

    command = [
        '--repo-root', str(repo_root),
        '--target-root', str(target_root),
        '--host', host_id,
        '--profile', args.profile,
    ]
    if args.require_closed_ready:
        command.append('--require-closed-ready')
    if args.allow_external_skill_fallback:
        command.append('--allow-external-skill-fallback')

    install_result = run_installer_core(repo_root, command)
    payload = parse_json_output(install_result)
    external_fallback_used = list(payload.get('external_fallback_used') or [])

    if args.install_external and not args.strict_offline:
        maybe_install_external_dependencies(
            repo_root,
            str(payload.get('install_mode') or install_mode),
            strict_offline=bool(args.strict_offline),
        )

    reconcile_install_postconditions(
        repo_root,
        target_root,
        host_id,
        profile=args.profile,
        install_external=bool(args.install_external),
        frontend=args.frontend,
        external_fallback_used=external_fallback_used,
        strict_offline=bool(args.strict_offline),
        skip_runtime_freshness_gate=bool(args.skip_runtime_freshness_gate),
        include_frontmatter=args.frontend == 'powershell',
    )
    print_install_completion_hint(args.frontend, host_id=host_id, profile=args.profile, target_root=target_root)
    return 0


def uninstall_command(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    host_id = normalize_host_id(args.host)
    target_root = resolve_target_root(host_id, args.target_root)
    assert_target_root_matches_host_intent(target_root, host_id)

    command = [
        '--repo-root', str(repo_root),
        '--target-root', str(target_root),
        '--host', host_id,
        '--profile', args.profile,
    ]
    if args.preview:
        command.append('--preview')
    if args.purge_empty_dirs:
        command.append('--purge-empty-dirs')
    if args.strict_owned_only:
        command.append('--strict-owned-only')
    result = run_uninstaller_core(repo_root, command)
    print_process_output(result)
    return int(result.returncode)


def upgrade_command(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    host_id = normalize_host_id(args.host)
    target_root = resolve_target_root(host_id, args.target_root)
    assert_target_root_matches_host_intent(target_root, host_id)
    target_root.mkdir(parents=True, exist_ok=True)

    upgrade_runtime(
        repo_root=repo_root,
        target_root=target_root,
        host_id=host_id,
        profile=args.profile,
        frontend=args.frontend,
        install_external=bool(args.install_external),
        strict_offline=bool(args.strict_offline),
        require_closed_ready=bool(args.require_closed_ready),
        allow_external_skill_fallback=bool(args.allow_external_skill_fallback),
        skip_runtime_freshness_gate=bool(args.skip_runtime_freshness_gate),
    )
    return 0


def route_command(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()

    command = [
        '--prompt', args.prompt,
        '--grade', args.grade,
        '--task-type', args.task_type,
    ]
    if args.requested_skill:
        command.extend(['--requested-skill', args.requested_skill])
    if args.host_id:
        command.extend(['--host-id', args.host_id])
    if args.target_root:
        command.extend(['--target-root', args.target_root])
    if args.force_runtime_neutral:
        command.append('--force-runtime-neutral')

    result = run_router_core(repo_root, command)
    print_process_output(result)
    return int(result.returncode)


def canonical_entry_command(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    host_id = normalize_host_id(args.host_id)
    command = [
        '--repo-root', str(repo_root),
        '--host-id', host_id,
        '--entry-id', args.entry_id,
        '--prompt', args.prompt,
    ]
    if args.requested_stage_stop:
        command.extend(['--requested-stage-stop', args.requested_stage_stop])
    if args.requested_grade_floor:
        command.extend(['--requested-grade-floor', args.requested_grade_floor])
    if args.run_id:
        command.extend(['--run-id', args.run_id])
    if args.artifact_root:
        command.extend(['--artifact-root', args.artifact_root])
    if args.force_runtime_neutral:
        command.append('--force-runtime-neutral')
    result = run_canonical_entry_core(repo_root, command)
    print_process_output(result)
    return int(result.returncode)


def verify_command(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    runtime_cfg = get_installed_runtime_config(repo_root)
    return passthrough_command(
        args,
        shell_script='check.sh',
        powershell_script=str(runtime_cfg['coherence_gate']),
    )


def runtime_command(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    runtime_cfg = get_installed_runtime_config(repo_root)
    return passthrough_command(
        args,
        shell_script='check.sh',
        powershell_script=str(runtime_cfg['runtime_entrypoint']),
    )


def passthrough_command(args: argparse.Namespace, *, shell_script: str, powershell_script: str) -> int:
    repo_root = Path(args.repo_root).resolve()
    script_path = repo_root / (powershell_script if args.frontend == 'powershell' else shell_script)
    if args.frontend == 'powershell':
        result = run_powershell_file(script_path, *args.rest)
    else:
        result = run_subprocess(['bash', str(script_path), *args.rest])
    print_process_output(result)
    return int(result.returncode)
