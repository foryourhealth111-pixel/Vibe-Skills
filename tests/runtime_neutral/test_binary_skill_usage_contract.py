from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_COMMON = REPO_ROOT / "scripts" / "runtime" / "VibeRuntime.Common.ps1"
SKILL_USAGE_COMMON = REPO_ROOT / "scripts" / "runtime" / "VibeSkillUsage.Common.ps1"


def resolve_powershell() -> str | None:
    candidates = [
        shutil.which("pwsh"),
        shutil.which("pwsh.exe"),
        r"C:\Program Files\PowerShell\7\pwsh.exe",
        shutil.which("powershell"),
        shutil.which("powershell.exe"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))
    return None


def ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def run_ps_json(script: str) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available")
    result = subprocess.run(
        [shell, "-NoLogo", "-NoProfile", "-Command", script],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return json.loads(result.stdout)


def as_list(value: object) -> list[object]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


class BinarySkillUsageContractTests(unittest.TestCase):
    def test_full_skill_load_records_hash_path_line_and_byte_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            skill_dir = root / "bundled" / "skills" / "demo-skill"
            skill_dir.mkdir(parents=True)
            skill_text = "---\nname: demo-skill\ndescription: demo\n---\n# Demo\nUse the demo workflow.\n"
            skill_path = skill_dir / "SKILL.md"
            skill_path.write_text(skill_text, encoding="utf-8", newline="\n")
            expected_hash = hashlib.sha256(skill_text.encode("utf-8")).hexdigest()

            payload = run_ps_json(
                "& { "
                f". {ps_quote(str(RUNTIME_COMMON))}; "
                f". {ps_quote(str(SKILL_USAGE_COMMON))}; "
                f"$record = New-VibeSkillUsageLoadedSkill -RepoRoot {ps_quote(str(root))} -SkillId 'demo-skill' -LoadedAtStage 'skeleton_check'; "
                "$record | ConvertTo-Json -Depth 20 "
                "}"
            )

            self.assertEqual("demo-skill", payload["skill_id"])
            self.assertEqual("loaded_full_skill_md", payload["load_status"])
            self.assertEqual(str(skill_path.resolve()), payload["skill_md_path"])
            self.assertEqual(expected_hash, payload["skill_md_sha256"])
            self.assertEqual("skeleton_check", payload["loaded_at_stage"])
            self.assertGreaterEqual(int(payload["loaded_byte_count"]), len(skill_text))
            self.assertEqual(6, int(payload["loaded_line_count"]))

    def test_artifact_impact_promotes_loaded_skill_to_used_and_removes_unused_reason(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            skill_dir = root / "bundled" / "skills" / "demo-skill"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("# Demo\nUse it.\n", encoding="utf-8", newline="\n")

            payload = run_ps_json(
                "& { "
                f". {ps_quote(str(RUNTIME_COMMON))}; "
                f". {ps_quote(str(SKILL_USAGE_COMMON))}; "
                f"$loaded = New-VibeSkillUsageLoadedSkill -RepoRoot {ps_quote(str(root))} -SkillId 'demo-skill' -LoadedAtStage 'skeleton_check'; "
                "$usage = New-VibeInitialSkillUsage -LoadedSkills @($loaded) -TouchedSkills @([pscustomobject]@{ skill_id = 'demo-skill'; reason = 'loaded_but_no_artifact_impact' }); "
                "$usage = Update-VibeSkillUsageArtifactImpact -SkillUsage $usage -SkillId 'demo-skill' -Stage 'xl_plan' -ArtifactRef 'xl_plan.md' -ImpactSummary 'Plan follows the loaded demo skill workflow.'; "
                "$usage | ConvertTo-Json -Depth 20 "
                "}"
            )

            self.assertEqual(["demo-skill"], payload["used_skills"])
            self.assertEqual([], payload["unused_skills"])
            used_rows = as_list(payload["used"])
            self.assertEqual(["demo-skill"], [item["skill_id"] for item in used_rows])
            self.assertEqual([], as_list(payload["unused"]))
            self.assertEqual("demo-skill", used_rows[0]["skill_id"])
            self.assertEqual("xl_plan", used_rows[0]["evidence"][0]["stage"])
            self.assertEqual("demo-skill", payload["evidence"][0]["skill_id"])
            self.assertEqual("xl_plan", payload["evidence"][0]["stage"])
            self.assertEqual("xl_plan.md", payload["evidence"][0]["artifact_ref"])
            self.assertIn("loaded demo skill workflow", payload["evidence"][0]["impact_summary"])

    def test_artifact_impact_can_update_after_empty_unused_json_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            skill_dir = root / "bundled" / "skills" / "demo-skill"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("# Demo\nUse it.\n", encoding="utf-8", newline="\n")

            payload = run_ps_json(
                "& { "
                f". {ps_quote(str(RUNTIME_COMMON))}; "
                f". {ps_quote(str(SKILL_USAGE_COMMON))}; "
                f"$loaded = New-VibeSkillUsageLoadedSkill -RepoRoot {ps_quote(str(root))} -SkillId 'demo-skill' -LoadedAtStage 'skeleton_check'; "
                "$usage = New-VibeInitialSkillUsage -LoadedSkills @($loaded) -TouchedSkills @([pscustomobject]@{ skill_id = 'demo-skill'; reason = 'loaded_but_no_artifact_impact' }); "
                "$usage = Update-VibeSkillUsageArtifactImpact -SkillUsage $usage -SkillId 'demo-skill' -Stage 'requirement_doc' -ArtifactRef 'requirement.md' -ImpactSummary 'Requirement uses the demo skill.'; "
                "$usage = ($usage | ConvertTo-Json -Depth 20 | ConvertFrom-Json); "
                "$usage = Update-VibeSkillUsageArtifactImpact -SkillUsage $usage -SkillId 'demo-skill' -Stage 'xl_plan' -ArtifactRef 'xl_plan.md' -ImpactSummary 'Plan keeps using the demo skill.'; "
                "$usage | ConvertTo-Json -Depth 20 "
                "}"
            )

            self.assertEqual(["demo-skill"], payload["used_skills"])
            self.assertEqual([], payload["unused_skills"])
            self.assertEqual([], as_list(payload["unused"]))
            stages = [item["stage"] for item in as_list(payload["evidence"])]
            self.assertEqual(["requirement_doc", "xl_plan"], stages)

    def test_runtime_freeze_emits_initial_binary_skill_usage(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir) / "artifacts"
            run_id = "pytest-binary-skill-usage-freeze"
            command = [
                shell,
                "-NoLogo",
                "-NoProfile",
                "-File",
                str(REPO_ROOT / "scripts" / "runtime" / "Freeze-RuntimeInputPacket.ps1"),
                "-Task",
                "Use biopython to parse FASTA and summarize sequence lengths.",
                "-Mode",
                "interactive_governed",
                "-RunId",
                run_id,
                "-ArtifactRoot",
                str(artifact_root),
            ]
            subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8", check=True)

            packet_path = next(artifact_root.rglob("runtime-input-packet.json"))
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            selected_skill = packet["route_snapshot"]["selected_skill"]
            usage = packet["skill_usage"]

            self.assertEqual("binary_used_unused", usage["state_model"])
            self.assertIn(selected_skill, [item["skill_id"] for item in usage["loaded_skills"]])
            selected_record = next(item for item in usage["loaded_skills"] if item["skill_id"] == selected_skill)
            self.assertEqual("loaded_full_skill_md", selected_record["load_status"])
            self.assertTrue(Path(selected_record["skill_md_path"]).exists())
            self.assertRegex(selected_record["skill_md_sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual([], usage["used_skills"])
            self.assertIn(selected_skill, usage["unused_skills"])
            self.assertIn(selected_skill, [item["skill_id"] for item in as_list(usage["unused"])])
            self.assertIn(
                "selected_but_no_artifact_impact",
                [item["reason"] for item in usage["unused_reasons"] if item["skill_id"] == selected_skill],
            )
            self.assertIn(
                "selected_but_no_artifact_impact",
                [item["reason"] for item in as_list(usage["unused"]) if item["skill_id"] == selected_skill],
            )
            self.assertNotIn("legacy_skill_routing", packet)
            self.assertNotIn("stage_assistant_hints", packet)


if __name__ == "__main__":
    unittest.main()
