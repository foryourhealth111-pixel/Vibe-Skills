param(
    [ValidateSet('All', 'Stability', 'Usability', 'Intelligence')]
    [string]$Mode = 'All',
    [switch]$WriteArtifacts,
    [string]$OutputDirectory = ''
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\common\vibe-governance-helpers.ps1')
. (Join-Path $PSScriptRoot '..\common\ProtectedDocumentCleanup.ps1')

function Add-Assertion {
    param(
        [System.Collections.Generic.List[object]]$Assertions,
        [bool]$Pass,
        [string]$Message,
        [object]$Details = $null,
        [string]$Family = 'stability'
    )

    $Assertions.Add([pscustomobject]@{
            family = $Family
            pass = [bool]$Pass
            message = $Message
            details = $Details
        }) | Out-Null

    $status = if ($Pass) { 'PASS' } else { 'FAIL' }
    Write-Host ('[{0}] [{1}] {2}' -f $status, $Family, $Message) -ForegroundColor $(if ($Pass) { 'Green' } else { 'Red' })
}

function Write-GateArtifacts {
    param(
        [string]$RepoRoot,
        [string]$OutputDirectory,
        [psobject]$Artifact
    )

    $dir = if ([string]::IsNullOrWhiteSpace($OutputDirectory)) { Join-Path $RepoRoot 'outputs\verify' } else { $OutputDirectory }
    New-Item -ItemType Directory -Force -Path $dir | Out-Null

    $jsonPath = Join-Path $dir 'vibe-document-asset-safety-gate.json'
    $mdPath = Join-Path $dir 'vibe-document-asset-safety-gate.md'
    Write-VgoUtf8NoBomText -Path $jsonPath -Content ($Artifact | ConvertTo-Json -Depth 100)

    $lines = @(
        '# VCO Document Asset Safety Gate',
        '',
        ('- Gate Result: **{0}**' -f $Artifact.gate_result),
        ('- Repo Root: `{0}`' -f $Artifact.repo_root),
        ('- Mode: `{0}`' -f $Artifact.mode),
        ('- Failure Count: {0}' -f $Artifact.summary.failure_count),
        '',
        '## Assertions',
        ''
    )
    foreach ($assertion in $Artifact.assertions) {
        $lines += ('- `{0}` `{1}` {2}' -f $(if ($assertion.pass) { 'PASS' } else { 'FAIL' }), $assertion.family, $assertion.message)
    }
    Write-VgoUtf8NoBomText -Path $mdPath -Content ($lines -join "`n")
}

function Copy-ScenarioTree {
    param(
        [Parameter(Mandatory)] [string]$SourceRoot,
        [Parameter(Mandatory)] [string]$DestinationRoot
    )

    New-Item -ItemType Directory -Force -Path $DestinationRoot | Out-Null
    foreach ($entry in @(Get-ChildItem -LiteralPath $SourceRoot -Force)) {
        Copy-Item -LiteralPath $entry.FullName -Destination $DestinationRoot -Recurse -Force
    }
}

$context = Get-VgoGovernanceContext -ScriptPath $PSCommandPath -EnforceExecutionContext
$repoRoot = $context.repoRoot
$policy = Get-VgoProtectedDocumentCleanupPolicy -RepoRoot $repoRoot
$extensions = Get-VgoProtectedDocumentExtensions -Policy $policy
$assertions = [System.Collections.Generic.List[object]]::new()
$fixturesRoot = Join-Path $repoRoot 'scripts\verify\fixtures\document-cleanup-safety'
$requiredPaths = @(
    'scripts/common/ProtectedDocumentCleanup.ps1',
    'scripts/governance/phase-end-cleanup.ps1',
    'config/phase-cleanup-policy.json',
    'docs/document-asset-cleanup-governance.md',
    'scripts/verify/fixtures/document-cleanup-safety'
)

foreach ($relPath in $requiredPaths) {
    Add-Assertion -Assertions $assertions -Pass (Test-Path -LiteralPath (Join-Path $repoRoot $relPath)) -Message ("required asset exists: {0}" -f $relPath) -Family 'stability'
}

$policyRaw = Get-Content -LiteralPath (Join-Path $repoRoot 'config\phase-cleanup-policy.json') -Raw -Encoding UTF8
$cleanupRaw = Get-Content -LiteralPath (Join-Path $repoRoot 'scripts\governance\phase-end-cleanup.ps1') -Raw -Encoding UTF8
$governanceRaw = Get-Content -LiteralPath (Join-Path $repoRoot 'docs\document-asset-cleanup-governance.md') -Raw -Encoding UTF8

Add-Assertion -Assertions $assertions -Pass ($policyRaw.Contains('"preview_only"')) -Message 'cleanup policy declares preview_only mode' -Family 'usability'
Add-Assertion -Assertions $assertions -Pass ($policyRaw.Contains('"quarantine_only"')) -Message 'cleanup policy declares quarantine_only mode' -Family 'stability'
Add-Assertion -Assertions $assertions -Pass ($cleanupRaw.Contains('PreviewOnly')) -Message 'cleanup script exposes PreviewOnly execution path' -Family 'usability'
Add-Assertion -Assertions $assertions -Pass ($cleanupRaw.Contains('Move-VgoProtectedDocumentsToQuarantine')) -Message 'cleanup script uses quarantine handling for protected tmp documents' -Family 'stability'
Add-Assertion -Assertions $assertions -Pass ($governanceRaw.Contains('No Fuzzy Destructive Cleanup')) -Message 'governance doc forbids fuzzy destructive cleanup' -Family 'intelligence'

$scenarioDirs = @(Get-ChildItem -LiteralPath $fixturesRoot -Directory | Sort-Object Name)
Add-Assertion -Assertions $assertions -Pass ($scenarioDirs.Count -ge 3) -Message 'document cleanup fixture family count is at least 3' -Family 'stability'

foreach ($scenario in $scenarioDirs) {
    $metadataPath = Join-Path $scenario.FullName 'metadata.json'
    $sourceRoot = Join-Path $scenario.FullName 'source'
    if (-not (Test-Path -LiteralPath $metadataPath) -or -not (Test-Path -LiteralPath $sourceRoot)) {
        Add-Assertion -Assertions $assertions -Pass $false -Message ("scenario incomplete: {0}" -f $scenario.Name) -Family 'stability'
        continue
    }

    $metadata = Get-Content -LiteralPath $metadataPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $sandboxRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("vgo-doc-safety-" + [Guid]::NewGuid().ToString('N'))
    try {
        Copy-ScenarioTree -SourceRoot $sourceRoot -DestinationRoot $sandboxRoot
        $tmpRoot = Join-Path $sandboxRoot '.tmp'
        $manifest = Get-VgoProtectedDocumentManifest -RepoRoot $sandboxRoot -Policy $policy -TmpRoot $tmpRoot

        Add-Assertion -Assertions $assertions -Pass ($manifest.summary.tmp_protected_total -eq [int]$metadata.expected_tmp_protected) -Message ("scenario {0} tmp protected count matches" -f $scenario.Name) -Details $manifest.summary.tmp_protected_total -Family 'intelligence'
        Add-Assertion -Assertions $assertions -Pass ($manifest.summary.retained_outside_tmp_total -eq [int]$metadata.expected_retained_outside_tmp) -Message ("scenario {0} retained protected count matches" -f $scenario.Name) -Details $manifest.summary.retained_outside_tmp_total -Family 'usability'

        $quarantineRoot = Join-Path $sandboxRoot 'quarantine'
        $quarantined = @(
            Move-VgoProtectedDocumentsToQuarantine -TmpRoot $tmpRoot -QuarantineRoot $quarantineRoot -Extensions $extensions |
                Where-Object {
                    $null -ne $_ -and $_ -ne [System.Management.Automation.Internal.AutomationNull]::Value
                }
        )
        if (Test-Path -LiteralPath $tmpRoot) {
            Remove-Item -LiteralPath $tmpRoot -Recurse -Force
        }

        Add-Assertion -Assertions $assertions -Pass ($quarantined.Count -eq [int]$metadata.expected_quarantined) -Message ("scenario {0} quarantined count matches" -f $scenario.Name) -Details $quarantined.Count -Family 'stability'
        $postChecks = @(Test-VgoProtectedDocumentPostConditions -Manifest $manifest -QuarantinedItems $quarantined)
        foreach ($postCheck in $postChecks) {
            Add-Assertion -Assertions $assertions -Pass ([bool]$postCheck.pass) -Message ("scenario {0} {1}" -f $scenario.Name, $postCheck.message) -Details $postCheck.path -Family 'stability'
        }

        $quarantinedPaths = @($quarantined | ForEach-Object { $_.relative_path })
        Add-Assertion -Assertions $assertions -Pass (($quarantinedPaths.Count -eq 0) -or ($quarantinedPaths | Where-Object { $_ -like '*.docx' -or $_ -like '*.xlsx' -or $_ -like '*.pptx' -or $_ -like '*.pdf' }).Count -eq $quarantinedPaths.Count) -Message ("scenario {0} quarantine set remains document-only" -f $scenario.Name) -Details $quarantinedPaths -Family 'intelligence'
    } finally {
        if (Test-Path -LiteralPath $sandboxRoot) {
            Remove-Item -LiteralPath $sandboxRoot -Recurse -Force
        }
    }
}

$filteredAssertions = switch ($Mode) {
    'Stability' { @($assertions | Where-Object { $_.family -eq 'stability' }) }
    'Usability' { @($assertions | Where-Object { $_.family -eq 'usability' }) }
    'Intelligence' { @($assertions | Where-Object { $_.family -eq 'intelligence' }) }
    default { @($assertions) }
}

$failureCount = @($filteredAssertions | Where-Object { -not $_.pass }).Count
$gateResult = if ($failureCount -eq 0) { 'PASS' } else { 'FAIL' }
$artifact = [pscustomobject]@{
    gate = 'vibe-document-asset-safety-gate'
    repo_root = $repoRoot
    mode = $Mode
    generated_at = (Get-Date).ToString('s')
    gate_result = $gateResult
    assertions = @($filteredAssertions)
    summary = [ordered]@{
        total = @($filteredAssertions).Count
        failure_count = $failureCount
    }
}

if ($WriteArtifacts) {
    Write-GateArtifacts -RepoRoot $repoRoot -OutputDirectory $OutputDirectory -Artifact $artifact
}

if ($failureCount -gt 0) {
    exit 1
}
