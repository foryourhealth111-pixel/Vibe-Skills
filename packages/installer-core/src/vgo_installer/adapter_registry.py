from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    from ._bootstrap import ensure_contracts_src_on_path
    from ._io import load_json
except ImportError:  # pragma: no cover - standalone module loading in file-based tests
    import importlib.util
    import sys

    bootstrap_path = Path(__file__).with_name('_bootstrap.py')
    bootstrap_spec = importlib.util.spec_from_file_location('vgo_installer_bootstrap', bootstrap_path)
    if bootstrap_spec is None or bootstrap_spec.loader is None:
        raise
    bootstrap_module = importlib.util.module_from_spec(bootstrap_spec)
    sys.modules.setdefault(bootstrap_spec.name, bootstrap_module)
    bootstrap_spec.loader.exec_module(bootstrap_module)
    ensure_contracts_src_on_path = bootstrap_module.ensure_contracts_src_on_path

    io_path = Path(__file__).with_name('_io.py')
    io_spec = importlib.util.spec_from_file_location('vgo_installer_adapter_registry_io', io_path)
    if io_spec is None or io_spec.loader is None:
        raise
    io_module = importlib.util.module_from_spec(io_spec)
    sys.modules.setdefault(io_spec.name, io_module)
    io_spec.loader.exec_module(io_module)
    load_json = io_module.load_json

ensure_contracts_src_on_path()
from vgo_contracts.adapter_registry_support import (
    load_adapter_registry_file,
    normalize_adapter_host_id,
    resolve_adapter_entry,
    resolve_adapter_registry_path,
)


def resolve_registry_path(repo_root: Path) -> tuple[Path, Path]:
    try:
        registry_path = resolve_adapter_registry_path(repo_root)
    except RuntimeError as exc:
        raise SystemExit(f'VGO adapter registry not found under repo root or ancestors: {repo_root}') from exc
    return registry_path.parents[1], registry_path


def resolve_registry(repo_root: Path) -> tuple[Path, dict[str, Any]]:
    registry_root, registry_path = resolve_registry_path(repo_root)
    return registry_root, load_adapter_registry_file(registry_path)


def resolve_adapter_entries(repo_root: Path) -> dict[str, dict[str, Any]]:
    _registry_root, registry = resolve_registry(repo_root)
    return {
        str(entry['id']): dict(entry)
        for entry in registry.get('adapters', [])
        if isinstance(entry, dict) and isinstance(entry.get('id'), str) and str(entry.get('id')).strip()
    }


def default_bootstrap_summary(host_id: str, entry: dict[str, Any]) -> str:
    summary = str(entry.get('bootstrap_summary') or '').strip()
    if summary:
        return summary
    if host_id == 'codex':
        return 'strongest governed lane'
    if host_id == 'windsurf':
        return 'supported path + runtime adapter'
    if host_id == 'openclaw':
        return 'preview runtime-core adapter'
    if host_id == 'opencode':
        return 'preview guidance adapter'
    return 'supported install/use path'


def resolve_bootstrap_choices(repo_root: Path) -> list[dict[str, Any]]:
    _registry_root, registry = resolve_registry(repo_root)
    aliases = dict(registry.get('aliases', {}) or {})
    choices: list[dict[str, Any]] = []
    for index, entry in enumerate(resolve_adapter_entries(repo_root).values(), start=1):
        host_id = str(entry.get('id') or '').strip()
        if not host_id:
            continue
        host_aliases = [host_id]
        for alias, target in aliases.items():
            if str(target).strip() == host_id and alias not in host_aliases:
                host_aliases.append(str(alias))
        choices.append(
            {
                'index': index,
                'id': host_id,
                'summary': default_bootstrap_summary(host_id, entry),
                'aliases': host_aliases,
            }
        )
    return choices


def resolve_supported_hosts(repo_root: Path) -> list[str]:
    return [str(choice['id']) for choice in resolve_bootstrap_choices(repo_root)]


def _target_root_spec_from_entry(entry: dict[str, Any]) -> dict[str, str]:
    target = dict(entry.get('default_target_root') or {})
    return {
        'env': str(target.get('env') or '').strip(),
        'rel': str(target.get('rel') or '').strip(),
        'kind': str(target.get('kind') or '').strip(),
        'install_mode': str(entry.get('install_mode') or '').strip(),
    }


def resolve_target_root_spec(repo_root: Path, host_id: str | None) -> tuple[str, dict[str, str]]:
    entry = resolve_adapter(repo_root, str(host_id or ''))
    normalized = str(entry.get('id') or '').strip().lower()
    if not normalized:
        raise SystemExit(f'Unsupported VGO host id: {host_id}')
    return normalized, _target_root_spec_from_entry(entry)


def resolve_default_target_root(
    repo_root: Path,
    host_id: str,
    *,
    env: dict[str, str] | None = None,
    home: str | Path | None = None,
) -> Path:
    _normalized, spec = resolve_target_root_spec(repo_root, host_id)
    env_map = env or dict(os.environ)
    home_path = Path(home).expanduser() if home is not None else Path.home()
    env_name = spec['env']
    env_value = str(env_map.get(env_name, '')).strip() if env_name else ''
    if env_value:
        return Path(env_value).expanduser().resolve()
    rel = spec['rel']
    if Path(rel).is_absolute():
        return Path(rel).resolve()
    return (home_path / rel).expanduser().resolve()


def path_matches_relative_signature(target_root: str, signature: str) -> bool:
    normalized_target = str(Path(target_root).expanduser().resolve()).replace('\\', '/').rstrip('/').lower()
    normalized_signature = str(signature or '').replace('\\', '/').strip('/').lower()
    if not normalized_signature:
        return False
    leaf = normalized_target.rsplit('/', 1)[-1]
    if '/' not in normalized_signature:
        return leaf == normalized_signature or normalized_target.endswith('/' + normalized_signature)
    return normalized_target.endswith('/' + normalized_signature)


def _target_root_signatures(host_id: str, entry: dict[str, Any]) -> tuple[str, ...]:
    spec = _target_root_spec_from_entry(entry)
    signatures = []
    if spec['rel']:
        signatures.append(spec['rel'])
    if host_id == 'opencode':
        signatures.append('.opencode')
    return tuple(signatures)


def resolve_matching_target_root_hosts(repo_root: Path, target_root: str) -> list[str]:
    matches: list[str] = []
    for host_id, entry in resolve_adapter_entries(repo_root).items():
        if any(path_matches_relative_signature(target_root, signature) for signature in _target_root_signatures(host_id, entry)):
            matches.append(host_id)
    return matches


def resolve_target_root_owner(repo_root: Path, target_root: str) -> str:
    matches = resolve_matching_target_root_hosts(repo_root, target_root)
    return matches[0] if matches else ''


def resolve_adapter(repo_root: Path, host_id: str) -> dict[str, Any]:
    registry_root, registry = resolve_registry(repo_root)
    normalized = normalize_adapter_host_id(host_id, registry)
    try:
        entry = resolve_adapter_entry(registry, host_id)
    except ValueError as exc:
        raise SystemExit(f'Unsupported VGO host id: {host_id}') from exc

    if str(entry.get('id') or '').strip().lower() != normalized:
        raise SystemExit(f'Unsupported VGO host id: {host_id}')

    result = dict(entry)
    for key in ('host_profile', 'settings_map', 'closure', 'manifest'):
        rel = entry.get(key)
        if rel:
            result[f'{key}_path'] = str((registry_root / rel).resolve())
            try:
                result[f'{key}_json'] = load_json(registry_root / rel)
            except FileNotFoundError:
                result[f'{key}_json'] = None
    return result
