param(
    [string]$Version = '',
    [string]$Updated = '',
    [switch]$RunGates,
    [switch]$Preview,
    [string]$PreviewOutputPath = ''
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\common\vibe-governance-helpers.ps1')

function Read-Text {
    param([string]$Path)
    return Get-Content -LiteralPath $Path -Raw -Encoding UTF8
}

function Write-Text {
    param(
        [string]$Path,
        [string]$Content
    )
    Write-VgoUtf8NoBomText -Path $Path -Content $Content
}

function Read-Json {
    param([Parameter(Mandatory)] [string]$Path)
    return (Read-Text -Path $Path | ConvertFrom-Json)
}

function Write-Json {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [object]$Payload
    )

    Write-Text -Path $Path -Content ($Payload | ConvertTo-Json -Depth 100)
}

function Update-MaintenanceSection {
    param(
        [string]$Path,
        [string]$Version,
        [string]$Updated
    )

    $text = Read-Text -Path $Path
    $updatedText = $text
    $updatedText = [regex]::Replace($updatedText, '(?m)^- Version:\s*.+$', "- Version: $Version")
    $updatedText = [regex]::Replace($updatedText, '(?m)^- Updated:\s*.+$', "- Updated: $Updated")
    if ($updatedText -ne $text) {
        Write-Text -Path $Path -Content $updatedText
    }
}

function Ensure-ChangelogHeader {
    param(
        [string]$Path,
        [string]$Version,
        [string]$Updated
    )

    $text = Read-Text -Path $Path
    $header = "## v$Version ($Updated)"
    if ($text -match [regex]::Escape($header)) {
        return
    }

    $entry = @(
        $header,
        '',
        '- Release cut by `scripts/governance/release-cut.ps1`.',
        '- Fill in detailed release notes before merge.',
        ''
    ) -join "`n"

    if ($text -match '(?m)^# .+$') {
        $updated = [regex]::Replace($text, '(?m)^(# .+)$', "`$1`n`n$entry", 1)
    } else {
        $updated = "$entry`n$text"
    }
    Write-Text -Path $Path -Content $updated
}

function Get-DistManifestOutputRelativePaths {
    param([Parameter(Mandatory)] [string]$RepoRoot)

    $sourceConfigPath = Join-Path $RepoRoot 'config/distribution-manifest-sources.json'
    if (-not (Test-Path -LiteralPath $sourceConfigPath)) {
        throw "distribution manifest source config missing: $sourceConfigPath"
    }

    $sourceConfig = Read-Json -Path $sourceConfigPath
    $outputs = New-Object System.Collections.Generic.List[string]

    foreach ($item in @($sourceConfig.lane_manifests)) {
        if ($null -ne $item -and $item.PSObject.Properties.Name -contains 'output_path' -and -not [string]::IsNullOrWhiteSpace([string]$item.output_path)) {
            [void]$outputs.Add([string]$item.output_path)
        }
    }

    foreach ($item in @($sourceConfig.public_manifests)) {
        if ($null -ne $item -and $item.PSObject.Properties.Name -contains 'output_path' -and -not [string]::IsNullOrWhiteSpace([string]$item.output_path)) {
            [void]$outputs.Add([string]$item.output_path)
        }
    }

    return @($outputs.ToArray())
}

function Sync-DistManifestOutputs {
    param([Parameter(Mandatory)] [string]$RepoRoot)

    $toolPath = Join-Path $RepoRoot 'scripts/build/sync_dist_release_manifests.py'
    if (-not (Test-Path -LiteralPath $toolPath)) {
        throw "distribution manifest sync tool missing: $toolPath"
    }

    $pythonSpec = Resolve-VgoPythonCommandSpec
    $arguments = @($pythonSpec.prefix_arguments) + @($toolPath, '--repo-root', $RepoRoot)
    & $pythonSpec.host_path @arguments
    if ($LASTEXITCODE -ne 0) {
        throw 'distribution manifest sync failed'
    }
}

function Get-ReleaseSummary {
    param(
        [Parameter(Mandatory)] [psobject]$Governance,
        [Parameter(Mandatory)] [string]$Version
    )

    if ($Governance.PSObject.Properties.Name -contains 'release' -and
        $null -ne $Governance.release -and
        $Governance.release.PSObject.Properties.Name -contains 'notes' -and
        -not [string]::IsNullOrWhiteSpace([string]$Governance.release.notes)) {
        return [string]$Governance.release.notes
    }

    return ("governed release surface for v{0}" -f $Version)
}

