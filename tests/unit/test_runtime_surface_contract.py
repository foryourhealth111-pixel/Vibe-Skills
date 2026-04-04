from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "packages" / "contracts" / "src" / "vgo_contracts" / "runtime_surface_contract.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("runtime_surface_contract_unit", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_runtime_surface_contract_resolves_packaging_payload_from_manifest_sources(tmp_path: Path) -> None:
    module = _load_module()
    repo_root = tmp_path
    config_dir = repo_root / "config"
    scripts_dir = repo_root / "scripts" / "runtime"
    config_dir.mkdir(parents=True)
    scripts_dir.mkdir(parents=True)

    (config_dir / "runtime-script-manifest.json").write_text(
        json.dumps({"files": ["scripts/runtime/router.py"], "directories": ["packages/contracts"]}, indent=2) + "\n",
        encoding="utf-8",
    )
    governance = {
        "packaging": {
            "runtime_payload": {
                "files": ["SKILL.md", "check.sh", "config/runtime-script-manifest.json"],
                "directories": ["config"],
            },
            "manifests": [
                {"id": "runtime_scripts", "path": "config/runtime-script-manifest.json"},
            ],
            "allow_installed_only": ["docs/compat-only.md"],
        }
    }

    contract = module.resolve_packaging_contract(governance, repo_root)

    assert contract["runtime_payload"]["files"] == [
        "SKILL.md",
        "check.sh",
        "config/runtime-script-manifest.json",
        "scripts/runtime/router.py",
    ]
    assert contract["runtime_payload"]["directories"] == ["config", "packages/contracts"]
    assert contract["mirror"] == contract["runtime_payload"]
    assert contract["manifests"] == [{"id": "runtime_scripts", "path": "config/runtime-script-manifest.json"}]
    assert contract["allow_installed_only"] == ["docs/compat-only.md"]
    assert contract["normalized_json_ignore_keys"] == ["updated", "generated_at"]


def test_runtime_surface_contract_owns_activation_and_runtime_ignore_policy() -> None:
    module = _load_module()

    for host_id in ("claude-code", "cursor", "windsurf", "openclaw", "opencode"):
        assert module.uses_skill_only_activation(host_id) is True

    for host_id in ("codex", "unknown", None):
        assert module.uses_skill_only_activation(host_id) is False

    assert module.is_ignored_runtime_artifact(Path("scripts/common/__pycache__/helper.cpython-310.pyc"))
    assert module.is_ignored_runtime_artifact(Path("scripts/.coverage"))
    assert not module.is_ignored_runtime_artifact(Path("scripts/runtime/native_specialist_runner.py"))
