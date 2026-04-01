#!/usr/bin/env bash
set -euo pipefail

PROFILE="full"
HOST_ID="codex"
INSTALL_EXTERNAL="false"
STRICT_OFFLINE="false"
REQUIRE_CLOSED_READY="false"
ALLOW_EXTERNAL_SKILL_FALLBACK="false"
SKIP_RUNTIME_FRESHNESS_GATE="false"
TARGET_ROOT=""
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ADAPTER_RESOLVER="${SCRIPT_DIR}/scripts/common/resolve_vgo_adapter.py"
ADAPTER_INSTALLER="${SCRIPT_DIR}/scripts/install/install_vgo_adapter.py"
PYTHON_MIN_MAJOR=3
PYTHON_MIN_MINOR=10

if [[ ! -f "${ADAPTER_RESOLVER}" ]]; then
  echo "[FAIL] Missing adapter resolver: ${ADAPTER_RESOLVER}" >&2
  exit 1
fi
if [[ ! -f "${ADAPTER_INSTALLER}" ]]; then
  echo "[FAIL] Missing adapter installer: ${ADAPTER_INSTALLER}" >&2
  exit 1
fi

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
    --install-external) INSTALL_EXTERNAL="true"; shift ;;
    --strict-offline) STRICT_OFFLINE="true"; shift ;;
    --require-closed-ready) REQUIRE_CLOSED_READY="true"; shift ;;
    --allow-external-skill-fallback) ALLOW_EXTERNAL_SKILL_FALLBACK="true"; shift ;;
    --skip-runtime-freshness-gate) SKIP_RUNTIME_FRESHNESS_GATE="true"; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

pick_python_for_adapter() {
  pick_supported_python
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
  "${python_bin}" "${ADAPTER_RESOLVER}" --repo-root "${SCRIPT_DIR}" --host "${host_id}" --property "${property}"
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
  resolve_canonical_repo_root "${1:-}" >/dev/null
}

