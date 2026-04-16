from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_PATH = REPO_ROOT / "scripts" / "common" / "runtime_contracts.py"
INSTALL_PATH = REPO_ROOT / "scripts" / "install" / "install_vgo_adapter.py"
UNINSTALL_PATH = REPO_ROOT / "scripts" / "uninstall" / "uninstall_vgo_adapter.py"


def load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class RuntimeContractsTests(unittest.TestCase):
    def test_install_and_uninstall_share_canonical_vibe_activation_contract(self) -> None:
        contracts = load_module("runtime_contracts", CONTRACTS_PATH)
        install = load_module("install_vgo_adapter", INSTALL_PATH)
        uninstall = load_module("uninstall_vgo_adapter", UNINSTALL_PATH)

        for host_id in {"codex", "claude-code", "opencode"}:
            contract = contracts.resolve_canonical_vibe_contract(REPO_ROOT, host_id)
            self.assertEqual(host_id, contract["host_id"])
            self.assertEqual("blocked", contract["fallback_policy"])
            self.assertFalse(contract["allow_skill_doc_fallback"])
            self.assertTrue(contract["proof_required"])

        expected_true = {"claude-code", "cursor", "windsurf", "openclaw", "opencode"}
        for host_id in expected_true:
            self.assertTrue(contracts.uses_skill_only_activation(host_id))
            self.assertTrue(install.uses_skill_only_activation(host_id))
            self.assertTrue(uninstall.uses_skill_only_activation(host_id))

        for host_id in {"codex", "unknown"}:
            self.assertFalse(contracts.uses_skill_only_activation(host_id))
            self.assertFalse(install.uses_skill_only_activation(host_id))
            self.assertFalse(uninstall.uses_skill_only_activation(host_id))

    def test_runtime_ignored_artifact_policy_covers_current_repo_noise(self) -> None:
        contracts = load_module("runtime_contracts", CONTRACTS_PATH)

        self.assertTrue(contracts.is_ignored_runtime_artifact(Path("scripts/common/__pycache__/helper.cpython-310.pyc")))
        self.assertTrue(contracts.is_ignored_runtime_artifact(Path("scripts/.pytest_cache/v/cache")))
        self.assertTrue(contracts.is_ignored_runtime_artifact(Path("scripts/.coverage")))
        self.assertTrue(contracts.is_ignored_runtime_artifact(Path("scripts/.venv/bin/python")))

        self.assertFalse(contracts.is_ignored_runtime_artifact(Path("scripts/runtime/native_specialist_runner.py")))


if __name__ == "__main__":
    unittest.main()
