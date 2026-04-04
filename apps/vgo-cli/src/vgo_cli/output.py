from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

from .errors import CliError
from .process import print_process_output


def parse_json_output(result: subprocess.CompletedProcess[str]) -> dict:
    if result.returncode != 0:
        print_process_output(result)
        raise CliError('core command failed')
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        print_process_output(result)
        raise CliError(f'Invalid JSON output from core command: {exc}') from exc


def print_install_completion_hint(frontend: str, *, profile: str, target_root: Path) -> None:
    if frontend == 'powershell':
        shell_name = 'pwsh' if shutil.which('pwsh') else 'powershell'
        print('')
        print('Installation complete.')
        print(f'Run: {shell_name} -NoProfile -File .\\check.ps1 -Profile {profile} -TargetRoot {target_root}')
        return
    print(f'Install done. Run: bash check.sh --profile {profile} --target-root {target_root}')



def print_install_banner(host_id: str, install_mode: str, profile: str, target_root: Path, args: object) -> None:
    print('=== VCO Adapter Installer ===')
    print(f'Host   : {host_id}')
    print(f'Mode   : {install_mode}')
    print(f'Profile: {profile}')
    print(f'Target : {target_root}')
    print(f'StrictOffline: {bool(getattr(args, "strict_offline", False))}')
    print(f'RequireClosedReady: {bool(getattr(args, "require_closed_ready", False))}')
    print(f'AllowExternalSkillFallback: {bool(getattr(args, "allow_external_skill_fallback", False))}')
    print(f'SkipRuntimeFreshnessGate: {bool(getattr(args, "skip_runtime_freshness_gate", False))}')



def print_json_payload(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
