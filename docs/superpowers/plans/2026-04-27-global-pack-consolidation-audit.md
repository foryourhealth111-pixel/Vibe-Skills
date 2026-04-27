# Global Pack Consolidation Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a read-only global Vibe-Skills pack audit that ranks packs by consolidation risk and writes JSON, CSV, and Chinese Markdown evidence.

**Architecture:** Add a focused verification-core module that reads pack/routing/keyword/skill metadata and produces a deterministic risk table without modifying live config. Expose it through a runtime-neutral wrapper and a PowerShell verify gate, then generate governance artifacts under `outputs/skills-audit` and `docs/governance`.

**Tech Stack:** Python standard library, unittest/pytest, PowerShell verify gates, JSON/CSV/Markdown artifacts, existing Vibe-Skills config layout.

---

## File Structure

- Create: `packages/verification-core/src/vgo_verify/global_pack_consolidation_audit.py`
  - Owns dataclasses, risk scoring, artifact writing, and CLI entrypoint.
- Create: `tests/runtime_neutral/test_global_pack_consolidation_audit.py`
  - Uses a temporary fixture repo to prove the audit is read-only and deterministic.
- Create: `scripts/verify/runtime_neutral/global_pack_consolidation_audit.py`
  - Runtime-neutral wrapper that bootstraps `verification-core` onto `sys.path`.
- Create: `scripts/verify/vibe-global-pack-consolidation-audit-gate.ps1`
  - PowerShell gate matching existing Vibe verify gate patterns.
- Generated during execution: `outputs/skills-audit/global-pack-consolidation-audit.json`
- Generated during execution: `outputs/skills-audit/global-pack-consolidation-audit.csv`
- Generated during execution: `docs/governance/global-pack-consolidation-audit-2026-04-27.md`

No task may edit these live routing files:

```text
config/pack-manifest.json
config/skill-keyword-index.json
config/skill-routing-rules.json
config/skills-lock.json
bundled/skills/**
```

## Execution Boundary

- This plan implements audit and report generation only.
- This plan does not consolidate any specific pack.
- This plan does not delete directories or migrate assets.
- If generated rankings differ from expected intuition, preserve the generated evidence and explain the scoring rather than hand-editing the output.

## Task 1: Add Failing Runtime-Neutral Tests

**Files:**
- Create: `tests/runtime_neutral/test_global_pack_consolidation_audit.py`

- [ ] **Step 1: Create the test file with imports and fixture helpers**

Create `tests/runtime_neutral/test_global_pack_consolidation_audit.py` with this content:

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

    def _write_skill(self, skill_id: str, description: str, body: str, *, scripts: bool = False, references: bool = False) -> None:
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
```

- [ ] **Step 2: Add behavior tests**

Append these test methods to the class before the final file end:

```python
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


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run the new test and confirm it fails for the expected reason**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_global_pack_consolidation_audit.py -q
```

Expected: fail with `ModuleNotFoundError: No module named 'vgo_verify.global_pack_consolidation_audit'`.

## Task 2: Implement The Global Pack Audit Module

**Files:**
- Create: `packages/verification-core/src/vgo_verify/global_pack_consolidation_audit.py`

- [ ] **Step 1: Create dataclasses, constants, and JSON helpers**

Create `packages/verification-core/src/vgo_verify/global_pack_consolidation_audit.py` with this initial content:

```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CSV_FIELDS = [
    "pack_id",
    "skill_candidate_count",
    "route_authority_count",
    "stage_assistant_count",
    "has_explicit_role_split",
    "default_task_count",
    "missing_default_skill_count",
    "suspected_overlap_count",
    "broad_keyword_count",
    "tool_primary_risk_count",
    "asset_heavy_candidate_count",
    "risk_score",
    "priority",
    "recommended_next_action",
    "rationale",
]

BROAD_KEYWORDS = {
    "analysis",
    "automation",
    "coding",
    "data",
    "debug",
    "development",
    "docs",
    "document",
    "evaluation",
    "model",
    "pipeline",
    "python",
    "research",
    "review",
    "science",
    "testing",
    "workflow",
    "writing",
}

STOP_TOKENS = {
    "agent",
    "assistant",
    "code",
    "data",
    "database",
    "for",
    "guide",
    "integration",
    "learning",
    "machine",
    "skill",
    "skills",
    "tool",
    "tools",
    "workflow",
}

