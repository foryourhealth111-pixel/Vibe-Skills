from __future__ import annotations

import sys
from pathlib import Path


def ensure_verification_core_src_on_path() -> Path:
    src = Path(__file__).resolve().parents[3] / 'packages' / 'verification-core' / 'src'
    src_str = str(src)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)
    return src
