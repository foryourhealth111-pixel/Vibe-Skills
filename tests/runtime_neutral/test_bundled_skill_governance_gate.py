from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GATE = REPO_ROOT / "scripts" / "verify" / "vibe-built-in-skill-governance-gate.ps1"
POLICY = REPO_ROOT / "config" / "bundled-skill-governance-policy.json"


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


class BuiltInSkillGovernanceGateTests(unittest.TestCase):
    def test_gate_script_uses_cross_platform_forward_slash_join_path_literals(self) -> None:
        text = GATE.read_text(encoding="utf-8-sig")
        self.assertIn("outputs/verify", text)
        self.assertIn("../..", text)
        self.assertIn("config/bundled-skill-governance-policy.json", text)
        self.assertNotIn("outputs\\verify", text)
        self.assertNotIn("config\\bundled-skill-governance-policy.json", text)

    def setUp(self) -> None:
        self.powershell = resolve_powershell()
        if self.powershell is None:
            self.skipTest("PowerShell is required for built-in skill governance gate tests.")
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self._write_fixture()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write(self, relative_path: str, content: str) -> None:
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")

    def _write_skill(self, skill_id: str, description: str, body: str) -> None:
        self._write(
            f"bundled/skills/{skill_id}/SKILL.md",
            (
                "---\n"
                f"name: {skill_id}\n"
                f"description: {description}\n"
                "---\n\n"
                f"# {skill_id}\n\n"
                f"{body}\n"
            ),
        )

    def _write_fixture(self) -> None:
        self._write("scripts/verify/vibe-built-in-skill-governance-gate.ps1", GATE.read_text(encoding="utf-8-sig"))
        self._write("config/bundled-skill-governance-policy.json", POLICY.read_text(encoding="utf-8"))

        self._write(
            "config/pack-manifest.json",
            json.dumps(
                {
                    "packs": [
                        {
                            "id": "fixture-pack",
                            "skill_candidates": ["clean-skill", "partial-skill"],
                            "defaults_by_task": {"planning": "clean-skill"},
                        }
                    ]
                },
                indent=2,
            )
            + "\n",
        )
        self._write(
            "config/skill-keyword-index.json",
            json.dumps(
                {
                    "skills": {
                        "clean-skill": {"keywords": ["governed workflow", "shared token"]},
                        "partial-skill": {"keywords": ["shared token"]},
                    }
                },
                indent=2,
            )
            + "\n",
        )
        self._write(
            "config/skill-routing-rules.json",
            json.dumps(
                {
                    "skills": {
                        "clean-skill": {"task_allow": ["planning"]},
                    }
                },
                indent=2,
            )
            + "\n",
        )

        self._write_skill(
            "clean-skill",
            "Neutral guidance for a governed routed skill.",
            "Use this skill when the request explicitly asks for this workflow or when the router selects it.",
        )
        self._write_skill(
            "partial-skill",
            "Focused helper for a narrower scenario.",
            "Recommended when the request mentions the helper explicitly or when a reviewer selects it.",
        )

    def _run_gate(self, *, write_artifacts: bool = False) -> subprocess.CompletedProcess[str]:
        command = [
            self.powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(self.root / "scripts" / "verify" / "vibe-built-in-skill-governance-gate.ps1"),
        ]
        if write_artifacts:
            command.append("-WriteArtifacts")
        try:
            return subprocess.run(command, cwd=self.root, capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired as exc:
            raise AssertionError(
                f"PowerShell governance gate timed out after 120s: {command}\nstdout:\n{exc.stdout or ''}\nstderr:\n{exc.stderr or ''}"
            ) from exc

    def test_gate_passes_for_neutral_built_in_skill_wording(self) -> None:
        result = self._run_gate()
        self.assertEqual(0, result.returncode, msg=result.stdout + result.stderr)
        self.assertIn("bundled built-in skills do not claim autonomous activation", result.stdout)

    def test_gate_fails_when_built_in_skill_claims_auto_activation(self) -> None:
        self._write_skill(
            "rogue-skill",
            "Auto-activating helper for anything that looks related.",
            "This skill auto-activates when the user says almost anything about reports.",
        )

        result = self._run_gate()
        self.assertNotEqual(0, result.returncode)
        self.assertIn("bundled built-in skills do not claim autonomous activation", result.stdout)
        self.assertIn("FAIL", result.stdout)

    def test_gate_fails_when_built_in_skill_claims_self_dispatch(self) -> None:
        self._write_skill(
            "rogue-self-dispatch",
            "Self-dispatching helper for anything that looks related.",
            "This skill self-dispatches whenever the user hints at dashboard work.",
        )

        result = self._run_gate()
        self.assertNotEqual(0, result.returncode)
        self.assertIn("bundled built-in skills do not claim autonomous activation", result.stdout)
        self.assertIn("FAIL", result.stdout)

    def test_gate_writes_audit_artifact_with_routing_coverage_and_keyword_collisions(self) -> None:
        result = self._run_gate(write_artifacts=True)
        self.assertEqual(0, result.returncode, msg=result.stdout + result.stderr)

        artifact = json.loads(
            (self.root / "outputs" / "verify" / "vibe-built-in-skill-governance-gate.json").read_text(encoding="utf-8")
        )

        self.assertEqual("PASS", artifact["gate_result"])
        self.assertEqual(2, artifact["summary"]["bundled_skill_count"])
        self.assertEqual(1, artifact["summary"]["full_routing_count"])
        self.assertEqual(1, artifact["summary"]["partial_routing_count"])
        self.assertEqual(0, artifact["summary"]["none_routing_count"])
        self.assertEqual(1, artifact["summary"]["keyword_collision_count"])
        self.assertEqual("shared token", artifact["keyword_collisions"][0]["keyword"])


if __name__ == "__main__":
    unittest.main()
