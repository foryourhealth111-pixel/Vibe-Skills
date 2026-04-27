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

from vgo_verify.ml_skills_pruning_audit import (
    audit_data_ml_problem_map,
    audit_repository,
    write_artifacts,
    write_data_ml_problem_artifacts,
)


class MlSkillsPruningAuditTests(unittest.TestCase):
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
            self._write(f"bundled/skills/{skill_id}/references/guide.md", "# Guide\n\nConcrete guidance.\n")

    def _write_fixture_repo(self) -> None:
        self._write_json(
            "config/pack-manifest.json",
            {
                "packs": [
                    {
                        "id": "data-ml",
                        "skill_candidates": [
                            "scikit-learn",
                            "anomaly-detector",
                            "training-machine-learning-models",
                            "shap",
                        ],
                        "route_authority_candidates": [
                            "scikit-learn",
                            "training-machine-learning-models",
                        ],
                        "stage_assistant_candidates": [
                            "anomaly-detector",
                        ],
                        "defaults_by_task": {
                            "planning": "scikit-learn",
                            "coding": "scikit-learn",
                        },
                    },
                    {
                        "id": "ai-llm",
                        "skill_candidates": [
                            "transformers",
                        ],
                        "defaults_by_task": {
                            "coding": "transformers",
                        },
                    },
                ]
            },
        )
        self._write_json(
            "config/skill-keyword-index.json",
            {
                "skills": {
                    "scikit-learn": {"keywords": ["machine learning", "sklearn", "classification"]},
                    "anomaly-detector": {"keywords": ["anomaly detection", "outlier", "machine learning"]},
                    "training-machine-learning-models": {"keywords": ["train model", "machine learning"]},
                    "shap": {"keywords": ["shap", "feature importance", "explain model"]},
                    "transformers": {"keywords": ["transformers", "fine tune model", "deep learning"]},
                }
            },
        )
        self._write_json(
            "config/skill-routing-rules.json",
            {
                "skills": {
                    "scikit-learn": {
                        "task_allow": ["coding", "research"],
                        "positive_keywords": ["sklearn", "classification"],
                        "negative_keywords": [],
                        "canonical_for_task": ["traditional_ml"],
                    },
                    "anomaly-detector": {
                        "task_allow": ["coding"],
                        "positive_keywords": ["anomaly"],
                        "negative_keywords": [],
                        "canonical_for_task": [],
                    },
                    "training-machine-learning-models": {
                        "task_allow": ["coding"],
                        "positive_keywords": ["train model"],
                        "negative_keywords": [],
                        "canonical_for_task": [],
                    },
                    "shap": {
                        "task_allow": ["review"],
                        "positive_keywords": ["shap"],
                        "negative_keywords": [],
                        "canonical_for_task": ["explainability"],
                    },
                    "transformers": {
                        "task_allow": ["coding"],
                        "positive_keywords": ["transformers"],
                        "negative_keywords": [],
                        "canonical_for_task": ["deep_learning"],
                    },
                }
            },
        )
        self._write_skill(
            "scikit-learn",
            "Traditional machine-learning owner for sklearn models.",
            "\n".join(
                [
                    "Use this for scikit-learn classification, regression, pipelines, cross validation, metrics, and reproducible model training.",
                    "Do not use it as the owner for deep-learning framework internals.",
                    "It should absorb generic training and evaluation templates when those templates add no independent workflow.",
                ]
                * 8
            ),
            references=True,
        )
        self._write_skill(
            "anomaly-detector",
            "Generic anomaly detector helper.",
            "Use this skill for anomaly detection. Pick a method, run it, and report anomalies.",
        )
        self._write_skill(
            "training-machine-learning-models",
            "Generic ML training helper.",
            "Use this skill for training machine-learning models. Split data, train, evaluate, and report results.",
        )
        self._write_skill(
            "shap",
            "SHAP explainability tool skill.",
            "Use this when the request explicitly needs SHAP values or model explanations.",
        )
        self._write_skill(
            "transformers",
            "Transformers deep-learning framework skill.",
            "Use this for transformer model fine-tuning, tokenizers, inference, and deep-learning workflows.",
            scripts=True,
        )

    def test_audit_marks_generic_template_ml_helpers_as_delete_candidates(self) -> None:
        artifact = audit_repository(self.root)
        rows = {row.skill_id: row for row in artifact.rows}

        self.assertEqual("delete", rows["anomaly-detector"].recommended_action)
        self.assertEqual("scikit-learn", rows["anomaly-detector"].replacement_skill)
        self.assertLessEqual(rows["anomaly-detector"].quality_score, 2)
        self.assertGreaterEqual(rows["anomaly-detector"].duplication_score, 4)
        self.assertEqual("low", rows["anomaly-detector"].risk_level)

        self.assertEqual("delete", rows["training-machine-learning-models"].recommended_action)
        self.assertEqual("scikit-learn", rows["training-machine-learning-models"].replacement_skill)

    def test_audit_keeps_or_defers_owner_and_specialist_skills(self) -> None:
        artifact = audit_repository(self.root)
        rows = {row.skill_id: row for row in artifact.rows}

        self.assertEqual("keep", rows["scikit-learn"].recommended_action)
        self.assertEqual("主专家", rows["scikit-learn"].category)
        self.assertGreaterEqual(rows["scikit-learn"].quality_score, 4)

        self.assertEqual("defer-specialist-review", rows["shap"].recommended_action)
        self.assertEqual("工具型", rows["shap"].category)
        self.assertEqual("medium", rows["shap"].risk_level)

        self.assertEqual("defer-specialist-review", rows["transformers"].recommended_action)
        self.assertEqual("工具型", rows["transformers"].category)
        self.assertTrue(rows["transformers"].has_scripts)

    def test_artifact_writer_outputs_json_csv_and_markdown(self) -> None:
        artifact = audit_repository(self.root)
        output_dir = self.root / "outputs" / "skills-audit"
        written = write_artifacts(self.root, artifact, output_dir)

        self.assertTrue(written["json"].exists())
        self.assertTrue(written["csv"].exists())
        self.assertTrue(written["markdown"].exists())

        csv_text = written["csv"].read_text(encoding="utf-8")
        self.assertIn("skill_id,category,current_pack,current_role", csv_text)
        self.assertIn("anomaly-detector", csv_text)

        markdown_text = written["markdown"].read_text(encoding="utf-8")
        self.assertIn("# ML Skills Pruning Audit", markdown_text)
        self.assertIn("## 删除候选", markdown_text)
        self.assertIn("anomaly-detector", markdown_text)

    def test_data_ml_problem_map_marks_targets_for_consolidation(self) -> None:
        artifact = audit_data_ml_problem_map(self.root)
        rows = {row.skill_id: row for row in artifact.rows}

        self.assertEqual("keep", rows["scikit-learn"].target_role)
        self.assertEqual("ml_tabular_modeling", rows["scikit-learn"].primary_problem_id)
        self.assertEqual("keep", rows["shap"].target_role)
        self.assertEqual("ml_explainability", rows["shap"].primary_problem_id)

        self.assertEqual("merge-delete-after-migration", rows["training-machine-learning-models"].target_role)
        self.assertEqual("scikit-learn", rows["training-machine-learning-models"].target_owner)
        self.assertTrue(rows["training-machine-learning-models"].delete_allowed_after_migration)

    def test_problem_artifact_writer_outputs_json_csv_and_markdown(self) -> None:
        artifact = audit_data_ml_problem_map(self.root)
        output_dir = self.root / "outputs" / "skills-audit"
        written = write_data_ml_problem_artifacts(self.root, artifact, output_dir)

        self.assertTrue(written["json"].exists())
        self.assertTrue(written["csv"].exists())
        self.assertTrue(written["markdown"].exists())
        self.assertIn("data-ml-problem-map", written["json"].name)

        csv_text = written["csv"].read_text(encoding="utf-8")
        self.assertIn("skill_id,problem_ids,primary_problem_id", csv_text)
        self.assertIn("training-machine-learning-models", csv_text)

        markdown_text = written["markdown"].read_text(encoding="utf-8")
        self.assertIn("# Data-ML Problem-First Consolidation", markdown_text)
        self.assertIn("## 目标保留", markdown_text)

    def test_runtime_neutral_wrapper_exposes_main(self) -> None:
        wrapper = REPO_ROOT / "scripts" / "verify" / "runtime_neutral" / "ml_skills_pruning_audit.py"
        text = wrapper.read_text(encoding="utf-8")
        self.assertIn("from vgo_verify.ml_skills_pruning_audit import", text)
        self.assertIn("raise SystemExit(main())", text)


if __name__ == "__main__":
    unittest.main()
