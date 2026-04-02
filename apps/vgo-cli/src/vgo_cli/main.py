from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Sequence


HOST_SPECS: dict[str, dict[str, str]] = {
    'codex': {'env': 'CODEX_HOME', 'rel': '.codex', 'install_mode': 'governed'},
    'claude-code': {'env': 'CLAUDE_HOME', 'rel': '.claude', 'install_mode': 'preview-guidance'},
    'cursor': {'env': 'CURSOR_HOME', 'rel': '.cursor', 'install_mode': 'preview-guidance'},
    'windsurf': {'env': 'WINDSURF_HOME', 'rel': '.codeium/windsurf', 'install_mode': 'runtime-core'},
    'openclaw': {'env': 'OPENCLAW_HOME', 'rel': '.openclaw', 'install_mode': 'runtime-core'},
    'opencode': {'env': 'OPENCODE_HOME', 'rel': '.config/opencode', 'install_mode': 'preview-guidance'},
}
HOST_ALIASES = {
    'claude': 'claude-code',
}
PYTHON_MIN_MAJOR = 3
PYTHON_MIN_MINOR = 10


class CliError(RuntimeError):
    pass


def normalize_host_id(host_id: str | None) -> str:
    text = str(host_id or os.environ.get('VCO_HOST_ID') or 'codex').strip().lower()
    normalized = HOST_ALIASES.get(text, text)
    if normalized not in HOST_SPECS:
        raise CliError(f"Unsupported host id: {host_id}")
    return normalized


def resolve_default_target_root(host_id: str) -> Path:
    spec = HOST_SPECS[host_id]
    env_value = os.environ.get(spec['env'], '').strip()
    if env_value:
        return Path(env_value).expanduser().resolve()
    rel = spec['rel']
    if os.path.isabs(rel):
        return Path(rel).resolve()
    return (Path.home() / rel).resolve()


def resolve_target_root(host_id: str, target_root: str | None) -> Path:
    if target_root and str(target_root).strip():
        return Path(str(target_root)).expanduser().resolve()
    return resolve_default_target_root(host_id)


def assert_target_root_matches_host_intent(target_root: Path, host_id: str) -> None:
    leaf = target_root.name.lower()
    normalized = target_root.as_posix().lower().rstrip('/')
    is_codex_root = leaf == '.codex'
    is_claude_root = leaf == '.claude'
    is_cursor_root = leaf == '.cursor'
    is_windsurf_root = normalized.endswith('/.codeium/windsurf')
    is_openclaw_root = leaf == '.openclaw'
    is_opencode_root = leaf == '.opencode' or normalized.endswith('/.config/opencode')

    def fail(message: str) -> None:
        raise CliError(message)

    if host_id == 'codex' and (is_claude_root or is_windsurf_root or is_openclaw_root):
        fail(f"Target root '{target_root}' looks like a non-Codex host root, but host='codex'.")
    if host_id == 'codex' and is_cursor_root:
        fail(
            f"Target root '{target_root}' looks like a Cursor home, but host='codex'.\n"
            "Pass --host cursor for preview guidance or use a Codex target root."
        )
    if host_id == 'codex' and is_opencode_root:
        fail(
            f"Target root '{target_root}' looks like an OpenCode root, but host='codex'.\n"
            "Pass --host opencode for the OpenCode preview lane or use a Codex target root."
        )
    if host_id == 'claude-code' and (is_codex_root or is_windsurf_root or is_openclaw_root):
        fail(f"Target root '{target_root}' looks like a non-Claude host root, but host='claude-code'.")
    if host_id == 'claude-code' and (is_cursor_root or is_opencode_root):
        fail(f"Target root '{target_root}' does not match host='claude-code'.")
    if host_id == 'cursor' and (is_codex_root or is_claude_root or is_windsurf_root or is_openclaw_root or is_opencode_root):
        fail(f"Target root '{target_root}' does not match host='cursor'.")
    if host_id == 'windsurf' and (is_codex_root or is_claude_root or is_openclaw_root or is_cursor_root or is_opencode_root):
        fail(f"Target root '{target_root}' does not match host='windsurf'.")
    if host_id == 'openclaw' and (is_codex_root or is_claude_root or is_windsurf_root or is_cursor_root or is_opencode_root):
        fail(f"Target root '{target_root}' does not match host='openclaw'.")
    if host_id == 'opencode' and (is_codex_root or is_claude_root or is_cursor_root or is_windsurf_root or is_openclaw_root):
        fail(f"Target root '{target_root}' looks like a non-OpenCode host root, but host='opencode'.")


