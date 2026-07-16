from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
FREEZE_SCRIPT = REPO_ROOT / "scripts" / "runtime" / "Freeze-RuntimeInputPacket.ps1"
INVOKE_SCRIPT = REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"
EXECUTE_SCRIPT = REPO_ROOT / "scripts" / "runtime" / "Invoke-PlanExecute.ps1"


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


def prepare_local_skill_env(root: Path) -> dict[str, str]:
    target_root = root / "home" / ".agents"
    skills = {
        "fasta-owner": "Use when the task requires parsing FASTA records and computing sequence statistics.",
        "reader-summary": "Use when technical findings must be rewritten as a concise reader-facing summary.",
    }
    for skill_id, description in skills.items():
        skill_dir = target_root / "skills" / skill_id
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {skill_id}\ndescription: {description}\n---\n# {skill_id}\n",
            encoding="utf-8",
            newline="\n",
        )
    env = os.environ.copy()
    env["VCO_HOST_ID"] = "codex"
    env["VIBE_AGENTS_HOME"] = str(target_root)
    return env


def normalized_powershell_error(value: str) -> str:
    return " ".join(value.split())


def agent_skill_organization() -> dict[str, object]:
    return {
        "schema_version": "agent_skill_organization_v1",
        "derived_by": "agent",
        "workflow_level": "L",
        "modules": [
            {
                "module_id": "fasta_parse",
                "goal": "Parse FASTA records and compute sequence statistics.",
                "candidate_skill_ids": ["fasta-owner"],
                "execution_mode": "blocked_gap",
                "acceptance_criteria": [
                    {
                        "criterion_id": "fasta-result",
                        "description": "The FASTA result is present and verified.",
                        "verification_mode": "automated",
                    }
                ],
            },
            {
                "module_id": "reader_summary",
                "goal": "Turn the findings into a concise reader-facing summary.",
                "candidate_skill_ids": ["reader-summary"],
                "execution_mode": "skill_assigned",
                "acceptance_criteria": [
                    {
                        "criterion_id": "reader-result",
                        "description": "The reader-facing summary is present and verified.",
                        "verification_mode": "automated",
                    }
                ],
            },
        ],
        "selected_skills": [
            {
                "skill_id": "reader-summary",
                "module_ids": ["reader_summary"],
                "responsibility": "Write the final reader-facing explanation.",
                "reason": "Its SKILL.md directly owns audience-facing summaries.",
            }
        ],
        "uncovered_modules": [
            {
                "module_id": "fasta_parse",
                "reason": "No parsing owner was approved for this plan.",
            }
        ],
        "workflow_level_contract": {
            "L": "Use one serial lane with the smallest complete organization.",
            "XL": "Use bounded waves when more modules or review lanes are needed.",
        },
    }


def multi_skill_module_organization() -> dict[str, object]:
    return {
        "schema_version": "agent_skill_organization_v1",
        "derived_by": "agent",
        "workflow_level": "XL",
        "modules": [
            {
                "module_id": "module_a",
                "goal": "Produce and independently verify one module result.",
                "candidate_skill_ids": ["fasta-owner", "reader-summary"],
                "required": True,
                "depends_on": [],
                "execution_mode": "skill_assigned",
                "acceptance_criteria": [
                    {
                        "criterion_id": "module-a-verified",
                        "description": "The owner result is independently verified.",
                        "verification_mode": "automated",
                    }
                ],
            }
        ],
        "selected_skills": [
            {
                "skill_id": "fasta-owner",
                "module_ids": ["module_a"],
                "role": "owner",
                "responsibility": "Produce the primary module result.",
                "reason": "Its SKILL.md owns the primary work.",
                "expected_outputs": ["module-a-result.json"],
                "verification": ["Check the result schema."],
            },
            {
                "skill_id": "reader-summary",
                "module_ids": ["module_a"],
                "role": "verifier",
                "responsibility": "Verify the primary module result.",
                "reason": "Its SKILL.md owns the reader-facing verification.",
                "expected_outputs": ["module-a-review.md"],
                "verification": ["Record a passing review result."],
            },
        ],
        "uncovered_modules": [],
        "workflow_level_contract": {
            "L": "Run owner and verifier serially.",
            "XL": "Use bounded lanes while preserving owner-before-verifier order.",
        },
    }


def dependent_module_organization() -> dict[str, object]:
    organization = multi_skill_module_organization()
    organization["workflow_level"] = "L"
    organization["modules"] = [
        {
            "module_id": "module_a",
            "goal": "Produce the upstream result.",
            "candidate_skill_ids": ["fasta-owner"],
            "required": True,
            "depends_on": [],
            "execution_mode": "skill_assigned",
            "acceptance_criteria": [
                {
                    "criterion_id": "module-a-result",
                    "description": "The upstream result exists.",
                    "verification_mode": "automated",
                }
            ],
        },
        {
            "module_id": "module_b",
            "goal": "Use the upstream result in a reader summary.",
            "candidate_skill_ids": ["reader-summary"],
            "required": True,
            "depends_on": ["module_a"],
            "execution_mode": "skill_assigned",
            "acceptance_criteria": [
                {
                    "criterion_id": "module-b-result",
                    "description": "The downstream summary exists.",
                    "verification_mode": "automated",
                }
            ],
        },
    ]
    organization["selected_skills"] = [
        {
            "skill_id": "fasta-owner",
            "module_ids": ["module_a"],
            "role": "owner",
            "responsibility": "Produce the upstream result.",
            "reason": "Its SKILL.md owns the upstream work.",
        },
        {
            "skill_id": "reader-summary",
            "module_ids": ["module_b"],
            "role": "owner",
            "responsibility": "Produce the downstream summary.",
            "reason": "Its SKILL.md owns the summary work.",
        },
    ]
    return organization


def independent_module_organization(*, write_scope: str | None = None) -> dict[str, object]:
    selected_skills: list[dict[str, object]] = [
        {
            "skill_id": "fasta-owner",
            "module_ids": ["module_a"],
            "role": "owner",
            "responsibility": "Produce the first independent result.",
            "reason": "Its SKILL.md owns the first module.",
        },
        {
            "skill_id": "reader-summary",
            "module_ids": ["module_b"],
            "role": "owner",
            "responsibility": "Produce the second independent result.",
            "reason": "Its SKILL.md owns the second module.",
        },
    ]
    if write_scope is not None:
        for selected in selected_skills:
            selected["write_scope"] = write_scope
    return {
        "schema_version": "agent_skill_organization_v1",
        "derived_by": "agent",
        "workflow_level": "XL",
        "modules": [
            {
                "module_id": "module_a",
                "goal": "Produce the first independent result.",
                "candidate_skill_ids": ["fasta-owner"],
                "required": True,
                "depends_on": [],
                "execution_mode": "skill_assigned",
                "acceptance_criteria": [
                    {
                        "criterion_id": "module-a-result",
                        "description": "The first result exists.",
                        "verification_mode": "automated",
                    }
                ],
            },
            {
                "module_id": "module_b",
                "goal": "Produce the second independent result.",
                "candidate_skill_ids": ["reader-summary"],
                "required": True,
                "depends_on": [],
                "execution_mode": "skill_assigned",
                "acceptance_criteria": [
                    {
                        "criterion_id": "module-b-result",
                        "description": "The second result exists.",
                        "verification_mode": "automated",
                    }
                ],
            },
        ],
        "selected_skills": selected_skills,
        "uncovered_modules": [],
        "workflow_level_contract": {
            "L": "Run the independent modules serially.",
            "XL": "Run independent non-conflicting modules in one bounded wave.",
        },
    }