TOKEN_ALIASES = {
    "citations": "citation",
    "debugging": "debug",
    "debugger": "debug",
    "docs": "doc",
    "documents": "doc",
    "evaluating": "evaluation",
    "experiments": "experiment",
    "references": "reference",
    "reviewer": "review",
    "reviewing": "review",
    "reviews": "review",
    "strategies": "strategy",
    "tests": "test",
    "testing": "test",
    "visualizations": "visualization",
    "writing": "write",
}

TOOL_MARKERS = {
    "api",
    "arxiv",
    "biorxiv",
    "database",
    "docx",
    "excel",
    "framework",
    "matplotlib",
    "openalex",
    "pdf",
    "plotly",
    "pubmed",
    "pyzotero",
    "sdk",
    "seaborn",
    "spreadsheet",
    "transcribe",
    "xlsx",
}


@dataclass(frozen=True)
class PackAuditRow:
    pack_id: str
    skill_candidate_count: int
    route_authority_count: int
    stage_assistant_count: int
    has_explicit_role_split: bool
    default_task_count: int
    missing_default_skill_count: int
    suspected_overlap_count: int
    broad_keyword_count: int
    tool_primary_risk_count: int
    asset_heavy_candidate_count: int
    risk_score: float
    priority: str
    recommended_next_action: str
    rationale: str


@dataclass(frozen=True)
class GlobalPackAuditArtifact:
    generated_at: str
    repo_root: str
    summary: dict[str, Any]
    rows: list[PackAuditRow]


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
```

- [ ] **Step 2: Add metadata extraction helpers**

Append:

```python
def _skill_candidates(pack: dict[str, Any]) -> list[str]:
    seen: set[str] = set()
    skills: list[str] = []
    for item in _as_list(pack.get("skill_candidates")):
        skill = str(item).strip()
        if skill and skill not in seen:
            seen.add(skill)
            skills.append(skill)
    return skills


def _role_candidates(pack: dict[str, Any], key: str) -> list[str]:
    return [str(item).strip() for item in _as_list(pack.get(key)) if str(item).strip()]


def _has_explicit_role_split(pack: dict[str, Any]) -> bool:
    return "route_authority_candidates" in pack or "stage_assistant_candidates" in pack


def _defaults(pack: dict[str, Any]) -> dict[str, str]:
    defaults = _as_dict(pack.get("defaults_by_task"))
    return {str(k): str(v).strip() for k, v in defaults.items() if str(v).strip()}


def _skill_dir(repo_root: Path, skill_id: str) -> Path:
    return repo_root / "bundled" / "skills" / skill_id


def _skill_text(repo_root: Path, skill_id: str) -> str:
    path = _skill_dir(repo_root, skill_id) / "SKILL.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _frontmatter_description(skill_text: str) -> str:
    match = re.search(r"(?ms)^---\s*(.*?)\s*---", skill_text)
    if not match:
        return ""
    for line in match.group(1).splitlines():
        if line.strip().startswith("description:"):
            return line.split(":", 1)[1].strip().strip('"').strip("'")
    return ""


def _asset_file_count(repo_root: Path, skill_id: str) -> int:
    root = _skill_dir(repo_root, skill_id)
    count = 0
    for child_name in ("scripts", "references", "assets", "examples"):
        child = root / child_name
        if child.exists():
            count += sum(1 for item in child.rglob("*") if item.is_file())
    return count
```

- [ ] **Step 3: Add overlap, keyword, and tool-risk helpers**

Append:

```python
def _tokenize_skill_id(skill_id: str) -> set[str]:
    tokens: set[str] = set()
    for raw in re.split(r"[-_\s]+", skill_id.lower()):
        token = re.sub(r"[^a-z0-9]+", "", raw)
        if not token:
            continue
        token = TOKEN_ALIASES.get(token, token)
        if token and token not in STOP_TOKENS:
            tokens.add(token)
    return tokens


def _suspected_overlap_count(skill_ids: list[str]) -> int:
    token_map = {skill: _tokenize_skill_id(skill) for skill in skill_ids}
    count = 0
    for index, left in enumerate(skill_ids):
        left_tokens = token_map[left]
        if not left_tokens:
            continue
        for right in skill_ids[index + 1 :]:
            right_tokens = token_map[right]
            if not right_tokens:
                continue
            intersection = left_tokens & right_tokens
            union = left_tokens | right_tokens
            if not intersection:
                continue
            jaccard = len(intersection) / max(len(union), 1)
            left_compact = re.sub(r"[-_\s]+", "", left.lower())
            right_compact = re.sub(r"[-_\s]+", "", right.lower())
            contains = left_compact in right_compact or right_compact in left_compact
            if jaccard >= 0.5 or contains:
                count += 1
    return count


