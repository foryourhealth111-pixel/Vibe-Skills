from __future__ import annotations

from hashlib import sha256
import os
from pathlib import Path


def workspace_memory_id(identity_root: str | Path) -> str:
    identity_key = Path(identity_root).resolve().as_posix()
    if os.name == "nt":
        identity_key = identity_key.lower()
    return f"ws:{sha256(identity_key.encode('utf-8')).hexdigest()[:24]}"
