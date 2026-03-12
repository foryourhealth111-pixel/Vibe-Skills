param(
    [switch]$WriteArtifacts,
    [switch]$Strict
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\common\vibe-governance-helpers.ps1')

function Assert-True {
    param(
        [bool]$Condition,
        [string]$Message
    )

    if ($Condition) {
        Write-Host "[PASS] $Message" -ForegroundColor Green
        return $true
    }

    Write-Host "[FAIL] $Message" -ForegroundColor Red
    return $false
}

function Get-GitStatusEntries {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot
    )

    $lines = @(& git -C $RepoRoot -c core.quotePath=false status --porcelain=v1 --untracked-files=all)
    if ($LASTEXITCODE -ne 0) {
        throw 'git status failed while computing repo cleanliness.'
    }

    $entries = @()
    foreach ($line in $lines) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }

        $status = $line.Substring(0, 2).Trim()
        $pathText = $line.Substring(3).Trim()
        if ($pathText.Contains(' -> ')) {
            $pathText = ($pathText -split ' -> ')[-1]
        }

        $entries += [pscustomobject]@{
            status = $status
            path = $pathText.Replace('\', '/')
        }
    }

    return @($entries)
}

function Test-PathMatchesPolicy {
    param(
        [Parameter(Mandatory)] [string]$RelativePath,
        [Parameter(Mandatory)] [string[]]$Patterns
    )

    $normalized = ($RelativePath.Replace('\', '/')).TrimStart('./')
    foreach ($pattern in $Patterns) {
        if ([string]::IsNullOrWhiteSpace($pattern)) {
            continue
        }

        $candidate = ($pattern.Replace('\', '/')).TrimStart('./')
        if ($candidate.EndsWith('/')) {
            if ($normalized.StartsWith($candidate, [System.StringComparison]::OrdinalIgnoreCase)) {
                return $true
            }
        } elseif ($normalized.Equals($candidate, [System.StringComparison]::OrdinalIgnoreCase)) {
            return $true
        }
    }

    return $false
}

function Add-ClassifiedEntry {
    param(
        [hashtable]$Bucket,
        [string]$Key,
        [psobject]$Entry
    )

    $Bucket[$Key] += [pscustomobject]@{
        status = $Entry.status
        path = $Entry.path
    }
}

function Write-Artifacts {
    param(
        [string]$RepoRoot,
        [psobject]$Artifact
    )

    $outputDir = Join-Path $RepoRoot 'outputs\verify'
    New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

    $jsonPath = Join-Path $outputDir 'vibe-repo-cleanliness-gate.json'
    $mdPath = Join-Path $outputDir 'vibe-repo-cleanliness-gate.md'
    Write-VgoUtf8NoBomText -Path $jsonPath -Content ($Artifact | ConvertTo-Json -Depth 100)

    $lines = @(
        '# VCO Repo Cleanliness Gate',
        '',
        ('- Gate Result: **{0}**' -f $Artifact.gate_result),
        ('- Repo Root: `{0}`' -f $Artifact.repo_root),
        ('- Total Dirty Paths: {0}' -f $Artifact.summary.changed_paths),
        ('- Local Noise Visible: {0}' -f $Artifact.summary.local_noise_visible),
        ('- Runtime Generated Visible: {0}' -f $Artifact.summary.runtime_generated_visible),
        ('- Managed Workset Visible: {0}' -f $Artifact.summary.managed_workset_visible),
        ('- High-Risk Managed Visible: {0}' -f $Artifact.summary.high_risk_managed_visible),
        ('- Other Dirty Visible: {0}' -f $Artifact.summary.other_dirty_visible),
        ('- Repo Zero Dirty: {0}' -f $Artifact.summary.repo_zero_dirty),
        ''
    )

    if ($Artifact.local_noise.Count -gt 0) {
        $lines += '## Local Noise'
        $lines += ''
        foreach ($item in $Artifact.local_noise | Select-Object -First 50) {
            $lines += ('- `{0}` ({1})' -f $item.path, $item.status)
        }
        $lines += ''
    }

    if ($Artifact.runtime_generated.Count -gt 0) {
        $lines += '## Runtime-Generated Paths'
        $lines += ''
        foreach ($item in $Artifact.runtime_generated | Select-Object -First 50) {
            $lines += ('- `{0}` ({1})' -f $item.path, $item.status)
        }
        $lines += ''
    }

    if ($Artifact.other_dirty.Count -gt 0) {
        $lines += '## Other Dirty Paths'
        $lines += ''
        foreach ($item in $Artifact.other_dirty | Select-Object -First 50) {
            $lines += ('- `{0}` ({1})' -f $item.path, $item.status)
        }
        $lines += ''
    }

    if ($Artifact.managed_workset.Count -gt 0 -or $Artifact.high_risk_managed.Count -gt 0) {
        $lines += '## Advisory Workset Pressure'
        $lines += ''
        $lines += ('- Managed workset backlog remains visible: {0}' -f $Artifact.summary.managed_workset_visible)
        $lines += ('- High-risk mirror backlog remains visible: {0}' -f $Artifact.summary.high_risk_managed_visible)
        $lines += '- A PASS here means local hygiene is closed; it does not mean the repository is already zero-dirty.'
        $lines += ''
    }

    Write-VgoUtf8NoBomText -Path $mdPath -Content ($lines -join "`r`n")
}

$context = Get-VgoGovernanceContext -ScriptPath $PSCommandPath -EnforceExecutionContext
$policyPath = Join-Path $context.repoRoot 'config\repo-cleanliness-policy.json'
if (-not (Test-Path -LiteralPath $policyPath)) {
    throw "repo-cleanliness policy not found: $policyPath"
}

$policy = Get-Content -LiteralPath $policyPath -Raw | ConvertFrom-Json
$entries = @(Get-GitStatusEntries -RepoRoot $context.repoRoot)
$classified = @{
    local_noise = @()
    runtime_generated = @()
    managed_workset = @()
    high_risk_managed = @()
    other_dirty = @()
}

foreach ($entry in $entries) {
    if (Test-PathMatchesPolicy -RelativePath $entry.path -Patterns @($policy.local_noise_paths)) {
        Add-ClassifiedEntry -Bucket $classified -Key 'local_noise' -Entry $entry
        continue
    }

    if (Test-PathMatchesPolicy -RelativePath $entry.path -Patterns @($policy.runtime_generated_roots)) {
        Add-ClassifiedEntry -Bucket $classified -Key 'runtime_generated' -Entry $entry
        continue
    }

    if (Test-PathMatchesPolicy -RelativePath $entry.path -Patterns @($policy.high_risk_managed_roots)) {
        Add-ClassifiedEntry -Bucket $classified -Key 'high_risk_managed' -Entry $entry
        continue
    }

    if (Test-PathMatchesPolicy -RelativePath $entry.path -Patterns @($policy.managed_workset_roots)) {
        Add-ClassifiedEntry -Bucket $classified -Key 'managed_workset' -Entry $entry
        continue
    }

    $isRootPath = -not $entry.path.Contains('/')
    if ($isRootPath -and $policy.PSObject.Properties.Name -contains 'managed_root_files' -and (Test-PathMatchesPolicy -RelativePath $entry.path -Patterns @($policy.managed_root_files))) {
        Add-ClassifiedEntry -Bucket $classified -Key 'managed_workset' -Entry $entry
        continue
    }

    Add-ClassifiedEntry -Bucket $classified -Key 'other_dirty' -Entry $entry
}

$results = [ordered]@{
    gate = 'vibe-repo-cleanliness-gate'
    repo_root = $context.repoRoot
    generated_at = (Get-Date).ToString('s')
    strict = [bool]$Strict
    gate_result = 'FAIL'
    local_noise = @($classified.local_noise)
    runtime_generated = @($classified.runtime_generated)
    managed_workset = @($classified.managed_workset)
    high_risk_managed = @($classified.high_risk_managed)
    other_dirty = @($classified.other_dirty)
    summary = [ordered]@{
        changed_paths = $entries.Count
        local_noise_visible = $classified.local_noise.Count
        runtime_generated_visible = $classified.runtime_generated.Count
        managed_workset_visible = $classified.managed_workset.Count
        high_risk_managed_visible = $classified.high_risk_managed.Count
        other_dirty_visible = $classified.other_dirty.Count
        repo_zero_dirty = [bool]($entries.Count -eq 0)
        failures = 0
    }
}

Write-Host '=== VCO Repo Cleanliness Gate ===' -ForegroundColor Cyan
Write-Host ("Repo root : {0}" -f $context.repoRoot)
Write-Host ("Dirty paths: {0}" -f $entries.Count)
Write-Host ''

$assertions = @()
$assertions += Assert-True -Condition ($classified.local_noise.Count -eq 0) -Message '[cleanliness] no local scratch / operator noise is visible in git status'
$assertions += Assert-True -Condition ($classified.runtime_generated.Count -eq 0) -Message '[cleanliness] no runtime-generated artifacts are visible in git status'
$assertions += Assert-True -Condition ($classified.other_dirty.Count -eq 0) -Message '[cleanliness] no uncategorized dirty paths remain visible'
if ($Strict) {
    $assertions += Assert-True -Condition ($classified.managed_workset.Count -eq 0) -Message '[cleanliness:strict] no governed canonical workset backlog remains visible'
    $assertions += Assert-True -Condition ($classified.high_risk_managed.Count -eq 0) -Message '[cleanliness:strict] no high-risk bundled mirror backlog remains visible'
}

Write-Host ''
Write-Host ("Advisory managed workset : {0}" -f $classified.managed_workset.Count) -ForegroundColor Yellow
Write-Host ("Advisory high-risk mirror: {0}" -f $classified.high_risk_managed.Count) -ForegroundColor Yellow
Write-Host ("Repo zero-dirty          : {0}" -f ($entries.Count -eq 0)) -ForegroundColor Yellow

$results.summary.failures = @($assertions | Where-Object { -not $_ }).Count
$results.gate_result = if ($results.summary.failures -eq 0) { 'PASS' } else { 'FAIL' }

if ($WriteArtifacts) {
    Write-Artifacts -RepoRoot $context.repoRoot -Artifact ([pscustomobject]$results)
}

if ($results.summary.failures -gt 0) {
    exit 1
}
exit 0
