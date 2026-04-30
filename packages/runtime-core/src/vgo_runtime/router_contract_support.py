from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CONTRACTS_SRC = Path(__file__).resolve().parents[4] / "packages" / "contracts" / "src"
if CONTRACTS_SRC.is_dir() and str(CONTRACTS_SRC) not in os.sys.path:
    os.sys.path.insert(0, str(CONTRACTS_SRC))

from vgo_contracts.discoverable_entry_surface import load_discoverable_entry_surface


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
    if git_candidates:
        return git_candidates[0]
    # Installed-host layouts can place host-level config files above skills/vibe.
    # Without a git root, prefer the nearest governed root to preserve installed
    # runtime routing semantics.
    return candidates[0]


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


def load_runtime_core_packaging(config_root: Path) -> dict[str, Any]:
    path = config_root / "runtime-core-packaging.json"
    if not path.exists():
        return {}
    payload = load_json(path)
    if not isinstance(payload, dict):
        return {}

    profiles = payload.get("profiles") or {}
    default_profile = str(payload.get("default_profile") or "full").strip() or "full"
    overlay = profiles.get(default_profile)
    if not isinstance(overlay, dict):
        return payload

    def _deep_merge(base: Any, extra: Any) -> Any:
        if isinstance(base, dict) and isinstance(extra, dict):
            merged = {key: _deep_merge(value, extra[key]) if key in extra else value for key, value in base.items()}
            for key, value in extra.items():
                if key not in merged:
                    merged[key] = value
            return merged
        return extra

    merged = dict(payload)
    merged.pop("profiles", None)
    merged.pop("default_profile", None)
    return _deep_merge(merged, overlay)


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


NEGATION_SCOPE_PATTERN = re.compile(
    r"(不是|并非|不属于|不涉及|不做|不使用|不调用|不指定|不限定|不需要|不要|不用|无需|避免|排除|without\b|no\b|not\s+using\b|do\s+not\s+use\b|don't\s+use\b|not\b)",
    re.IGNORECASE,
)
NEGATION_SCOPE_BOUNDARY_PATTERN = re.compile(r"[，。；;,.!?！？\r\n]")
NEGATION_CONTRAST_PATTERN = re.compile(
    r"(但使用|但是使用|但要使用|but\s+use|but\s+using|except\s+use|instead\s+use)",
    re.IGNORECASE,
)


def _keyword_pattern(needle: str) -> re.Pattern[str]:
    escaped = re.escape(needle)
    if re.search(r"[\u4e00-\u9fff]", needle):
        return re.compile(escaped)
    if re.search(r"[a-z0-9]", needle):
        return re.compile(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])")
    return re.compile(escaped)


def _keyword_is_negation_phrase(needle: str) -> bool:
    return NEGATION_SCOPE_PATTERN.search(needle) is not None


def _match_is_in_negated_scope(prompt_lower: str, match_start: int) -> bool:
    prefix = prompt_lower[max(0, match_start - 80):match_start]
    boundaries = list(NEGATION_SCOPE_BOUNDARY_PATTERN.finditer(prefix))
    if boundaries:
        prefix = prefix[boundaries[-1].end():]

    negation_matches = list(NEGATION_SCOPE_PATTERN.finditer(prefix))
    if not negation_matches:
        return False

    scoped_prefix = prefix[negation_matches[-1].start():]
    return NEGATION_CONTRAST_PATTERN.search(scoped_prefix) is None


def keyword_hit(prompt_lower: str, keyword: str | None) -> bool:
    needle = normalize_text(keyword)
    if not prompt_lower or not needle:
        return False

    matches = list(_keyword_pattern(needle).finditer(prompt_lower))
    if not matches:
        return False

    if _keyword_is_negation_phrase(needle):
        return True

    return any(not _match_is_in_negated_scope(prompt_lower, match.start()) for match in matches)


def keyword_ratio(prompt_lower: str, keywords: list[Any] | None) -> float:
    rows = normalize_keyword_list(keywords)
    if not rows:
        return 0.0
    hits = sum(1 for keyword in rows if keyword_hit(prompt_lower, keyword))
    if hits <= 0:
        return 0.0
    denominator = min(4, len(rows))
    if denominator <= 0:
        return 0.0
    return min(1.0, hits / denominator)


def candidate_name_score(prompt_lower: str, candidate: str) -> float:
    candidate_lower = normalize_text(candidate)
    if not candidate_lower:
        return 0.0
    variants = {
        candidate_lower,
        candidate_lower.replace("-", " "),
        candidate_lower.replace("-", ""),
        candidate_lower.replace("_", " "),
    }
    for variant in variants:
        if variant and keyword_hit(prompt_lower, variant):
            return 1.0
    return 0.0


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