function Update-ReleasesReadmeSurface {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [string]$Version,
        [Parameter(Mandatory)] [string]$Updated,
        [Parameter(Mandatory)] [string]$Summary
    )

    $text = Read-Text -Path $Path
    $currentLine = ('- [`v{0}.md`](v{0}.md): {1}' -f $Version, $Summary)
    $recentLine = ('- [`v{0}.md`](v{0}.md) - {1} - {2}' -f $Version, $Updated, $Summary)
    $lines = New-Object System.Collections.Generic.List[string]
    foreach ($line in ([regex]::Split($text, '\r?\n'))) {
        [void]$lines.Add([string]$line)
    }

    $currentHeaderIndex = -1
    $runtimeHeaderIndex = -1
    $recentHeaderIndex = -1
    $olderNotesIndex = -1
    for ($i = 0; $i -lt $lines.Count; $i++) {
        $trimmed = $lines[$i].Trim()
        if ($trimmed -eq '### Current Release Surface' -and $currentHeaderIndex -lt 0) {
            $currentHeaderIndex = $i
            continue
        }
        if ($trimmed -eq '### Release Runtime / Proof Handoff' -and $runtimeHeaderIndex -lt 0) {
            $runtimeHeaderIndex = $i
            continue
        }
        if ($trimmed -eq '## Recent Governed Releases' -and $recentHeaderIndex -lt 0) {
            $recentHeaderIndex = $i
            continue
        }
        if ($trimmed -eq 'Older release notes remain in this directory as historical version records, but they are not part of the active release surface.' -and $olderNotesIndex -lt 0) {
            $olderNotesIndex = $i
        }
    }

    if ($currentHeaderIndex -lt 0 -or $runtimeHeaderIndex -lt 0 -or $runtimeHeaderIndex -le $currentHeaderIndex) {
        throw "unable to locate 'Current Release Surface' section in $Path"
    }

    $currentBodyStart = $currentHeaderIndex + 1
    $currentBodyCount = $runtimeHeaderIndex - $currentBodyStart
    $lines.RemoveRange($currentBodyStart, $currentBodyCount)
    $currentSectionLines = [string[]]@('', $currentLine, '')
    $lines.InsertRange($currentBodyStart, $currentSectionLines)

    if ($recentHeaderIndex -lt 0 -or $olderNotesIndex -lt 0 -or $olderNotesIndex -le $recentHeaderIndex) {
        throw "unable to locate 'Recent Governed Releases' section in $Path"
    }

    $existingRecentLines = @(
        $lines.GetRange($recentHeaderIndex + 1, $olderNotesIndex - ($recentHeaderIndex + 1)) |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    )
    $filteredRecentLines = @(
        $existingRecentLines | Where-Object {
            $_ -notmatch ('^\-\s+\[`v' + [regex]::Escape($Version) + '\.md`\]\(v' + [regex]::Escape($Version) + '\.md\)')
        }
    )
    $lines.RemoveRange($recentHeaderIndex + 1, $olderNotesIndex - ($recentHeaderIndex + 1))
    $recentSectionLines = [string[]](@('', $recentLine) + @($filteredRecentLines) + @(''))
    $lines.InsertRange($recentHeaderIndex + 1, $recentSectionLines)

    Write-Text -Path $Path -Content ($lines -join "`n")
}

function New-ReleaseNoteTemplate {
    param(
        [Parameter(Mandatory)] [string]$Version,
        [Parameter(Mandatory)] [string]$Updated,
        [Parameter(Mandatory)] [string]$Head,
        [Parameter(Mandatory)] [string]$Summary
    )

    return @(
        "# VCO Release v$Version",
        '',
        "- Date: $Updated",
        "- Commit(base): $Head",
        '',
        '## Highlights',
        '',
        ('- Initial governed summary: {0}' -f $Summary),
        '',
        '## Validation Notes',
        '',
        '- Fill in the exact verification commands and outcomes before merge.',
        '',
        '## Migration Notes',
        '',
        '- Record only user-facing behavior, compatibility, or operator migration notes that remain true for this release.'
    ) -join "`n"
}

