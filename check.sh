#!/usr/bin/env bash
set -euo pipefail

PROFILE="full"
HOST_ID="codex"
TARGET_ROOT=""
SKIP_RUNTIME_FRESHNESS_GATE="false"
DEEP="false"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ADAPTER_QUERY_PY="${SCRIPT_DIR}/scripts/common/adapter_registry_query.py"
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
  IFS='.' read -r major minor patch <<EOF
${version}
EOF
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

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2 ;;
    --host) HOST_ID="$2"; shift 2 ;;
    --target-root) TARGET_ROOT="$2"; shift 2 ;;
    --skip-runtime-freshness-gate) SKIP_RUNTIME_FRESHNESS_GATE="true"; shift ;;
    --deep) DEEP="true"; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

pick_python_for_adapter() {
  pick_supported_python
}

pick_powershell() {
  local candidate resolved=""
  for candidate in pwsh pwsh.exe powershell powershell.exe; do
    if resolved="$(command -v "${candidate}" 2>/dev/null)"; then
      if [[ -n "${resolved}" ]]; then
        printf '%s' "${resolved}"
        return 0
      fi
    fi
  done
  return 1
}

run_powershell_command() {
  local command_text="$1"
  shift
  local shell_path=""
  shell_path="$(pick_powershell || true)"
  [[ -n "${shell_path}" ]] || return 127

  local leaf="${shell_path##*/}"
  leaf="$(printf '%s' "${leaf}" | tr '[:upper:]' '[:lower:]')"
  local cmd=("${shell_path}" "-NoProfile")
  if [[ "${leaf}" == "powershell" || "${leaf}" == "powershell.exe" ]]; then
    cmd+=("-ExecutionPolicy" "Bypass")
  fi
  cmd+=("-Command" "${command_text}")
  "${cmd[@]}" "$@"
}

run_powershell_file() {
  local script_path="$1"
  shift
  local shell_path=""
  shell_path="$(pick_powershell || true)"
  [[ -n "${shell_path}" ]] || return 127

  local leaf="${shell_path##*/}"
  leaf="$(printf '%s' "${leaf}" | tr '[:upper:]' '[:lower:]')"
  local cmd=("${shell_path}" "-NoProfile")
  if [[ "${leaf}" == "powershell" || "${leaf}" == "powershell.exe" ]]; then
    cmd+=("-ExecutionPolicy" "Bypass")
  fi
  cmd+=("-File" "${script_path}")
  "${cmd[@]}" "$@"
}

adapter_query_for_host() {
  local host_id="$1"
  local property="$2"
  local python_bin=""
  python_bin="$(pick_python_for_adapter || true)"
  if [[ -z "${python_bin}" ]]; then
    print_python_requirement_error "Adapter-driven host resolution metadata"
    exit 1
  fi
  "${python_bin}" "${ADAPTER_QUERY_PY}" --repo-root "${SCRIPT_DIR}" --host "${host_id}" --property "${property}"
}

resolve_host_id() {
  local host_id="${1:-${VCO_HOST_ID:-codex}}"
  adapter_query_for_host "${host_id}" "id"
}

