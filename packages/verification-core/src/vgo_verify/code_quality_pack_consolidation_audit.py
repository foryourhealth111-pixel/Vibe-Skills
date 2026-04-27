#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CSV_FIELDS = [
    "skill_id",
    "problem_ids",
    "primary_problem_id",
    "current_role",
    "target_role",
    "target_owner",
    "overlap_with",
    "unique_assets",
    "routing_change",
    "delete_allowed_now",
    "risk_level",
    "rationale",
]

TARGET_SKILL_CANDIDATES = [
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

TARGET_ROUTE_AUTHORITIES = [
    "code-reviewer",
    "deslop",
    "generating-test-reports",
    "receiving-code-review",
    "security-reviewer",
    "systematic-debugging",
    "tdd-guide",
    "verification-before-completion",
    "windows-hook-debugging",
]

TARGET_STAGE_ASSISTANTS = [
    "requesting-code-review",
]

CODE_QUALITY_DECISIONS: dict[str, dict[str, Any]] = {
    "code-reviewer": {
        "problem_ids": ["code_review_general"],
        "primary_problem_id": "code_review_general",
        "target_role": "keep-route-authority",
        "target_owner": "",
        "overlap_with": "code-review; reviewing-code; code-review-excellence",
        "routing_change": "keep as default code review route authority",
        "delete_allowed_now": False,
        "risk_level": "low",
        "rationale": "普通代码审查、PR review、质量检查需要一个默认主入口。",
    },
    "systematic-debugging": {
        "problem_ids": ["debug_root_cause"],
        "primary_problem_id": "debug_root_cause",
        "target_role": "keep-route-authority",
        "target_owner": "",
        "overlap_with": "debugging-strategies; error-resolver; build-error-resolver",
        "routing_change": "keep as default debug/root-cause route authority",
        "delete_allowed_now": False,
        "risk_level": "low",
        "rationale": "失败测试、bug、异常行为和根因定位应集中到系统化调试入口。",
    },
    "security-reviewer": {
        "problem_ids": ["security_review"],
        "primary_problem_id": "security_review",
        "target_role": "keep-route-authority",
        "target_owner": "",
        "overlap_with": "code-reviewer",
        "routing_change": "keep as narrow security review route authority",
        "delete_allowed_now": False,
        "risk_level": "low",
        "rationale": "OWASP、secret、auth、权限和输入校验风险是独立高风险场景。",
    },
    "tdd-guide": {
        "problem_ids": ["tdd_flow"],
        "primary_problem_id": "tdd_flow",
        "target_role": "keep-route-authority",
        "target_owner": "",
        "overlap_with": "verification-before-completion",
        "routing_change": "keep as TDD route authority",
        "delete_allowed_now": False,
        "risk_level": "low",
        "rationale": "TDD、先写失败测试、红绿重构有清楚触发边界。",
    },
    "generating-test-reports": {
        "problem_ids": ["test_report_packaging"],
        "primary_problem_id": "test_report_packaging",
        "target_role": "keep-route-authority",
        "target_owner": "",
        "overlap_with": "verification-before-completion; systematic-debugging",
        "routing_change": "keep as test report packaging route authority",
        "delete_allowed_now": False,
        "risk_level": "low",
        "rationale": "测试报告和 coverage 汇总是交付包装问题，不是修 bug。",
    },
    "windows-hook-debugging": {
        "problem_ids": ["windows_hook_debug"],
        "primary_problem_id": "windows_hook_debug",
        "target_role": "keep-route-authority",
        "target_owner": "",
        "overlap_with": "systematic-debugging",
        "routing_change": "keep as narrow Windows hook route authority",
        "delete_allowed_now": False,
        "risk_level": "low",
        "rationale": "Windows hook、Git Bash、WSL 和 cannot execute binary file 是明确窄场景。",
    },
    "deslop": {
        "problem_ids": ["ai_code_cleanup"],
        "primary_problem_id": "ai_code_cleanup",
        "target_role": "keep-route-authority",
        "target_owner": "",
        "overlap_with": "code-reviewer",
        "routing_change": "keep as AI-code-cleanup route authority",
        "delete_allowed_now": False,
        "risk_level": "low",
        "rationale": "清理 AI 生成代码废话、冗余注释和多余防御式检查是明确问题。",
    },
    "receiving-code-review": {
        "problem_ids": ["review_feedback_handling"],
        "primary_problem_id": "review_feedback_handling",
        "target_role": "keep-route-authority",
        "target_owner": "",
        "overlap_with": "code-reviewer",
        "routing_change": "keep as narrow review-feedback route authority",
        "delete_allowed_now": False,
        "risk_level": "low",
        "rationale": "用户会直接要求处理 CodeRabbit 或人工 review feedback，需要可直接命中。",
    },
    "verification-before-completion": {
        "problem_ids": ["completion_verification"],
        "primary_problem_id": "completion_verification",
        "target_role": "keep-route-authority",
        "target_owner": "",
        "overlap_with": "generating-test-reports; tdd-guide",
        "routing_change": "keep as narrow completion-evidence route authority",
        "delete_allowed_now": False,
        "risk_level": "low",
        "rationale": "收尾前确认测试和验收证据是完成声明前的独立质量门。",
    },
    "requesting-code-review": {
        "problem_ids": ["review_request_stage"],
        "primary_problem_id": "review_request_stage",
        "target_role": "stage-assistant",
        "target_owner": "code-reviewer",
        "overlap_with": "code-reviewer",
        "routing_change": "keep as stage assistant, not default route authority",
        "delete_allowed_now": False,
        "risk_level": "low",
        "rationale": "提交前请求 review 是流程提醒，不应抢普通 code review。",
    },
    "reviewing-code": {
        "problem_ids": ["code_review_general"],
        "primary_problem_id": "code_review_general",
        "target_role": "delete",
        "target_owner": "code-reviewer",
        "overlap_with": "code-reviewer; code-review",
        "routing_change": "delete legacy compatibility alias after reference check",
        "delete_allowed_now": True,
        "risk_level": "low",
        "rationale": "该 skill 是 legacy compatibility alias，且无独立资产。",
    },
    "build-error-resolver": {
        "problem_ids": ["debug_root_cause"],
        "primary_problem_id": "debug_root_cause",
        "target_role": "delete",
        "target_owner": "systematic-debugging",
        "overlap_with": "systematic-debugging; error-resolver",
        "routing_change": "delete thin build-error compatibility alias after reference check",
        "delete_allowed_now": True,
        "risk_level": "low",
        "rationale": "构建失败可由 systematic-debugging 接管，该目录只是薄兼容壳。",
    },
    "code-review": {
        "problem_ids": ["code_review_general"],
        "primary_problem_id": "code_review_general",
        "target_role": "move-out",
        "target_owner": "code-reviewer",
        "overlap_with": "code-reviewer; reviewing-code",
        "routing_change": "remove from code-quality route surface; keep directory for asset migration",
        "delete_allowed_now": False,
        "risk_level": "medium",
        "rationale": "与 code-reviewer 重叠，但有脚本和 reference，先迁移再决定删除。",
    },
    "debugging-strategies": {
        "problem_ids": ["debug_root_cause"],
        "primary_problem_id": "debug_root_cause",
        "target_role": "move-out",
        "target_owner": "systematic-debugging",
        "overlap_with": "systematic-debugging; error-resolver",
        "routing_change": "remove from code-quality route surface; keep as explicit/deferred content",
        "delete_allowed_now": False,
        "risk_level": "medium",
        "rationale": "和 systematic-debugging 重叠，内容较长，先退出主路由。",
    },
    "error-resolver": {
        "problem_ids": ["debug_root_cause"],
        "primary_problem_id": "debug_root_cause",
        "target_role": "move-out",
        "target_owner": "systematic-debugging",
        "overlap_with": "systematic-debugging; debugging-strategies",
        "routing_change": "remove from code-quality route surface; keep directory because assets are heavy",
        "delete_allowed_now": False,
        "risk_level": "high",
        "rationale": "资产重，不能第一刀删除；debug 主路由先交给 systematic-debugging。",
    },
    "code-review-excellence": {
        "problem_ids": ["review_training_standards"],
        "primary_problem_id": "review_training_standards",
        "target_role": "move-out",
        "target_owner": "explicit-review-training",
        "overlap_with": "code-reviewer",
        "routing_change": "remove from code-quality route surface; keep for explicit review culture/training use",
        "delete_allowed_now": False,
        "risk_level": "medium",
        "rationale": "更像 review 文化、标准、教学，不应抢实际代码审查主入口。",
    },
}


@dataclass(frozen=True)
class ProblemMapRow:
    skill_id: str
    problem_ids: str
    primary_problem_id: str
    current_role: str
    target_role: str
    target_owner: str
    overlap_with: str
    unique_assets: str
    routing_change: str
    delete_allowed_now: bool
    risk_level: str
    rationale: str


@dataclass(frozen=True)
class ProblemMapArtifact:
    generated_at: str
    repo_root: str
    rows: list[ProblemMapRow]

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "repo_root": self.repo_root,
            "summary": {
                "code_quality_skill_count": len(self.rows),
                "target_route_authority_count": len(TARGET_ROUTE_AUTHORITIES),
                "target_stage_assistant_count": len(TARGET_STAGE_ASSISTANTS),
                "delete_now_count": sum(1 for row in self.rows if row.target_role == "delete"),
                "move_out_count": sum(1 for row in self.rows if row.target_role == "move-out"),
            },
            "target_skill_candidates": TARGET_SKILL_CANDIDATES,
            "target_route_authorities": TARGET_ROUTE_AUTHORITIES,
            "target_stage_assistants": TARGET_STAGE_ASSISTANTS,
            "rows": [asdict(row) for row in self.rows],
        }


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _find_pack(repo_root: Path, pack_id: str) -> dict[str, Any]:
    manifest = _read_json(repo_root / "config" / "pack-manifest.json")
    for pack in _as_list(manifest.get("packs")):
        if isinstance(pack, dict) and pack.get("id") == pack_id:
            return pack
    raise ValueError(f"pack not found: {pack_id}")


