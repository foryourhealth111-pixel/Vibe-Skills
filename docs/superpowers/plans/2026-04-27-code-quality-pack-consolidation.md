# Code-Quality Pack Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 收敛 `code-quality` pack，删除确认安全的闲置薄包装，并修正 CodeRabbit feedback、completion evidence、AI code cleanup 三个已知误路由。

**Architecture:** 先新增一个 runtime-neutral 的 `code-quality` 问题地图审计，用测试锁定目标角色；再收敛 `config/pack-manifest.json`、关键词和 routing rules；最后删除安全的薄 alias 目录、刷新 `skills-lock.json`，并用 focused probes、pack smoke、offline gate 证明结果。整个实现不重写 router，只利用已有 `route_authority_candidates` / `stage_assistant_candidates` 机制。

**Tech Stack:** Python standard library, PowerShell verify gates, JSON config, existing Vibe-Skills bundled skill layout.

---

## 文件分工

- Create: `packages/verification-core/src/vgo_verify/code_quality_pack_consolidation_audit.py`
  - 负责生成 `code-quality` 问题地图、目标角色、资产清单和 artifacts。
- Create: `scripts/verify/runtime_neutral/code_quality_pack_consolidation_audit.py`
  - repo-local runner，沿用 `runtime_neutral` bootstrap 模式。
- Create: `scripts/verify/vibe-code-quality-pack-consolidation-audit-gate.ps1`
  - PowerShell gate，调用 Python runner。
- Create: `tests/runtime_neutral/test_code_quality_pack_consolidation_audit.py`
  - 测试审计决策、artifact 输出和只读行为。
- Modify: `config/pack-manifest.json`
  - 收敛 `code-quality.skill_candidates`，新增 `route_authority_candidates` 和 `stage_assistant_candidates`。
- Modify: `config/skill-keyword-index.json`
  - 强化目标 owner 的关键词，尤其是 `receiving-code-review`、`verification-before-completion`、`deslop`。
- Modify: `config/skill-routing-rules.json`
  - 加正向/负向边界，避免普通 review/debug 抢窄场景。
- Delete if safe: `bundled/skills/reviewing-code/SKILL.md`
  - legacy compatibility alias，无独立资产。
- Delete if safe: `bundled/skills/build-error-resolver/SKILL.md`
  - build-specific compatibility alias，无独立资产。
- Modify: `config/skills-lock.json`
  - 删除目录后运行 lock generator 刷新。
- Modify: `scripts/verify/vibe-pack-regression-matrix.ps1`
  - 添加 code-quality 边界 probes。
- Modify: `scripts/verify/vibe-skill-index-routing-audit.ps1`
  - 添加或修正 code-quality skill-level expectations。
- Create: `docs/governance/code-quality-problem-first-consolidation-2026-04-27.md`
  - 中文治理说明。
- Modify generated: `docs/governance/global-pack-consolidation-audit-2026-04-27.md`
  - 由 global audit gate 刷新。
- Create generated: `outputs/skills-audit/code-quality-problem-map.json`
- Create generated: `outputs/skills-audit/code-quality-problem-map.csv`
- Create generated: `outputs/skills-audit/code-quality-problem-consolidation.md`

## 执行边界

- 只治理 `code-quality` pack。
- 不治理 `bio-science`、`research-design`、`orchestration-core`、`aios-core`。
- 不修复既有 `skill-metadata-gate.ps1` 旧失败。
- 不修复既有 `vibe-skill-index-routing-audit.ps1` 的非 code-quality 旧失败。
- `code-review`、`debugging-strategies`、`error-resolver`、`code-review-excellence` 只移出 `code-quality`，本轮不物理删除。
- `reviewing-code`、`build-error-resolver` 只有在引用检查和 offline gate 证明安全后才物理删除。

## Task 1: 新增 code-quality 审计测试

**Files:**
- Create: `tests/runtime_neutral/test_code_quality_pack_consolidation_audit.py`
- Later implementation target: `packages/verification-core/src/vgo_verify/code_quality_pack_consolidation_audit.py`

