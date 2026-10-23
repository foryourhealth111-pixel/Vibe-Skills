from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess

from .host_skill_roots import resolve_codex_home


def _cache_component(value: object) -> str:
    if (
        not isinstance(value, str) or not value.strip() or value != value.strip()
        or value in {".", ".."} or any(char in value for char in "/\\:\0")
    ):
        raise ValueError("Host plugin inventory contains an invalid cache identity")
    return value


def resolve_codex_plugin_roots(cache_root: Path) -> tuple[Path, ...] | None:
    """Use the host's installed plugin inventory to select exact enabled cache versions."""
    codex_home = cache_root.resolve().parent.parent
    configured_home = resolve_codex_home()
    # A discovered Skill root cannot nominate a program to execute during scanning.
    if codex_home != configured_home:
        return None
    executable = codex_home / "plugins/.plugin-appserver" / ("codex.exe" if os.name == "nt" else "codex")
    if executable.is_file():
        command = str(executable)
    elif (codex_home / "config.toml").is_file():
        command = shutil.which("codex")
    else:
        return None
    if command is None:
        return None
    env = os.environ.copy()
    env["CODEX_HOME"] = str(codex_home)
    try:
        result = subprocess.run(
            [command, "plugin", "list", "--json"], capture_output=True,
            text=True, encoding="utf-8", env=env, timeout=5,
        )
    except (OSError, UnicodeError, subprocess.TimeoutExpired) as exc:
        raise ValueError("Host plugin inventory is unavailable") from exc
    if result.returncode != 0:
        raise ValueError("Host plugin inventory command failed")
    try:
        payload = json.loads(result.stdout)
    except ValueError as exc:
        raise ValueError("Host plugin inventory is not valid JSON") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("installed"), list):
        raise ValueError("Host plugin inventory must contain an installed plugin array")
    roots: list[Path] = []
    identities: set[str] = set()
    for entry in payload["installed"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("installed"), bool) or not isinstance(entry.get("enabled"), bool):
            raise ValueError("Host plugin inventory requires boolean installed and enabled fields")
        if not entry["installed"] or not entry["enabled"]:
            continue
        name = _cache_component(entry.get("name"))
        marketplace = _cache_component(entry.get("marketplaceName"))
        identity = f"{name}@{marketplace}"
        if entry.get("pluginId") != identity or identity in identities:
            raise ValueError("Host plugin inventory has conflicting plugin identities")
        identities.add(identity)
        if entry.get("version") is None:
            continue
        version = _cache_component(entry["version"])
        root = (cache_root / marketplace / name / version).resolve()
        if not root.is_relative_to(cache_root.resolve()):
            raise ValueError("Host plugin inventory cache root escapes the declared cache")
        roots.append(root)
    return tuple(roots)


def resolve_codex_plugin_skill_roots(plugin_root: Path) -> tuple[Path, ...]:
    """Resolve portable conventions or compatibility-manifest Skill exports."""
    root = plugin_root.resolve()
    exports: object = ["./skills/"]
    for relative in ("plugin.json", ".codex-plugin/plugin.json", ".claude-plugin/plugin.json"):
        manifest = root / relative
        if not manifest.is_file():
            continue
        payload = json.loads(manifest.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, dict):
            raise ValueError("Plugin manifest must be an object")
        if relative != "plugin.json":
            exports = payload.get("skills", exports)
        break
    if isinstance(exports, str):
        exports = [exports]
    if not isinstance(exports, list) or any(
        not isinstance(value, str) or not value.startswith("./")
        or ".." in value.replace("\\", "/").split("/")
        for value in exports
    ):
        raise ValueError("Plugin Skill exports must start with ./ and contain no parent components")
    roots = tuple(dict.fromkeys((root / value).resolve() for value in exports))
    if any(not path.is_relative_to(root) for path in roots):
        raise ValueError("Plugin Skill export escapes its installed plugin")
    return roots
