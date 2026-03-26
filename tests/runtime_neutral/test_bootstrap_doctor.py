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
        (self.root / "mcp" / "profiles").mkdir(parents=True, exist_ok=True)

        (self.root / "config" / "plugins-manifest.codex.json").write_text(
            json.dumps(
                {
                    "core": [{"name": "github", "install_mode": "manual-codex", "required": True}],
                    "optional": [{"name": "claude-flow", "install_mode": "scripted", "install": "npm install -g claude-flow"}],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (self.root / "mcp" / "servers.template.json").write_text(
            json.dumps(
                {
                    "servers": {
                        "github": {"mode": "plugin"},
                        "scrapling": {"mode": "stdio", "command": "scrapling", "note": "install scrapling"},
                    }
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (self.root / "mcp" / "profiles" / "full.json").write_text(
            json.dumps({"profile": "full", "enabled_servers": ["github", "scrapling"]}, indent=2) + "\n",
            encoding="utf-8",
        )
        (self.root / "config" / "secrets-policy.json").write_text(
            json.dumps(
                {
                    "allowed_secret_refs": [
                        {"name": "OPENAI_API_KEY", "scope": "env", "storage": ["env"]},
                        {"name": "COMPOSIO_SESSION_MCP_URL", "scope": "env", "storage": ["env"]},
                    ]
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (self.root / "config" / "tool-registry.json").write_text(
            json.dumps(
                {
                    "tools": [
                        {
                            "tool_id": "activepieces-mcp",
                            "display_name": "Activepieces MCP",
                            "risk_tier": "high",
                            "secret_refs": ["ACTIVEPIECES_MCP_TOKEN"],
                            "human_confirmation": {"per_action_required": True, "enable_required": True},
                        },
                        {
                            "tool_id": "composio-tool-router",
                            "display_name": "Composio Tool Router",
                            "risk_tier": "high",
                            "secret_refs": ["COMPOSIO_SESSION_MCP_URL"],
                            "human_confirmation": {"per_action_required": True, "enable_required": True},
                        },
                    ]
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (self.root / "config" / "memory-governance.json").write_text(
            json.dumps(
                {
                    "role_boundaries": {"cognee": {"status": "active"}},
                    "defaults_by_task": {
                        "coding": {"long_term": "cognee"},
                        "research": {"long_term": "cognee"},
                    },
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

    def test_settings_present_without_online_secrets_is_manual_actions_pending(self) -> None:
        (self.target_root / "mcp").mkdir(parents=True, exist_ok=True)
        (self.target_root / "mcp" / "servers.active.json").write_text('{"profile":"full"}\n', encoding="utf-8")
        (self.target_root / "settings.json").write_text(
            json.dumps({"vco": {"mcp_profile": "full"}, "env": {"OPENAI_API_KEY": "<pending>"}}) + "\n",
            encoding="utf-8",
        )

        artifact = self.module.evaluate(self.root, self.target_root)
        self.assertEqual("PASS", artifact["gate_result"])
        self.assertEqual("manual_actions_pending", artifact["summary"]["readiness_state"])


if __name__ == "__main__":
    unittest.main()
