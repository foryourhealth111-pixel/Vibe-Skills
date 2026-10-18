from __future__ import annotations

from pathlib import Path
import sys


sys.dont_write_bytecode = True
RUNTIME_SRC = Path(__file__).resolve().parents[2] / "packages" / "runtime-core" / "src"
if str(RUNTIME_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_SRC))

from vgo_runtime.skill_authority import main


if __name__ == "__main__":
    raise SystemExit(main())