function Get-ReleaseGateFallbackScripts {
    return @(
        'scripts/verify/vibe-version-consistency-gate.ps1',
        'scripts/verify/vibe-dist-manifest-gate.ps1',
        'scripts/verify/vibe-release-notes-quality-gate.ps1',
        'scripts/verify/vibe-version-packaging-gate.ps1',
        'scripts/verify/vibe-config-parity-gate.ps1',
        'scripts/verify/vibe-nested-bundled-parity-gate.ps1',
        'scripts/verify/vibe-mirror-edit-hygiene-gate.ps1',
        'scripts/verify/vibe-bom-frontmatter-gate.ps1',
        'scripts/verify/vibe-wave40-63-board-gate.ps1',
        'scripts/verify/vibe-capability-dedup-gate.ps1',
        'scripts/verify/vibe-adaptive-routing-readiness-gate.ps1',
        'scripts/verify/vibe-upstream-value-ops-gate.ps1',
        'scripts/verify/vibe-release-install-runtime-coherence-gate.ps1',
        'scripts/verify/vibe-upstream-corpus-manifest-gate.ps1',
        'scripts/verify/vibe-wave121-upstream-mapping-gate.ps1',
        'scripts/verify/vibe-operator-preview-contract-gate.ps1',
        'scripts/verify/vibe-output-fixture-migration-stage2-gate.ps1',
        'scripts/verify/vibe-wave124-ops-cockpit-v2-gate.ps1',
        'scripts/verify/vibe-wave125-gate-family-convergence-gate.ps1',
        'scripts/verify/vibe-upstream-mirror-freshness-gate.ps1',
        'scripts/verify/vibe-docling-contract-gate.ps1',
        'scripts/verify/vibe-connector-admission-gate.ps1',
        'scripts/verify/vibe-role-pack-governance-gate.ps1',
        'scripts/verify/vibe-capability-catalog-gate.ps1',
        'scripts/verify/vibe-promotion-board-gate.ps1',
        'scripts/verify/vibe-pilot-scenarios.ps1',
        'scripts/verify/vibe-deep-extraction-pilot-gate.ps1',
        'scripts/verify/vibe-memory-runtime-v3-gate.ps1',
        'scripts/verify/vibe-mem0-softrollout-gate.ps1',
        'scripts/verify/vibe-letta-policy-conformance-gate.ps1',
        'scripts/verify/vibe-browserops-scorecard-gate.ps1',
        'scripts/verify/vibe-browserops-softrollout-gate.ps1',
        'scripts/verify/vibe-desktopops-replay-gate.ps1',
        'scripts/verify/vibe-desktopops-softrollout-gate.ps1',
        'scripts/verify/vibe-docling-contract-v2-gate.ps1',
        'scripts/verify/vibe-connector-scorecard-gate.ps1',
        'scripts/verify/vibe-connector-action-ledger-gate.ps1',
        'scripts/verify/vibe-prompt-intelligence-productization-gate.ps1',
        'scripts/verify/vibe-cross-plane-task-contract-gate.ps1',
        'scripts/verify/vibe-cross-plane-replay-gate.ps1',
        'scripts/verify/vibe-promotion-scorecard-gate.ps1',
        'scripts/verify/vibe-ops-cockpit-gate.ps1',
        'scripts/verify/vibe-rollback-drill-gate.ps1',
        'scripts/verify/vibe-release-train-v2-gate.ps1',
        'scripts/verify/vibe-release-truth-consistency-gate.ps1',
        'scripts/verify/vibe-wave64-82-closure-gate.ps1',
        'scripts/verify/vibe-gate-reliability-gate.ps1',
        'scripts/verify/vibe-memory-quality-eval-gate.ps1',
        'scripts/verify/vibe-openworld-runtime-eval-gate.ps1',
        'scripts/verify/vibe-document-failure-taxonomy-gate.ps1',
        'scripts/verify/vibe-prompt-intelligence-eval-gate.ps1',
        'scripts/verify/vibe-candidate-quality-board-gate.ps1',
        'scripts/verify/vibe-role-pack-v2-gate.ps1',
        'scripts/verify/vibe-subagent-handoff-gate.ps1',
        'scripts/verify/vibe-discovery-intake-scorecard-gate.ps1',
        'scripts/verify/vibe-capability-lifecycle-gate.ps1',
        'scripts/verify/vibe-connector-sandbox-simulation-gate.ps1',
        'scripts/verify/vibe-skill-harvest-v2-gate.ps1',
        'scripts/verify/vibe-ops-dashboard-gate.ps1',
        'scripts/verify/vibe-release-evidence-bundle-gate.ps1',
        'scripts/verify/vibe-manual-apply-policy-gate.ps1',
        'scripts/verify/vibe-rollout-proposal-boundedness-gate.ps1',
        'scripts/verify/vibe-upstream-reaudit-matrix-gate.ps1',
        'scripts/verify/vibe-wave83-100-closure-gate.ps1'
    )
}

