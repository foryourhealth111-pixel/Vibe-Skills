from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "runtime-core" / "src"))

from vgo_runtime.router_contract_runtime import route_prompt  # noqa: E402


FREEZE_SCRIPT = REPO_ROOT / "scripts" / "runtime" / "Freeze-RuntimeInputPacket.ps1"
ROUTE_SKILLS = [
    "scientific-visualization",
    "latex-submission-pipeline",
    "pdf",
    "literature-review",
    "scikit-learn",
]


def install_skills(target_root: Path) -> None:
    skills_root = target_root / "skills"
    skills_root.mkdir(parents=True, exist_ok=True)
    for skill_id in ROUTE_SKILLS:
        shutil.copytree(REPO_ROOT / "bundled" / "skills" / skill_id, skills_root / skill_id)


def route(
    prompt: str,
    task_type: str = "research",
    grade: str = "XL",
    target_root: Path | None = None,
) -> dict[str, object]:
    return route_prompt(
        prompt=prompt,
        grade=grade,
        task_type=task_type,
        target_root=str(target_root) if target_root is not None else None,
        host_id="codex",
        repo_root=REPO_ROOT,
    )


def selected_skill(result: dict[str, object]) -> str:
    selected = result.get("candidate_focus")
    assert isinstance(selected, dict), result
    return str(selected.get("skill") or "")


def selected_pack(result: dict[str, object]) -> str:
    selected = result.get("candidate_focus")
    assert isinstance(selected, dict), result
    return str(selected.get("pack_id") or "")


def route_with_installed(prompt: str, task_type: str = "research", grade: str = "XL") -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tempdir:
        target_root = Path(tempdir) / ".agents"
        install_skills(target_root)
        return route(prompt, task_type=task_type, grade=grade, target_root=target_root)


def ranked_summary(result: dict[str, object]) -> list[tuple[str, str, float, str]]:
    ranked = result.get("ranked")
    assert isinstance(ranked, list), result
    rows: list[tuple[str, str, float, str]] = []
    for row in ranked[:8]:
        assert isinstance(row, dict), row
        rows.append(
            (
                str(row.get("pack_id") or ""),
                str(row.get("selected_candidate") or ""),
                float(row.get("score") or 0.0),
                str(row.get("candidate_selection_reason") or ""),
            )
        )
    return rows


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


