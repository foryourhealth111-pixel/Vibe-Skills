from __future__ import annotations

import json
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


def route(prompt: str, task_type: str = "research", grade: str = "XL") -> dict[str, object]:
    return route_prompt(
        prompt=prompt,
        grade=grade,
        task_type=task_type,
        repo_root=REPO_ROOT,
    )


def selected_skill(result: dict[str, object]) -> str:
    selected = result.get("selected")
    assert isinstance(selected, dict), result
    return str(selected.get("skill") or "")


def selected_pack(result: dict[str, object]) -> str:
    selected = result.get("selected")
    assert isinstance(selected, dict), result
    return str(selected.get("pack_id") or "")


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


def as_list(value: object) -> list[object]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


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
        artifact_root = Path(tempdir) / "artifacts"
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
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
        packet_path = next(artifact_root.rglob("runtime-input-packet.json"))
        return json.loads(packet_path.read_text(encoding="utf-8"))


class ScientificVisualizationLatexRoutingTests(unittest.TestCase):
    def test_data_visualization_result_figures_route_to_scientific_visualization(self) -> None:
        result = route("对机器学习结果做数据可视化和结果图")

        self.assertEqual("science-figures-visualization", selected_pack(result), ranked_summary(result))
        self.assertEqual("scientific-visualization", selected_skill(result), ranked_summary(result))

    def test_model_evaluation_result_figures_route_to_scientific_visualization(self) -> None:
        result = route("绘制模型评估结果图和投稿图")

        self.assertEqual("science-figures-visualization", selected_pack(result), ranked_summary(result))
        self.assertEqual("scientific-visualization", selected_skill(result), ranked_summary(result))

    def test_latex_paper_pdf_build_routes_to_latex_pipeline(self) -> None:
        result = route("用 LaTeX 写论文并构建 PDF")

        self.assertEqual("scholarly-publishing-workflow", selected_pack(result), ranked_summary(result))
        self.assertEqual("latex-submission-pipeline", selected_skill(result), ranked_summary(result))

    def test_latex_tooling_paper_build_routes_to_latex_pipeline(self) -> None:
        result = route("配置 latexmk/chktex/latexindent 编译论文 PDF", task_type="coding")

        self.assertEqual("scholarly-publishing-workflow", selected_pack(result), ranked_summary(result))
        self.assertEqual("latex-submission-pipeline", selected_skill(result), ranked_summary(result))

    def test_existing_pdf_extraction_still_routes_to_pdf(self) -> None:
        result = route("读取 PDF 并提取正文")

        self.assertEqual("docs-media", selected_pack(result), ranked_summary(result))
        self.assertEqual("pdf", selected_skill(result), ranked_summary(result))

    def test_generic_literature_review_does_not_route_to_latex_pipeline(self) -> None:
        result = route("普通文献综述和论文研究")

        self.assertNotEqual("latex-submission-pipeline", selected_skill(result), ranked_summary(result))

    def test_composite_research_freeze_selects_visualization_and_latex_build_skills(self) -> None:
        packet = freeze_packet(
            "我希望做一个完整研究项目：先做论文研究和文献综述，获取数据后训练机器学习模型，"
            "做数据可视化和结果图，最后用 LaTeX 写成论文 PDF。"
        )

        routing = packet["skill_routing"]
        selected = as_list(routing["selected"])
        selected_ids = {str(item["skill_id"]) for item in selected if isinstance(item, dict)}
        self.assertIn("scientific-visualization", selected_ids)
        self.assertIn("latex-submission-pipeline", selected_ids)
        self.assertNotIn("pdf", selected_ids)
