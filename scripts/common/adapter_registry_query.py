#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _load_adapter_registry_module():
    repo_root = Path(__file__).resolve().parents[2]
    package_src = repo_root / 'packages' / 'installer-core' / 'src'
    if str(package_src) not in sys.path:
        sys.path.insert(0, str(package_src))

    try:
        from vgo_installer import adapter_registry as module
    except ImportError:  # pragma: no cover - compatibility fallback for direct file loading
        import importlib.util

        module_path = package_src / 'vgo_installer' / 'adapter_registry.py'
        spec = importlib.util.spec_from_file_location('vgo_installer_adapter_registry', module_path)
        if spec is None or spec.loader is None:
            raise
        module = importlib.util.module_from_spec(spec)
        sys.modules.setdefault(spec.name, module)
        spec.loader.exec_module(module)
    return module


_ADAPTER_REGISTRY = _load_adapter_registry_module()
resolve_registry_path = _ADAPTER_REGISTRY.resolve_registry_path
resolve_registry = _ADAPTER_REGISTRY.resolve_registry
resolve_adapter = _ADAPTER_REGISTRY.resolve_adapter
resolve_bootstrap_choices = _ADAPTER_REGISTRY.resolve_bootstrap_choices
resolve_supported_hosts = _ADAPTER_REGISTRY.resolve_supported_hosts
resolve_target_root_owner = _ADAPTER_REGISTRY.resolve_target_root_owner


def query_property(value, property_path: str):
    current = value
    for part in property_path.split('.'):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            current = None
        if current is None:
            break
    return current


def write_value(value, fmt: str) -> None:
    if fmt == 'json':
        json.dump(value, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write('\n')
        return
    if isinstance(value, (dict, list)):
        json.dump(value, sys.stdout, ensure_ascii=False)
        sys.stdout.write('\n')
        return
    if value is not None:
        sys.stdout.write(f'{value}\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo-root', required=True)
    parser.add_argument('--host', default='codex')
    parser.add_argument('--property')
    parser.add_argument('--target-root-owner')
    parser.add_argument('--supported-hosts', action='store_true')
    parser.add_argument('--bootstrap-choice-lines', action='store_true')
    parser.add_argument('--format', choices=('json', 'text'), default='text')
    args = parser.parse_args()

    repo_root = Path(args.repo_root)

    if args.target_root_owner is not None:
        owner = resolve_target_root_owner(repo_root, args.target_root_owner)
        if owner:
            sys.stdout.write(f'{owner}\n')
        return

    if args.supported_hosts:
        hosts = resolve_supported_hosts(repo_root)
        if args.format == 'json':
            write_value(hosts, args.format)
        else:
            sys.stdout.write('|'.join(hosts) + '\n')
        return

    if args.bootstrap_choice_lines:
        for choice in resolve_bootstrap_choices(repo_root):
            sys.stdout.write(
                '{index}\t{id}\t{summary}\t{aliases}\n'.format(
                    index=choice['index'],
                    id=choice['id'],
                    summary=choice['summary'],
                    aliases=','.join(choice['aliases']),
                )
            )
        return

    adapter = resolve_adapter(repo_root, args.host)
    if args.property:
        write_value(query_property(adapter, args.property), args.format)
        return

    if args.format == 'json':
        json.dump(adapter, sys.stdout, ensure_ascii=False, indent=2)
    else:
        sys.stdout.write(json.dumps(adapter, ensure_ascii=False))
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()
