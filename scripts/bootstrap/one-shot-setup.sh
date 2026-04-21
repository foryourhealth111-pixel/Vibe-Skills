#!/usr/bin/env bash
set -euo pipefail

PROFILE="full"
HOST_ID=""
HOST_ID_EXPLICIT="false"
TARGET_ROOT=""
SKIP_EXTERNAL_INSTALL="false"
STRICT_OFFLINE="false"
INTENT_ADVICE_BASE_URL="${VCO_INTENT_ADVICE_BASE_URL:-}"
INTENT_ADVICE_API_KEY_INPUT=""
PYTHON_MIN_MAJOR=3
PYTHON_MIN_MINOR=10
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ADAPTER_QUERY_PY="${REPO_ROOT}/scripts/common/adapter_registry_query.py"
PYTHON_HELPERS_SH="${REPO_ROOT}/scripts/common/python_helpers.sh"
INSTALL_SH="${REPO_ROOT}/install.sh"
CHECK_SH="${REPO_ROOT}/check.sh"
MATERIALIZE_PS1="${REPO_ROOT}/scripts/setup/materialize-codex-mcp-profile.ps1"
PERSIST_OPENAI_PS1="${REPO_ROOT}/scripts/setup/persist-codex-openai-env.ps1"
CLAUDE_SCAFFOLD_SH="${REPO_ROOT}/scripts/bootstrap/scaffold-claude-preview.sh"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2 ;;
    --host) HOST_ID="$2"; HOST_ID_EXPLICIT="true"; shift 2 ;;
    --target-root) TARGET_ROOT="$2"; shift 2 ;;
    --skip-external-install) SKIP_EXTERNAL_INSTALL="true"; shift ;;
    --strict-offline) STRICT_OFFLINE="true"; shift ;;
    --intent-advice-base-url) INTENT_ADVICE_BASE_URL="$2"; shift 2 ;;
    --intent-advice-api-key) INTENT_ADVICE_API_KEY_INPUT="$2"; shift 2 ;;
    --openai-base-url) INTENT_ADVICE_BASE_URL="$2"; shift 2 ;;
    --openai-api-key) INTENT_ADVICE_API_KEY_INPUT="$2"; shift 2 ;;
    *)
      echo "Unknown arg: $1" >&2
      exit 1
      ;;
  esac
done

source "${PYTHON_HELPERS_SH}"

is_interactive_shell() {
  [[ -t 0 && -t 1 ]]
}

resolve_host_id() {
  local host_id="${1:-${VCO_HOST_ID:-codex}}"
  adapter_query_for_host "${host_id}" "id"
}

prompt_for_host_id() {
  local choice normalized count i alias
  local index id summary aliases
  local -a choice_ids=()
  local -a choice_summaries=()
  local -a choice_aliases=()
  local -a alias_list=()

  while IFS=$'\t' read -r index id summary aliases; do
    [[ -n "${index}" ]] || continue
    choice_ids+=("${id}")
    choice_summaries+=("${summary}")
    choice_aliases+=("${aliases}")
  done < <(bootstrap_choice_lines)

  count="${#choice_ids[@]}"
  if [[ "${count}" -eq 0 ]]; then
    echo "[FAIL] No bootstrap host choices were available from the adapter registry." >&2
    exit 1
  fi

  echo "Select the install target before bootstrap:"
  for ((i=0; i<count; i++)); do
    printf '  %d) %-12s - %s\n' "$((i + 1))" "${choice_ids[i]}" "${choice_summaries[i]}"
  done

  while true; do
    read -r -p "Install into which agent? [1-${count}]: " choice
    normalized="$(printf '%s' "${choice}" | tr '[:upper:]' '[:lower:]' | xargs)"

    for ((i=0; i<count; i++)); do
      if [[ "${normalized}" == "$((i + 1))" || "${normalized}" == "${choice_ids[i]}" ]]; then
        HOST_ID="${choice_ids[i]}"
        return 0
      fi

      IFS=',' read -r -a alias_list <<< "${choice_aliases[i]}"
      for alias in "${alias_list[@]}"; do
        if [[ "${normalized}" == "${alias}" ]]; then
          HOST_ID="${choice_ids[i]}"
          return 0
        fi
      done
    done

    echo "[WARN] Unsupported choice: ${choice}. Enter 1-${count}, or a supported host name." >&2
  done
}

