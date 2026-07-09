from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
OFFLINE_GATE = REPO_ROOT / "scripts" / "verify" / "vibe-offline-skills-gate.ps1"
OFFLINE_REQUIRED_AUDIT = REPO_ROOT / "scripts" / "verify" / "vibe-offline-required-skills-audit.ps1"
OFFLINE_LOCK_PARITY_AUDIT = REPO_ROOT / "scripts" / "verify" / "vibe-offline-lock-parity-audit.ps1"
OFFLINE_HASH_AUDIT = REPO_ROOT / "scripts" / "verify" / "vibe-offline-hash-audit.ps1"
OFFLINE_LIB_ROOT = REPO_ROOT / "scripts" / "verify" / "lib"


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


class OfflineSkillsGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.powershell = resolve_powershell()
        if self.powershell is None:
            self.skipTest("PowerShell is required for offline skills gate tests.")
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self._write_fixture()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write(self, relative_path: str, content: str) -> None:
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")

    def _write_fixture(self) -> None:
        self._write("scripts/verify/vibe-offline-skills-gate.ps1", OFFLINE_GATE.read_text(encoding="utf-8"))
        self._write("scripts/verify/vibe-offline-required-skills-audit.ps1", OFFLINE_REQUIRED_AUDIT.read_text(encoding="utf-8"))
        self._write("scripts/verify/vibe-offline-lock-parity-audit.ps1", OFFLINE_LOCK_PARITY_AUDIT.read_text(encoding="utf-8"))
        self._write("scripts/verify/vibe-offline-hash-audit.ps1", OFFLINE_HASH_AUDIT.read_text(encoding="utf-8"))
        shutil.copytree(OFFLINE_LIB_ROOT, self.root / "scripts" / "verify" / "lib", dirs_exist_ok=True)

        self._write(
            "config/runtime-core-packaging.json",
            json.dumps(
                {
                    "default_profile": "minimal",
                    "canonical_vibe_payload": {"target_relpath": "skills/vibe"},
                    "profiles": {
                        "minimal": {
                            "managed_skill_inventory": {
                                "public_entry_skills": ["vibe"],
                                "starter_skill_names": [],
                                "optional_skill_names": [],
                            }
                        }
                    },
                },
                indent=2,
            )
            + "\n",
        )
        self._write("skills/vibe/SKILL.md", "---\nname: vibe\ndescription: canonical fixture\n---\n")
        self._write("skills/helper/SKILL.md", "---\nname: helper\ndescription: tracked extra fixture\n---\n")
        self._write(
            "core/skills/vibe/skill.json",
            json.dumps(
                {
                    "skill_id": "vibe",
                    "name": "Vibe Code Orchestrator",
                    "version": 1,
                    "summary": "fixture",
                    "instruction_path": "core/skills/vibe/instruction.md",
                    "compatibility_path": "core/skills/vibe/compatibility.json",
                    "source_of_truth": {"kind": "canonical-skill", "path": "skills/vibe/SKILL.md"},
                    "tags": ["router"],
                },
                indent=2,
            )
            + "\n",
        )
        self._write(
            "config/skills-lock.json",
            json.dumps(
                {
                    "version": 1,
                    "generated_at": "2026-04-01T12:00:00+08:00",
                    "source": "skills",
                    "skill_count": 1,
                    "total_bytes": 128,
                    "skills": [
                        {
                            "name": "helper",
                            "relative_path": "skills/helper",
                            "file_count": 1,
                            "bytes": 64,
                            "skill_md_hash": None,
                            "dir_hash": "fixture",
                        }
                    ],
                },
                indent=2,
            )
            + "\n",
        )

    def _run_script(self, script_name: str, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                self.powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(self.root / "scripts" / "verify" / script_name),
                *args,
            ],
            cwd=self.root,
            capture_output=True,
            text=True,
        )

    def test_required_skills_audit_accepts_managed_vibe_without_skills_lock_entry(self) -> None:
        result = self._run_script("vibe-offline-required-skills-audit.ps1")
        self.assertEqual(0, result.returncode, msg=result.stdout + result.stderr)
        self.assertNotIn("missing: vibe", result.stdout)

    def test_wrapper_skips_lock_based_audits_when_skills_lock_is_absent(self) -> None:
        (self.root / "config" / "skills-lock.json").unlink()

        result = self._run_script("vibe-offline-skills-gate.ps1", "-SkipHash")
        self.assertEqual(0, result.returncode, msg=result.stdout + result.stderr)
        self.assertIn("[SKIP] skills-lock audit requires a generated lock file", result.stdout)
        self.assertIn("Offline skill audit wrapper passed.", result.stdout)

    def test_lock_parity_audit_requires_explicit_lock_when_called_directly(self) -> None:
        (self.root / "config" / "skills-lock.json").unlink()

        result = self._run_script("vibe-offline-lock-parity-audit.ps1")
        self.assertNotEqual(0, result.returncode)
        combined = result.stdout + result.stderr
        self.assertIn("Skills lock not found:", combined)
        self.assertIn("run scripts/verify/vibe-generate-skills-lock.ps1 or pass -SkillsLockPath", combined)

    def test_lock_parity_audit_fails_when_managed_vibe_is_listed_in_skills_lock(self) -> None:
        payload = json.loads((self.root / "config" / "skills-lock.json").read_text(encoding="utf-8"))
        payload["skills"].append(
            {
                "name": "vibe",
                "relative_path": "skills/vibe",
                "file_count": 1,
                "bytes": 64,
                "skill_md_hash": None,
                "dir_hash": "fixture",
            }
        )
        payload["skill_count"] = len(payload["skills"])
        (self.root / "config" / "skills-lock.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")

        result = self._run_script("vibe-offline-lock-parity-audit.ps1")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("managed entries in lock: vibe", result.stdout)

    def test_lock_parity_audit_fails_when_tracked_skill_is_missing(self) -> None:
        shutil.rmtree(self.root / "skills" / "helper")

        result = self._run_script("vibe-offline-lock-parity-audit.ps1")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("missing in skills root: helper", result.stdout)

    def test_required_skills_audit_fails_when_managed_vibe_is_missing(self) -> None:
        shutil.rmtree(self.root / "skills" / "vibe")

        result = self._run_script("vibe-offline-required-skills-audit.ps1")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("missing: vibe", result.stdout)


if __name__ == "__main__":
    unittest.main()