- [ ] **Step 1: 创建测试文件**

Create `tests/runtime_neutral/test_code_quality_pack_consolidation_audit.py` with this content:

```python
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
        self.assertEqual("stage-assistant", rows["requesting-code-review"].target_role)

    def test_problem_map_marks_safe_delete_and_move_out(self) -> None:
        artifact = audit_code_quality_problem_map(self.root)
        rows = {row.skill_id: row for row in artifact.rows}

        self.assertEqual("delete", rows["reviewing-code"].target_role)
        self.assertTrue(rows["reviewing-code"].delete_allowed_now)
        self.assertEqual("code-reviewer", rows["reviewing-code"].target_owner)

        self.assertEqual("delete", rows["build-error-resolver"].target_role)
        self.assertTrue(rows["build-error-resolver"].delete_allowed_now)
        self.assertEqual("systematic-debugging", rows["build-error-resolver"].target_owner)

        self.assertEqual("move-out", rows["error-resolver"].target_role)
        self.assertFalse(rows["error-resolver"].delete_allowed_now)
        self.assertIn("assets=1", rows["error-resolver"].unique_assets)

    def test_artifact_writer_outputs_json_csv_and_markdown(self) -> None:
        artifact = audit_code_quality_problem_map(self.root)
        written = write_code_quality_problem_artifacts(self.root, artifact, self.root / "outputs" / "skills-audit")

        self.assertTrue(written["json"].exists())
        self.assertTrue(written["csv"].exists())
        self.assertTrue(written["markdown"].exists())

        csv_text = written["csv"].read_text(encoding="utf-8")
        self.assertIn("skill_id,problem_ids,primary_problem_id", csv_text)
        self.assertIn("reviewing-code", csv_text)

        markdown_text = written["markdown"].read_text(encoding="utf-8")
        self.assertIn("# Code-Quality Problem-First Consolidation", markdown_text)
        self.assertIn("## 保留主路由", markdown_text)
        self.assertIn("## 删除候选", markdown_text)

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
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_code_quality_pack_consolidation_audit.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'vgo_verify.code_quality_pack_consolidation_audit'`.

## Task 2: 实现 code-quality 审计模块

**Files:**
- Create: `packages/verification-core/src/vgo_verify/code_quality_pack_consolidation_audit.py`
- Create: `scripts/verify/runtime_neutral/code_quality_pack_consolidation_audit.py`
- Create: `scripts/verify/vibe-code-quality-pack-consolidation-audit-gate.ps1`
- Test: `tests/runtime_neutral/test_code_quality_pack_consolidation_audit.py`

- [ ] **Step 1: 创建 Python 审计模块**

Create `packages/verification-core/src/vgo_verify/code_quality_pack_consolidation_audit.py` with this content:

```python
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
    route_authorities = {str(item) for item in _as_list(pack.get("route_authority_candidates"))}
    stage_assistants = {str(item) for item in _as_list(pack.get("stage_assistant_candidates"))}
    if skill_id in route_authorities:
        return "route_authority"
    if skill_id in stage_assistants:
        return "stage_assistant"
    return "candidate"


def _asset_summary(skill_dir: Path) -> str:
    scripts = len(list((skill_dir / "scripts").rglob("*"))) if (skill_dir / "scripts").exists() else 0
    references = len(list((skill_dir / "references").rglob("*"))) if (skill_dir / "references").exists() else 0
    assets = len(list((skill_dir / "assets").rglob("*"))) if (skill_dir / "assets").exists() else 0
    return f"scripts={scripts}; references={references}; assets={assets}"


def audit_code_quality_problem_map(repo_root: Path) -> ProblemMapArtifact:
    pack = _find_pack(repo_root, "code-quality")
    rows: list[ProblemMapRow] = []
    for skill_id_raw in _as_list(pack.get("skill_candidates")):
        skill_id = str(skill_id_raw)
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
        lines.append(f"| `{row.skill_id}` | `{row.target_role}` | `{owner}` | {row.rationale} |")
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
```

