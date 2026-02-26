#!/usr/bin/env bash
set -euo pipefail

PROFILE="full"
TARGET_ROOT="${HOME}/.codex"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2 ;;
    --target-root) TARGET_ROOT="$2"; shift 2 ;;
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

check_path "settings.json" "${TARGET_ROOT}/settings.json"
for n in vibe dialectic local-vco-roles spec-kit-vibe-compat superclaude-framework-compat ralph-loop cancel-ralph tdd-guide think-harder; do
  check_path "skill/${n}" "${TARGET_ROOT}/skills/${n}/SKILL.md"
done
check_path "vibe router script" "${TARGET_ROOT}/skills/vibe/scripts/router/resolve-pack-route.ps1"
check_path "vibe memory governance config" "${TARGET_ROOT}/skills/vibe/config/memory-governance.json"
check_path "vibe data scale overlay config" "${TARGET_ROOT}/skills/vibe/config/data-scale-overlay.json"
check_path "vibe quality debt overlay config" "${TARGET_ROOT}/skills/vibe/config/quality-debt-overlay.json"
check_path "vibe framework interop overlay config" "${TARGET_ROOT}/skills/vibe/config/framework-interop-overlay.json"
check_path "vibe ml lifecycle overlay config" "${TARGET_ROOT}/skills/vibe/config/ml-lifecycle-overlay.json"
check_path "vibe python clean code overlay config" "${TARGET_ROOT}/skills/vibe/config/python-clean-code-overlay.json"
check_path "vibe system design overlay config" "${TARGET_ROOT}/skills/vibe/config/system-design-overlay.json"
check_path "vibe cuda kernel overlay config" "${TARGET_ROOT}/skills/vibe/config/cuda-kernel-overlay.json"
check_path "vibe observability policy config" "${TARGET_ROOT}/skills/vibe/config/observability-policy.json"
check_path "vibe heartbeat policy config" "${TARGET_ROOT}/skills/vibe/config/heartbeat-policy.json"
check_path "vibe deep discovery policy config" "${TARGET_ROOT}/skills/vibe/config/deep-discovery-policy.json"
check_path "vibe capability catalog config" "${TARGET_ROOT}/skills/vibe/config/capability-catalog.json"
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

echo "Result: ${PASS} passed, ${FAIL} failed, ${WARN} warnings"
[[ ${FAIL} -eq 0 ]]
