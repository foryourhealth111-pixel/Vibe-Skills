from __future__ import annotations

from contextlib import ExitStack, contextmanager
import errno
import json
import os
import stat
from pathlib import Path
import tempfile
from typing import Iterator


def write_json_atomic(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            stream.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        temporary_path.replace(path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return path


@contextmanager
def exclusive_run_update(run_root: Path, *additional_roots: Path) -> Iterator[None]:
    """Reject overlapping writers; the OS releases ownership on close or exit."""
    if additional_roots:
        with ExitStack() as locks:
            for root in sorted({run_root, *additional_roots}):
                locks.enter_context(exclusive_run_update(root))
            yield
        return
    lock_dir = run_root.parent / ".locks"
    lock_path = lock_dir / f"{run_root.name}.lock"
    if lock_dir.resolve() != lock_dir or lock_path.resolve() != lock_path:
        raise ValueError(f"Run update lock must not traverse links: {lock_path}")
    lock_dir.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError(f"Run update lock must be a regular, unshared file: {lock_path}")
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            if exc.errno not in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                raise
            raise RuntimeError(f"Run {run_root.name!r} is already being updated; retry after it finishes") from exc
        yield
    finally:
        # Keep the inode stable so another writer cannot lock a replacement file.
        os.close(descriptor)
