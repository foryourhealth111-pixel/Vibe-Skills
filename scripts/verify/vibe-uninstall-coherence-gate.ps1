param(
    [string]$TargetRoot = '',
    [switch]$WriteArtifacts
)

$ErrorActionPreference = 'Stop'

function Add-Assertion {
    param(
        [System.Collections.Generic.List[object]]$Collection,
        [bool]$Condition,
        [string]$Message
    )

    if ($Condition) {
        Write-Host "[PASS] $Message"
    } else {
        Write-Host "[FAIL] $Message" -ForegroundColor Red
    }

    [void]$Collection.Add([pscustomobject]@{
        ok = $Condition
        message = $Message
    })
}

function Write-Artifacts {
    param(
        [string]$RepoRoot,
        [psobject]$Artifact
    )

    $outputDir = Join-Path $RepoRoot 'outputs\verify'
    New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

    $jsonPath = Join-Path $outputDir 'vibe-uninstall-coherence-gate.json'
    $mdPath = Join-Path $outputDir 'vibe-uninstall-coherence-gate.md'

    Write-VgoUtf8NoBomText -Path $jsonPath -Content ($Artifact | ConvertTo-Json -Depth 100)

    $lines = @(
        '# VCO Uninstall Coherence Gate',
        '',
        ('- Gate Result: **{0}**' -f $Artifact.gate_result),
        ('- Repo Root: `{0}`' -f $Artifact.repo_root),
        ('- Uninstall Entry: `{0}` / `{1}`' -f $Artifact.contract.uninstall_ps1, $Artifact.contract.uninstall_sh),
        ('- Documentation: `{0}`' -f $Artifact.contract.docs),
        ('- Assertion Failures: {0}' -f $Artifact.summary.failures),
        ('- Warnings: {0}' -f $Artifact.summary.warnings),
        ''
    )

    if ($Artifact.assertions.Count -gt 0) {
        $lines += '## Assertions'
        $lines += ''
        foreach ($item in $Artifact.assertions) {
            $lines += ('- [{0}] {1}' -f $(if ($item.ok) { 'PASS' } else { 'FAIL' }), $item.message)
        }
        $lines += ''
    }

    if ($Artifact.warnings.Count -gt 0) {
        $lines += '## Warnings'
        $lines += ''
        foreach ($item in $Artifact.warnings) {
            $lines += ('- {0}' -f $item)
        }
        $lines += ''
    }

    Write-VgoUtf8NoBomText -Path $mdPath -Content ($lines -join "`n")
}

. (Join-Path $PSScriptRoot '..\common\vibe-governance-helpers.ps1')

$TargetRoot = Resolve-VgoTargetRoot -TargetRoot $TargetRoot

$context = Get-VgoGovernanceContext -ScriptPath $PSCommandPath -EnforceExecutionContext
$assertions = New-Object System.Collections.Generic.List[object]
$warnings = New-Object System.Collections.Generic.List[string]

$repoRoot = [string]$context.repoRoot
$uninstallPs1 = [System.IO.Path]::Combine($repoRoot, 'uninstall.ps1')
$uninstallSh = [System.IO.Path]::Combine($repoRoot, 'uninstall.sh')
$docPath = [System.IO.Path]::Combine($repoRoot, 'docs', 'uninstall-governance.md')
$adapterRegistryPath = [System.IO.Path]::Combine($repoRoot, 'config', 'adapter-registry.json')
$adapterClosures = @()

if (Test-Path -LiteralPath $adapterRegistryPath) {
    try {
        $adapterRegistry = Get-Content -LiteralPath $adapterRegistryPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $adapterClosures = @($adapterRegistry.adapters | ForEach-Object {
            [pscustomobject]@{
                adapter_id = [string]$_.id
                closure_path = [System.IO.Path]::Combine($repoRoot, ([string]$_.closure -replace '/', [System.IO.Path]::DirectorySeparatorChar))
            }
        })
    } catch {
        $adapterClosures = @()
    }
}

