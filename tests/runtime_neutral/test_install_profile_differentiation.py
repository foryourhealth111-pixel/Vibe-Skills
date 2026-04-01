from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MINIMAL_MANIFEST = REPO_ROOT / "config" / "runtime-core-packaging.minimal.json"
FULL_MANIFEST = REPO_ROOT / "config" / "runtime-core-packaging.full.json"

REQUIRED_RUNTIME_SKILLS = {
    "vibe",
    "dialectic",
    "local-vco-roles",
    "spec-kit-vibe-compat",
    "superclaude-framework-compat",
    "ralph-loop",
    "cancel-ralph",
    "tdd-guide",
    "think-harder",
}

REQUIRED_WORKFLOW_SKILLS = {
    "brainstorming",
    "writing-plans",
    "subagent-driven-development",
    "systematic-debugging",
}

MINIMAL_REQUIRED_SKILLS = REQUIRED_RUNTIME_SKILLS | REQUIRED_WORKFLOW_SKILLS
MINIMAL_ALLOWLIST_SKILLS = (REQUIRED_RUNTIME_SKILLS - {"vibe"}) | REQUIRED_WORKFLOW_SKILLS
REPRESENTATIVE_NON_CORE_SKILL = "scikit-learn"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def count_files(root: Path) -> int:
    return sum(1 for candidate in root.rglob("*") if candidate.is_file())


class InstallProfileDifferentiationTests(unittest.TestCase):
    def install_profile(self, target_root: Path, *, profile: str) -> dict:
        command = [
            "bash",
            str(REPO_ROOT / "install.sh"),
            "--host",
            "codex",
            "--profile",
            profile,
            "--target-root",
            str(target_root),
        ]
        subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, check=True)
        ledger_path = target_root / ".vibeskills" / "install-ledger.json"
        self.assertTrue(ledger_path.exists())
        return load_json(ledger_path)

    def test_profile_packaging_manifests_exist_and_declare_distinct_payload_models(self) -> None:
        self.assertTrue(MINIMAL_MANIFEST.exists(), "minimal packaging manifest must exist")
        self.assertTrue(FULL_MANIFEST.exists(), "full packaging manifest must exist")

        minimal = load_json(MINIMAL_MANIFEST)
        full = load_json(FULL_MANIFEST)

        self.assertEqual("minimal", minimal["profile"])
        self.assertEqual("full", full["profile"])
        self.assertEqual(sorted(MINIMAL_ALLOWLIST_SKILLS), sorted(minimal["skills_allowlist"]))
        self.assertTrue(minimal["canonical_vibe_payload"]["enabled"])
        self.assertEqual("skills/vibe", minimal["canonical_vibe_payload"]["target_relpath"])
        self.assertTrue(full["copy_bundled_skills"])
        self.assertFalse(minimal["copy_bundled_skills"])

    def test_minimal_install_contains_only_required_foundation_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir) / "minimal-root"
            target_root.mkdir(parents=True, exist_ok=True)

            ledger = self.install_profile(target_root, profile="minimal")
            installed_skills = {
                candidate.name
                for candidate in (target_root / "skills").iterdir()
                if candidate.is_dir()
            }

            self.assertEqual(MINIMAL_REQUIRED_SKILLS, installed_skills)
            self.assertNotIn(REPRESENTATIVE_NON_CORE_SKILL, installed_skills)
            self.assertEqual("minimal", ledger["profile"])
            self.assertEqual(len(installed_skills), ledger["payload_summary"]["installed_skill_count"])
            # In a fresh temp target, every file should be installer-owned.
            self.assertEqual(count_files(target_root), ledger["payload_summary"]["installed_file_count"])

    def test_full_install_extends_minimal_payload_and_records_larger_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            minimal_root = root / "minimal-root"
            full_root = root / "full-root"
            minimal_root.mkdir(parents=True, exist_ok=True)
            full_root.mkdir(parents=True, exist_ok=True)

            minimal_ledger = self.install_profile(minimal_root, profile="minimal")
            full_ledger = self.install_profile(full_root, profile="full")

            minimal_skills = {
                candidate.name
                for candidate in (minimal_root / "skills").iterdir()
                if candidate.is_dir()
            }
            full_skills = {
                candidate.name
                for candidate in (full_root / "skills").iterdir()
                if candidate.is_dir()
            }

            self.assertTrue(MINIMAL_REQUIRED_SKILLS.issubset(full_skills))
            self.assertIn(REPRESENTATIVE_NON_CORE_SKILL, full_skills)
            self.assertGreater(len(full_skills), len(minimal_skills))
            self.assertGreater(
                full_ledger["payload_summary"]["installed_skill_count"],
                minimal_ledger["payload_summary"]["installed_skill_count"],
            )
            self.assertGreater(
                full_ledger["payload_summary"]["installed_file_count"],
                minimal_ledger["payload_summary"]["installed_file_count"],
            )

    def test_minimal_reinstall_prunes_previously_managed_full_profile_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir) / "shared-root"
            target_root.mkdir(parents=True, exist_ok=True)

            self.install_profile(target_root, profile="full")
            ledger = self.install_profile(target_root, profile="minimal")

            installed_skills = {
                candidate.name
                for candidate in (target_root / "skills").iterdir()
                if candidate.is_dir()
            }

            self.assertEqual(MINIMAL_REQUIRED_SKILLS, installed_skills)
            self.assertNotIn(REPRESENTATIVE_NON_CORE_SKILL, installed_skills)
            self.assertEqual(sorted(MINIMAL_REQUIRED_SKILLS), ledger["managed_skill_names"])
            self.assertEqual(sorted(MINIMAL_REQUIRED_SKILLS), ledger["payload_summary"]["installed_skill_names"])

    def test_payload_summary_ignores_preexisting_foreign_host_content(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir) / "shared-root"
            foreign_skill_root = target_root / "skills" / "foreign-user-skill"
            foreign_file = target_root / "host-notes.txt"
            target_root.mkdir(parents=True, exist_ok=True)
            foreign_skill_root.mkdir(parents=True, exist_ok=True)
            (foreign_skill_root / "SKILL.md").write_text("---\nname: foreign-user-skill\n---\n", encoding="utf-8")
            foreign_file.write_text("user content\n", encoding="utf-8")

            ledger = self.install_profile(target_root, profile="minimal")

            installed_skills = {
                candidate.name
                for candidate in (target_root / "skills").iterdir()
                if candidate.is_dir()
            }
            mirrored_foreign_skill = target_root / "skills" / "vibe" / "bundled" / "skills" / "foreign-user-skill"
            self.assertIn("foreign-user-skill", installed_skills)
            self.assertFalse(mirrored_foreign_skill.exists())
            self.assertNotIn("foreign-user-skill", ledger["payload_summary"]["installed_skill_names"])
            self.assertEqual(sorted(MINIMAL_REQUIRED_SKILLS), ledger["payload_summary"]["installed_skill_names"])
            self.assertLess(ledger["payload_summary"]["installed_file_count"], count_files(target_root))


if __name__ == "__main__":
    unittest.main()
