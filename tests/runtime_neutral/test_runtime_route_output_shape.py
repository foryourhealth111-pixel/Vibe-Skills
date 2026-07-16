from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_SRC = REPO_ROOT / "packages" / "runtime-core" / "src"
if str(RUNTIME_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_SRC))

from vgo_runtime.router_contract_runtime import route_prompt  # noqa: E402


POLICY = REPO_ROOT / "config" / "current-routing-debt-erasure.json"


ROUTE_CASES = [
    (
        "帮我做科研绘图，产出期刊级 figure，多面板、颜色无障碍、矢量导出",
        "L",
        "research",
        "scientific-visualization",
    ),
    (
        "请用 LaTeX 构建论文 PDF，检查 bibtex 引用、模板和 submission checklist",
        "L",
        "coding",
        "latex-submission-pipeline",
    ),
    (
        "机器学习 data preprocessing pipeline：清洗数据、feature encoding、standardize data、validate input data",
        "L",
        "coding",
        "preprocessing-data-with-automated-pipelines",
    ),
    (
        "request code review before merge：请整理提交评审材料，准备 code review request",
        "L",
        "review",
        "requesting-code-review",
    ),
]

ROUTE_SKILLS = [case[3] for case in ROUTE_CASES]

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


def install_route_skills(target_root: Path) -> None:
    skills_root = target_root / "skills"
    skills_root.mkdir(parents=True, exist_ok=True)
    for skill_id in ROUTE_SKILLS:
        shutil.copytree(REPO_ROOT / "bundled" / "skills" / skill_id, skills_root / skill_id)


def assert_public_route_output_shape(testcase: unittest.TestCase, result: dict[str, Any]) -> None:
    retired_fields = set(json.loads(POLICY.read_text(encoding="utf-8"))["high_risk_retired_fields"])
    testcase.assertNotIn("selected", result)
    testcase.assertNotIn("primary_candidate", result)
    testcase.assertNotIn("confirm_required", result)
    testcase.assertNotIn("confirm_options", result)
    testcase.assertNotIn("confirm_ui", result)
    testcase.assertNotIn("selected", result["skill_routing"])
    testcase.assertNotIn("primary_skill", result["skill_routing"])
    testcase.assertIn("ranked", result)
    testcase.assertIsInstance(result["ranked"], list)
    for pack_row in result["ranked"]:
        testcase.assertIsInstance(pack_row, dict)
        for field in retired_fields:
            testcase.assertNotIn(field, pack_row, pack_row.get("pack_id"))
        custom_admission = pack_row.get("custom_admission")
        if isinstance(custom_admission, dict):
            for field in retired_fields:
                testcase.assertNotIn(field, custom_admission, pack_row.get("pack_id"))
        ranking = pack_row.get("candidate_ranking") or []
        testcase.assertIsInstance(ranking, list)
        for candidate_row in ranking:
            testcase.assertIsInstance(candidate_row, dict)
            for field in retired_fields:
                testcase.assertNotIn(field, candidate_row, candidate_row.get("skill"))


class RuntimeRouteOutputShapeTests(unittest.TestCase):
    def test_runtime_route_output_exposes_fallback_audit_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            result = route_prompt(
                prompt="根据错误日志排查翻译接口失败并给出解决方案",
                grade="XL",
                task_type="debug",
                target_root=str(Path(tempdir) / ".agents"),
                host_id="codex",
                repo_root=REPO_ROOT,
            )

        self.assertIn("fallback_applied", result)
        self.assertIn("rejected_specialist_reasons", result)
        self.assertIn("pre_fallback_top", result)
        self.assertEqual("no_local_candidate", result["route_mode"])
        self.assertEqual("local_index_no_match", result["truth_level"])
        self.assertIsNone(result["candidate_focus"])

    def test_retired_programmatic_candidate_selection_modules_are_absent(self) -> None:
        retired_paths = [
            REPO_ROOT / "scripts" / "router" / "modules" / "41-candidate-selection.ps1",
            REPO_ROOT / "packages" / "runtime-core" / "src" / "vgo_runtime" / "router_contract_selection.py",
            REPO_ROOT / "packages" / "runtime-core" / "src" / "vgo_runtime" / "router.py",
            REPO_ROOT / "packages" / "runtime-core" / "src" / "vgo_runtime" / "execution.py",
            REPO_ROOT / "packages" / "runtime-core" / "src" / "vgo_runtime" / "execution_snapshot.py",
        ]
        for path in retired_paths:
            self.assertFalse(path.exists(), path)

        for relative_path in (
            "config/runtime-script-manifest.json",
            "config/routing-terminology-hard-cleanup.json",
            "config/kernel-boundary-demotion-matrix.json",
        ):
            text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
            for path in retired_paths:
                self.assertNotIn(path.name, text, relative_path)

        router_runtime = (
            REPO_ROOT / "packages" / "runtime-core" / "src" / "vgo_runtime" / "router_contract_runtime.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("def choose_authoritative_route", router_runtime)

    def test_python_route_output_has_only_current_skill_ranking_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir) / ".agents"
            install_route_skills(target_root)
            for prompt, grade, task_type, expected_skill in ROUTE_CASES:
                with self.subTest(expected_skill=expected_skill):
                    result = route_prompt(
                        prompt=prompt,
                        grade=grade,
                        task_type=task_type,
                        target_root=str(target_root),
                        host_id="codex",
                        repo_root=REPO_ROOT,
                    )

                    self.assertEqual("local-skill-index", result["candidate_focus"]["pack_id"])
                    self.assertEqual(expected_skill, result["candidate_focus"]["skill"])
                    assert_public_route_output_shape(self, result)

    def test_powershell_route_output_has_only_current_skill_ranking_fields(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        script_path = REPO_ROOT / "scripts" / "router" / "resolve-pack-route.ps1"
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir) / ".agents"
            install_route_skills(target_root)
            for prompt, grade, task_type, expected_skill in ROUTE_CASES:
                with self.subTest(expected_skill=expected_skill):
                    completed = subprocess.run(
                        [
                            shell,
                            "-NoLogo",
                            "-NoProfile",
                            "-ExecutionPolicy",
                            "Bypass",
                            "-File",
                            str(script_path),
                            "-Prompt",
                            prompt,
                            "-Grade",
                            grade,
                            "-TaskType",
                            task_type,
                            "-TargetRoot",
                            str(target_root),
                        ],
                        cwd=REPO_ROOT,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        check=True,
                        env={**os.environ},
                    )
                    result = json.loads(completed.stdout)

                    self.assertEqual("local-skill-index", result["candidate_focus"]["pack_id"])
                    self.assertEqual(expected_skill, result["candidate_focus"]["skill"])
                    assert_public_route_output_shape(self, result)


if __name__ == "__main__":
    unittest.main()
