from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RepoContext:
    repo_root: Path
    config_root: Path
    bundled_skills_root: Path


def resolve_repo_root(start_path: Path) -> Path:
    current = start_path.resolve()
    if current.is_file():
        current = current.parent

    candidates: list[Path] = []
    while True:
        if (current / "config" / "version-governance.json").exists():
            candidates.append(current)
        if current.parent == current:
            break
        current = current.parent

    if not candidates:
        raise RuntimeError(f"Unable to resolve VCO repo root from: {start_path}")

    git_candidates = [candidate for candidate in candidates if (candidate / ".git").exists()]
    return git_candidates[-1] if git_candidates else candidates[-1]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def load_router_config_bundle(config_root: Path) -> dict[str, Any]:
    return {
        "pack_manifest": load_json(config_root / "pack-manifest.json"),
        "alias_map": load_json(config_root / "skill-alias-map.json"),
        "thresholds": load_json(config_root / "router-thresholds.json"),
        "skill_keyword_index": load_json(config_root / "skill-keyword-index.json"),
        "fallback_policy": load_json(config_root / "fallback-governance.json"),
        "routing_rules": load_json(config_root / "skill-routing-rules.json"),
    }


def normalize_text(value: str | None) -> str:
    if value is None:
        return ""
    return str(value).strip().casefold()


def normalize_keyword_list(values: list[Any] | None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        token = normalize_text(str(value))
        if not token or token in seen:
            continue
        normalized.append(token)
        seen.add(token)
    return normalized


def keyword_ratio(prompt_lower: str, keywords: list[Any] | None) -> float:
    rows = normalize_keyword_list(keywords)
    if not rows:
        return 0.0
    hits = sum(1 for keyword in rows if keyword in prompt_lower)
    denominator = min(3, len(rows))
    return round(min(1.0, hits / denominator), 4)


def candidate_name_score(prompt_lower: str, candidate: str) -> float:
    candidate_lower = normalize_text(candidate)
    if not candidate_lower:
        return 0.0
    if candidate_lower in prompt_lower:
        return 1.0

    pieces = [piece for piece in re.split(r"[-_/ ]+", candidate_lower) if piece]
    if not pieces:
        return 0.0
    hits = sum(1 for piece in pieces if piece in prompt_lower)
    return round(hits / len(pieces), 4)


def resolve_home_directory() -> Path:
    candidates = [
        os.environ.get("HOME"),
        os.environ.get("USERPROFILE"),
    ]
    home_drive = os.environ.get("HOMEDRIVE")
    home_path = os.environ.get("HOMEPATH")
    if home_drive and home_path:
        candidates.append(f"{home_drive}{home_path}")

    for candidate in candidates:
        if candidate:
            return Path(candidate).expanduser().resolve()
    return Path.home().resolve()


def resolve_host_id(host_id: str | None = None) -> str:
    resolved = normalize_text(host_id or os.environ.get("VCO_HOST_ID") or "codex")
    aliases = {
        "claude": "claude-code",
    }
    resolved = aliases.get(resolved, resolved)
    if resolved not in {"codex", "claude-code", "cursor", "windsurf", "openclaw", "opencode", "generic"}:
        return "codex"
    return resolved


def resolve_target_root(target_root: str | None = None, host_id: str | None = None) -> Path:
    if target_root:
        return Path(target_root).expanduser().resolve()
    resolved_host_id = resolve_host_id(host_id)
    env_map = {
        "codex": ("CODEX_HOME", Path(".codex")),
        "claude-code": ("CLAUDE_HOME", Path(".claude")),
        "cursor": ("CURSOR_HOME", Path(".cursor")),
        "windsurf": ("WINDSURF_HOME", Path(".codeium") / "windsurf"),
        "openclaw": ("OPENCLAW_HOME", Path(".openclaw")),
        "opencode": ("OPENCODE_HOME", Path(".config") / "opencode"),
        "generic": ("", Path(".vibe-skills") / "generic"),
    }
    env_name, default_rel = env_map[resolved_host_id]
    if env_name and os.environ.get(env_name):
        return Path(os.environ[env_name]).expanduser().resolve()
    return (resolve_home_directory() / default_rel).resolve()


def resolve_requested_canonical(requested_skill: str | None, alias_map: dict[str, Any]) -> str | None:
    if not requested_skill:
        return None
    requested = normalize_text(str(requested_skill).lstrip("$"))
    if not requested:
        return None

    aliases = alias_map.get("aliases") or {}
    for alias, canonical in aliases.items():
        if normalize_text(alias) == requested:
            return normalize_text(str(canonical))
    return requested


def resolve_skill_md_path(repo: RepoContext, skill: str, target_root: str | None, host_id: str | None = None) -> Path | None:
    bundled = repo.bundled_skills_root / skill / "SKILL.md"
    if bundled.exists():
        return bundled
    installed_root = resolve_target_root(target_root, host_id)
    installed = installed_root / "skills" / skill / "SKILL.md"
    if installed.exists():
        return installed
    custom_installed = installed_root / "skills" / "custom" / skill / "SKILL.md"
    return custom_installed if custom_installed.exists() else None


def read_skill_descriptor(repo: RepoContext, skill: str, target_root: str | None, host_id: str | None = None) -> dict[str, Any]:
    path = resolve_skill_md_path(repo, skill, target_root, host_id)
    description = None
    if path and path.exists():
        lines = path.read_text(encoding="utf-8-sig").splitlines()
        if lines and lines[0].strip() == "---":
            for line in lines[1:20]:
                if line.strip() == "---":
                    break
                if line.lower().startswith("description:"):
                    description = line.split(":", 1)[1].strip()
                    break
    return {
        "skill": skill,
        "description": description,
        "skill_md_path": str(path) if path else None,
    }
