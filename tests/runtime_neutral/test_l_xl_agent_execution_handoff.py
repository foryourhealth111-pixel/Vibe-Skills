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
IMPLEMENTATION_EXECUTION_TASK = (
    "Implement a bounded migration with explicit code changes, tests, and verification."
)
DEBUG_EXECUTION_TASK = (
    "I have a failing test and a stack trace. Help me debug systematically before proposing fixes."
)


def agent_skill_organization(
    skill_ids: list[str],
    *,
    workflow_level: str = "L",
) -> dict[str, object]:
    module_id = "primary_work"
    return {
        "schema_version": "agent_skill_organization_v1",
        "derived_by": "agent",
        "workflow_level": workflow_level,
        "modules": [
            {
                "module_id": module_id,
                "goal": "Complete the governed task through the declared execution path.",
                "candidate_skill_ids": skill_ids,
                "execution_mode": "skill_assigned" if skill_ids else "blocked_gap",
                "acceptance_criteria": [
                    {
                        "criterion_id": "primary-work-result",
                        "description": "The governed task result satisfies the frozen requirement.",
                        "verification_mode": "automated",
                    }
                ],
            }
        ],
        "selected_skills": [
            {
                "skill_id": skill_id,
                "module_ids": [module_id],
                "responsibility": f"Own the bounded {skill_id} work.",
                "reason": f"The Agent reviewed {skill_id}/SKILL.md and selected it for this module.",
            }
            for skill_id in skill_ids
        ],
        "uncovered_modules": []
        if skill_ids
        else [{"module_id": module_id, "reason": "No task skill is required for this runtime-only test."}],
        "workflow_level_contract": {
            "L": "Use one bounded serial lane.",
            "XL": "Use bounded parallel lanes with governed review.",
        },
    }


def dependency_and_scope_organization(workflow_level: str) -> dict[str, object]:
    module_specs = [
        ("module_a", "topology-a", [], "shared:result"),
        ("module_b", "topology-b", [], "module:b"),
        ("module_c", "topology-c", ["module_a"], "module:c"),
        ("module_d", "topology-d", ["module_a"], "module:c"),
    ]
    return {
        "schema_version": "agent_skill_organization_v1",
        "derived_by": "agent",
        "workflow_level": workflow_level,
        "modules": [
            {
                "module_id": module_id,
                "goal": f"Produce the governed result for {module_id}.",
                "candidate_skill_ids": [skill_id],
                "required": True,
                "depends_on": depends_on,
                "execution_mode": "skill_assigned",
                "acceptance_criteria": [
                    {
                        "criterion_id": f"{module_id}-result",
                        "description": f"The result for {module_id} exists.",
                        "verification_mode": "automated",
                    }
                ],
            }
            for module_id, skill_id, depends_on, _ in module_specs
        ],
        "selected_skills": [
            {
                "skill_id": skill_id,
                "module_ids": [module_id],
                "role": "owner",
                "responsibility": f"Own the bounded work for {module_id}.",
                "reason": f"The Agent selected {skill_id} after reading its SKILL.md.",
                "write_scope": write_scope,
            }
            for module_id, skill_id, _, write_scope in module_specs
        ],
        "uncovered_modules": [],
        "workflow_level_contract": {
            "L": "Run every module work unit serially.",
            "XL": "Parallelize only dependency-ready work with distinct write scopes.",
        },
    }


def mixed_write_scope_organization() -> dict[str, object]:
    organization = dependency_and_scope_organization("XL")
    organization["modules"] = organization["modules"][:3]
    organization["selected_skills"] = organization["selected_skills"][:3]
    organization["modules"][2]["depends_on"] = []
    organization["selected_skills"][0]["write_scope"] = "shared:result"
    organization["selected_skills"][1]["write_scope"] = "shared:result"
    organization["selected_skills"][2]["write_scope"] = "independent:result"
    return organization


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


def run_runtime(
    task: str,
    artifact_root: Path,
    *,
    mode: str = "interactive_governed",
    script_relative_path: str = "scripts/runtime/invoke-vibe-runtime.ps1",
    run_id: str | None = None,
    governance_scope: str = "root",
    root_run_id: str = "",
    parent_run_id: str = "",
    parent_unit_id: str = "",
    inherited_requirement_doc_path: Path | None = None,
    inherited_execution_plan_path: Path | None = None,
    entry_intent_id: str = "",
    requested_stage_stop: str = "",
    requested_grade_floor: str = "",
    agent_organization: dict[str, object] | None = None,
    extra_env: dict[str, str] | None = None,
) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    script_path = REPO_ROOT / script_relative_path
    effective_run_id = run_id or ("pytest-topology-" + uuid.uuid4().hex[:10])
    delegation_envelope_path: Path | None = None
    if (
        governance_scope == "child"
        and root_run_id
        and parent_run_id
        and parent_unit_id
        and inherited_requirement_doc_path is not None
        and inherited_execution_plan_path is not None
    ):
        delegation_envelope_path = write_delegation_envelope_fixture(
            artifact_root,
            child_run_id=effective_run_id,
            root_run_id=root_run_id,
            parent_run_id=parent_run_id,
            parent_unit_id=parent_unit_id,
            inherited_requirement_doc_path=inherited_requirement_doc_path,
            inherited_execution_plan_path=inherited_execution_plan_path,
        )
    inherited_requirement = (
        f"-InheritedRequirementDocPath '{inherited_requirement_doc_path}' "
        if inherited_requirement_doc_path
        else ""
    )
    inherited_plan = (
        f"-InheritedExecutionPlanPath '{inherited_execution_plan_path}' "
        if inherited_execution_plan_path
        else ""
    )
    root_segment = f"-RootRunId '{root_run_id}' " if root_run_id else ""
    parent_segment = f"-ParentRunId '{parent_run_id}' " if parent_run_id else ""
    parent_unit_segment = f"-ParentUnitId '{parent_unit_id}' " if parent_unit_id else ""
    delegation_segment = (
        f"-DelegationEnvelopePath '{delegation_envelope_path}' "
        if delegation_envelope_path is not None
        else ""
    )
    entry_intent_segment = f"-EntryIntentId '{entry_intent_id}' " if entry_intent_id else ""
    requested_stop_segment = f"-RequestedStageStop '{requested_stage_stop}' " if requested_stage_stop else ""
    requested_grade_segment = f"-RequestedGradeFloor '{requested_grade_floor}' " if requested_grade_floor else ""
    host_decision_segment = ""
    if agent_organization is not None:
        host_decision_json = json.dumps(
            {"agent_skill_organization": agent_organization},
            separators=(",", ":"),
        ).replace("'", "''")
        host_decision_segment = f"-HostDecisionJson '{host_decision_json}' "

    command = [
        shell,
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "& { "
            f"$result = & '{script_path}' "
            f"-Task '{task}' "
            f"-Mode {mode} "
            f"-GovernanceScope {governance_scope} "
            f"-RunId '{effective_run_id}' "
            f"{root_segment}"
            f"{parent_segment}"
            f"{parent_unit_segment}"
            f"{inherited_requirement}"
            f"{inherited_plan}"
            f"{delegation_segment}"
            f"{entry_intent_segment}"
            f"{requested_stop_segment}"
            f"{requested_grade_segment}"
            f"{host_decision_segment}"
            f"-ArtifactRoot '{artifact_root}'; "
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
        env={**os.environ, **(extra_env or {})},
    )
    stdout = completed.stdout.strip()
    if stdout in ("", "null"):
        raise AssertionError(
            "invoke-vibe-runtime returned null payload. "
            f"stderr={completed.stderr.strip()}"
        )
    return json.loads(stdout)


def write_installed_skill(target_root: Path, skill_id: str) -> Path:
    skill_path = target_root / "skills" / skill_id / "SKILL.md"
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text(
        (
            "---\n"
            f"name: {skill_id}\n"
            f"description: Installed {skill_id} test skill.\n"
            "---\n"
        ),
        encoding="utf-8",
    )
    return skill_path


def write_delegation_envelope_fixture(
    artifact_root: Path,
    *,
    child_run_id: str,
    root_run_id: str,
    parent_run_id: str,
    parent_unit_id: str,
    inherited_requirement_doc_path: Path,
    inherited_execution_plan_path: Path,
) -> Path:
    session_root = artifact_root / "outputs" / "runtime" / "vibe-sessions" / child_run_id
    session_root.mkdir(parents=True, exist_ok=True)
    envelope_path = session_root / "delegation-envelope.json"
    envelope = {
        "root_run_id": root_run_id,
        "parent_run_id": parent_run_id,
        "parent_unit_id": parent_unit_id,
        "child_run_id": child_run_id,
        "governance_scope": "child_governed",
        "requirement_doc_path": str(inherited_requirement_doc_path.resolve()),
        "execution_plan_path": str(inherited_execution_plan_path.resolve()),
        "write_scope": "pytest:child-lane",
        "review_mode": "module_acceptance",
        "prompt_tail_required": "$vibe",
        "allow_requirement_freeze": False,
        "allow_plan_freeze": False,
        "allow_root_completion_claim": False,
    }
    envelope_path.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
    return envelope_path


