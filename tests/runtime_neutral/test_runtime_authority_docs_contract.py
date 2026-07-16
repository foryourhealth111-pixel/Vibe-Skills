from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_runtime_authority_docs_describe_current_python_and_powershell_roles() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    architecture = (
        REPO_ROOT / "docs" / "architecture" / "local-agent-kernel-v2.md"
    ).read_text(encoding="utf-8")
    forbidden_overclaims = (
        "PowerShell stays only as a thin host wrapper",
        "PowerShell owns launcher wrappers, host receipts, shell-native checks, and leaf execution only",
    )
    readme_claims = (
        "Python owns canonical validation",
        "truth chain from `agent_skill_organization`",
        "PowerShell performs stage orchestration",
        "The current Agent performs the approved module work",
        "Do not add new task semantics or task execution to PowerShell",
        "existing PowerShell stage scripts are transitional orchestration surfaces",
    )
    architecture_claims = (
        "Python owns final truth artifacts",
        "canonical validation",
        "structured runtime result",
        "PowerShell still performs stage orchestration",
        "Do not add new task semantics to PowerShell",
        "existing PowerShell stage scripts are transitional orchestration surfaces",
    )
    forbidden_claims = (
        "Do not let PowerShell own task semantics.",
    )

    for claim in readme_claims:
        assert claim in readme
    for claim in architecture_claims:
        assert claim in architecture
    for content in (readme, architecture):
        for claim in forbidden_overclaims:
            assert claim not in content
        for claim in forbidden_claims:
            assert claim not in content


def test_chinese_readme_describes_current_python_and_powershell_roles() -> None:
    content = (REPO_ROOT / "README.zh.md").read_text(encoding="utf-8")

    required_claims = (
        "Python 负责 canonical validation",
        "从 `agent_skill_organization` 到 `module-work-plan.json`",
        "canonical validation",
        "PowerShell 负责阶段编排",
        "批准后的模块工作由当前 Agent 真正完成",
        "不要再把新的任务语义或任务执行加到 PowerShell",
        "现有 PowerShell 阶段脚本只是迁移期编排面",
    )
    for claim in required_claims:
        assert claim in content
