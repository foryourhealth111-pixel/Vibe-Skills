#!/usr/bin/env bash
# VCO Health Check — verifies all dependencies are installed

CLAUDE_DIR="${HOME}/.claude"
PASS=0
FAIL=0
WARN=0

check() {
  local label="$1" path="$2" required="${3:-true}"
  if [ -e "$path" ]; then
    echo "  [OK] $label"
    ((PASS++))
  elif [ "$required" = "true" ]; then
    echo "  [FAIL] $label — missing: $path"
    ((FAIL++))
  else
    echo "  [WARN] $label — optional, missing: $path"
    ((WARN++))
  fi
}

echo "=== VCO Health Check ==="
echo ""

echo "Skills:"
check "VCO skill (SKILL.md)" "${CLAUDE_DIR}/skills/vibe/SKILL.md"
check "Protocol: do.md" "${CLAUDE_DIR}/skills/vibe/protocols/do.md"
check "Protocol: think.md" "${CLAUDE_DIR}/skills/vibe/protocols/think.md"
check "Protocol: review.md" "${CLAUDE_DIR}/skills/vibe/protocols/review.md"
check "Protocol: team.md" "${CLAUDE_DIR}/skills/vibe/protocols/team.md"
check "Protocol: retro.md" "${CLAUDE_DIR}/skills/vibe/protocols/retro.md"

echo ""
echo "Rules:"
check "Common rules" "${CLAUDE_DIR}/rules/common/agents.md"
check "TypeScript rules" "${CLAUDE_DIR}/rules/typescript/coding-style.md" false

echo ""
echo "Commands:"
check "SuperClaude sc:design" "${CLAUDE_DIR}/commands/sc/design.md"
check "SuperClaude sc:research" "${CLAUDE_DIR}/commands/sc/research.md"
check "SuperClaude sc:brainstorm" "${CLAUDE_DIR}/commands/sc/brainstorm.md"

echo ""
echo "Settings:"
check "settings.json" "${CLAUDE_DIR}/settings.json"

echo ""
echo "External tools:"
if command -v claude &>/dev/null; then
  echo "  [OK] claude CLI"
  ((PASS++))
else
  echo "  [FAIL] claude CLI not found"
  ((FAIL++))
fi

if command -v npm &>/dev/null; then
  echo "  [OK] npm"
  ((PASS++))
  if npm list -g claude-flow &>/dev/null 2>&1; then
    echo "  [OK] claude-flow (global)"
    ((PASS++))
  else
    echo "  [WARN] claude-flow not installed (needed for XL grade only)"
    ((WARN++))
  fi
else
  echo "  [WARN] npm not found"
  ((WARN++))
fi

echo ""
echo "=== Results: ${PASS} passed, ${FAIL} failed, ${WARN} warnings ==="
if [ "$FAIL" -gt 0 ]; then
  echo "Run install.sh to fix missing dependencies."
  exit 1
fi
