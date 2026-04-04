#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _load_adapter_registry_module():
    repo_root = Path(__file__).resolve().parents[2]
    package_src = repo_root / "packages" / "installer-core" / "src"
    if str(package_src) not in sys.path:
        sys.path.insert(0, str(package_src))

    try:
        from vgo_installer import adapter_registry as module
    except ImportError:  # pragma: no cover - compatibility fallback for direct file loading
        import importlib.util

        module_path = package_src / "vgo_installer" / "adapter_registry.py"
        spec = importlib.util.spec_from_file_location("vgo_installer_adapter_registry", module_path)
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--host", default="codex")
    parser.add_argument("--property")
    parser.add_argument("--format", choices=("json", "text"), default="text")
    args = parser.parse_args()

    adapter = resolve_adapter(Path(args.repo_root), args.host)
    if args.property:
        value = adapter
        for part in args.property.split("."):
            if isinstance(value, dict):
                value = value.get(part)
            else:
                value = None
            if value is None:
                break
        if args.format == "json":
            json.dump(value, sys.stdout, ensure_ascii=False, indent=2)
            sys.stdout.write("\n")
        elif isinstance(value, (dict, list)):
            json.dump(value, sys.stdout, ensure_ascii=False)
            sys.stdout.write("\n")
        elif value is not None:
            sys.stdout.write(f"{value}\n")
        return

    if args.format == "json":
        json.dump(adapter, sys.stdout, ensure_ascii=False, indent=2)
    else:
        sys.stdout.write(json.dumps(adapter, ensure_ascii=False))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
