from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys

from .errors import CliError
from .repo import load_json


def report_external_fallback_usage(external_fallback_used: list[str], *, strict_offline: bool) -> None:
    uniq_fallback = ','.join(sorted(set(str(item) for item in external_fallback_used if str(item).strip())))
    if not uniq_fallback:
        return
    if strict_offline:
        raise CliError(f'StrictOffline rejected external fallback usage: {uniq_fallback}')
    print(f'[WARN] External fallback skills were used (non-reproducible install): {uniq_fallback}')


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