function Get-ReleaseGateScriptsFromContract {
    param([psobject]$PreviewContract)

    if ($null -ne $PreviewContract -and
        $PreviewContract.PSObject.Properties.Name -contains 'operators' -and
        $null -ne $PreviewContract.operators) {
        $operators = $PreviewContract.operators
        $releaseCutOperator = $null
        if ($operators -is [System.Collections.IDictionary]) {
            if ($operators.Contains('release-cut')) {
                $releaseCutOperator = $operators['release-cut']
            }
        } elseif ($null -ne $operators.PSObject -and $operators.PSObject.Properties.Name -contains 'release-cut') {
            $releaseCutOperator = $operators.'release-cut'
        }

        if ($null -ne $releaseCutOperator -and
            $releaseCutOperator.PSObject.Properties.Name -contains 'apply_gates' -and
            $null -ne $releaseCutOperator.apply_gates) {
            $applyGates = @($releaseCutOperator.apply_gates | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) })
            if ($applyGates.Count -gt 0) {
                return @($applyGates)
            }
        }
    }

    return @(Get-ReleaseGateFallbackScripts)
}

function Get-ReleasePostcheckScriptsFromContract {
    param(
        [psobject]$PreviewContract,
        [string[]]$FallbackScripts = @()
    )

    if ($null -ne $PreviewContract -and
        $PreviewContract.PSObject.Properties.Name -contains 'operators' -and
        $null -ne $PreviewContract.operators) {
        $operators = $PreviewContract.operators
        $releaseCutOperator = $null
        if ($operators -is [System.Collections.IDictionary]) {
            if ($operators.Contains('release-cut')) {
                $releaseCutOperator = $operators['release-cut']
            }
        } elseif ($null -ne $operators.PSObject -and $operators.PSObject.Properties.Name -contains 'release-cut') {
            $releaseCutOperator = $operators.'release-cut'
        }

        if ($null -ne $releaseCutOperator -and
            $releaseCutOperator.PSObject.Properties.Name -contains 'postcheck_gates' -and
            $null -ne $releaseCutOperator.postcheck_gates) {
            $postcheckGates = @($releaseCutOperator.postcheck_gates | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) })
            if ($postcheckGates.Count -gt 0) {
                return @($postcheckGates)
            }
        }
    }

    if ($FallbackScripts.Count -gt 0) {
        return @($FallbackScripts)
    }

    return @(Get-ReleaseGateFallbackScripts)
}

function Get-PreviewReceiptPath {
    param(
        [string]$RepoRoot,
        [string]$RequestedPath,
        [psobject]$Contract
    )

    if (-not [string]::IsNullOrWhiteSpace($RequestedPath)) {
        return $RequestedPath
    }

    $root = if ($null -ne $Contract -and $Contract.PSObject.Properties.Name -contains 'preview_output_root') {
        [string]$Contract.preview_output_root
    } else {
        'outputs/governance/preview'
    }
    return Join-Path $RepoRoot (Join-Path $root 'release-cut.json')
}

function Invoke-ReleaseGate {
    param(
        [Parameter(Mandatory)] [string]$GatePath
    )

    $gateScript = Get-Content -LiteralPath $GatePath -Raw -Encoding UTF8
    $supportsWriteArtifacts = $gateScript -match '(?is)\bparam\s*\(.*?\[switch\]\s*\$WriteArtifacts\b'
    if ($supportsWriteArtifacts) {
        & $GatePath -WriteArtifacts
    } else {
        & $GatePath
    }
}