- [ ] **Step 2: 创建 runtime-neutral runner**

Create `scripts/verify/runtime_neutral/code_quality_pack_consolidation_audit.py`:

```python
#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from runpy import run_path

ensure_verification_core_src_on_path = run_path(str(Path(__file__).with_name("_bootstrap.py")))[
    "ensure_verification_core_src_on_path"
]
ensure_verification_core_src_on_path()

from vgo_verify.code_quality_pack_consolidation_audit import (  # noqa: E402
    ProblemMapArtifact,
    ProblemMapRow,
    audit_code_quality_problem_map,
    main,
    write_code_quality_problem_artifacts,
)

__all__ = [
    "ProblemMapArtifact",
    "ProblemMapRow",
    "audit_code_quality_problem_map",
    "main",
    "write_code_quality_problem_artifacts",
]

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: 创建 PowerShell gate**

Create `scripts/verify/vibe-code-quality-pack-consolidation-audit-gate.ps1`:

```powershell
[CmdletBinding()]
param(
    [string]$RepoRoot,
    [switch]$WriteArtifacts,
    [string]$OutputDirectory
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
} else {
    $RepoRoot = (Resolve-Path $RepoRoot).Path
}

$runnerPath = Join-Path $RepoRoot 'scripts/verify/runtime_neutral/code_quality_pack_consolidation_audit.py'
if (-not (Test-Path -LiteralPath $runnerPath)) {
    throw "Code-quality pack consolidation audit runner missing: $runnerPath"
}

. (Join-Path $RepoRoot 'scripts/common/vibe-governance-helpers.ps1')
$pythonInvocation = Get-VgoPythonCommand

$runnerArgs = @(
    $runnerPath,
    '--repo-root', $RepoRoot
)
if ($WriteArtifacts) {
    $runnerArgs += '--write-artifacts'
}
if ($OutputDirectory) {
    $runnerArgs += @('--output-directory', $OutputDirectory)
}

& $pythonInvocation.host_path @($pythonInvocation.prefix_arguments) @runnerArgs
$exitCode = $LASTEXITCODE
if ($exitCode -ne 0) {
    throw "vibe-code-quality-pack-consolidation-audit-gate failed with exit code $exitCode"
}

Write-Host '[PASS] vibe-code-quality-pack-consolidation-audit-gate passed' -ForegroundColor Green
```

- [ ] **Step 4: Run tests**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_code_quality_pack_consolidation_audit.py -q
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-code-quality-pack-consolidation-audit-gate.ps1
```

Expected:

```text
4 passed
[PASS] vibe-code-quality-pack-consolidation-audit-gate passed
```

- [ ] **Step 5: Commit audit infrastructure**

Run:

```powershell
git add packages/verification-core/src/vgo_verify/code_quality_pack_consolidation_audit.py scripts/verify/runtime_neutral/code_quality_pack_consolidation_audit.py scripts/verify/vibe-code-quality-pack-consolidation-audit-gate.ps1 tests/runtime_neutral/test_code_quality_pack_consolidation_audit.py
git commit -m "test: add code quality pack consolidation audit"
```

## Task 3: 收敛 code-quality live 配置

**Files:**
- Modify: `config/pack-manifest.json`
- Modify: `config/skill-keyword-index.json`
- Modify: `config/skill-routing-rules.json`
- Test: `scripts/verify/vibe-pack-regression-matrix.ps1`
- Test: `scripts/verify/vibe-skill-index-routing-audit.ps1`

- [ ] **Step 1: 修改 `code-quality.skill_candidates`**

In `config/pack-manifest.json`, replace the `code-quality.skill_candidates` list with:

```json
[
  "code-reviewer",
  "deslop",
  "generating-test-reports",
  "receiving-code-review",
  "requesting-code-review",
  "security-reviewer",
  "systematic-debugging",
  "tdd-guide",
  "verification-before-completion",
  "windows-hook-debugging"
]
```

