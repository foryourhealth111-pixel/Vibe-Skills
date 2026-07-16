from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

from tests.runtime_neutral.test_l_xl_agent_execution_handoff import agent_skill_organization, run_runtime


REQUIREMENT_TASK = "请阅读一篇论文，并给我写一个面向普通读者的中文总结报告。"
PLAN_TASK = "请先冻结需求，再给我一个清晰的执行计划，用来完成这次交付。"
SOURCE_DOCUMENT_ANALYSIS_TASK = (
    "Search the provided PDF and analyze the stated benchmark results. "
    "Answer three comparison questions in chat."
)
PURE_RETRIEVAL_NEGATIVE_TASK = (
    "请只检索并分析 Python 3.13 free-threaded build 的官方现状、限制和适用场景，"
    "最终仅在对话中给出简洁中文结论和官方链接。不要写代码，不要做 UI、Word、PDF 或文档排版。"
)
NON_UI_CODE_TASK = (
    "Diagnose and repair one isolated standard-library Python fixture through its CLI and public function. "
    "Use TDD, but do not build or inspect any UI, responsive layout, Word document, or rendered artifact."
)


def retrieval_agent_organization(workflow_level: str) -> dict[str, object]:
    return {
        "schema_version": "agent_skill_organization_v1",
        "derived_by": "agent",
        "workflow_level": workflow_level,
        "modules": [
            {
                "module_id": "local_retrieval",
                "goal": "Read the approved sources and answer in chat.",
                "candidate_skill_ids": [],
                "required": True,
                "depends_on": [],
                "execution_mode": "agent_direct",
                "write_scope": "chat:final_response",
                "expected_outputs": ["A concise source-grounded chat answer."],
                "verification": ["Check every conclusion against the approved sources."],
                "acceptance_criteria": [
                    {
                        "criterion_id": "source-grounded-chat-answer",
                        "description": "The chat answer is grounded in the approved sources.",
                        "verification_mode": "automated",
                    }
                ],
            }
        ],
        "selected_skills": [],
        "uncovered_modules": [],
        "workflow_level_contract": {
            "L": "Run the direct retrieval work serially.",
            "XL": "Use bounded waves only when independent modules justify them.",
        },
    }

REQUIREMENT_MACHINE_ONLY_HEADING_FRAGMENTS = [
    "Runtime Input Truth",
    "Skill Usage",
    "Skill Execution Decision",
    "Selected Skill",
    "Skill Routing And Usage Evidence",
    "Memory Context",
]

PLAN_MACHINE_ONLY_HEADING_FRAGMENTS = [
    "Anti-Proxy-Goal-Drift",
    "Skill Execution Decision",
    "Skill Routing And Usage Evidence",
    "Memory Context",
    "Binary Skill Usage Plan",
]

BRIEFING_RUNTIME_CONTROL_FRAGMENTS = [
    "Bounded governed stop reached. Return control to the user now.",
    "--continue-from-run-id",
    "--bounded-reentry-token",
    "manual execution outside governed re-entry is forbidden",
    "Do not continue in the same assistant turn",
    "source run id:",
]


def extract_h2_headings(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.startswith("## ")]


def find_heading_leaks(headings: list[str], fragments: list[str]) -> list[str]:
    return [heading for heading in headings if any(fragment in heading for fragment in fragments)]