def _current_role(skill_id: str, pack: dict[str, Any]) -> str:
    skill_candidates = {str(item) for item in _as_list(pack.get("skill_candidates"))}
    route_authorities = {str(item) for item in _as_list(pack.get("route_authority_candidates"))}
    stage_assistants = {str(item) for item in _as_list(pack.get("stage_assistant_candidates"))}
    if skill_id in route_authorities:
        return "route_authority"
    if skill_id in stage_assistants:
        return "stage_assistant"
    if skill_id not in skill_candidates:
        return "removed_from_pack"
    return "candidate"


def _asset_summary(skill_dir: Path) -> str:
    scripts = len(list((skill_dir / "scripts").rglob("*"))) if (skill_dir / "scripts").exists() else 0
    references = len(list((skill_dir / "references").rglob("*"))) if (skill_dir / "references").exists() else 0
    assets = len(list((skill_dir / "assets").rglob("*"))) if (skill_dir / "assets").exists() else 0
    return f"scripts={scripts}; references={references}; assets={assets}"


def audit_code_quality_problem_map(repo_root: Path) -> ProblemMapArtifact:
    pack = _find_pack(repo_root, "code-quality")
    rows: list[ProblemMapRow] = []
    pack_candidates = [str(item) for item in _as_list(pack.get("skill_candidates"))]
    skill_ids = list(dict.fromkeys([*pack_candidates, *CODE_QUALITY_DECISIONS.keys()]))
    for skill_id in skill_ids:
        decision = CODE_QUALITY_DECISIONS.get(
            skill_id,
            {
                "problem_ids": ["manual_review"],
                "primary_problem_id": "manual_review",
                "target_role": "manual-review",
                "target_owner": "",
                "overlap_with": "",
                "routing_change": "manual review required before route changes",
                "delete_allowed_now": False,
                "risk_level": "high",
                "rationale": "没有显式治理决策，不能静默移出或删除。",
            },
        )
        skill_dir = repo_root / "bundled" / "skills" / skill_id
        rows.append(
            ProblemMapRow(
                skill_id=skill_id,
                problem_ids="; ".join(decision["problem_ids"]),
                primary_problem_id=str(decision["primary_problem_id"]),
                current_role=_current_role(skill_id, pack),
                target_role=str(decision["target_role"]),
                target_owner=str(decision["target_owner"]),
                overlap_with=str(decision["overlap_with"]),
                unique_assets=_asset_summary(skill_dir),
                routing_change=str(decision["routing_change"]),
                delete_allowed_now=bool(decision["delete_allowed_now"]),
                risk_level=str(decision["risk_level"]),
                rationale=str(decision["rationale"]),
            )
        )
    return ProblemMapArtifact(
        generated_at=datetime.now(timezone.utc).isoformat(),
        repo_root=str(repo_root),
        rows=rows,
    )


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[ProblemMapRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def _markdown_table(rows: list[ProblemMapRow]) -> str:
    lines = ["| skill | target_role | target_owner | rationale |", "|---|---|---|---|"]
    for row in rows:
        owner = row.target_owner or "-"
        rationale = row.rationale.replace("|", "\\|").replace("\n", " ")
        lines.append(f"| `{row.skill_id}` | `{row.target_role}` | `{owner}` | {rationale} |")
    return "\n".join(lines)


def _write_markdown(path: Path, artifact: ProblemMapArtifact) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keep_rows = [row for row in artifact.rows if row.target_role == "keep-route-authority"]
    stage_rows = [row for row in artifact.rows if row.target_role == "stage-assistant"]
    delete_rows = [row for row in artifact.rows if row.target_role == "delete"]
    move_rows = [row for row in artifact.rows if row.target_role == "move-out"]
    text = "\n".join(
        [
            "# Code-Quality Problem-First Consolidation",
            "",
            f"generated_at: `{artifact.generated_at}`",
            "",
            "## 保留主路由",
            "",
            _markdown_table(keep_rows),
            "",
            "## 阶段助手",
            "",
            _markdown_table(stage_rows),
            "",
            "## 删除候选",
            "",
            _markdown_table(delete_rows),
            "",
            "## 移出 code-quality 但保留目录",
            "",
            _markdown_table(move_rows),
            "",
        ]
    )
    path.write_text(text, encoding="utf-8")


def write_code_quality_problem_artifacts(
    repo_root: Path,
    artifact: ProblemMapArtifact,
    output_dir: Path | None = None,
) -> dict[str, Path]:
    if output_dir is None:
        output_dir = repo_root / "outputs" / "skills-audit"
    json_path = output_dir / "code-quality-problem-map.json"
    csv_path = output_dir / "code-quality-problem-map.csv"
    markdown_path = output_dir / "code-quality-problem-consolidation.md"
    _write_json(json_path, artifact.to_dict())
    _write_csv(csv_path, artifact.rows)
    _write_markdown(markdown_path, artifact)
    return {"json": json_path, "csv": csv_path, "markdown": markdown_path}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit code-quality pack problem-first consolidation decisions.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[4])
    parser.add_argument("--write-artifacts", action="store_true")
    parser.add_argument("--output-directory", type=Path)
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    artifact = audit_code_quality_problem_map(repo_root)
    print(json.dumps(artifact.to_dict(), ensure_ascii=False, indent=2))
    if args.write_artifacts:
        write_code_quality_problem_artifacts(repo_root, artifact, args.output_directory)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
