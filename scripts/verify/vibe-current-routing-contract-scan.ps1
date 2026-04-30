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
    'scripts/runtime/Write-RequirementDoc.ps1',
    'scripts/runtime/Write-XlPlan.ps1',
    'scripts/runtime/invoke-vibe-runtime.ps1'
)

$legacyAllowedFiles = @(
    'scripts/runtime/VibeConsultation.Common.ps1',
    'tests/runtime_neutral/test_vibe_specialist_consultation.py',
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

$findings = New-Object System.Collections.Generic.List[object]

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

$summary = [pscustomobject]@{
    current_surface_violation_count = @($findings | Where-Object { $_.category -eq 'current_surface_violation' }).Count
    legacy_reference_count = [int]$legacyReferenceCount
    historical_reference_count = [int]$historicalReferenceCount
    findings = [object[]]$findings.ToArray()
}

if ($Json) {
    $summary | ConvertTo-Json -Depth 20
} else {
    '=== VCO Current Routing Contract Scan ==='
    ('Current surface violations: {0}' -f [int]$summary.current_surface_violation_count)
    ('Legacy compatibility references: {0}' -f [int]$summary.legacy_reference_count)
    ('Historical doc references: {0}' -f [int]$summary.historical_reference_count)
    foreach ($finding in @($summary.findings)) {
        '[FAIL] {0}:{1} [{2}] {3}' -f $finding.path, $finding.line, $finding.pattern, $finding.text
    }
    if ([int]$summary.current_surface_violation_count -eq 0) {
        'Gate Result: PASS'
    } else {
        'Gate Result: FAIL'
    }
}

if ([int]$summary.current_surface_violation_count -gt 0) {
    exit 1
}
exit 0
