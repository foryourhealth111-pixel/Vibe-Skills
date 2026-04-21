from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "setup" / "repair-claude-code-global-mcp.ps1"


def resolve_powershell() -> str | None:
    candidates = [
        shutil.which("pwsh"),
        shutil.which("pwsh.exe"),
        r"C:\Program Files\PowerShell\7\pwsh.exe",
        r"C:\Program Files\PowerShell\7-preview\pwsh.exe",
        shutil.which("powershell"),
        shutil.which("powershell.exe"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))
    return None


class ClaudeGlobalMcpRepairTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.config_path = self.root / ".claude.json"
        self.config_path.write_text(
            json.dumps(
                {
                    "mcpServers": {
                        "chrome": {"type": "stdio", "command": "npx", "args": ["chrome-devtools-mcp@latest"]},
                        "ruflo": {"type": "stdio", "command": "claude-flow.cmd", "args": ["mcp", "start"]},
                        "claude-flow": {"type": "stdio", "command": "claude-flow", "args": ["mcp", "start"]},
                    },
                    "projects": {
                        "D:/table/demo": {
                            "mcpServers": {
                                "playwright": {"type": "stdio", "command": "npx", "args": ["@playwright/mcp@latest"]},
                                "claude-flow": {"type": "stdio", "command": "claude-flow", "args": ["mcp", "start"]},
                            },
                            "disabledMcpServers": ["claude-flow", "other"],
                        }
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_repair_script_wraps_npx_and_removes_claude_flow_aliases(self) -> None:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell executable not available in PATH")

        result = subprocess.run(
            [
                powershell,
                "-NoProfile",
                "-File",
                str(SCRIPT_PATH),
                "-UserConfigPath",
                str(self.config_path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        payload = json.loads(result.stdout)
        config = json.loads(self.config_path.read_text(encoding="utf-8"))

        self.assertNotEqual(str(self.config_path), payload["backup_path"])
        self.assertTrue(Path(payload["backup_path"]).exists())
        self.assertIn("global:chrome", payload["wrapped_servers"])
        self.assertIn("project:D:/table/demo:playwright", payload["wrapped_servers"])
        self.assertIn("global:ruflo", payload["removed_servers"])
        self.assertIn("global:claude-flow", payload["removed_servers"])
        self.assertIn("project:D:/table/demo:claude-flow", payload["removed_servers"])
        self.assertEqual("cmd", config["mcpServers"]["chrome"]["command"])
        self.assertEqual(["/c", "npx", "chrome-devtools-mcp@latest"], config["mcpServers"]["chrome"]["args"])
        self.assertNotIn("ruflo", config["mcpServers"])
        self.assertNotIn("claude-flow", config["mcpServers"])
        self.assertEqual("cmd", config["projects"]["D:/table/demo"]["mcpServers"]["playwright"]["command"])
        self.assertEqual(["other"], config["projects"]["D:/table/demo"]["disabledMcpServers"])

    def test_repair_script_preserves_claude_flow_aliases_when_requested(self) -> None:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell executable not available in PATH")

        result = subprocess.run(
            [
                powershell,
                "-NoProfile",
                "-File",
                str(SCRIPT_PATH),
                "-UserConfigPath",
                str(self.config_path),
                "-PreserveClaudeFlowAliases",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        payload = json.loads(result.stdout)
        config = json.loads(self.config_path.read_text(encoding="utf-8"))

        self.assertEqual([], payload["removed_servers"])
        self.assertEqual([], payload["cleaned_lists"])
        self.assertIn("claude-flow", config["mcpServers"])
        self.assertIn("ruflo", config["mcpServers"])
        self.assertEqual(["claude-flow", "other"], config["projects"]["D:/table/demo"]["disabledMcpServers"])
        self.assertEqual("cmd", config["mcpServers"]["chrome"]["command"])
        self.assertEqual("cmd", config["projects"]["D:/table/demo"]["mcpServers"]["playwright"]["command"])


if __name__ == "__main__":
    unittest.main()