def shared_skill_multi_module_organization() -> dict[str, object]:
    return {
        "schema_version": "agent_skill_organization_v1",
        "derived_by": "agent",
        "workflow_level": "XL",
        "modules": [
            {
                "module_id": "module_a",
                "goal": "Produce the first module result.",
                "candidate_skill_ids": ["reader-summary"],
                "required": True,
                "depends_on": [],
                "execution_mode": "skill_assigned",
                "acceptance_criteria": [
                    {
                        "criterion_id": "module-a-result",
                        "description": "The first result exists.",
                        "verification_mode": "automated",
                    }
                ],
            },
            {
                "module_id": "module_b",
                "goal": "Produce the second module result.",
                "candidate_skill_ids": ["reader-summary"],
                "required": True,
                "depends_on": ["module_a"],
                "execution_mode": "skill_assigned",
                "acceptance_criteria": [
                    {
                        "criterion_id": "module-b-result",
                        "description": "The second result exists.",
                        "verification_mode": "automated",
                    }
                ],
            },
        ],
        "selected_skills": [
            {
                "skill_id": "reader-summary",
                "module_ids": ["module_a", "module_b"],
                "responsibility": "Apply the reader-summary method to both modules.",
                "reason": "Its SKILL.md owns both reader-facing modules.",
                "module_assignments": [
                    {
                        "module_id": "module_a",
                        "role": "owner",
                        "responsibility": "Write the first module result.",
                        "write_scope": "outputs/module-a/**",
                        "expected_outputs": ["outputs/module-a/result.md"],
                        "verification": ["Check the first result."],
                    },
                    {
                        "module_id": "module_b",
                        "role": "verifier",
                        "responsibility": "Verify and summarize the second module result.",
                        "write_scope": "outputs/module-b/**",
                        "expected_outputs": ["outputs/module-b/review.md"],
                        "verification": ["Check the second result."],
                    },
                ],
            }
        ],
        "uncovered_modules": [],
        "workflow_level_contract": {
            "L": "Run both modules serially.",
            "XL": "Keep the dependency while using module-specific work contracts.",
        },
    }


def overlapping_three_module_organization() -> dict[str, object]:
    organization = shared_skill_multi_module_organization()
    organization["modules"][1]["depends_on"] = []
    organization["modules"].append(
        {
            "module_id": "module_c",
            "goal": "Produce the third independent result.",
            "candidate_skill_ids": ["reader-summary"],
            "required": True,
            "depends_on": [],
            "execution_mode": "skill_assigned",
            "acceptance_criteria": [
                {
                    "criterion_id": "module-c-result",
                    "description": "The third result exists.",
                    "verification_mode": "automated",
                }
            ],
        }
    )
    selected = organization["selected_skills"][0]
    selected["module_ids"].append("module_c")
    selected["module_assignments"][0]["write_scope"] = "outputs/shared/**"
    selected["module_assignments"][1]["role"] = "owner"
    selected["module_assignments"][1]["write_scope"] = "outputs/shared/qa/**"
    selected["module_assignments"].append(
        {
            "module_id": "module_c",
            "role": "owner",
            "responsibility": "Write the third independent result.",
            "write_scope": "outputs/other/**",
            "expected_outputs": ["outputs/other/result.md"],
            "verification": ["Check the third result."],
        }
    )
    return organization


def agent_direct_organization() -> dict[str, object]:
    return {
        "schema_version": "agent_skill_organization_v1",
        "derived_by": "agent",
        "workflow_level": "L",
        "modules": [
            {
                "module_id": "direct_module",
                "goal": "Complete the approved module directly in the current Agent.",
                "candidate_skill_ids": [],
                "required": True,
                "depends_on": [],
                "execution_mode": "agent_direct",
                "write_scope": "outputs/direct/**",
                "expected_outputs": ["outputs/direct/result.md"],
                "verification": ["Check the direct result against the frozen criteria."],
                "acceptance_criteria": [
                    {
                        "criterion_id": "direct-result",
                        "description": "The direct result exists.",
                        "verification_mode": "automated",
                    }
                ],
            }
        ],
        "selected_skills": [],
        "uncovered_modules": [],
        "workflow_level_contract": {
            "L": "Run the approved direct module serially.",
            "XL": "Use bounded waves only when independent modules exist.",
        },
    }