class DocumentChainLayeringContractTests(unittest.TestCase):
    def _load_requirement_stop(self, task: str = REQUIREMENT_TASK) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(
                task=task,
                artifact_root=Path(tempdir),
                governance_scope="root",
                entry_intent_id="vibe",
                requested_stage_stop="requirement_doc",
            )
            requirement_doc = Path(payload["summary"]["artifacts"]["requirement_doc"]).read_text(encoding="utf-8")
            return {
                "payload": payload,
                "requirement_doc": requirement_doc,
                "host_user_briefing": payload["summary"]["host_user_briefing"]["rendered_text"],
            }

    def _load_plan_stop(self, task: str = PLAN_TASK) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(
                task=task,
                artifact_root=Path(tempdir),
                governance_scope="root",
                entry_intent_id="vibe",
                requested_stage_stop="xl_plan",
                requested_grade_floor="XL",
                agent_organization=agent_skill_organization([], workflow_level="XL"),
            )
            execution_plan = Path(payload["summary"]["artifacts"]["execution_plan"]).read_text(encoding="utf-8")
            return {
                "payload": payload,
                "execution_plan": execution_plan,
            }

    def _load_plan_stop_with_level(
        self,
        task: str,
        *,
        workflow_level: str,
        organization: dict[str, object] | None = None,
    ) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(
                task=task,
                artifact_root=Path(tempdir),
                governance_scope="root",
                entry_intent_id="vibe",
                requested_stage_stop="xl_plan",
                requested_grade_floor=workflow_level,
                agent_organization=organization
                or agent_skill_organization([], workflow_level=workflow_level),
            )
            return {
                "payload": payload,
                "execution_plan": Path(payload["summary"]["artifacts"]["execution_plan"]).read_text(
                    encoding="utf-8"
                ),
            }

    def test_requirement_doc_default_surface_omits_machine_only_sections(self) -> None:
        result = self._load_requirement_stop()
        requirement_doc = result["requirement_doc"]

        leaked_headings = find_heading_leaks(
            extract_h2_headings(requirement_doc),
            REQUIREMENT_MACHINE_ONLY_HEADING_FRAGMENTS,
        )

        self.assertEqual(
            [],
            leaked_headings,
            "Default requirement docs should stay user-facing. "
            f"Unexpected machine/audit sections leaked into the document: {leaked_headings}",
        )

    def test_requirement_doc_omits_empty_placeholder_sections(self) -> None:
        result = self._load_requirement_stop()
        requirement_doc = result["requirement_doc"]

        placeholder_lines = [
            line.strip()
            for line in requirement_doc.splitlines()
            if re.match(r"^No .+ were frozen for this run\.$", line.strip())
        ]

        self.assertEqual(
            [],
            placeholder_lines,
            "User-facing requirement docs should omit empty sections instead of rendering placeholder filler lines.",
        )

    def test_requirement_doc_heading_budget_stays_human_sized(self) -> None:
        result = self._load_requirement_stop()
        requirement_doc = result["requirement_doc"]

        headings = extract_h2_headings(requirement_doc)

        self.assertLessEqual(
            len(headings),
            12,
            "A default requirement doc should read like a short brief, not a merged governance ledger.",
        )

    def test_source_document_analysis_does_not_inherit_delivery_requirements(self) -> None:
        result = self._load_requirement_stop(task=SOURCE_DOCUMENT_ANALYSIS_TASK)
        requirement_doc = result["requirement_doc"]
        forbidden_fragments = [
            "Governed implementation artifacts",
            "before implementation",
            "TDD",
            "## Baseline UI Quality Dimensions",
            "Responsive Stability",
            "Word document",
            "Open, render, or export the touched document artifact",
            "## Artifact Review Requirements",
            "## Baseline Document Quality Dimensions",
        ]
        requirement_doc_folded = requirement_doc.casefold()
        leaked_fragments = [
            fragment for fragment in forbidden_fragments if fragment.casefold() in requirement_doc_folded
        ]

        self.assertEqual(
            [],
            leaked_fragments,
            "Reading a source document for an in-chat analysis must not turn into implementation, TDD, UI, "
            f"responsive, Word/rendering, or formal-document delivery work: {leaked_fragments}",
        )

    def test_pure_retrieval_defaults_to_l_without_code_ui_or_document_delivery(self) -> None:
        result = self._load_requirement_stop(task=PURE_RETRIEVAL_NEGATIVE_TASK)
        requirement_doc = result["requirement_doc"]

        self.assertIn("Recommended level: L", requirement_doc)
        for forbidden_fragment in (
            "Governed implementation artifacts",
            "before implementation",
            "TDD mode:",
            "## Baseline UI Quality Dimensions",
            "Responsive Stability",
            "## Artifact Review Requirements",
            "## Baseline Document Quality Dimensions",
            "Open the primary user-facing flow",
        ):
            with self.subTest(forbidden_fragment=forbidden_fragment):
                self.assertNotIn(forbidden_fragment, requirement_doc)

    def test_non_ui_code_task_requires_tdd_without_ui_or_document_checks(self) -> None:
        result = self._load_requirement_stop(task=NON_UI_CODE_TASK)
        requirement_doc = result["requirement_doc"]

        self.assertIn("Recommended level: L", requirement_doc)
        self.assertIn("TDD mode: required", requirement_doc)
        self.assertIn("Record failing-first evidence", requirement_doc)
        for forbidden_fragment in (
            "## Baseline UI Quality Dimensions",
            "Responsive Stability",
            "## Artifact Review Requirements",
            "## Baseline Document Quality Dimensions",
            "Open the primary user-facing flow",
            "Open, render, or export the touched document artifact",
        ):
            with self.subTest(forbidden_fragment=forbidden_fragment):
                self.assertNotIn(forbidden_fragment, requirement_doc)

    def test_pure_retrieval_plan_uses_task_work_not_implementation_waves(self) -> None:
        result = self._load_plan_stop_with_level(
            PURE_RETRIEVAL_NEGATIVE_TASK,
            workflow_level="L",
            organization=retrieval_agent_organization("L"),
        )
        execution_plan = result["execution_plan"]

        for forbidden_fragment in (
            "implementation preparation",
            "implementation and targeted verification",
            "direct implementation",
            "Code Task TDD Evidence Plan",
            "Baseline UI Quality Mapping",
            "Baseline Document Quality Mapping",
        ):
            with self.subTest(forbidden_fragment=forbidden_fragment):
                self.assertNotIn(forbidden_fragment, execution_plan)

        self.assertIn("Execution mode: `agent_direct`", execution_plan)
        self.assertIn("Work: current Agent as `owner`", execution_plan)
        self.assertNotIn("## Wave Plan", execution_plan)

    def test_non_ui_code_plan_keeps_tdd_without_ui_or_document_mappings(self) -> None:
        result = self._load_plan_stop_with_level(NON_UI_CODE_TASK, workflow_level="L")
        execution_plan = result["execution_plan"]

        self.assertIn("Code Task TDD Evidence Plan", execution_plan)
        self.assertNotIn("Baseline UI Quality Mapping", execution_plan)
        self.assertNotIn("Baseline Document Quality Mapping", execution_plan)

    def test_requirement_stop_briefing_omits_reentry_credentials_and_runtime_control_lines(self) -> None:
        result = self._load_requirement_stop(task="Clarify the project goal before any implementation starts.")
        briefing = result["host_user_briefing"]

        leaked_fragments = [fragment for fragment in BRIEFING_RUNTIME_CONTROL_FRAGMENTS if fragment in briefing]

        self.assertEqual(
            [],
            leaked_fragments,
            "Requirement-stop user briefings should explain the choice, not expose re-entry credentials or control-plane instructions.",
        )

    def test_execution_plan_default_surface_omits_machine_only_sections(self) -> None:
        result = self._load_plan_stop()
        execution_plan = result["execution_plan"]

        leaked_headings = find_heading_leaks(
            extract_h2_headings(execution_plan),
            PLAN_MACHINE_ONLY_HEADING_FRAGMENTS,
        )
        leaked_control_lines = [
            line.strip()
            for line in execution_plan.splitlines()
            if line.strip().startswith("- Governance scope:")
            or line.strip().startswith("- Root run id:")
            or line.strip().startswith("- Entry intent:")
            or line.strip().startswith("- Requested stop stage:")
            or line.strip().startswith("- Requested grade floor:")
        ]

        self.assertEqual(
            [],
            leaked_headings + leaked_control_lines,
            "A user-facing execution plan should not expose runtime-control or audit-only details by default.",
        )
