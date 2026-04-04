from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .ledger_service import derive_managed_skill_names_from_ledger, sanitize_managed_skill_names


@dataclass(frozen=True, slots=True)
class InstallPlan:
    profile: str
    host_id: str
    target_root: Path
    runtime_root: Path
    install_mode: str
    canonical_vibe_rel: str
    managed_skill_names: tuple[str, ...]
    previous_managed_skill_names: tuple[str, ...]
    packaging_manifest: dict[str, object]


def build_install_plan(
    *,
    profile: str,
    host_id: str,
    target_root: Path | str,
    install_mode: str = 'governed',
    canonical_vibe_rel: str = 'skills/vibe',
    managed_skill_names: list[str] | tuple[str, ...] | set[str] | None = None,
    existing_install_ledger: dict | None = None,
    packaging_manifest: dict[str, object] | None = None,
) -> InstallPlan:
    target_root_path = Path(target_root).resolve()
    normalized_rel = canonical_vibe_rel.replace('\\', '/').strip('/') or 'skills/vibe'
    safe_managed_skill_names = tuple(sanitize_managed_skill_names(managed_skill_names))
    previous_managed_skill_names = tuple(
        sorted(derive_managed_skill_names_from_ledger(target_root_path, existing_install_ledger))
    )
    manifest = {
        'profile': profile,
        'package_id': None,
        'copy_bundled_skills': False,
    }
    if packaging_manifest:
        manifest.update(packaging_manifest)
    manifest['profile'] = str(manifest.get('profile') or profile)
    manifest['copy_bundled_skills'] = bool(manifest.get('copy_bundled_skills'))

    return InstallPlan(
        profile=profile,
        host_id=host_id,
        target_root=target_root_path,
        runtime_root=target_root_path,
        install_mode=install_mode,
        canonical_vibe_rel=normalized_rel,
        managed_skill_names=safe_managed_skill_names,
        previous_managed_skill_names=previous_managed_skill_names,
        packaging_manifest=manifest,
    )
