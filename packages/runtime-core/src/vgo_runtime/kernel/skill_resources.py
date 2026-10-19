from __future__ import annotations

import hashlib
import json
from pathlib import Path
import stat


RESOURCE_CACHE_DIRS = frozenset({".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"})
RESOURCE_VIRTUALENV_DIRS = frozenset({".venv", "venv", ".env", "env"})


class SkillResourceError(ValueError):
    pass


def skill_resource_sha256(skill_file: Path, source_bytes: bytes) -> str:
    """Fingerprint contained Skill resources and links, excluding generated caches."""
    descriptor = skill_file.resolve()
    root = descriptor.parent
    files: list[tuple[str, str, str]] = []
    pending = [(root, frozenset())]
    try:
        while pending:
            directory, ancestors = pending.pop()
            resolved_directory = directory.resolve(strict=True)
            if resolved_directory in ancestors:
                raise SkillResourceError(f"Cyclic Skill resource directory: {directory.relative_to(root)}")
            lineage = ancestors | {resolved_directory}
            for path in sorted(directory.iterdir()):
                if path.name in RESOURCE_CACHE_DIRS or path.suffix in {".pyc", ".pyo"}:
                    continue
                relative = path.relative_to(root).as_posix()
                mode = path.stat().st_mode
                if stat.S_ISDIR(mode) and (
                    path.name in RESOURCE_VIRTUALENV_DIRS or (path / "pyvenv.cfg").is_file()
                ):
                    continue
                resolved = path.resolve(strict=True)
                if not resolved.is_relative_to(root):
                    raise SkillResourceError(f"Skill resource escapes its root: {relative}")
                if stat.S_ISDIR(mode):
                    pending.append((path, lineage))
                    continue
                if not stat.S_ISREG(mode):
                    raise SkillResourceError(f"Skill resource must be a regular file: {relative}")
                digest = hashlib.sha256()
                if resolved == descriptor:
                    digest.update(source_bytes)
                else:
                    with path.open("rb") as stream:
                        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                            digest.update(chunk)
                files.append((relative, resolved.relative_to(root).as_posix(), digest.hexdigest()))
    except (OSError, RuntimeError) as exc:
        raise SkillResourceError(f"Skill resources are unreadable: {exc}") from exc
    encoded = json.dumps(sorted(files), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