ensure_requested_host_id() {
  if [[ "${HOST_ID_EXPLICIT}" == "true" && -n "${HOST_ID}" ]]; then
    return 0
  fi
  if [[ -n "${VCO_HOST_ID:-}" ]]; then
    HOST_ID="${VCO_HOST_ID}"
    return 0
  fi
  if is_interactive_shell; then
    prompt_for_host_id
    return 0
  fi
  echo "[FAIL] No host was provided for one-shot bootstrap." >&2
  local supported_hosts=""
  supported_hosts="$(supported_host_hint)"
  echo "[FAIL] Pass --host ${supported_hosts} when running non-interactively." >&2
  return 1
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

target_root_owner_for_path() {
  local target_root="$1"
  local python_bin=""
  python_bin="$(pick_python || true)"
  if [[ -z "${python_bin}" ]]; then
    print_python_requirement_error "Adapter-driven target-root intent validation"
    exit 1
  fi
  "${python_bin}" "${ADAPTER_QUERY_PY}" --repo-root "${REPO_ROOT}" --target-root-owner "${target_root}"
}

adapter_query_for_host() {
  local host_id="$1"
  local property="$2"
  local python_bin=""
  python_bin="$(pick_python || true)"
  if [[ -z "${python_bin}" ]]; then
    print_python_requirement_error "Adapter-driven bootstrap metadata"
    exit 1
  fi
  "${python_bin}" "${ADAPTER_QUERY_PY}" --repo-root "${REPO_ROOT}" --host "${host_id}" --property "${property}"
}

adapter_query() {
  local property="$1"
  adapter_query_for_host "${HOST_ID}" "${property}"
}

bootstrap_choice_lines() {
  local python_bin=""
  python_bin="$(pick_python || true)"
  if [[ -z "${python_bin}" ]]; then
    print_python_requirement_error "Adapter-driven bootstrap host selection"
    exit 1
  fi
  "${python_bin}" "${ADAPTER_QUERY_PY}" --repo-root "${REPO_ROOT}" --bootstrap-choice-lines
}

supported_host_hint() {
  local python_bin=""
  python_bin="$(pick_python || true)"
  if [[ -z "${python_bin}" ]]; then
    print_python_requirement_error "Adapter-driven bootstrap host selection"
    exit 1
  fi
  "${python_bin}" "${ADAPTER_QUERY_PY}" --repo-root "${REPO_ROOT}" --supported-hosts
}

require_cmd() {
  local cmd="$1"
  local hint="${2:-}"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "[FAIL] Missing required command: ${cmd}${hint:+ (${hint})}" >&2
    exit 1
  fi
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

if ! ensure_requested_host_id; then
  exit 1
fi
HOST_ID="$(resolve_host_id "${HOST_ID}")"
if [[ -z "${TARGET_ROOT}" ]]; then
  TARGET_ROOT="$(resolve_default_target_root "${HOST_ID}")"
fi
assert_target_root_matches_host_intent "${TARGET_ROOT}" "${HOST_ID}"

read_existing_settings_env_value() {
  local codex_root="$1"
  local name="$2"
  local python_bin

  if ! python_bin="$(pick_python)"; then
    return 1
  fi

  "${python_bin}" - "${codex_root}" "${name}" <<'PY'
import json
import sys
from pathlib import Path

def emit(value):
    if value is None:
        raise SystemExit(1)
    sys.stdout.buffer.write(f"{value}\n".encode("utf-8", errors="backslashreplace"))

codex_root, name = sys.argv[1:3]
settings_path = Path(codex_root) / "settings.json"
if not settings_path.exists():
    raise SystemExit(1)

try:
    with settings_path.open("r", encoding="utf-8-sig") as fh:
        settings = json.load(fh)
except Exception:
    raise SystemExit(1)

env = settings.get("env", {})
value = env.get(name)
if isinstance(value, str) and value.strip():
    emit(value)
    raise SystemExit(0)
raise SystemExit(1)
PY
}

print_mcp_auto_provision_summary() {
  local python_bin=""
  python_bin="$(pick_python || true)"
  if [[ -z "${python_bin}" ]]; then
    return 0
  fi
  "${python_bin}" - "${TARGET_ROOT}" <<'PY'
import json
import shutil
import sys
from pathlib import Path

target_root = Path(sys.argv[1])
receipt_path = target_root / ".vibeskills" / "mcp-auto-provision.json"
active_path = target_root / "mcp" / "servers.active.json"
print("MCP auto-provision summary")
if not receipt_path.exists():
    print("- receipt: missing")
    sys.exit(0)

payload = json.loads(receipt_path.read_text(encoding="utf-8"))
try:
    active_payload = json.loads(active_path.read_text(encoding="utf-8")) if active_path.exists() else {}
except json.JSONDecodeError:
    active_payload = {}
active_servers = active_payload.get("servers") if isinstance(active_payload, dict) else {}
if not isinstance(active_servers, dict):
    active_servers = {}
print(f"- installed_locally: {payload.get('install_state') == 'installed_locally'}")
print(f"- mcp_auto_provision_attempted: {bool(payload.get('mcp_auto_provision_attempted'))}")
manual_follow_up = []
for item in payload.get("mcp_results") or []:
    name = str(item.get("name") or "")
    status = str(item.get("status") or "")
    next_step = str(item.get("next_step") or "none")
    active_entry = active_servers.get(name)
    if status == "local_tool_present" and isinstance(active_entry, dict):
        if str(active_entry.get("mode") or "") == "stdio" and shutil.which(str(active_entry.get("command") or "")):
            status = "ready"
            next_step = "none"
    print(f"- {name}: status={status} next_step={next_step}")
    if status != "ready":
        manual_follow_up.append(name)
print(f"- manual_follow_up: {', '.join(manual_follow_up) if manual_follow_up else 'none'}")
PY
}

seed_settings_env_with_python() {
  local codex_root="$1"
  local surface="$2"
  local base_url="$3"
  local api_key="$4"
  local python_bin

  if ! python_bin="$(pick_python)"; then
    echo "[WARN] Python not found; skipping ${surface} settings seed." >&2
    return 0
  fi

  "${python_bin}" - "${codex_root}" "${surface}" "${base_url}" "${api_key}" <<'PY'
import json
import os
import sys
from pathlib import Path

codex_root, surface, base_url, api_key = sys.argv[1:5]
settings_path = Path(codex_root) / "settings.json"
if not settings_path.exists():
    raise SystemExit(f"settings.json not found: {settings_path}")

with settings_path.open("r", encoding="utf-8-sig") as fh:
    settings = json.load(fh)

env = settings.setdefault("env", {})

if surface == "intent_advice":
    if base_url:
        env["VCO_INTENT_ADVICE_BASE_URL"] = base_url
    if api_key:
        env["VCO_INTENT_ADVICE_API_KEY"] = api_key
else:
    raise SystemExit(f"unsupported bootstrap settings seed: {surface}")

env.setdefault("VCO_PROFILE", "full")
env.setdefault("VCO_CODEX_MODE", "true")

with settings_path.open("w", encoding="utf-8", newline="\n") as fh:
    json.dump(settings, fh, ensure_ascii=False, indent=2)
    fh.write("\n")
PY
}

materialize_mcp_profile_with_python() {
  local repo_root="$1"
  local target_root="$2"
  local requested_profile="$3"
  local python_bin

  if ! python_bin="$(pick_python)"; then
    echo "[FAIL] Python is required to materialize the MCP active profile when no PowerShell host is available." >&2
    exit 1
  fi

  "${python_bin}" - "${repo_root}" "${target_root}" "${requested_profile}" <<'PY'
import json
import sys
from pathlib import Path

repo_root = Path(sys.argv[1])
target_root = Path(sys.argv[2])
requested_profile = sys.argv[3].strip()

settings_path = target_root / "settings.json"
profile_name = requested_profile
if not profile_name and settings_path.exists():
    with settings_path.open("r", encoding="utf-8-sig") as fh:
        settings = json.load(fh)
    profile_name = (
        settings.get("vco", {}).get("mcp_profile")
        if isinstance(settings.get("vco"), dict)
        else None
    )
profile_name = profile_name or "full"

template_path = repo_root / "mcp" / "servers.template.json"
profile_path = repo_root / "mcp" / "profiles" / f"{profile_name}.json"
if not template_path.exists():
    raise SystemExit(f"MCP servers template not found: {template_path}")
if not profile_path.exists():
    raise SystemExit(f"MCP profile not found: {profile_path}")

with template_path.open("r", encoding="utf-8-sig") as fh:
    template = json.load(fh)
with profile_path.open("r", encoding="utf-8-sig") as fh:
    profile = json.load(fh)

servers = template.get("servers", {})
enabled = [str(item) for item in profile.get("enabled_servers", [])]
missing = [name for name in enabled if name not in servers]
if missing:
    raise SystemExit("MCP profile references unknown servers: " + ", ".join(sorted(set(missing))))

active = {name: servers[name] for name in enabled}
artifact = {
    "generated_at": __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "target_root": str(target_root.resolve()),
    "profile": profile_name,
    "source_template": "mcp/servers.template.json",
    "source_profile": f"mcp/profiles/{profile_name}.json",
    "enabled_servers": enabled,
    "servers": active,
}

output_path = target_root / "mcp" / "servers.active.json"
output_path.parent.mkdir(parents=True, exist_ok=True)
with output_path.open("w", encoding="utf-8", newline="\n") as fh:
    json.dump(artifact, fh, ensure_ascii=False, indent=2)
    fh.write("\n")
PY
}

require_cmd bash "Linux/macOS bootstrap requires bash"
require_cmd git "required by the repository install flow"
PYTHON_BIN_FOR_BOOTSTRAP="$(pick_python || true)"
if [[ -z "${PYTHON_BIN_FOR_BOOTSTRAP}" ]]; then
  print_python_requirement_error "Shell-native settings and MCP materialization fallback"
  exit 1
fi
if [[ "${SKIP_EXTERNAL_INSTALL}" != "true" ]]; then
  require_cmd node "required for npm-managed runtimes"
  require_cmd npm "required for claude-flow / external CLI provisioning"
fi

ADAPTER_BOOTSTRAP_MODE="$(adapter_query bootstrap_mode)"

echo "=== VCO One-Shot Setup (shell) ==="
echo "Repo root             : ${REPO_ROOT}"
echo "Host                  : ${HOST_ID}"
echo "Mode                  : ${ADAPTER_BOOTSTRAP_MODE}"
echo "Target root           : ${TARGET_ROOT}"
echo "Profile               : ${PROFILE}"
echo "StrictOffline         : ${STRICT_OFFLINE}"
echo "SkipExternalInstall   : ${SKIP_EXTERNAL_INSTALL}"
if [[ "${SKIP_EXTERNAL_INSTALL}" != "true" ]]; then
  echo "External CLI install  : enabled (npm-based steps such as claude-flow may take several minutes; deprecated warnings are advisory unless the command exits non-zero)"
fi

install_args=(--profile "${PROFILE}" --host "${HOST_ID}" --target-root "${TARGET_ROOT}")
if [[ "${SKIP_EXTERNAL_INSTALL}" != "true" ]]; then
  install_args+=(--install-external)
fi
if [[ "${STRICT_OFFLINE}" == "true" ]]; then
  install_args+=(--strict-offline)
fi

echo
echo "[1/5] Installing adapter payload..."
VGO_SUPPRESS_INSTALL_COMPLETION_REPORT=1 bash "${INSTALL_SH}" "${install_args[@]}"

if [[ "${ADAPTER_BOOTSTRAP_MODE}" == "governed" ]]; then
  resolved_intent_advice_api_key="${INTENT_ADVICE_API_KEY_INPUT:-${VCO_INTENT_ADVICE_API_KEY:-}}"
  existing_intent_advice_key=""
  if existing_intent_advice_key="$(read_existing_settings_env_value "${TARGET_ROOT}" "VCO_INTENT_ADVICE_API_KEY" 2>/dev/null)"; then
    :
  else
    existing_intent_advice_key=""
  fi
  if [[ -n "${resolved_intent_advice_api_key}" ]]; then
    echo "[2/5] Seeding intent advice settings into target settings.json..."
    if pick_powershell >/dev/null 2>&1; then
      run_powershell_file "${PERSIST_OPENAI_PS1}" -CodexRoot "${TARGET_ROOT}" -BaseUrl "${INTENT_ADVICE_BASE_URL}" -ApiKey "${resolved_intent_advice_api_key}"
    else
      seed_settings_env_with_python "${TARGET_ROOT}" "intent_advice" "${INTENT_ADVICE_BASE_URL}" "${resolved_intent_advice_api_key}"
    fi
  elif [[ -n "${existing_intent_advice_key}" ]]; then
    echo "[2/5] Intent advice settings already exist in target settings.json; keeping current value."
  else
    echo "[WARN] VCO_INTENT_ADVICE_API_KEY not provided and not present in the current environment. Built-in intent advice readiness will remain pending."
  fi

  echo "[3/5] Built-in AI governance now uses separated functional keys: intent advice uses VCO_INTENT_ADVICE_* and vector diff embeddings use VCO_VECTOR_DIFF_*."

  echo "[4/5] Materializing MCP profile..."
  if pick_powershell >/dev/null 2>&1; then
    run_powershell_file "${MATERIALIZE_PS1}" -TargetRoot "${TARGET_ROOT}" -Force >/dev/null
  else
    materialize_mcp_profile_with_python "${REPO_ROOT}" "${TARGET_ROOT}" "${PROFILE}"
  fi

  echo "[5/5] Running deep health check..."
  bash "${CHECK_SH}" --profile "${PROFILE}" --host "${HOST_ID}" --target-root "${TARGET_ROOT}" --deep
elif [[ "${ADAPTER_BOOTSTRAP_MODE}" == "preview-guidance" ]]; then
  if [[ "${HOST_ID}" == "claude-code" ]]; then
    echo "[2/5] Hook installation is frozen for Claude Code because of compatibility issues."
    bash "${CLAUDE_SCAFFOLD_SH}" --repo-root "${REPO_ROOT}" --target-root "${TARGET_ROOT}" --force >/dev/null
  else
    echo "[2/5] Host-specific scaffold is currently unavailable for '${HOST_ID}'."
  fi
  echo "[3/5] No hook files or extra preview settings were installed into the target root."
  echo "[4/5] Provider settings remain host-managed for '${HOST_ID}'. Configure built-in intent advice with VCO_INTENT_ADVICE_API_KEY / VCO_INTENT_ADVICE_BASE_URL / VCO_INTENT_ADVICE_MODEL, and configure vector diff embeddings separately with VCO_VECTOR_DIFF_API_KEY / VCO_VECTOR_DIFF_BASE_URL / VCO_VECTOR_DIFF_MODEL. Do not paste API keys into chat."
  echo "[5/5] Running supported-path health check..."
  bash "${CHECK_SH}" --profile "${PROFILE}" --host "${HOST_ID}" --target-root "${TARGET_ROOT}" --deep
else
  echo "[2/5] Runtime-adapter path does not materialize host settings."
  echo "[3/5] Runtime-adapter path does not seed provider settings. Configure built-in intent advice with VCO_INTENT_ADVICE_API_KEY / VCO_INTENT_ADVICE_BASE_URL / VCO_INTENT_ADVICE_MODEL, and configure vector diff embeddings separately with VCO_VECTOR_DIFF_API_KEY / VCO_VECTOR_DIFF_BASE_URL / VCO_VECTOR_DIFF_MODEL. Do not paste secrets into chat."
  echo "[4/5] MCP materialization skipped for the runtime-adapter path."
  echo "[5/5] Running runtime-adapter health check..."
  bash "${CHECK_SH}" --profile "${PROFILE}" --host "${HOST_ID}" --target-root "${TARGET_ROOT}" --deep
fi

echo
print_mcp_auto_provision_summary
echo "One-shot setup completed."
echo "- Re-run deep doctor anytime with: bash ./check.sh --profile ${PROFILE} --host ${HOST_ID} --target-root \"${TARGET_ROOT}\" --deep"
if [[ "${ADAPTER_BOOTSTRAP_MODE}" == "governed" ]]; then
  echo "- MCP active file: ${TARGET_ROOT}/mcp/servers.active.json"
fi
echo "- Doctor artifacts: ${REPO_ROOT}/outputs/verify"
if ! pick_powershell >/dev/null 2>&1; then
  if ! command -v python3 >/dev/null 2>&1 && ! command -v python >/dev/null 2>&1; then
    echo "[WARN] Neither a PowerShell host nor Python is available. Deep authoritative doctor coverage remains unavailable in this shell environment."
  else
    echo "[INFO] No PowerShell host was found, but the shell runtime-neutral verification path was used where supported."
  fi
fi
