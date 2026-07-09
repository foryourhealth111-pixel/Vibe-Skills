param(
    [string]$SkillsRoot = "",
    [string]$RuntimeCorePackagingPath = "",
    [string]$SkillsLockPath = ""
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "lib\VibeOfflineSkillsAudit.ps1")
. (Join-Path $PSScriptRoot "lib\VibeOfflineSkillsAudit.Suites.ps1")

$summary = Invoke-VibeOfflineLockParityAudit `
    -ScriptRoot $PSScriptRoot `
    -SkillsRoot $SkillsRoot `
    -RuntimeCorePackagingPath $RuntimeCorePackagingPath `
    -SkillsLockPath $SkillsLockPath `
    -RequireSkillsLock
if (-not $summary.gate_passed) {
    exit 1
}

Write-Host "Vibe offline lock-parity audit passed." -ForegroundColor Green
exit 0
