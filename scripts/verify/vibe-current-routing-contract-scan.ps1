param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path,
    [switch]$Json
)

$ErrorActionPreference = 'Stop'

function Get-TextFileLines {
    param([Parameter(Mandatory)] [string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        return @()
    }
    return Get-Content -LiteralPath $Path -Encoding UTF8
}

function New-Finding {
    param(
        [Parameter(Mandatory)] [string]$Category,
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [int]$Line,
        [Parameter(Mandatory)] [string]$Pattern,
        [Parameter(Mandatory)] [string]$Text
    )
    [pscustomobject]@{
        category = $Category
        path = $Path
        line = $Line
        pattern = $Pattern
        text = $Text.Trim()
    }
}

$currentSurfaceFiles = @(
    'SKILL.md',
    'README.md',
    'docs/governance/current-routing-contract.md',
    'docs/governance/README.md',
    'scripts/runtime/Write-RequirementDoc.ps1',
    'scripts/runtime/Write-XlPlan.ps1',
    'scripts/runtime/invoke-vibe-runtime.ps1'
)

$currentRuntimeFiles = @(
    'scripts/runtime/VibeSkillRouting.Common.ps1',
    'scripts/runtime/VibeRuntime.Common.ps1',
    'scripts/runtime/Write-RequirementDoc.ps1',
    'scripts/runtime/Write-XlPlan.ps1',
    'scripts/runtime/invoke-vibe-runtime.ps1'
)

$legacyAllowedFiles = @(
    'tests/runtime_neutral/test_active_consultation_simplification.py'
)

$historicalRoots = @(
    'docs/superpowers/plans/',
    'docs/superpowers/specs/'
)

$activeForbiddenPatterns = @(
    'route owner',
    'primary skill',
    'secondary skill',
    'consultation expert',
    'auxiliary expert',
    'approved consultation',
    'consulted units'
)

$oldFormatFallbackPatterns = @(
    'legacy_skill_routing',
    'specialist_recommendations',
    'stage_assistant_hints',
    '## Specialist Consultation',
    'DiscussionConsultationPath',
    'PlanningConsultationPath'
)

$allowedCurrentExecutionPhrases = @(
    'derived_from_module_assignments',
    'source = ''module_assignments.units[*].bound_skill''',
    'no_specialist_recommendations'
)

function Test-CurrentRoutingEntrypointGuidance {
    param([Parameter(Mandatory)] [string]$RepoRoot)

    $guidanceFindings = New-Object System.Collections.Generic.List[object]
    $currentRoutingPath = Join-Path $RepoRoot 'docs/governance/current-routing-contract.md'
    $governanceReadmePath = Join-Path $RepoRoot 'docs/governance/README.md'

    $currentRoutingText = if (Test-Path -LiteralPath $currentRoutingPath) {
        Get-Content -LiteralPath $currentRoutingPath -Raw -Encoding UTF8
    } else {
        ''
    }
    if ([string]::IsNullOrWhiteSpace($currentRoutingText) -or $currentRoutingText.IndexOf('current-runtime-field-contract.md', [System.StringComparison]::OrdinalIgnoreCase) -lt 0) {
        $guidanceFindings.Add((New-Finding -Category 'current_entrypoint_guidance_violation' -Path 'docs/governance/current-routing-contract.md' -Line 1 -Pattern 'current-runtime-field-contract.md' -Text 'current routing contract must redirect readers to current runtime field contract first')) | Out-Null
    }
    if ([string]::IsNullOrWhiteSpace($currentRoutingText) -or $currentRoutingText.IndexOf('compatibility', [System.StringComparison]::OrdinalIgnoreCase) -lt 0) {
        $guidanceFindings.Add((New-Finding -Category 'current_entrypoint_guidance_violation' -Path 'docs/governance/current-routing-contract.md' -Line 1 -Pattern 'compatibility' -Text 'current routing contract must describe itself as a compatibility surface')) | Out-Null
    }

    $governanceReadmeText = if (Test-Path -LiteralPath $governanceReadmePath) {
        Get-Content -LiteralPath $governanceReadmePath -Raw -Encoding UTF8
    } else {
        ''
    }
    $runtimeFieldIndex = $governanceReadmeText.IndexOf('[`current-runtime-field-contract.md`](current-runtime-field-contract.md)', [System.StringComparison]::OrdinalIgnoreCase)
    $routingIndex = $governanceReadmeText.IndexOf('[`current-routing-contract.md`](current-routing-contract.md)', [System.StringComparison]::OrdinalIgnoreCase)
    if ($runtimeFieldIndex -lt 0 -or $routingIndex -lt 0 -or $runtimeFieldIndex -ge $routingIndex) {
        $guidanceFindings.Add((New-Finding -Category 'current_entrypoint_guidance_violation' -Path 'docs/governance/README.md' -Line 1 -Pattern 'current-runtime-field-contract-first' -Text 'governance README must point to current runtime field contract before current routing contract')) | Out-Null
    }

    return [object[]]$guidanceFindings.ToArray()
}

$findings = New-Object System.Collections.Generic.List[object]
$entrypointGuidanceFindings = @(Test-CurrentRoutingEntrypointGuidance -RepoRoot $RepoRoot)
foreach ($finding in $entrypointGuidanceFindings) {
    $findings.Add($finding) | Out-Null
}

foreach ($relative in $currentSurfaceFiles) {
    $fullPath = Join-Path $RepoRoot $relative
    $lines = @(Get-TextFileLines -Path $fullPath)
    for ($index = 0; $index -lt $lines.Count; $index++) {
        $lineText = [string]$lines[$index]
        foreach ($pattern in $activeForbiddenPatterns) {
            if ($lineText.IndexOf($pattern, [System.StringComparison]::OrdinalIgnoreCase) -ge 0) {
                $isLegacyLine = (
                    $lineText.IndexOf('legacy', [System.StringComparison]::OrdinalIgnoreCase) -ge 0 -or
                    $lineText.IndexOf('old artifact', [System.StringComparison]::OrdinalIgnoreCase) -ge 0 -or
                    $lineText.IndexOf('compatibility', [System.StringComparison]::OrdinalIgnoreCase) -ge 0
                )
                if (-not $isLegacyLine) {
                    $findings.Add((New-Finding -Category 'current_surface_violation' -Path $relative -Line ($index + 1) -Pattern $pattern -Text $lineText)) | Out-Null
                }
            }
        }
    }
}

foreach ($relative in $currentRuntimeFiles) {
    $fullPath = Join-Path $RepoRoot $relative
    $lines = @(Get-TextFileLines -Path $fullPath)
    for ($index = 0; $index -lt $lines.Count; $index++) {
        $lineText = [string]$lines[$index]
        foreach ($pattern in $oldFormatFallbackPatterns) {
            if ($lineText.IndexOf($pattern, [System.StringComparison]::OrdinalIgnoreCase) -lt 0) {
                continue
            }

            $allowed = $false
            foreach ($allowedPhrase in $allowedCurrentExecutionPhrases) {
                if ($lineText.IndexOf($allowedPhrase, [System.StringComparison]::OrdinalIgnoreCase) -ge 0) {
                    $allowed = $true
                    break
                }
            }
            if (-not $allowed) {
                $findings.Add((New-Finding -Category 'current_runtime_old_format_fallback' -Path $relative -Line ($index + 1) -Pattern $pattern -Text $lineText)) | Out-Null
            }
        }
    }
}

$legacyReferenceCount = 0
foreach ($relative in $legacyAllowedFiles) {
    $fullPath = Join-Path $RepoRoot $relative
    foreach ($line in @(Get-TextFileLines -Path $fullPath)) {
        if ($line -match 'consultation|stage_assistant|approved_consultation|consulted_units') {
            $legacyReferenceCount += 1
        }
    }
}

$historicalReferenceCount = 0
foreach ($root in $historicalRoots) {
    $fullRoot = Join-Path $RepoRoot $root
    if (-not (Test-Path -LiteralPath $fullRoot)) {
        continue
    }
    foreach ($file in Get-ChildItem -LiteralPath $fullRoot -Recurse -File -Include *.md) {
        foreach ($line in @(Get-Content -LiteralPath $file.FullName -Encoding UTF8)) {
            if ($line -match 'consultation|stage assistant|route owner|primary skill|secondary skill') {
                $historicalReferenceCount += 1
            }
        }
    }
}

$hardCleanupScript = Join-Path $RepoRoot 'scripts\verify\vibe-routing-terminology-hard-cleanup-scan.ps1'
$hardCleanup = $null
if (Test-Path -LiteralPath $hardCleanupScript) {
    $hardJson = & $hardCleanupScript -RepoRoot $RepoRoot -Json
    $hardCleanup = ($hardJson -join "`n") | ConvertFrom-Json
}

function Get-HardCleanupCount {
    param(
        [object]$Payload,
        [Parameter(Mandatory)] [string]$Name
    )
    if (-not $Payload) {
        return 0
    }
    if ($Payload.PSObject.Properties.Name -contains $Name) {
        return [int]$Payload.$Name
    }
    if ($Payload.PSObject.Properties.Name -contains 'summary' -and $Payload.summary.PSObject.Properties.Name -contains $Name) {
        return [int]$Payload.summary.$Name
    }
    return 0
}

$summary = [pscustomobject]@{
    current_entrypoint_guidance_violation_count = @($findings | Where-Object { $_.category -eq 'current_entrypoint_guidance_violation' }).Count
    current_surface_violation_count = @($findings | Where-Object { $_.category -eq 'current_surface_violation' }).Count
    current_runtime_old_format_fallback_count = @($findings | Where-Object { $_.category -eq 'current_runtime_old_format_fallback' }).Count
    retired_old_format_reference_count = [int]$legacyReferenceCount
    historical_reference_count = [int]$historicalReferenceCount
    hard_cleanup_current_doc_retired_term_violation_count = Get-HardCleanupCount -Payload $hardCleanup -Name 'current_doc_retired_term_violation_count'
    hard_cleanup_current_behavior_test_retired_field_read_count = Get-HardCleanupCount -Payload $hardCleanup -Name 'current_behavior_test_retired_field_read_count'
    hard_cleanup_historical_doc_retired_term_file_count = Get-HardCleanupCount -Payload $hardCleanup -Name 'historical_doc_retired_term_file_count'
    hard_cleanup_historical_doc_marked_retired_term_count = Get-HardCleanupCount -Payload $hardCleanup -Name 'historical_doc_marked_retired_term_count'
    hard_cleanup_historical_doc_unmarked_retired_term_count = Get-HardCleanupCount -Payload $hardCleanup -Name 'historical_doc_unmarked_retired_term_count'
    hard_cleanup_execution_internal_specialist_dispatch_reference_count = Get-HardCleanupCount -Payload $hardCleanup -Name 'execution_internal_specialist_dispatch_reference_count'
    hard_cleanup_current_policy_helper_dispatch_vocabulary_reference_count = Get-HardCleanupCount -Payload $hardCleanup -Name 'current_policy_helper_dispatch_vocabulary_reference_count'
    hard_cleanup_fail_count = Get-HardCleanupCount -Payload $hardCleanup -Name 'fail_count'
    hard_cleanup_review_count = Get-HardCleanupCount -Payload $hardCleanup -Name 'review_count'
    findings = [object[]]$findings.ToArray()
}

$hardCleanupBlockingViolationCount = [int]$summary.hard_cleanup_fail_count
if ($hardCleanupBlockingViolationCount -eq 0) {
    $hardCleanupBlockingViolationCount = (
        [int]$summary.hard_cleanup_current_doc_retired_term_violation_count +
        [int]$summary.hard_cleanup_current_behavior_test_retired_field_read_count +
        [int]$summary.hard_cleanup_current_policy_helper_dispatch_vocabulary_reference_count
    )
    $summary.hard_cleanup_fail_count = $hardCleanupBlockingViolationCount
}

if ($Json) {
    $summary | ConvertTo-Json -Depth 20
} else {
    '=== VCO Current Routing Contract Scan ==='
    ('Current entrypoint guidance violations: {0}' -f [int]$summary.current_entrypoint_guidance_violation_count)
    ('Current surface violations: {0}' -f [int]$summary.current_surface_violation_count)
    ('Current runtime old-format fallbacks: {0}' -f [int]$summary.current_runtime_old_format_fallback_count)
    ('Retired old-format references: {0}' -f [int]$summary.retired_old_format_reference_count)
    ('Historical doc references: {0}' -f [int]$summary.historical_reference_count)
    ('Hard cleanup current docs retired-term violations: {0}' -f [int]$summary.hard_cleanup_current_doc_retired_term_violation_count)
    ('Hard cleanup current behavior test retired-field reads: {0}' -f [int]$summary.hard_cleanup_current_behavior_test_retired_field_read_count)
    ('Hard cleanup historical docs with retired terms: {0}' -f [int]$summary.hard_cleanup_historical_doc_retired_term_file_count)
    ('Hard cleanup historical docs with retired marker: {0}' -f [int]$summary.hard_cleanup_historical_doc_marked_retired_term_count)
    ('Hard cleanup historical docs without retired marker: {0}' -f [int]$summary.hard_cleanup_historical_doc_unmarked_retired_term_count)
    ('Hard cleanup execution-internal specialist_dispatch references: {0}' -f [int]$summary.hard_cleanup_execution_internal_specialist_dispatch_reference_count)
    ('Hard cleanup current policy/helper dispatch vocabulary references: {0}' -f [int]$summary.hard_cleanup_current_policy_helper_dispatch_vocabulary_reference_count)
    ('Hard cleanup blocking failures: {0}' -f [int]$hardCleanupBlockingViolationCount)
    ('Hard cleanup compatibility review hits: {0}' -f [int]$summary.hard_cleanup_review_count)
    foreach ($finding in @($summary.findings)) {
        '[FAIL] {0}:{1} [{2}] {3}' -f $finding.path, $finding.line, $finding.pattern, $finding.text
    }
    if (
        [int]$summary.current_entrypoint_guidance_violation_count -eq 0 -and
        [int]$summary.current_surface_violation_count -eq 0 -and
        [int]$summary.current_runtime_old_format_fallback_count -eq 0 -and
        [int]$hardCleanupBlockingViolationCount -eq 0
    ) {
        'Gate Result: PASS'
    } else {
        'Gate Result: FAIL'
    }
}

if (
    [int]$summary.current_entrypoint_guidance_violation_count -gt 0 -or
    [int]$summary.current_surface_violation_count -gt 0 -or
    [int]$summary.current_runtime_old_format_fallback_count -gt 0 -or
    [int]$hardCleanupBlockingViolationCount -gt 0
) {
    exit 1
}
exit 0
