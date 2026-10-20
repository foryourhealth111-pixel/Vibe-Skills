from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from vgo_contracts.adapter_registry_support import load_adapter_registry, normalize_adapter_host_id


DEFAULT_SKILL_ROOTS = (
    "~/.agents/skills",
    "~/.codex/skills",
    "~/.codex/plugins/cache",
    "~/.claude/skills",
)
DEFAULT_SKILL_ROOTS_BY_HOST = {
    "codex": (
        "~/.agents/skills",
        "~/.codex/skills",
        "~/.codex/plugins/cache",
    ),
    "claude-code": (
        "~/.claude/skills",
    ),
}


@dataclass(frozen=True, slots=True)
class HostSkillRoot:
    host_id: str
    root_key: str
    path: Path
    source: str


def _normalize_host_id(host_id: str) -> str:
    return str(host_id or "").strip().lower()


def _home_from_agent_root(agent_root: Path) -> Path:
    resolved = agent_root.resolve()
    host_dirs = {".agents", ".codex", ".claude"}
    if resolved.name.casefold() == "skills" and resolved.parent.name.casefold() in host_dirs:
        return resolved.parent.parent
    if resolved.name.casefold() in host_dirs:
        return resolved.parent
    return Path.home().resolve()


def _skills_dir_from_agent_root(agent_root: Path) -> Path:
    resolved = agent_root.resolve()
    if resolved.name.casefold() in {".agents", ".codex", ".claude"}:
        return (resolved / "skills").resolve()
    return resolved


def _is_absolute_path(raw_path: str) -> bool:
    if raw_path.startswith(("/", "\\")):
        return True
    return len(raw_path) >= 3 and raw_path[1] == ":" and raw_path[2] in {"/", "\\"}


def _expand_root_path(raw_path: str, *, base_root: Path, home_root: Path) -> Path:
    text = str(raw_path or "").strip()
    if not text:
        raise ValueError("Skill root path must be a non-empty string")
    if text == "~" or text.startswith("~/") or text.startswith("~\\"):
        suffix = text[1:].lstrip("/\\")
        return (home_root / Path(suffix.replace("\\", "/"))).resolve()
    if _is_absolute_path(text):
        return Path(text).resolve()
    return (base_root / Path(text.replace("\\", "/"))).resolve()


def _load_extra_roots(config_path: Path) -> list[str]:
    if not config_path.is_file():
        return []
    payload = json.loads(config_path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"Skill roots config must be an object: {config_path}")
    if payload.get("schema_version") != 1:
        raise ValueError(f"Skill roots config schema_version must be 1: {config_path}")
    roots = payload.get("extra_skill_roots")
    if not isinstance(roots, list):
        raise ValueError(f"extra_skill_roots must be a list: {config_path}")
    for root in roots:
        if not isinstance(root, str) or not root.strip():
            raise ValueError(f"extra_skill_roots entries must be non-empty strings: {config_path}")
    return roots


def _append_roots(
    roots: list[HostSkillRoot],
    seen: set[Path],
    *,
    host_id: str,
    root_key: str,
    raw_roots: list[str] | tuple[str, ...],
    base_root: Path,
    home_root: Path,
    source: str,
) -> None:
    for raw_root in raw_roots:
        path = _expand_root_path(raw_root, base_root=base_root, home_root=home_root)
        if path in seen:
            continue
        seen.add(path)
        roots.append(HostSkillRoot(host_id=host_id, root_key=root_key, path=path, source=source))


def resolve_host_skill_roots(
    *,
    repo_root: Path,
    host_id: str,
    agent_root: Path,
    workspace_root: Path | None,
) -> tuple[HostSkillRoot, ...]:
    normalized_host_id = _normalize_host_id(host_id)
    if not normalized_host_id:
        raise ValueError("Host id is required for skill root resolution")
    normalized_host_id = normalize_adapter_host_id(normalized_host_id, load_adapter_registry(repo_root))

    home_root = _home_from_agent_root(agent_root)
    roots: list[HostSkillRoot] = []
    seen: set[Path] = set()

    if workspace_root is not None:
        workspace_config = workspace_root.resolve() / ".vibeskills" / "skill-roots.json"
        _append_roots(
            roots,
            seen,
            host_id=normalized_host_id,
            root_key="workspace_extra",
            raw_roots=_load_extra_roots(workspace_config),
            base_root=workspace_root.resolve(),
            home_root=home_root,
            source=str(workspace_config),
        )

    user_config = home_root / ".vibeskills" / "skill-roots.json"
    _append_roots(
        roots,
        seen,
        host_id=normalized_host_id,
        root_key="user_extra",
        raw_roots=_load_extra_roots(user_config),
        base_root=home_root,
        home_root=home_root,
        source=str(user_config),
    )

    skills_dir = _skills_dir_from_agent_root(agent_root)
    if skills_dir not in seen:
        seen.add(skills_dir)
        roots.append(
            HostSkillRoot(
                host_id=normalized_host_id,
                root_key="skills_dir",
                path=skills_dir,
                source=f"skills_dir:{skills_dir}",
            )
        )

    for raw_root in DEFAULT_SKILL_ROOTS_BY_HOST.get(normalized_host_id, ()):
        path = _expand_root_path(raw_root, base_root=home_root, home_root=home_root)
        if not path.is_dir() or path in seen:
            continue
        seen.add(path)
        root_key = "codex_plugin_cache" if raw_root == "~/.codex/plugins/cache" else "host_default"
        roots.append(HostSkillRoot(
            host_id=normalized_host_id, root_key=root_key, path=path, source=f"{root_key}:{path}",
        ))

    return tuple(roots)
