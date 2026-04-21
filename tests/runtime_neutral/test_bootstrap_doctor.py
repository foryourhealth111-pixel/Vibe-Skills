from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path
import importlib


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
                        {"name": "VCO_INTENT_ADVICE_API_KEY", "scope": "env", "storage": ["env"]},
                        {"name": "VCO_VECTOR_DIFF_API_KEY", "scope": "env", "storage": ["env"]},
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
            json.dumps({"vco": {"mcp_profile": "full"}, "env": {"VCO_INTENT_ADVICE_API_KEY": "<pending>"}}) + "\n",
            encoding="utf-8",
        )

        artifact = self.module.evaluate(self.root, self.target_root)
        self.assertEqual("PASS", artifact["gate_result"])
        self.assertEqual("manual_actions_pending", artifact["summary"]["readiness_state"])

    def test_mcp_receipt_keeps_install_and_mcp_readiness_separate(self) -> None:
        (self.target_root / ".vibeskills").mkdir(parents=True, exist_ok=True)
        (self.target_root / ".vibeskills" / "mcp-auto-provision.json").write_text(
            json.dumps(
                {
                    "install_state": "installed_locally",
                    "mcp_auto_provision_attempted": True,
                    "mcp_results": [
                        {"name": "github", "status": "host_native_unavailable", "next_step": "Register in host UI"},
                        {"name": "scrapling", "status": "local_tool_present", "next_step": "Register in host UI"},
                    ],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (self.target_root / "mcp").mkdir(parents=True, exist_ok=True)
        (self.target_root / "mcp" / "servers.active.json").write_text('{"profile":"full"}\n', encoding="utf-8")
        (self.target_root / "settings.json").write_text(
            json.dumps({"vco": {"mcp_profile": "full"}, "env": {"VCO_INTENT_ADVICE_API_KEY": "<pending>"}}) + "\n",
            encoding="utf-8",
        )

        artifact = self.module.evaluate(self.root, self.target_root)
        self.assertEqual("installed_locally", artifact["install_state"])
        self.assertTrue(artifact["mcp"]["auto_provision_attempted"])
        self.assertEqual("host_native_unavailable", artifact["mcp"]["servers"][0]["status"])
        self.assertEqual("local_tool_present", artifact["mcp"]["servers"][1]["status"])
        self.assertEqual("manual_actions_pending", artifact["summary"]["readiness_state"])

    def test_bootstrap_doctor_upgrades_stdio_server_to_ready_when_active_surface_and_command_agree(self) -> None:
        (self.target_root / ".vibeskills").mkdir(parents=True, exist_ok=True)
        (self.target_root / ".vibeskills" / "mcp-auto-provision.json").write_text(
            json.dumps(
                {
                    "install_state": "installed_locally",
                    "mcp_auto_provision_attempted": True,
                    "mcp_results": [
                        {"name": "scrapling", "status": "local_tool_present", "next_step": "Register in host UI"},
                    ],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (self.target_root / "mcp").mkdir(parents=True, exist_ok=True)
        (self.target_root / "mcp" / "servers.active.json").write_text(
            json.dumps(
                {
                    "profile": "full",
                    "enabled_servers": ["scrapling"],
                    "servers": {
                        "scrapling": {"mode": "stdio", "command": "scrapling", "args": ["mcp"]},
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (self.target_root / "settings.json").write_text(
            json.dumps({"vco": {"mcp_profile": "full"}, "env": {"VCO_INTENT_ADVICE_API_KEY": "<pending>"}}) + "\n",
            encoding="utf-8",
        )

        runtime_module = importlib.import_module("vgo_verify.bootstrap_doctor_runtime")
        original_command_present = runtime_module.command_present
        self.addCleanup(setattr, runtime_module, "command_present", original_command_present)
        runtime_module.command_present = lambda name: name == "scrapling"

        artifact = self.module.evaluate(self.root, self.target_root)

        self.assertEqual("ready", artifact["mcp"]["servers"][0]["status"])

    def test_bootstrap_doctor_reports_vibe_host_ready_separately_from_install_state(self) -> None:
        (self.target_root / ".vibeskills").mkdir(parents=True, exist_ok=True)
        (self.target_root / ".vibeskills" / "mcp-auto-provision.json").write_text(
            json.dumps(
                {
                    "install_state": "installed_locally",
                    "mcp_auto_provision_attempted": True,
                    "mcp_results": [],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (self.target_root / "skills" / "vibe").mkdir(parents=True, exist_ok=True)
        (self.target_root / "skills" / "vibe" / "SKILL.md").write_text("---\nname: vibe\n---\n", encoding="utf-8")
        (self.target_root / "commands").mkdir(parents=True, exist_ok=True)
        (self.target_root / "mcp").mkdir(parents=True, exist_ok=True)
        (self.target_root / "mcp" / "servers.active.json").write_text('{"profile":"full"}\n', encoding="utf-8")
        (self.target_root / "settings.json").write_text(
            json.dumps({"vco": {"mcp_profile": "full"}, "env": {"VCO_INTENT_ADVICE_API_KEY": "<pending>"}}) + "\n",
            encoding="utf-8",
        )

        artifact = self.module.evaluate(self.root, self.target_root)

        self.assertEqual("installed_locally", artifact["install_state"])
        self.assertIn("host_runtime", artifact)
        self.assertFalse(artifact["host_runtime"]["vibe_host_ready"])

    def test_bootstrap_doctor_reports_vibe_host_ready_when_runtime_surfaces_and_closure_agree(self) -> None:
        (self.target_root / ".vibeskills").mkdir(parents=True, exist_ok=True)
        (self.target_root / ".vibeskills" / "mcp-auto-provision.json").write_text(
            json.dumps(
                {
                    "install_state": "installed_locally",
                    "mcp_auto_provision_attempted": True,
                    "mcp_results": [],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        runtime_skill_entry = self.target_root / "skills" / "vibe" / "SKILL.md"
        runtime_skill_entry.parent.mkdir(parents=True, exist_ok=True)
        runtime_skill_entry.write_text("---\nname: vibe\n---\n", encoding="utf-8")
        commands_root = self.target_root / "commands"
        commands_root.mkdir(parents=True, exist_ok=True)
        (self.target_root / ".vibeskills" / "host-closure.json").write_text(
            json.dumps(
                {
                    "host_id": "codex",
                    "runtime_skill_entry": str(runtime_skill_entry.resolve()),
                    "commands_root": str(commands_root.resolve()),
                    "commands_materialized": True,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (self.target_root / "mcp").mkdir(parents=True, exist_ok=True)
        (self.target_root / "mcp" / "servers.active.json").write_text('{"profile":"full"}\n', encoding="utf-8")
        (self.target_root / "settings.json").write_text(
            json.dumps({"vco": {"mcp_profile": "full"}, "env": {"VCO_INTENT_ADVICE_API_KEY": "<pending>"}}) + "\n",
            encoding="utf-8",
        )

        artifact = self.module.evaluate(self.root, self.target_root)

        self.assertTrue(artifact["host_runtime"]["vibe_host_ready"])
        self.assertTrue(artifact["host_runtime"]["host_closure_exists"])
        self.assertTrue(artifact["host_runtime"]["settings_surface_exists"])

    def test_bootstrap_doctor_reports_healthy_global_instruction_bootstrap(self) -> None:
        sidecar_root = self.target_root / ".vibeskills"
        sidecar_root.mkdir(parents=True, exist_ok=True)
        (sidecar_root / "mcp-auto-provision.json").write_text(
            json.dumps(
                {
                    "install_state": "installed_locally",
                    "mcp_auto_provision_attempted": True,
                    "mcp_results": [],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        runtime_skill_entry = self.target_root / "skills" / "vibe" / "SKILL.md"
        runtime_skill_entry.parent.mkdir(parents=True, exist_ok=True)
        runtime_skill_entry.write_text("---\nname: vibe\n---\n", encoding="utf-8")
        commands_root = self.target_root / "commands"
        commands_root.mkdir(parents=True, exist_ok=True)
        (sidecar_root / "host-closure.json").write_text(
            json.dumps(
                {
                    "host_id": "codex",
                    "runtime_skill_entry": str(runtime_skill_entry.resolve()),
                    "commands_root": str(commands_root.resolve()),
                    "commands_materialized": True,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (self.target_root / "mcp").mkdir(parents=True, exist_ok=True)
        (self.target_root / "mcp" / "servers.active.json").write_text('{"profile":"full"}\n', encoding="utf-8")
        (self.target_root / "settings.json").write_text(
            json.dumps({"vco": {"mcp_profile": "full"}, "env": {"VCO_INTENT_ADVICE_API_KEY": "<pending>"}}) + "\n",
            encoding="utf-8",
        )
        bootstrap_path = self.target_root / "AGENTS.md"
        bootstrap_path.write_text(
            "<!-- VIBESKILLS:BEGIN managed-block host=codex block=global-vibe-bootstrap version=1 hash=deadbeef -->\n"
            "Use canonical vibe.\n"
            "<!-- VIBESKILLS:END managed-block -->\n",
            encoding="utf-8",
        )
        (sidecar_root / "global-instruction-bootstrap.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "status": "ok",
                    "host": "codex",
                    "target_file": str(bootstrap_path.resolve()),
                    "target_relpath": "AGENTS.md",
                    "documented_path": "~/.codex/AGENTS.md",
                    "block_id": "global-vibe-bootstrap",
                    "action": "inserted",
                    "template_version": 1,
                    "content_hash": "deadbeef",
                }
            )
            + "\n",
            encoding="utf-8",
        )

        artifact = self.module.evaluate(self.root, self.target_root)

        self.assertIn("global_instruction_bootstrap", artifact["host_runtime"])
        self.assertTrue(artifact["host_runtime"]["global_instruction_bootstrap"]["healthy"])
        self.assertEqual("AGENTS.md", artifact["host_runtime"]["global_instruction_bootstrap"]["target_relpath"])

    def test_bootstrap_doctor_fails_when_global_instruction_bootstrap_is_duplicated(self) -> None:
        sidecar_root = self.target_root / ".vibeskills"
        sidecar_root.mkdir(parents=True, exist_ok=True)
        (sidecar_root / "mcp-auto-provision.json").write_text(
            json.dumps(
                {
                    "install_state": "installed_locally",
                    "mcp_auto_provision_attempted": True,
                    "mcp_results": [],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        runtime_skill_entry = self.target_root / "skills" / "vibe" / "SKILL.md"
        runtime_skill_entry.parent.mkdir(parents=True, exist_ok=True)
        runtime_skill_entry.write_text("---\nname: vibe\n---\n", encoding="utf-8")
        commands_root = self.target_root / "commands"
        commands_root.mkdir(parents=True, exist_ok=True)
        (sidecar_root / "host-closure.json").write_text(
            json.dumps(
                {
                    "host_id": "codex",
                    "runtime_skill_entry": str(runtime_skill_entry.resolve()),
                    "commands_root": str(commands_root.resolve()),
                    "commands_materialized": True,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (self.target_root / "mcp").mkdir(parents=True, exist_ok=True)
        (self.target_root / "mcp" / "servers.active.json").write_text('{"profile":"full"}\n', encoding="utf-8")
        (self.target_root / "settings.json").write_text(
            json.dumps({"vco": {"mcp_profile": "full"}, "env": {"VCO_INTENT_ADVICE_API_KEY": "<pending>"}}) + "\n",
            encoding="utf-8",
        )
        block = (
            "<!-- VIBESKILLS:BEGIN managed-block host=codex block=global-vibe-bootstrap version=1 hash=deadbeef -->\n"
            "Use canonical vibe.\n"
            "<!-- VIBESKILLS:END managed-block -->\n"
        )
        bootstrap_path = self.target_root / "AGENTS.md"
        bootstrap_path.write_text(block + "\n" + block, encoding="utf-8")
        (sidecar_root / "global-instruction-bootstrap.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "status": "ok",
                    "host": "codex",
                    "target_file": str(bootstrap_path.resolve()),
                    "target_relpath": "AGENTS.md",
                    "documented_path": "~/.codex/AGENTS.md",
                    "block_id": "global-vibe-bootstrap",
                    "action": "inserted",
                    "template_version": 1,
                    "content_hash": "deadbeef",
                }
            )
            + "\n",
            encoding="utf-8",
        )

        artifact = self.module.evaluate(self.root, self.target_root)

        self.assertEqual("FAIL", artifact["gate_result"])
        self.assertIn("global instruction bootstrap", " ".join(artifact["summary"]["blocking_issues"]))

    def test_bootstrap_doctor_reports_missing_receipt_without_host_closure(self) -> None:
        sidecar_root = self.target_root / ".vibeskills"
        sidecar_root.mkdir(parents=True, exist_ok=True)
        (sidecar_root / "mcp-auto-provision.json").write_text(
            json.dumps(
                {
                    "install_state": "installed_locally",
                    "mcp_auto_provision_attempted": True,
                    "mcp_results": [],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        runtime_skill_entry = self.target_root / "skills" / "vibe" / "SKILL.md"
        runtime_skill_entry.parent.mkdir(parents=True, exist_ok=True)
        runtime_skill_entry.write_text("---\nname: vibe\n---\n", encoding="utf-8")
        commands_root = self.target_root / "commands"
        commands_root.mkdir(parents=True, exist_ok=True)
        (self.target_root / "mcp").mkdir(parents=True, exist_ok=True)
        (self.target_root / "mcp" / "servers.active.json").write_text('{"profile":"full"}\n', encoding="utf-8")
        (self.target_root / "settings.json").write_text(
            json.dumps({"vco": {"mcp_profile": "full"}, "env": {"VCO_INTENT_ADVICE_API_KEY": "<pending>"}}) + "\n",
            encoding="utf-8",
        )
        bootstrap_path = self.target_root / "AGENTS.md"
        bootstrap_path.write_text(
            "<!-- VIBESKILLS:BEGIN managed-block host=codex block=global-vibe-bootstrap version=1 hash=deadbeef -->\n"
            "Use canonical vibe.\n"
            "<!-- VIBESKILLS:END managed-block -->\n",
            encoding="utf-8",
        )

        artifact = self.module.evaluate(self.root, self.target_root)

        self.assertEqual("missing_receipt", artifact["host_runtime"]["global_instruction_bootstrap"]["status"])
        self.assertTrue(artifact["host_runtime"]["global_instruction_bootstrap"]["applicable"])

    def test_bootstrap_doctor_treats_malformed_bootstrap_receipt_as_unhealthy(self) -> None:
        sidecar_root = self.target_root / ".vibeskills"
        sidecar_root.mkdir(parents=True, exist_ok=True)
        (sidecar_root / "mcp-auto-provision.json").write_text(
            json.dumps(
                {
                    "install_state": "installed_locally",
                    "mcp_auto_provision_attempted": True,
                    "mcp_results": [],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        runtime_skill_entry = self.target_root / "skills" / "vibe" / "SKILL.md"
        runtime_skill_entry.parent.mkdir(parents=True, exist_ok=True)
        runtime_skill_entry.write_text("---\nname: vibe\n---\n", encoding="utf-8")
        commands_root = self.target_root / "commands"
        commands_root.mkdir(parents=True, exist_ok=True)
        (sidecar_root / "host-closure.json").write_text(
            json.dumps(
                {
                    "host_id": "codex",
                    "runtime_skill_entry": str(runtime_skill_entry.resolve()),
                    "commands_root": str(commands_root.resolve()),
                    "commands_materialized": True,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (self.target_root / "mcp").mkdir(parents=True, exist_ok=True)
        (self.target_root / "mcp" / "servers.active.json").write_text('{"profile":"full"}\n', encoding="utf-8")
        (self.target_root / "settings.json").write_text(
            json.dumps({"vco": {"mcp_profile": "full"}, "env": {"VCO_INTENT_ADVICE_API_KEY": "<pending>"}}) + "\n",
            encoding="utf-8",
        )
        bootstrap_path = self.target_root / "AGENTS.md"
        bootstrap_path.write_text(
            "<!-- VIBESKILLS:BEGIN managed-block host=codex block=global-vibe-bootstrap version=1 hash=deadbeef -->\n"
            "Use canonical vibe.\n"
            "<!-- VIBESKILLS:END managed-block -->\n",
            encoding="utf-8",
        )
        (sidecar_root / "global-instruction-bootstrap.codex.agents-md.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "status": "ok",
                    "host": "codex",
                    "target_file": str(bootstrap_path.resolve()),
                    "target_relpath": "AGENTS.md",
                    "documented_path": "~/.codex/AGENTS.md",
                    "block_id": "global-vibe-bootstrap",
                    "action": "inserted",
                    "template_version": "oops",
                    "content_hash": "deadbeef",
                }
            )
            + "\n",
            encoding="utf-8",
        )

        artifact = self.module.evaluate(self.root, self.target_root)

        self.assertEqual("FAIL", artifact["gate_result"])
        self.assertFalse(artifact["host_runtime"]["global_instruction_bootstrap"]["healthy"])
        self.assertEqual("unhealthy", artifact["host_runtime"]["global_instruction_bootstrap"]["status"])

    def test_bootstrap_doctor_does_not_treat_other_host_block_as_duplicate(self) -> None:
        sidecar_root = self.target_root / ".vibeskills"
        sidecar_root.mkdir(parents=True, exist_ok=True)
        (sidecar_root / "mcp-auto-provision.json").write_text(
            json.dumps(
                {
                    "install_state": "installed_locally",
                    "mcp_auto_provision_attempted": True,
                    "mcp_results": [],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        runtime_skill_entry = self.target_root / "skills" / "vibe" / "SKILL.md"
        runtime_skill_entry.parent.mkdir(parents=True, exist_ok=True)
        runtime_skill_entry.write_text("---\nname: vibe\n---\n", encoding="utf-8")
        commands_root = self.target_root / "commands"
        commands_root.mkdir(parents=True, exist_ok=True)
        (sidecar_root / "host-closure.json").write_text(
            json.dumps(
                {
                    "host_id": "codex",
                    "runtime_skill_entry": str(runtime_skill_entry.resolve()),
                    "commands_root": str(commands_root.resolve()),
                    "commands_materialized": True,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (self.target_root / "mcp").mkdir(parents=True, exist_ok=True)
        (self.target_root / "mcp" / "servers.active.json").write_text('{"profile":"full"}\n', encoding="utf-8")
        (self.target_root / "settings.json").write_text(
            json.dumps({"vco": {"mcp_profile": "full"}, "env": {"VCO_INTENT_ADVICE_API_KEY": "<pending>"}}) + "\n",
            encoding="utf-8",
        )
        bootstrap_path = self.target_root / "AGENTS.md"
        bootstrap_path.write_text(
            "<!-- VIBESKILLS:BEGIN managed-block host=codex block=global-vibe-bootstrap version=1 hash=deadbeef -->\n"
            "Use canonical vibe.\n"
            "<!-- VIBESKILLS:END managed-block -->\n\n"
            "<!-- VIBESKILLS:BEGIN managed-block host=opencode block=global-vibe-bootstrap version=1 hash=beadfeed -->\n"
            "Use canonical vibe.\n"
            "<!-- VIBESKILLS:END managed-block -->\n",
            encoding="utf-8",
        )
        (sidecar_root / "global-instruction-bootstrap.codex.agents-md.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "status": "ok",
                    "host": "codex",
                    "target_file": str(bootstrap_path.resolve()),
                    "target_relpath": "AGENTS.md",
                    "documented_path": "~/.codex/AGENTS.md",
                    "block_id": "global-vibe-bootstrap",
                    "action": "inserted",
                    "template_version": 1,
                    "content_hash": "deadbeef",
                }
            )
            + "\n",
            encoding="utf-8",
        )

        artifact = self.module.evaluate(self.root, self.target_root)

        self.assertEqual("PASS", artifact["gate_result"])
        self.assertTrue(artifact["host_runtime"]["global_instruction_bootstrap"]["healthy"])
        self.assertEqual(1, artifact["host_runtime"]["global_instruction_bootstrap"]["duplicate_count"])

    def test_malformed_non_dict_mcp_receipt_degrades_to_unknown_state(self) -> None:
        (self.target_root / ".vibeskills").mkdir(parents=True, exist_ok=True)
        (self.target_root / ".vibeskills" / "mcp-auto-provision.json").write_text("[1]\n", encoding="utf-8")
        (self.target_root / "mcp").mkdir(parents=True, exist_ok=True)
        (self.target_root / "mcp" / "servers.active.json").write_text('{"profile":"full"}\n', encoding="utf-8")
        (self.target_root / "settings.json").write_text(
            json.dumps({"vco": {"mcp_profile": "full"}, "env": {"VCO_INTENT_ADVICE_API_KEY": "<pending>"}}) + "\n",
            encoding="utf-8",
        )

        artifact = self.module.evaluate(self.root, self.target_root)

        self.assertEqual("unknown", artifact["install_state"])
        self.assertFalse(artifact["mcp"]["auto_provision_attempted"])
        self.assertEqual("manual_actions_pending", artifact["summary"]["readiness_state"])

    def test_claude_code_doctor_detects_windows_bare_npx_and_bad_claude_flow_schema(self) -> None:
        support_module = importlib.import_module("vgo_verify.bootstrap_doctor_support")
        original_is_windows = support_module.IS_WINDOWS
        self.addCleanup(setattr, support_module, "IS_WINDOWS", original_is_windows)
        support_module.IS_WINDOWS = True

        sidecar_root = self.target_root / ".vibeskills"
        sidecar_root.mkdir(parents=True, exist_ok=True)
        (sidecar_root / "mcp-auto-provision.json").write_text(
            json.dumps(
                {
                    "install_state": "installed_locally",
                    "mcp_auto_provision_attempted": True,
                    "mcp_results": [],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        runtime_skill_entry = self.target_root / "skills" / "vibe" / "SKILL.md"
        runtime_skill_entry.parent.mkdir(parents=True, exist_ok=True)
        runtime_skill_entry.write_text("---\nname: vibe\n---\n", encoding="utf-8")
        commands_root = self.target_root / "commands"
        commands_root.mkdir(parents=True, exist_ok=True)
        (sidecar_root / "host-closure.json").write_text(
            json.dumps(
                {
                    "host_id": "claude-code",
                    "runtime_skill_entry": str(runtime_skill_entry.resolve()),
                    "commands_root": str(commands_root.resolve()),
                    "commands_materialized": True,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (self.target_root / "mcp").mkdir(parents=True, exist_ok=True)
        (self.target_root / "mcp" / "servers.active.json").write_text('{"profile":"full"}\n', encoding="utf-8")
        (self.target_root / "settings.json").write_text(
            json.dumps({"vco": {"mcp_profile": "full"}, "env": {"VCO_INTENT_ADVICE_API_KEY": "<pending>"}}) + "\n",
            encoding="utf-8",
        )

        package_root = self.root / "npm" / "node_modules" / "claude-flow"
        hooks_tools_path = package_root / "v3" / "@claude-flow" / "cli" / "dist" / "src" / "mcp-tools" / "hooks-tools.js"
        hooks_tools_path.parent.mkdir(parents=True, exist_ok=True)
        (package_root / "package.json").write_text(json.dumps({"version": "3.1.0-alpha.44"}) + "\n", encoding="utf-8")
        hooks_tools_path.write_text(
            "export const hooksIntelligenceLearn = { properties: { trajectoryIds: { type: 'array', description: 'Specific trajectories to learn from' } } };",
            encoding="utf-8",
        )
        (self.root / ".claude.json").write_text(
            json.dumps(
                {
                    "mcpServers": {
                        "chrome": {"type": "stdio", "command": "npx", "args": ["chrome-devtools-mcp@latest"]},
                        "ruflo": {
                            "type": "stdio",
                            "command": str((self.root / "npm" / "claude-flow.cmd").resolve()),
                            "args": ["mcp", "start"],
                        },
                        "claude-flow": {"type": "stdio", "command": "claude-flow", "args": ["mcp", "start"]},
                    }
                }
            )
            + "\n",
            encoding="utf-8",
        )

        with mock.patch.object(support_module.Path, "home", return_value=self.root):
            artifact = self.module.evaluate(self.root, self.target_root)

        global_mcp = artifact["host_runtime"]["claude_code_global_mcp"]
        self.assertEqual("issues_detected", global_mcp["status"])
        self.assertEqual(["global:chrome"], global_mcp["windows_bare_npx_servers"])
        self.assertEqual(["global:ruflo", "global:claude-flow"], global_mcp["duplicate_claude_flow_aliases"])
        self.assertTrue(global_mcp["claude_flow_schema_issue"]["detected"])
        self.assertTrue(any("bare npx entries" in item for item in artifact["summary"]["manual_actions"]))
        self.assertTrue(any("invalid MCP schema" in item for item in artifact["summary"]["manual_actions"]))

    def test_claude_code_doctor_scans_project_level_mcp_servers(self) -> None:
        support_module = importlib.import_module("vgo_verify.bootstrap_doctor_support")
        original_is_windows = support_module.IS_WINDOWS
        self.addCleanup(setattr, support_module, "IS_WINDOWS", original_is_windows)
        support_module.IS_WINDOWS = True

        sidecar_root = self.target_root / ".vibeskills"
        sidecar_root.mkdir(parents=True, exist_ok=True)
        (sidecar_root / "mcp-auto-provision.json").write_text(
            json.dumps(
                {
                    "install_state": "installed_locally",
                    "mcp_auto_provision_attempted": True,
                    "mcp_results": [],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        runtime_skill_entry = self.target_root / "skills" / "vibe" / "SKILL.md"
        runtime_skill_entry.parent.mkdir(parents=True, exist_ok=True)
        runtime_skill_entry.write_text("---\nname: vibe\n---\n", encoding="utf-8")
        commands_root = self.target_root / "commands"
        commands_root.mkdir(parents=True, exist_ok=True)
        (sidecar_root / "host-closure.json").write_text(
            json.dumps(
                {
                    "host_id": "claude-code",
                    "runtime_skill_entry": str(runtime_skill_entry.resolve()),
                    "commands_root": str(commands_root.resolve()),
                    "commands_materialized": True,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (self.target_root / "mcp").mkdir(parents=True, exist_ok=True)
        (self.target_root / "mcp" / "servers.active.json").write_text('{"profile":"full"}\n', encoding="utf-8")
        (self.target_root / "settings.json").write_text(
            json.dumps({"vco": {"mcp_profile": "full"}, "env": {"VCO_INTENT_ADVICE_API_KEY": "<pending>"}}) + "\n",
            encoding="utf-8",
        )
        (self.root / ".claude.json").write_text(
            json.dumps(
                {
                    "projects": {
                        "D:/table/demo": {
                            "mcpServers": {
                                "playwright": {"type": "stdio", "command": "npx", "args": ["@playwright/mcp@latest"]},
                                "claude-flow": {"type": "stdio", "command": "claude-flow", "args": ["mcp", "start"]},
                            }
                        }
                    }
                }
            )
            + "\n",
            encoding="utf-8",
        )

        with mock.patch.object(support_module.Path, "home", return_value=self.root):
            artifact = self.module.evaluate(self.root, self.target_root)

        global_mcp = artifact["host_runtime"]["claude_code_global_mcp"]
        self.assertEqual("issues_detected", global_mcp["status"])
        self.assertEqual(["project:D:/table/demo:playwright"], global_mcp["windows_bare_npx_servers"])
        self.assertEqual(["project:D:/table/demo:claude-flow"], global_mcp["claude_flow_mcp_servers"])


if __name__ == "__main__":
    unittest.main()
