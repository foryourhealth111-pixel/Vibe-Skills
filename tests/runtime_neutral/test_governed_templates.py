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
