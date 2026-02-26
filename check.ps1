param(
  [ValidateSet("minimal", "full")]
  [string]$Profile = "full",
  [string]$TargetRoot = (Join-Path $env:USERPROFILE ".codex")
)

$requiredSkills = @('vibe', 'dialectic', 'local-vco-roles', 'spec-kit-vibe-compat', 'superclaude-framework-compat', 'ralph-loop', 'cancel-ralph', 'tdd-guide', 'think-harder')
$requiredWorkflow = @('brainstorming', 'writing-plans', 'subagent-driven-development', 'systematic-debugging')
$optionalWorkflow = @('requesting-code-review', 'receiving-code-review', 'verification-before-completion')

$pass = 0
$fail = 0
$warn = 0

function Check-Path {
  param([string]$Label, [string]$Path, [bool]$Required = $true)
  if (Test-Path -LiteralPath $Path) {
    Write-Host "[OK] $Label"
    $script:pass++
  } elseif ($Required) {
    Write-Host "[FAIL] $Label -> $Path" -ForegroundColor Red
    $script:fail++
  } else {
    Write-Host "[WARN] $Label -> $Path" -ForegroundColor Yellow
    $script:warn++
  }
}

Write-Host "=== VCO Codex Health Check ===" -ForegroundColor Cyan
Write-Host "Target: $TargetRoot"

Check-Path -Label "settings.json" -Path (Join-Path $TargetRoot 'settings.json')
Check-Path -Label "plugins manifest" -Path (Join-Path $TargetRoot 'config\plugins-manifest.codex.json')
Check-Path -Label "upstream lock" -Path (Join-Path $TargetRoot 'config\upstream-lock.json')

foreach ($name in $requiredSkills) {
  Check-Path -Label "skill/$name" -Path (Join-Path $TargetRoot "skills\$name\SKILL.md")
}

Check-Path -Label "vibe router script" -Path (Join-Path $TargetRoot "skills\vibe\scripts\router\resolve-pack-route.ps1")
Check-Path -Label "vibe memory governance config" -Path (Join-Path $TargetRoot "skills\vibe\config\memory-governance.json")
Check-Path -Label "vibe data scale overlay config" -Path (Join-Path $TargetRoot "skills\vibe\config\data-scale-overlay.json")
Check-Path -Label "vibe quality debt overlay config" -Path (Join-Path $TargetRoot "skills\vibe\config\quality-debt-overlay.json")
Check-Path -Label "vibe framework interop overlay config" -Path (Join-Path $TargetRoot "skills\vibe\config\framework-interop-overlay.json")
Check-Path -Label "vibe ml lifecycle overlay config" -Path (Join-Path $TargetRoot "skills\vibe\config\ml-lifecycle-overlay.json")
Check-Path -Label "vibe python clean code overlay config" -Path (Join-Path $TargetRoot "skills\vibe\config\python-clean-code-overlay.json")
Check-Path -Label "vibe system design overlay config" -Path (Join-Path $TargetRoot "skills\vibe\config\system-design-overlay.json")
Check-Path -Label "vibe cuda kernel overlay config" -Path (Join-Path $TargetRoot "skills\vibe\config\cuda-kernel-overlay.json")

foreach ($name in $requiredWorkflow) {
  Check-Path -Label "workflow skill/$name" -Path (Join-Path $TargetRoot "skills\$name\SKILL.md")
}

if ($Profile -eq 'full') {
  foreach ($name in $optionalWorkflow) {
    Check-Path -Label "optional workflow skill/$name" -Path (Join-Path $TargetRoot "skills\$name\SKILL.md") -Required:$false
  }
}

Check-Path -Label "rules/common" -Path (Join-Path $TargetRoot 'rules\common\agents.md')
Check-Path -Label "hooks/write-guard.js" -Path (Join-Path $TargetRoot 'hooks\write-guard.js')
Check-Path -Label "mcp template" -Path (Join-Path $TargetRoot 'mcp\servers.template.json')

if (Get-Command npm -ErrorAction SilentlyContinue) {
  Write-Host "[OK] npm"
  $pass++
} else {
  Write-Host "[WARN] npm not found (needed for claude-flow)" -ForegroundColor Yellow
  $warn++
}

Write-Host ""
Write-Host "Result: $pass passed, $fail failed, $warn warnings"
if ($fail -gt 0) { exit 1 }
