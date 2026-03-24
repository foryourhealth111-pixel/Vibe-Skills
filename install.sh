#!/usr/bin/env bash
set -euo pipefail

PROFILE="full"
HOST_ID="codex"
INSTALL_EXTERNAL="false"
STRICT_OFFLINE="false"
ALLOW_EXTERNAL_SKILL_FALLBACK="false"
SKIP_RUNTIME_FRESHNESS_GATE="false"
TARGET_ROOT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2 ;;
    --host) HOST_ID="$2"; shift 2 ;;
    --target-root) TARGET_ROOT="$2"; shift 2 ;;
    --install-external) INSTALL_EXTERNAL="true"; shift ;;
    --strict-offline) STRICT_OFFLINE="true"; shift ;;
    --allow-external-skill-fallback) ALLOW_EXTERNAL_SKILL_FALLBACK="true"; shift ;;
    --skip-runtime-freshness-gate) SKIP_RUNTIME_FRESHNESS_GATE="true"; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

resolve_host_id() {
  local host_id="${1:-${VCO_HOST_ID:-codex}}"
  host_id="$(printf '%s' "${host_id}" | tr '[:upper:]' '[:lower:]')"
  case "${host_id}" in
    codex) printf '%s' 'codex' ;;
    claude|claude-code) printf '%s' 'claude-code' ;;
    cursor) printf '%s' 'cursor' ;;
    *)
      echo "[FAIL] Unsupported VCO host id: ${host_id}. Supported values: codex, claude-code, cursor" >&2
      exit 1
      ;;
  esac
}

resolve_default_target_root() {
  local host_id="$1"
  case "${host_id}" in
    codex) printf '%s' "${CODEX_HOME:-${HOME}/.codex}" ;;
    claude-code) printf '%s' "${CLAUDE_HOME:-${HOME}/.claude}" ;;
    cursor) printf '%s' "${CURSOR_HOME:-${HOME}/.cursor}" ;;
    *)
      echo "[FAIL] Unsupported VCO host id for target-root resolution: ${host_id}" >&2
      exit 1
      ;;
  esac
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

assert_target_root_matches_host_intent() {
  local target_root="$1"
  local host_id="$2"
  local leaf
  leaf="$(basename "${target_root}")"
  leaf="$(printf '%s' "${leaf}" | tr '[:upper:]' '[:lower:]')"
  if [[ "${host_id}" == "codex" && "${leaf}" == ".claude" ]]; then
    echo "[FAIL] Target root '${target_root}' looks like a Claude Code home, but host='codex'." >&2
    echo "[FAIL] Pass --host claude-code for preview guidance or use a Codex target root." >&2
    exit 1
  fi
  if [[ "${host_id}" == "codex" && "${leaf}" == ".cursor" ]]; then
    echo "[FAIL] Target root '${target_root}' looks like a Cursor home, but host='codex'." >&2
    echo "[FAIL] Pass --host cursor for preview guidance or use a Codex target root." >&2
    exit 1
  fi
  if [[ "${host_id}" == "claude-code" && "${leaf}" == ".codex" ]]; then
    echo "[FAIL] Target root '${target_root}' looks like a Codex home, but host='claude-code'." >&2
    echo "[FAIL] Use --host codex for the official closure lane or choose a Claude Code target root." >&2
    exit 1
  fi
  if [[ "${host_id}" == "claude-code" && "${leaf}" == ".cursor" ]]; then
    echo "[FAIL] Target root '${target_root}' looks like a Cursor home, but host='claude-code'." >&2
    echo "[FAIL] Pass --host cursor for Cursor preview guidance or choose a Claude Code target root." >&2
    exit 1
  fi
  if [[ "${host_id}" == "cursor" && "${leaf}" == ".codex" ]]; then
    echo "[FAIL] Target root '${target_root}' looks like a Codex home, but host='cursor'." >&2
    echo "[FAIL] Use --host codex for the official closure lane or choose a Cursor target root." >&2
    exit 1
  fi
  if [[ "${host_id}" == "cursor" && "${leaf}" == ".claude" ]]; then
    echo "[FAIL] Target root '${target_root}' looks like a Claude Code home, but host='cursor'." >&2
    echo "[FAIL] Pass --host claude-code for Claude preview guidance or choose a Cursor target root." >&2
    exit 1
  fi
}

