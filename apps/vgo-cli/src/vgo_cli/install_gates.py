from __future__ import annotations

from pathlib import Path
import subprocess
import sys

from .errors import CliError
from .process import (
    choose_powershell,
    print_process_output,
    run_powershell_file,
    run_subprocess,
)
from .repo import get_installed_runtime_config, resolve_canonical_repo_root


def run_runtime_neutral_freshness_gate(repo_root: Path, target_root: Path, gate_relpath: str) -> subprocess.CompletedProcess[str] | None:
    gate_path = repo_root / gate_relpath
    if not gate_path.exists():
        return None
    return run_subprocess([sys.executable, str(gate_path), '--target-root', str(target_root), '--write-receipt'])


def run_runtime_freshness_gate(repo_root: Path, target_root: Path, *, skip_gate: bool, include_frontmatter: bool) -> None:
    if skip_gate:
        print('[WARN] Skipping runtime freshness gate by request.')
        return

    canonical_root = resolve_canonical_repo_root(repo_root)
    if canonical_root is None:
        print('[WARN] Runtime freshness gate requires the canonical repo root; skipping because no outer .git root was found.')
        return

    runtime_cfg = get_installed_runtime_config(canonical_root)
    gate_path = canonical_root / str(runtime_cfg['post_install_gate'])
    if not gate_path.exists():
        raise CliError(f'Runtime freshness gate script missing: {gate_path}')

    neutral_result = run_runtime_neutral_freshness_gate(canonical_root, target_root, str(runtime_cfg['neutral_freshness_gate']))
    if neutral_result is not None:
        print_process_output(neutral_result)
        if neutral_result.returncode != 0:
            raise CliError('Runtime freshness gate failed after install.')
    else:
        shell_path = choose_powershell()
        if not shell_path:
            print('[WARN] runtime freshness gate skipped: neither Python runtime-neutral gate nor a PowerShell fallback is available.')
            return
        result = run_powershell_file(gate_path, '-TargetRoot', str(target_root), '-WriteReceipt')
        print_process_output(result)
        if result.returncode != 0:
            raise CliError('Runtime freshness gate failed after install.')

    receipt_path = target_root / str(runtime_cfg['receipt_relpath'])
    if not receipt_path.exists():
        raise CliError(f'Runtime freshness receipt missing after install: {receipt_path}')

    if include_frontmatter:
        frontmatter_gate = canonical_root / str(runtime_cfg['frontmatter_gate'])
        if not frontmatter_gate.exists():
            raise CliError(f'frontmatter gate script missing: {frontmatter_gate}')
        result = run_powershell_file(frontmatter_gate, '-TargetRoot', str(target_root))
        print_process_output(result)
        if result.returncode != 0:
            raise CliError('Frontmatter BOM gate failed after install.')


def run_offline_gate(repo_root: Path, target_root: Path) -> None:
    gate_path = repo_root / 'scripts' / 'verify' / 'vibe-offline-skills-gate.ps1'
    if not gate_path.exists():
        raise CliError(f'StrictOffline requested, but offline gate script is missing: {gate_path}')
    if not choose_powershell():
        raise CliError('StrictOffline requires an available PowerShell host to run the offline gate')
    result = run_powershell_file(
        gate_path,
        '-SkillsRoot', str(target_root / 'skills'),
        '-PackManifestPath', str(repo_root / 'config' / 'pack-manifest.json'),
        '-SkillsLockPath', str(repo_root / 'config' / 'skills-lock.json'),
    )
    print_process_output(result)
    if result.returncode != 0:
        raise CliError('StrictOffline validation failed (vibe-offline-skills-gate).')
