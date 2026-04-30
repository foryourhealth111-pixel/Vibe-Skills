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

from vgo_verify.code_quality_pack_consolidation_audit import (
    audit_code_quality_problem_map,
    write_code_quality_problem_artifacts,
)


class CodeQualityPackConsolidationAuditTests(unittest.TestCase):
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
        assets: bool = False,
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
        if assets:
            self._write(f"bundled/skills/{skill_id}/assets/example.txt", "asset\n")

    def _write_fixture_repo(self) -> None:
        candidates = [
            "build-error-resolver",
            "code-review",
            "code-reviewer",
            "code-review-excellence",
            "debugging-strategies",
            "deslop",
            "error-resolver",
            "generating-test-reports",
            "receiving-code-review",
            "requesting-code-review",
            "reviewing-code",
            "security-reviewer",
            "systematic-debugging",
            "tdd-guide",
            "verification-before-completion",
            "windows-hook-debugging",
        ]
        self._write_json(
            "config/pack-manifest.json",
            {
                "packs": [
                    {
                        "id": "code-quality",
                        "skill_candidates": candidates,
                        "defaults_by_task": {
                            "debug": "systematic-debugging",
                            "coding": "tdd-guide",
                            "review": "code-reviewer",
                        },
                    }
                ]
            },
        )
        self._write_json("config/skill-keyword-index.json", {"skills": {}})
        self._write_json("config/skill-routing-rules.json", {"skills": {}})
        for skill in candidates:
            self._write_skill(
                skill,
                f"{skill} fixture.",
                f"Use {skill} for its named workflow.",
                scripts=skill in {"code-review", "code-reviewer"},
                references=skill in {"code-review", "error-resolver"},
                assets=skill == "error-resolver",
            )

    def test_problem_map_assigns_target_roles(self) -> None:
        artifact = audit_code_quality_problem_map(self.root)
        rows = {row.skill_id: row for row in artifact.rows}

        self.assertEqual("keep-route-authority", rows["code-reviewer"].target_role)
        self.assertEqual("code_review_general", rows["code-reviewer"].primary_problem_id)
        self.assertEqual("keep-route-authority", rows["systematic-debugging"].target_role)
        self.assertEqual("debug_root_cause", rows["systematic-debugging"].primary_problem_id)
        self.assertEqual("keep-route-authority", rows["receiving-code-review"].target_role)
        self.assertEqual("review_feedback_handling", rows["receiving-code-review"].primary_problem_id)
        self.assertEqual("keep-route-authority", rows["requesting-code-review"].target_role)
        self.assertEqual("review_request_preparation", rows["requesting-code-review"].primary_problem_id)

    def test_problem_map_marks_safe_delete_and_move_out(self) -> None:
        artifact = audit_code_quality_problem_map(self.root)
        rows = {row.skill_id: row for row in artifact.rows}

        self.assertEqual("delete", rows["reviewing-code"].target_role)
        self.assertTrue(rows["reviewing-code"].delete_allowed_now)
        self.assertEqual("code-reviewer", rows["reviewing-code"].target_owner)

        self.assertEqual("delete", rows["build-error-resolver"].target_role)
        self.assertTrue(rows["build-error-resolver"].delete_allowed_now)
        self.assertEqual("systematic-debugging", rows["build-error-resolver"].target_owner)

        self.assertEqual("defer-migration", rows["error-resolver"].target_role)
        self.assertFalse(rows["error-resolver"].delete_allowed_now)
        self.assertIn("assets=1", rows["error-resolver"].unique_assets)

    def test_problem_map_keeps_removed_decisions_visible_after_consolidation(self) -> None:
        target_candidates = [
            "code-reviewer",
            "deslop",
            "generating-test-reports",
            "receiving-code-review",
            "requesting-code-review",
            "security-reviewer",
            "systematic-debugging",
            "tdd-guide",
            "verification-before-completion",
            "windows-hook-debugging",
        ]
        self._write_json(
            "config/pack-manifest.json",
            {
                "packs": [
                    {
                        "id": "code-quality",
                        "skill_candidates": target_candidates,
                        "route_authority_candidates": target_candidates,
                        "stage_assistant_candidates": [],
                        "defaults_by_task": {
                            "debug": "systematic-debugging",
                            "coding": "tdd-guide",
                            "review": "code-reviewer",
                        },
                    }
                ]
            },
        )

        artifact = audit_code_quality_problem_map(self.root)
        rows = {row.skill_id: row for row in artifact.rows}

        self.assertEqual(16, len(rows))
        self.assertEqual("removed_from_pack", rows["reviewing-code"].current_role)
        self.assertEqual("delete", rows["reviewing-code"].target_role)
        self.assertEqual("removed_from_pack", rows["build-error-resolver"].current_role)
        self.assertEqual("merge-delete-after-migration", rows["code-review"].target_role)

    def test_artifact_writer_outputs_json_csv_and_markdown(self) -> None:
        artifact = audit_code_quality_problem_map(self.root)
        self.assertEqual(0, artifact.to_dict()["summary"]["target_stage_assistant_count"])
        written = write_code_quality_problem_artifacts(self.root, artifact, self.root / "outputs" / "skills-audit")

        self.assertTrue(written["json"].exists())
        self.assertTrue(written["csv"].exists())
        self.assertTrue(written["markdown"].exists())

        csv_text = written["csv"].read_text(encoding="utf-8")
        self.assertIn("skill_id,problem_ids,primary_problem_id", csv_text)
        self.assertIn("reviewing-code", csv_text)

        markdown_text = written["markdown"].read_text(encoding="utf-8")
        self.assertIn("# Code-Quality Problem-First Consolidation", markdown_text)
        self.assertIn("## 保留直接路由", markdown_text)
        self.assertIn("## 删除候选", markdown_text)

    def test_second_pass_marks_legacy_directories_for_pruning_or_deferral(self) -> None:
        artifact = audit_code_quality_problem_map(self.root)
        rows = {row.skill_id: row for row in artifact.rows}

        self.assertEqual("merge-delete-after-migration", rows["code-review"].target_role)
        self.assertFalse(rows["code-review"].delete_allowed_now)
        self.assertEqual("code-reviewer", rows["code-review"].target_owner)

        self.assertEqual("delete", rows["debugging-strategies"].target_role)
        self.assertTrue(rows["debugging-strategies"].delete_allowed_now)
        self.assertEqual("systematic-debugging", rows["debugging-strategies"].target_owner)

        self.assertEqual("delete", rows["code-review-excellence"].target_role)
        self.assertTrue(rows["code-review-excellence"].delete_allowed_now)
        self.assertEqual("code-reviewer", rows["code-review-excellence"].target_owner)

        self.assertEqual("defer-migration", rows["error-resolver"].target_role)
        self.assertFalse(rows["error-resolver"].delete_allowed_now)
        self.assertEqual("systematic-debugging", rows["error-resolver"].target_owner)

    def test_real_repo_migrates_code_review_assets_and_removes_deleted_directories(self) -> None:
        code_reviewer_root = REPO_ROOT / "bundled" / "skills" / "code-reviewer"

        self.assertTrue((code_reviewer_root / "references" / "python-style-guide.md").exists())
        self.assertTrue((code_reviewer_root / "scripts" / "check_style.py").exists())

        for deleted_skill in [
            "code-review",
            "debugging-strategies",
            "code-review-excellence",
        ]:
            with self.subTest(deleted_skill=deleted_skill):
                self.assertFalse((REPO_ROOT / "bundled" / "skills" / deleted_skill).exists())

        self.assertTrue((REPO_ROOT / "bundled" / "skills" / "error-resolver").exists())

    def test_problem_artifact_does_not_describe_live_stage_assistants(self) -> None:
        artifact = audit_code_quality_problem_map(self.root)
        written = write_code_quality_problem_artifacts(
            self.root,
            artifact,
            self.root / "outputs" / "skills-audit",
        )

        markdown_text = written["markdown"].read_text(encoding="utf-8")
        self.assertNotIn("## 阶段助手", markdown_text)
        self.assertIn("## 保留直接路由", markdown_text)
        self.assertIn("## 迁移后删除", markdown_text)
        self.assertIn("## 推迟迁移", markdown_text)

    def test_audit_and_writer_do_not_modify_live_config(self) -> None:
        config_paths = [
            self.root / "config" / "pack-manifest.json",
            self.root / "config" / "skill-keyword-index.json",
            self.root / "config" / "skill-routing-rules.json",
        ]
        before = {path: path.read_text(encoding="utf-8") for path in config_paths}

        artifact = audit_code_quality_problem_map(self.root)
        write_code_quality_problem_artifacts(self.root, artifact, self.root / "outputs" / "skills-audit")

        after = {path: path.read_text(encoding="utf-8") for path in config_paths}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