HOST_ID="$(resolve_host_id "${HOST_ID}")"
if [[ -z "${TARGET_ROOT}" ]]; then
  TARGET_ROOT="$(resolve_default_target_root "${HOST_ID}")"
fi
assert_target_root_matches_host_intent "${TARGET_ROOT}" "${HOST_ID}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CANONICAL_SKILLS_ROOT="$(safe_parent_dir "${SCRIPT_DIR}")"
WORKSPACE_ROOT="$(safe_parent_dir "${CANONICAL_SKILLS_ROOT}")"
WORKSPACE_SKILLS_ROOT=""
WORKSPACE_SUPERPOWERS_ROOT=""
if [[ -n "${WORKSPACE_ROOT}" ]]; then
  WORKSPACE_SKILLS_ROOT="${WORKSPACE_ROOT}/skills"
  WORKSPACE_SUPERPOWERS_ROOT="${WORKSPACE_ROOT}/superpowers/skills"
fi
SP_SRC_ROOT="${SCRIPT_DIR}/bundled/superpowers-skills"
ADAPTER_RESOLVER="${SCRIPT_DIR}/scripts/common/resolve_vgo_adapter.py"
ADAPTER_INSTALLER="${SCRIPT_DIR}/scripts/install/install_vgo_adapter.py"

if [[ ! -f "${ADAPTER_RESOLVER}" ]]; then
  echo "[FAIL] Missing adapter resolver: ${ADAPTER_RESOLVER}" >&2
  exit 1
fi
if [[ ! -f "${ADAPTER_INSTALLER}" ]]; then
  echo "[FAIL] Missing adapter installer: ${ADAPTER_INSTALLER}" >&2
  exit 1
fi

EXTERNAL_FALLBACK_USED=()
MISSING_REQUIRED=()