def _skill_keywords(keyword_index: dict[str, Any], skill_id: str) -> list[str]:
    skills = _as_dict(keyword_index.get("skills"))
    entry = _as_dict(skills.get(skill_id))
    return [str(item).strip().lower() for item in _as_list(entry.get("keywords")) if str(item).strip()]


def _rule_keywords(routing_rules: dict[str, Any], skill_id: str) -> list[str]:
    skills = _as_dict(routing_rules.get("skills"))
    entry = _as_dict(skills.get(skill_id))
    positive = [str(item).strip().lower() for item in _as_list(entry.get("positive_keywords")) if str(item).strip()]
    negative = [str(item).strip().lower() for item in _as_list(entry.get("negative_keywords")) if str(item).strip()]
    return positive + negative


def _broad_keyword_count(keyword_index: dict[str, Any], routing_rules: dict[str, Any], skill_ids: list[str]) -> int:
    keyword_to_skills: dict[str, set[str]] = {}
    for skill in skill_ids:
        for keyword in _skill_keywords(keyword_index, skill) + _rule_keywords(routing_rules, skill):
            if not keyword:
                continue
            keyword_to_skills.setdefault(keyword, set()).add(skill)
    broad_shared = {
        keyword
        for keyword, owners in keyword_to_skills.items()
        if len(owners) >= 2 and (keyword in BROAD_KEYWORDS or len(keyword.split()) <= 2)
    }
    return len(broad_shared)


def _tool_like(skill_id: str, description: str) -> bool:
    haystack = f"{skill_id} {description}".lower()
    return any(marker in haystack for marker in TOOL_MARKERS)


def _tool_primary_risk_count(repo_root: Path, pack: dict[str, Any], skill_ids: list[str]) -> int:
    explicit = _has_explicit_role_split(pack)
    route_authority = _role_candidates(pack, "route_authority_candidates")
    default_skills = list(_defaults(pack).values())
    primary = route_authority if explicit and route_authority else skill_ids
    primary_set = set(primary) | set(default_skills)
    count = 0
    for skill in sorted(primary_set):
        description = _frontmatter_description(_skill_text(repo_root, skill))
        if _tool_like(skill, description):
            count += 1
    return count
```

- [ ] **Step 4: Add scoring and recommendation helpers**

Append:

```python
def _priority(score: float) -> str:
    if score >= 30:
        return "P0"
    if score >= 16:
        return "P1"
    return "P2"


def _recommended_next_action(row: PackAuditRow) -> str:
    if row.priority == "P0":
        return "write a pack-specific problem map before changing routing"
    if not row.has_explicit_role_split and row.skill_candidate_count >= 5:
        return "add explicit route authority and stage assistant roles after content review"
    if row.suspected_overlap_count > 0:
        return "review suspected duplicate skills and add route regression probes"
    return "observe; no immediate consolidation pass recommended"


def _rationale(
    *,
    skill_count: int,
    route_count: int,
    stage_count: int,
    explicit_roles: bool,
    missing_defaults: int,
    overlaps: int,
    broad_keywords: int,
    tool_primary_risk: int,
    asset_heavy: int,
) -> str:
    reasons: list[str] = []
    if skill_count >= 12:
        reasons.append(f"{skill_count} skill candidates")
    if route_count >= 8:
        reasons.append(f"{route_count} route authorities")
    if not explicit_roles and skill_count >= 5:
        reasons.append("no explicit role split")
    if missing_defaults:
        reasons.append(f"{missing_defaults} defaults point outside candidates")
    if overlaps:
        reasons.append(f"{overlaps} suspected overlap pairs")
    if broad_keywords:
        reasons.append(f"{broad_keywords} shared broad keywords")
    if tool_primary_risk:
        reasons.append(f"{tool_primary_risk} tool-like primary candidates")
    if asset_heavy:
        reasons.append(f"{asset_heavy} candidates with scripts/references/assets")
    return "; ".join(reasons) if reasons else "low structural risk"


def _risk_score(
    *,
    skill_count: int,
    route_count: int,
    explicit_roles: bool,
    missing_defaults: int,
    overlaps: int,
    broad_keywords: int,
    tool_primary_risk: int,
    asset_heavy: int,
) -> float:
    score = 0.0
    score += min(skill_count * 0.8, 24.0)
    if explicit_roles:
        score += min(route_count * 1.5, 20.0)
    elif skill_count >= 5:
        score += 18.0
    score += missing_defaults * 5.0
    score += min(overlaps * 2.0, 20.0)
    score += min(broad_keywords * 1.5, 15.0)
    score += min(tool_primary_risk * 1.2, 15.0)
    score += min(asset_heavy * 0.8, 10.0)
    return round(score, 2)
