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
        registry_exists = (current / 'adapters' / 'index.json').exists() or (current / 'config' / 'adapter-registry.json').exists()
        if registry_exists:
            return current
        if current.parent == current:
            break
        current = current.parent

    raise CliError('Unable to resolve workspace repo root for CLI host registry.')


@lru_cache(maxsize=1)
def _contract_modules() -> tuple[Path, ModuleType, ModuleType]:
    repo_root = _resolve_workspace_repo_root()
    extend_workspace_package_path(repo_root)
    from vgo_contracts import adapter_registry_support as registry_module
    from vgo_contracts import target_root_contract as target_root_module

    return repo_root, registry_module, target_root_module


def _load_registry() -> tuple[Path, dict[str, object], ModuleType, ModuleType]:
    repo_root, registry_module, target_root_module = _contract_modules()
    registry = dict(registry_module.load_adapter_registry(repo_root))
    return repo_root, registry, registry_module, target_root_module


def _default_host_id(registry: dict[str, object]) -> str:
    return str(registry.get('default_adapter_id') or 'codex').strip().lower() or 'codex'


def _resolve_host_entry(host_id: str | None) -> tuple[str, dict[str, object]]:
    _repo_root, registry, registry_module, _target_root_module = _load_registry()
    requested_host = str(host_id or os.environ.get('VCO_HOST_ID') or '').strip()
    normalized = str(registry_module.normalize_adapter_host_id(requested_host, registry)).strip().lower()
    if not normalized:
        normalized = _default_host_id(registry)
    try:
        entry = dict(registry_module.resolve_adapter_entry(registry, normalized))
    except ValueError:
        normalized = _default_host_id(registry)
        try:
            entry = dict(registry_module.resolve_adapter_entry(registry, normalized))
        except ValueError as exc:
            raise CliError(f'Unable to resolve host registry entry for: {host_id}') from exc
    return normalized, entry


def _target_root_spec(host_id: str | None) -> tuple[str, dict[str, str]]:
    normalized, entry = _resolve_host_entry(host_id)
    target = dict(entry.get('default_target_root') or {})
    return normalized, {
        'env': str(target.get('env') or '').strip(),
        'rel': str(target.get('rel') or '').strip(),
        'kind': str(target.get('kind') or '').strip(),
        'install_mode': str(entry.get('install_mode') or '').strip(),
    }


def normalize_host_id(host_id: str | None) -> str:
    normalized, _ = _resolve_host_entry(host_id)
    return normalized


def resolve_default_target_root(host_id: str) -> Path:
    normalized, spec = _target_root_spec(host_id)
    _repo_root, _registry, _registry_module, target_root_module = _load_registry()
    target_root_text = target_root_module.resolve_target_root_text(
        default_target_root=spec['rel'],
        default_target_root_env=spec['env'],
        env=dict(os.environ),
        home=str(Path.home()),
        descriptor_id=normalized,
    )
    return Path(str(target_root_text)).expanduser().resolve()


def resolve_target_root(host_id: str, target_root: str | None) -> Path:
    if target_root and str(target_root).strip():
        return Path(str(target_root)).expanduser().resolve()
    return resolve_default_target_root(host_id)


def install_mode_for_host(host_id: str) -> str:
    _, spec = _target_root_spec(host_id)
    return spec['install_mode']
