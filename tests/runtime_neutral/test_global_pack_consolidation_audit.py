from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
VERIFICATION_CORE_SRC = REPO_ROOT / "packages" / "verification-core" / "src"
if str(VERIFICATION_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(VERIFICATION_CORE_SRC))

from vgo_verify.global_pack_consolidation_audit import (
    audit_repository,
    write_artifacts,
)


class GlobalPackConsolidationAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self._write_fixture_repo()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write(self, relative_path: str, content: str) -> None:
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")

    def _write_json(self, relative_path: str, payload: object) -> None:
        self._write(relative_path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")

    def _write_skill(
        self,
        skill_id: str,
        description: str,
        body: str,
        *,
        scripts: bool = False,
        references: bool = False,
    ) -> None:
        self._write(
            f"bundled/skills/{skill_id}/SKILL.md",
            "---\n"
            f"name: {skill_id}\n"
            f"description: {description}\n"
            "---\n\n"
            f"# {skill_id}\n\n"
            f"{body}\n",
        )
        if scripts:
            self._write(f"bundled/skills/{skill_id}/scripts/run.py", "print('ok')\n")
        if references:
            self._write(f"bundled/skills/{skill_id}/references/guide.md", "# Guide\n\nGuidance.\n")

    def _write_fixture_repo(self) -> None:
        self._write_json(
            "config/pack-manifest.json",
            {
                "packs": [
                    {
                        "id": "research-design",
                        "skill_candidates": [
                            "designing-experiments",
                            "hypothesis-generation",
                            "hypothesis-testing",
                            "performing-causal-analysis",
                            "performing-regression-analysis",
                            "research-lookup",
                            "report-generator",
                        ],
                        "route_authority_candidates": [
                            "designing-experiments",
                            "hypothesis-generation",
                            "hypothesis-testing",
                            "performing-causal-analysis",
                            "performing-regression-analysis",
                            "research-lookup",
                        ],
                        "stage_assistant_candidates": ["report-generator"],
                        "defaults_by_task": {
                            "planning": "designing-experiments",
                            "research": "research-lookup",
                        },
                    },
                    {
                        "id": "code-quality",
                        "skill_candidates": [
                            "code-review",
                            "code-reviewer",
                            "reviewing-code",
                            "systematic-debugging",
                            "debugging-strategies",
                            "error-resolver",
                        ],
                        "defaults_by_task": {
                            "debug": "systematic-debugging",
                            "review": "code-reviewer",
                        },
                    },
                    {
                        "id": "data-ml",
                        "skill_candidates": [
                            "scikit-learn",
                            "ml-data-leakage-guard",
                            "preprocessing-data-with-automated-pipelines",
                        ],
                        "route_authority_candidates": [
                            "scikit-learn",
                            "ml-data-leakage-guard",
                        ],
                        "stage_assistant_candidates": [
                            "preprocessing-data-with-automated-pipelines",
                        ],
                        "defaults_by_task": {
                            "coding": "scikit-learn",
                            "review": "ml-data-leakage-guard",
                        },
                    },
                ]
            },
        )
        self._write_json(
            "config/skill-keyword-index.json",
            {
                "skills": {
                    "code-review": {"keywords": ["code review", "review code", "security review"]},
                    "code-reviewer": {"keywords": ["code review", "review code", "security review"]},
                    "reviewing-code": {"keywords": ["code review", "review code"]},
                    "systematic-debugging": {"keywords": ["debug", "root cause", "failing test"]},
                    "debugging-strategies": {"keywords": ["debug", "root cause"]},
                    "error-resolver": {"keywords": ["error", "fix failure"]},
                    "research-lookup": {"keywords": ["research", "literature", "lookup"]},
                    "designing-experiments": {"keywords": ["experiment design", "research design"]},
                }
            },
        )
        self._write_json(
            "config/skill-routing-rules.json",
            {
                "skills": {
                    "research-lookup": {"positive_keywords": ["research", "lookup"], "negative_keywords": []},
                    "designing-experiments": {"positive_keywords": ["experiment design"], "negative_keywords": []},
                    "code-review": {"positive_keywords": ["code review"], "negative_keywords": []},
                    "code-reviewer": {"positive_keywords": ["code review"], "negative_keywords": []},
                    "systematic-debugging": {"positive_keywords": ["debug"], "negative_keywords": []},
                }
            },
        )
        for skill in [
            "designing-experiments",
            "hypothesis-generation",
            "hypothesis-testing",
            "performing-causal-analysis",
            "performing-regression-analysis",
            "research-lookup",
            "report-generator",
            "code-review",
            "code-reviewer",
            "reviewing-code",
            "systematic-debugging",
            "debugging-strategies",
            "error-resolver",
            "scikit-learn",
            "ml-data-leakage-guard",
            "preprocessing-data-with-automated-pipelines",
        ]:
            self._write_skill(
                skill,
                f"{skill} skill for testing pack consolidation audit.",
                f"Use {skill} for its named workflow. This fixture keeps content short.",
                scripts=skill in {"performing-regression-analysis", "systematic-debugging"},
                references=skill in {"research-lookup", "scikit-learn"},
            )

    def test_audit_ranks_high_risk_packs(self) -> None:
        artifact = audit_repository(self.root)
        rows = {row.pack_id: row for row in artifact.rows}

        self.assertEqual(3, artifact.summary["pack_count"])
        self.assertEqual("P0", rows["research-design"].priority)
        self.assertGreater(rows["research-design"].risk_score, rows["data-ml"].risk_score)
        self.assertGreaterEqual(rows["research-design"].route_authority_count, 6)
        self.assertTrue(rows["research-design"].has_explicit_role_split)

        self.assertEqual("P0", rows["code-quality"].priority)
        self.assertFalse(rows["code-quality"].has_explicit_role_split)
        self.assertGreater(rows["code-quality"].suspected_overlap_count, 0)
        self.assertEqual(2, artifact.summary["p0_count"])

    def test_artifact_writer_outputs_json_csv_and_markdown(self) -> None:
        artifact = audit_repository(self.root)
        written = write_artifacts(self.root, artifact, self.root / "outputs" / "skills-audit")

        self.assertTrue(written["json"].exists())
        self.assertTrue(written["csv"].exists())
        self.assertTrue(written["markdown"].exists())

        csv_text = written["csv"].read_text(encoding="utf-8")
        self.assertIn("pack_id,skill_candidate_count,route_authority_count", csv_text)
        self.assertIn("research-design", csv_text)

        markdown_text = written["markdown"].read_text(encoding="utf-8")
        self.assertIn("# Global Pack Consolidation Audit", markdown_text)
        self.assertIn("## P0", markdown_text)
        self.assertIn("research-design", markdown_text)

    def test_audit_and_writer_do_not_modify_live_config(self) -> None:
        config_paths = [
            self.root / "config" / "pack-manifest.json",
            self.root / "config" / "skill-keyword-index.json",
            self.root / "config" / "skill-routing-rules.json",
        ]
        before = {path: path.read_text(encoding="utf-8") for path in config_paths}

        artifact = audit_repository(self.root)
        write_artifacts(self.root, artifact, self.root / "outputs" / "skills-audit")

        after = {path: path.read_text(encoding="utf-8") for path in config_paths}
        self.assertEqual(before, after)

    def test_negative_keywords_do_not_raise_overlap_risk(self) -> None:
        before = audit_repository(self.root)
        before_rows = {row.pack_id: row for row in before.rows}

        rules_path = self.root / "config" / "skill-routing-rules.json"
        rules = json.loads(rules_path.read_text(encoding="utf-8"))
        rules["skills"]["code-review"]["negative_keywords"] = ["shared negative only"]
        rules["skills"]["code-reviewer"]["negative_keywords"] = ["shared negative only"]
        rules_path.write_text(json.dumps(rules, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        after = audit_repository(self.root)
        after_rows = {row.pack_id: row for row in after.rows}

        self.assertEqual(
            before_rows["code-quality"].broad_keyword_count,
            after_rows["code-quality"].broad_keyword_count,
        )

    def test_audit_reads_bom_encoded_json_config(self) -> None:
        pack_manifest_path = self.root / "config" / "pack-manifest.json"
        original = pack_manifest_path.read_text(encoding="utf-8")
        pack_manifest_path.write_text(original, encoding="utf-8-sig", newline="\n")

        artifact = audit_repository(self.root)

        self.assertEqual(3, artifact.summary["pack_count"])
        self.assertIn("research-design", {row.pack_id for row in artifact.rows})

    def test_real_pack_manifest_uses_skill_candidates_without_legacy_fields(self) -> None:
        manifest = json.loads((REPO_ROOT / "config" / "pack-manifest.json").read_text(encoding="utf-8-sig"))
        missing_skill_candidates: list[str] = []
        packs_with_legacy_fields: list[str] = []

        for pack in manifest["packs"]:
            if not pack.get("skill_candidates"):
                missing_skill_candidates.append(pack["id"])
            if "route_authority_candidates" in pack or "stage_assistant_candidates" in pack:
                packs_with_legacy_fields.append(pack["id"])

        self.assertEqual([], missing_skill_candidates)
        self.assertEqual([], packs_with_legacy_fields)


if __name__ == "__main__":
    unittest.main()