- [ ] **Step 2: Add route authority list**

In the same `code-quality` pack, add:

```json
"route_authority_candidates": [
  "code-reviewer",
  "deslop",
  "generating-test-reports",
  "receiving-code-review",
  "security-reviewer",
  "systematic-debugging",
  "tdd-guide",
  "verification-before-completion",
  "windows-hook-debugging"
]
```

- [ ] **Step 3: Add stage assistant list**

Add:

```json
"stage_assistant_candidates": [
  "requesting-code-review"
]
```

Keep existing defaults:

```json
"defaults_by_task": {
  "debug": "systematic-debugging",
  "coding": "tdd-guide",
  "review": "code-reviewer"
}
```

- [ ] **Step 4: Update keyword index**

In `config/skill-keyword-index.json`, ensure these entries include the listed keywords. Preserve existing useful keywords and append missing ones:

```json
"code-reviewer": {
  "keywords": [
    "code review",
    "PR review",
    "quality checks",
    "maintainability",
    "bugs",
    "代码审查",
    "代码评审"
  ]
},
"receiving-code-review": {
  "keywords": [
    "review feedback",
    "CodeRabbit",
    "code review feedback",
    "评审意见",
    "逐条判断",
    "是否要改"
  ]
},
"verification-before-completion": {
  "keywords": [
    "completion gate",
    "completion evidence",
    "acceptance evidence",
    "验收证据",
    "完成前验证",
    "收尾前确认",
    "测试通过证据"
  ]
},
"deslop": {
  "keywords": [
    "AI-generated code slop",
    "remove slop",
    "cleanup ai code",
    "多余注释",
    "冗余防御式检查",
    "清理AI生成代码"
  ]
}
```

- [ ] **Step 5: Update routing rules**

In `config/skill-routing-rules.json`, update the four most important rules.

`code-reviewer` must keep review/coding/debug task allow and include negative keywords:

```json
"negative_keywords": [
  "CodeRabbit",
  "review feedback",
  "评审意见",
  "逐条判断",
  "completion evidence",
  "验收证据",
  "AI-generated code slop",
  "清理AI生成代码"
]
```

`receiving-code-review` must include:

```json
"positive_keywords": [
  "address review",
  "feedback",
  "review feedback",
  "CodeRabbit",
  "评审反馈",
  "评审意见",
  "逐条判断",
  "是否要改"
],
"negative_keywords": [
  "run code review",
  "request review",
  "security audit",
  "root cause"
]
```

`verification-before-completion` must include:

```json
"positive_keywords": [
  "verify",
  "run tests",
  "completion gate",
  "completion evidence",
  "acceptance evidence",
  "验收",
  "验收证据",
  "完成前验证",
  "收尾前确认",
  "测试通过证据"
],
"negative_keywords": [
  "test report",
  "coverage report",
  "root cause",
  "debug",
  "CodeRabbit"
]
```

`deslop` must include:

```json
"positive_keywords": [
  "cleanup ai code",
  "remove slop",
  "AI-generated code slop",
  "unnecessary comments",
  "defensive checks",
  "代码清理",
  "多余注释",
  "冗余防御式检查",
  "清理AI生成代码"
]
```

- [ ] **Step 6: Run focused route probes**

Run:

