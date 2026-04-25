from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
FREEZE_SCRIPT = REPO_ROOT / "scripts" / "runtime" / "Freeze-RuntimeInputPacket.ps1"
RUNTIME_SCRIPT = REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"


def resolve_powershell() -> str | None:
    candidates = [
        shutil.which("pwsh"),
        shutil.which("pwsh.exe"),
        r"C:\Program Files\PowerShell\7\pwsh.exe",
        r"C:\Program Files\PowerShell\7-preview\pwsh.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))
    return None


def ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def build_host_decision_json() -> str:
    return json.dumps(
        {
            "decision_kind": "approval_response",
            "decision_action": "approve_requirement",
            "continuation_context": {
                "structured_bounded_reentry": True,
                "source_run_id": "prior-run",
                "terminal_stage": "requirement_doc",
                "next_stage": "xl_plan",
                "prior_task": "research ECG public datasets for diagnosis tasks",
                "prior_task_type": "research",
                "prior_goal": "research ECG public datasets for diagnosis tasks",
                "prior_deliverable": "Chinese report and dataset table",
                "prior_constraints": ["public-only", "official-source-only"],
                "control_only_prompt": True,
            },
        },
        ensure_ascii=False,
    )


def run_freeze(*, artifact_root: Path, host_decision_json: str) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    run_id = "pytest-structured-reentry-freeze-" + uuid.uuid4().hex[:10]
    command = [
        shell,
        "-NoLogo",
        "-NoProfile",
        "-Command",
        (
            "& { "
            "$env:VCO_HOST_ID = 'codex'; "
            f"$result = & {ps_quote(str(FREEZE_SCRIPT))} "
            "-Task '批准' "
            "-Mode interactive_governed "
            f"-RunId {ps_quote(run_id)} "
            f"-ArtifactRoot {ps_quote(str(artifact_root))} "
            f"-HostDecisionJson {ps_quote(host_decision_json)}; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
        env={**os.environ, "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "1"},
    )
    return json.loads(completed.stdout)


def run_runtime(
    *,
    artifact_root: Path,
    host_decision_json: str,
    requested_stage_stop: str | None = None,
) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    run_id = "pytest-structured-reentry-runtime-" + uuid.uuid4().hex[:10]
    command = [
        shell,
        "-NoLogo",
        "-NoProfile",
        "-Command",
        (
            "& { "
            "$env:VCO_HOST_ID = 'codex'; "
            f"$result = & {ps_quote(str(RUNTIME_SCRIPT))} "
            "-Task '批准' "
            "-Mode interactive_governed "
            f"-RunId {ps_quote(run_id)} "
            f"{'-RequestedStageStop ' + ps_quote(requested_stage_stop) + ' ' if requested_stage_stop else ''}"
            f"-ArtifactRoot {ps_quote(str(artifact_root))} "
            f"-HostDecisionJson {ps_quote(host_decision_json)}; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
        env={**os.environ, "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "1"},
    )
    return json.loads(completed.stdout)


def run_common_script(script: str) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    command = [
        shell,
        "-NoLogo",
        "-NoProfile",
        "-Command",
        (
            "& { "
            f". {ps_quote(str(REPO_ROOT / 'scripts' / 'runtime' / 'VibeRuntime.Common.ps1'))}; "
            f"{script} "
            "}"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    return json.loads(completed.stdout)


class StructuredBoundedReentryContinuationTests(unittest.TestCase):
    def test_phase_decomposition_rejects_non_object_phase_records(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            raise unittest.SkipTest("PowerShell executable not available in PATH")

        command = [
            shell,
            "-NoLogo",
            "-NoProfile",
            "-Command",
            (
                "& { "
                f". {ps_quote(str(REPO_ROOT / 'scripts' / 'runtime' / 'VibeRuntime.Common.ps1'))}; "
                "try { "
                "$decision = [pscustomobject]@{ "
                "  phase_decomposition = [pscustomobject]@{ phases = @('oops') } "
                "}; "
                "Resolve-VibeHostPhaseDecomposition -HostDecision $decision -Task 'demo task' | Out-Null; "
                "@{ ok = $true } | ConvertTo-Json -Compress "
                "} catch { "
                "@{ ok = $false; error = $_.Exception.Message } | ConvertTo-Json -Compress "
                "} "
                "}"
            ),
        ]
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
        payload = json.loads(completed.stdout)

        self.assertFalse(payload["ok"])
        self.assertIn("each execution phase must be a JSON object", payload["error"])

    def test_phase_decomposition_accepts_hashtable_host_decision(self) -> None:
        payload = run_common_script(
            "$decision = @{ "
            "  phase_decomposition = @{ "
            "    phases = @(@{ "
            "      phase_id = 'dataset-search'; "
            "      stage_order = 10; "
            "      stage_type = 'discovery'; "
            "      stage_label = 'Dataset Search'; "
            "      goal = 'Find public datasets'; "
            "      acceptance_checks = @('official source verified') "
            "    }) "
            "  } "
            "}; "
            "$result = Resolve-VibeHostPhaseDecomposition -HostDecision $decision -Task 'find public datasets'; "
            "$result | ConvertTo-Json -Depth 20 -Compress"
        )

        self.assertEqual(1, payload["phase_count"])
        self.assertEqual("dataset-search", payload["phases"][0]["phase_id"])
        self.assertEqual("discovery", payload["phases"][0]["stage_type"])
        self.assertEqual(["official source verified"], payload["phases"][0]["acceptance_checks"])

    def test_specialist_dispatch_accepts_hashtable_host_decision(self) -> None:
        payload = run_common_script(
            "$hostDecision = @{ "
            "  specialist_dispatch_decision = @{ "
            "    selection_mode = 'curated_only'; "
            "    approved_skill_ids = @('research-lookup'); "
            "    deferred_skill_ids = @('latex-submission-pipeline'); "
            "    rejected_skill_ids = @() "
            "  } "
            "}; "
            "$recommendations = @("
            "  @{ skill_id = 'research-lookup' }, "
            "  @{ skill_id = 'latex-submission-pipeline' }"
            "); "
            "$result = Resolve-VibeHostSpecialistDispatchDecision "
            "-HostDecision $hostDecision "
            "-Recommendations $recommendations "
            "-GovernanceScope 'root' "
            "-Policy $null; "
            "$result | ConvertTo-Json -Depth 20 -Compress"
        )

        self.assertEqual("curated_only", payload["selection_mode"])
        self.assertEqual(["research-lookup"], payload["approved_skill_ids"])
        self.assertEqual(["latex-submission-pipeline"], payload["deferred_skill_ids"])
        self.assertEqual("current", payload["reconciliation_state"])

    def test_code_task_tdd_decision_accepts_hashtable_host_decision(self) -> None:
        payload = run_common_script(
            "$hostDecision = @{ "
            "  code_task_tdd_decision = @{ "
            "    mode = 'not_applicable'; "
            "    reason = 'Document artifact only.' "
            "  } "
            "}; "
            "$result = Get-VibeCodeTaskTddDecisionFromHostDecision -HostDecision $hostDecision; "
            "$result | ConvertTo-Json -Depth 20 -Compress"
        )

        self.assertEqual("not_applicable", payload["mode"])
        self.assertEqual("host_decision", payload["source"])
        self.assertEqual("Document artifact only.", payload["reason"])

    def test_execution_phase_metadata_preserves_hashtable_record_fields(self) -> None:
        payload = run_common_script(
            "$phaseDecomposition = [pscustomobject]@{ "
            "  phases = @([pscustomobject]@{ "
            "    phase_id = 'phase-discovery'; "
            "    stage_order = 10; "
            "    stage_type = 'discovery'; "
            "    stage_label = 'Discovery'; "
            "    dispatch_phase = 'pre_execution' "
            "  }) "
            "}; "
            "$records = @(@{ "
            "  skill_id = 'research-lookup'; "
            "  native_skill_entrypoint = '/tmp/research-lookup/SKILL.md'; "
            "  dispatch_phase = 'pre_execution'; "
            "  rationale = 'domain lookup needed' "
            "}); "
            "$result = Add-VibeExecutionPhaseMetadataToRecords -Records $records -PhaseDecomposition $phaseDecomposition; "
            "$result[0] | ConvertTo-Json -Depth 20 -Compress"
        )

        self.assertEqual("research-lookup", payload["skill_id"])
        self.assertEqual("/tmp/research-lookup/SKILL.md", payload["native_skill_entrypoint"])
        self.assertEqual("domain lookup needed", payload["rationale"])
        self.assertEqual("phase-discovery", payload["phase_id"])
        self.assertEqual("discovery", payload["stage_type"])

    def test_task_signal_matching_uses_explicit_stems_without_substring_false_positives(self) -> None:
        payload = run_common_script(
            "$result = [ordered]@{ "
            "  diagnose_type = Get-VibeInferredTaskType -Task 'Please diagnose routing behavior'; "
            "  suffix_type = Get-VibeInferredTaskType -Task 'suffix cleanup in docs'; "
            "  diagnose_stem_hit = Test-VibeTaskSignalHit -TaskLower 'please diagnose routing behavior' -Pattern 'diagnos*'; "
            "  suffix_fix_hit = Test-VibeTaskSignalHit -TaskLower 'suffix cleanup in docs' -Pattern 'fix'; "
            "  short_stem_hit = Test-VibeTaskSignalHit -TaskLower 'suffix cleanup in docs' -Pattern 'fix*' "
            "}; "
            "$result | ConvertTo-Json -Depth 20 -Compress"
        )

        self.assertEqual("debug", payload["diagnose_type"])
        self.assertEqual("planning", payload["suffix_type"])
        self.assertTrue(payload["diagnose_stem_hit"])
        self.assertFalse(payload["suffix_fix_hit"])
        self.assertFalse(payload["short_stem_hit"])

    def test_freeze_reuses_prior_task_type_for_control_only_structured_reentry(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir) / "artifacts"
            payload = run_freeze(
                artifact_root=artifact_root,
                host_decision_json=build_host_decision_json(),
            )
            packet = payload["packet"]

            self.assertEqual("research", packet["canonical_router"]["task_type"])
            self.assertIn("continuation_context", packet)
            self.assertTrue(packet["continuation_context"]["structured_bounded_reentry"])
            self.assertTrue(packet["continuation_context"]["control_only_prompt"])
            self.assertEqual("approval_response", packet["host_decision"]["decision_kind"])
            self.assertEqual("approve_requirement", packet["host_decision"]["decision_action"])

    def test_stale_host_specialist_dispatch_decision_is_safely_shrunk(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            raise unittest.SkipTest("PowerShell executable not available in PATH")

        command = [
            shell,
            "-NoLogo",
            "-NoProfile",
            "-Command",
            (
                "& { "
                f". {ps_quote(str(REPO_ROOT / 'scripts' / 'runtime' / 'VibeRuntime.Common.ps1'))}; "
                "$hostDecision = [pscustomobject]@{ specialist_dispatch_decision = [pscustomobject]@{ "
                "selection_mode = 'curated_only'; "
                "approved_skill_ids = @('old-skill'); "
                "deferred_skill_ids = @(); "
                "rejected_skill_ids = @() "
                "} }; "
                "$recommendations = @([pscustomobject]@{ skill_id = 'new-skill' }); "
                "$result = Resolve-VibeHostSpecialistDispatchDecision "
                "-HostDecision $hostDecision "
                "-Recommendations $recommendations "
                "-GovernanceScope 'root' "
                "-Policy $null; "
                "$result | ConvertTo-Json -Depth 20 "
                "}"
            ),
        ]
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
        payload = json.loads(completed.stdout)

        self.assertEqual([], payload["approved_skill_ids"])
        self.assertEqual(["old-skill"], payload["stale_skill_ids"])
        self.assertEqual("stale_recuration_required", payload["reconciliation_state"])
        self.assertTrue(payload["requires_recuration"])

    def test_runtime_skips_global_memory_reads_for_structured_bounded_reentry(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir) / "artifacts"
            payload = run_runtime(
                artifact_root=artifact_root,
                host_decision_json=build_host_decision_json(),
                requested_stage_stop=None,
            )
            summary = payload["summary"]
            report_path = Path(summary["artifacts"]["memory_activation_report"])
            report = json.loads(report_path.read_text(encoding="utf-8"))
            stages = {stage["stage"]: stage for stage in report["stages"]}

            self.assertEqual(1, len(stages["skeleton_check"]["read_actions"]))
            self.assertEqual("state_store", stages["skeleton_check"]["read_actions"][0]["owner"])
            self.assertEqual([], stages["deep_interview"]["read_actions"])
            self.assertEqual([], stages["xl_plan"]["read_actions"])


if __name__ == "__main__":
    unittest.main()
