from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = REPO_ROOT / "config" / "runtime-input-packet-policy.json"
RUNTIME_COMMON = REPO_ROOT / "scripts" / "runtime" / "VibeRuntime.Common.ps1"
FREEZE_SCRIPT = REPO_ROOT / "scripts" / "runtime" / "Freeze-RuntimeInputPacket.ps1"
PLAN_EXECUTE = REPO_ROOT / "scripts" / "runtime" / "Invoke-PlanExecute.ps1"
WRITE_REQUIREMENT_DOC = REPO_ROOT / "scripts" / "runtime" / "Write-RequirementDoc.ps1"
WRITE_XL_PLAN = REPO_ROOT / "scripts" / "runtime" / "Write-XlPlan.ps1"
CURRENT_FIELD_DOC = REPO_ROOT / "docs" / "governance" / "current-runtime-field-contract.md"
ENTRY_PROTOCOL_FILES = [
    REPO_ROOT / "SKILL.md",
    REPO_ROOT / "protocols" / "runtime.md",
    REPO_ROOT / "protocols" / "team.md",
]
CURRENT_USER_VISIBLE_RUNTIME_FILES = [
    WRITE_REQUIREMENT_DOC,
    WRITE_XL_PLAN,
    PLAN_EXECUTE,
    REPO_ROOT / "scripts" / "verify" / "vibe-governed-runtime-contract-gate.ps1",
    REPO_ROOT / "scripts" / "verify" / "vibe-runtime-execution-proof-gate.ps1",
]
RUNTIME_EXECUTION_PROOF_GATE = REPO_ROOT / "scripts" / "verify" / "vibe-runtime-execution-proof-gate.ps1"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class CurrentRoutingVocabularyFinalCleanupTests(unittest.TestCase):
    def test_policy_uses_current_skill_execution_contract_fields(self) -> None:
        policy = json.loads(read(POLICY_PATH))
        required_fields = set(policy["required_fields"])

        self.assertIn("skill_routing", required_fields)
        self.assertIn("skill_usage", required_fields)
        self.assertNotIn("specialist_dispatch", required_fields)
        self.assertNotIn("specialist_recommendations", required_fields)

        self.assertIn("skill_execution_contract", policy)
        self.assertIn("host_skill_execution_contract", policy)
        self.assertIn("interactive_skill_execution_disclosure", policy)
        self.assertNotIn("specialist_dispatch_contract", policy)
        self.assertNotIn("host_specialist_dispatch_contract", policy)
        self.assertNotIn("interactive_specialist_disclosure", policy)

        disclosure = policy["interactive_skill_execution_disclosure"]
        self.assertEqual("selected_skill_execution_only", disclosure["scope"])
        self.assertEqual("Pre-execution skill disclosure:", disclosure["header"])

    def test_current_runtime_projection_helper_has_current_name_and_no_root_dispatch_fallback(self) -> None:
        text = read(RUNTIME_COMMON)

        self.assertIn("function Get-VibeRuntimeSelectedSkillExecutionProjection", text)
        self.assertNotIn("function Get-VibeRuntimeSpecialistDispatchProjection", text)
        self.assertNotIn("RuntimeInputPacket.specialist_dispatch", text)
        self.assertNotIn("PropertyName 'specialist_dispatch'", text)

        helper_body = text.split("function Get-VibeRuntimeSelectedSkillExecutionProjection", 1)[1].split(
            "function Get-VibeRuntimeSpecialistRecommendations",
            1,
        )[0]
        for field in [
            "selected_skill_execution",
            "blocked_skill_execution",
            "degraded_skill_execution",
            "selected_skill_ids",
            "blocked_skill_ids",
            "degraded_skill_ids",
            "source = 'skill_routing.selected'",
        ]:
            self.assertIn(field, helper_body)
        for field in [
            "approved_dispatch",
            "local_specialist_suggestions",
            "approved_skill_ids",
        ]:
            self.assertNotIn(field, helper_body)

    def test_active_policy_readers_use_current_contract_names(self) -> None:
        freeze_text = read(FREEZE_SCRIPT)
        self.assertIn("skill_execution_contract", freeze_text)
        self.assertNotIn("specialist_dispatch_contract", freeze_text)

        runtime_text = read(RUNTIME_COMMON)
        self.assertIn("host_skill_execution_contract", runtime_text)
        self.assertIn("interactive_skill_execution_disclosure", runtime_text)
        self.assertNotIn("host_specialist_dispatch_contract", runtime_text)
        self.assertNotIn("interactive_specialist_disclosure", runtime_text)

    def test_generated_current_artifacts_do_not_use_dispatch_headings_or_counts(self) -> None:
        combined = "\n".join(
            [
                read(WRITE_REQUIREMENT_DOC),
                read(WRITE_XL_PLAN),
                read(PLAN_EXECUTE),
            ]
        )

        self.assertIn("Host Skill Execution Decision", combined)
        self.assertIn("selected_skill_execution_count", combined)
        self.assertNotIn("Host Specialist Dispatch Decision", combined)
        self.assertNotIn("approved_specialist_dispatch_count", combined)
        self.assertNotRegex(combined, r"(?m)^\s*dispatch_unit_count\s*=")

    def test_current_user_visible_surfaces_use_skill_execution_wording(self) -> None:
        combined = "\n".join(read(path) for path in ENTRY_PROTOCOL_FILES + CURRENT_USER_VISIBLE_RUNTIME_FILES)

        for forbidden in [
            "## Specialist Dispatch",
            "## Native Specialist Dispatch",
            "## Specialist Decision",
            "## Specialist Decision Plan",
            "## Specialist Skill Dispatch Plan",
            "## Specialist Dispatch Audit",
            "specialist dispatch section",
            "specialist dispatch integrity proof",
            "specialist dispatch accounting",
            "fallback specialist dispatch",
        ]:
            self.assertNotIn(forbidden, combined)

        for required in [
            "Skill Execution",
            "Skill Execution Decision",
            "Selected Skill Execution Plan",
            "selected_skill_execution",
        ]:
            self.assertIn(required, combined)

    def test_current_runtime_field_doc_uses_selected_skill_execution_anchor(self) -> None:
        text = read(CURRENT_FIELD_DOC)
        current_section = text.split("## Retired Layer", 1)[0]

        self.assertIn("selected_skill_execution", current_section)
        self.assertIn("skill_execution_units", current_section)
        self.assertIn("execution_skill_outcomes", current_section)
        self.assertNotIn("approved_skill_execution", current_section)
        self.assertNotIn("specialist_dispatch as root routing packet field", current_section)

    def test_runtime_execution_proof_gate_reads_current_skill_execution_counts(self) -> None:
        text = read(RUNTIME_EXECUTION_PROOF_GATE)

        self.assertIn("executeReceipt.skill_execution_unit_count", text)
        self.assertIn("executionManifest.specialist_accounting.skill_execution_unit_count", text)
        self.assertIn("proofManifest.skill_execution_unit_count", text)
        self.assertNotIn("executeReceipt.specialist_dispatch_unit_count", text)
        self.assertNotIn("executionManifest.specialist_accounting.dispatch_unit_count", text)
        self.assertNotIn("proofManifest.specialist_dispatch_unit_count", text)


if __name__ == "__main__":
    unittest.main()
