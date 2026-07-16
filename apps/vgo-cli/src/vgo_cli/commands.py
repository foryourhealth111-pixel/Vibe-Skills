from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

from .core_bridge import run_canonical_entry_core, run_compatibility_exit_core, run_entry_locator_core, run_inspect_run_core, run_local_kernel_core, run_router_core, run_skill_index_core
from .errors import CliError
from .output import print_json_payload
from .process import print_process_output, run_powershell_file, run_subprocess
from .repo import get_installed_runtime_config, get_local_release_metadata
from .workspace import extend_workspace_package_path


def _resolve_skills_dir(raw_value: str) -> Path:
    if str(raw_value or '').strip():
        return Path(raw_value).expanduser().resolve()
    return (Path.home() / '.agents' / 'skills').resolve()


def _git_text(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ['git', *args],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise CliError(f"Unable to read source git state: {result.stderr.strip()}")
    return result.stdout.strip()


def _source_git_state(repo_root: Path) -> tuple[str, bool]:
    try:
        commit = _git_text(repo_root, 'rev-parse', 'HEAD')
        dirty = bool(_git_text(repo_root, 'status', '--porcelain'))
    except CliError:
        return "unknown", True
    return commit, dirty


def _load_public_release_bundle(source_root: Path) -> dict[str, object] | None:
    bundle_path = source_root / "release-bundle.json"
    if not bundle_path.is_file():
        return None
    payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise CliError(f"Expected JSON object: {bundle_path}")
    return payload


def _local_release_version(source_root: Path) -> str:
    try:
        return str(get_local_release_metadata(source_root).get("version") or "").strip()
    except Exception:
        return ""


def _install_source_kwargs(source_root: Path) -> dict[str, object]:
    bundle = _load_public_release_bundle(source_root)
    if bundle is not None:
        public_install = bundle.get("public_install") or {}
        if str(public_install.get("source_kind") or "").strip() == "public_release":
            release = bundle.get("release") or {}
            asset = bundle.get("asset") or {}
            version = str(release.get("version") or "").strip()
            asset_name = str(asset.get("file_name") or "").strip()
            if not version or not asset_name:
                raise CliError("Public release bundle is missing release version or asset name.")
            digest = str(asset.get("payload_digest_sha256") or "").strip()
            return {
                "source_kind": "public_release",
                "release_version": version,
                "release_asset_name": asset_name,
                "release_asset_digest": digest,
                "installer_version": version,
                "package_version": version,
            }

    commit, dirty = _source_git_state(source_root)
    version = _local_release_version(source_root) or "0.1.0"
    return {
        "source_kind": "developer_repo",
        "source_git_commit": commit,
        "source_git_dirty": dirty,
        "installer_version": version,
        "package_version": version,
    }


def install_command(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    skills_dir = _resolve_skills_dir(args.skills_dir)
    extend_workspace_package_path(repo_root)
    from vgo_installer.simple_skill_installer import install_vibe_skill

    receipt = install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
        **_install_source_kwargs(repo_root),
    )
    print_json_payload(receipt)
    return 0


def uninstall_command(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    skills_dir = _resolve_skills_dir(args.skills_dir)
    extend_workspace_package_path(repo_root)
    from vgo_installer.simple_skill_installer import uninstall_vibe_skill

    print_json_payload(uninstall_vibe_skill(skills_dir=skills_dir))
    return 0


def update_command(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    skills_dir = _resolve_skills_dir(args.skills_dir)
    extend_workspace_package_path(repo_root)
    from vgo_installer.simple_skill_installer import update_vibe_skill

    receipt = update_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
        **_install_source_kwargs(repo_root),
    )
    print_json_payload(receipt)
    return 0


def check_command(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    skills_dir = _resolve_skills_dir(args.skills_dir)
    extend_workspace_package_path(repo_root)
    from vgo_installer.simple_skill_installer import check_vibe_skill

    result = check_vibe_skill(skills_dir=skills_dir)
    print_json_payload(result)
    return 0 if result.get("ok") else 1


def upgrade_command(args: argparse.Namespace) -> int:
    print("[WARN] The upgrade command is deprecated; use update with --skills-dir.", file=sys.stderr)
    if not hasattr(args, "skills_dir"):
        args.skills_dir = ""
    return update_command(args)


def _require_powershell_frontend(
    args: argparse.Namespace,
    *,
    command_name: str,
    proof_hint: str,
) -> None:
    if args.frontend == 'powershell':
        return
    raise CliError(
        f"{command_name} is a PowerShell-first operator command. "
        f"It does not fall back to check.sh. Use `check` when you need `installed locally` proof; "
        f"use the returned runtime artifacts when you need {proof_hint}."
    )


def index_command(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    command = ['--agent-root', args.agent_root]
    if getattr(args, 'host_id', None):
        command.extend(['--host-id', args.host_id])
    if getattr(args, 'workspace_root', None):
        command.extend(['--workspace-root', args.workspace_root])
    if getattr(args, 'json', False):
        command.append('--json')
    result = run_skill_index_core(repo_root, command)
    print_process_output(result)
    return int(result.returncode)


def run_command(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    command = [
        '--agent-root', args.agent_root,
        '--prompt', args.prompt,
    ]
    if getattr(args, 'run_id', None):
        command.extend(['--run-id', args.run_id])
    if getattr(args, 'host_id', None):
        command.extend(['--host-id', args.host_id])
    if getattr(args, 'workspace_root', None):
        command.extend(['--workspace-root', args.workspace_root])
    if getattr(args, 'json', False):
        command.append('--json')
    result = run_local_kernel_core(repo_root, command)
    print_process_output(result)
    return int(result.returncode)


def inspect_run_command(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    command = [
        '--agent-root', args.agent_root,
        '--run-id', args.run_id,
    ]
    if getattr(args, 'host_id', None):
        command.extend(['--host-id', args.host_id])
    if getattr(args, 'workspace_root', None):
        command.extend(['--workspace-root', args.workspace_root])
    result = run_inspect_run_core(repo_root, command)
    print_process_output(result)
    return int(result.returncode)


def locate_entry_command(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    command = [
        '--repo-root', str(repo_root),
        '--change-kind', args.change_kind,
    ]
    result = run_entry_locator_core(repo_root, command)
    print_process_output(result)
    return int(result.returncode)


def compatibility_exit_command(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    command = [
        '--repo-root', str(repo_root),
    ]
    result = run_compatibility_exit_core(repo_root, command)
    print_process_output(result)
    return int(result.returncode)


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
    output_json_path = str(getattr(args, 'output_json_path', '') or '').strip()
    if output_json_path:
        if result.returncode != 0:
            print_process_output(result)
            return int(result.returncode)
        Path(output_json_path).write_text(result.stdout or "", encoding="utf-8")
        if result.stderr:
            print_process_output(
                subprocess.CompletedProcess(
                    args=result.args,
                    returncode=result.returncode,
                    stdout="",
                    stderr=result.stderr,
                )
            )
        return int(result.returncode)
    print_process_output(result)
    return int(result.returncode)


def canonical_entry_command(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    command = [
        '--repo-root', str(repo_root),
        '--prompt', args.prompt,
    ]
    if getattr(args, 'host_id', None):
        command.extend(['--host-id', args.host_id])
    if getattr(args, 'entry_id', None):
        command.extend(['--entry-id', args.entry_id])
    if args.requested_stage_stop:
        command.extend(['--requested-stage-stop', args.requested_stage_stop])
    if args.requested_grade_floor:
        command.extend(['--requested-grade-floor', args.requested_grade_floor])
    if args.run_id:
        command.extend(['--run-id', args.run_id])
    if getattr(args, 'workspace_root', None):
        command.extend(['--workspace-root', args.workspace_root])
    if args.artifact_root:
        command.extend(['--artifact-root', args.artifact_root])
    if getattr(args, 'local_agent_root', None):
        command.extend(['--local-agent-root', args.local_agent_root])
    if getattr(args, 'continue_from_run_id', None):
        command.extend(['--continue-from-run-id', args.continue_from_run_id])
    if getattr(args, 'bounded_reentry_token', None):
        command.extend(['--bounded-reentry-token', args.bounded_reentry_token])
    if getattr(args, 'module_execution_json_file', None):
        command.extend(['--module-execution-json-file', args.module_execution_json_file])
    if getattr(args, 'host_decision_json', None):
        command.extend(['--host-decision-json', args.host_decision_json])
    if getattr(args, 'host_decision_json_file', None):
        command.extend(['--host-decision-json-file', args.host_decision_json_file])
    if args.force_runtime_neutral:
        command.append('--force-runtime-neutral')
    result = run_canonical_entry_core(repo_root, command)
    print_process_output(result)
    return int(result.returncode)


def verify_command(args: argparse.Namespace) -> int:
    _require_powershell_frontend(
        args,
        command_name='verify',
        proof_hint='`runtime coherent` proof',
    )
    repo_root = Path(args.repo_root).resolve()
    runtime_cfg = get_installed_runtime_config(repo_root)
    return passthrough_command(
        args,
        shell_script='check.sh',
        powershell_script=str(runtime_cfg['coherence_gate']),
    )


def runtime_command(args: argparse.Namespace) -> int:
    _require_powershell_frontend(
        args,
        command_name='runtime',
        proof_hint='`runtime coherent` proof',
    )
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