def run_write_xl_plan(
    task: str,
    artifact_root: Path,
    requirement_doc_path: Path,
    runtime_input_packet_path: Path | None = None,
    *,
    run_id: str | None = None,
) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    script_path = REPO_ROOT / "scripts" / "runtime" / "Write-XlPlan.ps1"
    effective_run_id = run_id or ("pytest-write-plan-" + uuid.uuid4().hex[:10])
    ps_command = (
        "& { "
        f"$result = & '{script_path}' "
        f"-Task '{task}' "
        "-Mode interactive_governed "
        f"-RunId '{effective_run_id}' "
        f"-RequirementDocPath '{requirement_doc_path}' "
        f"-ArtifactRoot '{artifact_root}' "
    )
    if runtime_input_packet_path is not None:
        ps_command += f"-RuntimeInputPacketPath '{runtime_input_packet_path}' "
    ps_command += "$result | ConvertTo-Json -Depth 20 }"
    command = [
        shell,
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        ps_command,
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    stdout = completed.stdout.strip()
    if stdout not in ("", "null"):
        return json.loads(stdout)

    receipt_path = artifact_root / "outputs" / "runtime" / "vibe-sessions" / effective_run_id / "execution-plan-receipt.json"
    if not receipt_path.exists():
        raise AssertionError(
            "Write-XlPlan returned null payload and did not emit a receipt. "
            f"stderr={completed.stderr.strip()}"
        )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    return {
        "execution_plan_path": receipt["execution_plan_path"],
        "module_work_plan_path": receipt["module_work_plan_path"],
        "receipt_path": str(receipt_path),
        "receipt": receipt,
    }


def run_plan_execute(
    task: str,
    artifact_root: Path,
    requirement_doc_path: Path,
    execution_plan_path: Path,
    runtime_input_packet_path: Path,
    *,
    module_work_plan_path: Path | None = None,
    extra_env: dict[str, str] | None = None,
) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    script_path = REPO_ROOT / "scripts" / "runtime" / "Invoke-PlanExecute.ps1"
    resolved_module_work_plan_path = module_work_plan_path or (
        runtime_input_packet_path.parent / "module-work-plan.json"
    )
    module_work_plan = load_json(resolved_module_work_plan_path)
    run_id = str(module_work_plan["source_run_id"])
    command = [
        shell,
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "& { "
            f"$result = & '{script_path}' "
            f"-Task '{task}' "
            "-Mode interactive_governed "
            f"-RunId '{run_id}' "
            f"-RequirementDocPath '{requirement_doc_path}' "
            f"-ExecutionPlanPath '{execution_plan_path}' "
            f"-ModuleWorkPlanPath '{resolved_module_work_plan_path}' "
            f"-RuntimeInputPacketPath '{runtime_input_packet_path}' "
            f"-ArtifactRoot '{artifact_root}'; "
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
        env={**os.environ, **(extra_env or {})},
    )
    return json.loads(completed.stdout)


def load_json(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def module_skill_assignments(runtime_input: dict[str, object]) -> list[dict[str, object]]:
    module_assignments = runtime_input.get("module_assignments") or {}
    units = module_assignments.get("units") if isinstance(module_assignments, dict) else []
    rows: list[dict[str, object]] = []
    for unit in list(units or []):
        if not isinstance(unit, dict):
            continue
        skill_id = str(unit.get("bound_skill") or "")
        if not skill_id:
            continue
        row = dict(unit)
        row["skill_id"] = skill_id
        rows.append(row)
    return rows


class GovernedPlanAndHandoffTests(unittest.TestCase):
    def test_public_vibe_defaults_to_requirement_confirmation_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(
                task="Implement the runtime hardening after confirming scope and plan.",
                artifact_root=Path(tempdir),
                governance_scope="root",
                entry_intent_id="vibe",
            )
            summary = payload["summary"]
            runtime_input = load_json(summary["artifacts"]["runtime_input_packet"])
            stage_lineage = load_json(summary["artifacts"]["stage_lineage"])

            self.assertEqual("vibe", runtime_input["entry_intent_id"])
            self.assertEqual("requirement_doc", runtime_input["requested_stage_stop"])
            self.assertEqual("requirement_doc", summary["terminal_stage"])
            self.assertEqual(
                ["skeleton_check", "deep_interview", "requirement_doc"],
                list(summary["executed_stage_order"]),
            )
            self.assertEqual(
                ["skeleton_check", "deep_interview", "requirement_doc"],
                [item["stage_name"] for item in stage_lineage["stages"]],
            )
            self.assertEqual("requirement_doc", summary["bounded_return_control"]["terminal_stage"])
            self.assertEqual("xl_plan", summary["bounded_return_control"]["next_stage"])
            self.assertEqual("requirement_confirmation", summary["bounded_return_control"]["approval_kind"])
            self.assertIn(
                "revise_requirement",
                summary["bounded_return_control"]["host_decision_contract"]["allowed_decision_actions"],
            )
            self.assertEqual(["vibe"], list(summary["bounded_return_control"]["allowed_followup_entry_ids"]))
            self.assertTrue(bool(summary["bounded_return_control"]["explicit_new_user_message_required"]))
            self.assertIn("Do not auto-continue into `xl_plan`", summary["bounded_return_control"]["approval_prompt"])
            self.assertIn("Governed runtime host briefing:", summary["host_user_briefing"]["rendered_text"])
            self.assertIn("当前已停在需求确认阶段。", summary["host_user_briefing"]["rendered_text"])
            self.assertIn("先拆任务，再拆模块", summary["host_user_briefing"]["rendered_text"])
            self.assertNotIn("--continue-from-run-id", summary["host_user_briefing"]["rendered_text"])
            self.assertNotIn("--bounded-reentry-token", summary["host_user_briefing"]["rendered_text"])
            self.assertFalse(summary["artifacts"]["execution_plan"])
            self.assertFalse(summary["artifacts"]["execute_receipt"])
            self.assertFalse(summary["artifacts"]["cleanup_receipt"])

    def test_explicit_requirement_doc_stop_stops_after_requirement_freeze(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(
                task="Clarify the project goal before any implementation starts.",
                artifact_root=Path(tempdir),
                governance_scope="root",
                entry_intent_id="vibe",
                requested_stage_stop="requirement_doc",
            )
            summary = payload["summary"]
            runtime_input = load_json(summary["artifacts"]["runtime_input_packet"])
            stage_lineage = load_json(summary["artifacts"]["stage_lineage"])

            self.assertEqual("vibe", runtime_input["entry_intent_id"])
            self.assertNotIn("requested_skill", runtime_input["canonical_router"])
            self.assertEqual("requirement_doc", runtime_input["requested_stage_stop"])
            self.assertIsNone(runtime_input["requested_grade_floor"])
            self.assertEqual("requirement_doc", summary["terminal_stage"])
            self.assertEqual(
                ["skeleton_check", "deep_interview", "requirement_doc"],
                list(summary["executed_stage_order"]),
            )
            self.assertEqual(
                ["skeleton_check", "deep_interview", "requirement_doc"],
                [item["stage_name"] for item in stage_lineage["stages"]],
            )
            self.assertEqual("requirement_doc", summary["bounded_return_control"]["terminal_stage"])
            self.assertEqual(payload["run_id"], summary["bounded_return_control"]["source_run_id"])
            self.assertTrue(bool(summary["bounded_return_control"]["explicit_user_reentry_required"]))
            self.assertEqual(
                ["vibe"],
                list(summary["bounded_return_control"]["allowed_followup_entry_ids"]),
            )
            self.assertTrue(summary["artifacts"]["host_user_briefing"])
            self.assertIn("Governed runtime host briefing:", summary["host_user_briefing"]["rendered_text"])
            self.assertIn("当前已停在需求确认阶段。", summary["host_user_briefing"]["rendered_text"])
            self.assertIn("先拆任务，再拆模块", summary["host_user_briefing"]["rendered_text"])
            self.assertNotIn("--continue-from-run-id", summary["host_user_briefing"]["rendered_text"])
            self.assertNotIn("--bounded-reentry-token", summary["host_user_briefing"]["rendered_text"])
            self.assertTrue(summary["artifacts"]["requirement_doc"])
            self.assertFalse(summary["artifacts"]["execution_plan"])
            self.assertFalse(summary["artifacts"]["execute_receipt"])
            self.assertFalse(summary["artifacts"]["cleanup_receipt"])

    def test_requirement_stop_exposes_self_contained_agent_skill_organization_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(
                task="Read a local project note and summarize the requested facts.",
                artifact_root=Path(tempdir),
                governance_scope="root",
                entry_intent_id="vibe",
                requested_stage_stop="requirement_doc",
            )

            summary = payload["summary"]
            decision_contract = summary["bounded_return_control"]["host_decision_contract"]
            organization_contract = decision_contract["agent_skill_organization_contract"]

            self.assertEqual(
                "host_decision.agent_skill_organization",
                organization_contract["submission_field"],
            )
            self.assertEqual(
                {
                    "approve",
                    "approve_requirement",
                    "approve_requirement_doc",
                    "approve_requirements",
                },
                set(organization_contract["required_for_decision_actions"]),
            )
            self.assertEqual(
                "agent_skill_organization_v1",
                organization_contract["schema_version"],
            )
            self.assertEqual("agent", organization_contract["derived_by"])
            self.assertEqual(["L", "XL"], list(organization_contract["allowed_workflow_levels"]))
            self.assertEqual(
                [
                    "schema_version",
                    "derived_by",
                    "workflow_level",
                    "modules",
                    "selected_skills",
                    "uncovered_modules",
                    "workflow_level_contract",
                ],
                list(organization_contract["required_top_level_fields"]),
            )

            module_contract = organization_contract["module_contract"]
            self.assertEqual(
                [
                    "module_id",
                    "goal",
                    "candidate_skill_ids",
                    "execution_mode",
                    "acceptance_criteria",
                ],
                list(module_contract["required_fields"]),
            )
            self.assertEqual(
                ["skill_assigned", "agent_direct", "blocked_gap"],
                list(module_contract["allowed_execution_modes"]),
            )
            self.assertEqual(1, module_contract["minimum_items"])
            self.assertEqual(["module_id", "goal"], list(module_contract["non_empty_fields"]))
            self.assertTrue(module_contract["unique_module_id_required"])
            self.assertTrue(module_contract["dependency_contract"]["known_module_ids_required"])
            self.assertTrue(module_contract["dependency_contract"]["acyclic_required"])
            criterion_contract = module_contract["acceptance_criterion_contract"]
            self.assertEqual(
                ["criterion_id", "description", "verification_mode"],
                list(criterion_contract["required_fields"]),
            )
            self.assertEqual(
                ["automated", "manual"],
                list(criterion_contract["allowed_verification_modes"]),
            )
            self.assertEqual(1, criterion_contract["minimum_items"])
            self.assertTrue(criterion_contract["unique_criterion_id_per_module"])

            coverage_modes = organization_contract["coverage_contract"]["modes"]
            self.assertEqual(
                {"skill_assigned", "agent_direct", "blocked_gap"},
                set(coverage_modes),
            )
            self.assertTrue(coverage_modes["skill_assigned"]["selected_skill_required"])
            self.assertTrue(coverage_modes["agent_direct"]["selected_skill_forbidden"])
            self.assertTrue(coverage_modes["agent_direct"]["uncovered_module_forbidden"])
            self.assertEqual(
                ["write_scope", "expected_outputs", "verification"],
                list(coverage_modes["agent_direct"]["required_module_fields"]),
            )
            self.assertTrue(coverage_modes["blocked_gap"]["uncovered_module_required"])

            selected_skill_contract = organization_contract["selected_skill_contract"]
            self.assertEqual(
                ["skill_id", "module_ids", "responsibility", "reason"],
                list(selected_skill_contract["required_fields"]),
            )
            self.assertTrue(selected_skill_contract["candidate_membership_required"])
            self.assertTrue(selected_skill_contract["known_module_ids_required"])
            self.assertEqual(
                ["skill_id", "responsibility", "reason"],
                list(selected_skill_contract["non_empty_fields"]),
            )
            self.assertEqual(1, selected_skill_contract["module_ids_minimum_items"])
            self.assertTrue(
                selected_skill_contract["module_assignments_required_when_multiple_modules"]
            )
            module_assignment_contract = selected_skill_contract["module_assignment_contract"]
            self.assertEqual(
                [
                    "module_id",
                    "role",
                    "responsibility",
                    "write_scope",
                    "expected_outputs",
                    "verification",
                ],
                list(module_assignment_contract["required_fields"]),
            )
            self.assertEqual(
                ["owner", "support", "verifier"],
                list(module_assignment_contract["allowed_roles"]),
            )
            self.assertTrue(module_assignment_contract["one_entry_per_declared_module"])
            role_order_contract = module_assignment_contract["role_order_contract"]
            self.assertTrue(role_order_contract["support_runs_before_owner"])
            self.assertTrue(role_order_contract["owner_waits_for_support"])
            self.assertTrue(role_order_contract["verifier_runs_after_owner"])
            self.assertTrue(role_order_contract["role_must_match_temporal_position"])
            self.assertEqual(
                "Use verifier, not support, for review or minimality checks that must happen after the owner finishes.",
                role_order_contract["post_owner_review_rule"],
            )

            skill_identity_contract = organization_contract["skill_identity_contract"]
            self.assertEqual("skill_id", skill_identity_contract["selection_field"])
            self.assertEqual("resolved_skill_entrypoint", skill_identity_contract["authority"])
            self.assertEqual("exact", skill_identity_contract["match_rule"])
            self.assertTrue(skill_identity_contract["display_name_is_not_selection_id"])
            self.assertEqual(
                "directory containing the retained SKILL.md under a declared local Skill root",
                skill_identity_contract["local_directory_rule"],
            )
            self.assertEqual(
                "use the nested Skill directory name when the retained SKILL.md is nested",
                skill_identity_contract["nested_skill_rule"],
            )

            uncovered_module_contract = organization_contract["uncovered_module_contract"]
            self.assertEqual(
                ["module_id", "reason"],
                list(uncovered_module_contract["required_fields"]),
            )
            self.assertTrue(uncovered_module_contract["known_module_id_required"])

            workflow_contract = organization_contract["workflow_level_contract"]
            self.assertEqual(["L", "XL"], list(workflow_contract["required_fields"]))
            self.assertEqual("non_empty_string", workflow_contract["value_type"])

            forbidden_mcp_contract = organization_contract["forbidden_mcp_contract"]
            self.assertEqual("config/forbidden-mcp-policy.json", forbidden_mcp_contract["policy_path"])
            self.assertEqual(
                {"chrome", "chrome-devtools", "playwright", "context7", "claude-flow"},
                set(forbidden_mcp_contract["forbidden_mcp_ids"]),
            )
            self.assertEqual("exact", forbidden_mcp_contract["id_match"])
            self.assertTrue(forbidden_mcp_contract["selected_skills_must_not_require_forbidden_mcps"])

            direct_example = organization_contract["examples"]["agent_direct"]
            self.assertEqual(
                "agent_skill_organization_v1",
                direct_example["schema_version"],
            )
            self.assertEqual("agent_direct", direct_example["modules"][0]["execution_mode"])
            self.assertEqual(
                {
                    "criterion_id": "direct-result",
                    "description": "The requested result is complete and accurate.",
                    "verification_mode": "automated",
                },
                direct_example["modules"][0]["acceptance_criteria"][0],
            )
            self.assertEqual([], list(direct_example["selected_skills"]))
            self.assertEqual([], list(direct_example["uncovered_modules"]))
            self.assertEqual(
                {"L", "XL"},
                set(direct_example["workflow_level_contract"]),
            )
            skill_example = organization_contract["examples"]["skill_assigned"]
            self.assertEqual(
                "skill_assigned",
                skill_example["modules"][0]["execution_mode"],
            )
            self.assertEqual(
                {
                    "criterion_id": "skill-result",
                    "description": "The Skill-owned result satisfies the module goal.",
                    "verification_mode": "automated",
                },
                skill_example["modules"][0]["acceptance_criteria"][0],
            )
            self.assertEqual(
                skill_example["selected_skills"][0]["skill_id"],
                skill_example["modules"][0]["candidate_skill_ids"][0],
            )
            self.assertEqual(
                skill_example["modules"][0]["module_id"],
                skill_example["selected_skills"][0]["module_ids"][0],
            )

            preferred_payload = decision_contract["preferred_payload"]
            self.assertFalse(decision_contract["preferred_payload_complete"])
            self.assertEqual(
                ["agent_skill_organization"],
                list(decision_contract["required_agent_supplied_fields"]),
            )
            self.assertIn("agent_skill_organization", preferred_payload)
            self.assertIsNone(preferred_payload["agent_skill_organization"])

            rendered_text = summary["host_user_briefing"]["rendered_text"]
            self.assertIn(
                "Use the directory name that directly contains the retained `SKILL.md` as `skill_id`",
                rendered_text,
            )
            self.assertIn(
                "Do not submit a displayed Skill name or frontmatter `name` as `skill_id`",
                rendered_text,
            )
            self.assertIn(
                "bounded_return_control.host_decision_contract.agent_skill_organization_contract",
                rendered_text,
            )
            self.assertIn("host_decision.agent_skill_organization", rendered_text)
            self.assertIn("不要通过失败重试或读取运行时源码猜字段", rendered_text)

    def test_requirement_stop_host_briefing_explains_l_and_xl_before_choice(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(
                task="Clarify the project goal before any implementation starts.",
                artifact_root=Path(tempdir),
                governance_scope="root",
                entry_intent_id="vibe",
                requested_stage_stop="requirement_doc",
            )
            summary = payload["summary"]
            requirement_doc = Path(summary["artifacts"]["requirement_doc"]).read_text(encoding="utf-8")
            rendered_text = summary["host_user_briefing"]["rendered_text"]
            self.assertIn("当前已停在需求确认阶段。", rendered_text)
            self.assertIn("先拆任务，再拆模块", rendered_text)
            self.assertIn("按模块搜索本地 skills", rendered_text)
            self.assertIn("阅读候选 `SKILL.md`", rendered_text)
            self.assertIn("给出 `L` / `XL` 两套 skills 组织方案", rendered_text)
            self.assertIn("明确标出缺口", rendered_text)
            self.assertNotIn("Screened task-skill shortlist size:", rendered_text)
            self.assertNotIn("L selected task skills:", rendered_text)
            self.assertNotIn("XL selected task skills:", rendered_text)
            self.assertIn("Recommendation reason:", rendered_text)
            self.assertIn("Why this decision matters:", rendered_text)
            self.assertIn("L workflow:", rendered_text)
            self.assertIn("L skills:", rendered_text)
            self.assertIn("按模块搜索本地 skills", rendered_text)
            self.assertIn("XL workflow:", rendered_text)
            self.assertNotIn("subagent-driven-development", rendered_text)
            self.assertIn("由当前 Agent 依据已冻结计划分波次协调", rendered_text)
            self.assertIn("Before asking the user to choose L or XL", rendered_text)
            self.assertIn("task-specific workflow", rendered_text)
            self.assertIn("task-specific candidate skill names", rendered_text)
            self.assertIn("not yet selected or used", rendered_text)
            self.assertLess(
                rendered_text.index("Before asking the user to choose L or XL"),
                rendered_text.index("Question:"),
            )
            self.assertIn("请根据上面的说明选择并确认这次任务级别。", rendered_text)
            self.assertIn("## Skill Search Guide", requirement_doc)
            self.assertNotIn("L selected task skills:", requirement_doc)
            self.assertNotIn("XL selected task skills:", requirement_doc)
            self.assertIn("Why this decision matters:", requirement_doc)
            self.assertIn("L skills:", requirement_doc)
            self.assertIn("XL skills:", requirement_doc)
            self.assertNotIn("subagent-driven-development", requirement_doc)
            self.assertIn("由当前 Agent 依据已冻结计划分波次协调", requirement_doc)

    def test_explicit_xl_plan_stop_freezes_requirement_and_plan_then_stops_before_execute(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(
                task="Plan the migration and freeze the requirement before execution.",
                artifact_root=Path(tempdir),
                governance_scope="root",
                entry_intent_id="vibe",
                requested_stage_stop="xl_plan",
                requested_grade_floor="XL",
                agent_organization=agent_skill_organization([], workflow_level="XL"),
            )
            summary = payload["summary"]
            runtime_input = load_json(summary["artifacts"]["runtime_input_packet"])
            stage_lineage = load_json(summary["artifacts"]["stage_lineage"])
            requirement_doc = Path(summary["artifacts"]["requirement_doc"]).read_text(encoding="utf-8")
            execution_plan = Path(summary["artifacts"]["execution_plan"]).read_text(encoding="utf-8")
            plan_receipt = load_json(summary["artifacts"]["execution_plan_receipt"])

            self.assertEqual("vibe", runtime_input["entry_intent_id"])
            self.assertNotIn("requested_skill", runtime_input["canonical_router"])
            self.assertEqual("xl_plan", runtime_input["requested_stage_stop"])
            self.assertEqual("XL", runtime_input["requested_grade_floor"])
            self.assertEqual("xl_plan", summary["terminal_stage"])
            self.assertEqual(
                ["skeleton_check", "deep_interview", "requirement_doc", "xl_plan"],
                list(summary["executed_stage_order"]),
            )
            self.assertEqual(
                ["skeleton_check", "deep_interview", "requirement_doc", "xl_plan"],
                [item["stage_name"] for item in stage_lineage["stages"]],
            )
            self.assertEqual("xl_plan", summary["bounded_return_control"]["terminal_stage"])
            self.assertEqual(payload["run_id"], summary["bounded_return_control"]["source_run_id"])
            self.assertTrue(bool(summary["bounded_return_control"]["explicit_user_reentry_required"]))
            self.assertIn(
                "revise_plan",
                summary["bounded_return_control"]["host_decision_contract"]["allowed_decision_actions"],
            )
            plan_revision_contract = summary["bounded_return_control"]["host_decision_contract"][
                "plan_revision_contract"
            ]
            self.assertTrue(plan_revision_contract["revision_delta_required"])
            self.assertTrue(plan_revision_contract["text_delta_does_not_mutate_organization"])
            self.assertTrue(plan_revision_contract["full_organization_replacement_required_when_changed"])
            self.assertEqual(
                [
                    "modules",
                    "skills",
                    "roles",
                    "dependencies",
                    "write_scopes",
                    "expected_outputs",
                    "verification",
                    "workflow_level",
                ],
                list(plan_revision_contract["organization_change_fields"]),
            )
            self.assertEqual(
                ["vibe"],
                list(summary["bounded_return_control"]["allowed_followup_entry_ids"]),
            )
            self.assertTrue(summary["artifacts"]["host_user_briefing"])
            self.assertIn("Governed runtime host briefing:", summary["host_user_briefing"]["rendered_text"])
            self.assertNotIn("--continue-from-run-id", summary["host_user_briefing"]["rendered_text"])
            self.assertNotIn("--bounded-reentry-token", summary["host_user_briefing"]["rendered_text"])
            self.assertNotIn("Entry intent", requirement_doc)
            self.assertNotIn("Requested stop stage", requirement_doc)
            self.assertNotIn("Requested grade floor", execution_plan)
            self.assertIn("## Execution Summary", execution_plan)
            self.assertIn("## Frozen Inputs", execution_plan)
            self.assertEqual("XL", plan_receipt["internal_grade"])
            self.assertFalse(summary["artifacts"]["execute_receipt"])
            self.assertFalse(summary["artifacts"]["execution_manifest"])
            self.assertFalse(summary["artifacts"]["cleanup_receipt"])

    def test_requested_xl_grade_floor_clamps_governed_runtime_execution_grade(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(
                task="Implement the migration with explicit code changes, tests, and verification.",
                artifact_root=Path(tempdir),
                governance_scope="root",
                entry_intent_id="vibe",
                requested_stage_stop="phase_cleanup",
                requested_grade_floor="XL",
                agent_organization=agent_skill_organization([], workflow_level="XL"),
            )
            summary = payload["summary"]
            runtime_input = load_json(summary["artifacts"]["runtime_input_packet"])
            plan_receipt = load_json(summary["artifacts"]["execution_plan_receipt"])
            execution_manifest = load_json(summary["artifacts"]["execution_manifest"])

            self.assertEqual("vibe", runtime_input["entry_intent_id"])
            self.assertNotIn("requested_skill", runtime_input["canonical_router"])
            self.assertEqual("phase_cleanup", runtime_input["requested_stage_stop"])
            self.assertEqual("XL", runtime_input["requested_grade_floor"])
            self.assertEqual("XL", runtime_input["internal_grade"])
            self.assertEqual("XL", plan_receipt["internal_grade"])
            self.assertEqual("XL", execution_manifest["internal_grade"])

    def test_explicit_requirement_doc_stop_stays_before_execute_without_wrapper_confirm(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(
                task="Design architecture migration with staged review and planning gates.",
                artifact_root=Path(tempdir),
                governance_scope="root",
                entry_intent_id="vibe",
                requested_stage_stop="requirement_doc",
            )
            summary = payload["summary"]
            runtime_input = load_json(summary["artifacts"]["runtime_input_packet"])
            stage_lineage = load_json(summary["artifacts"]["stage_lineage"])

            self.assertNotIn("confirm_required", runtime_input["route_snapshot"])
            self.assertEqual("requirement_doc", summary["terminal_stage"])
            self.assertEqual(["skeleton_check", "deep_interview", "requirement_doc"], list(summary["executed_stage_order"]))
            self.assertEqual(
                ["skeleton_check", "deep_interview", "requirement_doc"],
                [item["stage_name"] for item in stage_lineage["stages"]],
            )
            self.assertTrue(summary["artifacts"]["requirement_doc"])
            self.assertTrue(summary["artifacts"]["host_user_briefing"])

    def test_plan_and_execute_scripts_do_not_let_stale_packet_grade_undercut_floor(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            initial_payload = run_runtime(
                task=IMPLEMENTATION_EXECUTION_TASK,
                artifact_root=artifact_root,
                governance_scope="root",
                entry_intent_id="vibe",
                requested_grade_floor="XL",
                agent_organization=agent_skill_organization([], workflow_level="XL"),
            )
            initial_summary = initial_payload["summary"]
            requirement_doc_path = Path(initial_summary["artifacts"]["requirement_doc"])
            runtime_input_packet_path = Path(initial_summary["artifacts"]["runtime_input_packet"])
            runtime_input_packet = load_json(runtime_input_packet_path)
            runtime_input_packet["internal_grade"] = "L"
            runtime_input_packet_path.write_text(
                json.dumps(runtime_input_packet, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            plan_payload = run_write_xl_plan(
                task=IMPLEMENTATION_EXECUTION_TASK,
                artifact_root=artifact_root,
                requirement_doc_path=requirement_doc_path,
                runtime_input_packet_path=runtime_input_packet_path,
            )
            plan_receipt = load_json(plan_payload["receipt_path"])
            execution_payload = run_plan_execute(
                task=IMPLEMENTATION_EXECUTION_TASK,
                artifact_root=artifact_root,
                requirement_doc_path=requirement_doc_path,
                execution_plan_path=Path(plan_payload["execution_plan_path"]),
                runtime_input_packet_path=runtime_input_packet_path,
                module_work_plan_path=Path(plan_payload["module_work_plan_path"]),
            )
            execution_receipt = load_json(execution_payload["receipt_path"])
            execution_manifest = load_json(execution_receipt["execution_manifest_path"])

            self.assertEqual("XL", plan_receipt["internal_grade"])
            self.assertEqual("XL", execution_receipt["internal_grade"])
            self.assertEqual("XL", execution_manifest["internal_grade"])

    def test_write_xl_plan_uses_session_runtime_input_packet_when_path_is_omitted(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            initial_payload = run_runtime(
                task="Plan a small bounded migration.",
                artifact_root=artifact_root,
                governance_scope="root",
                entry_intent_id="vibe",
                requested_stage_stop="xl_plan",
                requested_grade_floor="XL",
                agent_organization=agent_skill_organization([], workflow_level="XL"),
            )
            initial_summary = initial_payload["summary"]
            run_id = str(initial_payload["run_id"])
            requirement_doc_path = Path(initial_summary["artifacts"]["requirement_doc"])
            runtime_input_packet_path = Path(initial_summary["artifacts"]["runtime_input_packet"])

            plan_payload = run_write_xl_plan(
                task="Plan a small bounded migration.",
                artifact_root=artifact_root,
                requirement_doc_path=requirement_doc_path,
                run_id=run_id,
            )
            plan_receipt = load_json(plan_payload["receipt_path"])
            execution_plan = Path(plan_payload["execution_plan_path"]).read_text(encoding="utf-8")

            self.assertEqual(str(runtime_input_packet_path), plan_receipt["runtime_input_packet_path"])
            self.assertEqual("XL", plan_receipt["internal_grade"])
            self.assertIn("## Execution Summary", execution_plan)
            self.assertIn("## Frozen Inputs", execution_plan)
            self.assertNotIn("Entry intent: vibe", execution_plan)
            self.assertNotIn("Requested stop stage: xl_plan", execution_plan)
            self.assertNotIn("Requested grade floor: XL", execution_plan)

    def test_write_xl_plan_uses_skill_search_guide_in_host_facing_disclosure(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available in PATH")

        script_path = REPO_ROOT / "scripts" / "runtime" / "Write-RequirementDoc.ps1"
        run_id = "pytest-xl-plan-skill-search-guide"
        intent_contract = {
            "title": "Governed workflow level confirmation",
            "goal": "Clarify which workflow level should run before any execution starts.",
            "deliverable": "A requirement document with explicit L and XL guidance.",
            "constraints": [
                "Do not start execution before the user chooses the workflow level.",
            ],
            "acceptance_criteria": [
                "Both levels explain the workflow, expected skills, and reason for the recommendation.",
            ],
            "non_goals": [
                "Do not auto-continue into execution planning.",
            ],
            "autonomy_mode": "interactive_governed",
            "assumptions": [
                "The user still needs to confirm the workflow level.",
            ],
        }

        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            intent_contract_path = artifact_root / "intent-contract.json"
            runtime_input_packet_path = artifact_root / "runtime-input-packet.json"
            intent_contract_path.write_text(
                json.dumps(intent_contract, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            runtime_input_packet_path.write_text(
                json.dumps(
                    {
                        "governance_scope": "root",
                        "module_assignments": {
                            "unit_count": 0,
                            "status": "no_bound_skills",
                            "units": [],
                        },
                        "hierarchy": {
                            "root_run_id": run_id,
                        },
                        "host_adapter": {
                            "effective_host_id": "codex",
                            "target_root": str(artifact_root / ".agents"),
                        },
                        "authority_flags": {
                            "explicit_runtime_skill": "vibe",
                        },
                        "route_snapshot": {
                            "task_type": "research",
                            "route_mode": "candidate_discovery_only",
                            "confirm_required": False,
                        },
                        "skill_search_guide": {
                            "schema_version": "skill_search_guide_v1",
                            "skill_roots": [{"kind": "host_local", "path": "C:/Users/demo/.agents/skills"}],
                            "search_protocol": [
                                "先拆任务，再拆模块",
                                "每个模块单独搜索本地 skills",
                            ],
                            "selection_rules": [
                                "优先选真 owner，不选只沾边的 helper",
                            ],
                            "disclosure_rules": [
                                "xl_plan 阶段公开模块、候选、最终采用和缺口",
                            ],
                            "workflow_level_contract": {"levels": ["L", "XL"]},
                        },
                        "agent_skill_organization": agent_skill_organization([]),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    shell,
                    "-NoLogo",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    (
                        "& { "
                        f"$result = & '{script_path}' "
                        "-Task 'Clarify the governed workflow level before execution.' "
                        "-Mode interactive_governed "
                        f"-RunId '{run_id}' "
                        f"-IntentContractPath '{intent_contract_path}' "
                        f"-RuntimeInputPacketPath '{runtime_input_packet_path}' "
                        f"-ArtifactRoot '{artifact_root}'; "
                        "$result | ConvertTo-Json -Depth 20 }"
                    ),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=True,
            )
            requirement_payload = json.loads(completed.stdout)
            requirement_doc_path = Path(requirement_payload["requirement_doc_path"])

            plan_payload = run_write_xl_plan(
                task="Clarify the governed workflow level before execution.",
                artifact_root=artifact_root,
                requirement_doc_path=requirement_doc_path,
                runtime_input_packet_path=runtime_input_packet_path,
                run_id=run_id,
            )
            execution_plan = Path(plan_payload["execution_plan_path"]).read_text(encoding="utf-8")

            self.assertIn("## Skill Search Guide", execution_plan)
            self.assertIn("先拆任务，再拆模块", execution_plan)
            self.assertIn("每个模块单独搜索本地 skills", execution_plan)
            self.assertNotIn("- Selected task skills: `research`, `humanizer`, `paper-writer`", execution_plan)
            self.assertNotIn("- Bounded work skill:", execution_plan)
            self.assertIn("## Frozen Inputs", execution_plan)
            self.assertNotIn("## Binary Skill Usage Plan", execution_plan)
            self.assertNotIn("- Used skill candidates: `research`, `humanizer`, `paper-writer`.", execution_plan)

    def test_write_xl_plan_keeps_unknown_phase_module_work_in_ungrouped_section(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            target_root = artifact_root / ".agents"
            write_installed_skill(target_root, "systematic-debugging")
            initial_payload = run_runtime(
                task=DEBUG_EXECUTION_TASK,
                artifact_root=artifact_root,
                governance_scope="root",
                agent_organization=agent_skill_organization(["systematic-debugging"]),
                extra_env={"VIBE_AGENTS_HOME": str(target_root)},
            )
            initial_summary = initial_payload["summary"]
            requirement_doc_path = Path(initial_summary["artifacts"]["requirement_doc"])
            runtime_input_packet_path = Path(initial_summary["artifacts"]["runtime_input_packet"])
            runtime_input_packet = load_json(runtime_input_packet_path)

            assigned_skill_units = module_skill_assignments(runtime_input_packet)
            self.assertGreaterEqual(len(assigned_skill_units), 1)
            unknown_assignment_skill_id = str(assigned_skill_units[0]["skill_id"])
            runtime_input_packet["module_assignments"]["units"][0]["phase_id"] = "missing-phase"
            runtime_input_packet["execution_phase_decomposition"] = {
                "phases": [
                    {
                        "phase_id": "phase-1",
                        "stage_type": "implementation",
                        "dispatch_phase": "in_execution",
                        "stage_order": 1,
                        "stage_label": "Implementation",
                        "goal": "Exercise ungrouped module assignment rendering.",
                        "depends_on": [],
                        "artifacts_in": [],
                        "artifacts_out": [],
                        "acceptance_checks": [],
                    }
                ]
            }

            runtime_input_packet_path.write_text(
                json.dumps(runtime_input_packet, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            plan_payload = run_write_xl_plan(
                task=DEBUG_EXECUTION_TASK,
                artifact_root=artifact_root,
                requirement_doc_path=requirement_doc_path,
                runtime_input_packet_path=runtime_input_packet_path,
            )
            execution_plan = Path(plan_payload["execution_plan_path"]).read_text(encoding="utf-8")

            self.assertIn("### Phase `ungrouped`", execution_plan)
            self.assertIn(unknown_assignment_skill_id, execution_plan)
            self.assertNotIn("fallback skill execution", execution_plan)
            self.assertIn(
                f"- Dispatch {unknown_assignment_skill_id} as owner.",
                execution_plan,
            )
            self.assertIn("Binding profile: module_work_unit", execution_plan)
            self.assertNotIn("- Suggest pytest-ungrouped-suggestion.", execution_plan)

    def test_plan_execute_uses_the_frozen_module_plan_when_packet_mirrors_are_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            target_root = artifact_root / ".agents"
            expected_entrypoint = write_installed_skill(
                target_root,
                "systematic-debugging",
            ).resolve()
            initial_payload = run_runtime(
                task=DEBUG_EXECUTION_TASK,
                artifact_root=artifact_root,
                governance_scope="root",
                agent_organization=agent_skill_organization(["systematic-debugging"]),
                extra_env={"VIBE_AGENTS_HOME": str(target_root)},
            )
            initial_summary = initial_payload["summary"]
            requirement_doc_path = Path(initial_summary["artifacts"]["requirement_doc"])
            execution_plan_path = Path(initial_summary["artifacts"]["execution_plan"])
            runtime_input_packet_path = Path(initial_summary["artifacts"]["runtime_input_packet"])
            runtime_input_packet = load_json(runtime_input_packet_path)

            assigned_skill_units = module_skill_assignments(runtime_input_packet)
            self.assertGreaterEqual(len(assigned_skill_units), 1)
            module_work_plan = load_json(initial_summary["artifacts"]["module_work_plan"])
            planned_unit = next(
                unit
                for unit in module_work_plan["work_units"]
                if unit["skill_id"] == "systematic-debugging"
            )
            self.assertEqual("systematic-debugging", planned_unit["skill_id"])
            runtime_input_packet["module_assignments"]["units"][0].pop("skill_root", None)
            runtime_input_packet["module_assignments"]["units"][0].pop("skill_entrypoint", None)
            runtime_input_packet_path.write_text(
                json.dumps(runtime_input_packet, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            execution_payload = run_plan_execute(
                task=DEBUG_EXECUTION_TASK,
                artifact_root=artifact_root,
                requirement_doc_path=requirement_doc_path,
                execution_plan_path=execution_plan_path,
                runtime_input_packet_path=runtime_input_packet_path,
            )
            execution_receipt = load_json(execution_payload["receipt_path"])
            execution_manifest = load_json(execution_receipt["execution_manifest_path"])
            handoff = load_json(execution_payload["agent_execution_handoff_path"])

            self.assertEqual("agent_action_required", handoff["status"])
            self.assertEqual(
                expected_entrypoint,
                Path(
                    next(
                        unit["skill_entrypoint"]
                        for unit in handoff["units"]
                        if unit["skill_id"] == "systematic-debugging"
                    )
                ).resolve(),
            )
            self.assertEqual("agent_action_required", execution_manifest["status"])

    def test_plan_execute_hands_off_bound_skill_without_fake_completion(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_path = Path(tempdir)
            target_root = temp_path / ".agents"
            expected_entrypoint = write_installed_skill(target_root, "systematic-debugging").resolve()
            payload = run_runtime(
                task=DEBUG_EXECUTION_TASK,
                artifact_root=temp_path,
                governance_scope="root",
                agent_organization=agent_skill_organization(["systematic-debugging"]),
                extra_env={"VIBE_AGENTS_HOME": str(target_root)},
            )
            summary = payload["summary"]
            runtime_input = load_json(summary["artifacts"]["runtime_input_packet"])
            requirement_doc = Path(summary["artifacts"]["requirement_doc"]).read_text(encoding="utf-8")
            execution_plan = Path(summary["artifacts"]["execution_plan"]).read_text(encoding="utf-8")
            handoff = load_json(summary["artifacts"]["agent_execution_handoff"])
            module_work_plan = load_json(summary["artifacts"]["module_work_plan"])
            execution_manifest = load_json(summary["artifacts"]["execution_manifest"])

            assigned_skill_units = module_skill_assignments(runtime_input)
            self.assertGreaterEqual(len(assigned_skill_units), 1)
            assignment = assigned_skill_units[0]
            for field in (
                "binding_profile",
                "dispatch_phase",
                "execution_priority",
                "lane_policy",
                "parallelizable_in_root_xl",
                "write_scope",
                "review_mode",
            ):
                with self.subTest(field=field):
                    self.assertIn(field, assignment)

            self.assertNotIn("## Selected Skill", requirement_doc)
            self.assertNotIn("Binding: profile=", requirement_doc)
            self.assertIn("## Module Work Plan", execution_plan)
            self.assertNotIn("## Specialist Consultation", execution_plan)
            self.assertNotIn("## Binary Skill Usage Plan", execution_plan)
            self.assertNotIn("## Skill Routing And Usage Evidence", execution_plan)
            self.assertIn("Binding profile:", execution_plan)
            self.assertEqual("plan_execute", summary["terminal_stage"])
            self.assertFalse(summary["artifacts"]["cleanup_receipt"])
            self.assertEqual("agent_action_required", execution_manifest["status"])
            for retired_result_field in (
                "execution_skill_outcomes",
                "executed_skill_execution_units",
                "failed_skill_execution_units",
                "blocked_skill_execution_units",
            ):
                with self.subTest(retired_result_field=retired_result_field):
                    self.assertNotIn(retired_result_field, execution_manifest)

            assigned_units = [
                unit for unit in handoff["units"] if unit["skill_id"] == assignment["skill_id"]
            ]
            self.assertEqual(1, len(assigned_units))
            assigned = assigned_units[0]
            self.assertEqual(expected_entrypoint, Path(assigned["skill_entrypoint"]).resolve())
            for field in (
                "unit_id",
                "module_id",
                "skill_id",
                "skill_entrypoint",
                "responsibility",
                "expected_outputs",
                "verification",
                "depends_on_unit_ids",
                "write_scope",
            ):
                with self.subTest(field=field):
                    self.assertIn(field, assigned)

            self.assertEqual("agent_action_required", handoff["status"])
            self.assertEqual("agent", handoff["control_owner"])
            self.assertEqual("module_execution_v1", handoff["result_contract"]["schema_version"])
            self.assertRegex(handoff["result_contract"]["module_work_plan_digest"], r"^[0-9a-f]{64}$")
            self.assertEqual("owner", handoff["units"][0]["role"])
            self.assertEqual(
                [unit["unit_id"] for unit in handoff["units"]],
                [unit["unit_id"] for unit in handoff["result_contract"]["units"]],
            )
            self.assertEqual(
                [module["module_id"] for module in module_work_plan["modules"]],
                [module["module_id"] for module in handoff["result_contract"]["modules"]],
            )
            self.assertTrue(str(handoff["module_execution_path"]).endswith("module-execution.json"))
            self.assertIn("--module-execution-json-file", handoff["return_command"])
            self.assertIn(str(REPO_ROOT.resolve()), handoff["return_command"])
            self.assertNotIn("<vibe_root>", handoff["return_command"])
            self.assertIsNone(summary["artifacts"]["module_execution"])
            self.assertFalse(Path(handoff["module_execution_path"]).exists())

    def test_agent_handoff_provides_a_directly_fillable_module_execution_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_path = Path(tempdir)
            target_root = temp_path / ".agents"
            write_installed_skill(target_root, "systematic-debugging")
            payload = run_runtime(
                task=DEBUG_EXECUTION_TASK,
                artifact_root=temp_path,
                governance_scope="root",
                agent_organization=agent_skill_organization(["systematic-debugging"]),
                extra_env={"VIBE_AGENTS_HOME": str(target_root)},
            )
            summary = payload["summary"]
            handoff = load_json(summary["artifacts"]["agent_execution_handoff"])
            contract = handoff["result_contract"]
            template = contract["submission_template"]

            self.assertEqual(
                [
                    "schema_version",
                    "source_run_id",
                    "module_work_plan_digest",
                    "units",
                    "modules",
                    "tdd_evidence",
                ],
                contract["required_top_level_fields"],
            )
            self.assertEqual(["completed", "failed", "blocked"], contract["terminal_states"])
            self.assertEqual(["passing", "failing", "blocked"], contract["criterion_terminal_states"])
            self.assertEqual(["criterion_id", "state"], contract["criterion_result_required_fields"])
            self.assertEqual("module_execution_v1", template["schema_version"])
            self.assertEqual(contract["source_run_id"], template["source_run_id"])
            self.assertEqual(contract["module_work_plan_digest"], template["module_work_plan_digest"])
            self.assertEqual(
                [
                    "unit_id",
                    "module_id",
                    "skill_id",
                    "role",
                    "state",
                    "result_summary",
                    "evidence_paths",
                    "verification_results",
                ],
                contract["units"][0]["required_result_fields"],
            )
            self.assertEqual(
                [
                    "module_id",
                    "required",
                    "execution_mode",
                    "gap_reason",
                    "state",
                    "criterion_results",
                ],
                contract["modules"][0]["required_result_fields"],
            )
            self.assertEqual(
                {
                    "unit_id": contract["units"][0]["unit_id"],
                    "module_id": contract["units"][0]["module_id"],
                    "skill_id": contract["units"][0]["skill_id"],
                    "role": contract["units"][0]["role"],
                    "state": None,
                    "result_summary": "",
                    "evidence_paths": [],
                    "verification_results": [],
                },
                template["units"][0],
            )
            self.assertEqual(
                {
                    "module_id": contract["modules"][0]["module_id"],
                    "required": contract["modules"][0]["required"],
                    "execution_mode": contract["modules"][0]["execution_mode"],
                    "gap_reason": contract["modules"][0]["gap_reason"],
                    "state": None,
                    "criterion_results": [
                        {
                            "criterion_id": criterion["criterion_id"],
                            "state": None,
                            "details": "",
                        }
                        for criterion in contract["modules"][0]["acceptance_criteria"]
                    ],
                },
                template["modules"][0],
            )
            self.assertTrue(contract["tdd_evidence"]["required_code_task_tdd_evidence_requirements"])
            self.assertEqual(
                {
                    "state": None,
                    "evidence_paths": [],
                    "red_phase_evidence_paths": [],
                    "green_phase_evidence_paths": [],
                    "refactor_phase_evidence_paths": [],
                    "covered_code_task_tdd_evidence_requirements": [],
                    "covered_code_task_tdd_exceptions": [],
                    "notes": "",
                },
                template["tdd_evidence"],
            )
            briefing = Path(summary["artifacts"]["host_user_briefing"]).read_text(encoding="utf-8")
            self.assertIn("Copy `result_contract.submission_template`", briefing)
            self.assertIn("`passing`, `failing`, or `blocked`", briefing)
            self.assertIn("same `module-execution.json`", briefing)
            self.assertIn("do not create a separate `tdd-evidence.json`", briefing)

    def test_execution_plan_omits_repo_release_boilerplate_for_bounded_task(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            target_root = artifact_root / ".agents"
            write_installed_skill(target_root, "systematic-debugging")
            payload = run_runtime(
                task="Diagnose and repair one isolated Python fixture through its CLI and public function.",
                artifact_root=artifact_root,
                governance_scope="root",
                requested_stage_stop="xl_plan",
                requested_grade_floor="L",
                agent_organization=agent_skill_organization(["systematic-debugging"]),
                extra_env={"VIBE_AGENTS_HOME": str(target_root)},
            )

            execution_plan = Path(payload["summary"]["artifacts"]["execution_plan"]).read_text(
                encoding="utf-8"
            )

            self.assertIn("## Verification Commands", execution_plan)
            self.assertIn("## Rollback Plan", execution_plan)
            self.assertIn("## Phase Cleanup Contract", execution_plan)
            for unrelated_boilerplate in (
                "Re-run mirror sync and parity validation",
                "Revert only the governed-runtime change set",
                "Run node audit and cleanup",
            ):
                with self.subTest(unrelated_boilerplate=unrelated_boilerplate):
                    self.assertNotIn(unrelated_boilerplate, execution_plan)

    def test_child_handoff_contains_only_the_approved_module_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            target_root = artifact_root / ".agents"
            write_installed_skill(target_root, "scientific-reporting")
            composite_task = (
                "Analyze biological sequences with Python, draft a scientific report, "
                "and prepare the execution planning notes."
            )
            root_payload = run_runtime(
                task=composite_task,
                artifact_root=artifact_root,
                governance_scope="root",
                agent_organization=agent_skill_organization(["scientific-reporting"]),
                extra_env={"VIBE_AGENTS_HOME": str(target_root)},
            )
            root_summary = root_payload["summary"]
            root_artifacts = root_summary["artifacts"]
            root_runtime_input = load_json(root_artifacts["runtime_input_packet"])
            root_assignments = module_skill_assignments(root_runtime_input)
            planned_skill_ids = [
                str(item.get("skill_id", "")).strip()
                for item in root_assignments
                if str(item.get("skill_id", "")).strip()
            ]
            if not planned_skill_ids:
                self.skipTest("Root run did not expose module Skill assignment ids")

            parent_unit_id = "pytest-child-topology-unit"
            child_run_id = "pytest-topology-" + uuid.uuid4().hex[:10]
            child_payload = run_runtime(
                task=composite_task + " Child lane requests a Skill outside its approved module assignment.",
                artifact_root=artifact_root,
                run_id=child_run_id,
                governance_scope="child",
                root_run_id=str(root_summary["run_id"]),
                parent_run_id=str(root_summary["run_id"]),
                parent_unit_id=parent_unit_id,
                inherited_requirement_doc_path=Path(root_artifacts["requirement_doc"]),
                inherited_execution_plan_path=Path(root_artifacts["execution_plan"]),
                agent_organization=agent_skill_organization(planned_skill_ids[:1]),
                extra_env={"VIBE_AGENTS_HOME": str(target_root)},
            )
            child_summary = child_payload["summary"]
            child_execution_manifest = load_json(child_summary["artifacts"]["execution_manifest"])
            child_handoff = load_json(child_summary["artifacts"]["agent_execution_handoff"])

            self.assertEqual("agent_action_required", child_handoff["status"])
            self.assertEqual(
                planned_skill_ids[:1],
                [unit["skill_id"] for unit in child_handoff["units"]],
            )
            self.assertIsNone(child_summary["artifacts"]["module_execution"])
            self.assertFalse(Path(child_handoff["module_execution_path"]).exists())
            self.assertFalse(bool(child_execution_manifest["authority"]["completion_claim_allowed"]))

    def test_child_handoff_remains_frozen_to_approved_module_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            target_root = artifact_root / ".agents"
            write_installed_skill(target_root, "scientific-reporting")
            composite_task = (
                "Analyze biological sequences with Python, draft a scientific report, "
                "and prepare the execution planning notes."
            )
            root_payload = run_runtime(
                task=composite_task,
                artifact_root=artifact_root,
                governance_scope="root",
                agent_organization=agent_skill_organization(["scientific-reporting"]),
                extra_env={"VIBE_AGENTS_HOME": str(target_root)},
            )
            root_summary = root_payload["summary"]
            root_artifacts = root_summary["artifacts"]
            root_runtime_input = load_json(root_artifacts["runtime_input_packet"])
            root_assignments = module_skill_assignments(root_runtime_input)
            planned_skill_ids = [
                str(item.get("skill_id", "")).strip()
                for item in root_assignments
                if str(item.get("skill_id", "")).strip()
            ]
            if len(planned_skill_ids) < 1:
                self.skipTest("Root run did not expose module Skill assignment ids")

            parent_unit_id = "pytest-child-topology-frozen-unit"
            child_run_id = "pytest-topology-" + uuid.uuid4().hex[:10]
            child_payload = run_runtime(
                task=composite_task + " Child lane requests a Skill outside its approved module assignment.",
                artifact_root=artifact_root,
                run_id=child_run_id,
                governance_scope="child",
                root_run_id=str(root_summary["run_id"]),
                parent_run_id=str(root_summary["run_id"]),
                parent_unit_id=parent_unit_id,
                inherited_requirement_doc_path=Path(root_artifacts["requirement_doc"]),
                inherited_execution_plan_path=Path(root_artifacts["execution_plan"]),
                agent_organization=agent_skill_organization(planned_skill_ids[:1]),
                extra_env={"VIBE_AGENTS_HOME": str(target_root)},
            )
            child_summary = child_payload["summary"]
            child_execution_manifest = load_json(child_summary["artifacts"]["execution_manifest"])
            child_handoff = load_json(child_summary["artifacts"]["agent_execution_handoff"])

            self.assertEqual(
                planned_skill_ids[:1],
                [unit["skill_id"] for unit in child_handoff["units"]],
            )
            self.assertIsNone(child_summary["artifacts"]["module_execution"])
            self.assertFalse(Path(child_handoff["module_execution_path"]).exists())
            self.assertFalse(bool(child_execution_manifest["authority"]["completion_claim_allowed"]))

    def test_child_divergent_skill_request_without_local_entrypoint_does_not_bind(self) -> None:
        cases = [
            ("L", ""),
            ("XL", "XL"),
        ]

        for expected_grade, requested_grade_floor in cases:
            with self.subTest(expected_grade=expected_grade):
                with tempfile.TemporaryDirectory() as tempdir:
                    artifact_root = Path(tempdir)
                    root_payload = run_runtime(
                        task=IMPLEMENTATION_EXECUTION_TASK,
                        artifact_root=artifact_root,
                        governance_scope="root",
                        requested_grade_floor=requested_grade_floor,
                        agent_organization=agent_skill_organization([], workflow_level=expected_grade),
                    )
                    root_summary = root_payload["summary"]
                    parent_unit_id = f"pytest-{expected_grade.lower()}-divergent-child-unit"
                    child_run_id = "pytest-topology-" + uuid.uuid4().hex[:10]
                    child_payload = run_runtime(
                        task=IMPLEMENTATION_EXECUTION_TASK
                        + " Child lane diverges into a new Skill demand set.",
                        artifact_root=artifact_root,
                        run_id=child_run_id,
                        governance_scope="child",
                        root_run_id=str(root_summary["run_id"]),
                        parent_run_id=str(root_summary["run_id"]),
                        parent_unit_id=parent_unit_id,
                        inherited_requirement_doc_path=Path(root_summary["artifacts"]["requirement_doc"]),
                        inherited_execution_plan_path=Path(root_summary["artifacts"]["execution_plan"]),
                        requested_grade_floor=requested_grade_floor,
                        agent_organization=agent_skill_organization([], workflow_level=expected_grade),
                    )

                    child_summary = child_payload["summary"]
                    child_execution_manifest = load_json(child_summary["artifacts"]["execution_manifest"])
                    child_handoff = load_json(child_summary["artifacts"]["agent_execution_handoff"])
                    child_module_work_plan = load_json(
                        child_summary["artifacts"]["module_work_plan"]
                    )

                    self.assertEqual(expected_grade, child_execution_manifest["internal_grade"])
                    self.assertEqual(expected_grade, child_handoff["workflow_level"])
                    self.assertEqual([], child_handoff["units"])
                    self.assertEqual(
                        ["blocked_gap"],
                        [
                            module["execution_mode"]
                            for module in child_module_work_plan["modules"]
                        ],
                    )
                    self.assertIsNone(child_summary["artifacts"]["module_execution"])
                    self.assertFalse(Path(child_handoff["module_execution_path"]).exists())
                    self.assertEqual("agent_action_required", child_execution_manifest["status"])
                    self.assertFalse(bool(child_execution_manifest["authority"]["completion_claim_allowed"]))

    def test_agent_handoff_enforces_l_serial_and_xl_ready_nonconflicting_waves(self) -> None:
        for workflow_level in ("L", "XL"):
            with self.subTest(workflow_level=workflow_level):
                with tempfile.TemporaryDirectory() as tempdir:
                    artifact_root = Path(tempdir)
                    target_root = artifact_root / ".agents"
                    for skill_id in ("topology-a", "topology-b", "topology-c", "topology-d"):
                        write_installed_skill(target_root, skill_id)

                    payload = run_runtime(
                        task="Produce four governed module results with one dependency and one write conflict.",
                        artifact_root=artifact_root,
                        governance_scope="root",
                        requested_grade_floor="XL" if workflow_level == "XL" else "",
                        agent_organization=dependency_and_scope_organization(workflow_level),
                        extra_env={"VIBE_AGENTS_HOME": str(target_root)},
                    )
                    summary = payload["summary"]
                    handoff = load_json(summary["artifacts"]["agent_execution_handoff"])
                    module_work_plan = load_json(summary["artifacts"]["module_work_plan"])
                    self.assertIsNone(summary["artifacts"]["module_execution"])
                    self.assertFalse(Path(handoff["module_execution_path"]).exists())

                self.assertEqual("agent_action_required", handoff["status"])
                self.assertEqual("agent", handoff["control_owner"])
                self.assertEqual(
                    ["skill_assigned"] * 4,
                    [module["execution_mode"] for module in module_work_plan["modules"]],
                )

                unit_by_id = {unit["unit_id"]: unit for unit in handoff["units"]}
                earlier_unit_ids: set[str] = set()
                parallel_wave_seen = False
                for wave in handoff["waves"]:
                    wave_unit_ids = list(wave["unit_ids"])
                    wave_units = [unit_by_id[unit_id] for unit_id in wave_unit_ids]
                    for unit in wave_units:
                        self.assertTrue(
                            set(unit["depends_on_unit_ids"]).issubset(earlier_unit_ids),
                            f"{unit['unit_id']} was handed off before its dependencies completed",
                        )

                    if workflow_level == "L":
                        self.assertEqual("sequential", wave["execution_mode"])
                        self.assertEqual(1, len(wave_unit_ids))
                    elif len(wave_unit_ids) > 1:
                        parallel_wave_seen = True
                        self.assertEqual("bounded_parallel", wave["execution_mode"])
                        write_scopes = [unit["write_scope"] for unit in wave_units]
                        self.assertEqual(len(write_scopes), len(set(write_scopes)))

                    earlier_unit_ids.update(wave_unit_ids)

                self.assertEqual(set(unit_by_id), earlier_unit_ids)
                if workflow_level == "XL":
                    self.assertTrue(parallel_wave_seen)

    def test_xl_partitions_mixed_write_scope_conflicts_into_bounded_waves(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            target_root = artifact_root / ".agents"
            for skill_id in ("topology-a", "topology-b", "topology-c"):
                write_installed_skill(target_root, skill_id)

            payload = run_runtime(
                task="Run two conflicting modules and one independent module.",
                artifact_root=artifact_root,
                governance_scope="root",
                requested_grade_floor="XL",
                agent_organization=mixed_write_scope_organization(),
                extra_env={"VIBE_AGENTS_HOME": str(target_root)},
            )
            handoff = load_json(payload["summary"]["artifacts"]["agent_execution_handoff"])

        unit_by_id = {unit["unit_id"]: unit for unit in handoff["units"]}
        parallel_waves = [wave for wave in handoff["waves"] if wave["execution_mode"] == "bounded_parallel"]
        self.assertEqual(1, len(parallel_waves))
        parallel_units = [unit_by_id[unit_id] for unit_id in parallel_waves[0]["unit_ids"]]
        self.assertEqual(2, len(parallel_units))
        self.assertEqual(
            2,
            len({unit["write_scope"] for unit in parallel_units}),
        )
        self.assertEqual(
            ["sequential"],
            [wave["execution_mode"] for wave in handoff["waves"] if wave not in parallel_waves],
        )

    def test_blocked_module_is_recorded_without_a_fake_skill_result_or_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(
                task="Stop because the required module has no approved Skill owner.",
                artifact_root=Path(tempdir),
                governance_scope="root",
                agent_organization=agent_skill_organization([]),
            )
            summary = payload["summary"]
            handoff = load_json(summary["artifacts"]["agent_execution_handoff"])
            execution_manifest = load_json(summary["artifacts"]["execution_manifest"])
            module_work_plan = load_json(summary["artifacts"]["module_work_plan"])
            self.assertIsNone(summary["artifacts"]["module_execution"])
            self.assertFalse(Path(handoff["module_execution_path"]).exists())

            self.assertEqual("plan_execute", summary["terminal_stage"])
            self.assertFalse(summary["artifacts"]["cleanup_receipt"])
            self.assertEqual([], handoff["units"])
            self.assertEqual([], handoff["waves"])
            self.assertEqual(
                ["blocked_gap"],
                [module["execution_mode"] for module in module_work_plan["modules"]],
            )
            manifest_text = json.dumps(execution_manifest, ensure_ascii=False)
            for retired_result_field in (
                "execution_skill_outcomes",
                "executed_skill_execution_units",
                "failed_skill_execution_units",
                "blocked_skill_execution_units",
            ):
                with self.subTest(retired_result_field=retired_result_field):
                    self.assertNotIn(retired_result_field, manifest_text)

    def test_runtime_packaging_uses_canonical_sources_without_nested_runtime_compatibility(self) -> None:
        governance = json.loads((REPO_ROOT / "config" / "version-governance.json").read_text(encoding="utf-8"))
        generated_compat = governance["packaging"]["generated_compatibility"]["nested_runtime_root"]
        canonical_runtime_root = REPO_ROOT / "scripts" / "runtime"
        bundled_runtime_roots = [
            REPO_ROOT / "bundled" / "skills" / "vibe" / "scripts" / "runtime",
            REPO_ROOT / "bundled" / "skills" / "vibe" / "bundled" / "skills" / "vibe" / "scripts" / "runtime",
        ]

        self.assertEqual("", generated_compat["relative_path"])
        self.assertEqual("disabled", generated_compat["materialization_mode"])
        self.assertTrue(canonical_runtime_root.exists())
        for bundled_runtime in bundled_runtime_roots:
            with self.subTest(bundled_runtime=str(bundled_runtime)):
                self.assertFalse(bundled_runtime.exists())


if __name__ == "__main__":
    unittest.main()
