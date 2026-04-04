from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_PATH = REPO_ROOT / "scripts" / "verify" / "vibe-bom-frontmatter-gate.ps1"
GOVERNANCE_PATH = REPO_ROOT / "config" / "version-governance.json"


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


class FrontmatterGateScopeActivationTests(unittest.TestCase):
    def test_gate_skips_missing_bundled_scope_when_topology_does_not_define_it(self) -> None:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell not available")

        governance = json.loads(GOVERNANCE_PATH.read_text(encoding="utf-8"))
        target_ids = {target["id"] for target in governance["mirror_topology"]["targets"]}
        self.assertNotIn("bundled", target_ids)

        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir) / "target"
            installed_skill = target_root / "skills" / "vibe" / "SKILL.md"
            installed_skill.parent.mkdir(parents=True, exist_ok=True)
            installed_skill.write_text("---\nname: vibe\n---\n", encoding="utf-8", newline="\n")

            result = subprocess.run(
                [
                    powershell,
                    "-NoProfile",
                    "-File",
                    str(GATE_PATH),
                    "-TargetRoot",
                    str(target_root),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("[SKIP] bundled", result.stdout)
        self.assertIn("[PASS] installed", result.stdout)

    def test_gate_uses_runtime_config_installed_target_and_closure_gate_paths(self) -> None:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell not available")

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)

            def write(relative_path: str, content: str) -> Path:
                path = root / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8", newline="\n")
                return path

            write(
                "scripts/common/vibe-governance-helpers.ps1",
                (REPO_ROOT / "scripts" / "common" / "vibe-governance-helpers.ps1").read_text(encoding="utf-8"),
            )
            write(
                "scripts/common/runtime_contracts.py",
                (REPO_ROOT / "scripts" / "common" / "runtime_contracts.py").read_text(encoding="utf-8"),
            )
            write(
                "scripts/verify/vibe-bom-frontmatter-gate.ps1",
                GATE_PATH.read_text(encoding="utf-8"),
            )
            write("docs/frontmatter-bom-governance.md", "stop-ship\nbyte-0\n")
            write("scripts/governance/release-cut.ps1", "Write-VgoUtf8NoBomText\n")
            write(
                "scripts/verify/custom-installed-runtime-freshness-gate.ps1",
                "Write-Host 'custom freshness'\n",
            )
            write(
                "config/frontmatter-integrity-policy.json",
                json.dumps(
                    {
                        "version": 1,
                        "scopes": [
                            {
                                "id": "canonical",
                                "root": "canonical",
                                "requires_target_root": False,
                                "relpaths": ["SKILL.md"],
                            },
                            {
                                "id": "installed",
                                "root": "installed",
                                "requires_target_root": True,
                                "relpaths": ["SKILL.md"],
                            },
                        ],
                    },
                    indent=2,
                )
                + "\n",
            )
            write(
                "config/version-governance.json",
                json.dumps(
                    {
                        "release": {
                            "version": "9.9.9",
                            "updated": "2026-04-03",
                            "channel": "stable",
                            "notes": "fixture",
                        },
                        "source_of_truth": {"canonical_root": "."},
                        "mirror_topology": {
                            "canonical_target_id": "canonical",
                            "sync_source_target_id": "canonical",
                            "targets": [
                                {
                                    "id": "canonical",
                                    "path": ".",
                                    "role": "canonical",
                                    "required": True,
                                    "presence_policy": "required",
                                    "sync_enabled": False,
                                    "parity_policy": "authoritative",
                                }
                            ],
                        },
                        "execution_context_policy": {
                            "require_outer_git_root": True,
                            "fail_if_script_path_is_under_mirror_root": True,
                        },
                        "runtime": {
                            "installed_runtime": {
                                "target_relpath": "custom/vibe-runtime",
                                "post_install_gate": "scripts/verify/custom-installed-runtime-freshness-gate.ps1",
                            }
                        },
                    },
                    indent=2,
                )
                + "\n",
            )
            write("SKILL.md", "---\nname: vibe\n---\n")

            target_root = root / "target"
            installed_skill = target_root / "custom" / "vibe-runtime" / "SKILL.md"
            installed_skill.parent.mkdir(parents=True, exist_ok=True)
            installed_skill.write_text("---\nname: vibe\n---\n", encoding="utf-8", newline="\n")

            subprocess.run(["git", "init"], cwd=root, capture_output=True, text=True, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, capture_output=True, text=True, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, capture_output=True, text=True, check=True)

            result = subprocess.run(
                [
                    powershell,
                    "-NoProfile",
                    "-File",
                    str(root / "scripts" / "verify" / "vibe-bom-frontmatter-gate.ps1"),
                    "-TargetRoot",
                    str(target_root),
                ],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("[PASS] installed", result.stdout)
        self.assertIn("custom/vibe-runtime/SKILL.md", result.stdout)
        self.assertIn("custom-installed-runtime-freshness-gate.ps1", result.stdout)


if __name__ == "__main__":
    unittest.main()