def freeze_packet(task: str) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available")
    with tempfile.TemporaryDirectory() as tempdir:
        home = Path(tempdir) / "home"
        target_root = home / ".agents"
        codex_home = home / ".codex"
        install_skills(target_root)
        codex_home.mkdir(parents=True, exist_ok=True)
        artifact_root = Path(tempdir) / "artifacts"
        organization = {
            "schema_version": "agent_skill_organization_v1",
            "derived_by": "agent",
            "workflow_level": "XL",
            "modules": [
                {
                    "module_id": "research_figures",
                    "goal": "Create publication-ready research figures.",
                    "candidate_skill_ids": ["scientific-visualization"],
                    "execution_mode": "skill_assigned",
                    "acceptance_criteria": [
                        {
                            "criterion_id": "figures-result",
                            "description": "Publication-ready research figures are present and verified.",
                            "verification_mode": "automated",
                        }
                    ],
                },
                {
                    "module_id": "paper_build",
                    "goal": "Write and build the final LaTeX paper.",
                    "candidate_skill_ids": ["latex-submission-pipeline"],
                    "execution_mode": "skill_assigned",
                    "acceptance_criteria": [
                        {
                            "criterion_id": "paper-build-result",
                            "description": "The LaTeX paper and compiled output are present and verified.",
                            "verification_mode": "automated",
                        }
                    ],
                },
            ],
            "selected_skills": [
                {
                    "skill_id": "scientific-visualization",
                    "module_ids": ["research_figures"],
                    "responsibility": "Create publication-ready figures.",
                    "reason": "Its SKILL.md owns scientific visualization.",
                },
                {
                    "skill_id": "latex-submission-pipeline",
                    "module_ids": ["paper_build"],
                    "responsibility": "Write and build the LaTeX paper.",
                    "reason": "Its SKILL.md owns LaTeX submission builds.",
                },
            ],
            "uncovered_modules": [],
            "workflow_level_contract": {
                "L": "Use one serial governed lane.",
                "XL": "Use bounded waves when the approved organization needs them.",
            },
        }
        subprocess.run(
            [
                shell,
                "-NoLogo",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(FREEZE_SCRIPT),
                "-Task",
                task,
                "-Mode",
                "interactive_governed",
                "-RunId",
                "pytest-scientific-visualization-latex-routing",
                "-ArtifactRoot",
                str(artifact_root),
                "-RequestedGradeFloor",
                "XL",
                "-HostDecisionJson",
                json.dumps({"agent_skill_organization": organization}, ensure_ascii=False),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
            env={
                **dict(os.environ),
                "CODEX_HOME": str(codex_home),
                "VCO_HOST_ID": "codex",
                "VIBE_AGENTS_HOME": str(target_root),
            },
        )
        packet_path = next(artifact_root.rglob("runtime-input-packet.json"))
        return json.loads(packet_path.read_text(encoding="utf-8"))


class ScientificVisualizationLatexRoutingTests(unittest.TestCase):
    def test_data_visualization_result_figures_route_to_scientific_visualization(self) -> None:
        result = route_with_installed("对机器学习结果做数据可视化和结果图")

        self.assertEqual("local-skill-index", selected_pack(result), ranked_summary(result))
        self.assertEqual("scientific-visualization", selected_skill(result), ranked_summary(result))

    def test_model_evaluation_result_figures_route_to_scientific_visualization(self) -> None:
        result = route_with_installed("绘制模型评估结果图和投稿图")

        self.assertEqual("local-skill-index", selected_pack(result), ranked_summary(result))
        self.assertEqual("scientific-visualization", selected_skill(result), ranked_summary(result))

    def test_latex_paper_pdf_build_routes_to_latex_pipeline(self) -> None:
        result = route_with_installed("用 LaTeX 写论文并构建 PDF")

        self.assertEqual("local-skill-index", selected_pack(result), ranked_summary(result))
        self.assertEqual("latex-submission-pipeline", selected_skill(result), ranked_summary(result))

    def test_latex_tooling_paper_build_routes_to_latex_pipeline(self) -> None:
        result = route_with_installed("配置 latexmk/chktex/latexindent 编译论文 PDF", task_type="coding")

        self.assertEqual("local-skill-index", selected_pack(result), ranked_summary(result))
        self.assertEqual("latex-submission-pipeline", selected_skill(result), ranked_summary(result))

    def test_existing_pdf_extraction_still_routes_to_pdf(self) -> None:
        result = route_with_installed("读取 PDF 并提取正文")

        self.assertEqual("local-skill-index", selected_pack(result), ranked_summary(result))
        self.assertEqual("pdf", selected_skill(result), ranked_summary(result))

    def test_generic_literature_review_does_not_route_to_latex_pipeline(self) -> None:
        result = route_with_installed("普通文献综述和论文研究")

        self.assertNotEqual("latex-submission-pipeline", selected_skill(result), ranked_summary(result))

    def test_composite_research_freeze_uses_agent_selected_visualization_and_latex_skills(self) -> None:
        packet = freeze_packet(
            "我希望做一个完整研究项目：先做论文研究和文献综述，获取数据后训练机器学习模型，"
            "做数据可视化和结果图，最后用 LaTeX 写成论文 PDF。"
        )

        selected_ids = {
            str(item["skill_id"])
            for item in packet["agent_skill_organization"]["selected_skills"]
        }
        bound_ids = {
            str(unit["bound_skill"])
            for unit in packet["module_assignments"]["units"]
            if str(unit.get("bound_skill") or "")
        }
        self.assertEqual(
            {"scientific-visualization", "latex-submission-pipeline"},
            selected_ids,
        )
        self.assertEqual(selected_ids, bound_ids)
        self.assertEqual("agent_skill_organization", packet["module_assignments"]["source"])
