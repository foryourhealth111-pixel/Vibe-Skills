param(
    [switch]$WriteArtifacts,
    [string]$OutputDirectory = ''
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\common\vibe-governance-helpers.ps1')

function Write-GateArtifacts {
    param(
        [string]$RepoRoot,
        [string]$OutputDirectory,
        [psobject]$Artifact
    )

    $dir = if ([string]::IsNullOrWhiteSpace($OutputDirectory)) { Join-Path $RepoRoot 'outputs\verify' } else { $OutputDirectory }
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $jsonPath = Join-Path $dir 'vibe-governance-entry-compression-gate.json'
    $mdPath = Join-Path $dir 'vibe-governance-entry-compression-gate.md'

    Write-VgoUtf8NoBomText -Path $jsonPath -Content ($Artifact | ConvertTo-Json -Depth 100)

    $lines = @(
        '# VCO Governance Entry Compression Gate',
        '',
        ('- Gate Result: **{0}**' -f $Artifact.gate_result),
        ('- Repo Root: `{0}`' -f $Artifact.repo_root),
        ('- Missing required paths: `{0}`' -f $Artifact.summary.missing_required_paths),
        ('- Content violations: `{0}`' -f $Artifact.summary.content_violations),
        ('- Failure count: `{0}`' -f $Artifact.summary.failure_count),
        '',
        '## Required Entry Paths',
        ''
    )

    foreach ($p in @($Artifact.results.required_paths)) {
        $lines += ('- `{0}` exists=`{1}`' -f $p.relpath, $p.exists)
    }

    if (@($Artifact.results.failures).Count -gt 0) {
        $lines += ''
        $lines += '## Failures'
        $lines += ''
        foreach ($f in @($Artifact.results.failures)) {
            $lines += ('- {0}' -f $f)
        }
    }

    Write-VgoUtf8NoBomText -Path $mdPath -Content ($lines -join "`n")
}

function Require-File {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [AllowEmptyCollection()] [System.Collections.Generic.List[string]]$Failures
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        [void]$Failures.Add(("missing_required_file:{0}" -f $Path))
        return $false
    }
    return $true
}

$context = Get-VgoGovernanceContext -ScriptPath $PSCommandPath -EnforceExecutionContext
$repoRoot = $context.repoRoot

$familyMapPath = Join-Path $repoRoot 'docs\governance-family-map.md'
$operatorRunbookPath = Join-Path $repoRoot 'docs\operator-default-runbooks.md'
$contribRunbookPath = Join-Path $repoRoot 'docs\contributor-default-runbooks.md'
$gateFamilyIndexPath = Join-Path $repoRoot 'scripts\verify\gate-family-index.md'
$familyIndexJsonPath = Join-Path $repoRoot 'config\governance-family-index.json'

$docsReadmePath = Join-Path $repoRoot 'docs\README.md'
$proofBundlePath = Join-Path $repoRoot 'docs\status\non-regression-proof-bundle.md'
$repoReadmePath = Join-Path $repoRoot 'README.md'

$failures = New-Object System.Collections.Generic.List[string]
$requiredOk = $true
foreach ($p in @(
    $repoReadmePath,
    $docsReadmePath,
    $proofBundlePath,
    $gateFamilyIndexPath,
    $familyMapPath,
    $familyIndexJsonPath,
    $operatorRunbookPath,
    $contribRunbookPath
)) {
    $requiredOk = (Require-File -Path $p -Failures $failures) -and $requiredOk
}

$contentViolations = 0
if (Test-Path -LiteralPath $familyMapPath) {
    $mapText = Get-Content -LiteralPath $familyMapPath -Raw -Encoding UTF8
    foreach ($needle in @(
        'scripts/verify/gate-family-index.md',
        'config/governance-family-index.json',
        'docs/operator-default-runbooks.md',
        'docs/contributor-default-runbooks.md',
        'scripts/verify/vibe-governance-entry-compression-gate.ps1'
    )) {
        if ($mapText -notmatch [Regex]::Escape($needle)) {
            [void]$failures.Add(("governance_family_map_missing_reference:{0}" -f $needle))
            $contentViolations++
        }
    }
}

