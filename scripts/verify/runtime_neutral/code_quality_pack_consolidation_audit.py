#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from runpy import run_path

ensure_verification_core_src_on_path = run_path(str(Path(__file__).with_name("_bootstrap.py")))[
    "ensure_verification_core_src_on_path"
]
ensure_verification_core_src_on_path()

from vgo_verify.code_quality_pack_consolidation_audit import (  # noqa: E402
    ProblemMapArtifact,
    ProblemMapRow,
    audit_code_quality_problem_map,
    main,
    write_code_quality_problem_artifacts,
)

__all__ = [
    "ProblemMapArtifact",
    "ProblemMapRow",
    "audit_code_quality_problem_map",
    "main",
    "write_code_quality_problem_artifacts",
]

if __name__ == "__main__":
    raise SystemExit(main())
