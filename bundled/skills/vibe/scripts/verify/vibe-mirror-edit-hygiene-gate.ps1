param(
    [switch]$WriteArtifacts
)

$ErrorActionPreference = 'Stop'

function Assert-True {
    param(
        [bool]$Condition,
        [string]$Message
    )

    if ($Condition) {
        Write-Host "[PASS] $Message"
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
        throw 'git status failed while computing mirror edit hygiene.'
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

function Test-GovernedMirrorRelativePath {
    param(
        [Parameter(Mandatory)] [string]$RelativePath,
        [Parameter(Mandatory)] [psobject]$Packaging
    )

    $rel = $RelativePath.Replace('\\', '/')
    if (@($Packaging.mirror.files) -contains $rel) {
        return $true
    }

    foreach ($dir in @($Packaging.mirror.directories)) {
        $prefix = ('{0}/' -f $dir).Replace('\\', '/')
        if ($rel.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
            return $true
        }
    }

    return $false
}

function Test-MirrorMatchesCanonical {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$MirrorPath,
        [Parameter(Mandatory)] [string]$CanonicalRelativePath
    )

    $canonicalPath = Join-Path $RepoRoot $CanonicalRelativePath
    $resolvedMirrorPath = Join-Path $RepoRoot $MirrorPath
    if (-not (Test-Path -LiteralPath $canonicalPath) -or -not (Test-Path -LiteralPath $resolvedMirrorPath)) {
        return $false
    }

    $canonicalItem = Get-Item -LiteralPath $canonicalPath
    $mirrorItem = Get-Item -LiteralPath $resolvedMirrorPath
    if ($canonicalItem.PSIsContainer -or $mirrorItem.PSIsContainer) {
        return $false
    }

    $canonicalHash = (Get-FileHash -LiteralPath $canonicalPath -Algorithm SHA256).Hash
    $mirrorHash = (Get-FileHash -LiteralPath $resolvedMirrorPath -Algorithm SHA256).Hash
    return ($canonicalHash -eq $mirrorHash)
}

function Write-Artifacts {
    param(
        [string]$RepoRoot,
        [psobject]$Artifact
    )

    $outputDir = Join-Path $RepoRoot 'outputs\verify'
    New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

    $jsonPath = Join-Path $outputDir 'vibe-mirror-edit-hygiene-gate.json'
    $mdPath = Join-Path $outputDir 'vibe-mirror-edit-hygiene-gate.md'

    $Artifact | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

    $lines = @(
        '# VCO Mirror Edit Hygiene Gate',
        '',
        ('- Gate Result: **{0}**' -f $Artifact.gate_result),
        ('- Repo Root: `{0}`' -f $Artifact.repo_root),
        ('- Changed Paths: {0}' -f $Artifact.summary.changed_paths),
        ('- Mirror-only Edits: {0}' -f $Artifact.summary.mirror_only_edits),
        ('- Paired Mirror Edits: {0}' -f $Artifact.summary.paired_mirror_edits),
        ('- Reconciled Mirror Edits: {0}' -f $Artifact.summary.reconciled_mirror_edits),
        ('- Allowlisted Mirror Edits: {0}' -f $Artifact.summary.allowlisted_mirror_edits),
        ''
    )

    if ($Artifact.mirror_only_edits.Count -gt 0) {
        $lines += '## Mirror-only Edits'
        $lines += ''
        foreach ($item in $Artifact.mirror_only_edits) {
            $lines += ('- `{0}` ({1}) -> counterpart `{2}`' -f $item.path, $item.status, $item.canonical_counterpart)
        }
        $lines += ''
    }

    if ($Artifact.paired_mirror_edits.Count -gt 0) {
        $lines += '## Paired Mirror Edits'
        $lines += ''
        foreach ($item in $Artifact.paired_mirror_edits) {
            $lines += ('- `{0}` ({1}) paired with canonical `{2}`' -f $item.path, $item.status, $item.canonical_counterpart)
        }
        $lines += ''
    }

    if ($Artifact.reconciled_mirror_edits.Count -gt 0) {
        $lines += '## Reconciled Mirror Edits'
        $lines += ''
        foreach ($item in $Artifact.reconciled_mirror_edits) {
            $lines += ('- `{0}` ({1}) already matches canonical `{2}` and is treated as topology refresh' -f $item.path, $item.status, $item.canonical_counterpart)
        }
        $lines += ''
    }

    if ($Artifact.allowlisted_mirror_edits.Count -gt 0) {
        $lines += '## Allowlisted Mirror Edits'
        $lines += ''
        foreach ($item in $Artifact.allowlisted_mirror_edits) {
            $lines += ('- `{0}` ({1})' -f $item.path, $item.status)
        }
        $lines += ''
    }

    $lines | Set-Content -LiteralPath $mdPath -Encoding UTF8
}

. (Join-Path $PSScriptRoot '..\common\vibe-governance-helpers.ps1')

$context = Get-VgoGovernanceContext -ScriptPath $PSCommandPath -EnforceExecutionContext
$packaging = $context.packaging
$allowBundledOnly = @($packaging.allow_bundled_only)
$mirrorTargets = @($context.mirrorTargets | Where-Object { -not $_.isCanonical } | Sort-Object { $_.path.Length } -Descending)
$gitEntries = @(Get-GitStatusEntries -RepoRoot $context.repoRoot)
$mirrorPaths = New-Object System.Collections.Generic.HashSet[string]([System.StringComparer]::OrdinalIgnoreCase)
$canonicalPaths = New-Object System.Collections.Generic.HashSet[string]([System.StringComparer]::OrdinalIgnoreCase)
$results = [ordered]@{
    gate = 'vibe-mirror-edit-hygiene-gate'
    repo_root = $context.repoRoot
    generated_at = (Get-Date).ToString('s')
    gate_result = 'FAIL'
    changed_entries = @($gitEntries)
    mirror_only_edits = @()
    paired_mirror_edits = @()
    reconciled_mirror_edits = @()
    allowlisted_mirror_edits = @()
    summary = [ordered]@{
        changed_paths = $gitEntries.Count
        mirror_only_edits = 0
        paired_mirror_edits = 0
        reconciled_mirror_edits = 0
        allowlisted_mirror_edits = 0
        failures = 0
    }
}

foreach ($entry in $gitEntries) {
    $matchedMirror = $mirrorTargets | Where-Object {
        $_.path -and ($entry.path -eq $_.path -or $entry.path.StartsWith(('{0}/' -f $_.path).Replace('\', '/'), [System.StringComparison]::OrdinalIgnoreCase))
    } | Select-Object -First 1

    if ($null -ne $matchedMirror) {
        [void]$mirrorPaths.Add($entry.path)
        continue
    }

    [void]$canonicalPaths.Add($entry.path)
}

Write-Host '=== VCO Mirror Edit Hygiene Gate ==='
Write-Host ("Repo root : {0}" -f $context.repoRoot)
Write-Host ("Changed   : {0}" -f $gitEntries.Count)
Write-Host ''

foreach ($entry in $gitEntries) {
    $matchedMirror = $mirrorTargets | Where-Object {
        $_.path -and ($entry.path -eq $_.path -or $entry.path.StartsWith(('{0}/' -f $_.path).Replace('\', '/'), [System.StringComparison]::OrdinalIgnoreCase))
    } | Select-Object -First 1

    if ($null -eq $matchedMirror) {
        continue
    }

    $prefix = if ($entry.path -eq $matchedMirror.path) { $matchedMirror.path } else { ('{0}/' -f $matchedMirror.path).Replace('\', '/') }
    $relative = if ($entry.path -eq $matchedMirror.path) { '' } else { $entry.path.Substring($prefix.Length) }
    if ([string]::IsNullOrWhiteSpace($relative)) {
        continue
    }

    $canonicalCounterpart = $relative.Replace('\', '/')
    $classification = [ordered]@{
        target = $matchedMirror.id
        status = $entry.status
        path = $entry.path
        relative_path = $canonicalCounterpart
        canonical_counterpart = $canonicalCounterpart
    }

    $isOptionalNestedRemoval = (
        $matchedMirror.id -eq 'nested_bundled' -and
        $entry.status -eq 'D' -and
        -not [bool]$matchedMirror.required -and
        [string]$matchedMirror.presence_policy -ne 'required'
    )

    if ($isOptionalNestedRemoval) {
        $results.reconciled_mirror_edits += [pscustomobject]$classification
        continue
    }

    if ($allowBundledOnly -contains $canonicalCounterpart) {
        $results.allowlisted_mirror_edits += [pscustomobject]$classification
        continue
    }

    if (-not (Test-GovernedMirrorRelativePath -RelativePath $canonicalCounterpart -Packaging $packaging)) {
        $results.mirror_only_edits += [pscustomobject]$classification
        continue
    }

    $contentMatchesCanonical = $false
    if (-not $canonicalPaths.Contains($canonicalCounterpart)) {
        $contentMatchesCanonical = Test-MirrorMatchesCanonical -RepoRoot $context.repoRoot -MirrorPath $entry.path -CanonicalRelativePath $canonicalCounterpart
    }

    if ($canonicalPaths.Contains($canonicalCounterpart)) {
        $results.paired_mirror_edits += [pscustomobject]$classification
    } elseif ($contentMatchesCanonical) {
        $results.reconciled_mirror_edits += [pscustomobject]$classification
    } else {
        $results.mirror_only_edits += [pscustomobject]$classification
    }
}

$assertions = @()
$assertions += Assert-True -Condition ($results.mirror_only_edits.Count -eq 0) -Message '[hygiene] no mirror-only edits detected under bundled / nested mirrors'
$assertions += Assert-True -Condition ($results.paired_mirror_edits.Count -ge 0) -Message '[hygiene] mirror edit pairing scan completed'

$results.summary.mirror_only_edits = $results.mirror_only_edits.Count
$results.summary.paired_mirror_edits = $results.paired_mirror_edits.Count
$results.summary.reconciled_mirror_edits = $results.reconciled_mirror_edits.Count
$results.summary.allowlisted_mirror_edits = $results.allowlisted_mirror_edits.Count
$results.summary.failures = @($assertions | Where-Object { -not $_ }).Count
$results.gate_result = if ($results.summary.failures -eq 0) { 'PASS' } else { 'FAIL' }

if ($WriteArtifacts) {
    Write-Artifacts -RepoRoot $context.repoRoot -Artifact ([pscustomobject]$results)
}

if ($results.summary.failures -gt 0) {
    exit 1
}
