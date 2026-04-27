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
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


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


def _priority_for_rank(score: float, rank: int) -> str:
    if rank <= 6 and score >= 23:
        return "P0"
    if score >= 14:
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
    del stage_count
    reasons: list[str] = []
    if skill_count >= 12:
        reasons.append(f"{skill_count} skill candidates")
    if route_count >= 5:
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
    score += min(skill_count * 0.9, 24.0)
    if explicit_roles:
        score += min(route_count * 2.2, 22.0)
    elif skill_count >= 5:
        score += 18.0
    score += missing_defaults * 5.0
    score += min(overlaps * 2.2, 22.0)
    score += min(broad_keywords * 1.8, 18.0)
    score += min(tool_primary_risk * 1.2, 15.0)
    score += min(asset_heavy * 0.8, 10.0)
    return round(score, 2)


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
            priority="P2",
            recommended_next_action="",
            rationale=rationale,
        )
        rows.append(provisional)

    rows = sorted(rows, key=lambda row: (-row.risk_score, row.pack_id))
    finalized_rows: list[PackAuditRow] = []
    for rank, row in enumerate(rows, start=1):
        priority = _priority_for_rank(row.risk_score, rank)
        finalized = PackAuditRow(**{**asdict(row), "priority": priority})
        finalized_rows.append(
            PackAuditRow(
                **{
                    **asdict(finalized),
                    "recommended_next_action": _recommended_next_action(finalized),
                }
            )
        )
    rows = finalized_rows
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


def write_artifacts(
    repo_root: Path,
    artifact: GlobalPackAuditArtifact,
    output_dir: Path | None = None,
) -> dict[str, Path]:
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