$results = [ordered]@{
    gate = 'vibe-uninstall-coherence-gate'
    repo_root = $context.repoRoot
    target_root = [System.IO.Path]::GetFullPath($TargetRoot)
    generated_at = (Get-Date).ToString('s')
    gate_result = 'FAIL'
    assertions = @()
    warnings = @()
    contract = [ordered]@{
        uninstall_ps1 = $uninstallPs1
        uninstall_sh = $uninstallSh
        docs = $docPath
        adapter_registry = $adapterRegistryPath
        adapter_closures = @()
    }
    summary = [ordered]@{
        failures = 0
        warnings = 0
    }
}

Write-Host '=== VCO Uninstall Coherence Gate ==='
Write-Host ("Repo root  : {0}" -f $context.repoRoot)
Write-Host ("Target root: {0}" -f $TargetRoot)
Write-Host ''

Add-Assertion -Collection $assertions -Condition (Test-Path -LiteralPath $uninstallPs1) -Message '[repo] uninstall.ps1 entrypoint exists'
Add-Assertion -Collection $assertions -Condition (Test-Path -LiteralPath $uninstallSh) -Message '[repo] uninstall.sh entrypoint exists'
Add-Assertion -Collection $assertions -Condition (Test-Path -LiteralPath $docPath) -Message '[docs] uninstall governance doc exists'
Add-Assertion -Collection $assertions -Condition (Test-Path -LiteralPath $adapterRegistryPath) -Message '[config] adapter-registry.json exists'

if (Test-Path -LiteralPath $docPath) {
    Add-Assertion -Collection $assertions -Condition (Select-String -LiteralPath $docPath -Pattern 'owned-only' -SimpleMatch -Quiet) -Message '[docs] governance doc states owned-only uninstall'
    Add-Assertion -Collection $assertions -Condition (Select-String -LiteralPath $docPath -Pattern 'ledger-first' -SimpleMatch -Quiet) -Message '[docs] governance doc mentions ledger-first ownership'
} else {
    Add-Assertion -Collection $assertions -Condition $false -Message '[docs] governance doc states owned-only uninstall'
    Add-Assertion -Collection $assertions -Condition $false -Message '[docs] governance doc mentions ledger-first ownership'
}

if ($adapterClosures.Count -eq 0) {
    Add-Assertion -Collection $assertions -Condition $false -Message '[config] adapter-registry.json yielded adapter closures'
} else {
    Add-Assertion -Collection $assertions -Condition $true -Message '[config] adapter-registry.json yielded adapter closures'
}

$results.contract.adapter_closures = @($adapterClosures | ForEach-Object { [string]$_.closure_path })

foreach ($adapterEntry in $adapterClosures) {
    $adapterId = [string]$adapterEntry.adapter_id
    $adapterPath = [string]$adapterEntry.closure_path
    if (-not (Test-Path -LiteralPath $adapterPath)) {
        Add-Assertion -Collection $assertions -Condition $false -Message ("[closure] {0} adapter closure file exists" -f $adapterId)
        continue
    }

    $adapterJson = Get-Content -LiteralPath $adapterPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $contract = $adapterJson.uninstall_contract
    Add-Assertion -Collection $assertions -Condition ($null -ne $contract) -Message ("[closure] {0} declares uninstall_contract" -f $adapterId)
    if ($null -ne $contract) {
        Add-Assertion -Collection $assertions -Condition ($contract.ledger_first -eq $true) -Message ("[closure] {0} requests ledger_first" -f $adapterId)
        Add-Assertion -Collection $assertions -Condition ([string]::IsNullOrWhiteSpace($contract.documentation_reference) -eq $false) -Message ("[closure] {0} points to docs/uninstall-governance.md" -f $adapterId)
    }
}

$failed = @($assertions | Where-Object { -not $_.ok }).Count
$results.summary.failures = $failed
$results.summary.warnings = $warnings.Count
$results.assertions = $assertions
$results.warnings = $warnings
$results.gate_result = if ($failed -eq 0) { 'PASS' } else { 'FAIL' }

if ($WriteArtifacts) {
    Write-Artifacts -RepoRoot $context.repoRoot -Artifact $results
}

if ($failed -ne 0) {
    exit 1
}
