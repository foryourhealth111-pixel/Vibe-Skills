#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI_MAIN="${SCRIPT_DIR}/apps/vgo-cli/src/vgo_cli/main.py"
PYTHON_MIN_MAJOR=3
PYTHON_MIN_MINOR=10

python_version_of() {
  local candidate="$1"
  "${candidate}" - <<'PY'
import sys
print(f"{sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}")
PY
}

python_meets_minimum() {
  local candidate="$1"
  local version major minor patch
  version="$(python_version_of "${candidate}" 2>/dev/null || true)"
  [[ -n "${version}" ]] || return 1
  IFS='.' read -r major minor patch <<EOF2
${version}
EOF2
  [[ -n "${major}" && -n "${minor}" ]] || return 1
  if (( major > PYTHON_MIN_MAJOR )); then
    return 0
  fi
  if (( major == PYTHON_MIN_MAJOR && minor >= PYTHON_MIN_MINOR )); then
    return 0
  fi
  return 1
}

pick_supported_python() {
  local candidate resolved=""
  for candidate in python3 python; do
    if ! resolved="$(command -v "${candidate}" 2>/dev/null)"; then
      continue
    fi
    if [[ -n "${resolved}" ]] && python_meets_minimum "${resolved}"; then
      printf '%s' "${resolved}"
      return 0
    fi
  done
  return 1
}

print_python_requirement_error() {
  echo "[FAIL] vgo-cli shell uninstall launcher requires Python ${PYTHON_MIN_MAJOR}.${PYTHON_MIN_MINOR}+. Install a modern Python 3.10+ and ensure 'python3 --version' reports >= ${PYTHON_MIN_MAJOR}.${PYTHON_MIN_MINOR} before rerunning." >&2
}

PYTHON_BIN="$(pick_supported_python || true)"
if [[ -z "${PYTHON_BIN}" ]]; then
  print_python_requirement_error
  exit 1
fi

if [[ -f "${CLI_MAIN}" ]]; then
  export PYTHONPATH="${SCRIPT_DIR}/apps/vgo-cli/src${PYTHONPATH:+:${PYTHONPATH}}"
  exec "${PYTHON_BIN}" -m vgo_cli.main uninstall --repo-root "${SCRIPT_DIR}" --frontend shell "$@"
fi

echo "[FAIL] Missing required vgo-cli entrypoint at ${CLI_MAIN}." >&2
echo "[FAIL] The shell uninstall wrapper no longer falls back to legacy uninstall scripts." >&2
exit 1
