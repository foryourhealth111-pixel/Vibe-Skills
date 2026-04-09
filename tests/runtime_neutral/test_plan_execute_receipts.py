from __future__ import annotations

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


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


def extract_powershell_function(script_path: Path, function_name: str) -> str:
    text = script_path.read_text(encoding="utf-8")
    match = re.search(rf"function\s+{re.escape(function_name)}\s*\{{", text)
    if match is None:
        raise AssertionError(f"Function {function_name} not found in {script_path}")

    start = match.start()
    index = match.end() - 1
    depth = 0
    while index < len(text):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                index += 1
                break
        index += 1
    return text[start:index]


class PlanExecuteReceiptTests(unittest.TestCase):
    def test_native_specialist_prompt_references_declared_entrypoint_rule(self) -> None:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell not available")

        common_path = REPO_ROOT / "scripts" / "runtime" / "VibeExecution.Common.ps1"
        function_body = extract_powershell_function(common_path, "New-VibeNativeSpecialistPrompt")

        ps_script = (
            "& { "
            f". '{common_path}'; "
            f"{function_body} "
            "$dispatch = [pscustomobject]@{ "
            "skill_id = 'systematic-debugging'; "
            "bounded_role = 'specialist_assist'; "
            "native_skill_entrypoint = '/tmp/demo/SKILL.runtime-mirror.md'; "
            "skill_root = '/tmp/demo'; "
            "visibility_class = 'path_resolved'; "
            "native_usage_required = $true; "
            "usage_required = $true; "
            "must_preserve_workflow = $true; "
            "required_inputs = @('input'); "
            "expected_outputs = @('output'); "
            "verification_expectation = 'verify'; "
            "progressive_load_policy = @('Open the specialist /tmp/demo/SKILL.runtime-mirror.md entrypoint first.') "
            "}; "
            "$prompt = New-VibeNativeSpecialistPrompt "
            "-Dispatch $dispatch "
            "-RequirementDocPath 'req.md' "
            "-ExecutionPlanPath 'plan.md' "
            "-GovernanceScope 'root' "
            "-WriteScope 'scope' "
            "-RunId 'run-1'; "
            "$prompt }"
        )

        completed = subprocess.run(
            [powershell, "-NoLogo", "-NoProfile", "-Command", ps_script],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )

        prompt = completed.stdout
        self.assertIn(
            "- Open the declared native_skill_entrypoint before doing bounded specialist work.",
            prompt,
        )
        self.assertNotIn("- Open the specialist SKILL.md entrypoint before doing bounded specialist work.", prompt)

    def test_convert_to_vibe_executed_unit_receipt_preserves_prompt_injection_fields(self) -> None:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell not available")

        helper_path = REPO_ROOT / "scripts" / "runtime" / "VibeRuntime.Common.ps1"
        common_path = REPO_ROOT / "scripts" / "runtime" / "VibeExecution.Common.ps1"
        script_path = REPO_ROOT / "scripts" / "runtime" / "Invoke-PlanExecute.ps1"
        function_body = extract_powershell_function(script_path, "ConvertTo-VibeExecutedUnitReceipt")

        ps_script = (
            "& { "
            f". '{helper_path}'; "
            f". '{common_path}'; "
            f"{function_body} "
            "$outcome = [pscustomobject]@{ "
            "lane_id = 'lane-1'; "
            "lane_entry = [pscustomobject]@{ "
            "lane_kind = 'specialist_dispatch'; "
            "source_unit_id = 'unit-1'; "
            "write_scope = 'read_only'; "
            "dispatch = [pscustomobject]@{ "
            "skill_id = 'systematic-debugging'; "
            "dispatch_phase = 'plan_execute'; "
            "binding_profile = 'native'; "
            "lane_policy = 'bounded_native' "
            "} "
            "}; "
            "lane_result = [pscustomobject]@{ "
            "unit_id = 'unit-1'; "
            "status = 'degraded_non_authoritative'; "
            "exit_code = 0; "
            "timed_out = $false; "
            "verification_passed = $false; "
            "execution_driver = 'codex-cli'; "
            "live_native_execution = $false; "
            "degraded = $true; "
            "prompt_path = 'prompt.md'; "
            "prompt_injection_complete = $false; "
            "missing_prompt_injection_fields = @('skill_root', 'usage_required') "
            "}; "
            "lane_result_path = 'result.json'; "
            "lane_receipt_path = 'receipt.json' "
            "}; "
            "$receipt = ConvertTo-VibeExecutedUnitReceipt -WaveId 'wave-1' -StepId 'step-1' -Outcome $outcome; "
            "$receipt | ConvertTo-Json -Depth 10 }"
        )

        completed = subprocess.run(
            [powershell, "-NoLogo", "-NoProfile", "-Command", ps_script],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )

        receipt = json.loads(completed.stdout)
        self.assertEqual("prompt.md", receipt["prompt_path"])
        self.assertFalse(receipt["prompt_injection_complete"])
        self.assertEqual(["skill_root", "usage_required"], receipt["missing_prompt_injection_fields"])

    def test_specialist_summary_preserves_prompt_injection_fields(self) -> None:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell not available")

        common_path = REPO_ROOT / "scripts" / "runtime" / "VibeExecution.Common.ps1"

        ps_script = (
            "& { "
            f". '{common_path}'; "
            "$unitReceipt = [pscustomobject]@{ "
            "unit_id = 'unit-1'; "
            "skill_id = 'systematic-debugging'; "
            "dispatch_phase = 'plan_execute'; "
            "binding_profile = 'native'; "
            "lane_policy = 'bounded_native'; "
            "result_path = 'result.json'; "
            "verification_passed = $false; "
            "execution_driver = 'codex-cli'; "
            "live_native_execution = $false; "
            "degraded = $true; "
            "prompt_path = 'prompt.md'; "
            "prompt_injection_complete = $false; "
            "missing_prompt_injection_fields = @('skill_root', 'usage_required'); "
            "lane_receipt_path = 'receipt.json' "
            "}; "
            "$laneEntry = [pscustomobject]@{ parallelizable = $true }; "
            "$summary = New-VibeExecutedSpecialistUnitSummary -UnitReceipt $unitReceipt -LaneEntry $laneEntry; "
            "$summary | ConvertTo-Json -Depth 10 }"
        )

        completed = subprocess.run(
            [powershell, "-NoLogo", "-NoProfile", "-Command", ps_script],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )

        summary = json.loads(completed.stdout)
        self.assertEqual("prompt.md", summary["prompt_path"])
        self.assertFalse(summary["prompt_injection_complete"])
        self.assertEqual(["skill_root", "usage_required"], summary["missing_prompt_injection_fields"])
        self.assertTrue(summary["parallelizable"])

    def test_degraded_specialist_without_prompt_does_not_claim_prompt_injection_complete(self) -> None:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell not available")

        common_path = REPO_ROOT / "scripts" / "runtime" / "VibeExecution.Common.ps1"

        ps_script = (
            "& { "
            f". '{common_path}'; "
            "$policy = [pscustomobject]@{ "
            "degrade_contract = [pscustomobject]@{ status = 'degraded_non_authoritative'; verification_passed = $false; execution_driver = 'degraded_contract' ; hazard_alert = 'alert' } "
            "}; "
            "$dispatch = [pscustomobject]@{ "
            "skill_id = 'systematic-debugging'; "
            "bounded_role = 'specialist_assist'; "
            "native_usage_required = $true; "
            "usage_required = $true; "
            "must_preserve_workflow = $true "
            "}; "
            "$result = New-VibeDegradedSpecialistDispatchResult -UnitId 'unit-1' -Dispatch $dispatch -SessionRoot ([System.IO.Path]::GetTempPath()) -Policy $policy -Reason 'adapter_unavailable'; "
            "$result.result | ConvertTo-Json -Depth 10 }"
        )

        completed = subprocess.run(
            [powershell, "-NoLogo", "-NoProfile", "-Command", ps_script],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )

        result = json.loads(completed.stdout)
        self.assertIsNone(result["prompt_path"])
        self.assertFalse(result["prompt_injection_complete"])
        self.assertEqual([], result["missing_prompt_injection_fields"])


if __name__ == "__main__":
    unittest.main()
