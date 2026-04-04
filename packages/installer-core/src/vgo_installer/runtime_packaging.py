from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from ._io import load_json
except ImportError:  # pragma: no cover - standalone module loading in file-based tests
    import importlib.util
    import sys

    io_path = Path(__file__).with_name('_io.py')
    spec = importlib.util.spec_from_file_location('vgo_installer_runtime_packaging_io', io_path)
    if spec is None or spec.loader is None:
        raise
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(spec.name, module)
    spec.loader.exec_module(module)
    load_json = module.load_json


RUNTIME_CORE_BASE_MANIFEST = Path('config/runtime-core-packaging.json')


def _deep_merge(base: Any, overlay: Any) -> Any:
    if isinstance(base, dict) and isinstance(overlay, dict):
        merged = {key: _deep_merge(value, overlay[key]) if key in overlay else value for key, value in base.items()}
        for key, value in overlay.items():
            if key not in merged:
                merged[key] = value
        return merged
    return overlay


def load_runtime_core_packaging_base(repo_root: Path) -> dict[str, Any]:
    return load_json((repo_root / RUNTIME_CORE_BASE_MANIFEST).resolve())


def resolve_runtime_core_projection_path(repo_root: Path, profile: str) -> Path:
    base = load_runtime_core_packaging_base(repo_root)
    manifest_map = base.get('profile_manifests') or {}
    manifest_rel = str(manifest_map.get(profile) or '').strip()
    if manifest_rel:
        return (repo_root / manifest_rel).resolve()
    return (repo_root / RUNTIME_CORE_BASE_MANIFEST).resolve()


def resolve_runtime_core_packaging(repo_root: Path, profile: str) -> dict[str, Any]:
    base = load_runtime_core_packaging_base(repo_root)
    profiles = base.get('profiles') or {}
    profile_overlay = profiles.get(profile)
    if isinstance(profile_overlay, dict):
        merged = dict(base)
        merged.pop('profiles', None)
        merged.pop('default_profile', None)
        merged = _deep_merge(merged, profile_overlay)
        merged.setdefault('profile', profile)
        merged.setdefault('bundled_skills_source', 'bundled/skills')
        merged.setdefault('skills_allowlist', [])
        merged.setdefault(
            'copy_bundled_skills',
            any(entry.get('target') == 'skills' for entry in merged.get('copy_directories') or []),
        )
        return merged

    projection_path = resolve_runtime_core_projection_path(repo_root, profile)
    packaging = load_json(projection_path)
    packaging.setdefault('profile', profile)
    packaging.setdefault('bundled_skills_source', 'bundled/skills')
    packaging.setdefault('skills_allowlist', [])
    packaging.setdefault(
        'copy_bundled_skills',
        any(entry.get('target') == 'skills' for entry in packaging.get('copy_directories') or []),
    )
    return packaging