```powershell
$resolver = Resolve-Path .\scripts\router\resolve-pack-route.ps1
$cases = @(
  [pscustomobject]@{Name='feedback'; Prompt='收到CodeRabbit评审意见，帮我逐条判断是否要改'; Grade='M'; Task='review'; Skill='receiving-code-review'},
  [pscustomobject]@{Name='completion'; Prompt='准备收尾，确认测试通过并给出验收证据'; Grade='M'; Task='review'; Skill='verification-before-completion'},
  [pscustomobject]@{Name='deslop'; Prompt='清理AI生成代码里的废话注释和多余防御式检查'; Grade='M'; Task='coding'; Skill='deslop'},
  [pscustomobject]@{Name='review'; Prompt='run code review and quality checks'; Grade='M'; Task='review'; Skill='code-reviewer'},
  [pscustomobject]@{Name='debug'; Prompt='构建失败，TypeScript compile error，帮我定位'; Grade='M'; Task='debug'; Skill='systematic-debugging'}
)
foreach ($c in $cases) {
  $route = (& $resolver -Prompt $c.Prompt -Grade $c.Grade -TaskType $c.Task | ConvertFrom-Json)
  if ($route.selected.pack_id -ne 'code-quality' -or $route.selected.skill -ne $c.Skill) {
    throw "case $($c.Name) expected code-quality/$($c.Skill), got $($route.selected.pack_id)/$($route.selected.skill)"
  }
}
```

Expected: command exits with no error.

## Task 4: 删除安全的闲置薄包装

**Files:**
- Delete: `bundled/skills/reviewing-code/SKILL.md`
- Delete: `bundled/skills/build-error-resolver/SKILL.md`
- Modify later: `config/skills-lock.json`

- [ ] **Step 1: Check references before deletion**

Run:

```powershell
rg "reviewing-code|build-error-resolver" -n .
```

Expected: matches are limited to:

```text
config/pack-manifest.json
config/skill-keyword-index.json
config/skill-routing-rules.json
config/skills-lock.json
bundled/skills/reviewing-code/SKILL.md
bundled/skills/build-error-resolver/SKILL.md
docs/superpowers/specs/2026-04-27-code-quality-pack-consolidation-design.md
docs/superpowers/plans/2026-04-27-code-quality-pack-consolidation.md
```

If extra runtime, installer, profile, or test assertions reference either skill, stop and remove or update those references before deleting.

- [ ] **Step 2: Delete only confirmed-safe directories**

Use PowerShell native commands after verifying paths:

```powershell
$targets = @(
  (Resolve-Path .\bundled\skills\reviewing-code).Path,
  (Resolve-Path .\bundled\skills\build-error-resolver).Path
)
$repo = (Resolve-Path .).Path
foreach ($target in $targets) {
  if (-not $target.StartsWith($repo, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "refusing to delete outside repo: $target"
  }
}
foreach ($target in $targets) {
  Remove-Item -LiteralPath $target -Recurse -Force
}
```

Expected: both directories removed, no other directories touched.

- [ ] **Step 3: Remove deleted skills from config if still present**

Confirm neither skill remains in live routing configs:

```powershell
rg '"reviewing-code"|"build-error-resolver"' config
```

Expected: no matches in `config/pack-manifest.json`, `config/skill-keyword-index.json`, or `config/skill-routing-rules.json` after Task 3 cleanup. `config/skills-lock.json` may still match before lock refresh.

## Task 5: Add route regressions

**Files:**
- Modify: `scripts/verify/vibe-pack-regression-matrix.ps1`
- Modify: `scripts/verify/vibe-skill-index-routing-audit.ps1`

- [ ] **Step 1: Add pack regression cases**

In `scripts/verify/vibe-pack-regression-matrix.ps1`, add cases after existing code-quality cases:

```powershell
[pscustomobject]@{ Name = "code-quality review feedback"; Prompt = "收到CodeRabbit评审意见，帮我逐条判断是否要改"; Grade = "M"; TaskType = "review"; RequestedSkill = $null; ExpectedPack = "code-quality"; ExpectedSkill = "receiving-code-review"; AllowedModes = @("pack_overlay", "confirm_required") },
[pscustomobject]@{ Name = "code-quality completion evidence"; Prompt = "准备收尾，确认测试通过并给出验收证据"; Grade = "M"; TaskType = "review"; RequestedSkill = $null; ExpectedPack = "code-quality"; ExpectedSkill = "verification-before-completion"; AllowedModes = @("pack_overlay", "confirm_required") },
[pscustomobject]@{ Name = "code-quality ai code cleanup"; Prompt = "清理AI生成代码里的废话注释和多余防御式检查"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "code-quality"; ExpectedSkill = "deslop"; AllowedModes = @("pack_overlay", "confirm_required") },
[pscustomobject]@{ Name = "code-quality build failure default"; Prompt = "构建失败，TypeScript compile error，帮我定位"; Grade = "M"; TaskType = "debug"; RequestedSkill = $null; ExpectedPack = "code-quality"; ExpectedSkill = "systematic-debugging"; AllowedModes = @("pack_overlay", "confirm_required") },
```

