param(
    [string]$SkillsRoot = "",
    [string]$RuntimeCorePackagingPath = "",
    [string]$SkillsLockPath = "",
    [switch]$SkipHash
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "lib\VibeOfflineSkillsAudit.ps1")
. (Join-Path $PSScriptRoot "lib\VibeOfflineSkillsAudit.Suites.ps1")

$requiredSummary = Invoke-VibeOfflineRequiredSkillsAudit `
    -ScriptRoot $PSScriptRoot `
    -SkillsRoot $SkillsRoot `
    -RuntimeCorePackagingPath $RuntimeCorePackagingPath

$lockParitySummary = Invoke-VibeOfflineLockParityAudit `
    -ScriptRoot $PSScriptRoot `
    -SkillsRoot $SkillsRoot `
    -RuntimeCorePackagingPath $RuntimeCorePackagingPath `
    -SkillsLockPath $SkillsLockPath

$summaries = @($requiredSummary, $lockParitySummary)
if (-not $SkipHash) {
    $hashSummary = Invoke-VibeOfflineHashAudit `
        -ScriptRoot $PSScriptRoot `
        -SkillsRoot $SkillsRoot `
        -RuntimeCorePackagingPath $RuntimeCorePackagingPath `
        -SkillsLockPath $SkillsLockPath
    $summaries += $hashSummary
}

$totalAssertions = (@($summaries | Measure-Object -Property total -Sum).Sum)
$passedAssertions = (@($summaries | Measure-Object -Property passed -Sum).Sum)
$failedAssertions = (@($summaries | Measure-Object -Property failed -Sum).Sum)

Write-Host ""
Write-Host "=== VCO Offline Skills Gate (Compatibility Wrapper) ==="
Write-Host ("Suites: {0}" -f $summaries.Count)
Write-Host ("skip_hash={0}" -f $SkipHash.IsPresent)
Write-Host ("Total assertions: {0}" -f $totalAssertions)
Write-Host ("Passed: {0}" -f $passedAssertions)
Write-Host ("Failed: {0}" -f $failedAssertions)

if ($failedAssertions -gt 0) {
    exit 1
}

Write-Host "Offline skill audit wrapper passed." -ForegroundColor Green
exit 0
