from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import shutil

from ._bootstrap import ensure_contracts_src_on_path

ensure_contracts_src_on_path()

from vgo_contracts.catalog_descriptor import CatalogDescriptor


PACKAGE_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = PACKAGE_ROOT.parents[1]
CATALOG_ROOT = PACKAGE_ROOT / 'catalog'
SKILL_SOURCE_ROOT = REPO_ROOT / 'bundled' / 'skills'


def _build_descriptor(catalog_root: Path, skill_source_root: Path) -> dict[str, object]:
    descriptor = CatalogDescriptor(
        catalog_root=str(catalog_root),
        skill_source_root=str(skill_source_root),
        profiles_manifest=str(catalog_root / 'profiles' / 'index.json'),
        groups_manifest=str(catalog_root / 'groups' / 'index.json'),
        metadata_manifest=str(catalog_root / 'metadata' / 'index.json'),
        owner='skill-catalog',
        owners=['skill-catalog'],
    )
    return asdict(descriptor)


def describe_local_catalog() -> dict[str, object]:
    return _build_descriptor(CATALOG_ROOT.resolve(), SKILL_SOURCE_ROOT.resolve())


def export_catalog_descriptor(output_root: Path | str) -> dict[str, object]:
    target_root = Path(output_root).resolve()
    exported_catalog_root = target_root / 'catalog'
    exported_skill_root = exported_catalog_root / 'skills'
    if exported_catalog_root.exists():
        shutil.rmtree(exported_catalog_root)
    shutil.copytree(CATALOG_ROOT, exported_catalog_root)
    shutil.copytree(SKILL_SOURCE_ROOT, exported_skill_root)
    return _build_descriptor(exported_catalog_root, exported_skill_root)
