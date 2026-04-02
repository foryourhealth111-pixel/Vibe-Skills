#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI_MAIN="${SCRIPT_DIR}/apps/vgo-cli/src/vgo_cli/main.py"
LEGACY_INSTALLER="${SCRIPT_DIR}/scripts/install/install_vgo_adapter.py"
PYTHON_MIN_MAJOR=3
PYTHON_MIN_MINOR=10

# run_runtime_freshness_gate semantics are delegated to vgo_cli.main.

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
  local context="$1"
  local candidate resolved version found_any="false"
  echo "[FAIL] ${context} requires Python ${PYTHON_MIN_MAJOR}.${PYTHON_MIN_MINOR}+." >&2
  for candidate in python3 python; do
    if resolved="$(command -v "${candidate}" 2>/dev/null)"; then
      found_any="true"
      version="$(python_version_of "${resolved}" 2>/dev/null || echo unknown)"
      echo "[FAIL] Detected ${candidate} -> ${resolved} (${version})" >&2
    fi
  done
  if [[ "${found_any}" != "true" ]]; then
    echo "[FAIL] No usable python3/python executable was found in PATH." >&2
  fi
  if [[ "$(uname -s 2>/dev/null)" == "Darwin" ]]; then
    echo "[FAIL] macOS often provides zsh plus an old/missing system Python. Install a modern Python 3.10+ and ensure 'python3 --version' reports >= ${PYTHON_MIN_MAJOR}.${PYTHON_MIN_MINOR} before rerunning." >&2
  else
    echo "[FAIL] Install a modern Python 3.10+ and ensure 'python3 --version' reports >= ${PYTHON_MIN_MAJOR}.${PYTHON_MIN_MINOR} before rerunning." >&2
  fi
}

PYTHON_BIN="$(pick_supported_python || true)"
if [[ -z "${PYTHON_BIN}" ]]; then
  print_python_requirement_error "vgo-cli shell install launcher"
  exit 1
fi

legacy_install_fallback() {
  local forward_args=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --profile|--host|--target-root)
        if [[ $# -lt 2 ]]; then
          echo "[FAIL] Missing value for $1" >&2
          exit 1
        fi
        forward_args+=("$1" "$2")
        shift 2
        ;;
      --require-closed-ready|--allow-external-skill-fallback)
        forward_args+=("$1")
        shift
        ;;
      --install-external|--strict-offline|--skip-runtime-freshness-gate)
        echo "[WARN] Legacy fallback ignores $1 because vgo-cli is unavailable." >&2
        shift
        ;;
      *)
        forward_args+=("$1")
        shift
        ;;
    esac
  done

  "${PYTHON_BIN}" "${LEGACY_INSTALLER}" --repo-root "${SCRIPT_DIR}" "${forward_args[@]}"
  local rc=$?
  if (( rc != 0 )); then
    exit $rc
  fi
  echo "Install done. Legacy fallback completed without vgo-cli."
}

if [[ -f "${CLI_MAIN}" ]]; then
  export PYTHONPATH="${SCRIPT_DIR}/apps/vgo-cli/src${PYTHONPATH:+:${PYTHONPATH}}"
  exec "${PYTHON_BIN}" -m vgo_cli.main install --repo-root "${SCRIPT_DIR}" --frontend shell "$@"
fi

echo "[WARN] Missing vgo-cli entrypoint at ${CLI_MAIN}; falling back to legacy installer dispatch." >&2
legacy_install_fallback "$@"
