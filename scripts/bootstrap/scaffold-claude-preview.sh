#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=""
TARGET_ROOT=""
FORCE="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-root) REPO_ROOT="$2"; shift 2 ;;
    --target-root) TARGET_ROOT="$2"; shift 2 ;;
    --force) FORCE="true"; shift ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "${REPO_ROOT}" || -z "${TARGET_ROOT}" ]]; then
  echo "[FAIL] --repo-root and --target-root are required" >&2
  exit 1
fi

python3 - <<'PY' "${TARGET_ROOT}"
import json, sys
from pathlib import Path

target = Path(sys.argv[1]).resolve()
print(json.dumps({
    "result": "PASS",
    "host_id": "claude-code",
    "target_root": str(target),
    "preview_settings_path": None,
    "message": "Claude preview scaffold no longer installs managed hooks or preview settings; use the supported settings-only installer path instead.",
}, ensure_ascii=False, indent=2))
PY
