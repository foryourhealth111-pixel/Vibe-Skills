from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

from .core_bridge import run_canonical_entry_core, run_compatibility_exit_core, run_entry_locator_core, run_inspect_run_core, run_local_kernel_core, run_router_core, run_skill_index_core
from .errors import (
    CliError,
    CliIoError,
    CliMissingResourceError,
    CliPermissionError,
    CliStateError,
    CliUnavailableError,
)
from .output import print_json_payload
from .process import print_process_output, run_powershell_file, run_subprocess
from .repo import get_installed_runtime_config, get_local_release_metadata
from .workspace import extend_workspace_package_path


PROJECT_URL = "https://github.com/foryourhealth111-pixel/Vibe-Skills"


def _installer_cli_error(exc: RuntimeError | OSError | ValueError) -> CliError:
    if isinstance(exc, PermissionError):
        return CliPermissionError(str(exc))
    if isinstance(exc, FileNotFoundError):
        return CliMissingResourceError(str(exc))
    if isinstance(exc, TimeoutError):
        return CliUnavailableError(str(exc))
    if isinstance(exc, OSError):
        return CliIoError(str(exc))
    return CliStateError(str(exc))


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
    try:
        payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise CliStateError(f"Unreadable public release bundle: {bundle_path}") from exc
    if not isinstance(payload, dict):
        raise CliStateError(f"Expected JSON object: {bundle_path}")
    return payload


def _bundle_mapping(
    bundle: dict[str, object],
    field_name: str,
    bundle_path: Path,
) -> dict[str, object]:
    value = bundle.get(field_name)
    if not isinstance(value, dict):
        raise CliStateError(f"Public release bundle field '{field_name}' must be an object: {bundle_path}")
    return value


def _bundle_required_text(
    mapping: dict[str, object],
    field_name: str,
    bundle_path: Path,
) -> str:
    value = mapping.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise CliStateError(f"Public release bundle field '{field_name}' must be non-empty text: {bundle_path}")
    return value.strip()


def _local_release_version(source_root: Path) -> str:
    try:
        return str(get_local_release_metadata(source_root).get("version") or "").strip()
    except Exception:
        return ""


def _install_source_kwargs(source_root: Path) -> dict[str, object]:
    bundle = _load_public_release_bundle(source_root)
    if bundle is not None:
        public_install_value = bundle.get("public_install")
        if public_install_value is None:
            public_install: dict[str, object] = {}
        elif isinstance(public_install_value, dict):
            public_install = public_install_value
        else:
            raise CliStateError(
                f"Public release bundle field 'public_install' must be an object: "
                f"{source_root / 'release-bundle.json'}"
            )
        source_kind = public_install.get("source_kind")
        if source_kind is not None and not isinstance(source_kind, str):
            raise CliStateError(
                f"Public release bundle field 'source_kind' must be text: "
                f"{source_root / 'release-bundle.json'}"
            )
        if str(source_kind or "").strip() == "public_release":
            bundle_path = source_root / "release-bundle.json"
            release = _bundle_mapping(bundle, "release", bundle_path)
            asset = _bundle_mapping(bundle, "asset", bundle_path)
            version = _bundle_required_text(release, "version", bundle_path)
            asset_name = _bundle_required_text(asset, "file_name", bundle_path)
            digest_value = asset.get("payload_digest_sha256")
            if digest_value is not None and not isinstance(digest_value, str):
                raise CliStateError(
                    f"Public release bundle field 'payload_digest_sha256' must be text: {bundle_path}"
                )
            digest = str(digest_value or "").strip()
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

    try:
        receipt = install_vibe_skill(
            repo_root=repo_root,
            skills_dir=skills_dir,
            installed_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
            **_install_source_kwargs(repo_root),
        )
    except (RuntimeError, OSError, ValueError) as exc:
        raise _installer_cli_error(exc) from exc
    print_json_payload(receipt)
    return 0


def uninstall_command(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    skills_dir = _resolve_skills_dir(args.skills_dir)
    extend_workspace_package_path(repo_root)
    from vgo_installer.simple_skill_installer import uninstall_vibe_skill

    try:
        result = uninstall_vibe_skill(skills_dir=skills_dir)
    except (RuntimeError, OSError, ValueError) as exc:
        raise _installer_cli_error(exc) from exc
    print_json_payload(result)
    if not result.get("ok"):
        message = "Vibe uninstall is incomplete; retry after resolving the reported failures."
        if result.get("unavailable_files") or result.get("unavailable_directories"):
            raise CliUnavailableError(message)
        if result.get("permission_denied_files") or result.get("permission_denied_directories"):
            raise CliPermissionError(message)
        raise CliIoError(message)
    return 0


def update_command(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    skills_dir = _resolve_skills_dir(args.skills_dir)
    extend_workspace_package_path(repo_root)
    from vgo_installer.simple_skill_installer import update_vibe_skill

    try:
        receipt = update_vibe_skill(
            repo_root=repo_root,
            skills_dir=skills_dir,
            installed_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
            **_install_source_kwargs(repo_root),
        )
    except (RuntimeError, OSError, ValueError) as exc:
        raise _installer_cli_error(exc) from exc
    print_json_payload(receipt)
    return 0


def check_command(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    skills_dir = _resolve_skills_dir(args.skills_dir)
    extend_workspace_package_path(repo_root)
    from vgo_installer.simple_skill_installer import check_vibe_skill

    try:
        result = check_vibe_skill(skills_dir=skills_dir)
    except (RuntimeError, OSError, ValueError) as exc:
        raise _installer_cli_error(exc) from exc
    result["current_state"] = {
        "local_runtime": {
            "result": "PASS" if result.get("ok") else "FAIL",
            "source": "installed_vibe_skill_receipt",
        },
        "ci": {
            "url": f"{PROJECT_URL}/actions/workflows/vco-gates.yml",
            "source": "generated_workflow_proof",
        },
        "release": {
            "url": f"{PROJECT_URL}/releases/latest",
            "source": "github_release",
        },
    }
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
