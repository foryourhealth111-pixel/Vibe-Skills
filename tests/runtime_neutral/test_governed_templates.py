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
        headings = _load_section_headings(REPO_ROOT / "templates" / "requirements" / "governed-requirement-template.md")

        for section in policy["required_sections"]:
            self.assertIn(section, headings)

        self.assertIn("Artifact Review Requirements", headings)
        self.assertIn("Code Task TDD Evidence Requirements", headings)
        self.assertIn("Code Task TDD Exceptions", headings)
        self.assertIn("Baseline Document Quality Dimensions", headings)
        self.assertIn("Baseline UI Quality Dimensions", headings)
        self.assertIn("Task-Specific Acceptance Extensions", headings)
        self.assertIn("Research Augmentation Sources", headings)

    def test_plan_template_covers_policy_sections_and_artifact_planning_fields(self) -> None:
        policy = json.loads((REPO_ROOT / "config" / "plan-execution-policy.json").read_text(encoding="utf-8"))
        headings = _load_section_headings(REPO_ROOT / "templates" / "plans" / "governed-execution-plan-template.md")

        for section in policy["required_plan_sections"]:
            self.assertIn(section, headings)

        self.assertIn("Artifact Review Strategy", headings)
        self.assertIn("Code Task TDD Evidence Plan", headings)
        self.assertIn("Baseline Document Quality Mapping", headings)
        self.assertIn("Baseline UI Quality Mapping", headings)
        self.assertIn("Task-Specific Acceptance Mapping", headings)
        self.assertIn("Research Augmentation Plan", headings)

    def test_write_xl_plan_script_emits_artifact_planning_sections(self) -> None:
        script_text = (REPO_ROOT / "scripts" / "runtime" / "Write-XlPlan.ps1").read_text(encoding="utf-8")

        self.assertIn("## Artifact Review Strategy", script_text)
        self.assertIn("## Code Task TDD Evidence Plan", script_text)
        self.assertIn("## Baseline Document Quality Mapping", script_text)
        self.assertIn("## Baseline UI Quality Mapping", script_text)
        self.assertIn("## Task-Specific Acceptance Mapping", script_text)
        self.assertIn("## Research Augmentation Plan", script_text)


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

    def test_frozen_specialist_decision_requirement_doc_defines_specialist_decision_section(self) -> None:
        headings = _load_section_headings(
            REPO_ROOT / "docs" / "requirements" / "2026-04-15-vibe-specialist-decision-fallback.md"
        )

        self.assertIn("Specialist Decision", headings)
