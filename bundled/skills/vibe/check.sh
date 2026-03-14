#!/usr/bin/env bash
set -euo pipefail

PROFILE="full"
TARGET_ROOT="${HOME}/.codex"
SKIP_RUNTIME_FRESHNESS_GATE="false"
DEEP="false"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2 ;;
    --target-root) TARGET_ROOT="$2"; shift 2 ;;
    --skip-runtime-freshness-gate) SKIP_RUNTIME_FRESHNESS_GATE="true"; shift ;;
    --deep) DEEP="true"; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

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
    if [[ ! -d "${SCRIPT_DIR}/.git" ]]; then
      warn_note "vibe runtime freshness receipt unavailable because check.sh is not running from the canonical repo root."
      return
    fi
    if ! command -v pwsh >/dev/null 2>&1; then
      warn_note "vibe runtime freshness receipt unavailable because pwsh is not installed in this shell environment."
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

  if [[ ! -d "${SCRIPT_DIR}/.git" ]]; then
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
    if ! command -v pwsh >/dev/null 2>&1; then
      warn_note 'runtime freshness gate skipped: neither Python runtime-neutral gate nor pwsh fallback is available.'
      return
    fi
    if pwsh -NoProfile -File "$gate_path" -TargetRoot "$TARGET_ROOT"; then
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
  if [[ ! -d "${SCRIPT_DIR}/.git" ]]; then
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
    if ! command -v pwsh >/dev/null 2>&1; then
      warn_note 'runtime coherence gate skipped: neither Python runtime-neutral gate nor pwsh fallback is available.'
      return
    fi
    if pwsh -NoProfile -File "$gate_path" -TargetRoot "$TARGET_ROOT"; then
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

echo "=== VCO Codex Health Check ==="
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

check_path "settings.json" "${TARGET_ROOT}/settings.json"
check_path "vibe version governance config" "${TARGET_ROOT}/${runtime_target_rel}/config/version-governance.json"
check_path "vibe release ledger" "${runtime_skill_root}/references/release-ledger.jsonl"
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
check_path "vibe bundled retrieval intent profiles config" "${runtime_nested_skill_root}/config/retrieval-intent-profiles.json"
check_path "vibe bundled retrieval source registry config" "${runtime_nested_skill_root}/config/retrieval-source-registry.json"
check_path "vibe bundled retrieval rerank weights config" "${runtime_nested_skill_root}/config/retrieval-rerank-weights.json"
check_path "vibe bundled exploration policy config" "${runtime_nested_skill_root}/config/exploration-policy.json"
check_path "vibe bundled exploration intent profiles config" "${runtime_nested_skill_root}/config/exploration-intent-profiles.json"
check_path "vibe bundled exploration domain map config" "${runtime_nested_skill_root}/config/exploration-domain-map.json"
check_path "vibe bundled llm acceleration policy config" "${runtime_nested_skill_root}/config/llm-acceleration-policy.json"
for n in brainstorming writing-plans subagent-driven-development systematic-debugging; do
  check_path "workflow/${n}" "${TARGET_ROOT}/skills/${n}/SKILL.md"
done
if [[ "${PROFILE}" == "full" ]]; then
  for n in requesting-code-review receiving-code-review verification-before-completion; do
    check_path "optional/${n}" "${TARGET_ROOT}/skills/${n}/SKILL.md" false
  done
fi
check_path "rules/common" "${TARGET_ROOT}/rules/common/agents.md"
check_path "hooks/write-guard" "${TARGET_ROOT}/hooks/write-guard.js"
check_path "mcp template" "${TARGET_ROOT}/mcp/servers.template.json"

show_installed_runtime_upgrade_hint
run_runtime_freshness_gate
validate_runtime_receipt
run_runtime_coherence_gate

if command -v npm >/dev/null 2>&1; then
  echo "[OK] npm"
  PASS=$((PASS+1))
else
  echo "[WARN] npm not found (needed for claude-flow)"
  WARN=$((WARN+1))
fi

if [[ "${DEEP}" == "true" ]]; then
  doctor_path="${SCRIPT_DIR}/scripts/verify/vibe-bootstrap-doctor-gate.ps1"
  if [[ ! -f "${doctor_path}" ]]; then
    echo "[FAIL] vibe bootstrap doctor gate -> ${doctor_path}"
    FAIL=$((FAIL+1))
  elif run_runtime_neutral_bootstrap_doctor; then
    echo "[OK] vibe bootstrap doctor gate"
    PASS=$((PASS+1))
  elif [[ $? -eq 127 ]]; then
    if ! command -v pwsh >/dev/null 2>&1; then
      echo "[WARN] vibe bootstrap doctor gate skipped because neither the Python runtime-neutral doctor nor pwsh is available in this shell environment."
      WARN=$((WARN+1))
    elif pwsh -NoProfile -File "${doctor_path}" -TargetRoot "${TARGET_ROOT}" -WriteArtifacts; then
      echo "[OK] vibe bootstrap doctor gate"
      PASS=$((PASS+1))
    else
      echo "[FAIL] vibe bootstrap doctor gate"
      FAIL=$((FAIL+1))
    fi
  else
    echo "[FAIL] vibe bootstrap doctor gate"
    FAIL=$((FAIL+1))
  fi
fi

echo "Result: ${PASS} passed, ${FAIL} failed, ${WARN} warnings"
[[ ${FAIL} -eq 0 ]]