$context = Get-VgoGovernanceContext -ScriptPath $PSCommandPath -EnforceExecutionContext
$repoRoot = $context.repoRoot
$governancePath = $context.governancePath
$governance = $context.governance

$previewContractPath = Join-Path $repoRoot 'config/operator-preview-contract.json'
$previewContract = if (Test-Path -LiteralPath $previewContractPath) {
    Get-Content -LiteralPath $previewContractPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}

if ([string]::IsNullOrWhiteSpace($Version)) {
    $Version = [string]$governance.release.version
}
if ([string]::IsNullOrWhiteSpace($Updated)) {
    $Updated = (Get-Date -Format 'yyyy-MM-dd')
}

$maintenanceFiles = @($governance.version_markers.maintenance_files)
$changelogPath = Join-Path $repoRoot ([string]$governance.version_markers.changelog_path)
$ledgerRel = [string]$governance.logs.release_ledger_jsonl
$ledgerPath = Join-Path $repoRoot $ledgerRel
$releaseNotesDir = Join-Path $repoRoot ([string]$governance.logs.release_notes_dir)
$releaseNotePath = Join-Path $releaseNotesDir ("v{0}.md" -f $Version)
$releaseReadmeRel = 'docs/releases/README.md'
$releaseReadmePath = Join-Path $repoRoot $releaseReadmeRel
$distManifestRels = @(Get-DistManifestOutputRelativePaths -RepoRoot $repoRoot)
$releaseSummary = Get-ReleaseSummary -Governance $governance -Version $Version
$syncScript = Join-Path $repoRoot 'scripts\governance\sync-bundled-vibe.ps1'
$applyGateScripts = if ($RunGates) { Get-ReleaseGateScriptsFromContract -PreviewContract $previewContract } else { @() }
$postcheckGateScripts = if ($RunGates) { Get-ReleasePostcheckScriptsFromContract -PreviewContract $previewContract -FallbackScripts $applyGateScripts } else { @() }
$head = (git -C $repoRoot rev-parse --short HEAD).Trim()

if ($Preview) {
    $previewPath = Get-PreviewReceiptPath -RepoRoot $repoRoot -RequestedPath $PreviewOutputPath -Contract $previewContract
    $previewRoot = Split-Path -Parent $previewPath
    $plannedFileActions = @(
        [ordered]@{ path = 'config/version-governance.json'; action = 'update release.version + release.updated' },
        [ordered]@{ path = [string]$governance.version_markers.changelog_path; action = 'ensure release changelog header' },
        [ordered]@{ path = $ledgerRel; action = 'append release ledger record' },
        [ordered]@{ path = (Get-VgoRelativePathPortable -BasePath $repoRoot -TargetPath $releaseNotePath); action = 'create release notes if missing with governed section skeleton' },
        [ordered]@{ path = $releaseReadmeRel; action = 'update current release surface and recent governed releases entry' }
    ) + @($maintenanceFiles | ForEach-Object {
        [ordered]@{ path = [string]$_; action = 'update maintenance section version/updated' }
    }) + @($distManifestRels | ForEach-Object {
        [ordered]@{ path = [string]$_; action = 'sync generated dist manifest from authoritative source config' }
    })

    $syncPreviewPath = Join-Path $previewRoot 'sync-bundled-vibe-from-release-cut.json'
    if (Test-Path -LiteralPath $syncScript) {
        # operator-preview contract requires sync-bundled-vibe.ps1 -Preview before apply.
        & $syncScript -Preview -PreviewOutputPath $syncPreviewPath -PruneBundledExtras
        if ($LASTEXITCODE -ne 0) {
            throw 'sync-bundled-vibe preview failed'
        }
    }

    $artifact = [ordered]@{
        operator = 'release-cut'
        contract_version = if ($null -ne $previewContract -and $previewContract.PSObject.Properties.Name -contains 'contract_version') { $previewContract.contract_version } else { 1 }
        mode = 'preview'
        precheck = [ordered]@{
            repo_root = $repoRoot
            canonical_target_id = $context.canonicalTarget.id
            sync_source_target_id = $context.syncSourceTarget.id
            current_version = [string]$governance.release.version
            requested_version = $Version
            requested_updated = $Updated
            git_head = $head
            run_gates = [bool]$RunGates
        }
        preview = [ordered]@{
            generated_at = (Get-Date).ToString('s')
            planned_file_actions = $plannedFileActions
            sync_preview_receipt = if (Test-Path -LiteralPath $syncPreviewPath) { (Get-VgoRelativePathPortable -BasePath $repoRoot -TargetPath $syncPreviewPath) } else { $null }
            planned_gates = $applyGateScripts
        }
        postcheck = [ordered]@{
            verify_after_apply = $postcheckGateScripts
        }
    }
    Write-VgoUtf8NoBomText -Path $previewPath -Content ($artifact | ConvertTo-Json -Depth 100)
    Write-Host ("Preview receipt written: {0}" -f $previewPath) -ForegroundColor Yellow
    return
}