```

- [ ] **Step 5: Add `audit_repository()`**

Append:

```python
def audit_repository(repo_root: Path) -> GlobalPackAuditArtifact:
    pack_manifest = _read_json(repo_root / "config" / "pack-manifest.json")
    keyword_index = _read_json(repo_root / "config" / "skill-keyword-index.json")
    routing_rules = _read_json(repo_root / "config" / "skill-routing-rules.json")

    rows: list[PackAuditRow] = []
    for pack in _as_list(pack_manifest.get("packs")):
        if not isinstance(pack, dict):
            continue
        pack_id = str(pack.get("id") or "").strip()
        if not pack_id:
            continue
        skills = _skill_candidates(pack)
        route_authority = _role_candidates(pack, "route_authority_candidates")
        stage_assistant = _role_candidates(pack, "stage_assistant_candidates")
        explicit_roles = _has_explicit_role_split(pack)
        defaults = _defaults(pack)
        missing_defaults = sum(1 for skill in defaults.values() if skill not in skills)
        overlaps = _suspected_overlap_count(skills)
        broad_keywords = _broad_keyword_count(keyword_index, routing_rules, skills)
        tool_primary_risk = _tool_primary_risk_count(repo_root, pack, skills)
        asset_heavy = sum(1 for skill in skills if _asset_file_count(repo_root, skill) > 0)
        score = _risk_score(
            skill_count=len(skills),
            route_count=len(route_authority),
            explicit_roles=explicit_roles,
            missing_defaults=missing_defaults,
            overlaps=overlaps,
            broad_keywords=broad_keywords,
            tool_primary_risk=tool_primary_risk,
            asset_heavy=asset_heavy,
        )
        priority = _priority(score)
        rationale = _rationale(
            skill_count=len(skills),
            route_count=len(route_authority),
            stage_count=len(stage_assistant),
            explicit_roles=explicit_roles,
            missing_defaults=missing_defaults,
            overlaps=overlaps,
            broad_keywords=broad_keywords,
            tool_primary_risk=tool_primary_risk,
            asset_heavy=asset_heavy,
        )
        provisional = PackAuditRow(
            pack_id=pack_id,
            skill_candidate_count=len(skills),
            route_authority_count=len(route_authority),
            stage_assistant_count=len(stage_assistant),
            has_explicit_role_split=explicit_roles,
            default_task_count=len(defaults),
            missing_default_skill_count=missing_defaults,
            suspected_overlap_count=overlaps,
            broad_keyword_count=broad_keywords,
            tool_primary_risk_count=tool_primary_risk,
            asset_heavy_candidate_count=asset_heavy,
            risk_score=score,
            priority=priority,
            recommended_next_action="",
            rationale=rationale,
        )
        rows.append(
            PackAuditRow(
                **{
                    **asdict(provisional),
                    "recommended_next_action": _recommended_next_action(provisional),
                }
            )
        )

    rows = sorted(rows, key=lambda row: (-row.risk_score, row.pack_id))
    summary = {
        "pack_count": len(rows),
        "p0_count": sum(1 for row in rows if row.priority == "P0"),
        "p1_count": sum(1 for row in rows if row.priority == "P1"),
        "p2_count": sum(1 for row in rows if row.priority == "P2"),
        "top_pack": rows[0].pack_id if rows else "",
    }
    return GlobalPackAuditArtifact(
        generated_at=datetime.now(timezone.utc).isoformat(),
        repo_root=str(repo_root),
        summary=summary,
        rows=rows,
    )
```

- [ ] **Step 6: Add artifact writers and CLI**

Append:

```python
def _markdown_table(rows: list[PackAuditRow]) -> list[str]:
    lines = [
        "| priority | pack | score | skills | route authority | stage assistant | rationale |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            "| {priority} | `{pack}` | {score:.2f} | {skills} | {route} | {stage} | {rationale} |".format(
                priority=row.priority,
                pack=row.pack_id,
                score=row.risk_score,
                skills=row.skill_candidate_count,
                route=row.route_authority_count,
                stage=row.stage_assistant_count,
                rationale=row.rationale.replace("|", "/"),
            )
        )
    return lines


