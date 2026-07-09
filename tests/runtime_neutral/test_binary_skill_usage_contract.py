from __future__ import annotations

import hashlib
import json
import os
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
        [shell, "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
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
    def test_claude_code_local_authority_accepts_explicit_shared_root_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            target_root = root / "home" / ".agents"
            skill_dir = target_root / "skills" / "feature-planning"
            skill_dir.mkdir(parents=True)
            skill_path = skill_dir / "SKILL.md"
            skill_path.write_text("# Feature Planning\n", encoding="utf-8", newline="\n")

            payload = run_ps_json(
                "& { "
                f". {ps_quote(str(RUNTIME_COMMON))}; "
                f". {ps_quote(str(SKILL_USAGE_COMMON))}; "
                f"$authority = Resolve-VibeLocalSkillAuthority -RepoRoot {ps_quote(str(REPO_ROOT))} -SkillId 'feature-planning' -NativeSkillEntrypoint {ps_quote(str(skill_path))} -TargetRoot {ps_quote(str(target_root))} -HostId 'claude-code' -RequireProvidedEntrypoint; "
                "$authority | ConvertTo-Json -Depth 20 "
                "}"
            )

            self.assertTrue(payload["valid"])
            self.assertEqual("ok", payload["reason"])
            self.assertEqual(str(skill_path.resolve()), payload["canonical_entrypoint"])
            self.assertEqual(str((target_root / "skills").resolve()), payload["source_root"])

    def test_local_authority_allows_retired_wrapper_name_when_it_is_a_real_local_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            target_root = root / "home" / ".agents"
            skill_dir = target_root / "skills" / "vibe-upgrade"
            skill_dir.mkdir(parents=True)
            skill_path = skill_dir / "SKILL.md"
            skill_path.write_text(
                "---\nname: vibe-upgrade\ndescription: Reused local helper.\n---\n# Reused local helper\n",
                encoding="utf-8",
                newline="\n",
            )

            payload = run_ps_json(
                "& { "
                f". {ps_quote(str(RUNTIME_COMMON))}; "
                f". {ps_quote(str(SKILL_USAGE_COMMON))}; "
                f"$authority = Resolve-VibeLocalSkillAuthority -RepoRoot {ps_quote(str(REPO_ROOT))} -SkillId 'vibe-upgrade' -NativeSkillEntrypoint {ps_quote(str(skill_path))} -TargetRoot {ps_quote(str(target_root))} -HostId 'codex' -RequireProvidedEntrypoint; "
                "$authority | ConvertTo-Json -Depth 20 "
                "}"
            )

            self.assertTrue(payload["valid"])
            self.assertEqual("ok", payload["reason"])
            self.assertEqual(str(skill_path.resolve()), payload["canonical_entrypoint"])

    def test_loaded_skill_record_keeps_real_descriptor_proof(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            target_root = root / "home" / ".agents"
            skill_dir = target_root / "skills" / "demo-skill"
            skill_dir.mkdir(parents=True)
            skill_text = "---\nname: demo-skill\ndescription: demo\n---\n# Demo\nUse the demo workflow.\n"
            skill_path = skill_dir / "SKILL.md"
            skill_path.write_text(skill_text, encoding="utf-8", newline="\n")
            expected_hash = hashlib.sha256(skill_text.encode("utf-8")).hexdigest()

            payload = run_ps_json(
                "& { "
                f". {ps_quote(str(RUNTIME_COMMON))}; "
                f". {ps_quote(str(SKILL_USAGE_COMMON))}; "
                f"$record = New-VibeSkillUsageLoadedSkill -RepoRoot {ps_quote(str(REPO_ROOT))} -SkillId 'demo-skill' -LoadedAtStage 'skeleton_check' -TargetRoot {ps_quote(str(target_root))} -HostId 'codex'; "
                "$record | ConvertTo-Json -Depth 20 "
                "}"
            )

            self.assertEqual("demo-skill", payload["skill_id"])
            self.assertEqual("loaded_full_skill_md", payload["load_status"])
            self.assertEqual(str(skill_path.resolve()), payload["skill_md_path"])
            self.assertEqual(expected_hash, payload["skill_md_sha256"])
            self.assertEqual("skeleton_check", payload["loaded_at_stage"])
            self.assertGreater(int(payload["loaded_byte_count"]), 0)
            self.assertGreater(int(payload["loaded_line_count"]), 0)

    def test_artifact_impact_promotes_loaded_skill_to_used(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            target_root = root / "home" / ".agents"
            skill_dir = target_root / "skills" / "demo-skill"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("# Demo\nUse it.\n", encoding="utf-8", newline="\n")

            payload = run_ps_json(
                "& { "
                f". {ps_quote(str(RUNTIME_COMMON))}; "
                f". {ps_quote(str(SKILL_USAGE_COMMON))}; "
                f"$loaded = New-VibeSkillUsageLoadedSkill -RepoRoot {ps_quote(str(REPO_ROOT))} -SkillId 'demo-skill' -LoadedAtStage 'skeleton_check' -TargetRoot {ps_quote(str(target_root))} -HostId 'codex'; "
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
            self.assertEqual("xl_plan", used_rows[0]["evidence"][0]["stage"])
            self.assertEqual("xl_plan.md", payload["evidence"][0]["artifact_ref"])
            self.assertIn("loaded demo skill workflow", payload["evidence"][0]["impact_summary"])

    def test_runtime_freeze_records_selected_skill_as_loaded_but_not_yet_used(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            target_root = root / "home" / ".agents"
            skill_dir = target_root / "skills" / "biopython-fasta"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\nname: biopython-fasta\ndescription: Use biopython to parse FASTA and summarize sequence lengths.\n---\n# Biopython FASTA\n",
                encoding="utf-8",
                newline="\n",
            )
            artifact_root = Path(tempdir) / "artifacts"
            run_id = "pytest-binary-skill-usage-freeze"
            env = os.environ.copy()
            env["VCO_HOST_ID"] = "codex"
            env["VIBE_AGENTS_HOME"] = str(target_root)
            command = [
                shell,
                "-NoLogo",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
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
            subprocess.run(command, cwd=REPO_ROOT, env=env, capture_output=True, text=True, encoding="utf-8", check=True)

            packet_path = next(artifact_root.rglob("runtime-input-packet.json"))
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            selected_skill = packet["work_binding"]["units"][0]["bound_skill"]
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
            self.assertNotIn("legacy_skill_routing", packet)
            self.assertNotIn("stage_assistant_hints", packet)


if __name__ == "__main__":
    unittest.main()