$governance.release.version = $Version
$governance.release.updated = $Updated
$governanceJson = $governance | ConvertTo-Json -Depth 30
Write-Text -Path $governancePath -Content $governanceJson

foreach ($rel in $maintenanceFiles) {
    $path = Join-Path $repoRoot $rel
    if (-not (Test-Path -LiteralPath $path)) {
        throw "maintenance file missing: $rel"
    }
    Update-MaintenanceSection -Path $path -Version $Version -Updated $Updated
}

Ensure-ChangelogHeader -Path $changelogPath -Version $Version -Updated $Updated

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $ledgerPath) | Out-Null
$entry = [ordered]@{
    recorded_at = (Get-Date).ToString('s')
    version = $Version
    updated = $Updated
    git_head = $head
    actor = $env:USERNAME
}

# Pre-write duplicate check: only append if (version, git_head) combination doesn't exist
$shouldAppend = $true
if (Test-Path -LiteralPath $ledgerPath) {
    $existingLines = Get-Content -LiteralPath $ledgerPath -Encoding UTF8
    foreach ($line in $existingLines) {
        if (-not [string]::IsNullOrWhiteSpace($line)) {
            $existingEntry = $line | ConvertFrom-Json
            if ($existingEntry.version -eq $Version -and $existingEntry.git_head -eq $head) {
                $shouldAppend = $false
                Write-Host ("Skipping duplicate ledger entry: version={0}, git_head={1} already recorded at {2}" -f $Version, $head, $existingEntry.recorded_at) -ForegroundColor Yellow
                break
            }
        }
    }
}

if ($shouldAppend) {
    $separator = ''
    if (Test-Path -LiteralPath $ledgerPath) {
        $existingLedgerText = Read-Text -Path $ledgerPath
        if (-not [string]::IsNullOrEmpty($existingLedgerText) -and
            -not ($existingLedgerText.EndsWith("`n") -or $existingLedgerText.EndsWith("`r"))) {
            $separator = [Environment]::NewLine
        }
    }
    Append-VgoUtf8NoBomText -Path $ledgerPath -Content ($separator + (($entry | ConvertTo-Json -Compress) + [Environment]::NewLine))
}

New-Item -ItemType Directory -Force -Path $releaseNotesDir | Out-Null
if (-not (Test-Path -LiteralPath $releaseNotePath)) {
    $note = New-ReleaseNoteTemplate -Version $Version -Updated $Updated -Head $head -Summary $releaseSummary
    Write-Text -Path $releaseNotePath -Content $note
}

if (Test-Path -LiteralPath $releaseReadmePath) {
    Update-ReleasesReadmeSurface -Path $releaseReadmePath -Version $Version -Updated $Updated -Summary $releaseSummary
}

if (Test-Path -LiteralPath $syncScript) {
    & $syncScript -PruneBundledExtras
    if ($LASTEXITCODE -ne 0) {
        throw 'sync-bundled-vibe failed'
    }
}

Sync-DistManifestOutputs -RepoRoot $repoRoot

if ($RunGates) {
    foreach ($rel in $applyGateScripts) {
        $gatePath = Join-Path $repoRoot $rel
        if (-not (Test-Path -LiteralPath $gatePath)) {
            throw "required gate script missing: $rel"
        }
        Invoke-ReleaseGate -GatePath $gatePath
        if ($LASTEXITCODE -ne 0) {
            throw "gate failed: $rel"
        }
    }
}

Write-Host 'Release cut complete.' -ForegroundColor Green
Write-Host ("version={0}, updated={1}" -f $Version, $Updated)
