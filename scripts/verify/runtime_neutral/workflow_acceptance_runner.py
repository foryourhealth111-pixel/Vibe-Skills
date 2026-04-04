#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from runpy import run_path

ensure_verification_core_src_on_path = run_path(str(Path(__file__).with_name('_bootstrap.py')))['ensure_verification_core_src_on_path']
ensure_verification_core_src_on_path()

from vgo_verify.workflow_acceptance import evaluate, main, write_artifacts

__all__ = ['evaluate', 'main', 'write_artifacts']

if __name__ == '__main__':
    raise SystemExit(main())
