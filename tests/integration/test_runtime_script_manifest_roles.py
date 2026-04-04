from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ROUTER_MODULE_DIR = REPO_ROOT / "scripts" / "router" / "modules"
RUNTIME_SCRIPT_DIR = REPO_ROOT / "scripts" / "runtime"


def _load_manifest() -> dict:
    return json.loads((REPO_ROOT / "config" / "runtime-script-manifest.json").read_text(encoding="utf-8"))


def test_runtime_script_manifest_role_groups_cover_flat_projection() -> None:
    manifest = _load_manifest()
    role_groups = manifest["role_groups"]

    file_groups = role_groups["files"]
    grouped_files = []
    for values in file_groups.values():
        grouped_files.extend(values)
    assert set(grouped_files) == set(manifest["files"])
    assert len(grouped_files) == len(set(grouped_files))

    directory_groups = role_groups["directories"]
    grouped_directories = []
    for values in directory_groups.values():
        grouped_directories.extend(values)
    assert set(grouped_directories) == set(manifest["directories"])
    assert len(grouped_directories) == len(set(grouped_directories))


def test_runtime_script_manifest_separates_semantic_owners_from_compatibility_shims() -> None:
    manifest = _load_manifest()
    directory_groups = manifest["role_groups"]["directories"]

    semantic_owners = set(directory_groups["semantic_owners"])
    runtime_support = set(directory_groups["runtime_support"])
    compatibility_shims = set(directory_groups["compatibility_shims"])

    assert semantic_owners.isdisjoint(runtime_support)
    assert semantic_owners.isdisjoint(compatibility_shims)
    assert runtime_support.isdisjoint(compatibility_shims)

    assert "apps/vgo-cli" in semantic_owners
    assert "packages/contracts" in semantic_owners
    assert "packages/installer-core" in semantic_owners
    assert "packages/runtime-core" in semantic_owners
    assert "packages/verification-core" in semantic_owners

    compatibility_router_files = set(manifest["role_groups"]["files"]["compatibility_runtime_neutral_router_files"])
    assert compatibility_router_files == {
        "scripts/router/runtime_neutral/router_contract.py",
        "scripts/router/runtime_neutral/custom_admission.py",
    }

    router_module_support_files = set(manifest["role_groups"]["files"]["router_module_support_files"])
    expected_router_module_support_files = {
        path.as_posix().replace(str(REPO_ROOT.as_posix()) + "/", "")
        for path in sorted(ROUTER_MODULE_DIR.glob("*.ps1"))
    }
    assert router_module_support_files == expected_router_module_support_files

    compatibility_verification_support_files = set(
        manifest["role_groups"]["files"]["compatibility_runtime_neutral_verification_support_files"]
    )
    assert compatibility_verification_support_files == {
        "scripts/verify/runtime_neutral/_bootstrap.py",
    }

    compatibility_verification_files = set(manifest["role_groups"]["files"]["compatibility_runtime_neutral_verification_files"])
    assert compatibility_verification_files == {
        "scripts/verify/runtime_neutral/bootstrap_doctor.py",
        "scripts/verify/runtime_neutral/coherence_gate.py",
        "scripts/verify/runtime_neutral/freshness_gate.py",
        "scripts/verify/runtime_neutral/opencode_preview_smoke.py",
        "scripts/verify/runtime_neutral/release_notes_quality.py",
        "scripts/verify/runtime_neutral/release_truth_gate.py",
        "scripts/verify/runtime_neutral/router_ai_connectivity_probe.py",
        "scripts/verify/runtime_neutral/router_bridge_gate.py",
        "scripts/verify/runtime_neutral/runtime_delivery_acceptance.py",
        "scripts/verify/runtime_neutral/workflow_acceptance_runner.py",
    }

    compatibility_shim_files = set(manifest["role_groups"]["files"]["compatibility_shim_files"])
    assert compatibility_shim_files == {
        "scripts/install/Install-VgoAdapter.ps1",
        "scripts/uninstall/Uninstall-VgoAdapter.ps1",
    }

    governed_runtime_support_files = set(manifest["role_groups"]["files"]["governed_runtime_support_files"])
    expected_governed_runtime_support_files = {
        path.as_posix().replace(str(REPO_ROOT.as_posix()) + "/", "")
        for path in sorted(RUNTIME_SCRIPT_DIR.glob("*"))
        if path.is_file()
    }
    assert governed_runtime_support_files == expected_governed_runtime_support_files

    assert all(path.startswith(("packages/", "apps/")) for path in semantic_owners)
    assert all(
        path.startswith("scripts/")
        for path in runtime_support
        | compatibility_shims
        | compatibility_router_files
        | router_module_support_files
        | compatibility_verification_support_files
        | compatibility_verification_files
        | compatibility_shim_files
        | governed_runtime_support_files
    )


def test_runtime_script_manifest_marks_router_python_entrypoint_as_compatibility_surface() -> None:
    manifest = _load_manifest()
    file_groups = manifest["role_groups"]["files"]

    assert "scripts/router/invoke-pack-route.py" in file_groups["compatibility_entrypoints"]
    assert "scripts/router/resolve-pack-route.ps1" in file_groups["router_entrypoints"]
    assert all(path.startswith("scripts/verify/") for path in file_groups["verification_gates"])


def test_runtime_script_manifest_avoids_broad_common_directory_projection() -> None:
    manifest = _load_manifest()
    file_groups = manifest["role_groups"]["files"]
    directory_groups = manifest["role_groups"]["directories"]

    assert "scripts/common" not in manifest["directories"]
    assert "scripts/common" not in directory_groups["runtime_support"]

    runtime_support_files = set(file_groups["runtime_support_files"])
    assert runtime_support_files == {
        "scripts/common/vibe-governance-helpers.ps1",
        "scripts/common/adapter_registry_query.py",
        "scripts/common/AntiProxyGoalDrift.ps1",
    }
    assert runtime_support_files.issubset(set(manifest["files"]))


def test_runtime_script_manifest_avoids_broad_runtime_neutral_directory_projection() -> None:
    manifest = _load_manifest()
    file_groups = manifest["role_groups"]["files"]

    assert "scripts/router/runtime_neutral" not in manifest["directories"]
    assert "scripts/verify/runtime_neutral" not in manifest["directories"]
    assert manifest["role_groups"]["directories"]["compatibility_shims"] == []
    assert "scripts/verify/runtime_neutral/_bootstrap.py" in file_groups["compatibility_runtime_neutral_verification_support_files"]


def test_runtime_script_manifest_avoids_broad_router_module_directory_projection() -> None:
    manifest = _load_manifest()
    file_groups = manifest["role_groups"]["files"]

    assert "scripts/router/modules" not in manifest["directories"]
    assert "scripts/router/modules" not in manifest["role_groups"]["directories"]["runtime_support"]
    assert set(file_groups["router_module_support_files"]) == {
        path.as_posix().replace(str(REPO_ROOT.as_posix()) + "/", "")
        for path in sorted(ROUTER_MODULE_DIR.glob("*.ps1"))
    }


def test_runtime_script_manifest_avoids_broad_governed_runtime_directory_projection() -> None:
    manifest = _load_manifest()
    file_groups = manifest["role_groups"]["files"]

    assert "scripts/runtime" not in manifest["directories"]
    assert "scripts/runtime" not in manifest["role_groups"]["directories"]["runtime_support"]
    assert set(file_groups["governed_runtime_support_files"]) == {
        path.as_posix().replace(str(REPO_ROOT.as_posix()) + "/", "")
        for path in sorted(RUNTIME_SCRIPT_DIR.glob("*"))
        if path.is_file()
    }
