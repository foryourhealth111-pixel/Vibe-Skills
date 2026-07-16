from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "verify" / "runtime_neutral" / "bootstrap_doctor.py"


def load_module():
    spec = importlib.util.spec_from_file_location("runtime_neutral_bootstrap_doctor", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class BootstrapDoctorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "config").mkdir(parents=True, exist_ok=True)
        (self.root / "config" / "plugins-manifest.codex.json").write_text(
            json.dumps(
                {
                    "core": [{"name": "github", "install_mode": "manual-codex", "required": True}],
                    "optional": [],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (self.root / "config" / "secrets-policy.json").write_text(
            json.dumps({"allowed_secret_refs": []}, indent=2) + "\n",
            encoding="utf-8",
        )
        (self.root / "config" / "tool-registry.json").write_text(
            json.dumps({"tools": []}, indent=2) + "\n",
            encoding="utf-8",
        )
        (self.root / "config" / "memory-governance.json").write_text(
            json.dumps(
                {
                    "role_boundaries": {"cognee": {"status": "active"}},
                    "defaults_by_task": {"coding": {"long_term": "cognee"}},
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        self.target_root = self.root / "target"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_missing_settings_is_core_install_incomplete(self) -> None:
        artifact = self.module.evaluate(self.root, self.target_root)
        self.assertEqual("FAIL", artifact["gate_result"])
        self.assertEqual("core_install_incomplete", artifact["summary"]["readiness_state"])
        self.assertNotIn("mcp", artifact)

    def test_settings_present_reports_installed_without_mcp_surface(self) -> None:
        self.target_root.mkdir(parents=True, exist_ok=True)
        (self.target_root / "settings.json").write_text(
            json.dumps({"vco": {"skill_root": "~/.agents/skills"}, "env": {}}) + "\n",
            encoding="utf-8",
        )

        artifact = self.module.evaluate(self.root, self.target_root)

        self.assertEqual("installed_locally", artifact["install_state"])
        self.assertNotIn("mcp", artifact)
        self.assertTrue(artifact["summary"]["manual_actions"])
        self.assertFalse(
            any("mcp" in action.lower() or "servers.active.json" in action.lower() for action in artifact["summary"]["manual_actions"])
        )

    def test_host_runtime_prefers_declared_shared_runtime_root_when_present(self) -> None:
        shared_runtime_root = self.root / "shared-runtime"
        self.target_root.mkdir(parents=True, exist_ok=True)
        (shared_runtime_root / "skills" / "vibe").mkdir(parents=True, exist_ok=True)
        (shared_runtime_root / "skills" / "vibe" / "SKILL.md").write_text("# vibe\n", encoding="utf-8")
        (self.target_root / "commands").mkdir(parents=True, exist_ok=True)
        (self.target_root / "settings.json").write_text(
            json.dumps({"vco": {"skill_root": "~/.agents/skills"}, "env": {}}) + "\n",
            encoding="utf-8",
        )
        sidecar_root = self.target_root / ".vibeskills"
        sidecar_root.mkdir(parents=True, exist_ok=True)
        (sidecar_root / "host-settings.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "host_id": "openclaw",
                    "managed": True,
                    "runtime_root": str(shared_runtime_root.resolve()),
                    "commands_root": str((self.target_root / "commands").resolve()),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (sidecar_root / "host-closure.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "host_id": "openclaw",
                    "runtime_root": str(shared_runtime_root.resolve()),
                    "runtime_skill_entry": str((shared_runtime_root / "skills" / "vibe" / "SKILL.md").resolve()),
                    "commands_root": str((self.target_root / "commands").resolve()),
                    "commands_materialized": True,
                    "host_closure_state": "closed_ready",
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        artifact = self.module.evaluate(self.root, self.target_root)

        self.assertEqual(str(shared_runtime_root.resolve()), artifact["host_runtime"]["runtime_root_path"])
        self.assertNotIn("specialist_wrapper_ready", artifact["host_runtime"])
        self.assertEqual(
            str((shared_runtime_root / "skills" / "vibe" / "SKILL.md").resolve()),
            artifact["host_runtime"]["runtime_skill_entry_path"],
        )
        self.assertTrue(artifact["host_runtime"]["runtime_skill_entry_exists"])
        self.assertTrue(artifact["host_runtime"]["host_closure_runtime_matches"])
        self.assertTrue(artifact["host_runtime"]["host_closure_commands_match"])


if __name__ == "__main__":
    unittest.main()
