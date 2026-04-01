from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_PACKAGING = REPO_ROOT / "config" / "runtime-core-packaging.json"
MINIMAL_MANIFEST = REPO_ROOT / "config" / "runtime-core-packaging.minimal.json"
FULL_MANIFEST = REPO_ROOT / "config" / "runtime-core-packaging.full.json"
CATALOG_MANIFEST = REPO_ROOT / "config" / "skill-catalog-packaging.json"
CATALOG_PROFILES = REPO_ROOT / "config" / "skill-catalog-profiles.json"
CATALOG_GROUPS = REPO_ROOT / "config" / "skill-catalog-groups.json"

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
REPRESENTATIVE_NON_CORE_SKILL = "scikit-learn"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def count_files(root: Path) -> int:
    return sum(1 for candidate in root.rglob("*") if candidate.is_file())


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

    def rerun_python_installer_from_installed_runtime(self, target_root: Path, *, profile: str) -> dict:
        command = [
            "python3",
            str(REPO_ROOT / "scripts" / "install" / "install_vgo_adapter.py"),
            "--repo-root",
            str(target_root / "skills" / "vibe"),
            "--target-root",
            str(target_root),
            "--host",
            "codex",
            "--profile",
            profile,
        ]
        subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, check=True)
        return load_json(target_root / ".vibeskills" / "install-ledger.json")

    def rerun_powershell_installer_from_installed_runtime(self, target_root: Path, *, profile: str) -> dict:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell is required for installed-runtime rerun verification.")

        env = os.environ.copy()
        empty_bin = target_root.parent / "no-python-path"
        empty_bin.mkdir(parents=True, exist_ok=True)
        env["PATH"] = str(empty_bin)
        command = [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(REPO_ROOT / "scripts" / "install" / "Install-VgoAdapter.ps1"),
            "-RepoRoot",
            str(target_root / "skills" / "vibe"),
            "-TargetRoot",
            str(target_root),
            "-HostId",
            "codex",
            "-Profile",
            profile,
        ]
        subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, check=True, env=env)
        return load_json(target_root / ".vibeskills" / "install-ledger.json")

    def test_profile_packaging_manifests_exist_and_declare_distinct_payload_models(self) -> None:
        self.assertTrue(MINIMAL_MANIFEST.exists(), "minimal packaging manifest must exist")
        self.assertTrue(FULL_MANIFEST.exists(), "full packaging manifest must exist")
        self.assertTrue(CATALOG_MANIFEST.exists(), "skill catalog packaging manifest must exist")
        self.assertTrue(CATALOG_PROFILES.exists(), "skill catalog profiles manifest must exist")
        self.assertTrue(CATALOG_GROUPS.exists(), "skill catalog groups manifest must exist")

        runtime_packaging = load_json(RUNTIME_PACKAGING)
        minimal = load_json(MINIMAL_MANIFEST)
        full = load_json(FULL_MANIFEST)
        catalog = load_json(CATALOG_MANIFEST)
        profiles = load_json(CATALOG_PROFILES)
        groups = load_json(CATALOG_GROUPS)

        self.assertEqual("config/skill-catalog-packaging.json", runtime_packaging["catalog_packaging_manifest"])
        self.assertEqual("minimal", minimal["profile"])
        self.assertEqual("full", full["profile"])
        self.assertTrue(minimal["canonical_vibe_payload"]["enabled"])
        self.assertEqual("skills/vibe", minimal["canonical_vibe_payload"]["target_relpath"])
        self.assertFalse(full["copy_bundled_skills"])
        self.assertFalse(minimal["copy_bundled_skills"])
        self.assertEqual("foundation-workflow", minimal["catalog_profile"])
        self.assertEqual("default-full", full["catalog_profile"])
        self.assertEqual("skill-catalog", catalog["package_id"])
        self.assertEqual("bundled/skills", catalog["catalog_root"])
        self.assertEqual("config/skill-catalog-profiles.json", catalog["profiles_manifest"])
        self.assertEqual("config/skill-catalog-groups.json", catalog["groups_manifest"])
        self.assertIn("foundation-workflow", profiles["profiles"])
        self.assertIn("default-full", profiles["profiles"])
        self.assertIn("workflow-foundation", groups["groups"])
        self.assertIn("optional-review", groups["groups"])

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
            self.assertEqual(["runtime-core"], ledger["managed_runtime_units"])
            self.assertEqual(sorted(REQUIRED_RUNTIME_SKILLS), ledger["managed_runtime_skill_names"])
            self.assertEqual(["foundation-workflow"], ledger["managed_catalog_profiles"])
            self.assertEqual(sorted(REQUIRED_WORKFLOW_SKILLS), ledger["managed_catalog_skill_names"])
            self.assertEqual("core-default", ledger["packaging_manifest"]["runtime_profile"])
            self.assertEqual("foundation-workflow", ledger["packaging_manifest"]["catalog_profile"])
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
            self.assertEqual(["runtime-core"], full_ledger["managed_runtime_units"])
            self.assertEqual(sorted(REQUIRED_RUNTIME_SKILLS), full_ledger["managed_runtime_skill_names"])
            self.assertEqual(["default-full"], full_ledger["managed_catalog_profiles"])
            self.assertEqual("core-default", full_ledger["packaging_manifest"]["runtime_profile"])
            self.assertEqual("default-full", full_ledger["packaging_manifest"]["catalog_profile"])
            self.assertIn(REPRESENTATIVE_NON_CORE_SKILL, full_ledger["managed_catalog_skill_names"])
            self.assertGreater(
                full_ledger["payload_summary"]["installed_skill_count"],
                minimal_ledger["payload_summary"]["installed_skill_count"],
            )
            self.assertGreater(
                full_ledger["payload_summary"]["installed_file_count"],
                minimal_ledger["payload_summary"]["installed_file_count"],
            )

    def test_full_rerun_from_installed_runtime_preserves_catalog_surface_for_python_installer(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir) / "full-root"
            target_root.mkdir(parents=True, exist_ok=True)

            first_ledger = self.install_profile(target_root, profile="full")
            rerun_ledger = self.rerun_python_installer_from_installed_runtime(target_root, profile="full")

            installed_skills = {
                candidate.name
                for candidate in (target_root / "skills").iterdir()
                if candidate.is_dir()
            }

            self.assertIn(REPRESENTATIVE_NON_CORE_SKILL, installed_skills)
            self.assertTrue((target_root / "skills" / REPRESENTATIVE_NON_CORE_SKILL).is_dir())
            self.assertEqual(["default-full"], rerun_ledger["managed_catalog_profiles"])
            self.assertIn(REPRESENTATIVE_NON_CORE_SKILL, rerun_ledger["managed_catalog_skill_names"])
            self.assertEqual(set(first_ledger["managed_catalog_skill_names"]), set(rerun_ledger["managed_catalog_skill_names"]))

    def test_python_installed_runtime_reruns_do_not_absorb_or_prune_foreign_skill_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir) / "full-root"
            target_root.mkdir(parents=True, exist_ok=True)

            self.install_profile(target_root, profile="full")
            foreign_skill_root = target_root / "skills" / "foreign-user-skill"
            foreign_skill_root.mkdir(parents=True, exist_ok=True)
            (foreign_skill_root / "SKILL.md").write_text("---\nname: foreign-user-skill\n---\n", encoding="utf-8")

            rerun_full_ledger = self.rerun_python_installer_from_installed_runtime(target_root, profile="full")
            self.assertTrue(foreign_skill_root.exists())
            self.assertNotIn("foreign-user-skill", rerun_full_ledger["managed_catalog_skill_names"])
            self.assertNotIn("foreign-user-skill", rerun_full_ledger["managed_skill_names"])

            rerun_minimal_ledger = self.rerun_python_installer_from_installed_runtime(target_root, profile="minimal")
            self.assertTrue(foreign_skill_root.exists())
            self.assertNotIn("foreign-user-skill", rerun_minimal_ledger["managed_catalog_skill_names"])
            self.assertNotIn("foreign-user-skill", rerun_minimal_ledger["managed_skill_names"])

    def test_full_rerun_from_installed_runtime_preserves_catalog_surface_for_powershell_installer(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir) / "full-root"
            target_root.mkdir(parents=True, exist_ok=True)

            first_ledger = self.install_profile(target_root, profile="full")
            rerun_ledger = self.rerun_powershell_installer_from_installed_runtime(target_root, profile="full")

            installed_skills = {
                candidate.name
                for candidate in (target_root / "skills").iterdir()
                if candidate.is_dir()
            }

            self.assertIn(REPRESENTATIVE_NON_CORE_SKILL, installed_skills)
            self.assertTrue((target_root / "skills" / REPRESENTATIVE_NON_CORE_SKILL).is_dir())
            self.assertEqual(["default-full"], rerun_ledger["managed_catalog_profiles"])
            self.assertIn(REPRESENTATIVE_NON_CORE_SKILL, rerun_ledger["managed_catalog_skill_names"])
            self.assertEqual(set(first_ledger["managed_catalog_skill_names"]), set(rerun_ledger["managed_catalog_skill_names"]))

    def test_powershell_installed_runtime_reruns_do_not_absorb_or_prune_foreign_skill_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir) / "full-root"
            target_root.mkdir(parents=True, exist_ok=True)

            self.install_profile(target_root, profile="full")
            foreign_skill_root = target_root / "skills" / "foreign-user-skill"
            foreign_skill_root.mkdir(parents=True, exist_ok=True)
            (foreign_skill_root / "SKILL.md").write_text("---\nname: foreign-user-skill\n---\n", encoding="utf-8")

            rerun_full_ledger = self.rerun_powershell_installer_from_installed_runtime(target_root, profile="full")
            self.assertTrue(foreign_skill_root.exists())
            self.assertNotIn("foreign-user-skill", rerun_full_ledger["managed_catalog_skill_names"])
            self.assertNotIn("foreign-user-skill", rerun_full_ledger["managed_skill_names"])

            rerun_minimal_ledger = self.rerun_powershell_installer_from_installed_runtime(target_root, profile="minimal")
            self.assertTrue(foreign_skill_root.exists())
            self.assertNotIn("foreign-user-skill", rerun_minimal_ledger["managed_catalog_skill_names"])
            self.assertNotIn("foreign-user-skill", rerun_minimal_ledger["managed_skill_names"])

    def test_python_installed_runtime_rejects_non_leaf_catalog_skill_names_from_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            source_root = root / "source-root"
            fresh_target = root / "fresh-target"
            source_root.mkdir(parents=True, exist_ok=True)
            fresh_target.mkdir(parents=True, exist_ok=True)

            self.install_profile(source_root, profile="full")
            ledger_path = source_root / ".vibeskills" / "install-ledger.json"
            ledger = load_json(ledger_path)
            ledger["managed_catalog_skill_names"] = ["../../outside"]
            ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            result = subprocess.run(
                [
                    "python3",
                    str(REPO_ROOT / "scripts" / "install" / "install_vgo_adapter.py"),
                    "--repo-root",
                    str(source_root / "skills" / "vibe"),
                    "--target-root",
                    str(fresh_target),
                    "--host",
                    "codex",
                    "--profile",
                    "full",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(0, result.returncode)
            self.assertIn("Invalid skill name", result.stderr or result.stdout)

    def test_python_installed_runtime_rejects_non_leaf_previous_managed_skill_names_from_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            target_root = root / "full-root"
            outside_root = root / "outside"
            target_root.mkdir(parents=True, exist_ok=True)
            outside_root.mkdir(parents=True, exist_ok=True)
            outside_note = outside_root / "note.txt"
            outside_note.write_text("keep me\n", encoding="utf-8")

            self.install_profile(target_root, profile="full")
            ledger_path = target_root / ".vibeskills" / "install-ledger.json"
            ledger = load_json(ledger_path)
            ledger["managed_runtime_skill_names"] = ["../../outside", "vibe"]
            ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            result = subprocess.run(
                [
                    "python3",
                    str(REPO_ROOT / "scripts" / "install" / "install_vgo_adapter.py"),
                    "--repo-root",
                    str(target_root / "skills" / "vibe"),
                    "--target-root",
                    str(target_root),
                    "--host",
                    "codex",
                    "--profile",
                    "full",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(0, result.returncode)
            self.assertIn("Invalid skill name", result.stderr or result.stdout)
            self.assertTrue(outside_root.exists())
            self.assertEqual("keep me\n", outside_note.read_text(encoding="utf-8"))

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
            self.assertEqual(["runtime-core"], ledger["managed_runtime_units"])
            self.assertEqual(["foundation-workflow"], ledger["managed_catalog_profiles"])
            self.assertEqual(sorted(MINIMAL_REQUIRED_SKILLS), ledger["managed_skill_names"])
            self.assertEqual(sorted(MINIMAL_REQUIRED_SKILLS), ledger["payload_summary"]["installed_skill_names"])

    def test_powershell_minimal_rerun_prunes_previously_managed_full_profile_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir) / "shared-root"
            target_root.mkdir(parents=True, exist_ok=True)

            self.install_profile(target_root, profile="full")
            ledger = self.rerun_powershell_installer_from_installed_runtime(target_root, profile="minimal")

            installed_skills = {
                candidate.name
                for candidate in (target_root / "skills").iterdir()
                if candidate.is_dir()
            }

            self.assertEqual(MINIMAL_REQUIRED_SKILLS, installed_skills)
            self.assertNotIn(REPRESENTATIVE_NON_CORE_SKILL, installed_skills)
            self.assertEqual(["runtime-core"], ledger["managed_runtime_units"])
            self.assertEqual(["foundation-workflow"], ledger["managed_catalog_profiles"])
            self.assertEqual(sorted(MINIMAL_REQUIRED_SKILLS), ledger["managed_skill_names"])

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
