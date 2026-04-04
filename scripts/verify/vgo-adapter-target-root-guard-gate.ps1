param(
    [string]$RepoRoot = '',
    [switch]$WriteArtifacts
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
}

. (Join-Path $RepoRoot 'scripts\common\vibe-governance-helpers.ps1')

function Convert-ToDemoTargetRoot {
    param(
        [Parameter(Mandatory)] [string]$RelativePath,
        [switch]$RepoLocal
    )

    $base = if ($RepoLocal) { 'C:\repo' } else { 'C:\Users\demo' }
    $suffix = ([string]$RelativePath).Replace('/', '\').TrimStart('\')
    if ([string]::IsNullOrWhiteSpace($suffix)) {
        return $base
    }
    return ($base.TrimEnd('\') + '\' + $suffix)
}

$catalog = Resolve-VgoHostCatalog -StartPath $RepoRoot
$cases = @()

foreach ($entry in @($catalog.entries.Values | Sort-Object id)) {
    $cases += [pscustomobject]@{
        host = [string]$entry.id
        target = Convert-ToDemoTargetRoot -RelativePath ([string]$entry.rel)
        should_throw = $false
        kind = 'default-target-root'
    }
}

$hostEntries = @($catalog.entries.Values | Where-Object { [string]$_.id -ne 'generic' } | Sort-Object id)
foreach ($entry in $hostEntries) {
    foreach ($foreign in $hostEntries) {
        if ([string]$entry.id -eq [string]$foreign.id) {
            continue
        }

        $cases += [pscustomobject]@{
            host = [string]$entry.id
            target = Convert-ToDemoTargetRoot -RelativePath ([string]$foreign.rel)
            should_throw = $true
            kind = 'foreign-host-root'
        }
    }

    $cases += [pscustomobject]@{
        host = 'generic'
        target = Convert-ToDemoTargetRoot -RelativePath ([string]$entry.rel)
        should_throw = $true
        kind = 'generic-vs-host-root'
    }
}

$cases += [pscustomobject]@{
    host = 'opencode'
    target = Convert-ToDemoTargetRoot -RelativePath '.opencode' -RepoLocal
    should_throw = $false
    kind = 'opencode-repo-local-root'
}

$failures = @()
$rows = @()

foreach ($case in $cases) {
    $threw = $false
    try {
        Assert-VgoTargetRootMatchesHostIntent -TargetRoot $case.target -HostId $case.host
    } catch {
        $threw = $true
    }
    if ($threw -ne [bool]$case.should_throw) {
        $failures += "guard mismatch kind=$($case.kind) host=$($case.host) target=$($case.target) expected_throw=$($case.should_throw) actual_throw=$threw"
    }
    $rows += [pscustomobject]@{
        kind = [string]$case.kind
        host = [string]$case.host
        target = [string]$case.target
        expected_throw = [bool]$case.should_throw
        actual_throw = [bool]$threw
    }
}

$gateResult = if ($failures.Count -eq 0) { 'PASS' } else { 'FAIL' }
$gatePayload = [ordered]@{}
$gatePayload['gate'] = 'vgo-adapter-target-root-guard-gate'
$gatePayload['result'] = $gateResult
$gatePayload['row_count'] = @($rows).Count
$gatePayload['rows'] = @($rows)
$gatePayload['failures'] = @($failures)

if ($WriteArtifacts) {
    $outDir = Join-Path $RepoRoot 'outputs\verify'
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null
    $outPath = Join-Path $outDir 'vgo-adapter-target-root-guard-gate.json'
    $gatePayload | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $outPath -Encoding UTF8
}

$gatePayload | ConvertTo-Json -Depth 10
if ($failures.Count -gt 0) { exit 1 }
