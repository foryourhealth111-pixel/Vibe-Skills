from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

from .errors import CliError
from .mcp_provision import manual_follow_up_servers
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


def print_install_completion_hint(frontend: str, *, host_id: str, profile: str, target_root: Path) -> None:
    if frontend == 'powershell':
        shell_name = 'pwsh' if shutil.which('pwsh') else 'powershell'
        print('')
        print('Installation complete.')
        print(f'Run: {shell_name} -NoProfile -File .\\check.ps1 -Profile {profile} -HostId {host_id} -TargetRoot {target_root}')
        return
    print(f'Install done. Run: bash check.sh --profile {profile} --host {host_id} --target-root {target_root}')


def print_install_completion_report(
    frontend: str,
    *,
    host_id: str,
    profile: str,
    target_root: Path,
    install_receipt: dict[str, object],
    mcp_receipt: dict[str, object],
) -> None:
    follow_up = manual_follow_up_servers(mcp_receipt)
    host_runtime = install_receipt.get('host_runtime') if isinstance(install_receipt, dict) else {}
    vibe_host_ready = 'unknown'
    if isinstance(host_runtime, dict) and 'vibe_host_ready' in host_runtime:
        vibe_host_ready = bool(host_runtime.get('vibe_host_ready'))
    print('')
    print('MCP auto-provision summary')
    print(f'- host: {host_id}')
    print(f'- profile: {profile}')
    print(f'- target_root: {target_root}')
    print(f'- installed_locally: {mcp_receipt.get("install_state") == "installed_locally"}')
    print(f'- vibe_host_ready: {vibe_host_ready}')
    print(f'- mcp_auto_provision_attempted: {bool(mcp_receipt.get("mcp_auto_provision_attempted"))}')
    print('- completed_parts: runtime payload installed; post-install gates reconciled; MCP outcomes summarized once at completion')
    for item in mcp_receipt.get('mcp_results') or []:
        print(
            f'- {item["name"]}: status={item["status"]} '
            f'provision_path={item["provision_path"]} next_step={item["next_step"]}'
        )
    print(f'- online_ready: verify separately with the router connectivity probe for {target_root}')
    print(f'- manual_follow_up: {", ".join(follow_up) if follow_up else "none"}')



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
