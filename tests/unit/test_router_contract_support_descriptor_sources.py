from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / 'packages' / 'runtime-core' / 'src' / 'vgo_runtime' / 'router_contract_support.py'


def _load_module():
    spec = importlib.util.spec_from_file_location('router_contract_support_unit', MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'unable to load module from {MODULE_PATH}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_skill(path: Path, name: str, description: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n",
        encoding='utf-8',
    )
    return path


def _write_runtime_core_packaging(repo_root: Path) -> None:
    config_root = repo_root / 'config'
    config_root.mkdir(parents=True, exist_ok=True)
    (config_root / 'runtime-core-packaging.json').write_text(
        json.dumps(
            {
                'public_skill_surface': {
                    'canonical_entrypoint_relpath': 'skills/vibe',
                    'root_relpath': 'skills',
                },
                'internal_skill_corpus': {
                    'target_relpath': 'skills/vibe/bundled/skills',
                    'entrypoint_filename': 'SKILL.runtime-mirror.md',
                },
                'compatibility_skill_projections': {
                    'resolver_roots': ['skills'],
                },
            },
            ensure_ascii=False,
            indent=2,
        ) + '\n',
        encoding='utf-8',
    )


def test_resolver_prefers_internal_corpus_descriptor_when_split_semantics_available(tmp_path: Path) -> None:
    module = _load_module()
    repo_root = tmp_path / 'repo'
    target_root = tmp_path / 'target'
    _write_runtime_core_packaging(repo_root)

    repo_internal = _write_skill(
        repo_root / 'skills' / 'vibe' / 'bundled' / 'skills' / 'skill-alpha' / 'SKILL.runtime-mirror.md',
        'skill-alpha',
        'repo internal corpus',
    )
    _write_skill(
        repo_root / 'bundled' / 'skills' / 'skill-alpha' / 'SKILL.md',
        'skill-alpha',
        'legacy bundled fallback',
    )
    _write_skill(
        target_root / 'skills' / 'vibe' / 'bundled' / 'skills' / 'skill-alpha' / 'SKILL.runtime-mirror.md',
        'skill-alpha',
        'installed internal corpus',
    )
    _write_skill(
        target_root / 'skills' / 'skill-alpha' / 'SKILL.md',
        'skill-alpha',
        'compat projection',
    )
    _write_skill(
        target_root / 'skills' / 'custom' / 'skill-alpha' / 'SKILL.md',
        'skill-alpha',
        'custom',
    )

    repo = module.RepoContext(
        repo_root=repo_root,
        config_root=repo_root / 'config',
        bundled_skills_root=repo_root / 'bundled' / 'skills',
    )
    resolved = module.resolve_skill_md_path(repo, 'skill-alpha', str(target_root))
    assert resolved == repo_internal

    descriptor = module.read_skill_descriptor(repo, 'skill-alpha', str(target_root))
    assert descriptor['skill_md_path'] == str(resolved)
    assert descriptor['description'] == 'repo internal corpus'


def test_resolver_uses_installed_internal_corpus_when_repo_internal_descriptor_is_absent(tmp_path: Path) -> None:
    module = _load_module()
    repo_root = tmp_path / 'repo'
    target_root = tmp_path / 'target'
    _write_runtime_core_packaging(repo_root)

    installed_internal = _write_skill(
        target_root / 'skills' / 'vibe' / 'bundled' / 'skills' / 'skill-beta' / 'SKILL.runtime-mirror.md',
        'skill-beta',
        'installed internal corpus',
    )
    _write_skill(
        target_root / 'skills' / 'skill-beta' / 'SKILL.md',
        'skill-beta',
        'compat projection',
    )
    repo = module.RepoContext(
        repo_root=repo_root,
        config_root=repo_root / 'config',
        bundled_skills_root=repo_root / 'bundled' / 'skills',
    )

    resolved = module.resolve_skill_md_path(repo, 'skill-beta', str(target_root))
    assert resolved == installed_internal

    descriptor = module.read_skill_descriptor(repo, 'skill-beta', str(target_root))
    assert descriptor['skill_md_path'] == str(installed_internal)
    assert descriptor['description'] == 'installed internal corpus'


def test_resolver_keeps_legacy_installed_skill_fallback_when_split_semantics_available(tmp_path: Path) -> None:
    module = _load_module()
    repo_root = tmp_path / 'repo'
    target_root = tmp_path / 'target'
    _write_runtime_core_packaging(repo_root)

    installed_public = _write_skill(
        target_root / 'skills' / 'legacy-skill' / 'SKILL.md',
        'legacy-skill',
        'legacy installed projection',
    )
    repo = module.RepoContext(
        repo_root=repo_root,
        config_root=repo_root / 'config',
        bundled_skills_root=repo_root / 'bundled' / 'skills',
    )

    resolved = module.resolve_skill_md_path(repo, 'legacy-skill', str(target_root))
    assert resolved == installed_public