- [ ] **Step 2: Add skill-index audit cases**

In `scripts/verify/vibe-skill-index-routing-audit.ps1`, add cases after the existing code-quality cases:

```powershell
[pscustomobject]@{ Name = "review feedback handling"; Prompt = "收到CodeRabbit评审意见，帮我逐条判断是否要改"; Grade = "M"; TaskType = "review"; ExpectedPack = "code-quality"; ExpectedSkill = "receiving-code-review" },
[pscustomobject]@{ Name = "completion evidence"; Prompt = "准备收尾，确认测试通过并给出验收证据"; Grade = "M"; TaskType = "review"; ExpectedPack = "code-quality"; ExpectedSkill = "verification-before-completion" },
[pscustomobject]@{ Name = "ai code cleanup"; Prompt = "清理AI生成代码里的废话注释和多余防御式检查"; Grade = "M"; TaskType = "coding"; ExpectedPack = "code-quality"; ExpectedSkill = "deslop" },
[pscustomobject]@{ Name = "build failure root cause"; Prompt = "构建失败，TypeScript compile error，帮我定位"; Grade = "M"; TaskType = "debug"; ExpectedPack = "code-quality"; ExpectedSkill = "systematic-debugging" },
```

- [ ] **Step 3: Run pack regression**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-pack-regression-matrix.ps1
```

Expected: all assertions pass. Total assertion count will increase from 80.

- [ ] **Step 4: Run skill-index audit and record unrelated old failures**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-skill-index-routing-audit.ps1
```

Expected:

- New code-quality cases pass.
- Existing non-code-quality failures may remain:
  - `umap reduction`
  - orchestration `brainstorming`
  - orchestration `writing-plans`
  - orchestration `subagent`
  - `scientific writing`
  - `figma implementation`

If any new code-quality case fails, return to Task 3 and adjust keywords or routing rules.

## Task 6: Generate governance artifacts and docs

**Files:**
- Create generated: `outputs/skills-audit/code-quality-problem-map.json`
- Create generated: `outputs/skills-audit/code-quality-problem-map.csv`
- Create generated: `outputs/skills-audit/code-quality-problem-consolidation.md`
- Create: `docs/governance/code-quality-problem-first-consolidation-2026-04-27.md`
- Modify generated: `docs/governance/global-pack-consolidation-audit-2026-04-27.md`

- [ ] **Step 1: Generate code-quality artifacts**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-code-quality-pack-consolidation-audit-gate.ps1 -WriteArtifacts -OutputDirectory outputs\skills-audit
```

Expected:

```text
[PASS] vibe-code-quality-pack-consolidation-audit-gate passed
```

and these files exist:

```text
outputs/skills-audit/code-quality-problem-map.json
outputs/skills-audit/code-quality-problem-map.csv
outputs/skills-audit/code-quality-problem-consolidation.md
```

- [ ] **Step 2: Write governance note**

Create `docs/governance/code-quality-problem-first-consolidation-2026-04-27.md` with these sections:

```markdown
# Code-Quality Problem-First 收敛证据

日期：2026-04-27

## 结论先看

本轮只治理 `code-quality` pack。目标是把普通代码评审、调试、安全、TDD、测试报告、收尾验证和 AI 代码清理分成清楚的问题入口。

## 数量变化

