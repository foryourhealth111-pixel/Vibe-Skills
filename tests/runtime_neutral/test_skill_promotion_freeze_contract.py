from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
FREEZE_SCRIPT = REPO_ROOT / "scripts" / "runtime" / "Freeze-RuntimeInputPacket.ps1"
HELPER_SCRIPT = REPO_ROOT / "scripts" / "common" / "vibe-governance-helpers.ps1"
RUNTIME_COMMON = REPO_ROOT / "scripts" / "runtime" / "VibeRuntime.Common.ps1"
ML_PROMPT = (
    "Build a scikit-learn tabular classification baseline, "
    "run feature selection, and compare cross-validation metrics."
)


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


def freeze_runtime_packet(task: str, artifact_root: Path) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    run_id = "pytest-freeze-" + uuid.uuid4().hex[:10]
    completed = subprocess.run(
        [
            shell,
            "-NoLogo",
            "-NoProfile",
            "-Command",
            (
                "& { "
                f"$result = & '{FREEZE_SCRIPT}' "
                f"-Task '{task}' "
                "-Mode interactive_governed "
                f"-RunId '{run_id}' "
                f"-ArtifactRoot '{artifact_root}'; "
                "$result | ConvertTo-Json -Depth 20 }"
            ),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
        env=dict(os.environ),
    )
    return json.loads(completed.stdout)


def load_json(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def as_list(value: object) -> list[object]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def run_powershell_json(script_body: str) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    completed = subprocess.run(
        [
            shell,
            "-NoLogo",
            "-NoProfile",
            "-Command",
            f"& {{ . '{RUNTIME_COMMON}'; {script_body} }}",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return json.loads(completed.stdout)


def extract_split_specialist_dispatch_function() -> str:
    content = FREEZE_SCRIPT.read_text(encoding="utf-8")
    match = re.search(
        r"(function Split-VibeSpecialistDispatch \{.*?^\})\s*^\$runtime =",
        content,
        re.DOTALL | re.MULTILINE,
    )
    if not match:
        raise AssertionError("Unable to locate Split-VibeSpecialistDispatch in Freeze-RuntimeInputPacket.ps1")
    return match.group(1)


class SkillPromotionFreezeContractTests(unittest.TestCase):
    def test_runtime_input_policy_allows_no_specialist_decision_and_keeps_advisory_fallbacks(self) -> None:
        policy = load_json(REPO_ROOT / "config" / "runtime-input-packet-policy.json")

        self.assertEqual(0, int(policy["required_specialist_recommendation_count"]))
        self.assertTrue(bool(policy["require_specialist_decision_evidence"]))
        self.assertGreater(float(policy["minimum_specialist_recommendation_confidence"]), 0.0)
        self.assertFalse(bool(policy["include_stage_assistant_recommendations"]))
        fallback_by_task_type = policy["fallback_specialists_by_task_type"]
        for task_type in ("planning", "debug", "research", "coding", "review", "default"):
            with self.subTest(task_type=task_type):
                self.assertIn(task_type, fallback_by_task_type)
        for task_type in ("debug", "coding", "review"):
            with self.subTest(task_type=task_type):
                self.assertGreaterEqual(len(as_list(fallback_by_task_type[task_type])), 1)

    def test_eligible_matched_skill_is_approved_and_not_ghosted(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = freeze_runtime_packet(ML_PROMPT, Path(tempdir))
            packet = load_json(payload["packet_path"])
            selected = as_list(packet["skill_routing"]["selected"])
            selected_ids = [item["skill_id"] for item in selected]
            decision = packet["specialist_decision"]

            self.assertIn("scikit-learn", selected_ids)
            self.assertIn("scikit-learn", as_list(decision["matched_skill_ids"]))
            self.assertIn("scikit-learn", as_list(decision["approved_dispatch_skill_ids"]))
            self.assertGreaterEqual(len(as_list(decision["surfaced_skill_ids"])), len(as_list(decision["matched_skill_ids"])))

            scikit_dispatch = next(item for item in selected if item["skill_id"] == "scikit-learn")
            self.assertIsNotNone(
                scikit_dispatch["native_skill_entrypoint"],
                "scikit-learn dispatch should have native_skill_entrypoint populated before path checks",
            )
            self.assertTrue(Path(scikit_dispatch["native_skill_entrypoint"]).is_absolute())
            self.assertTrue(Path(scikit_dispatch["native_skill_entrypoint"]).exists())

    def test_freeze_records_explicit_states_for_all_surfaced_recommendations(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = freeze_runtime_packet(ML_PROMPT, Path(tempdir))
            packet = load_json(payload["packet_path"])

            routing_rows = (
                as_list(packet["skill_routing"]["candidates"])
                + as_list(packet["skill_routing"]["selected"])
                + as_list(packet["skill_routing"]["rejected"])
            )
            surfaced = {str(item["skill_id"]) for item in routing_rows if str(item["skill_id"])}
            states = {str(item["state"]) for item in routing_rows if str(item["skill_id"])}

            self.assertTrue(surfaced)
            self.assertTrue(states.issubset({"candidate", "selected", "rejected"}))

    def test_freeze_keeps_consultation_truth_out_of_execution_dispatch_surface(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = freeze_runtime_packet(ML_PROMPT, Path(tempdir))
            packet = load_json(payload["packet_path"])

            self.assertNotIn("specialist_consultation", packet)
            self.assertNotIn("legacy_skill_routing", packet)
            self.assertGreaterEqual(len(as_list(packet["skill_routing"]["candidates"])), 1)
            self.assertGreaterEqual(len(as_list(packet["skill_routing"]["selected"])), 1)

    def test_policy_can_allow_incomplete_contract_without_forced_freeze_degrade(self) -> None:
        split_function = extract_split_specialist_dispatch_function()
        payload = run_powershell_json(
            (
                "& { "
                f". '{HELPER_SCRIPT}'; "
                f"{split_function} "
                "$policy = [pscustomobject]@{ "
                "promotion_enabled = $true; "
                "default_mode = 'recall_first'; "
                "allow_auto_dispatch_when_non_destructive = $true; "
                "require_contract_complete = $false; "
                "destructive_prompt_patterns = [pscustomobject]@{}; "
                "degraded_fallback_rules = [pscustomobject]@{ missing_contract = 'explicit_degraded' } "
                "}; "
                "$recommendation = Get-VgoSkillPromotionMetadata "
                "-Prompt 'generic prompt' "
                "-SkillMdPath '' "
                "-Description '' "
                "-RequiredInputs @() "
                "-ExpectedOutputs @() "
                "-VerificationExpectation '' "
                "-PromotionPolicy $policy; "
                "$recommendation | Add-Member -NotePropertyName skill_id -NotePropertyValue 'demo-skill'; "
                "$dispatch = Split-VibeSpecialistDispatch -GovernanceScope 'root' -Recommendations @($recommendation); "
                "$dispatch | ConvertTo-Json -Depth 20 }"
            )
        )

        approved_dispatch = as_list(payload["approved_dispatch"])
        self.assertEqual(1, len(approved_dispatch))
        self.assertEqual("demo-skill", approved_dispatch[0]["skill_id"])
        self.assertEqual([], as_list(payload["degraded"]))
        outcome = next(item for item in as_list(payload["promotion_outcomes"]) if item["skill_id"] == "demo-skill")
        self.assertEqual("approved_dispatch", outcome["promotion_state"])

    def test_split_specialist_dispatch_accepts_partial_host_decision_without_optional_lists(self) -> None:
        split_function = extract_split_specialist_dispatch_function()
        payload = run_powershell_json(
            (
                "& { "
                f". '{HELPER_SCRIPT}'; "
                f"{split_function} "
                "$policy = [pscustomobject]@{ "
                "promotion_enabled = $true; "
                "default_mode = 'recall_first'; "
                "allow_auto_dispatch_when_non_destructive = $false; "
                "require_contract_complete = $true; "
                "destructive_prompt_patterns = [pscustomobject]@{}; "
                "degraded_fallback_rules = [pscustomobject]@{ missing_contract = 'explicit_degraded' } "
                "}; "
                "$recommendation = Get-VgoSkillPromotionMetadata "
                "-Prompt 'generic prompt' "
                "-SkillMdPath '/tmp/skill.md' "
                "-SkillRoot '/tmp' "
                "-Description 'desc' "
                "-RequiredInputs @('input') "
                "-ExpectedOutputs @('output') "
                "-VerificationExpectation 'verify' "
                "-PromotionPolicy $policy; "
                "$recommendation | Add-Member -NotePropertyName skill_id -NotePropertyValue 'demo-skill'; "
                "$hostDecision = [pscustomobject]@{ selection_mode = 'curated_only' }; "
                "$dispatch = Split-VibeSpecialistDispatch "
                "-GovernanceScope 'root' "
                "-Recommendations @($recommendation) "
                "-HostSpecialistDispatchDecision $hostDecision; "
                "$dispatch | ConvertTo-Json -Depth 20 }"
            )
        )

        self.assertEqual([], as_list(payload["approved_dispatch"]))
        self.assertEqual(["demo-skill"], [item["skill_id"] for item in as_list(payload["local_specialist_suggestions"])])
        self.assertFalse(payload["escalation_required"])
        self.assertEqual("not_required", payload["escalation_status"])

    def test_surface_only_recommendation_is_not_auto_approved_in_root_scope(self) -> None:
        split_function = extract_split_specialist_dispatch_function()
        payload = run_powershell_json(
            (
                "& { "
                f". '{HELPER_SCRIPT}'; "
                f"{split_function} "
                "$policy = [pscustomobject]@{ "
                "promotion_enabled = $true; "
                "default_mode = 'recall_first'; "
                "allow_auto_dispatch_when_non_destructive = $false; "
                "require_contract_complete = $true; "
                "destructive_prompt_patterns = [pscustomobject]@{}; "
                "degraded_fallback_rules = [pscustomobject]@{ missing_contract = 'explicit_degraded' } "
                "}; "
                "$recommendation = Get-VgoSkillPromotionMetadata "
                "-Prompt 'generic prompt' "
                "-SkillMdPath '/tmp/skill.md' "
                "-SkillRoot '/tmp' "
                "-Description 'desc' "
                "-RequiredInputs @('input') "
                "-ExpectedOutputs @('output') "
                "-VerificationExpectation 'verify' "
                "-PromotionPolicy $policy; "
                "$recommendation | Add-Member -NotePropertyName skill_id -NotePropertyValue 'demo-skill'; "
                "$dispatch = Split-VibeSpecialistDispatch -GovernanceScope 'root' -Recommendations @($recommendation); "
                "$dispatch | ConvertTo-Json -Depth 20 }"
            )
        )

        self.assertEqual([], as_list(payload["approved_dispatch"]))
        self.assertEqual(["demo-skill"], [item["skill_id"] for item in as_list(payload["local_specialist_suggestions"])])
        outcome = next(item for item in as_list(payload["promotion_outcomes"]) if item["skill_id"] == "demo-skill")
        self.assertEqual("local_suggestion", outcome["promotion_state"])
        self.assertEqual("surface_only", outcome["recommended_promotion_action"])