def _markdown_report(artifact: GlobalPackAuditArtifact) -> str:
    lines: list[str] = [
        "# Global Pack Consolidation Audit",
        "",
        "日期：2026-04-27",
        "",
        "## 结论先看",
        "",
        "本报告是只读体检，不修改 live routing，不删除 skill 目录。",
        "",
        f"- pack 总数：{artifact.summary['pack_count']}",
        f"- P0：{artifact.summary['p0_count']}",
        f"- P1：{artifact.summary['p1_count']}",
        f"- P2：{artifact.summary['p2_count']}",
        f"- 当前最高风险 pack：`{artifact.summary['top_pack']}`",
        "",
        "## 全局排序",
        "",
    ]
    lines.extend(_markdown_table(artifact.rows))
    for priority in ("P0", "P1", "P2"):
        grouped = [row for row in artifact.rows if row.priority == priority]
        lines.extend(["", f"## {priority}", ""])
        if not grouped:
            lines.append("无。")
            continue
        lines.extend(_markdown_table(grouped))
    lines.extend(
        [
            "",
            "## 边界说明",
            "",
            "- 本报告只说明治理优先级，不代表删除建议。",
            "- 具体 pack 收敛需要下一轮 problem-first 设计。",
            "- 带 scripts、references、examples 或 assets 的 skill 不能直接删除。",
            "- 若后续修改路由，需要补对应 route regression probe。",
            "",
        ]
    )
    return "\n".join(lines)