def resolve_requested_canonical(
    requested_skill: str | None,
    alias_map: dict[str, Any],
    *,
    repo_root: Path | None = None,
) -> str | None:
    if not requested_skill:
        return None
    requested = normalize_text(str(requested_skill).lstrip("$"))
    if not requested:
        return None

    aliases = alias_map.get("aliases") or {}
    for alias, canonical in aliases.items():
        if normalize_text(alias) == requested:
            requested = normalize_text(str(canonical))
            break

    if repo_root is None:
        return requested

    try:
        surface = load_discoverable_entry_surface(repo_root)
    except RuntimeError:
        return requested

    entry_ids = {normalize_text(entry.id) for entry in surface.entries if normalize_text(entry.id)}
    if requested in entry_ids:
        canonical_runtime_skill = normalize_text(surface.canonical_runtime_skill)
        if canonical_runtime_skill:
            return canonical_runtime_skill
    return requested


def resolve_public_skill_surface(repo: RepoContext) -> dict[str, Any]:
    packaging = load_runtime_core_packaging(repo.config_root)
    surface = packaging.get("public_skill_surface") or {}
    discoverable_entry_surface = str(surface.get("discoverable_entry_surface") or "").strip()
    canonical_relpath = (
        str(surface.get("canonical_entrypoint_relpath") or "").strip()
        or str((packaging.get("canonical_vibe_payload") or {}).get("target_relpath") or "skills/vibe").strip()
        or "skills/vibe"
    )
    root_relpath = str(surface.get("root_relpath") or "skills").strip() or "skills"
    projected_skill_names = [
        str(name).strip()
        for name in surface.get("projected_skill_names") or []
        if str(name).strip()
    ]
    if discoverable_entry_surface:
        try:
            projected_skill_names = load_discoverable_entry_surface(repo.repo_root).projected_skill_names
        except RuntimeError:
            pass
    return {
        "root_relpath": root_relpath,
        "canonical_entrypoint_relpath": canonical_relpath,
        "discoverable_entry_surface": discoverable_entry_surface,
        "projected_skill_names": projected_skill_names,
    }


def resolve_compatibility_skill_projections(repo: RepoContext) -> dict[str, Any]:
    packaging = load_runtime_core_packaging(repo.config_root)
    projections = packaging.get("compatibility_skill_projections") or {}
    resolver_roots = projections.get("resolver_roots") or [projections.get("target_root") or "skills"]
    normalized_roots = [
        str(root).strip()
        for root in resolver_roots
        if str(root).strip()
    ] or ["skills"]
    return {
        "resolver_roots": normalized_roots,
    }


def resolve_internal_skill_corpus(repo: RepoContext) -> dict[str, Any]:
    packaging = load_runtime_core_packaging(repo.config_root)
    corpus = packaging.get("internal_skill_corpus") or {}
    return {
        "source": str(corpus.get("source") or packaging.get("bundled_skills_source") or "bundled/skills").strip() or "bundled/skills",
        "target_relpath": str(corpus.get("target_relpath") or "skills/vibe/catalog/skills").strip() or "skills/vibe/catalog/skills",
        "entrypoint_filename": str(corpus.get("entrypoint_filename") or "SKILL.runtime-mirror.md").strip() or "SKILL.runtime-mirror.md",
    }


def iter_skill_descriptor_candidates(
    repo: RepoContext,
    skill: str,
    target_root: str | None,
    host_id: str | None = None,
) -> list[Path]:
    installed_root = resolve_target_root(target_root, host_id)
    public_surface = resolve_public_skill_surface(repo)
    internal_corpus = resolve_internal_skill_corpus(repo)
    compatibility_skill_projections = resolve_compatibility_skill_projections(repo)
    canonical_root = installed_root / public_surface["canonical_entrypoint_relpath"]
    internal_root = installed_root / internal_corpus["target_relpath"]
    internal_entrypoint = internal_corpus["entrypoint_filename"]

    repo_vibe_root = repo.repo_root
    repo_internal_root = repo.repo_root / internal_corpus["target_relpath"]

    compatibility_candidates = [
        installed_root / rel_root / skill / "SKILL.md"
        for rel_root in compatibility_skill_projections["resolver_roots"]
    ]

    candidates = [
        canonical_root / "SKILL.md" if skill == Path(public_surface["canonical_entrypoint_relpath"]).name else None,
        repo_internal_root / skill / "SKILL.md",
        repo_internal_root / skill / internal_entrypoint,
        internal_root / skill / internal_entrypoint,
        internal_root / skill / "SKILL.md",
        *compatibility_candidates,
        installed_root / public_surface["root_relpath"] / "custom" / skill / "SKILL.md",
        repo_vibe_root / "SKILL.md" if skill == Path(public_surface["canonical_entrypoint_relpath"]).name else None,
        repo.bundled_skills_root / skill / "SKILL.md",
    ]

    ordered: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate is None:
            continue
        normalized = candidate.resolve(strict=False)
        if normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(candidate)
    return ordered


def resolve_skill_md_path(repo: RepoContext, skill: str, target_root: str | None, host_id: str | None = None) -> Path | None:
    for candidate in iter_skill_descriptor_candidates(repo, skill, target_root, host_id):
        if candidate.exists():
            return candidate
    return None


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
