from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_SRC = REPO_ROOT / "apps" / "vgo-cli" / "src"
INSTALLER_SRC = REPO_ROOT / "packages" / "installer-core" / "src"
CONTRACTS_SRC = REPO_ROOT / "packages" / "contracts" / "src"
SHELL_ENTRYPOINT = REPO_ROOT / "uninstall.sh"
POWERSHELL_ENTRYPOINT = REPO_ROOT / "uninstall.ps1"


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


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_simple_vibe_receipt(skills_dir: Path) -> Path:
    install_root = skills_dir / "vibe"
    skill_path = install_root / "SKILL.md"
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text("---\nname: vibe\n---\n", encoding="utf-8")
    write_json(
        install_root / ".vibeskills" / "install-receipt.json",
        {
            "schema_version": 1,
            "receipt_kind": "vibe-skill-install",
            "skill_id": "vibe",
            "skills_dir": str(skills_dir.resolve()),
            "install_root": str(install_root.resolve()),
            "files": [{"path": "SKILL.md", "sha256": "fixture"}],
        },
    )
    return skill_path


class UnifiedUninstallTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.target_root = self.root / "target"
        self.target_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_python_uninstall(
        self,
        *,
        host: str = "codex",
        purge_empty_dirs: bool = False,
    ) -> dict[str, object]:
        env = os.environ.copy()
        python_path_entries = [str(CLI_SRC), str(INSTALLER_SRC), str(CONTRACTS_SRC)]
        if env.get("PYTHONPATH"):
            python_path_entries.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(python_path_entries)

        cmd = [
            sys.executable,
            "-m",
            "vgo_installer.uninstall_runtime",
            "--repo-root",
            str(REPO_ROOT),
            "--target-root",
            str(self.target_root),
            "--host",
            host,
            "--profile",
            "full",
        ]
        if purge_empty_dirs:
            cmd.append("--purge-empty-dirs")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, env=env)
        return json.loads(result.stdout)

    def test_entrypoint_shell_uninstalls_receipt_owned_vibe_skill(self) -> None:
        skills_dir = self.target_root / "skills"
        skill_path = write_simple_vibe_receipt(skills_dir)

        result = subprocess.run(
            [
                "bash",
                str(SHELL_ENTRYPOINT),
                "--skills-dir",
                str(skills_dir),
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        payload = json.loads(result.stdout)
        self.assertEqual(["SKILL.md"], payload["removed_files"])
        self.assertFalse(skill_path.exists())

    def test_entrypoint_powershell_uninstalls_receipt_owned_vibe_skill(self) -> None:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell not available")

        skills_dir = self.target_root / "skills"
        skill_path = write_simple_vibe_receipt(skills_dir)

        result = subprocess.run(
            [
                powershell,
                "-NoLogo",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(POWERSHELL_ENTRYPOINT),
                "-SkillsDir",
                str(skills_dir),
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        payload = json.loads(result.stdout)
        self.assertEqual(["SKILL.md"], payload["removed_files"])
        self.assertFalse(skill_path.exists())

    def test_uninstall_prefers_install_ledger_and_skips_foreign_paths(self) -> None:
        managed_file = self.target_root / "commands" / "vibe.md"
        foreign_file = self.target_root / "commands" / "user.md"
        managed_file.parent.mkdir(parents=True, exist_ok=True)
        managed_file.write_text("managed\n", encoding="utf-8")
        foreign_file.write_text("foreign\n", encoding="utf-8")
        write_json(
            self.target_root / ".vibeskills" / "install-ledger.json",
            {
                "schema_version": 1,
                "host_id": "cursor",
                "target_root": str(self.target_root.resolve()),
                "install_mode": "preview-guidance",
                "profile": "full",
                "created_paths": ["commands/vibe.md"],
                "managed_json_paths": [],
                "generated_from_template_if_absent": [],
                "host_visible_entry_paths": [],
                "runtime_root": "skills/vibe",
                "canonical_vibe_root": "skills/vibe",
            },
        )

        payload = self.run_python_uninstall(host="cursor")

        self.assertFalse(managed_file.exists())
        self.assertTrue(foreign_file.exists())
        self.assertIn("ledger", payload["ownership_source"])
        self.assertIn("commands/vibe.md", payload["deleted_paths"])
        self.assertIn("commands/user.md", payload["skipped_foreign_paths"])

    def test_uninstall_preserves_workspace_project_sidecar(self) -> None:
        project_path = self.target_root / ".vibeskills" / "project.json"
        requirement_path = self.target_root / ".vibeskills" / "docs" / "requirements" / "req.md"
        write_json(
            project_path,
            {
                "schema_version": 1,
                "workspace_root": str(self.target_root.resolve()),
                "workspace_sidecar_root": str((self.target_root / ".vibeskills").resolve()),
            },
        )
        requirement_path.parent.mkdir(parents=True, exist_ok=True)
        requirement_path.write_text("# runtime artifact\n", encoding="utf-8")

        payload = self.run_python_uninstall(host="cursor")

        self.assertTrue(project_path.exists())
        self.assertTrue(requirement_path.exists())
        self.assertNotIn(".vibeskills", payload["deleted_paths"])

    def test_uninstall_writes_receipt_and_purges_empty_owned_directories(self) -> None:
        managed_file = self.target_root / "commands" / "vibe.md"
        managed_file.parent.mkdir(parents=True, exist_ok=True)
        managed_file.write_text("managed\n", encoding="utf-8")

        payload = self.run_python_uninstall(host="cursor", purge_empty_dirs=True)

        receipt_path = Path(payload["receipt_path"])
        self.assertTrue(receipt_path.exists())
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual("PASS", receipt["gate_result"])
        self.assertIn("commands/vibe.md", receipt["deleted_paths"])
        self.assertFalse((self.target_root / "commands").exists())
        self.assertTrue(receipt["empty_dirs_removed"])


if __name__ == "__main__":
    unittest.main()