def choose_powershell() -> str | None:
    candidates = [
        shutil.which('pwsh'),
        shutil.which('pwsh.exe'),
        shutil.which('powershell'),
        shutil.which('powershell.exe'),
        r'C:\Program Files\PowerShell\7\pwsh.exe',
        r'C:\Program Files\PowerShell\7-preview\pwsh.exe',
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))
    return None


def print_process_output(result: subprocess.CompletedProcess[str]) -> None:
    if result.stdout:
        sys.stdout.write(result.stdout)
    if result.stderr:
        sys.stderr.write(result.stderr)


def run_subprocess(command: Sequence[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(list(command), cwd=cwd, capture_output=True, text=True)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8-sig'))


def load_governance(repo_root: Path) -> dict:
    return load_json(repo_root / 'config' / 'version-governance.json')


def get_installed_runtime_config(repo_root: Path) -> dict[str, object]:
    defaults = {
        'target_relpath': 'skills/vibe',
        'receipt_relpath': 'skills/vibe/outputs/runtime-freshness-receipt.json',
        'post_install_gate': 'scripts/verify/vibe-installed-runtime-freshness-gate.ps1',
        'frontmatter_gate': 'scripts/verify/vibe-bom-frontmatter-gate.ps1',
    }
    governance = load_governance(repo_root)
    runtime_cfg = (((governance.get('runtime') or {}).get('installed_runtime')) or {})
    merged = dict(defaults)
    for key in defaults:
        value = runtime_cfg.get(key)
        if isinstance(value, str) and value.strip():
            merged[key] = value
    return merged


def resolve_canonical_repo_root(start_path: Path) -> Path | None:
    current = start_path.resolve()
    while True:
        if (current / '.git').exists() and (current / 'config' / 'version-governance.json').exists():
            return current
        if current.parent == current:
            return None
        current = current.parent


def run_powershell_file(script_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    shell_path = choose_powershell()
    if not shell_path:
        raise CliError(f'PowerShell is required to run: {script_path}')
    leaf = Path(shell_path).name.lower()
    command = [shell_path, '-NoProfile']
    if leaf.startswith('powershell'):
        command += ['-ExecutionPolicy', 'Bypass']
    command += ['-File', str(script_path), *args]
    return run_subprocess(command)


def run_runtime_neutral_freshness_gate(repo_root: Path, target_root: Path) -> subprocess.CompletedProcess[str] | None:
    gate_path = repo_root / 'scripts' / 'verify' / 'runtime_neutral' / 'freshness_gate.py'
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

    neutral_result = run_runtime_neutral_freshness_gate(canonical_root, target_root)
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


def refresh_install_ledger_payload_summary(repo_root: Path, target_root: Path) -> None:
    installer = repo_root / 'scripts' / 'install' / 'install_vgo_adapter.py'
    result = run_subprocess([sys.executable, str(installer), '--target-root', str(target_root), '--refresh-install-ledger'])
    print_process_output(result)
    if result.returncode != 0:
        raise CliError('Post-install ledger refresh failed.')


def resolve_codex_duplicate_skill_root(target_root: Path, host_id: str) -> Path | None:
    if host_id != 'codex' or target_root.name.lower() != '.codex':
        return None
    parent = target_root.parent
    if parent == target_root:
        return None
    return parent / '.agents' / 'skills' / 'vibe'


def test_vibe_skill_dir(root: Path) -> bool:
    skill_md = root / 'SKILL.md'
    if not skill_md.exists():
        return False
    return 'name: vibe' in skill_md.read_text(encoding='utf-8', errors='ignore')


def quarantine_codex_duplicate_skill_surface(target_root: Path, host_id: str) -> None:
    duplicate_root = resolve_codex_duplicate_skill_root(target_root, host_id)
    if duplicate_root is None or not duplicate_root.is_dir():
        return
    target_skill_root = target_root / 'skills' / 'vibe'
    if not target_skill_root.is_dir():
        return
    if duplicate_root.resolve() == target_skill_root.resolve():
        return
    if not test_vibe_skill_dir(duplicate_root):
        raise CliError(
            f"Duplicate Codex-discovered skill surface exists at '{duplicate_root}', but it is not a recognizable vibe skill copy."
        )
    quarantine_root = duplicate_root.parent.parent / 'skills-disabled'
    quarantine_root.mkdir(parents=True, exist_ok=True)
    suffix = datetime.now().strftime('%Y%m%dT%H%M%S')
    quarantine_path = quarantine_root / f'vibe.codex-duplicate-{suffix}'
    shutil.move(str(duplicate_root), str(quarantine_path))
    print(f'[WARN] Quarantined duplicate Codex-discovered vibe skill: {duplicate_root} -> {quarantine_path}')


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


def maybe_install_external_dependencies(repo_root: Path, install_mode: str) -> None:
    if install_mode != 'governed':
        print(f"[WARN] InstallExternal is currently only applied to the governed Codex lane. Skipping external install for mode '{install_mode}'.")
        return
    if shutil.which('npm'):
        for package in ('claude-flow', '@th0rgal/ralph-wiggum'):
            subprocess.run(['npm', 'install', '-g', package], capture_output=True, text=True)
    if not shutil.which('scrapling'):
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'scrapling[ai]'], capture_output=True, text=True)
    if shutil.which('xan') is None:
        print('[WARN] xan CLI not detected. Install manually (brew/pixi/conda/cargo) to enable large CSV acceleration.')
    ivy_probe = subprocess.run([sys.executable, '-c', 'import ivy'], capture_output=True, text=True)
    if ivy_probe.returncode != 0:
        print('[WARN] ivy Python package not detected. Install manually (pip install ivy) to enable framework-interop analyzer hints.')
    if shutil.which('fuck-u-code') is None:
        print('[WARN] fuck-u-code CLI not detected. Install manually if you want external quality-debt analyzer hints (quality-debt-overlay still works without it).')
    manifest_path = repo_root / 'config' / 'plugins-manifest.codex.json'
    if manifest_path.exists():
        try:
            manifest = load_json(manifest_path)
        except Exception:
            return
        print('Codex-only mode: plugin auto-install commands are disabled.')
        for plugin in manifest.get('core') or []:
            name = plugin.get('name', 'unknown')
            mode = plugin.get('install_mode', 'manual-codex')
            hint = plugin.get('install_hint', 'Provision manually in your Codex environment.')
            print(f'[MANUAL] {name} ({mode}) - {hint}')


def parse_json_output(result: subprocess.CompletedProcess[str]) -> dict:
    if result.returncode != 0:
        print_process_output(result)
        raise CliError('core command failed')
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        print_process_output(result)
        raise CliError(f'Invalid JSON output from core command: {exc}') from exc


def print_install_banner(host_id: str, install_mode: str, profile: str, target_root: Path, args: argparse.Namespace) -> None:
    print('=== VCO Adapter Installer ===')
    print(f'Host   : {host_id}')
    print(f'Mode   : {install_mode}')
    print(f'Profile: {profile}')
    print(f'Target : {target_root}')
    print(f'StrictOffline: {bool(args.strict_offline)}')
    print(f'RequireClosedReady: {bool(args.require_closed_ready)}')
    print(f'AllowExternalSkillFallback: {bool(args.allow_external_skill_fallback)}')
    print(f'SkipRuntimeFreshnessGate: {bool(args.skip_runtime_freshness_gate)}')


def install_command(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    host_id = normalize_host_id(args.host)
    target_root = resolve_target_root(host_id, args.target_root)
    assert_target_root_matches_host_intent(target_root, host_id)
    target_root.mkdir(parents=True, exist_ok=True)

    install_mode = HOST_SPECS[host_id]['install_mode']
    print_install_banner(host_id, install_mode, args.profile, target_root, args)

    installer = repo_root / 'scripts' / 'install' / 'install_vgo_adapter.py'
    command = [
        sys.executable,
        str(installer),
        '--repo-root', str(repo_root),
        '--target-root', str(target_root),
        '--host', host_id,
        '--profile', args.profile,
    ]
    if args.require_closed_ready:
        command.append('--require-closed-ready')
    if args.allow_external_skill_fallback:
        command.append('--allow-external-skill-fallback')

    install_result = run_subprocess(command)
    payload = parse_json_output(install_result)
    external_fallback_used = list(payload.get('external_fallback_used') or [])

    if args.install_external:
        maybe_install_external_dependencies(repo_root, str(payload.get('install_mode') or install_mode))

    if args.strict_offline:
        run_offline_gate(repo_root, target_root)
        if external_fallback_used:
            uniq_fallback = ','.join(sorted(set(str(item) for item in external_fallback_used if str(item).strip())))
            raise CliError(f'StrictOffline rejected external fallback usage: {uniq_fallback}')
    elif external_fallback_used:
        uniq_fallback = ','.join(sorted(set(str(item) for item in external_fallback_used if str(item).strip())))
        print(f'[WARN] External fallback skills were used (non-reproducible install): {uniq_fallback}')

    quarantine_codex_duplicate_skill_surface(target_root, host_id)
    run_runtime_freshness_gate(
        repo_root,
        target_root,
        skip_gate=bool(args.skip_runtime_freshness_gate),
        include_frontmatter=args.frontend == 'powershell',
    )
    refresh_install_ledger_payload_summary(repo_root, target_root)

    if args.frontend == 'powershell':
        shell_name = 'pwsh' if shutil.which('pwsh') else 'powershell'
        print('')
        print('Installation complete.')
        print(f'Run: {shell_name} -NoProfile -File .\\check.ps1 -Profile {args.profile} -TargetRoot {target_root}')
    else:
        print(f'Install done. Run: bash check.sh --profile {args.profile} --target-root {target_root}')
    return 0


def uninstall_command(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    host_id = normalize_host_id(args.host)
    target_root = resolve_target_root(host_id, args.target_root)
    assert_target_root_matches_host_intent(target_root, host_id)

    uninstaller = repo_root / 'scripts' / 'uninstall' / 'uninstall_vgo_adapter.py'
    command = [
        sys.executable,
        str(uninstaller),
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
    result = run_subprocess(command)
    print_process_output(result)
    return int(result.returncode)


def passthrough_command(args: argparse.Namespace, *, shell_script: str, powershell_script: str) -> int:
    repo_root = Path(args.repo_root).resolve()
    script_path = repo_root / (powershell_script if args.frontend == 'powershell' else shell_script)
    if args.frontend == 'powershell':
        result = run_powershell_file(script_path, *args.rest)
    else:
        result = run_subprocess(['bash', str(script_path), *args.rest])
    print_process_output(result)
    return int(result.returncode)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command', required=True)

    install_parser = subparsers.add_parser('install')
    install_parser.add_argument('--repo-root', required=True)
    install_parser.add_argument('--frontend', choices=('shell', 'powershell'), default='shell')
    install_parser.add_argument('--profile', choices=('minimal', 'full'), default='full')
    install_parser.add_argument('--host', default='codex')
    install_parser.add_argument('--target-root', default='')
    install_parser.add_argument('--install-external', action='store_true')
    install_parser.add_argument('--strict-offline', action='store_true')
    install_parser.add_argument('--require-closed-ready', action='store_true')
    install_parser.add_argument('--allow-external-skill-fallback', action='store_true')
    install_parser.add_argument('--skip-runtime-freshness-gate', action='store_true')
    install_parser.set_defaults(handler=install_command)

    uninstall_parser = subparsers.add_parser('uninstall')
    uninstall_parser.add_argument('--repo-root', required=True)
    uninstall_parser.add_argument('--frontend', choices=('shell', 'powershell'), default='shell')
    uninstall_parser.add_argument('--profile', choices=('minimal', 'full'), default='full')
    uninstall_parser.add_argument('--host', default='codex')
    uninstall_parser.add_argument('--target-root', default='')
    uninstall_parser.add_argument('--preview', action='store_true')
    uninstall_parser.add_argument('--purge-empty-dirs', action='store_true')
    uninstall_parser.add_argument('--strict-owned-only', action='store_true')
    uninstall_parser.set_defaults(handler=uninstall_command)

    check_parser = subparsers.add_parser('check')
    check_parser.add_argument('--repo-root', required=True)
    check_parser.add_argument('--frontend', choices=('shell', 'powershell'), default='shell')
    check_parser.add_argument('rest', nargs=argparse.REMAINDER)
    check_parser.set_defaults(handler=lambda ns: passthrough_command(ns, shell_script='check.sh', powershell_script='check.ps1'))

    verify_parser = subparsers.add_parser('verify')
    verify_parser.add_argument('--repo-root', required=True)
    verify_parser.add_argument('--frontend', choices=('shell', 'powershell'), default='powershell')
    verify_parser.add_argument('rest', nargs=argparse.REMAINDER)
    verify_parser.set_defaults(handler=lambda ns: passthrough_command(ns, shell_script='check.sh', powershell_script='scripts/verify/vibe-release-install-runtime-coherence-gate.ps1'))

    runtime_parser = subparsers.add_parser('runtime')
    runtime_parser.add_argument('--repo-root', required=True)
    runtime_parser.add_argument('--frontend', choices=('shell', 'powershell'), default='powershell')
    runtime_parser.add_argument('rest', nargs=argparse.REMAINDER)
    runtime_parser.set_defaults(handler=lambda ns: passthrough_command(ns, shell_script='check.sh', powershell_script='scripts/runtime/invoke-vibe-runtime.ps1'))

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except CliError as exc:
        message = str(exc).strip()
        if message:
            for line in message.splitlines():
                print(f'[FAIL] {line}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
