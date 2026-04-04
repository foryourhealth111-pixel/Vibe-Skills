from __future__ import annotations

import sys
from pathlib import Path


def ensure_contracts_src_on_path() -> Path:
    contracts_src = Path(__file__).resolve().parents[4] / "packages" / "contracts" / "src"
    if contracts_src.is_dir() and str(contracts_src) not in sys.path:
        sys.path.insert(0, str(contracts_src))
    return contracts_src