resolve_default_target_root() {
  local host_id="$1"
  local env_name rel env_value
  env_name="$(adapter_query_for_host "${host_id}" 'default_target_root.env')"
  rel="$(adapter_query_for_host "${host_id}" 'default_target_root.rel')"

  env_value=""
  if [[ -n "${env_name}" && "${env_name}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
    env_value="${!env_name:-}"
  fi

  if [[ -n "${env_value}" ]]; then
    printf '%s' "${env_value}"
    return 0
  fi
  if [[ -z "${rel}" ]]; then
    echo "[FAIL] Adapter '${host_id}' does not define default_target_root.rel." >&2
    exit 1
  fi
  if [[ "${rel}" == /* ]]; then
    printf '%s' "${rel}"
  else
    printf '%s' "${HOME}/${rel}"
  fi
}

safe_parent_dir() {
  local path="${1:-}"
  [[ -n "${path}" ]] || return 0
  local parent=""
  parent="$(cd "${path}/.." 2>/dev/null && pwd || true)"
  if [[ -z "${parent}" || "${parent}" == "${path}" || "${parent}" == "/" ]]; then
    return 0
  fi
  printf '%s' "${parent}"
}

canonical_repo_available() {
  local current="${1:-}"
  [[ -n "${current}" ]] || return 1
  current="$(cd "${current}" 2>/dev/null && pwd || true)"
  [[ -n "${current}" ]] || return 1

  while [[ -n "${current}" ]]; do
    if [[ -e "${current}/.git" && -f "${current}/config/version-governance.json" ]]; then
      return 0
    fi
    local parent
    parent="$(dirname "${current}")"
    if [[ "${parent}" == "${current}" ]]; then
      break
    fi
    current="${parent}"
  done

  return 1
}

target_root_owner_for_path() {
  local target_root="$1"
  local python_bin=""
  python_bin="$(pick_python_for_adapter || true)"
  if [[ -z "${python_bin}" ]]; then
    print_python_requirement_error "Adapter-driven target-root intent validation"
    exit 1
  fi
  "${python_bin}" "${ADAPTER_QUERY_PY}" --repo-root "${SCRIPT_DIR}" --target-root-owner "${target_root}"
}

assert_target_root_matches_host_intent() {
  local target_root="$1"
  local host_id="$2"
  local foreign_host=""
  foreign_host="$(target_root_owner_for_path "${target_root}")"
  if [[ -z "${foreign_host}" || "${foreign_host}" == "${host_id}" ]]; then
    return 0
  fi
  if [[ "${host_id}" == "codex" && "${foreign_host}" == "cursor" ]]; then
    echo "[FAIL] Target root '${target_root}' looks like a Cursor home, but host='codex'." >&2
    echo "[FAIL] Pass --host cursor for preview guidance or use a Codex target root." >&2
    exit 1
  fi
  if [[ "${host_id}" == "codex" && "${foreign_host}" == "opencode" ]]; then
    echo "[FAIL] Target root '${target_root}' looks like an OpenCode root, but host='codex'." >&2
    echo "[FAIL] Pass --host opencode for the OpenCode preview lane or use a Codex target root." >&2
    exit 1
  fi
  echo "[FAIL] Target root '${target_root}' looks like the default target root for host='${foreign_host}', but host='${host_id}'." >&2
  exit 1
}

HOST_ID="$(resolve_host_id "${HOST_ID}")"
if [[ -z "${TARGET_ROOT}" ]]; then
  TARGET_ROOT="$(resolve_default_target_root "${HOST_ID}")"
fi
assert_target_root_matches_host_intent "${TARGET_ROOT}" "${HOST_ID}"

resolve_codex_duplicate_skill_root() {
  if [[ "${HOST_ID}" != "codex" ]]; then
    return 1
  fi

  local leaf=""
  leaf="$(basename "${TARGET_ROOT}")"
  leaf="$(printf '%s' "${leaf}" | tr '[:upper:]' '[:lower:]')"
  if [[ "${leaf}" != ".codex" ]]; then
    return 1
  fi

  local parent=""
  parent="$(safe_parent_dir "${TARGET_ROOT}")"
  if [[ -z "${parent}" ]]; then
    return 1
  fi

  printf '%s' "${parent}/.agents/skills/vibe"
}

test_vibe_skill_dir() {
  local root="${1:-}"
  local skill_md="${root}/SKILL.md"
  [[ -f "${skill_md}" ]] || return 1
  if grep -Eq '^[[:space:]]*name:[[:space:]]*vibe[[:space:]]*$' "${skill_md}"; then
    return 0
  fi
  return 1
}

check_codex_duplicate_skill_surface() {
  local duplicate_root=""
  duplicate_root="$(resolve_codex_duplicate_skill_root || true)"
  if [[ -z "${duplicate_root}" || ! -d "${duplicate_root}" ]]; then
    return 0
  fi

  if test_vibe_skill_dir "${duplicate_root}"; then
    echo "[FAIL] duplicate Codex-discovered vibe skill surface -> ${duplicate_root}"
    echo "[FAIL] Re-run install.sh for the default Codex root to quarantine the legacy .agents copy, or move it out of .agents/skills manually."
    FAIL=$((FAIL+1))
    return 0
  fi

  warn_note "unexpected directory exists at Codex duplicate-surface path: ${duplicate_root}"
}

PASS=0
FAIL=0
WARN=0

check_path() {
  local label="$1"; local path="$2"; local required="${3:-true}"
  if [[ -e "$path" ]]; then
    echo "[OK] $label"
    PASS=$((PASS+1))
  elif [[ "$required" == "true" ]]; then
    echo "[FAIL] $label -> $path"
    FAIL=$((FAIL+1))
  else
    echo "[WARN] $label -> $path"
    WARN=$((WARN+1))
  fi
}

check_absent_path() {
  local label="$1"; local path="$2"
  if [[ -e "$path" ]]; then
    echo "[FAIL] $label -> $path"
    FAIL=$((FAIL+1))
  else
    echo "[OK] $label"
    PASS=$((PASS+1))
  fi
}

check_condition() {
  local label="$1"; local condition="$2"; local detail="${3:-}"
  if [[ "$condition" == "true" ]]; then
    echo "[OK] $label"
    PASS=$((PASS+1))
  else
    if [[ -n "$detail" ]]; then
      echo "[FAIL] $label -> $detail"
    else
      echo "[FAIL] $label"
    fi
    FAIL=$((FAIL+1))
  fi
}

warn_note() {
  local message="$1"
  echo "[WARN] ${message}"
  WARN=$((WARN+1))
}

info_note() {
  local message="$1"
  echo "[INFO] ${message}"
}

normalize_path() {
  local value="${1:-}"
  if [[ -z "$value" ]]; then
    return 0
  fi

  local python_bin=""
  if python_bin="$(pick_python 2>/dev/null)"; then
    "${python_bin}" - "$value" "$PWD" <<'PY'
import os
import re
import sys

value = (sys.argv[1] or "").strip()
cwd = sys.argv[2]
normalized = value.replace("\\", "/")

if re.match(r"^[A-Za-z]:/", normalized):
    drive = normalized[0].lower()
    rest = normalized[2:].lstrip("/")
    candidate = f"/mnt/{drive}/{rest}"
elif re.match(r"^/[A-Za-z]/", normalized):
    drive = normalized[1].lower()
    rest = normalized[3:].lstrip("/")
    candidate = f"/mnt/{drive}/{rest}"
elif os.path.isabs(normalized):
    candidate = normalized
else:
    candidate = os.path.abspath(os.path.join(cwd, normalized))

candidate = re.sub(r"/+", "/", candidate).rstrip("/")
print(candidate.lower() if candidate else candidate)
PY
    return 0
  fi

  printf '%s' "$value" | tr '\\' '/' | sed 's#//*#/#g; s#/$##' | tr '[:upper:]' '[:lower:]'
}

json_query_lines_from_file() {
  local json_path="$1"
  local expr="$2"
  if [[ ! -f "$json_path" ]]; then
    return 1
  fi

  if command -v python3 >/dev/null 2>&1; then
    python3 - "$json_path" "$expr" <<'PY'
import json, sys
path, expr = sys.argv[1], sys.argv[2]
with open(path, encoding='utf-8-sig') as fh:
    data = json.load(fh)
value = data
for part in expr.split('.'):
    value = value[part]
if isinstance(value, list):
    for item in value:
        print('true' if item is True else 'false' if item is False else item)
elif isinstance(value, bool):
    print('true' if value else 'false')
elif value is None:
    pass
else:
    print(value)
PY
    return $?
  elif command -v python >/dev/null 2>&1; then
    python - "$json_path" "$expr" <<'PY'
import json, sys
path, expr = sys.argv[1], sys.argv[2]
with open(path, encoding='utf-8-sig') as fh:
    data = json.load(fh)
value = data
for part in expr.split('.'):
    value = value[part]
if isinstance(value, list):
    for item in value:
        print('true' if item is True else 'false' if item is False else item)
elif isinstance(value, bool):
    print('true' if value else 'false')
elif value is None:
    pass
else:
    print(value)
PY
    return $?
  elif pick_powershell >/dev/null 2>&1; then
    run_powershell_command '
param([string]$Path,[string]$Expr)
$raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
$value = $raw | ConvertFrom-Json
foreach ($part in $Expr.Split(".")) {
  $value = $value.$part
}
if ($value -is [System.Collections.IEnumerable] -and -not ($value -is [string])) {
  foreach ($item in $value) {
    if ($item -is [bool]) {
      if ($item) { "true" } else { "false" }
    } elseif ($null -ne $item) {
      $item
    }
  }
} elseif ($value -is [bool]) {
  if ($value) { "true" } else { "false" }
} elseif ($null -ne $value) {
  $value
}
' -Args "$json_path" "$expr"
    return $?
  fi

  return 1
}

json_query_scalar_from_file() {
  local json_path="$1"
  local expr="$2"
  json_query_lines_from_file "$json_path" "$expr" | head -n 1
}

pick_python() {
  pick_supported_python
}

adapter_query() {
  local property="$1"
  adapter_query_for_host "${HOST_ID}" "${property}"
}

run_runtime_neutral_freshness_gate() {
  local gate_path="${SCRIPT_DIR}/scripts/verify/runtime_neutral/freshness_gate.py"
  local python_bin=""
  if [[ ! -f "${gate_path}" ]]; then
    return 127
  fi
  if ! python_bin="$(pick_python)"; then
    return 127
  fi
  "${python_bin}" "${gate_path}" --target-root "${TARGET_ROOT}"
}

run_runtime_neutral_coherence_gate() {
  local gate_path="${SCRIPT_DIR}/scripts/verify/runtime_neutral/coherence_gate.py"
  local python_bin=""
  if [[ ! -f "${gate_path}" ]]; then
    return 127
  fi
  if ! python_bin="$(pick_python)"; then
    return 127
  fi
  "${python_bin}" "${gate_path}" --target-root "${TARGET_ROOT}"
}

run_runtime_neutral_bootstrap_doctor() {
  local gate_path="${SCRIPT_DIR}/scripts/verify/runtime_neutral/bootstrap_doctor.py"
  local python_bin=""
  if [[ ! -f "${gate_path}" ]]; then
    return 127
  fi
  if ! python_bin="$(pick_python)"; then
    return 127
  fi
  "${python_bin}" "${gate_path}" --target-root "${TARGET_ROOT}" --write-artifacts
}

validate_runtime_receipt() {
  local target_rel="skills/vibe"
  local receipt_rel="skills/vibe/outputs/runtime-freshness-receipt.json"
  local repo_governance="${SCRIPT_DIR}/config/version-governance.json"
  if [[ -f "$repo_governance" ]]; then
    local configured_repo_target_rel
    configured_repo_target_rel="$(json_query_scalar_from_file "$repo_governance" 'runtime.installed_runtime.target_relpath' 2>/dev/null || true)"
    if [[ -n "$configured_repo_target_rel" ]]; then
      target_rel="$configured_repo_target_rel"
    fi

    local configured_repo_receipt_rel
    configured_repo_receipt_rel="$(json_query_scalar_from_file "$repo_governance" 'runtime.installed_runtime.receipt_relpath' 2>/dev/null || true)"
    if [[ -n "$configured_repo_receipt_rel" ]]; then
      receipt_rel="$configured_repo_receipt_rel"
    fi
  fi

  local installed_governance="${TARGET_ROOT}/${target_rel}/config/version-governance.json"
  if [[ -f "$installed_governance" ]]; then
    local configured_target_rel
    configured_target_rel="$(json_query_scalar_from_file "$installed_governance" 'runtime.installed_runtime.target_relpath' 2>/dev/null || true)"
    if [[ -n "$configured_target_rel" ]]; then
      target_rel="$configured_target_rel"
      installed_governance="${TARGET_ROOT}/${target_rel}/config/version-governance.json"
    fi

    local configured_receipt_rel
    configured_receipt_rel="$(json_query_scalar_from_file "$installed_governance" 'runtime.installed_runtime.receipt_relpath' 2>/dev/null || true)"
    if [[ -n "$configured_receipt_rel" ]]; then
      receipt_rel="$configured_receipt_rel"
    fi
  fi

  local receipt_path="${TARGET_ROOT}/${receipt_rel}"
  if [[ ! -f "$receipt_path" ]]; then
    if [[ "$SKIP_RUNTIME_FRESHNESS_GATE" == "true" ]]; then
      warn_note "vibe runtime freshness receipt unavailable because the gate was skipped by request."
      return
    fi
    if ! canonical_repo_available "${SCRIPT_DIR}"; then
      warn_note "vibe runtime freshness receipt unavailable because check.sh is not running from the canonical repo root."
      return
    fi
    if ! pick_powershell >/dev/null 2>&1; then
      warn_note "vibe runtime freshness receipt unavailable because pwsh is not installed and no compatible PowerShell host is available in this shell environment."
      return
    fi
    echo "[FAIL] vibe runtime freshness receipt -> $receipt_path"
    FAIL=$((FAIL+1))
    return
  fi
  echo "[OK] vibe runtime freshness receipt"
  PASS=$((PASS+1))

  local receipt_gate_result
  receipt_gate_result="$(json_query_scalar_from_file "$receipt_path" 'gate_result' 2>/dev/null || true)"
  if [[ -z "$receipt_gate_result" ]]; then
    warn_note "unable to parse runtime freshness receipt for semantic validation."
    return
  fi

  check_condition "vibe runtime freshness receipt gate_result" "$([[ "$receipt_gate_result" == "PASS" ]] && echo true || echo false)" "$receipt_gate_result"

  local receipt_version expected_receipt_version
  receipt_version="$(json_query_scalar_from_file "$receipt_path" 'receipt_version' 2>/dev/null || true)"
  expected_receipt_version='1'
  if [[ -f "$repo_governance" ]]; then
    local configured_receipt_version
    configured_receipt_version="$(json_query_scalar_from_file "$repo_governance" 'runtime.installed_runtime.receipt_contract_version' 2>/dev/null || true)"
    if [[ -n "$configured_receipt_version" ]]; then
      expected_receipt_version="$configured_receipt_version"
    fi
  fi
  check_condition "vibe runtime freshness receipt version" "$([[ "$receipt_version" =~ ^[0-9]+$ && "$receipt_version" -ge "$expected_receipt_version" ]] && echo true || echo false)" "${receipt_version:-<missing>}"

  local receipt_target_root receipt_installed_root
  receipt_target_root="$(json_query_scalar_from_file "$receipt_path" 'target_root' 2>/dev/null || true)"
  receipt_installed_root="$(json_query_scalar_from_file "$receipt_path" 'installed_root' 2>/dev/null || true)"
  local expected_target_root expected_installed_root
  expected_target_root="$(normalize_path "$TARGET_ROOT")"
  expected_installed_root="$(normalize_path "${TARGET_ROOT}/${target_rel}")"
  check_condition "vibe runtime freshness receipt target_root" "$([[ "$(normalize_path "$receipt_target_root")" == "$expected_target_root" ]] && echo true || echo false)" "${receipt_target_root:-<missing>}"
  check_condition "vibe runtime freshness receipt installed_root" "$([[ "$(normalize_path "$receipt_installed_root")" == "$expected_installed_root" ]] && echo true || echo false)" "${receipt_installed_root:-<missing>}"

  local installed_version installed_updated receipt_release_version receipt_release_updated
  installed_version="$(json_query_scalar_from_file "$installed_governance" 'release.version' 2>/dev/null || true)"
  installed_updated="$(json_query_scalar_from_file "$installed_governance" 'release.updated' 2>/dev/null || true)"
  receipt_release_version="$(json_query_scalar_from_file "$receipt_path" 'release.version' 2>/dev/null || true)"
  receipt_release_updated="$(json_query_scalar_from_file "$receipt_path" 'release.updated' 2>/dev/null || true)"

  if [[ -n "$installed_version" ]]; then
    check_condition "vibe runtime freshness receipt release.version" "$([[ "$receipt_release_version" == "$installed_version" ]] && echo true || echo false)" "${receipt_release_version:-<missing>}"
  fi
  if [[ -n "$installed_updated" ]]; then
    check_condition "vibe runtime freshness receipt release.updated" "$([[ "$receipt_release_updated" == "$installed_updated" ]] && echo true || echo false)" "${receipt_release_updated:-<missing>}"
  fi
}

show_installed_runtime_upgrade_hint() {
  local repo_governance="${SCRIPT_DIR}/config/version-governance.json"
  [[ -f "$repo_governance" ]] || return

  local target_rel='skills/vibe'
  local configured_target_rel
  configured_target_rel="$(json_query_scalar_from_file "$repo_governance" 'runtime.installed_runtime.target_relpath' 2>/dev/null || true)"
  if [[ -n "$configured_target_rel" ]]; then
    target_rel="$configured_target_rel"
  fi

  local installed_governance="${TARGET_ROOT}/${target_rel}/config/version-governance.json"
  [[ -f "$installed_governance" ]] || return

  local repo_version repo_updated installed_version installed_updated
  repo_version="$(json_query_scalar_from_file "$repo_governance" 'release.version' 2>/dev/null || true)"
  repo_updated="$(json_query_scalar_from_file "$repo_governance" 'release.updated' 2>/dev/null || true)"
  installed_version="$(json_query_scalar_from_file "$installed_governance" 'release.version' 2>/dev/null || true)"
  installed_updated="$(json_query_scalar_from_file "$installed_governance" 'release.updated' 2>/dev/null || true)"

  if [[ -n "$repo_version" && "$repo_version" != "$installed_version" ]] || [[ -n "$repo_updated" && "$repo_updated" != "$installed_updated" ]]; then
    warn_note "installed runtime release differs from canonical repo release (installed=${installed_version:-<missing>}/${installed_updated:-<missing>}, repo=${repo_version:-<missing>}/${repo_updated:-<missing>}). Re-run install.sh or one-shot-setup.sh for TARGET_ROOT=${TARGET_ROOT} before treating freshness failures as receipt-only issues."
  fi
}

run_runtime_freshness_gate() {
  if [[ "$SKIP_RUNTIME_FRESHNESS_GATE" == "true" ]]; then
    warn_note 'runtime freshness gate skipped by request.'
    return
  fi

  if ! canonical_repo_available "${SCRIPT_DIR}"; then
    warn_note 'runtime freshness gate skipped: run canonical repo check.sh to execute freshness verification.'
    return
  fi

  local governance_path="${SCRIPT_DIR}/config/version-governance.json"
  local gate_rel='scripts/verify/vibe-installed-runtime-freshness-gate.ps1'
  if [[ -f "$governance_path" ]]; then
    local configured_gate
    configured_gate="$(json_query_scalar_from_file "$governance_path" 'runtime.installed_runtime.post_install_gate' 2>/dev/null || true)"
    if [[ -n "$configured_gate" ]]; then
      gate_rel="$configured_gate"
    fi
  fi

  local gate_path="${SCRIPT_DIR}/${gate_rel}"
  if [[ ! -f "$gate_path" ]]; then
    echo "[FAIL] vibe runtime freshness gate script -> $gate_path"
    FAIL=$((FAIL+1))
    return
  fi

  if run_runtime_neutral_freshness_gate; then
    echo "[OK] vibe installed runtime freshness gate"
    PASS=$((PASS+1))
  elif [[ $? -eq 127 ]]; then
    if ! pick_powershell >/dev/null 2>&1; then
      warn_note 'runtime freshness gate skipped: neither Python runtime-neutral gate nor a PowerShell fallback is available.'
      return
    fi
    if run_powershell_file "$gate_path" -TargetRoot "$TARGET_ROOT"; then
      echo "[OK] vibe installed runtime freshness gate"
      PASS=$((PASS+1))
    else
      echo "[FAIL] vibe installed runtime freshness gate"
      FAIL=$((FAIL+1))
    fi
  else
    echo "[FAIL] vibe installed runtime freshness gate"
    FAIL=$((FAIL+1))
  fi
}

run_runtime_coherence_gate() {
  if ! canonical_repo_available "${SCRIPT_DIR}"; then
    warn_note 'runtime coherence gate skipped: run canonical repo check.sh to execute coherence verification.'
    return
  fi

  local governance_path="${SCRIPT_DIR}/config/version-governance.json"
  local gate_rel='scripts/verify/vibe-release-install-runtime-coherence-gate.ps1'
  if [[ -f "$governance_path" ]]; then
    local configured_gate
    configured_gate="$(json_query_scalar_from_file "$governance_path" 'runtime.installed_runtime.coherence_gate' 2>/dev/null || true)"
    if [[ -n "$configured_gate" ]]; then
      gate_rel="$configured_gate"
    fi
  fi

  local gate_path="${SCRIPT_DIR}/${gate_rel}"
  if [[ ! -f "$gate_path" ]]; then
    echo "[FAIL] vibe runtime coherence gate script -> $gate_path"
    FAIL=$((FAIL+1))
    return
  fi

  if run_runtime_neutral_coherence_gate; then
    echo "[OK] vibe release/install/runtime coherence gate"
    PASS=$((PASS+1))
  elif [[ $? -eq 127 ]]; then
    if ! pick_powershell >/dev/null 2>&1; then
      warn_note 'runtime coherence gate skipped: neither Python runtime-neutral gate nor a PowerShell fallback is available.'
      return
    fi
    if run_powershell_file "$gate_path" -TargetRoot "$TARGET_ROOT"; then
      echo "[OK] vibe release/install/runtime coherence gate"
      PASS=$((PASS+1))
    else
      echo "[FAIL] vibe release/install/runtime coherence gate"
      FAIL=$((FAIL+1))
    fi
  else
    echo "[FAIL] vibe release/install/runtime coherence gate"
    FAIL=$((FAIL+1))
  fi
}

ADAPTER_CHECK_MODE="$(adapter_query check_mode)"

echo "=== VCO Adapter Health Check ==="
echo "Host: ${HOST_ID}"
echo "Mode: ${ADAPTER_CHECK_MODE}"
echo "Target: ${TARGET_ROOT}"
echo "SkipRuntimeFreshnessGate: ${SKIP_RUNTIME_FRESHNESS_GATE}"
echo "Deep: ${DEEP}"

runtime_target_rel="skills/vibe"
repo_governance_path="${SCRIPT_DIR}/config/version-governance.json"
if [[ -f "$repo_governance_path" ]]; then
  configured_runtime_target_rel="$(json_query_scalar_from_file "$repo_governance_path" 'runtime.installed_runtime.target_relpath' 2>/dev/null || true)"
  if [[ -n "$configured_runtime_target_rel" ]]; then
    runtime_target_rel="$configured_runtime_target_rel"
  fi
fi

runtime_skill_root="${TARGET_ROOT}/${runtime_target_rel}"
runtime_nested_skill_root="${runtime_skill_root}/bundled/skills/vibe"

if [[ "${ADAPTER_CHECK_MODE}" == "governed" ]]; then
  check_path "settings.json" "${TARGET_ROOT}/settings.json"
fi
if [[ "${ADAPTER_CHECK_MODE}" == "preview-guidance" ]]; then
  if [[ "${HOST_ID}" == "opencode" ]]; then
    info_note "opencode preview now runs as skills-only activation; the real opencode.json stays untouched and sidecar state is verified"
  elif [[ "${HOST_ID}" == "claude-code" ]]; then
    info_note "claude-code preview now verifies sidecar state plus a managed settings.json and hook surface"
  else
    info_note "${HOST_ID} preview now runs as skills-only activation; host-native config files stay untouched and sidecar state is verified"
  fi
fi
if [[ "${ADAPTER_CHECK_MODE}" == "runtime-core" ]]; then
  info_note "${HOST_ID} runtime-core now verifies skill-native activation and sidecar state only; host-native workflow/config files are intentionally absent"
fi
if [[ "${HOST_ID}" == "claude-code" || "${HOST_ID}" == "cursor" || "${HOST_ID}" == "windsurf" || "${HOST_ID}" == "openclaw" || "${HOST_ID}" == "opencode" ]]; then
  check_path "host settings sidecar" "${TARGET_ROOT}/.vibeskills/host-settings.json"
fi
if [[ "${HOST_ID}" == "claude-code" ]]; then
  check_path "settings.json" "${TARGET_ROOT}/settings.json"
  managed_host_id="$(json_query_scalar_from_file "${TARGET_ROOT}/settings.json" 'vibeskills.host_id' 2>/dev/null || true)"
  if [[ "${managed_host_id}" == "claude-code" ]]; then
    echo "[OK] settings.json managed vibeskills node"
    PASS=$((PASS+1))
  else
    echo "[FAIL] settings.json managed vibeskills node"
    FAIL=$((FAIL+1))
  fi
  hook_script_path="${TARGET_ROOT}/hooks/write-guard.js"
  check_path "managed Claude hook script" "${hook_script_path}"
  python_bin_for_hook_check="$(pick_python_for_adapter || true)"
  if [[ -z "${python_bin_for_hook_check}" ]]; then
    print_python_requirement_error "Claude hook verification"
    echo "[FAIL] settings.json managed Claude hook command"
    FAIL=$((FAIL+1))
  else
    hook_check_result="$(
    "${python_bin_for_hook_check}" - "${TARGET_ROOT}/settings.json" "${hook_script_path}" <<'PY' 2>/dev/null || true
import json, sys
settings_path, hook_path = sys.argv[1], sys.argv[2]
with open(settings_path, encoding='utf-8-sig') as fh:
    payload = json.load(fh)
hooks = payload.get("hooks", {})
entries = hooks.get("PreToolUse", [])
expected = f"node {hook_path}"
for entry in entries:
    if not isinstance(entry, dict):
        continue
    if str(entry.get("description") or "").strip() != "VibeSkills managed write guard":
        continue
    nested = entry.get("hooks")
    if not isinstance(nested, list) or not nested:
        continue
    first = nested[0]
    if not isinstance(first, dict):
        continue
    if str(first.get("command") or "").strip() == expected:
        print("ok")
        raise SystemExit(0)
print("missing")
raise SystemExit(1)
PY
    )"
    if [[ "${hook_check_result}" == "ok" ]]; then
      echo "[OK] settings.json managed Claude hook command"
      PASS=$((PASS+1))
    else
      echo "[FAIL] settings.json managed Claude hook command"
      FAIL=$((FAIL+1))
    fi
  fi
fi
check_path "host closure manifest" "${TARGET_ROOT}/.vibeskills/host-closure.json"
if [[ -f "${TARGET_ROOT}/.vibeskills/host-closure.json" ]]; then
  closure_state="$(json_query_scalar_from_file "${TARGET_ROOT}/.vibeskills/host-closure.json" 'host_closure_state' 2>/dev/null || true)"
  if [[ -n "${closure_state}" ]]; then
    if [[ "${closure_state}" == "closed_ready" ]]; then
      echo "[OK] host closure state -> ${closure_state}"
      PASS=$((PASS+1))
    else
      warn_note "host closure state -> ${closure_state}"
    fi
  fi
  wrapper_launcher="$(json_query_scalar_from_file "${TARGET_ROOT}/.vibeskills/host-closure.json" 'specialist_wrapper.launcher_path' 2>/dev/null || true)"
  if [[ -n "${wrapper_launcher}" ]]; then
    check_path "specialist wrapper launcher" "${wrapper_launcher}"
  fi
fi
if [[ "${ADAPTER_CHECK_MODE}" == "governed" ]]; then
  check_path "plugins manifest" "${TARGET_ROOT}/config/plugins-manifest.codex.json"
fi
check_codex_duplicate_skill_surface
check_path "upstream lock" "${TARGET_ROOT}/config/upstream-lock.json"
check_path "vibe version governance config" "${TARGET_ROOT}/${runtime_target_rel}/config/version-governance.json"
installed_runtime_governance="${runtime_skill_root}/config/version-governance.json"
runtime_release_ledger_required="true"
if [[ -f "${installed_runtime_governance}" ]]; then
  if ! json_query_lines_from_file "${installed_runtime_governance}" 'packaging.mirror.directories' 2>/dev/null | grep -Fxq 'references' && \
     ! json_query_lines_from_file "${installed_runtime_governance}" 'packaging.allow_bundled_only' 2>/dev/null | grep -Fxq 'references/release-ledger.jsonl'; then
    runtime_release_ledger_required="false"
  fi
fi
if [[ "${runtime_release_ledger_required}" == "true" ]]; then
  check_path "vibe release ledger" "${runtime_skill_root}/references/release-ledger.jsonl"
else
  echo "[OK] vibe release ledger skipped (not packaged into installed runtime contract)"
  PASS=$((PASS+1))
fi
for n in vibe dialectic local-vco-roles spec-kit-vibe-compat superclaude-framework-compat ralph-loop cancel-ralph tdd-guide think-harder; do
  check_path "skill/${n}" "${TARGET_ROOT}/skills/${n}/SKILL.md"
done
check_path "vibe router script" "${runtime_skill_root}/scripts/router/resolve-pack-route.ps1"
check_path "vibe memory governance config" "${runtime_skill_root}/config/memory-governance.json"
check_path "vibe data scale overlay config" "${runtime_skill_root}/config/data-scale-overlay.json"
check_path "vibe quality debt overlay config" "${runtime_skill_root}/config/quality-debt-overlay.json"
check_path "vibe framework interop overlay config" "${runtime_skill_root}/config/framework-interop-overlay.json"
check_path "vibe ml lifecycle overlay config" "${runtime_skill_root}/config/ml-lifecycle-overlay.json"
check_path "vibe python clean code overlay config" "${runtime_skill_root}/config/python-clean-code-overlay.json"
check_path "vibe system design overlay config" "${runtime_skill_root}/config/system-design-overlay.json"
check_path "vibe cuda kernel overlay config" "${runtime_skill_root}/config/cuda-kernel-overlay.json"
check_path "vibe observability policy config" "${runtime_skill_root}/config/observability-policy.json"
check_path "vibe heartbeat policy config" "${runtime_skill_root}/config/heartbeat-policy.json"
check_path "vibe deep discovery policy config" "${runtime_skill_root}/config/deep-discovery-policy.json"
check_path "vibe llm acceleration policy config" "${runtime_skill_root}/config/llm-acceleration-policy.json"
check_path "vibe capability catalog config" "${runtime_skill_root}/config/capability-catalog.json"
check_path "vibe retrieval policy config" "${runtime_skill_root}/config/retrieval-policy.json"
check_path "vibe retrieval intent profiles config" "${runtime_skill_root}/config/retrieval-intent-profiles.json"
check_path "vibe retrieval source registry config" "${runtime_skill_root}/config/retrieval-source-registry.json"
check_path "vibe retrieval rerank weights config" "${runtime_skill_root}/config/retrieval-rerank-weights.json"
check_path "vibe exploration policy config" "${runtime_skill_root}/config/exploration-policy.json"
check_path "vibe exploration intent profiles config" "${runtime_skill_root}/config/exploration-intent-profiles.json"
check_path "vibe exploration domain map config" "${runtime_skill_root}/config/exploration-domain-map.json"
if [[ -d "${runtime_nested_skill_root}" ]]; then
  check_path "vibe bundled retrieval intent profiles config" "${runtime_nested_skill_root}/config/retrieval-intent-profiles.json"
  check_path "vibe bundled retrieval source registry config" "${runtime_nested_skill_root}/config/retrieval-source-registry.json"
  check_path "vibe bundled retrieval rerank weights config" "${runtime_nested_skill_root}/config/retrieval-rerank-weights.json"
  check_path "vibe bundled exploration policy config" "${runtime_nested_skill_root}/config/exploration-policy.json"
  check_path "vibe bundled exploration intent profiles config" "${runtime_nested_skill_root}/config/exploration-intent-profiles.json"
  check_path "vibe bundled exploration domain map config" "${runtime_nested_skill_root}/config/exploration-domain-map.json"
  check_path "vibe bundled llm acceleration policy config" "${runtime_nested_skill_root}/config/llm-acceleration-policy.json"
  check_absent_path "vibe nested bundled skill entrypoint hidden" "${runtime_nested_skill_root}/SKILL.md"
  check_path "vibe nested bundled skill runtime mirror" "${runtime_nested_skill_root}/SKILL.runtime-mirror.md"
else
  echo "[OK] vibe nested bundled config checks skipped (target absent; policy=optional)"
  PASS=$((PASS+1))
fi
for n in brainstorming writing-plans subagent-driven-development systematic-debugging; do
  check_path "workflow/${n}" "${TARGET_ROOT}/skills/${n}/SKILL.md"
done
if [[ "${PROFILE}" == "full" ]]; then
  for n in requesting-code-review receiving-code-review verification-before-completion; do
    check_path "optional/${n}" "${TARGET_ROOT}/skills/${n}/SKILL.md" false
  done
fi
if [[ "${HOST_ID}" == "opencode" ]]; then
  if [[ "${ADAPTER_CHECK_MODE}" != "preview-guidance" ]]; then
    for n in vibe vibe-implement vibe-review; do
      check_path "opencode command/${n}" "${TARGET_ROOT}/commands/${n}.md"
      check_path "opencode compat command/${n}" "${TARGET_ROOT}/command/${n}.md"
    done
    for n in vibe-plan vibe-implement vibe-review; do
      check_path "opencode agent/${n}" "${TARGET_ROOT}/agents/${n}.md"
      check_path "opencode compat agent/${n}" "${TARGET_ROOT}/agent/${n}.md"
    done
  fi
  check_path "opencode preview config example" "${TARGET_ROOT}/opencode.json.example"
fi
if [[ "${ADAPTER_CHECK_MODE}" == "governed" ]]; then
  check_path "rules/common" "${TARGET_ROOT}/rules/common/agents.md"
  check_path "mcp template" "${TARGET_ROOT}/mcp/servers.template.json"
fi

show_installed_runtime_upgrade_hint
run_runtime_freshness_gate
validate_runtime_receipt
run_runtime_coherence_gate

if [[ "${ADAPTER_CHECK_MODE}" == "governed" ]] && command -v npm >/dev/null 2>&1; then
  echo "[OK] npm"
  PASS=$((PASS+1))
elif [[ "${ADAPTER_CHECK_MODE}" == "governed" ]]; then
  echo "[WARN] npm not found (needed for claude-flow)"
  WARN=$((WARN+1))
else
  echo "[OK] npm check skipped for non-governed adapter mode"
  PASS=$((PASS+1))
fi

if [[ "${DEEP}" == "true" ]]; then
  if [[ "${ADAPTER_CHECK_MODE}" != "governed" ]]; then
    echo "[WARN] deep doctor skipped for adapter mode '${ADAPTER_CHECK_MODE}'"
    WARN=$((WARN+1))
  else
    doctor_path="${SCRIPT_DIR}/scripts/verify/vibe-bootstrap-doctor-gate.ps1"
    if [[ ! -f "${doctor_path}" ]]; then
      echo "[FAIL] vibe bootstrap doctor gate -> ${doctor_path}"
      FAIL=$((FAIL+1))
    elif run_runtime_neutral_bootstrap_doctor; then
      echo "[OK] vibe bootstrap doctor gate"
      PASS=$((PASS+1))
    elif [[ $? -eq 127 ]]; then
      if ! pick_powershell >/dev/null 2>&1; then
        echo "[WARN] vibe bootstrap doctor gate skipped because neither the Python runtime-neutral doctor nor a PowerShell host is available in this shell environment."
        WARN=$((WARN+1))
      elif run_powershell_file "${doctor_path}" -TargetRoot "${TARGET_ROOT}" -WriteArtifacts; then
        echo "[OK] vibe bootstrap doctor gate"
        PASS=$((PASS+1))
      else
        echo "[FAIL] vibe bootstrap doctor gate"
        FAIL=$((FAIL+1))
      fi
    else
      echo "[FAIL] vibe bootstrap doctor gate"
      WARN=$((WARN+1))
      FAIL=$((FAIL+1))
    fi
  fi
fi

echo "Result: ${PASS} passed, ${FAIL} failed, ${WARN} warnings"
[[ ${FAIL} -eq 0 ]]