def write_artifacts(repo_root: Path, artifact: GlobalPackAuditArtifact, output_dir: Path | None = None) -> dict[str, Path]:
    if output_dir is None:
        output_dir = repo_root / "outputs" / "skills-audit"
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "global-pack-consolidation-audit.json"
    csv_path = output_dir / "global-pack-consolidation-audit.csv"
    markdown_path = repo_root / "docs" / "governance" / "global-pack-consolidation-audit-2026-04-27.md"
    markdown_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "generated_at": artifact.generated_at,
        "repo_root": artifact.repo_root,
        "summary": artifact.summary,
        "rows": [asdict(row) for row in artifact.rows],
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in artifact.rows:
            writer.writerow(asdict(row))

    markdown_path.write_text(_markdown_report(artifact), encoding="utf-8", newline="\n")
    return {"json": json_path, "csv": csv_path, "markdown": markdown_path}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Vibe-Skills packs for consolidation risk.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--write-artifacts", action="store_true")
    parser.add_argument("--output-directory", type=Path)
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    artifact = audit_repository(repo_root)
    if args.write_artifacts:
        write_artifacts(repo_root, artifact, args.output_directory)

    payload = {
        "generated_at": artifact.generated_at,
        "repo_root": artifact.repo_root,
        "summary": artifact.summary,
        "rows": [asdict(row) for row in artifact.rows],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 7: Run the tests**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_global_pack_consolidation_audit.py -q
```

Expected: `3 passed`.

- [ ] **Step 8: Commit the module and tests**

Run:

```powershell
git add packages/verification-core/src/vgo_verify/global_pack_consolidation_audit.py tests/runtime_neutral/test_global_pack_consolidation_audit.py
git commit -m "feat: add global pack consolidation audit"
```

## Task 3: Add Runtime-Neutral Wrapper And Verify Gate

**Files:**
- Create: `scripts/verify/runtime_neutral/global_pack_consolidation_audit.py`
- Create: `scripts/verify/vibe-global-pack-consolidation-audit-gate.ps1`

- [ ] **Step 1: Create the runtime-neutral Python wrapper**

Create `scripts/verify/runtime_neutral/global_pack_consolidation_audit.py`:

```python
#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from runpy import run_path

ensure_verification_core_src_on_path = run_path(str(Path(__file__).with_name("_bootstrap.py")))[
    "ensure_verification_core_src_on_path"
]
ensure_verification_core_src_on_path()

from vgo_verify.global_pack_consolidation_audit import (
    GlobalPackAuditArtifact,
    PackAuditRow,
    audit_repository,
    main,
    write_artifacts,
)

__all__ = [
    "GlobalPackAuditArtifact",
    "PackAuditRow",
    "audit_repository",
    "main",
    "write_artifacts",
]

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Create the PowerShell gate**

Create `scripts/verify/vibe-global-pack-consolidation-audit-gate.ps1`:

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

$runnerPath = Join-Path $RepoRoot 'scripts/verify/runtime_neutral/global_pack_consolidation_audit.py'
if (-not (Test-Path -LiteralPath $runnerPath)) {
    throw "Global pack consolidation audit runner missing: $runnerPath"
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
    throw "vibe-global-pack-consolidation-audit-gate failed with exit code $exitCode"
}

Write-Host '[PASS] vibe-global-pack-consolidation-audit-gate passed' -ForegroundColor Green
```

- [ ] **Step 3: Run the gate without artifacts**

Run:

```powershell
.\scripts\verify\vibe-global-pack-consolidation-audit-gate.ps1
```

Expected: prints JSON and `[PASS] vibe-global-pack-consolidation-audit-gate passed`.

- [ ] **Step 4: Commit wrapper and gate**

Run:

```powershell
git add scripts/verify/runtime_neutral/global_pack_consolidation_audit.py scripts/verify/vibe-global-pack-consolidation-audit-gate.ps1
git commit -m "chore: add global pack audit gate"
```

## Task 4: Generate Governance Artifacts

**Files:**
- Create: `outputs/skills-audit/global-pack-consolidation-audit.json`
- Create: `outputs/skills-audit/global-pack-consolidation-audit.csv`
- Create: `docs/governance/global-pack-consolidation-audit-2026-04-27.md`

- [ ] **Step 1: Run the gate with artifact writing**

Run:

```powershell
.\scripts\verify\vibe-global-pack-consolidation-audit-gate.ps1 -WriteArtifacts -OutputDirectory outputs\skills-audit
```

Expected:

```text
[PASS] vibe-global-pack-consolidation-audit-gate passed
```

- [ ] **Step 2: Inspect generated Markdown**

Run:

```powershell
Get-Content -LiteralPath docs\governance\global-pack-consolidation-audit-2026-04-27.md -TotalCount 120
```

Expected:

```text
# Global Pack Consolidation Audit
...
## P0
...
```

- [ ] **Step 3: Inspect generated machine-readable artifacts**

Run:

```powershell
Get-Item outputs\skills-audit\global-pack-consolidation-audit.json
Get-Item outputs\skills-audit\global-pack-consolidation-audit.csv
```

Expected: both files exist and have non-zero length.

- [ ] **Step 4: Commit tracked governance report**

Run:

```powershell
git add docs/governance/global-pack-consolidation-audit-2026-04-27.md
git commit -m "docs: add global pack consolidation audit"
```

Do not add `outputs/skills-audit/*` unless `git status --short` shows these files are already tracked by the repo.

## Task 5: Final Verification

**Files:**
- No planned source changes.

- [ ] **Step 1: Run focused tests**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_global_pack_consolidation_audit.py -q
```

Expected: all tests pass.

- [ ] **Step 2: Run the new audit gate**

Run:

```powershell
.\scripts\verify\vibe-global-pack-consolidation-audit-gate.ps1 -WriteArtifacts -OutputDirectory outputs\skills-audit
```

Expected: gate passes.

- [ ] **Step 3: Run existing routing smoke**

Run:

```powershell
.\scripts\verify\vibe-pack-routing-smoke.ps1
```

Expected: all assertions pass. This proves the read-only audit work did not break routing config checks.

- [ ] **Step 4: Run offline skills gate**

Run:

```powershell
.\scripts\verify\vibe-offline-skills-gate.ps1
```

Expected: gate passes and `present_skills` equals `lock_skills`.

- [ ] **Step 5: Confirm live config stayed unmodified**

Run:

```powershell
git status --short
```

Expected: no modifications to:

```text
config/pack-manifest.json
config/skill-keyword-index.json
config/skill-routing-rules.json
config/skills-lock.json
bundled/skills/
```

If `outputs/skills-audit/*` appears as untracked files, leave them uncommitted unless the repo already tracks that output family.

## Task 6: Final Report And Handoff

**Files:**
- No planned source changes.

- [ ] **Step 1: Summarize final commits**

Run:

```powershell
git log --oneline -6
```

Expected: includes commits for:

```text
feat: add global pack consolidation audit
chore: add global pack audit gate
docs: add global pack consolidation audit
```

- [ ] **Step 2: Summarize audit result in Chinese**

The final user-facing summary must clearly separate:

```text
已完成：全局只读审计、P0/P1/P2 排序、中文治理报告、测试和 gate
未完成且本轮不做：具体 pack 收敛、删除 skill、改 routing config、迁移 assets
```

- [ ] **Step 3: Recommend the next pack only after evidence**

Use the generated report's P0 ranking. Do not hard-code `research-design` as the final answer unless the generated audit actually ranks it as P0/top priority.