def run_freeze(
    shell: str,
    *,
    artifact_root: Path,
    env: dict[str, str],
    requested_stage_stop: str,
    host_decision: dict[str, object] | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [
        shell,
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(FREEZE_SCRIPT),
        "-Task",
        "Use fasta-owner to parse FASTA records and explain the results for general readers.",
        "-Mode",
        "interactive_governed",
        "-RunId",
        "pytest-agent-skill-organization",
        "-RequestedStageStop",
        requested_stage_stop,
        "-ArtifactRoot",
        str(artifact_root),
    ]
    if host_decision is not None:
        command.extend(["-HostDecisionJson", json.dumps(host_decision, ensure_ascii=False)])
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def run_plan_execute(
    shell: str,
    *,
    artifact_root: Path,
    env: dict[str, str],
    run_id: str,
    task: str,
    organization: dict[str, object],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            shell,
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(INVOKE_SCRIPT),
            "-Task",
            task,
            "-Mode",
            "interactive_governed",
            "-RunId",
            run_id,
            "-RequestedStageStop",
            "plan_execute",
            "-HostDecisionJson",
            json.dumps(
                {"agent_skill_organization": organization}, ensure_ascii=False
            ),
            "-ArtifactRoot",
            str(artifact_root),
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


class AgentSkillOrganizationContractTests(unittest.TestCase):
    def test_requirement_packet_keeps_route_candidates_out_of_module_assignments(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            artifact_root = root / "artifacts"
            completed = run_freeze(
                shell,
                artifact_root=artifact_root,
                env=prepare_local_skill_env(root),
                requested_stage_stop="requirement_doc",
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            packet_path = next(artifact_root.rglob("runtime-input-packet.json"))
            packet = json.loads(packet_path.read_text(encoding="utf-8"))

        self.assertGreaterEqual(len(packet["skill_routing"]["candidates"]), 1)
        self.assertNotIn("selected", packet["skill_routing"])
        self.assertEqual([], packet["module_assignments"]["units"])
        self.assertIsNone(packet["agent_skill_organization"])

    def test_xl_plan_freeze_requires_agent_skill_organization(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            completed = run_freeze(
                shell,
                artifact_root=root / "artifacts",
                env=prepare_local_skill_env(root),
                requested_stage_stop="xl_plan",
            )

        self.assertNotEqual(0, completed.returncode)
        self.assertIn("agent_skill_organization is required before xl_plan", completed.stderr)

    def test_single_module_skill_inherits_the_module_work_contract(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        organization = agent_skill_organization()
        module = next(
            item for item in organization["modules"] if item["module_id"] == "reader_summary"
        )
        module["write_scope"] = "no task-file writes"
        module["expected_outputs"] = ["An in-memory reader summary."]
        module["verification"] = ["Check the summary against the approved source material."]
        selected_skill = organization["selected_skills"][0]
        for field in ("write_scope", "expected_outputs", "verification"):
            self.assertNotIn(field, selected_skill)

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            artifact_root = root / "artifacts"
            completed = run_plan_execute(
                shell,
                artifact_root=artifact_root,
                env=prepare_local_skill_env(root),
                run_id="pytest-single-module-inherited-contract",
                task="Produce one reader-facing module result.",
                organization=organization,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            module_work_plan = json.loads(
                next(artifact_root.rglob("module-work-plan.json")).read_text(encoding="utf-8")
            )
            handoff = json.loads(
                next(artifact_root.rglob("agent-execution-handoff.json")).read_text(
                    encoding="utf-8"
                )
            )

        expected = {
            "write_scope": "no task-file writes",
            "expected_outputs": ["An in-memory reader summary."],
            "verification": ["Check the summary against the approved source material."],
        }
        for units in (module_work_plan["work_units"], handoff["units"]):
            unit = next(item for item in units if item["module_id"] == "reader_summary")
            self.assertEqual(expected, {field: unit[field] for field in expected})

    def test_single_module_skill_fields_override_module_work_contract(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        organization = agent_skill_organization()
        module = next(
            item for item in organization["modules"] if item["module_id"] == "reader_summary"
        )
        module["write_scope"] = "outputs/module-default/**"
        module["expected_outputs"] = ["outputs/module-default/result.md"]
        module["verification"] = ["Check the module default result."]
        expected = {
            "write_scope": "outputs/skill-override/**",
            "expected_outputs": ["outputs/skill-override/result.md"],
            "verification": ["Check the selected Skill result."],
        }
        organization["selected_skills"][0].update(expected)

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            artifact_root = root / "artifacts"
            completed = run_plan_execute(
                shell,
                artifact_root=artifact_root,
                env=prepare_local_skill_env(root),
                run_id="pytest-single-module-override-contract",
                task="Produce one reader-facing module result.",
                organization=organization,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            module_work_plan = json.loads(
                next(artifact_root.rglob("module-work-plan.json")).read_text(encoding="utf-8")
            )
            handoff = json.loads(
                next(artifact_root.rglob("agent-execution-handoff.json")).read_text(
                    encoding="utf-8"
                )
            )

        for units in (module_work_plan["work_units"], handoff["units"]):
            unit = next(item for item in units if item["module_id"] == "reader_summary")
            self.assertEqual(expected, {field: unit[field] for field in expected})

    def test_xl_plan_rejects_missing_or_mismatched_module_execution_modes(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        missing_mode = agent_direct_organization()
        missing_mode["modules"][0].pop("execution_mode")

        uncovered_as_skill = agent_skill_organization()
        uncovered_as_skill["modules"][0]["execution_mode"] = "skill_assigned"
        uncovered_as_skill["modules"][1]["execution_mode"] = "skill_assigned"

        selected_as_gap = multi_skill_module_organization()
        selected_as_gap["modules"][0]["execution_mode"] = "blocked_gap"

        cases = (
            (missing_mode, "must include execution_mode"),
            (uncovered_as_skill, "declares skill_assigned but is not covered by a selected skill"),
            (selected_as_gap, "declares blocked_gap but is not declared uncovered"),
        )
        for index, (organization, expected_error) in enumerate(cases):
            with self.subTest(expected_error=expected_error):
                with tempfile.TemporaryDirectory() as tempdir:
                    root = Path(tempdir)
                    completed = run_freeze(
                        shell,
                        artifact_root=root / "artifacts",
                        env=prepare_local_skill_env(root),
                        requested_stage_stop="xl_plan",
                        host_decision={"agent_skill_organization": organization},
                    )

                self.assertNotEqual(0, completed.returncode, f"case {index} unexpectedly passed")
                self.assertIn(expected_error, normalized_powershell_error(completed.stderr))

    def test_xl_plan_rejects_ambiguous_multi_module_skill_work(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        missing_assignments = shared_skill_multi_module_organization()
        missing_assignments["selected_skills"][0].pop("module_assignments")

        invalid_role = independent_module_organization()
        invalid_role["selected_skills"][0]["role"] = "module_owner"

        cases = (
            (
                missing_assignments,
                "must include one module_assignments entry per module",
            ),
            (invalid_role, "role must be `owner`, `support`, or `verifier`"),
        )
        for organization, expected_error in cases:
            with self.subTest(expected_error=expected_error):
                with tempfile.TemporaryDirectory() as tempdir:
                    root = Path(tempdir)
                    completed = run_freeze(
                        shell,
                        artifact_root=root / "artifacts",
                        env=prepare_local_skill_env(root),
                        requested_stage_stop="xl_plan",
                        host_decision={"agent_skill_organization": organization},
                    )

                self.assertNotEqual(0, completed.returncode)
                self.assertIn(expected_error, normalized_powershell_error(completed.stderr))

    def test_xl_plan_rejects_module_write_scopes_that_claim_runtime_result_artifacts(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        selected_skill = shared_skill_multi_module_organization()
        selected_skill["selected_skills"][0]["module_assignments"][0]["write_scope"] = (
            "outputs/runtime/vibe-sessions/prior-run/module-execution.json#module_a"
        )

        agent_direct = agent_direct_organization()
        agent_direct["modules"][0]["write_scope"] = "module-execution.json#direct_module"

        for organization in (selected_skill, agent_direct):
            with self.subTest(execution_mode=organization["modules"][0]["execution_mode"]):
                with tempfile.TemporaryDirectory() as tempdir:
                    root = Path(tempdir)
                    completed = run_freeze(
                        shell,
                        artifact_root=root / "artifacts",
                        env=prepare_local_skill_env(root),
                        requested_stage_stop="xl_plan",
                        host_decision={"agent_skill_organization": organization},
                    )

                self.assertNotEqual(0, completed.returncode)
                self.assertIn(
                    "canonical runtime",
                    normalized_powershell_error(completed.stderr),
                )

    def test_xl_plan_rejects_unstructured_module_acceptance_criteria(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        organization = agent_direct_organization()
        organization["modules"][0]["acceptance_criteria"] = ["The result exists."]

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            completed = run_freeze(
                shell,
                artifact_root=root / "artifacts",
                env=prepare_local_skill_env(root),
                requested_stage_stop="xl_plan",
                host_decision={"agent_skill_organization": organization},
            )

        self.assertNotEqual(0, completed.returncode)
        self.assertIn(
            "acceptance_criteria items must be JSON objects",
            normalized_powershell_error(completed.stderr),
        )

    def test_xl_plan_requires_at_least_one_module_acceptance_criterion(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        cases = ("missing", "empty")
        for case in cases:
            with self.subTest(case=case):
                organization = agent_direct_organization()
                if case == "missing":
                    organization["modules"][0].pop("acceptance_criteria")
                else:
                    organization["modules"][0]["acceptance_criteria"] = []

                with tempfile.TemporaryDirectory() as tempdir:
                    root = Path(tempdir)
                    completed = run_freeze(
                        shell,
                        artifact_root=root / "artifacts",
                        env=prepare_local_skill_env(root),
                        requested_stage_stop="xl_plan",
                        host_decision={"agent_skill_organization": organization},
                    )

                self.assertNotEqual(0, completed.returncode)
                self.assertIn(
                    "must include at least one acceptance criterion",
                    normalized_powershell_error(completed.stderr),
                )

    def test_xl_plan_validates_module_acceptance_criterion_fields(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        base_criterion = {
            "criterion_id": "direct-result",
            "description": "The direct result exists.",
            "verification_mode": "automated",
        }
        cases: tuple[tuple[list[dict[str, object]], str], ...] = (
            ([{k: v for k, v in base_criterion.items() if k != "criterion_id"}], "must include criterion_id"),
            ([{k: v for k, v in base_criterion.items() if k != "description"}], "must include description"),
            ([{**base_criterion, "verification_mode": "visual"}], "verification_mode must be"),
            ([base_criterion, dict(base_criterion)], "contains duplicate acceptance criterion `direct-result`"),
        )

        for criteria, expected_error in cases:
            with self.subTest(expected_error=expected_error):
                organization = agent_direct_organization()
                organization["modules"][0]["acceptance_criteria"] = criteria

                with tempfile.TemporaryDirectory() as tempdir:
                    root = Path(tempdir)
                    completed = run_freeze(
                        shell,
                        artifact_root=root / "artifacts",
                        env=prepare_local_skill_env(root),
                        requested_stage_stop="xl_plan",
                        host_decision={"agent_skill_organization": organization},
                    )

                self.assertNotEqual(0, completed.returncode)
                self.assertIn(expected_error, normalized_powershell_error(completed.stderr))

    def test_xl_plan_rejects_module_criteria_that_require_post_return_cleanup(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        descriptions = (
            "Temporary probes are absent, the cleanup receipt is emitted, and completion wording "
            "is permitted only after delivery acceptance passes.",
            "If the input gate or any dependent analysis module is blocked, no analysis Markdown, "
            "simulated result, successful cleanup statement, or completion language is produced.",
        )

        for description in descriptions:
            with self.subTest(description=description), tempfile.TemporaryDirectory() as tempdir:
                root = Path(tempdir)
                organization = agent_direct_organization()
                organization["modules"][0]["acceptance_criteria"][0]["description"] = description
                completed = run_freeze(
                    shell,
                    artifact_root=root / "artifacts",
                    env=prepare_local_skill_env(root),
                    requested_stage_stop="xl_plan",
                    host_decision={"agent_skill_organization": organization},
                )

            self.assertNotEqual(0, completed.returncode)
            self.assertIn(
                "post-return cleanup is not a valid module acceptance criterion",
                normalized_powershell_error(completed.stderr),
            )

    def test_xl_plan_accepts_module_local_temporary_file_cleanup(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        organization = agent_direct_organization()
        organization["modules"][0]["acceptance_criteria"][0]["description"] = (
            "Temporary files created by this module are removed before its result is returned."
        )

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            completed = run_freeze(
                shell,
                artifact_root=root / "artifacts",
                env=prepare_local_skill_env(root),
                requested_stage_stop="xl_plan",
                host_decision={"agent_skill_organization": organization},
            )

        self.assertEqual(0, completed.returncode, completed.stderr)

    def test_xl_plan_accepts_a_nested_skill_entrypoint_from_the_declared_root(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            target_root = root / "home" / ".agents"
            nested_skill = (
                target_root
                / "skills"
                / "document-suite"
                / "vendor"
                / "docx-toolkit"
                / "SKILL.md"
            )
            nested_skill.parent.mkdir(parents=True)
            nested_skill.write_text(
                "---\n"
                "name: docx-toolkit\n"
                "description: Create and validate formal DOCX documents.\n"
                "---\n"
                "# DOCX Toolkit\n",
                encoding="utf-8",
                newline="\n",
            )
            organization = agent_direct_organization()
            organization["modules"][0].update(
                {
                    "candidate_skill_ids": ["docx-toolkit"],
                    "execution_mode": "skill_assigned",
                }
            )
            organization["selected_skills"] = [
                {
                    "skill_id": "docx-toolkit",
                    "module_ids": ["direct_module"],
                    "responsibility": "Create the formal DOCX document.",
                    "reason": "Its nested SKILL.md directly owns DOCX production.",
                }
            ]
            env = os.environ.copy()
            env["VCO_HOST_ID"] = "codex"
            env["VIBE_AGENTS_HOME"] = str(target_root)
            completed = run_freeze(
                shell,
                artifact_root=root / "artifacts",
                env=env,
                requested_stage_stop="xl_plan",
                host_decision={"agent_skill_organization": organization},
            )

        self.assertEqual(0, completed.returncode, completed.stderr)

    def test_xl_plan_accepts_a_codex_plugin_cache_skill_without_a_global_link(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            target_root = root / "home" / ".agents"
            plugin_cache = root / "home" / ".codex" / "plugins" / "cache"
            plugin_skill = (
                plugin_cache
                / "openai-primary-runtime"
                / "documents"
                / "26.709.11516"
                / "skills"
                / "documents"
                / "SKILL.md"
            )
            plugin_skill.parent.mkdir(parents=True)
            plugin_skill.write_text(
                "---\n"
                "name: documents\n"
                "description: Render and verify formal documents.\n"
                "---\n"
                "# Documents\n",
                encoding="utf-8",
                newline="\n",
            )
            organization = agent_direct_organization()
            organization["modules"][0].update(
                {
                    "candidate_skill_ids": ["documents"],
                    "execution_mode": "skill_assigned",
                }
            )
            organization["selected_skills"] = [
                {
                    "skill_id": "documents",
                    "module_ids": ["direct_module"],
                    "responsibility": "Render and verify the formal document.",
                    "reason": "The enabled Codex plugin Skill owns document rendering and QA.",
                }
            ]
            env = os.environ.copy()
            env["VCO_HOST_ID"] = "codex"
            env["VIBE_AGENTS_HOME"] = str(target_root)
            artifact_root = root / "artifacts"
            completed = run_freeze(
                shell,
                artifact_root=artifact_root,
                env=env,
                requested_stage_stop="xl_plan",
                host_decision={"agent_skill_organization": organization},
            )
            if completed.returncode == 0:
                packet = json.loads(next(artifact_root.rglob("runtime-input-packet.json")).read_text(encoding="utf-8"))

        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn(
            {"kind": "host_plugin_cache", "path": str(plugin_cache.resolve())},
            packet["skill_search_guide"]["skill_roots"],
        )
        self.assertEqual(str(plugin_skill.resolve()), packet["module_assignments"]["units"][0]["skill_entrypoint"])

    def test_xl_plan_rejects_an_ambiguous_codex_plugin_cache_skill_id(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            target_root = root / "home" / ".agents"
            plugin_cache = root / "home" / ".codex" / "plugins" / "cache"
            for provider in ("provider-a", "provider-b"):
                skill_file = plugin_cache / provider / "documents" / "1" / "skills" / "documents" / "SKILL.md"
                skill_file.parent.mkdir(parents=True)
                skill_file.write_text(
                    "---\nname: documents\ndescription: Render formal documents.\n---\n# Documents\n",
                    encoding="utf-8",
                    newline="\n",
                )
            organization = agent_direct_organization()
            organization["modules"][0].update(
                {
                    "candidate_skill_ids": ["documents"],
                    "execution_mode": "skill_assigned",
                }
            )
            organization["selected_skills"] = [
                {
                    "skill_id": "documents",
                    "module_ids": ["direct_module"],
                    "responsibility": "Render and verify the formal document.",
                    "reason": "The selected Skill must resolve to one exact local entrypoint.",
                }
            ]
            env = os.environ.copy()
            env["VCO_HOST_ID"] = "codex"
            env["VIBE_AGENTS_HOME"] = str(target_root)
            completed = run_freeze(
                shell,
                artifact_root=root / "artifacts",
                env=env,
                requested_stage_stop="xl_plan",
                host_decision={"agent_skill_organization": organization},
            )

        self.assertNotEqual(0, completed.returncode)
        self.assertIn("ambiguous_nested_skill_id", normalized_powershell_error(completed.stderr))

    def test_route_candidates_are_audit_only_during_requirement_progression(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            artifact_root = root / "artifacts"
            target_root = root / "home" / ".agents"
            env = os.environ.copy()
            env["VCO_HOST_ID"] = "codex"
            env["VIBE_AGENTS_HOME"] = str(target_root)
            for skill_id in ("sleep-stress-alpha", "sleep-stress-beta"):
                skill_dir = target_root / "skills" / skill_id
                skill_dir.mkdir(parents=True)
                (skill_dir / "SKILL.md").write_text(
                    "---\n"
                    f"name: {skill_id}\n"
                    "description: Analyze sleep logs, stress scores, focus ratings, and daily wellness tables.\n"
                    "---\n"
                    f"# {skill_id}\n",
                    encoding="utf-8",
                    newline="\n",
                )
            completed = subprocess.run(
                [
                    shell,
                    "-NoLogo",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(INVOKE_SCRIPT),
                    "-Task",
                    "Review sleep and stress patterns from wearable exports before I decide next steps.",
                    "-Mode",
                    "interactive_governed",
                    "-RunId",
                    "pytest-agent-skill-route-audit",
                    "-HostDecisionJson",
                    "{}",
                    "-RequestedStageStop",
                    "requirement_doc",
                    "-ArtifactRoot",
                    str(artifact_root),
                ],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            packet = json.loads(next(artifact_root.rglob("runtime-input-packet.json")).read_text(encoding="utf-8"))
            summary = json.loads(next(artifact_root.rglob("runtime-summary.json")).read_text(encoding="utf-8"))

        self.assertGreaterEqual(len(packet["skill_routing"]["candidates"]), 1)
        self.assertEqual("requirement_doc", summary["terminal_stage"])

    def test_runtime_has_no_route_confirmation_stop(self) -> None:
        runtime = INVOKE_SCRIPT.read_text(encoding="utf-8")

        self.assertNotIn("routing_confirmation_required", runtime)
        self.assertNotIn("$confirmRequired = [bool](Get-VibeNestedPropertySafe", runtime)

    def test_agent_skill_organization_is_the_only_module_assignments_source(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            artifact_root = root / "artifacts"
            completed = run_freeze(
                shell,
                artifact_root=artifact_root,
                env=prepare_local_skill_env(root),
                requested_stage_stop="xl_plan",
                host_decision={"agent_skill_organization": agent_skill_organization()},
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            packet_path = next(artifact_root.rglob("runtime-input-packet.json"))
            packet = json.loads(packet_path.read_text(encoding="utf-8"))

        self.assertEqual("agent_skill_organization_v1", packet["agent_skill_organization"]["schema_version"])
        self.assertEqual(["reader-summary"], [row["bound_skill"] for row in packet["module_assignments"]["units"]])
        self.assertEqual("agent_skill_organization", packet["module_assignments"]["source"])
        self.assertEqual(
            "Write the final reader-facing explanation.",
            packet["module_assignments"]["units"][0]["task_slice"],
        )

    def test_xl_plan_renders_agent_modules_candidates_selection_and_gaps(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            artifact_root = root / "artifacts"
            completed = subprocess.run(
                [
                    shell,
                    "-NoLogo",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(INVOKE_SCRIPT),
                    "-Task",
                    "Use fasta-owner to parse FASTA records and explain the results for general readers.",
                    "-Mode",
                    "interactive_governed",
                    "-RunId",
                    "pytest-agent-skill-organization-plan",
                    "-RequestedStageStop",
                    "xl_plan",
                    "-HostDecisionJson",
                    json.dumps({"agent_skill_organization": agent_skill_organization()}, ensure_ascii=False),
                    "-ArtifactRoot",
                    str(artifact_root),
                ],
                cwd=REPO_ROOT,
                env=prepare_local_skill_env(root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            summary_path = next(artifact_root.rglob("runtime-summary.json"))
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            plan_path = Path(summary["artifacts"]["execution_plan"])
            plan_text = plan_path.read_text(encoding="utf-8")
            module_work_plan_path = Path(summary["artifacts"]["module_work_plan"])
            module_work_plan = json.loads(module_work_plan_path.read_text(encoding="utf-8"))

        self.assertEqual("xl_plan", summary["terminal_stage"])
        self.assertIn("## Task Modules", plan_text)
        self.assertIn("## Candidate Skills By Module", plan_text)
        self.assertIn("## Module Work Plan", plan_text)
        self.assertIn("## Uncovered Modules", plan_text)
        self.assertIn("## L / XL Organization Difference", plan_text)
        self.assertIn("fasta_parse", plan_text)
        self.assertIn("fasta-owner", plan_text)
        self.assertIn("reader-summary", plan_text)
        self.assertIn("Write the final reader-facing explanation.", plan_text)
        self.assertIn("No parsing owner was approved for this plan.", plan_text)
        self.assertIn("Execution mode: `blocked_gap`", plan_text)
        self.assertIn("Execution mode: `skill_assigned`", plan_text)
        self.assertIn("Acceptance:", plan_text)
        self.assertEqual("module_work_plan_v1", module_work_plan["schema_version"])
        self.assertEqual("L", module_work_plan["workflow_level"])
        self.assertEqual(
            ["fasta_parse", "reader_summary"],
            [module["module_id"] for module in module_work_plan["modules"]],
        )
        self.assertEqual("blocked_gap", module_work_plan["modules"][0]["execution_mode"])
        self.assertEqual(
            "No parsing owner was approved for this plan.",
            module_work_plan["modules"][0]["gap_reason"],
        )
        self.assertEqual("skill_assigned", module_work_plan["modules"][1]["execution_mode"])
        self.assertEqual("reader_summary", module_work_plan["work_units"][0]["module_id"])
        self.assertEqual("reader-summary", module_work_plan["work_units"][0]["skill_id"])
        self.assertEqual("owner", module_work_plan["work_units"][0]["role"])

    def test_plan_execute_hands_off_only_agent_selected_skills(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            artifact_root = root / "artifacts"
            completed = subprocess.run(
                [
                    shell,
                    "-NoLogo",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(INVOKE_SCRIPT),
                    "-Task",
                    "Use fasta-owner to parse FASTA records and explain the results for general readers.",
                    "-Mode",
                    "interactive_governed",
                    "-RunId",
                    "pytest-agent-skill-organization-execute",
                    "-RequestedStageStop",
                    "plan_execute",
                    "-HostDecisionJson",
                    json.dumps({"agent_skill_organization": agent_skill_organization()}, ensure_ascii=False),
                    "-ArtifactRoot",
                    str(artifact_root),
                ],
                cwd=REPO_ROOT,
                env=prepare_local_skill_env(root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            summary = json.loads(next(artifact_root.rglob("runtime-summary.json")).read_text(encoding="utf-8"))
            packet = json.loads(next(artifact_root.rglob("runtime-input-packet.json")).read_text(encoding="utf-8"))
            manifest = json.loads(next(artifact_root.rglob("execution-manifest.json")).read_text(encoding="utf-8"))
            handoff = json.loads(
                Path(summary["artifacts"]["agent_execution_handoff"]).read_text(encoding="utf-8")
            )
            execute_receipt = json.loads(
                next(artifact_root.rglob("phase-execute.json")).read_text(encoding="utf-8")
            )

        self.assertEqual("plan_execute", summary["terminal_stage"])
        self.assertEqual(["reader-summary"], [row["bound_skill"] for row in packet["module_assignments"]["units"]])
        self.assertEqual(["reader-summary"], manifest["module_handoff"]["assigned_skill_ids"])
        self.assertNotIn("fasta-owner", manifest["module_handoff"]["assigned_skill_ids"])
        self.assertEqual("agent_action_required", manifest["module_handoff"]["status"])
        self.assertEqual("agent_execution_handoff_v1", handoff["schema_version"])
        self.assertEqual("agent_action_required", handoff["status"])
        self.assertEqual("agent", handoff["control_owner"])
        self.assertEqual(["reader-summary"], [unit["skill_id"] for unit in handoff["units"]])
        self.assertEqual(["reader_summary"], [unit["module_id"] for unit in handoff["units"]])
        self.assertIsNone(summary["artifacts"]["module_execution"])
        self.assertFalse(Path(handoff["module_execution_path"]).exists())
        self.assertEqual("agent_action_required", execute_receipt["status"])
        self.assertEqual(
            summary["artifacts"]["agent_execution_handoff"],
            execute_receipt["agent_execution_handoff_path"],
        )
        self.assertEqual(
            handoff["module_execution_path"],
            execute_receipt["module_execution_path"],
        )
        self.assertEqual(["reader-summary"], execute_receipt["assigned_skill_ids"])

    def test_module_plan_preserves_module_acceptance_and_skill_roles(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            artifact_root = root / "artifacts"
            completed = subprocess.run(
                [
                    shell,
                    "-NoLogo",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(INVOKE_SCRIPT),
                    "-Task",
                    "Produce and independently verify one module result.",
                    "-Mode",
                    "interactive_governed",
                    "-RunId",
                    "pytest-module-role-plan",
                    "-RequestedStageStop",
                    "xl_plan",
                    "-HostDecisionJson",
                    json.dumps(
                        {"agent_skill_organization": multi_skill_module_organization()},
                        ensure_ascii=False,
                    ),
                    "-ArtifactRoot",
                    str(artifact_root),
                ],
                cwd=REPO_ROOT,
                env=prepare_local_skill_env(root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            module_work_plan = json.loads(
                next(artifact_root.rglob("module-work-plan.json")).read_text(encoding="utf-8")
            )

        module = module_work_plan["modules"][0]
        self.assertEqual("module-a-verified", module["acceptance_criteria"][0]["criterion_id"])
        self.assertEqual("automated", module["acceptance_criteria"][0]["verification_mode"])
        units = {unit["skill_id"]: unit for unit in module_work_plan["work_units"]}
        self.assertEqual("owner", units["fasta-owner"]["role"])
        self.assertEqual("verifier", units["reader-summary"]["role"])
        self.assertEqual(["module-a-result.json"], units["fasta-owner"]["expected_outputs"])
        self.assertEqual(["Record a passing review result."], units["reader-summary"]["verification"])
        self.assertEqual(
            [units["fasta-owner"]["unit_id"]],
            units["reader-summary"]["depends_on_unit_ids"],
        )
        self.assertRegex(module_work_plan["requirement_digest"], r"^[0-9a-f]{64}$")
        self.assertRegex(module_work_plan["organization_digest"], r"^[0-9a-f]{64}$")

    def test_verifier_waits_for_owner_before_agent_execution(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            artifact_root = root / "artifacts"
            completed = subprocess.run(
                [
                    shell,
                    "-NoLogo",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(INVOKE_SCRIPT),
                    "-Task",
                    "Produce and independently verify one module result.",
                    "-Mode",
                    "interactive_governed",
                    "-RunId",
                    "pytest-module-verifier-waits",
                    "-RequestedStageStop",
                    "plan_execute",
                    "-HostDecisionJson",
                    json.dumps(
                        {"agent_skill_organization": multi_skill_module_organization()},
                        ensure_ascii=False,
                    ),
                    "-ArtifactRoot",
                    str(artifact_root),
                ],
                cwd=REPO_ROOT,
                env=prepare_local_skill_env(root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            module_work_plan = json.loads(
                next(artifact_root.rglob("module-work-plan.json")).read_text(encoding="utf-8")
            )
            handoff = json.loads(
                next(artifact_root.rglob("agent-execution-handoff.json")).read_text(encoding="utf-8")
            )

        planned_units = {unit["role"]: unit for unit in module_work_plan["work_units"]}
        self.assertFalse(Path(handoff["module_execution_path"]).exists())
        self.assertEqual(
            [planned_units["owner"]["unit_id"]],
            planned_units["verifier"]["depends_on_unit_ids"],
        )
        self.assertEqual(1, planned_units["owner"]["stage_order"])
        self.assertEqual(2, planned_units["verifier"]["stage_order"])

    def test_xl_does_not_parallelize_work_units_with_the_same_write_scope(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            artifact_root = root / "artifacts"
            completed = subprocess.run(
                [
                    shell,
                    "-NoLogo",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(INVOKE_SCRIPT),
                    "-Task",
                    "Produce two independent results in one shared output.",
                    "-Mode",
                    "interactive_governed",
                    "-RunId",
                    "pytest-module-write-scope",
                    "-RequestedStageStop",
                    "plan_execute",
                    "-HostDecisionJson",
                    json.dumps(
                        {
                            "agent_skill_organization": independent_module_organization(
                                write_scope="shared:result"
                            )
                        },
                        ensure_ascii=False,
                    ),
                    "-ArtifactRoot",
                    str(artifact_root),
                ],
                cwd=REPO_ROOT,
                env=prepare_local_skill_env(root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            module_work_plan = json.loads(
                next(artifact_root.rglob("module-work-plan.json")).read_text(encoding="utf-8")
            )
            handoff = json.loads(
                next(artifact_root.rglob("agent-execution-handoff.json")).read_text(encoding="utf-8")
            )

        self.assertEqual(
            ["shared:result", "shared:result"],
            [unit["write_scope"] for unit in module_work_plan["work_units"]],
        )
        self.assertEqual(["sequential", "sequential"], [wave["execution_mode"] for wave in handoff["waves"]])

    def test_module_plan_drives_l_serial_and_xl_bounded_parallel_handoff_waves(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        observed_steps: dict[str, list[dict[str, object]]] = {}
        for workflow_level in ("L", "XL"):
            with tempfile.TemporaryDirectory() as tempdir:
                root = Path(tempdir)
                artifact_root = root / "artifacts"
                organization = independent_module_organization()
                organization["workflow_level"] = workflow_level
                completed = subprocess.run(
                    [
                        shell,
                        "-NoLogo",
                        "-NoProfile",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-File",
                        str(INVOKE_SCRIPT),
                        "-Task",
                        "Produce two independent module results.",
                        "-Mode",
                        "interactive_governed",
                        "-RunId",
                        f"pytest-module-topology-{workflow_level.lower()}",
                        "-RequestedStageStop",
                        "plan_execute",
                        "-HostDecisionJson",
                        json.dumps(
                            {"agent_skill_organization": organization},
                            ensure_ascii=False,
                        ),
                        "-ArtifactRoot",
                        str(artifact_root),
                    ],
                    cwd=REPO_ROOT,
                    env=prepare_local_skill_env(root),
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=False,
                )
                self.assertEqual(0, completed.returncode, completed.stderr)
                handoff = json.loads(
                    next(artifact_root.rglob("agent-execution-handoff.json")).read_text(
                        encoding="utf-8"
                    )
                )
                observed_steps[workflow_level] = list(handoff["waves"])

        self.assertEqual(
            ["sequential", "sequential"],
            [wave["execution_mode"] for wave in observed_steps["L"]],
        )
        self.assertEqual(1, max(len(wave["unit_ids"]) for wave in observed_steps["L"]))
        self.assertEqual(["bounded_parallel"], [wave["execution_mode"] for wave in observed_steps["XL"]])
        self.assertEqual(2, len(observed_steps["XL"][0]["unit_ids"]))

    def test_shared_skill_uses_module_specific_work_contracts(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        organization = shared_skill_multi_module_organization()
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            artifact_root = root / "artifacts"
            completed = run_plan_execute(
                shell,
                artifact_root=artifact_root,
                env=prepare_local_skill_env(root),
                run_id="pytest-module-specific-skill-work",
                task="Use one selected Skill for two different modules.",
                organization=organization,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            module_work_plan = json.loads(
                next(artifact_root.rglob("module-work-plan.json")).read_text(encoding="utf-8")
            )
            handoff = json.loads(
                next(artifact_root.rglob("agent-execution-handoff.json")).read_text(
                    encoding="utf-8"
                )
            )

        fields = ("role", "responsibility", "write_scope", "expected_outputs", "verification")
        expected = {
            assignment["module_id"]: {field: assignment[field] for field in fields}
            for assignment in organization["selected_skills"][0]["module_assignments"]
        }
        for units in (module_work_plan["work_units"], handoff["units"]):
            actual = {
                unit["module_id"]: {field: unit[field] for field in fields}
                for unit in units
            }
            self.assertEqual(expected, actual)

    def test_xl_waves_limit_parallelism_and_detect_nested_write_scope_conflicts(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            artifact_root = root / "artifacts"
            completed = subprocess.run(
                [
                    shell,
                    "-NoLogo",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(INVOKE_SCRIPT),
                    "-Task",
                    "Run three independent XL modules with two nested output paths.",
                    "-Mode",
                    "interactive_governed",
                    "-RunId",
                    "pytest-xl-bounded-overlap",
                    "-RequestedStageStop",
                    "plan_execute",
                    "-HostDecisionJson",
                    json.dumps(
                        {"agent_skill_organization": overlapping_three_module_organization()},
                        ensure_ascii=False,
                    ),
                    "-ArtifactRoot",
                    str(artifact_root),
                ],
                cwd=REPO_ROOT,
                env=prepare_local_skill_env(root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            handoff = json.loads(
                next(artifact_root.rglob("agent-execution-handoff.json")).read_text(
                    encoding="utf-8"
                )
            )

        units = {unit["unit_id"]: unit for unit in handoff["units"]}
        self.assertLessEqual(max(len(wave["unit_ids"]) for wave in handoff["waves"]), 2)
        for wave in handoff["waves"]:
            scopes = [units[unit_id]["write_scope"] for unit_id in wave["unit_ids"]]
            self.assertFalse(
                "outputs/shared/**" in scopes and "outputs/shared/qa/**" in scopes,
                scopes,
            )
        self.assertEqual(
            {"module_a", "module_b", "module_c"},
            {unit["module_id"] for unit in handoff["units"]},
        )

    def test_visible_xl_wave_plan_matches_module_work_waves(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            artifact_root = root / "artifacts"
            completed = subprocess.run(
                [
                    shell,
                    "-NoLogo",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(INVOKE_SCRIPT),
                    "-Task",
                    "Run three independent XL modules with two nested output paths.",
                    "-Mode",
                    "interactive_governed",
                    "-RunId",
                    "pytest-visible-xl-module-waves",
                    "-RequestedStageStop",
                    "xl_plan",
                    "-HostDecisionJson",
                    json.dumps(
                        {"agent_skill_organization": overlapping_three_module_organization()},
                        ensure_ascii=False,
                    ),
                    "-ArtifactRoot",
                    str(artifact_root),
                ],
                cwd=REPO_ROOT,
                env=prepare_local_skill_env(root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            plan_text = next((artifact_root / "docs" / "plans").glob("*.md")).read_text(
                encoding="utf-8"
            )

        wave_lines = [line for line in plan_text.splitlines() if line.startswith("- Wave ")]
        self.assertEqual(2, len(wave_lines))
        self.assertIn("Wave 1 (`bounded_parallel`)", wave_lines[0])
        self.assertIn("`module_a`", wave_lines[0])
        self.assertIn("`module_c`", wave_lines[0])
        self.assertNotIn("`module_b`", wave_lines[0])
        self.assertIn("Wave 2 (`sequential`)", wave_lines[1])
        self.assertIn("`module_b`", wave_lines[1])
        self.assertNotIn("skeleton, intent freeze", plan_text)

    def test_agent_direct_execution_requires_an_explicit_approved_module_mode(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            artifact_root = root / "artifacts"
            completed = subprocess.run(
                [
                    shell,
                    "-NoLogo",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(INVOKE_SCRIPT),
                    "-Task",
                    "Complete one approved module directly.",
                    "-Mode",
                    "interactive_governed",
                    "-RunId",
                    "pytest-agent-direct-module",
                    "-RequestedStageStop",
                    "plan_execute",
                    "-HostDecisionJson",
                    json.dumps(
                        {"agent_skill_organization": agent_direct_organization()},
                        ensure_ascii=False,
                    ),
                    "-ArtifactRoot",
                    str(artifact_root),
                ],
                cwd=REPO_ROOT,
                env=prepare_local_skill_env(root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            module_work_plan = json.loads(
                next(artifact_root.rglob("module-work-plan.json")).read_text(encoding="utf-8")
            )
            execution_manifest = json.loads(
                next(artifact_root.rglob("execution-manifest.json")).read_text(encoding="utf-8")
            )
            handoff = json.loads(
                next(artifact_root.rglob("agent-execution-handoff.json")).read_text(encoding="utf-8")
            )

        self.assertEqual("agent_direct", module_work_plan["modules"][0]["execution_mode"])
        self.assertEqual(None, module_work_plan["work_units"][0]["skill_id"])
        self.assertFalse(Path(handoff["module_execution_path"]).exists())
        self.assertEqual([], execution_manifest["module_handoff"]["assigned_skill_ids"])

    def test_agent_direct_module_freezes_its_explicit_work_contract(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        organization = agent_direct_organization()
        organization["modules"][0].update(
            {
                "write_scope": "outputs/direct/**",
                "expected_outputs": ["outputs/direct/result.md"],
                "verification": ["Check the direct result against the frozen criteria."],
            }
        )

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            artifact_root = root / "artifacts"
            completed = subprocess.run(
                [
                    shell,
                    "-NoLogo",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(INVOKE_SCRIPT),
                    "-Task",
                    "Complete one approved module directly.",
                    "-Mode",
                    "interactive_governed",
                    "-RunId",
                    "pytest-agent-direct-explicit-contract",
                    "-RequestedStageStop",
                    "xl_plan",
                    "-HostDecisionJson",
                    json.dumps(
                        {"agent_skill_organization": organization}, ensure_ascii=False
                    ),
                    "-ArtifactRoot",
                    str(artifact_root),
                ],
                cwd=REPO_ROOT,
                env=prepare_local_skill_env(root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            module_work_plan = json.loads(
                next(artifact_root.rglob("module-work-plan.json")).read_text(encoding="utf-8")
            )

        direct_unit = module_work_plan["work_units"][0]
        self.assertEqual("outputs/direct/**", direct_unit["write_scope"])
        self.assertEqual(["outputs/direct/result.md"], direct_unit["expected_outputs"])
        self.assertEqual(
            ["Check the direct result against the frozen criteria."],
            direct_unit["verification"],
        )

    def test_agent_direct_module_requires_an_explicit_work_contract(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        cases = (
            ("write_scope", "must include write_scope"),
            ("expected_outputs", "must include expected_outputs"),
            ("verification", "must include verification"),
        )
        for missing_field, expected_error in cases:
            with self.subTest(missing_field=missing_field):
                organization = agent_direct_organization()
                organization["modules"][0].update(
                    {
                        "write_scope": "outputs/direct/**",
                        "expected_outputs": ["outputs/direct/result.md"],
                        "verification": ["Check the direct result."],
                    }
                )
                organization["modules"][0].pop(missing_field)
                with tempfile.TemporaryDirectory() as tempdir:
                    root = Path(tempdir)
                    completed = run_freeze(
                        shell,
                        artifact_root=root / "artifacts",
                        env=prepare_local_skill_env(root),
                        requested_stage_stop="xl_plan",
                        host_decision={"agent_skill_organization": organization},
                    )

                self.assertNotEqual(0, completed.returncode)
                self.assertIn(expected_error, normalized_powershell_error(completed.stderr))

    def test_agent_direct_plan_is_not_described_as_local_skill_coverage(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            artifact_root = root / "artifacts"
            completed = subprocess.run(
                [
                    shell,
                    "-NoLogo",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(INVOKE_SCRIPT),
                    "-Task",
                    "Read the local note and answer the requested facts in chat.",
                    "-Mode",
                    "interactive_governed",
                    "-RunId",
                    "pytest-agent-direct-plan-language",
                    "-RequestedStageStop",
                    "xl_plan",
                    "-HostDecisionJson",
                    json.dumps(
                        {"agent_skill_organization": agent_direct_organization()},
                        ensure_ascii=False,
                    ),
                    "-ArtifactRoot",
                    str(artifact_root),
                ],
                cwd=REPO_ROOT,
                env=prepare_local_skill_env(root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            plan_text = next((artifact_root / "docs" / "plans").glob("*.md")).read_text(
                encoding="utf-8"
            )

        self.assertIn(
            "No module is blocked by a Skill gap; `direct_module` is explicitly assigned to the current Agent without a local Skill.",
            plan_text,
        )
        self.assertNotIn("Every declared module has an Agent-selected owner", plan_text)
        self.assertNotIn("## Wave Plan", plan_text)
        self.assertNotIn("## Rollback Plan", plan_text)
        self.assertNotIn("Remove temporary artifacts", plan_text)

    def test_cleanup_briefing_leads_with_task_and_required_module_status(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            artifact_root = root / "artifacts"
            completed = subprocess.run(
                [
                    shell,
                    "-NoLogo",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(INVOKE_SCRIPT),
                    "-Task",
                    "Produce an upstream result and a reader-facing summary.",
                    "-Mode",
                    "interactive_governed",
                    "-RunId",
                    "pytest-module-cleanup-briefing",
                    "-RequestedStageStop",
                    "phase_cleanup",
                    "-HostDecisionJson",
                    json.dumps(
                        {"agent_skill_organization": agent_skill_organization()},
                        ensure_ascii=False,
                    ),
                    "-ArtifactRoot",
                    str(artifact_root),
                ],
                cwd=REPO_ROOT,
                env=prepare_local_skill_env(root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            summary = json.loads(
                next(artifact_root.rglob("runtime-summary.json")).read_text(encoding="utf-8")
            )
            briefing = Path(summary["artifacts"]["host_user_briefing"]).read_text(
                encoding="utf-8"
            )

        self.assertTrue(
            briefing.startswith("The approved plan is ready for the current Agent to execute."),
            briefing,
        )
        self.assertIn("Continue in this Agent turn.", briefing)
        self.assertIn("module-execution.json", briefing)
        self.assertIn("reader_summary", briefing)
        self.assertIn("reader-summary", briefing)

    def test_plan_execute_rejects_packets_without_agent_skill_organization(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            artifact_root = root / "artifacts"
            env = prepare_local_skill_env(root)
            freeze = run_freeze(
                shell,
                artifact_root=artifact_root,
                env=env,
                requested_stage_stop="requirement_doc",
            )
            self.assertEqual(0, freeze.returncode, freeze.stderr)
            packet_path = next(artifact_root.rglob("runtime-input-packet.json"))
            requirement_path = root / "requirement.md"
            plan_path = root / "plan.md"
            requirement_path.write_text("# Requirement\n", encoding="utf-8")
            plan_path.write_text("# Plan\n", encoding="utf-8")
            completed = subprocess.run(
                [
                    shell,
                    "-NoLogo",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(EXECUTE_SCRIPT),
                    "-Task",
                    "Use fasta-owner to parse FASTA records and explain the results for general readers.",
                    "-Mode",
                    "interactive_governed",
                    "-RunId",
                    "pytest-agent-skill-organization-execute-reject",
                    "-RequirementDocPath",
                    str(requirement_path),
                    "-ExecutionPlanPath",
                    str(plan_path),
                    "-RuntimeInputPacketPath",
                    str(packet_path),
                    "-ArtifactRoot",
                    str(artifact_root),
                ],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )

        self.assertNotEqual(0, completed.returncode)
        self.assertIn("plan_execute requires agent_skill_organization", completed.stderr)

    def test_plan_execute_uses_module_plan_even_when_retired_module_assignments_differs(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            artifact_root = root / "artifacts"
            env = prepare_local_skill_env(root)
            run_id = "pytest-agent-skill-organization-plan-source"
            freeze = subprocess.run(
                [
                    shell, "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", str(INVOKE_SCRIPT),
                    "-Task", "Use fasta-owner to parse FASTA records and explain the results for general readers.",
                    "-Mode", "interactive_governed",
                    "-RunId", run_id,
                    "-RequestedStageStop", "xl_plan",
                    "-HostDecisionJson", json.dumps({"agent_skill_organization": agent_skill_organization()}),
                    "-ArtifactRoot", str(artifact_root),
                ],
                cwd=REPO_ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
            )
            self.assertEqual(0, freeze.returncode, freeze.stderr)
            source_session = next(artifact_root.rglob("pytest-agent-skill-organization-plan-source"))
            source_summary = json.loads((source_session / "runtime-summary.json").read_text(encoding="utf-8"))
            packet_path = source_session / "runtime-input-packet.json"
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            packet["module_assignments"]["units"][0]["bound_skill"] = "fasta-owner"
            packet_path.write_text(json.dumps(packet), encoding="utf-8")
            requirement_path = Path(source_summary["artifacts"]["requirement_doc"])
            plan_path = Path(source_summary["artifacts"]["execution_plan"])
            module_work_plan_path = Path(source_summary["artifacts"]["module_work_plan"])
            completed = subprocess.run(
                [
                    shell,
                    "-NoLogo",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(EXECUTE_SCRIPT),
                    "-Task",
                    "Use fasta-owner to parse FASTA records and explain the results for general readers.",
                    "-Mode",
                    "interactive_governed",
                    "-RunId",
                    run_id,
                    "-RequirementDocPath",
                    str(requirement_path),
                    "-ExecutionPlanPath",
                    str(plan_path),
                    "-ModuleWorkPlanPath",
                    str(module_work_plan_path),
                    "-RuntimeInputPacketPath",
                    str(packet_path),
                    "-ArtifactRoot",
                    str(artifact_root),
                ],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )

            manifest = json.loads(
                (artifact_root / "outputs" / "runtime" / "vibe-sessions" / run_id / "execution-manifest.json").read_text(encoding="utf-8")
            )

        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual(["reader-summary"], manifest["module_handoff"]["assigned_skill_ids"])

    def test_plan_execute_rejects_module_plan_after_requirement_changes(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            artifact_root = root / "artifacts"
            env = prepare_local_skill_env(root)
            run_id = "pytest-module-plan-requirement-digest"
            completed = subprocess.run(
                [
                    shell,
                    "-NoLogo",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(INVOKE_SCRIPT),
                    "-Task",
                    "Produce one reader-facing module result.",
                    "-Mode",
                    "interactive_governed",
                    "-RunId",
                    run_id,
                    "-RequestedStageStop",
                    "xl_plan",
                    "-HostDecisionJson",
                    json.dumps({"agent_skill_organization": agent_skill_organization()}),
                    "-ArtifactRoot",
                    str(artifact_root),
                ],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            session_root = next(artifact_root.rglob(run_id))
            requirement_path = next(artifact_root.rglob("*.md"))
            plan_path = next((artifact_root / "docs" / "plans").glob("*.md"))
            packet_path = session_root / "runtime-input-packet.json"
            requirement_path.write_text(
                requirement_path.read_text(encoding="utf-8") + "\nChanged after approval.\n",
                encoding="utf-8",
            )
            execute = subprocess.run(
                [
                    shell,
                    "-NoLogo",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(EXECUTE_SCRIPT),
                    "-Task",
                    "Produce one reader-facing module result.",
                    "-Mode",
                    "interactive_governed",
                    "-RunId",
                    run_id,
                    "-RequirementDocPath",
                    str(requirement_path),
                    "-ExecutionPlanPath",
                    str(plan_path),
                    "-RuntimeInputPacketPath",
                    str(packet_path),
                    "-ArtifactRoot",
                    str(artifact_root),
                ],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )

        self.assertNotEqual(0, execute.returncode)
        self.assertIn("module work plan requirement digest mismatch", execute.stderr)

    def test_plan_execute_keeps_downstream_module_pending_until_dependency_passes(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            artifact_root = root / "artifacts"
            completed = subprocess.run(
                [
                    shell,
                    "-NoLogo",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(INVOKE_SCRIPT),
                    "-Task",
                    "Produce an upstream result and then summarize it.",
                    "-Mode",
                    "interactive_governed",
                    "-RunId",
                    "pytest-dependent-module-execute",
                    "-RequestedStageStop",
                    "plan_execute",
                    "-HostDecisionJson",
                    json.dumps(
                        {"agent_skill_organization": dependent_module_organization()},
                        ensure_ascii=False,
                    ),
                    "-ArtifactRoot",
                    str(artifact_root),
                ],
                cwd=REPO_ROOT,
                env=prepare_local_skill_env(root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            module_work_plan = json.loads(
                next(artifact_root.rglob("module-work-plan.json")).read_text(encoding="utf-8")
            )
            handoff = json.loads(
                next(artifact_root.rglob("agent-execution-handoff.json")).read_text(encoding="utf-8")
            )

        self.assertFalse(Path(handoff["module_execution_path"]).exists())
        planned_units = {unit["module_id"]: unit for unit in module_work_plan["work_units"]}
        self.assertEqual(
            [planned_units["module_a"]["unit_id"]],
            planned_units["module_b"]["depends_on_unit_ids"],
        )
        self.assertEqual(
            ["module_a", "module_b"],
            [unit["module_id"] for unit in handoff["units"]],
        )
        self.assertEqual(
            ["sequential", "sequential"],
            [wave["execution_mode"] for wave in handoff["waves"]],
        )

    def test_plan_execute_rejects_agent_organization_changed_after_plan(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            artifact_root = root / "artifacts"
            env = prepare_local_skill_env(root)
            run_id = "pytest-module-plan-organization-digest"
            completed = subprocess.run(
                [
                    shell,
                    "-NoLogo",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(INVOKE_SCRIPT),
                    "-Task",
                    "Produce one reader-facing module result.",
                    "-Mode",
                    "interactive_governed",
                    "-RunId",
                    run_id,
                    "-RequestedStageStop",
                    "xl_plan",
                    "-HostDecisionJson",
                    json.dumps({"agent_skill_organization": agent_skill_organization()}),
                    "-ArtifactRoot",
                    str(artifact_root),
                ],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            session_root = next(artifact_root.rglob(run_id))
            packet_path = session_root / "runtime-input-packet.json"
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            packet["agent_skill_organization"]["selected_skills"][0]["responsibility"] = "Changed after approval."
            packet_path.write_text(json.dumps(packet), encoding="utf-8")
            summary = json.loads((session_root / "runtime-summary.json").read_text(encoding="utf-8"))
            execute = subprocess.run(
                [
                    shell,
                    "-NoLogo",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(EXECUTE_SCRIPT),
                    "-Task",
                    "Produce one reader-facing module result.",
                    "-Mode",
                    "interactive_governed",
                    "-RunId",
                    run_id,
                    "-RequirementDocPath",
                    str(summary["artifacts"]["requirement_doc"]),
                    "-ExecutionPlanPath",
                    str(summary["artifacts"]["execution_plan"]),
                    "-ModuleWorkPlanPath",
                    str(summary["artifacts"]["module_work_plan"]),
                    "-RuntimeInputPacketPath",
                    str(packet_path),
                    "-ArtifactRoot",
                    str(artifact_root),
                ],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )

        self.assertNotEqual(0, execute.returncode)
        self.assertIn("module work plan organization digest mismatch", execute.stderr)


if __name__ == "__main__":
    unittest.main()
