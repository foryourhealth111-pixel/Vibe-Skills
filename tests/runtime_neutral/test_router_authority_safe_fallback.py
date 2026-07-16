from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "runtime-core" / "src"))

from vgo_runtime.router_contract_runtime import route_prompt

ROUTE_SKILLS = [
    "systematic-debugging",
    "latex-submission-pipeline",
    "pdf",
    "gh-fix-ci",
    "sentry",
]


def install_skills(target_root: Path) -> None:
    skills_root = target_root / "skills"
    skills_root.mkdir(parents=True, exist_ok=True)
    for skill_id in ROUTE_SKILLS:
        shutil.copytree(REPO_ROOT / "bundled" / "skills" / skill_id, skills_root / skill_id)


def route(prompt: str, *, grade: str, task_type: str) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tempdir:
        target_root = Path(tempdir) / ".agents"
        install_skills(target_root)
        return route_prompt(
            prompt=prompt,
            grade=grade,
            task_type=task_type,
            repo_root=REPO_ROOT,
            target_root=str(target_root),
        )


def selected(result: dict[str, object]) -> tuple[str, str]:
    selected_row = result.get("candidate_focus")
    if not isinstance(selected_row, dict):
        return "", ""
    return str(selected_row.get("pack_id") or ""), str(selected_row.get("skill") or "")


def test_debug_logs_api_failure_falls_back_to_systematic_debugging() -> None:
    result = route(
        prompt="根据错误日志排查翻译接口失败并给出解决方案，检查 runtime pipeline 和 API 请求",
        grade="XL",
        task_type="debug",
    )

    assert selected(result) == ("local-skill-index", "systematic-debugging")
    assert result["fallback_applied"] is False
    assert result["rejected_specialist_reasons"] == []
    assert result["pre_fallback_top"] == {"pack_id": "local-skill-index", "skill": "systematic-debugging"}


def test_explicit_latex_submission_build_stays_in_scholarly_publishing() -> None:
    result = route(
        prompt="配置 latexmk chktex latexindent 编译 LaTeX manuscript PDF 并打包 submission zip",
        grade="XL",
        task_type="coding",
    )

    assert selected(result) == ("local-skill-index", "latex-submission-pipeline")
    assert result["fallback_applied"] is False


def test_existing_pdf_extraction_stays_in_docs_media() -> None:
    result = route(
        prompt="读取 PDF 并提取正文",
        grade="XL",
        task_type="coding",
    )

    assert selected(result) == ("local-skill-index", "pdf")


def test_github_actions_logs_route_to_integration_devops() -> None:
    result = route(
        prompt="查看 github actions 日志并修复 CI pipeline failed",
        grade="L",
        task_type="debug",
    )

    assert selected(result) == ("local-skill-index", "gh-fix-ci")


def test_sentry_alert_routes_to_integration_devops() -> None:
    result = route(
        prompt="排查 sentry production error 和线上告警",
        grade="L",
        task_type="debug",
    )

    assert selected(result) == ("local-skill-index", "sentry")