| 项目 | 收敛前 | 收敛后 |
|---|---:|---:|
| `code-quality.skill_candidates` | 16 | 10 |
| `code-quality.route_authority_candidates` | 0 | 9 |
| `code-quality.stage_assistant_candidates` | 0 | 1 |
| 物理删除 skill 目录 | 0 | 2 |

## 保留主路由

| skill | 负责的问题 |
|---|---|
| `code-reviewer` | 普通代码评审、PR review、质量检查。 |
| `systematic-debugging` | 失败测试、bug、异常行为、根因定位。 |
| `security-reviewer` | OWASP、secret、auth、权限、输入校验风险。 |
| `tdd-guide` | TDD、先写失败测试、红绿重构。 |
| `generating-test-reports` | 测试报告和 coverage 报告整理。 |
| `windows-hook-debugging` | Windows hook / Git Bash / WSL 执行异常。 |
| `deslop` | 清理 AI 生成代码废话、冗余注释、多余防御式检查。 |
| `receiving-code-review` | 收到 CodeRabbit 或人工评审意见后逐条判断是否要改。 |
| `verification-before-completion` | 收尾前确认测试、验收证据、完成声明前验证。 |

## 阶段助手

| skill | 为什么不是主入口 |
|---|---|
| `requesting-code-review` | 提交前请求 review 是流程动作，不是普通代码质量问题主入口。 |

## 删除目录

| skill | 删除原因 |
|---|---|
| `reviewing-code` | legacy compatibility alias，无独立资产，由 `code-reviewer` 接管。 |
| `build-error-resolver` | 薄兼容壳，无独立资产，由 `systematic-debugging` 接管。 |

## 移出 code-quality 但保留目录

| skill | 原因 |
|---|---|
| `code-review` | 和 `code-reviewer` 重叠，但有脚本/reference，先迁移后决定删除。 |
| `debugging-strategies` | 和 `systematic-debugging` 重叠，先退出主路由。 |
| `error-resolver` | 资产重，不能第一刀删除。 |
| `code-review-excellence` | 更像 review 文化/标准/教学，不抢实际代码审查。 |

## 修正的误路由

| 提示 | 新归属 |
|---|---|
| `收到CodeRabbit评审意见，帮我逐条判断是否要改` | `code-quality / receiving-code-review` |
| `准备收尾，确认测试通过并给出验收证据` | `code-quality / verification-before-completion` |
| `清理AI生成代码里的废话注释和多余防御式检查` | `code-quality / deslop` |

## 验证

列出实际运行命令和通过/失败情况。非本轮旧失败要单独标注。
```

- [ ] **Step 3: Refresh global pack audit report**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-global-pack-consolidation-audit-gate.ps1 -WriteArtifacts -OutputDirectory outputs\skills-audit
```

Expected: command passes and updates:

```text
docs/governance/global-pack-consolidation-audit-2026-04-27.md
outputs/skills-audit/global-pack-consolidation-audit.json
outputs/skills-audit/global-pack-consolidation-audit.csv
```

## Task 7: Refresh lock and run final verification

**Files:**
- Modify: `config/skills-lock.json`
- All changed files from prior tasks

- [ ] **Step 1: Refresh skills lock**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-generate-skills-lock.ps1
```

Expected:

```text
skills-lock generated: ...
skills=333
```

The expected skill count assumes only `reviewing-code` and `build-error-resolver` were physically deleted from the current 335-skill state.

- [ ] **Step 2: Run JSON parse check**

Run:

```powershell
@(
  'config/pack-manifest.json',
  'config/skill-keyword-index.json',
  'config/skill-routing-rules.json',
  'config/skills-lock.json'
) | ForEach-Object {
  Get-Content -LiteralPath $_ -Raw | ConvertFrom-Json | Out-Null
  Write-Host "[PASS] $_ parses"
}
```

Expected: all four files print `[PASS]`.

- [ ] **Step 3: Run focused and broad verification**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_code_quality_pack_consolidation_audit.py -q
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-code-quality-pack-consolidation-audit-gate.ps1 -WriteArtifacts -OutputDirectory outputs\skills-audit
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-pack-regression-matrix.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-pack-routing-smoke.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-offline-skills-gate.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-global-pack-consolidation-audit-gate.ps1 -WriteArtifacts -OutputDirectory outputs\skills-audit
```

