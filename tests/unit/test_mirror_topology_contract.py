from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "packages" / "contracts" / "src" / "vgo_contracts" / "mirror_topology_contract.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("mirror_topology_contract_unit", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_resolve_mirror_topology_targets_prefers_topology_targets() -> None:
    module = _load_module()
    governance = {
        "source_of_truth": {
            "canonical_root": "legacy",
            "bundled_root": "legacy/bundled",
        },
        "mirror_topology": {
            "targets": [
                {"id": "canonical", "path": ".", "role": "canonical"},
                {"id": "bundled", "path": "bundled/skills/vibe", "role": "mirror"},
            ]
        },
    }

    targets = module.resolve_mirror_topology_targets(governance)

    assert [target["id"] for target in targets] == ["canonical", "bundled"]
    assert targets[0]["path"] == "."
    assert targets[1]["path"] == "bundled/skills/vibe"


def test_resolve_mirror_topology_targets_falls_back_to_legacy_source_of_truth() -> None:
    module = _load_module()
    governance = {
        "source_of_truth": {
            "canonical_root": ".",
            "bundled_root": "bundled/skills/vibe",
            "nested_bundled_root": "bundled/skills/vibe/bundled/skills/vibe",
        }
    }

    targets = module.resolve_mirror_topology_targets(governance)

    assert [target["id"] for target in targets] == ["canonical", "bundled", "nested_bundled"]
    assert targets[2]["path"] == "bundled/skills/vibe/bundled/skills/vibe"


def test_resolve_canonical_mirror_relpath_uses_topology_contract() -> None:
    module = _load_module()
    governance = {
        "mirror_topology": {
            "canonical_target_id": "primary",
            "targets": [
                {"id": "primary", "path": "repo-root", "role": "canonical"},
                {"id": "bundled", "path": "bundled/skills/vibe", "role": "mirror"},
            ],
        }
    }

    assert module.resolve_canonical_mirror_relpath(governance) == "repo-root"


def test_generated_nested_suffix_preserves_topology_and_legacy_behavior() -> None:
    module = _load_module()
    topology_governance = {
        "mirror_topology": {
            "targets": [
                {"id": "bundled", "path": "bundled/skills/vibe", "role": "mirror"},
                {
                    "id": "nested_bundled",
                    "path": "bundled/skills/vibe/bundled/skills/vibe",
                    "role": "mirror",
                    "materialization_mode": "release_install_only",
                },
            ]
        }
    }
    legacy_governance = {
        "source_of_truth": {
            "bundled_root": "bundled/skills/vibe",
        }
    }

    assert module.resolve_generated_nested_compatibility_suffix(topology_governance) == Path("bundled/skills/vibe")
    assert module.resolve_generated_nested_compatibility_suffix(legacy_governance) == Path("bundled/skills/vibe")