json_query_lines() {
  local expr="$1"
  local governance_path="${SCRIPT_DIR}/config/version-governance.json"
  if [[ ! -f "${governance_path}" ]]; then
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
  elif command -v pwsh >/dev/null 2>&1; then
    pwsh -NoProfile -Command '
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

json_query_scalar() {
  local expr="$1"
  json_query_lines "${expr}" | head -n 1
}

pick_python() {
  if command -v python3 >/dev/null 2>&1; then
    echo "python3"
    return 0
  fi
  if command -v python >/dev/null 2>&1; then
    echo "python"
    return 0
  fi
  return 1
}

adapter_query() {
  local property="$1"
  local python_bin=""
  python_bin="$(pick_python || true)"
  if [[ -z "${python_bin}" ]]; then
    echo "[FAIL] Python is required for adapter-driven installation metadata." >&2
    exit 1
  fi
  "${python_bin}" "${ADAPTER_RESOLVER}" --repo-root "${SCRIPT_DIR}" --host "${HOST_ID}" --property "${property}"
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
  "${python_bin}" "${gate_path}" --target-root "${TARGET_ROOT}" --write-receipt
}

run_runtime_freshness_gate() {
  if [[ "${SKIP_RUNTIME_FRESHNESS_GATE}" == "true" ]]; then
    echo "[WARN] Skipping runtime freshness gate by request."
    return 0
  fi

  if ! canonical_repo_available "${SCRIPT_DIR}"; then
    echo "[WARN] Runtime freshness gate requires the canonical repo root; skipping because no outer .git root was found."
    return 0
  fi

  local gate_rel="scripts/verify/vibe-installed-runtime-freshness-gate.ps1"
  local configured_gate
  configured_gate="$(json_query_scalar 'runtime.installed_runtime.post_install_gate' 2>/dev/null || true)"
  if [[ -n "${configured_gate}" ]]; then
    gate_rel="${configured_gate}"
  fi
  local gate_path="${SCRIPT_DIR}/${gate_rel}"
  if [[ ! -f "${gate_path}" ]]; then
    echo "[FAIL] Runtime freshness gate script missing: ${gate_path}"
    return 1
  fi

  if run_runtime_neutral_freshness_gate; then
    :
  elif [[ $? -eq 127 ]]; then
    if ! command -v pwsh >/dev/null 2>&1; then
      echo "[WARN] runtime freshness gate skipped: neither Python runtime-neutral gate nor pwsh fallback is available."
      return 0
    fi
    pwsh -NoProfile -File "${gate_path}" -TargetRoot "${TARGET_ROOT}" -WriteReceipt
  else
    return 1
  fi

  local receipt_rel receipt_path
  receipt_rel="$(json_query_scalar 'runtime.installed_runtime.receipt_relpath' 2>/dev/null || true)"
  [[ -n "${receipt_rel}" ]] || receipt_rel='skills/vibe/outputs/runtime-freshness-receipt.json'
  receipt_path="${TARGET_ROOT}/${receipt_rel}"
  if [[ ! -f "${receipt_path}" ]]; then
    echo "[FAIL] Runtime freshness receipt missing after install: ${receipt_path}"
    return 1
  fi
}

copy_dir_content() {
  local src="$1"
  local dst="$2"
  [[ -d "${src}" ]] || return 0
  mkdir -p "${dst}"
  cp -R "${src}/." "${dst}/"
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

    mapfile -t files < <(json_query_lines 'packaging.mirror.files' 2>/dev/null)
    mapfile -t dirs < <(json_query_lines 'packaging.mirror.directories' 2>/dev/null)
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
    [[ -d "${dst}" ]] && rm -rf "${dst}"
    copy_dir_content "${src}" "${dst}"
  done
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
echo "AllowExternalSkillFallback: ${ALLOW_EXTERNAL_SKILL_FALLBACK}"
echo "SkipRuntimeFreshnessGate: ${SKIP_RUNTIME_FRESHNESS_GATE}"

TARGET_VIBE_REL="$(json_query_scalar 'runtime.installed_runtime.target_relpath' 2>/dev/null || true)"
[[ -n "${TARGET_VIBE_REL}" ]] || TARGET_VIBE_REL='skills/vibe'

PYTHON_BIN_FOR_ADAPTER="$(pick_python || true)"
if [[ -z "${PYTHON_BIN_FOR_ADAPTER}" ]]; then
  echo "[FAIL] Python is required for adapter-driven installation." >&2
  exit 1
fi
ADAPTER_INSTALL_JSON="$("${PYTHON_BIN_FOR_ADAPTER}" "${ADAPTER_INSTALLER}" \
  --repo-root "${SCRIPT_DIR}" \
  --target-root "${TARGET_ROOT}" \
  --host "${HOST_ID}" \
  --profile "${PROFILE}" \
  $([[ "${ALLOW_EXTERNAL_SKILL_FALLBACK}" == "true" ]] && printf '%s' '--allow-external-skill-fallback'))"
if [[ -n "${ADAPTER_INSTALL_JSON}" ]]; then
  mapfile -t EXTERNAL_FALLBACK_USED < <(printf '%s\n' "${ADAPTER_INSTALL_JSON}" | "${PYTHON_BIN_FOR_ADAPTER}" -c 'import json,sys; data=json.load(sys.stdin); [print(x) for x in data.get("external_fallback_used", [])]')
fi

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
  if ! command -v pwsh >/dev/null 2>&1; then
    echo "[FAIL] StrictOffline requires pwsh to run offline gate"
    exit 1
  fi

  pwsh -NoProfile -File "${OFFLINE_GATE}" \
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

run_runtime_freshness_gate

echo "Install done. Run: bash check.sh --profile ${PROFILE} --target-root ${TARGET_ROOT}"