foreach ($pair in @(
    @{ path = $operatorRunbookPath; label = 'operator-runbook' },
    @{ path = $contribRunbookPath; label = 'contributor-runbook' }
)) {
    if (-not (Test-Path -LiteralPath $pair.path)) { continue }
    $text = Get-Content -LiteralPath $pair.path -Raw -Encoding UTF8

    foreach ($needle in @(
        'scripts/verify/gate-family-index.md',
        'docs/status/non-regression-proof-bundle.md'
    )) {
        if ($text -notmatch [Regex]::Escape($needle)) {
            [void]$failures.Add(("{0}_missing_reference:{1}" -f $pair.label, $needle))
            $contentViolations++
        }
    }

    if ($text -notmatch [Regex]::Escape('vibe-governance-entry-compression-gate.ps1')) {
        [void]$failures.Add(("{0}_missing_gate_reference:vibe-governance-entry-compression-gate.ps1" -f $pair.label))
        $contentViolations++
    }
}

if (Test-Path -LiteralPath $familyIndexJsonPath) {
    try {
        $idx = Get-Content -LiteralPath $familyIndexJsonPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ([string]$idx.policy -ne 'human-entry-compression-before-physical-consolidation') {
            [void]$failures.Add('governance_family_index_policy_mismatch')
            $contentViolations++
        }

        $entry = @($idx.human_entry_order)
        foreach ($expected in @('README.md', 'docs/README.md', 'docs/status/non-regression-proof-bundle.md', 'scripts/verify/gate-family-index.md')) {
            if (-not ($entry -contains $expected)) {
                [void]$failures.Add(("governance_family_index_missing_entry:{0}" -f $expected))
                $contentViolations++
            }
        }
    } catch {
        [void]$failures.Add('governance_family_index_invalid_json')
        $contentViolations++
    }
}

$requiredPaths = @(
    @{ relpath = 'README.md'; fullpath = $repoReadmePath },
    @{ relpath = 'docs/README.md'; fullpath = $docsReadmePath },
    @{ relpath = 'docs/status/non-regression-proof-bundle.md'; fullpath = $proofBundlePath },
    @{ relpath = 'scripts/verify/gate-family-index.md'; fullpath = $gateFamilyIndexPath },
    @{ relpath = 'docs/governance-family-map.md'; fullpath = $familyMapPath },
    @{ relpath = 'config/governance-family-index.json'; fullpath = $familyIndexJsonPath },
    @{ relpath = 'docs/operator-default-runbooks.md'; fullpath = $operatorRunbookPath },
    @{ relpath = 'docs/contributor-default-runbooks.md'; fullpath = $contribRunbookPath }
)

$requiredOut = @()
foreach ($p in $requiredPaths) {
    $requiredOut += [pscustomobject]@{
        relpath = [string]$p.relpath
        exists = [bool](Test-Path -LiteralPath $p.fullpath)
    }
}

$gateResult = if ($failures.Count -eq 0) { 'PASS' } else { 'FAIL' }
$summary = [pscustomobject]@{
    missing_required_paths = [int](@($failures | Where-Object { $_ -like 'missing_required_file:*' }).Count)
    content_violations = [int]$contentViolations
    failure_count = [int]$failures.Count
}

$artifact = [pscustomobject]@{
    gate = 'vibe-governance-entry-compression-gate'
    repo_root = $repoRoot
    generated_at = (Get-Date).ToString('s')
    gate_result = $gateResult
    summary = $summary
    results = [pscustomobject]@{
        required_paths = @($requiredOut)
        failures = @($failures)
    }
}

if ($WriteArtifacts) {
    Write-GateArtifacts -RepoRoot $repoRoot -OutputDirectory $OutputDirectory -Artifact $artifact
}

if ($failures.Count -gt 0) { exit 1 }