Expected:

- pytest passes.
- code-quality audit gate passes.
- pack regression passes.
- pack routing smoke passes.
- offline skills gate passes with `present_skills=333` and `lock_skills=333`.
- global pack audit gate passes.

- [ ] **Step 4: Run known-debt checks and record results**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-skill-index-routing-audit.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\verify\skill-metadata-gate.ps1
```

Expected:

- `vibe-skill-index-routing-audit.ps1` may still fail on known non-code-quality cases; all new code-quality cases must pass.
- `skill-metadata-gate.ps1` may still fail on known alias/template old debt; do not fix under this plan unless the failure is newly caused by deleted code-quality skills.

- [ ] **Step 5: Check diff hygiene**

Run:

```powershell
git diff --check
git status --short
git diff --stat
```

Expected:

- `git diff --check` exits 0.
- Status shows only intended files.
- Diff includes two deleted skill directories and code-quality config/doc/test/artifact changes.

## Task 8: Commit implementation

**Files:**
- All implementation files from Tasks 1-7

- [ ] **Step 1: Stage intended files only**

Run:

```powershell
git add `
  packages/verification-core/src/vgo_verify/code_quality_pack_consolidation_audit.py `
  scripts/verify/runtime_neutral/code_quality_pack_consolidation_audit.py `
  scripts/verify/vibe-code-quality-pack-consolidation-audit-gate.ps1 `
  tests/runtime_neutral/test_code_quality_pack_consolidation_audit.py `
  config/pack-manifest.json `
  config/skill-keyword-index.json `
  config/skill-routing-rules.json `
  config/skills-lock.json `
  bundled/skills/reviewing-code/SKILL.md `
  bundled/skills/build-error-resolver/SKILL.md `
  scripts/verify/vibe-pack-regression-matrix.ps1 `
  scripts/verify/vibe-skill-index-routing-audit.ps1 `
  docs/governance/code-quality-problem-first-consolidation-2026-04-27.md `
  docs/governance/global-pack-consolidation-audit-2026-04-27.md `
  outputs/skills-audit/code-quality-problem-map.json `
  outputs/skills-audit/code-quality-problem-map.csv `
  outputs/skills-audit/code-quality-problem-consolidation.md `
  outputs/skills-audit/global-pack-consolidation-audit.json `
  outputs/skills-audit/global-pack-consolidation-audit.csv
```

If a path does not exist because a safety check blocked deletion or artifact generation, do not stage a substitute. Revisit the task that should have produced it.

- [ ] **Step 2: Verify staged diff**

Run:

```powershell
git diff --cached --stat
git diff --cached --check
```

Expected:

- Cached diff contains intended files only.
- Cached diff check exits 0.

- [ ] **Step 3: Commit**

Run:

```powershell
git commit -m "feat: consolidate code quality routing"
```

Expected: commit succeeds.

- [ ] **Step 4: Final status**

Run:

```powershell
git status --short --branch
git log -1 --oneline
```

Expected:

- Worktree is clean.
- Latest commit is `feat: consolidate code quality routing`.

## Final Report Requirements

Final report to the user must include:

- Branch name.
- Commit hash.
- Before/after counts:
  - `code-quality.skill_candidates`: `16 -> 10`
  - `route_authority_candidates`: `0 -> 9`
  - `stage_assistant_candidates`: `0 -> 1`
  - present skills: `335 -> 333` if two deletions landed.
- Deleted skills:
  - `reviewing-code`
  - `build-error-resolver`
- Moved out but retained:
  - `code-review`
  - `debugging-strategies`
  - `error-resolver`
  - `code-review-excellence`
- Kept route authorities and their problem ownership.
- Verification commands and exact pass/fail counts.
- Known residual old failures that were not part of this plan.
