#!/usr/bin/env bash
set -euo pipefail

PROFILE="full"
INSTALL_EXTERNAL="false"
STRICT_OFFLINE="false"
ALLOW_EXTERNAL_SKILL_FALLBACK="false"
TARGET_ROOT="${HOME}/.codex"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2 ;;
    --target-root) TARGET_ROOT="$2"; shift 2 ;;
    --install-external) INSTALL_EXTERNAL="true"; shift ;;
    --strict-offline) STRICT_OFFLINE="true"; shift ;;
    --allow-external-skill-fallback) ALLOW_EXTERNAL_SKILL_FALLBACK="true"; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CANONICAL_SKILLS_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
WORKSPACE_SKILLS_ROOT="${WORKSPACE_ROOT}/skills"
WORKSPACE_SUPERPOWERS_ROOT="${WORKSPACE_ROOT}/superpowers/skills"
SP_SRC_ROOT="${SCRIPT_DIR}/bundled/superpowers-skills"

EXTERNAL_FALLBACK_USED=()
MISSING_REQUIRED=()

copy_dir_content() {
  local src="$1"
  local dst="$2"
  [[ -d "${src}" ]] || return 0
  mkdir -p "${dst}"
  cp -R "${src}/." "${dst}/"
}

sync_vibe_canonical_to_target() {
  local canonical_root="${SCRIPT_DIR}"
  local target_vibe_root="${TARGET_ROOT}/skills/vibe"
  local files=(
    "SKILL.md"
    "check.ps1"
    "check.sh"
    "install.ps1"
    "install.sh"
  )
  local dirs=(
    "config"
    "protocols"
    "references"
    "docs"
    "scripts"
  )

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

echo "=== VCO Codex Installer ==="
echo "Profile: ${PROFILE}"
echo "Target : ${TARGET_ROOT}"
echo "StrictOffline: ${STRICT_OFFLINE}"
echo "AllowExternalSkillFallback: ${ALLOW_EXTERNAL_SKILL_FALLBACK}"

mkdir -p \
  "${TARGET_ROOT}/skills" \
  "${TARGET_ROOT}/rules" \
  "${TARGET_ROOT}/hooks" \
  "${TARGET_ROOT}/agents/templates" \
  "${TARGET_ROOT}/mcp/profiles" \
  "${TARGET_ROOT}/config" \
  "${TARGET_ROOT}/commands"

copy_dir_content "${SCRIPT_DIR}/bundled/skills" "${TARGET_ROOT}/skills"

# Ensure unified /vibe entry uses the latest router implementation (script + modules) after install.
VIBE_ROUTER_SRC_DIR="${SCRIPT_DIR}/scripts/router"
VIBE_ROUTER_DEST_DIR="${TARGET_ROOT}/skills/vibe/scripts/router"
if [[ -d "${VIBE_ROUTER_SRC_DIR}" ]]; then
  copy_dir_content "${VIBE_ROUTER_SRC_DIR}" "${VIBE_ROUTER_DEST_DIR}"
fi

# Enforce canonical vibe mirror files/dirs to avoid main-vs-bundled drift after install.
sync_vibe_canonical_to_target

required_core=(
  dialectic local-vco-roles spec-kit-vibe-compat superclaude-framework-compat
  ralph-loop cancel-ralph tdd-guide think-harder
)
required_sp=(brainstorming writing-plans subagent-driven-development systematic-debugging)
optional_sp=(requesting-code-review receiving-code-review verification-before-completion)

for n in "${required_core[@]}"; do
  ensure_skill_present "${n}" "true" \
    "${CANONICAL_SKILLS_ROOT}/${n}" \
    "${WORKSPACE_SKILLS_ROOT}/${n}" \
    "${WORKSPACE_SUPERPOWERS_ROOT}/${n}" \
    "${SP_SRC_ROOT}/${n}"
done

for n in "${required_sp[@]}"; do
  ensure_skill_present "${n}" "true" \
    "${WORKSPACE_SKILLS_ROOT}/${n}" \
    "${WORKSPACE_SUPERPOWERS_ROOT}/${n}" \
    "${SP_SRC_ROOT}/${n}" \
    "${CANONICAL_SKILLS_ROOT}/${n}"
done

if [[ "${PROFILE}" == "full" ]]; then
  for n in "${optional_sp[@]}"; do
    ensure_skill_present "${n}" "false" \
      "${WORKSPACE_SKILLS_ROOT}/${n}" \
      "${WORKSPACE_SUPERPOWERS_ROOT}/${n}" \
      "${SP_SRC_ROOT}/${n}" \
      "${CANONICAL_SKILLS_ROOT}/${n}"
  done
fi

copy_dir_content "${SCRIPT_DIR}/rules" "${TARGET_ROOT}/rules"
copy_dir_content "${SCRIPT_DIR}/hooks" "${TARGET_ROOT}/hooks"
copy_dir_content "${SCRIPT_DIR}/agents/templates" "${TARGET_ROOT}/agents/templates"
copy_dir_content "${SCRIPT_DIR}/mcp" "${TARGET_ROOT}/mcp"
cp "${SCRIPT_DIR}/config/plugins-manifest.codex.json" "${TARGET_ROOT}/config/plugins-manifest.codex.json"
cp "${SCRIPT_DIR}/config/upstream-lock.json" "${TARGET_ROOT}/config/upstream-lock.json"
if [[ -f "${SCRIPT_DIR}/config/skills-lock.json" ]]; then
  cp "${SCRIPT_DIR}/config/skills-lock.json" "${TARGET_ROOT}/config/skills-lock.json"
fi

if [[ ! -f "${TARGET_ROOT}/settings.json" ]]; then
  cp "${SCRIPT_DIR}/config/settings.template.codex.json" "${TARGET_ROOT}/settings.json"
fi

if [[ "${INSTALL_EXTERNAL}" == "true" ]]; then
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
    if "${PYTHON_BIN}" -c "import ivy; print(ivy.__version__)" >/dev/null 2>&1; then
      echo "[INFO] ivy Python package already installed"
    else
      echo "[WARN] ivy Python package not detected. Install manually (pip install ivy) to enable framework-interop analyzer hints."
    fi
  else
    echo "[WARN] python not detected. Install Python + ivy (pip install ivy) if you want framework-interop analyzer hints."
  fi

  if ! command -v fuck-u-code >/dev/null 2>&1; then
    echo "[WARN] fuck-u-code CLI not detected. Install manually if you want external quality-debt analyzer hints (quality-debt-overlay still works without it)."
  fi
fi

if [[ ${#MISSING_REQUIRED[@]} -gt 0 ]]; then
  uniq_missing="$(printf "%s\n" "${MISSING_REQUIRED[@]}" | sort -u | tr '\n' ',' | sed 's/,$//')"
  echo "[FAIL] Missing required vendored skills: ${uniq_missing}"
  exit 1
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

echo "Install done. Run: bash check.sh --profile ${PROFILE} --target-root ${TARGET_ROOT}"
