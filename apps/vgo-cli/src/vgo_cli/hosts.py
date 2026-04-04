from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from types import ModuleType

from .errors import CliError
from .workspace import extend_workspace_package_path


@lru_cache(maxsize=1)
def _resolve_workspace_repo_root() -> Path:
    current = Path(__file__).resolve()
    if current.is_file():
        current = current.parent

    while True:
        installer_core_src = current / 'packages' / 'installer-core' / 'src'
        registry_exists = (current / 'adapters' / 'index.json').exists() or (current / 'config' / 'adapter-registry.json').exists()
        if installer_core_src.is_dir() and registry_exists:
            return current
        if current.parent == current:
            break
        current = current.parent

    raise CliError('Unable to resolve workspace repo root for CLI host registry.')


@lru_cache(maxsize=1)
def _installer_registry_module() -> tuple[Path, ModuleType]:
    repo_root = _resolve_workspace_repo_root()
    extend_workspace_package_path(repo_root)
    from vgo_installer import adapter_registry as module

    return repo_root, module


def _raise_host_error(host_id: str | None, exc: SystemExit) -> None:
    message = str(exc).strip()
    if message.startswith('Unsupported VGO host id:'):
        raise CliError(f'Unsupported host id: {host_id}') from None
    raise CliError(message) from None


def _resolve_host_entry(host_id: str | None) -> tuple[str, dict[str, object]]:
    repo_root, module = _installer_registry_module()
    requested_host = str(host_id or os.environ.get('VCO_HOST_ID') or '').strip()
    try:
        entry = dict(module.resolve_adapter(repo_root, requested_host))
    except SystemExit as exc:
        _raise_host_error(host_id, exc)

    normalized = str(entry.get('id') or '').strip().lower()
    if not normalized:
        raise CliError(f'Unsupported host id: {host_id}')
    return normalized, entry


def _target_root_spec(host_id: str | None) -> tuple[str, dict[str, str]]:
    repo_root, module = _installer_registry_module()
    requested_host = str(host_id or os.environ.get('VCO_HOST_ID') or '').strip()
    try:
        normalized, spec = module.resolve_target_root_spec(repo_root, requested_host)
    except SystemExit as exc:
        _raise_host_error(host_id, exc)
    return str(normalized), dict(spec)


def normalize_host_id(host_id: str | None) -> str:
    normalized, _ = _resolve_host_entry(host_id)
    return normalized


def resolve_default_target_root(host_id: str) -> Path:
    repo_root, module = _installer_registry_module()
    requested_host = str(host_id or os.environ.get('VCO_HOST_ID') or '').strip()
    try:
        return Path(module.resolve_default_target_root(repo_root, requested_host, env=dict(os.environ), home=Path.home()))
    except SystemExit as exc:
        _raise_host_error(host_id, exc)


def resolve_target_root(host_id: str, target_root: str | None) -> Path:
    if target_root and str(target_root).strip():
        return Path(str(target_root)).expanduser().resolve()
    return resolve_default_target_root(host_id)


def install_mode_for_host(host_id: str) -> str:
    _, spec = _target_root_spec(host_id)
    return spec['install_mode']


def assert_target_root_matches_host_intent(target_root: Path, host_id: str) -> None:
    normalized_host = normalize_host_id(host_id)
    repo_root, module = _installer_registry_module()
    try:
        matching_hosts = list(module.resolve_matching_target_root_hosts(repo_root, str(target_root)))
    except SystemExit as exc:
        _raise_host_error(host_id, exc)
    if not matching_hosts or normalized_host in matching_hosts:
        return

    foreign_host = matching_hosts[0]
    if normalized_host == 'codex' and foreign_host == 'cursor':
        raise CliError(
            f"Target root '{target_root}' looks like a Cursor home, but host='codex'.\n"
            "Pass --host cursor for preview guidance or use a Codex target root."
        )
    if normalized_host == 'codex' and foreign_host == 'opencode':
        raise CliError(
            f"Target root '{target_root}' looks like an OpenCode root, but host='codex'.\n"
            "Pass --host opencode for the OpenCode preview lane or use a Codex target root."
        )
    raise CliError(
        f"Target root '{target_root}' looks like the default target root for host='{foreign_host}', but host='{normalized_host}'."
    )