resolve_canonical_repo_root() {
  local current="${1:-}"
  [[ -n "${current}" ]] || return 1
  current="$(cd "${current}" 2>/dev/null && pwd || true)"
  [[ -n "${current}" ]] || return 1

  while [[ -n "${current}" ]]; do
    if [[ -e "${current}/.git" && -f "${current}/config/version-governance.json" ]]; then
      printf '%s' "${current}"
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

assert_target_root_matches_host_intent() {
  local target_root="$1"
  local host_id="$2"
  local leaf normalized_target is_codex_root is_claude_root is_cursor_root is_windsurf_root is_openclaw_root
  leaf="$(basename "${target_root}")"
  leaf="$(printf '%s' "${leaf}" | tr '[:upper:]' '[:lower:]')"
  normalized_target="$(printf '%s' "${target_root}" | tr '\\' '/' | tr '[:upper:]' '[:lower:]')"
  normalized_target="${normalized_target%/}"
  is_codex_root="false"
  is_claude_root="false"
  is_cursor_root="false"
  is_windsurf_root="false"
  is_openclaw_root="false"
  [[ "${leaf}" == ".codex" ]] && is_codex_root="true"
  [[ "${leaf}" == ".claude" ]] && is_claude_root="true"
  [[ "${leaf}" == ".cursor" ]] && is_cursor_root="true"
  [[ "${normalized_target}" == */.codeium/windsurf ]] && is_windsurf_root="true"
  [[ "${leaf}" == ".openclaw" ]] && is_openclaw_root="true"
  local is_opencode_root="false"
  [[ "${leaf}" == ".opencode" || "${normalized_target}" == */.config/opencode ]] && is_opencode_root="true"
  if [[ "${host_id}" == "codex" && ( "${is_claude_root}" == "true" || "${is_windsurf_root}" == "true" || "${is_openclaw_root}" == "true" ) ]]; then
    echo "[FAIL] Target root '${target_root}' looks like a non-Codex host root, but host='codex'." >&2
    exit 1
  fi
  if [[ "${host_id}" == "codex" && "${is_cursor_root}" == "true" ]]; then
    echo "[FAIL] Target root '${target_root}' looks like a Cursor home, but host='codex'." >&2
    echo "[FAIL] Pass --host cursor for preview guidance or use a Codex target root." >&2
    exit 1
  fi
  if [[ "${host_id}" == "claude-code" && ( "${is_codex_root}" == "true" || "${is_windsurf_root}" == "true" || "${is_openclaw_root}" == "true" ) ]]; then
    echo "[FAIL] Target root '${target_root}' looks like a non-Claude host root, but host='claude-code'." >&2
    exit 1
  fi
  if [[ "${host_id}" == "codex" && "${is_opencode_root}" == "true" ]]; then
    echo "[FAIL] Target root '${target_root}' looks like an OpenCode root, but host='codex'." >&2
    echo "[FAIL] Pass --host opencode for the OpenCode preview lane or use a Codex target root." >&2
    exit 1
  fi
  if [[ "${host_id}" == "claude-code" && "${is_codex_root}" == "true" ]]; then
    echo "[FAIL] Target root '${target_root}' looks like a Codex home, but host='claude-code'." >&2
    echo "[FAIL] Use --host codex for the official closure lane or choose a Claude Code target root." >&2
    exit 1
  fi
  if [[ "${host_id}" == "claude-code" && "${is_opencode_root}" == "true" ]]; then
    echo "[FAIL] Target root '${target_root}' looks like an OpenCode root, but host='claude-code'." >&2
    echo "[FAIL] Use --host opencode for the OpenCode preview lane or choose a Claude Code target root." >&2
    exit 1
  fi
  if [[ "${host_id}" == "claude-code" && "${is_cursor_root}" == "true" ]]; then
    echo "[FAIL] Target root '${target_root}' looks like a Cursor home, but host='claude-code'." >&2
    echo "[FAIL] Pass --host cursor for Cursor preview guidance or choose a Claude Code target root." >&2
    exit 1
  fi
  if [[ "${host_id}" == "cursor" && "${is_codex_root}" == "true" ]]; then
    echo "[FAIL] Target root '${target_root}' looks like a Codex home, but host='cursor'." >&2
    echo "[FAIL] Use --host codex for the official closure lane or choose a Cursor target root." >&2
    exit 1
  fi
  if [[ "${host_id}" == "cursor" && "${is_claude_root}" == "true" ]]; then
    echo "[FAIL] Target root '${target_root}' looks like a Claude Code home, but host='cursor'." >&2
    echo "[FAIL] Pass --host claude-code for Claude preview guidance or choose a Cursor target root." >&2
    exit 1
  fi
  if [[ "${host_id}" == "cursor" && "${is_windsurf_root}" == "true" ]]; then
    echo "[FAIL] Target root '${target_root}' looks like a Windsurf home, but host='cursor'." >&2
    echo "[FAIL] Pass --host windsurf for preview runtime-core or choose a Cursor target root." >&2
    exit 1
  fi
  if [[ "${host_id}" == "cursor" && "${is_openclaw_root}" == "true" ]]; then
    echo "[FAIL] Target root '${target_root}' looks like an OpenClaw home, but host='cursor'." >&2
    echo "[FAIL] Pass --host openclaw for runtime-core guidance or choose a Cursor target root." >&2
    exit 1
  fi
  if [[ "${host_id}" == "windsurf" && ( "${is_codex_root}" == "true" || "${is_claude_root}" == "true" || "${is_openclaw_root}" == "true" ) ]]; then
    echo "[FAIL] Target root '${target_root}' looks like a non-Windsurf host root, but host='windsurf'." >&2
    exit 1
  fi
  if [[ "${host_id}" == "windsurf" && "${is_cursor_root}" == "true" ]]; then
    echo "[FAIL] Target root '${target_root}' looks like a Cursor home, but host='windsurf'." >&2
    echo "[FAIL] Pass --host cursor for preview guidance or choose a Windsurf target root." >&2
    exit 1
  fi
  if [[ "${host_id}" == "openclaw" && ( "${is_codex_root}" == "true" || "${is_claude_root}" == "true" || "${is_windsurf_root}" == "true" ) ]]; then
    echo "[FAIL] Target root '${target_root}' looks like a non-OpenClaw host root, but host='openclaw'." >&2
    exit 1
  fi
  if [[ "${host_id}" == "openclaw" && "${is_cursor_root}" == "true" ]]; then
    echo "[FAIL] Target root '${target_root}' looks like a Cursor home, but host='openclaw'." >&2
    echo "[FAIL] Pass --host cursor for preview guidance or choose an OpenClaw target root." >&2
    exit 1
  fi
  if [[ "${host_id}" == "opencode" && ( "${is_codex_root}" == "true" || "${is_claude_root}" == "true" || "${is_cursor_root}" == "true" || "${is_windsurf_root}" == "true" || "${is_openclaw_root}" == "true" ) ]]; then
    echo "[FAIL] Target root '${target_root}' looks like a non-OpenCode host root, but host='opencode'." >&2
    exit 1
  fi
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

quarantine_codex_duplicate_skill_surface() {
  local duplicate_root=""
  duplicate_root="$(resolve_codex_duplicate_skill_root || true)"
  if [[ -z "${duplicate_root}" || ! -d "${duplicate_root}" ]]; then
    return 0
  fi

  local target_skill_root="${TARGET_ROOT}/skills/vibe"
  [[ -d "${target_skill_root}" ]] || return 0

  local duplicate_real=""
  local target_real=""
  duplicate_real="$(cd "${duplicate_root}" 2>/dev/null && pwd || true)"
  target_real="$(cd "${target_skill_root}" 2>/dev/null && pwd || true)"
  if [[ -n "${duplicate_real}" && -n "${target_real}" && "${duplicate_real}" == "${target_real}" ]]; then
    return 0
  fi

  if ! test_vibe_skill_dir "${duplicate_root}"; then
    echo "[FAIL] Duplicate Codex-discovered skill surface exists at ${duplicate_root}, but it is not a recognizable vibe skill copy." >&2
    echo "[FAIL] Move it out of .agents/skills manually before using Codex with the installed ~/.codex/skills/vibe lane." >&2
    return 1
  fi

  local agents_root=""
  agents_root="$(dirname "$(dirname "${duplicate_root}")")"
  local quarantine_root="${agents_root}/skills-disabled"
  local quarantine_path="${quarantine_root}/vibe.codex-duplicate-$(date +%Y%m%dT%H%M%S)"
  mkdir -p "${quarantine_root}"
  mv "${duplicate_root}" "${quarantine_path}"
  echo "[WARN] Quarantined duplicate Codex-discovered vibe skill: ${duplicate_root} -> ${quarantine_path}"
}

CANONICAL_SKILLS_ROOT="$(safe_parent_dir "${SCRIPT_DIR}")"
WORKSPACE_ROOT="$(safe_parent_dir "${CANONICAL_SKILLS_ROOT}")"
WORKSPACE_SKILLS_ROOT=""
WORKSPACE_SUPERPOWERS_ROOT=""
if [[ -n "${WORKSPACE_ROOT}" ]]; then
  WORKSPACE_SKILLS_ROOT="${WORKSPACE_ROOT}/skills"
  WORKSPACE_SUPERPOWERS_ROOT="${WORKSPACE_ROOT}/superpowers/skills"
fi
SP_SRC_ROOT="${SCRIPT_DIR}/bundled/superpowers-skills"

EXTERNAL_FALLBACK_USED=()
MISSING_REQUIRED=()

json_query_lines_from_file() {
  local governance_path="$1"
  local expr="$2"
  if [[ -z "${governance_path}" || ! -f "${governance_path}" ]]; then
    return 1
  fi

  if command -v python3 >/dev/null 2>&1; then
    python3 - "${governance_path}" "${expr}" <<'PY'
import json, sys
path, expr = sys.argv[1], sys.argv[2]
with open(path, encoding='utf-8-sig') as fh:
    data = json.load(fh)
value = data
for part in expr.split('.'):
    value = value[part]
if isinstance(value, list):
    for item in value:
        print(item)
elif isinstance(value, bool):
    print('true' if value else 'false')
elif value is None:
    pass
else:
    print(value)
PY
    return $?
  elif command -v python >/dev/null 2>&1; then
    python - "${governance_path}" "${expr}" <<'PY'
import json, sys
path, expr = sys.argv[1], sys.argv[2]
with open(path, encoding='utf-8-sig') as fh:
    data = json.load(fh)
value = data
for part in expr.split('.'):
    value = value[part]
if isinstance(value, list):
    for item in value:
        print(item)
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
' -Args "$governance_path" "$expr"
    return $?
  fi

  return 1
}

json_query_lines() {
  local expr="$1"
  json_query_lines_from_file "${SCRIPT_DIR}/config/version-governance.json" "${expr}"
}

json_query_scalar_from_file() {
  local governance_path="$1"
  local expr="$2"
  json_query_lines_from_file "${governance_path}" "${expr}" | head -n 1
}

json_query_scalar() {
  local expr="$1"
  json_query_lines "${expr}" | head -n 1
}

pick_python() {
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

adapter_query() {
  local property="$1"
  local python_bin=""
  python_bin="$(pick_python || true)"
  if [[ -z "${python_bin}" ]]; then
    print_python_requirement_error "Adapter-driven installation metadata"
    exit 1
  fi
  "${python_bin}" "${ADAPTER_RESOLVER}" --repo-root "${SCRIPT_DIR}" --host "${HOST_ID}" --property "${property}"
}

run_runtime_neutral_freshness_gate() {
  local repo_root="${1:-${SCRIPT_DIR}}"
  local gate_path="${repo_root}/scripts/verify/runtime_neutral/freshness_gate.py"
  local python_bin=""
  if [[ ! -f "${gate_path}" ]]; then
    return 127
  fi
  if ! python_bin="$(pick_python)"; then
    return 127
  fi
  "${python_bin}" "${gate_path}" --target-root "${TARGET_ROOT}" --write-receipt
}

run_runtime_freshness_gate() {
  if [[ "${SKIP_RUNTIME_FRESHNESS_GATE}" == "true" ]]; then
    echo "[WARN] Skipping runtime freshness gate by request."
    return 0
  fi

  local canonical_root=""
  canonical_root="$(resolve_canonical_repo_root "${SCRIPT_DIR}" || true)"
  if [[ -z "${canonical_root}" ]]; then
    echo "[WARN] Runtime freshness gate requires the canonical repo root; skipping because no outer .git root was found."
    return 0
  fi

  local gate_rel="scripts/verify/vibe-installed-runtime-freshness-gate.ps1"
  local governance_path="${canonical_root}/config/version-governance.json"
  local configured_gate
  configured_gate="$(json_query_scalar_from_file "${governance_path}" 'runtime.installed_runtime.post_install_gate' 2>/dev/null || true)"
  if [[ -n "${configured_gate}" ]]; then
    gate_rel="${configured_gate}"
  fi
  local gate_path="${canonical_root}/${gate_rel}"
  if [[ ! -f "${gate_path}" ]]; then
    echo "[FAIL] Runtime freshness gate script missing: ${gate_path}"
    return 1
  fi

  if run_runtime_neutral_freshness_gate "${canonical_root}"; then
    :
  elif [[ $? -eq 127 ]]; then
    if ! pick_powershell >/dev/null 2>&1; then
      echo "[WARN] runtime freshness gate skipped: neither Python runtime-neutral gate nor a PowerShell fallback is available."
      return 0
    fi
    run_powershell_file "${gate_path}" -TargetRoot "${TARGET_ROOT}" -WriteReceipt
  else
    return 1
  fi

  local receipt_rel receipt_path
  receipt_rel="$(json_query_scalar_from_file "${governance_path}" 'runtime.installed_runtime.receipt_relpath' 2>/dev/null || true)"
  [[ -n "${receipt_rel}" ]] || receipt_rel='skills/vibe/outputs/runtime-freshness-receipt.json'
  receipt_path="${TARGET_ROOT}/${receipt_rel}"
  if [[ ! -f "${receipt_path}" ]]; then
    echo "[FAIL] Runtime freshness receipt missing after install: ${receipt_path}"
    return 1
  fi
}

refresh_install_ledger_payload_summary() {
  local python_bin=""
  if ! python_bin="$(pick_python)"; then
    echo "[FAIL] Post-install ledger refresh requires Python ${PYTHON_MIN_MAJOR}.${PYTHON_MIN_MINOR}+."
    return 1
  fi

  "${python_bin}" "${ADAPTER_INSTALLER}" \
    --target-root "${TARGET_ROOT}" \
    --refresh-install-ledger >/dev/null
}

copy_dir_content() {
  local src="$1"
  local dst="$2"
  [[ -d "${src}" ]] || return 0
  mkdir -p "${dst}"
  cp -R "${src}/." "${dst}/"
}

remove_path_entry() {
  local path="$1"
  if [[ -L "${path}" || -f "${path}" ]]; then
    rm -f "${path}"
    return 0
  fi
  if [[ -d "${path}" ]]; then
    rmdir "${path}"
  fi
}

prune_dir_content_individually() {
  local src="$1"
  local dst="$2"
  [[ -d "${src}" && -d "${dst}" ]] || return 0

  local path="" rel="" src_equivalent=""
  while IFS= read -r -d '' path; do
    rel="${path#${dst}/}"
    src_equivalent="${src}/${rel}"
    if [[ ! -e "${src_equivalent}" ]]; then
      remove_path_entry "${path}"
    fi
  done < <(find "${dst}" -mindepth 1 -depth -print0)
}

sync_dir_content_individually() {
  local src="$1"
  local dst="$2"
  [[ -d "${src}" ]] || return 0
  copy_dir_content "${src}" "${dst}"
  prune_dir_content_individually "${src}" "${dst}"
}

sync_vibe_canonical_to_target() {
  local governance_path="${SCRIPT_DIR}/config/version-governance.json"
  local canonical_rel='.'
  local files=()
  local dirs=()

  if [[ -f "${governance_path}" ]]; then
    local configured_canonical_rel
    configured_canonical_rel="$(json_query_scalar 'source_of_truth.canonical_root' 2>/dev/null || true)"
    if [[ -n "${configured_canonical_rel}" ]]; then
      canonical_rel="${configured_canonical_rel}"
    fi

    while IFS= read -r line; do
      files+=("${line}")
    done < <(json_query_lines 'packaging.mirror.files' 2>/dev/null || true)
    while IFS= read -r line; do
      dirs+=("${line}")
    done < <(json_query_lines 'packaging.mirror.directories' 2>/dev/null || true)
  else
    echo "[WARN] Missing version governance config: ${governance_path}; using safe fallback mirror scope."
  fi

  if [[ ${#files[@]} -eq 0 || ${#dirs[@]} -eq 0 ]]; then
    echo "[WARN] Failed to load packaging mirror scope from version-governance.json; using safe fallback mirror scope."
    files=(
      "SKILL.md"
      "check.ps1"
      "check.sh"
      "install.ps1"
      "install.sh"
    )
    dirs=(
      "config"
      "protocols"
      "references"
      "docs"
      "scripts"
    )
  fi

  local canonical_root="${SCRIPT_DIR}/${canonical_rel}"
  local target_vibe_root="${TARGET_ROOT}/skills/vibe"

  local rel src dst
  for rel in "${files[@]}"; do
    src="${canonical_root}/${rel}"
    dst="${target_vibe_root}/${rel}"
    [[ -f "${src}" ]] || continue
    mkdir -p "$(dirname "${dst}")"
    cp "${src}" "${dst}"
  done

  for rel in "${dirs[@]}"; do
    src="${canonical_root}/${rel}"
    dst="${target_vibe_root}/${rel}"
    sync_dir_content_individually "${src}" "${dst}"
  done
}

sanitize_installed_runtime_skill_entrypoints() {
  local nested_skills_root="${TARGET_ROOT}/skills/vibe/bundled/skills"
  [[ -d "${nested_skills_root}" ]] || return 0

  local skill_md=""
  local renamed=0
  while IFS= read -r -d '' skill_md; do
    local mirror_path="${skill_md%/SKILL.md}/SKILL.runtime-mirror.md"
    mv "${skill_md}" "${mirror_path}"
    echo "[INFO] Hid nested runtime mirror skill entrypoint: ${skill_md} -> ${mirror_path}"
    renamed=$((renamed+1))
  done < <(find "${nested_skills_root}" -mindepth 2 -maxdepth 2 -type f -name 'SKILL.md' -print0)

  if [[ ${renamed} -eq 0 ]]; then
    echo "[INFO] Nested runtime mirror skill entrypoints already sanitized."
  fi
}

restore_skill_entrypoint_if_needed() {
  local skill_root="$1"
  local mirror_path="${skill_root}/SKILL.runtime-mirror.md"
  local skill_md="${skill_root}/SKILL.md"
  if [[ -f "${skill_md}" || ! -f "${mirror_path}" ]]; then
    return 0
  fi
  mv "${mirror_path}" "${skill_md}"
}

ensure_skill_present() {
  local name="$1"
  local required="$2"
  shift 2
  local fallback_sources=("$@")

  if [[ -f "${TARGET_ROOT}/skills/${name}/SKILL.md" ]]; then
    return 0
  fi

  if [[ "${ALLOW_EXTERNAL_SKILL_FALLBACK}" == "true" ]]; then
    local src
    for src in "${fallback_sources[@]}"; do
      [[ -n "${src}" ]] || continue
      if [[ -d "${src}" ]]; then
        echo "[WARN] Using external fallback source for skill '${name}': ${src}"
        copy_dir_content "${src}" "${TARGET_ROOT}/skills/${name}"
        restore_skill_entrypoint_if_needed "${TARGET_ROOT}/skills/${name}"
        EXTERNAL_FALLBACK_USED+=("${name}")
        break
      fi
    done
  fi

  if [[ ! -f "${TARGET_ROOT}/skills/${name}/SKILL.md" ]]; then
    if [[ "${required}" == "true" ]]; then
      echo "[WARN] Missing required vendored skill: ${name}"
      MISSING_REQUIRED+=("${name}")
    else
      echo "[WARN] Missing optional vendored skill: ${name}"
    fi
  fi
}

ADAPTER_INSTALL_MODE="$(adapter_query install_mode)"

echo "=== VCO Adapter Installer ==="
echo "Host   : ${HOST_ID}"
echo "Mode   : ${ADAPTER_INSTALL_MODE}"
echo "Profile: ${PROFILE}"
echo "Target : ${TARGET_ROOT}"
echo "StrictOffline: ${STRICT_OFFLINE}"
echo "RequireClosedReady: ${REQUIRE_CLOSED_READY}"
echo "AllowExternalSkillFallback: ${ALLOW_EXTERNAL_SKILL_FALLBACK}"
echo "SkipRuntimeFreshnessGate: ${SKIP_RUNTIME_FRESHNESS_GATE}"

TARGET_VIBE_REL="$(json_query_scalar 'runtime.installed_runtime.target_relpath' 2>/dev/null || true)"
[[ -n "${TARGET_VIBE_REL}" ]] || TARGET_VIBE_REL='skills/vibe'

PYTHON_BIN_FOR_ADAPTER="$(pick_python || true)"
if [[ -z "${PYTHON_BIN_FOR_ADAPTER}" ]]; then
  print_python_requirement_error "Adapter-driven installation"
  exit 1
fi
ADAPTER_INSTALL_JSON="$("${PYTHON_BIN_FOR_ADAPTER}" "${ADAPTER_INSTALLER}" \
  --repo-root "${SCRIPT_DIR}" \
  --target-root "${TARGET_ROOT}" \
  --host "${HOST_ID}" \
  --profile "${PROFILE}" \
  $([[ "${REQUIRE_CLOSED_READY}" == "true" ]] && printf '%s' '--require-closed-ready') \
  $([[ "${ALLOW_EXTERNAL_SKILL_FALLBACK}" == "true" ]] && printf '%s' '--allow-external-skill-fallback'))"
if [[ -n "${ADAPTER_INSTALL_JSON}" ]]; then
  while IFS= read -r line; do
    EXTERNAL_FALLBACK_USED+=("${line}")
  done < <(printf '%s\n' "${ADAPTER_INSTALL_JSON}" | "${PYTHON_BIN_FOR_ADAPTER}" -c 'import json,sys; data=json.load(sys.stdin); [print(x) for x in data.get("external_fallback_used", [])]')
fi

sanitize_installed_runtime_skill_entrypoints

if [[ "${INSTALL_EXTERNAL}" == "true" ]]; then
  if [[ "${ADAPTER_INSTALL_MODE}" != "governed" ]]; then
    echo "[WARN] InstallExternal is currently only applied to the governed Codex lane. Skipping external install for host '${HOST_ID}'."
  else
    if command -v npm >/dev/null 2>&1; then
      npm install -g claude-flow || true
      npm install -g @th0rgal/ralph-wiggum || true
    fi

    if ! command -v xan >/dev/null 2>&1; then
      if command -v brew >/dev/null 2>&1; then
        brew install xan || true
      elif command -v pixi >/dev/null 2>&1; then
        pixi global install xan || true
      elif command -v conda >/dev/null 2>&1; then
        conda install -y conda-forge::xan || true
      else
        echo "[WARN] xan CLI not detected. Install manually (brew/pixi/conda/cargo) to enable large CSV acceleration."
      fi
    fi

    PYTHON_BIN=""
    if command -v python3 >/dev/null 2>&1; then
      PYTHON_BIN="python3"
    elif command -v python >/dev/null 2>&1; then
      PYTHON_BIN="python"
    fi

    if [[ -n "${PYTHON_BIN}" ]]; then
      if ! command -v scrapling >/dev/null 2>&1; then
        if "${PYTHON_BIN}" -m pip install 'scrapling[ai]' >/dev/null 2>&1; then
          if command -v scrapling >/dev/null 2>&1; then
            echo "[INFO] Installed scrapling[ai]"
          else
            echo "[WARN] scrapling[ai] package install completed, but the scrapling CLI is still not callable from PATH. Export your Python scripts directory before relying on the default scrapling MCP surface."
          fi
        else
          echo "[WARN] Failed to install scrapling[ai]. Install manually (${PYTHON_BIN} -m pip install 'scrapling[ai]') to enable the default scrapling MCP surface."
        fi
      else
        echo "[INFO] scrapling already installed"
      fi

      if "${PYTHON_BIN}" -c "import ivy; print(ivy.__version__)" >/dev/null 2>&1; then
        echo "[INFO] ivy Python package already installed"
      else
        echo "[WARN] ivy Python package not detected. Install manually (pip install ivy) to enable framework-interop analyzer hints."
      fi
    else
      echo "[WARN] python not detected. Install Python + scrapling[ai] (python -m pip install 'scrapling[ai]') and ivy (pip install ivy) if you want the default scraping surface and framework-interop analyzer hints."
    fi

    if ! command -v fuck-u-code >/dev/null 2>&1; then
      echo "[WARN] fuck-u-code CLI not detected. Install manually if you want external quality-debt analyzer hints (quality-debt-overlay still works without it)."
    fi
  fi
fi

if [[ "${STRICT_OFFLINE}" == "true" ]]; then
  OFFLINE_GATE="${SCRIPT_DIR}/scripts/verify/vibe-offline-skills-gate.ps1"
  if [[ ! -f "${OFFLINE_GATE}" ]]; then
    echo "[FAIL] StrictOffline requested, but offline gate script is missing: ${OFFLINE_GATE}"
    exit 1
  fi
  if ! pick_powershell >/dev/null 2>&1; then
    echo "[FAIL] StrictOffline requires an available PowerShell host to run the offline gate"
    exit 1
  fi

  run_powershell_file "${OFFLINE_GATE}" \
    -SkillsRoot "${TARGET_ROOT}/skills" \
    -PackManifestPath "${SCRIPT_DIR}/config/pack-manifest.json" \
    -SkillsLockPath "${SCRIPT_DIR}/config/skills-lock.json"

  if [[ ${#EXTERNAL_FALLBACK_USED[@]} -gt 0 ]]; then
    uniq_fallback="$(printf "%s\n" "${EXTERNAL_FALLBACK_USED[@]}" | sort -u | tr '\n' ',' | sed 's/,$//')"
    echo "[FAIL] StrictOffline rejected external fallback usage: ${uniq_fallback}"
    exit 1
  fi
elif [[ ${#EXTERNAL_FALLBACK_USED[@]} -gt 0 ]]; then
  uniq_fallback="$(printf "%s\n" "${EXTERNAL_FALLBACK_USED[@]}" | sort -u | tr '\n' ',' | sed 's/,$//')"
  echo "[WARN] External fallback skills were used (non-reproducible install): ${uniq_fallback}"
fi

quarantine_codex_duplicate_skill_surface
run_runtime_freshness_gate
refresh_install_ledger_payload_summary

echo "Install done. Run: bash check.sh --profile ${PROFILE} --target-root ${TARGET_ROOT}"
