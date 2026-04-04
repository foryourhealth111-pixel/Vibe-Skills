from __future__ import annotations

from pathlib import Path


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
        return git_candidates[-1]
    return candidates[-1]
