from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
OFFLINE_GATE = REPO_ROOT / "scripts" / "verify" / "vibe-offline-skills-gate.ps1"


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
    bundled_required_skills = [
        "brainstorming",
        "cancel-ralph",
        "dialectic",
        "local-vco-roles",
        "ralph-loop",
        "spec-kit-vibe-compat",
        "subagent-driven-development",
        "superclaude-framework-compat",
        "systematic-debugging",
        "tdd-guide",
        "think-harder",
        "vibe-do-it",
        "vibe-how-do-we-do",
        "vibe-what-do-i-want",
        "writing-plans",
    ]

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
        self._write("config/pack-manifest.json", json.dumps({"packs": []}, indent=2) + "\n")
        self._write("SKILL.md", "---\nname: vibe\ndescription: canonical fixture\n---\n")
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
                    "source_of_truth": {"kind": "canonical-skill", "path": "SKILL.md"},
                    "tags": ["router"],
                },
                indent=2,
            )
            + "\n",
        )

        for skill_name in self.bundled_required_skills:
            self._write(
                f"bundled/skills/{skill_name}/SKILL.md",
                f"---\nname: {skill_name}\ndescription: bundled fixture\n---\n",
            )

        lock_skills = [
            {
                "name": skill_name,
                "relative_path": f"bundled/skills/{skill_name}",
                "file_count": 1,
                "bytes": 64,
                "skill_md_hash": None,
                "dir_hash": "fixture",
            }
            for skill_name in self.bundled_required_skills
        ]
        self._write(
            "config/skills-lock.json",
            json.dumps(
                {
                    "version": 1,
                    "generated_at": "2026-04-01T12:00:00+08:00",
                    "source": "bundled/skills",
                    "skill_count": len(lock_skills),
                    "total_bytes": 768,
                    "skills": lock_skills,
                },
                indent=2,
            )
            + "\n",
        )

    def _run_gate(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                self.powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(self.root / "scripts" / "verify" / "vibe-offline-skills-gate.ps1"),
                "-SkipHash",
            ],
            cwd=self.root,
            capture_output=True,
            text=True,
        )

    def test_gate_accepts_canonical_vibe_when_not_present_under_bundled_skills(self) -> None:
        result = self._run_gate()
        self.assertEqual(0, result.returncode, msg=result.stdout + result.stderr)
        self.assertNotIn("missing required routed skills: vibe", result.stdout)
        self.assertNotIn("skills-lock entries missing in skills root: vibe", result.stdout)

    def test_gate_fails_when_stale_vibe_entry_remains_in_bundled_skills_lock(self) -> None:
        payload = json.loads((self.root / "config" / "skills-lock.json").read_text(encoding="utf-8"))
        payload["skills"].append(
            {
                "name": "vibe",
                "relative_path": "bundled/skills/vibe",
                "file_count": 1,
                "bytes": 64,
                "skill_md_hash": None,
                "dir_hash": "fixture",
            }
        )
        payload["skill_count"] = len(payload["skills"])
        (self.root / "config" / "skills-lock.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")

        result = self._run_gate()
        self.assertNotEqual(0, result.returncode)
        self.assertIn("skills-lock entries missing in skills root: vibe", result.stdout)

    def test_gate_fails_when_required_wrapper_skill_is_missing(self) -> None:
        wrapper_root = self.root / "bundled" / "skills" / "vibe-do-it"
        shutil.rmtree(wrapper_root)

        payload = json.loads((self.root / "config" / "skills-lock.json").read_text(encoding="utf-8"))
        payload["skills"] = [
            item
            for item in payload["skills"]
            if item.get("name") != "vibe-do-it"
        ]
        payload["skill_count"] = len(payload["skills"])
        (self.root / "config" / "skills-lock.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")

        result = self._run_gate()
        self.assertNotEqual(0, result.returncode)
        self.assertIn("missing required routed skills: vibe-do-it", result.stdout)


if __name__ == "__main__":
    unittest.main()
