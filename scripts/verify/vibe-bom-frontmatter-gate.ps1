param(
    [string]$TargetRoot = '',
    [switch]$WriteArtifacts
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\common\vibe-governance-helpers.ps1')

function Test-Byte0Frontmatter {
    param([byte[]]$Bytes)
    return ($null -ne $Bytes -and $Bytes.Length -ge 3 -and $Bytes[0] -eq 0x2D -and $Bytes[1] -eq 0x2D -and $Bytes[2] -eq 0x2D)
}

function Get-FirstBytesHex {
    param([byte[]]$Bytes, [int]$Count = 6)
    if ($null -eq $Bytes -or $Bytes.Length -eq 0) { return $null }
    $take = [Math]::Min($Count, $Bytes.Length)
    return ((0..($take - 1)) | ForEach-Object { '{0:X2}' -f $Bytes[$_] }) -join ''
}

function Write-GateArtifacts {
    param(
        [string]$RepoRoot,
        [psobject]$Artifact
    )

    $outputDir = Join-Path $RepoRoot 'outputs\verify'
    New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
    $jsonPath = Join-Path $outputDir 'vibe-bom-frontmatter-gate.json'
    $mdPath = Join-Path $outputDir 'vibe-bom-frontmatter-gate.md'

    Write-VgoUtf8NoBomText -Path $jsonPath -Content ($Artifact | ConvertTo-Json -Depth 100)

    $lines = @(
        '# VCO BOM / Frontmatter Gate',
        '',
        ('- Gate Result: **{0}**' -f $Artifact.gate_result),
        ('- Repo Root: `{0}`' -f $Artifact.repo_root),
        ('- Target Root: `{0}`' -f $(if ([string]::IsNullOrWhiteSpace($Artifact.target_root)) { '<not provided>' } else { $Artifact.target_root })),
        ('- Policy: `{0}`' -f $Artifact.policy_path),
        '',
        '## Summary',
        '',
        ('- Active Scopes: {0}' -f $Artifact.summary.active_scopes),
        ('- Items Checked: {0}' -f $Artifact.summary.items_checked),
        ('- Failures: {0}' -f $Artifact.summary.failures),
        ''
    )

    foreach ($item in $Artifact.items) {
        $lines += ('- [{0}] `{1}` :: exists={2}, bom={3}, byte0_frontmatter={4}, result={5}' -f $item.scope, $item.path, $item.exists, $item.has_utf8_bom, $item.byte0_frontmatter, $item.result)
    }

    Write-VgoUtf8NoBomText -Path $mdPath -Content ($lines -join "`n")
}

$context = Get-VgoGovernanceContext -ScriptPath $PSCommandPath -EnforceExecutionContext
$policyPath = Join-Path $context.repoRoot 'config\frontmatter-integrity-policy.json'
if (-not (Test-Path -LiteralPath $policyPath)) {
    throw "frontmatter policy missing: $policyPath"
}
$policy = Get-Content -LiteralPath $policyPath -Raw -Encoding UTF8 | ConvertFrom-Json

$runtimeRel = 'skills/vibe'
if ($null -ne $context.runtimeConfig -and $context.runtimeConfig.PSObject.Properties.Name -contains 'target_relpath' -and -not [string]::IsNullOrWhiteSpace([string]$context.runtimeConfig.target_relpath)) {
    $runtimeRel = [string]$context.runtimeConfig.target_relpath
}

$governanceDocPath = Join-Path $context.repoRoot 'docs\frontmatter-bom-governance.md'
$helpersPath = Join-Path $context.repoRoot 'scripts\common\vibe-governance-helpers.ps1'
$releaseCutPath = Join-Path $context.repoRoot 'scripts\governance\release-cut.ps1'
$installedFreshnessGateRel = 'scripts/verify/vibe-installed-runtime-freshness-gate.ps1'
if ($null -ne $context.runtimeConfig -and $context.runtimeConfig.PSObject.Properties.Name -contains 'post_install_gate' -and -not [string]::IsNullOrWhiteSpace([string]$context.runtimeConfig.post_install_gate)) {
    $installedFreshnessGateRel = [string]$context.runtimeConfig.post_install_gate
}
$installedFreshnessGatePath = Join-Path $context.repoRoot $installedFreshnessGateRel

$results = [ordered]@{
    gate = 'vibe-bom-frontmatter-gate'
    repo_root = $context.repoRoot
    target_root = if ([string]::IsNullOrWhiteSpace($TargetRoot)) { '' } else { [System.IO.Path]::GetFullPath($TargetRoot) }
    policy_path = $policyPath
    generated_at = (Get-Date).ToString('s')
    gate_result = 'FAIL'
    items = @()
    summary = [ordered]@{
        active_scopes = 0
        items_checked = 0
        failures = 0
    }
}

$failed = $false
foreach ($scope in @($policy.scopes)) {
    $scopeId = [string]$scope.id
    $basePath = $null
    $active = $true
    $skipReason = $null

    switch ($scope.root) {
        'canonical' { $basePath = $context.canonicalRoot }
        'bundled' {
            $basePath = $context.bundledRoot
            if ($null -eq $context.bundledTarget -or [string]::IsNullOrWhiteSpace([string]$context.bundledRoot)) {
                $active = $false
                $skipReason = 'bundled target absent'
            }
        }
        'nested_bundled' {
            $basePath = $context.nestedBundledRoot
            if ($null -eq $context.nestedTarget -or [string]::IsNullOrWhiteSpace([string]$context.nestedBundledRoot) -or -not [bool]$context.nestedTarget.exists) {
                $active = $false
                $skipReason = 'nested_bundled target absent'
            }
        }
        'installed' {
            if ([string]::IsNullOrWhiteSpace($TargetRoot)) {
                $active = $false
                $skipReason = 'TargetRoot not provided'
            } else {
                $basePath = Join-Path $TargetRoot $runtimeRel
            }
        }
        default {
            $active = $false
            $skipReason = ('unknown scope root: {0}' -f $scope.root)
        }
    }

    if ($active) {
        $results.summary.active_scopes++
    }

    foreach ($rel in @($scope.relpaths)) {
        $fullPath = if ($null -ne $basePath) { Join-Path $basePath $rel } else { $rel }
        $exists = $active -and (Test-Path -LiteralPath $fullPath)
        $hasBom = $false
        $byte0Frontmatter = $false
        $firstBytesHex = $null
        $result = 'SKIP'
        $reason = $skipReason

        if ($active) {
            $results.summary.items_checked++
            if ($exists) {
                $bytes = [System.IO.File]::ReadAllBytes($fullPath)
                $hasBom = [bool](Test-VgoUtf8BomBytes -Bytes $bytes)
                $byte0Frontmatter = [bool](Test-Byte0Frontmatter -Bytes $bytes)
                $firstBytesHex = Get-FirstBytesHex -Bytes $bytes
                if ((-not $hasBom) -and $byte0Frontmatter) {
                    $result = 'PASS'
                    $reason = 'byte0 frontmatter visible'
                } else {
                    $result = 'FAIL'
                    if ($hasBom) {
                        $reason = 'UTF-8 BOM present before frontmatter'
                    } elseif (-not $byte0Frontmatter) {
                        $reason = 'byte0 is not ---'
                    }
                    $failed = $true
                    $results.summary.failures++
                }
            } else {
                $result = 'FAIL'
                $reason = 'frontmatter-sensitive file missing'
                $failed = $true
                $results.summary.failures++
            }
        }

        $results.items += [pscustomobject]@{
            scope = $scopeId
            path = $fullPath
            exists = [bool]$exists
            has_utf8_bom = [bool]$hasBom
            byte0_frontmatter = [bool]$byte0Frontmatter
            first_bytes_hex = $firstBytesHex
            result = $result
            reason = $reason
        }
    }
}

$governanceDocText = if (Test-Path -LiteralPath $governanceDocPath) { Get-Content -LiteralPath $governanceDocPath -Raw -Encoding UTF8 } else { '' }
$releaseCutText = if (Test-Path -LiteralPath $releaseCutPath) { Get-Content -LiteralPath $releaseCutPath -Raw -Encoding UTF8 } else { '' }

$extraChecks = @(
    [pscustomobject]@{
        scope = 'governance_doc'
        path = $governanceDocPath
        pass = ((Test-Path -LiteralPath $governanceDocPath) -and ($governanceDocText -match 'stop-ship') -and ($governanceDocText -match '字节 0|byte-0'))
        reason = 'frontmatter governance doc exists and documents byte-0 stop-ship contract'
    },
    [pscustomobject]@{
        scope = 'governance_helpers'
        path = $helpersPath
        pass = (Test-Path -LiteralPath $helpersPath)
        reason = 'no-BOM governance helper exists'
    },
    [pscustomobject]@{
        scope = 'release_cut_writer'
        path = $releaseCutPath
        pass = ((Test-Path -LiteralPath $releaseCutPath) -and ($releaseCutText -match 'Write-VgoUtf8NoBomText'))
        reason = 'release-cut is wired to UTF-8 no-BOM writer'
    },
    [pscustomobject]@{
        scope = 'installed_runtime_closure'
        path = $installedFreshnessGatePath
        pass = (Test-Path -LiteralPath $installedFreshnessGatePath)
        reason = 'installed runtime freshness gate from effective runtime config exists for runtime closure'
    }
)

foreach ($check in $extraChecks) {
    $results.summary.items_checked++
    if (-not $check.pass) {
        $failed = $true
        $results.summary.failures++
    }
    $results.items += [pscustomobject]@{
        scope = $check.scope
        path = $check.path
        exists = [bool](Test-Path -LiteralPath $check.path)
        has_utf8_bom = $null
        byte0_frontmatter = $null
        first_bytes_hex = $null
        result = if ($check.pass) { 'PASS' } else { 'FAIL' }
        reason = $check.reason
    }
}

$results.gate_result = if ($failed) { 'FAIL' } else { 'PASS' }
Write-Host '=== VCO BOM / Frontmatter Gate ==='
foreach ($item in $results.items) {
    $color = if ($item.result -eq 'PASS') { 'Green' } elseif ($item.result -eq 'FAIL') { 'Red' } else { 'Yellow' }
    Write-Host ('[{0}] {1} -> {2} ({3})' -f $item.result, $item.scope, $item.path, $item.reason) -ForegroundColor $color
}

if ($WriteArtifacts) {
    Write-GateArtifacts -RepoRoot $context.repoRoot -Artifact ([pscustomobject]$results)
}

if ($failed) { exit 1 }
exit 0
