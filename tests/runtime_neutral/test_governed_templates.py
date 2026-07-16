from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_section_headings(path: Path) -> set[str]:
    headings: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            headings.add(stripped[3:].strip())
    return headings


class GovernedTemplateTests(unittest.TestCase):
    def test_requirement_template_covers_policy_sections_and_artifact_fields(self) -> None:
        policy = json.loads((REPO_ROOT / "config" / "requirement-doc-policy.json").read_text(encoding="utf-8"))
        template_path = REPO_ROOT / "templates" / "requirements" / "governed-requirement-template.md"
        headings = _load_section_headings(template_path)

        for section in policy["required_sections"]:
            self.assertIn(section, headings)

        for optional_heading in (
            "Artifact Review Requirements",
            "Code Task TDD Evidence Requirements",
            "Code Task TDD Exceptions",
            "Baseline Document Quality Dimensions",
            "Baseline UI Quality Dimensions",
            "Task-Specific Acceptance Extensions",
            "Research Augmentation Sources",
        ):
            self.assertNotIn(optional_heading, headings)
        self.assertIn(
            "Task-specific sections are emitted only when the frozen requirement makes them applicable.",
            template_path.read_text(encoding="utf-8"),
        )

    def test_plan_template_covers_policy_sections_and_artifact_planning_fields(self) -> None:
        policy = json.loads((REPO_ROOT / "config" / "plan-execution-policy.json").read_text(encoding="utf-8"))
        template_path = REPO_ROOT / "templates" / "plans" / "governed-execution-plan-template.md"
        headings = _load_section_headings(template_path)

        for section in policy["required_plan_sections"]:
            self.assertIn(section, headings)

        for optional_heading in (
            "Artifact Review Strategy",
            "Code Task TDD Evidence Plan",
            "Baseline Document Quality Mapping",
            "Baseline UI Quality Mapping",
            "Task-Specific Acceptance Mapping",
            "Research Augmentation Plan",
        ):
            self.assertNotIn(optional_heading, headings)
        self.assertIn(
            "Task-specific sections are emitted only when the frozen requirement makes them applicable.",
            template_path.read_text(encoding="utf-8"),
        )

    def test_write_xl_plan_script_emits_artifact_planning_sections(self) -> None:
        script_text = (REPO_ROOT / "scripts" / "runtime" / "Write-XlPlan.ps1").read_text(encoding="utf-8")

        self.assertIn("-Heading 'Artifact Review Strategy'", script_text)
        self.assertIn("-Heading 'Code Task TDD Evidence Plan'", script_text)
        self.assertIn("-Heading 'Baseline Document Quality Mapping'", script_text)
        self.assertIn("-Heading 'Baseline UI Quality Mapping'", script_text)
        self.assertIn("-Heading 'Task-Specific Acceptance Mapping'", script_text)
        self.assertIn("-Heading 'Research Augmentation Plan'", script_text)


    def test_project_delivery_contract_requires_artifact_and_tdd_coverage_fields(self) -> None:
        contract = json.loads(
            (REPO_ROOT / "config" / "project-delivery-acceptance-contract.json").read_text(encoding="utf-8")
        )
        must_report_fields = set((contract.get("report_requirements") or {}).get("must_report_fields") or [])

        self.assertIn("artifact_review_coverage", must_report_fields)
        self.assertIn("tdd_evidence_coverage", must_report_fields)

    def test_project_delivery_contract_id_suffix_tracks_declared_version(self) -> None:
        contract = json.loads(
            (REPO_ROOT / "config" / "project-delivery-acceptance-contract.json").read_text(encoding="utf-8")
        )

        version = int(contract.get("version") or 0)
        self.assertTrue(str(contract.get("contract_id") or "").endswith(f"-v{version}"))
