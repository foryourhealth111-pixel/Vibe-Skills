from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def resolve_adapter_registry_path(start_path: str | Path) -> Path:
    current = Path(start_path).resolve()
    if current.is_file():
        current = current.parent

    while True:
        adapter_index = current / 'adapters' / 'index.json'
        if adapter_index.exists():
            return adapter_index

        config_registry = current / 'config' / 'adapter-registry.json'
        if config_registry.exists():
            return config_registry

        if current.parent == current:
            break
        current = current.parent

    raise RuntimeError(f'VGO adapter registry not found from start path: {start_path}')


def load_adapter_registry_file(registry_path: str | Path) -> dict[str, Any]:
    return json.loads(Path(registry_path).read_text(encoding='utf-8-sig'))


def load_adapter_registry(start_path: str | Path) -> dict[str, Any]:
    return load_adapter_registry_file(resolve_adapter_registry_path(start_path))


def normalize_adapter_host_id(host_id: str | None, registry: dict[str, Any]) -> str:
    normalized = str(host_id or registry.get('default_adapter_id') or 'codex').strip().lower()
    aliases = dict(registry.get('aliases') or {})
    return str(aliases.get(normalized, normalized))


def resolve_adapter_entry(registry: dict[str, Any], host_id: str | None) -> dict[str, Any]:
    normalized = normalize_adapter_host_id(host_id, registry)
    for entry in registry.get('adapters', []):
        if isinstance(entry, dict) and entry.get('id') == normalized:
            return dict(entry)
    raise ValueError(f'unsupported adapter id: {host_id}')
