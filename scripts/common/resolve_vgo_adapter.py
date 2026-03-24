#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path


def load_json(path: Path):
    with path.open("r", encoding="utf-8-sig") as fh:
        return json.load(fh)


def embedded_registry():
    return {
        "schema_version": 1,
        "default_adapter_id": "codex",
        "aliases": {"claude": "claude-code"},
        "adapters": [
            {
                "id": "codex",
                "status": "supported-with-constraints",
                "install_mode": "governed",
                "check_mode": "governed",
                "bootstrap_mode": "governed",
                "default_target_root": {"env": "CODEX_HOME", "rel": ".codex", "kind": "host-home"},
                "host_profile": "adapters/codex/host-profile.json",
                "settings_map": "adapters/codex/settings-map.json",
                "closure": "adapters/codex/closure.json",
                "manifest": "dist/host-codex/manifest.json",
            },
            {
                "id": "claude-code",
                "status": "preview",
                "install_mode": "preview-guidance",
                "check_mode": "preview-guidance",
                "bootstrap_mode": "preview-guidance",
                "default_target_root": {"env": "CLAUDE_HOME", "rel": ".claude", "kind": "host-home"},
                "host_profile": "adapters/claude-code/host-profile.json",
                "settings_map": "adapters/claude-code/settings-map.json",
                "closure": "adapters/claude-code/closure.json",
                "manifest": "dist/host-claude-code/manifest.json",
            },
            {
                "id": "cursor",
                "status": "preview",
                "install_mode": "preview-guidance",
                "check_mode": "preview-guidance",
                "bootstrap_mode": "preview-guidance",
                "default_target_root": {"env": "CURSOR_HOME", "rel": ".cursor", "kind": "host-home"},
                "host_profile": "adapters/cursor/host-profile.json",
                "settings_map": "adapters/cursor/settings-map.json",
                "closure": "adapters/cursor/closure.json",
                "manifest": "dist/host-cursor/manifest.json",
            },
        ],
    }


def resolve_registry(repo_root: Path):
    current = repo_root.resolve()
    while True:
        registry_path = current / "adapters" / "index.json"
        if registry_path.exists():
            return current, load_json(registry_path)
        if current.parent == current:
            break
        current = current.parent

    if (repo_root / "config" / "version-governance.json").exists():
        return repo_root.resolve(), embedded_registry()

    raise SystemExit(f"VGO adapter registry not found under repo root or ancestors: {repo_root}")


def resolve_adapter(repo_root: Path, host_id: str):
    registry_root, registry = resolve_registry(repo_root)
    normalized = (host_id or registry.get("default_adapter_id") or "codex").strip().lower()
    normalized = registry.get("aliases", {}).get(normalized, normalized)
    for entry in registry.get("adapters", []):
        if entry.get("id") == normalized:
            result = dict(entry)
            for key in ("host_profile", "settings_map", "closure", "manifest"):
                rel = entry.get(key)
                if rel:
                    result[f"{key}_path"] = str((registry_root / rel).resolve())
                    try:
                        result[f"{key}_json"] = load_json(registry_root / rel)
                    except FileNotFoundError:
                        result[f"{key}_json"] = None
            return result
    raise SystemExit(f"Unsupported VGO host id: {host_id}")


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
