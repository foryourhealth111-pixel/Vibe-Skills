param(
    [Parameter(Mandatory)] [string]$CanonicalSlug,
    [Parameter(Mandatory)] [string]$UpstreamRepo,
    [Parameter(Mandatory)] [string]$UpstreamRef,
    [Parameter(Mandatory)] [string]$LicenseSpdx,
    [Parameter(Mandatory)] [string]$DistributionTier,
    [Parameter(Mandatory)] [string]$RedistributionPosture,
    [Parameter(Mandatory)] [string]$IntegrationMode,
    [Parameter(Mandatory)] [string]$LocalPath,
    [switch]$ShippedByDefault,
    [switch]$ModifiedByVco,
    [string]$RefreshCommand = '',
    [string]$RequiredNoticeFiles = 'none',
    [string]$TrademarkNotes = 'none',
    [string]$SecurityOrComplianceNotes = 'none',
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\common\vibe-governance-helpers.ps1')

$context = Get-VgoGovernanceContext -ScriptPath $PSCommandPath -EnforceExecutionContext
$repoRoot = $context.repoRoot

$templatePath = Join-Path $repoRoot 'templates\ORIGIN.md.tmpl'
if (-not (Test-Path -LiteralPath $templatePath)) {
    throw "ORIGIN template not found: $templatePath"
}

$targetRoot = if ([System.IO.Path]::IsPathRooted($LocalPath)) {
    [System.IO.Path]::GetFullPath($LocalPath)
} else {
    [System.IO.Path]::GetFullPath((Join-Path $repoRoot $LocalPath))
}

if (-not (Test-VgoPathWithin -ParentPath (Join-Path $repoRoot 'vendor') -ChildPath $targetRoot)) {
    throw "ORIGIN records must live under vendor/**. target=$targetRoot"
}
if ([System.String]::Equals(
        $targetRoot.TrimEnd('\', '/'),
        [System.IO.Path]::GetFullPath((Join-Path $repoRoot 'vendor')).TrimEnd('\', '/'),
        [System.StringComparison]::OrdinalIgnoreCase
    )) {
    throw "ORIGIN records must live under vendor/**, not at vendor root. target=$targetRoot"
}

New-Item -ItemType Directory -Force -Path $targetRoot | Out-Null
$originPath = Join-Path $targetRoot 'ORIGIN.md'
if ((Test-Path -LiteralPath $originPath) -and -not $Force) {
    throw "ORIGIN.md already exists: $originPath (use -Force to overwrite)"
}

$content = @(
    '# ORIGIN',
    '',
    ('- `canonical_slug`: `{0}`' -f $CanonicalSlug),
    ('- `upstream_repo`: `{0}`' -f $UpstreamRepo),
    ('- `upstream_ref`: `{0}`' -f $UpstreamRef),
    ('- `license_spdx`: `{0}`' -f $LicenseSpdx),
    ('- `distribution_tier`: `{0}`' -f $DistributionTier),
    ('- `redistribution_posture`: `{0}`' -f $RedistributionPosture),
    ('- `integration_mode`: `{0}`' -f $IntegrationMode),
    ('- `local_path`: `{0}`' -f (Get-VgoRelativePathPortable -BasePath $repoRoot -TargetPath $targetRoot)),
    ('- `shipped_by_default`: `{0}`' -f $(if ($ShippedByDefault) { 'true' } else { 'false' })),
    ('- `modified_by_vco`: `{0}`' -f $(if ($ModifiedByVco) { 'true' } else { 'false' })),
    ('- `refresh_command`: `{0}`' -f $(if ([string]::IsNullOrWhiteSpace($RefreshCommand)) { 'pwsh -File scripts/governance/new-origin-record.ps1 ...' } else { $RefreshCommand })),
    ('- `required_notice_files`: `{0}`' -f $RequiredNoticeFiles),
    ('- `trademark_notes`: `{0}`' -f $TrademarkNotes),
    ('- `security_or_compliance_notes`: `{0}`' -f $SecurityOrComplianceNotes),
    '',
    '## Notes',
    '',
    '- Describe whether this asset is verbatim, adapted, or retained only for reference.',
    '- If the asset is not shipped by default, say so explicitly.'
)

Write-VgoUtf8NoBomText -Path $originPath -Content ($content -join "`n")
Write-Host "ORIGIN record written: $originPath" -ForegroundColor Green
