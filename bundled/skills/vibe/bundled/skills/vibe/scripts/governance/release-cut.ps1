param(
    [string]$Version = "",
    [string]$Updated = "",
    [switch]$RunGates
)

$ErrorActionPreference = "Stop"

function Read-Text {
    param([string]$Path)
    return Get-Content -LiteralPath $Path -Raw -Encoding UTF8
}

function Write-Text {
    param(
        [string]$Path,
        [string]$Content
    )
    Set-Content -LiteralPath $Path -Value $Content -Encoding UTF8
}

function Update-MaintenanceSection {
    param(
        [string]$Path,
        [string]$Version,
        [string]$Updated
    )

    $text = Read-Text -Path $Path
    $updatedText = $text
    $updatedText = [regex]::Replace($updatedText, "(?m)^- Version:\s*.+$", "- Version: $Version")
    $updatedText = [regex]::Replace($updatedText, "(?m)^- Updated:\s*.+$", "- Updated: $Updated")
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
        "",
        "- Release cut by `scripts/governance/release-cut.ps1`.",
        "- Fill in detailed release notes before merge.",
        ""
    ) -join "`n"

    if ($text -match "(?m)^# .+$") {
        $updated = [regex]::Replace($text, "(?m)^(# .+)$", "`$1`n`n$entry", 1)
    } else {
        $updated = "$entry`n$text"
    }
    Write-Text -Path $Path -Content $updated
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$governancePath = Join-Path $repoRoot "config\version-governance.json"
if (-not (Test-Path -LiteralPath $governancePath)) {
    throw "version-governance config not found: $governancePath"
}

$governance = Get-Content -LiteralPath $governancePath -Raw -Encoding UTF8 | ConvertFrom-Json
if ([string]::IsNullOrWhiteSpace($Version)) {
    $Version = [string]$governance.release.version
}
if ([string]::IsNullOrWhiteSpace($Updated)) {
    $Updated = (Get-Date -Format "yyyy-MM-dd")
}

$governance.release.version = $Version
$governance.release.updated = $Updated
$governanceJson = $governance | ConvertTo-Json -Depth 30
Write-Text -Path $governancePath -Content $governanceJson

$maintenanceFiles = @($governance.version_markers.maintenance_files)
foreach ($rel in $maintenanceFiles) {
    $path = Join-Path $repoRoot $rel
    if (-not (Test-Path -LiteralPath $path)) {
        throw "maintenance file missing: $rel"
    }
    Update-MaintenanceSection -Path $path -Version $Version -Updated $Updated
}

$changelogPath = Join-Path $repoRoot ([string]$governance.version_markers.changelog_path)
Ensure-ChangelogHeader -Path $changelogPath -Version $Version -Updated $Updated

$ledgerRel = [string]$governance.logs.release_ledger_jsonl
$ledgerPath = Join-Path $repoRoot $ledgerRel
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $ledgerPath) | Out-Null
$head = (git -C $repoRoot rev-parse --short HEAD).Trim()
$entry = [ordered]@{
    recorded_at = (Get-Date).ToString("s")
    version = $Version
    updated = $Updated
    git_head = $head
    actor = $env:USERNAME
}
Add-Content -LiteralPath $ledgerPath -Value ($entry | ConvertTo-Json -Compress) -Encoding UTF8

$releaseNotesDir = Join-Path $repoRoot ([string]$governance.logs.release_notes_dir)
New-Item -ItemType Directory -Force -Path $releaseNotesDir | Out-Null
$releaseNotePath = Join-Path $releaseNotesDir ("v{0}.md" -f $Version)
if (-not (Test-Path -LiteralPath $releaseNotePath)) {
    $note = @(
        "# VCO Release v$Version",
        "",
        "- Date: $Updated",
        "- Commit(base): $head",
        "",
        "## Highlights",
        "",
        "- TODO",
        "",
        "## Migration Notes",
        "",
        "- TODO"
    ) -join "`n"
    Write-Text -Path $releaseNotePath -Content $note
}

$syncScript = Join-Path $repoRoot "scripts\governance\sync-bundled-vibe.ps1"
if (Test-Path -LiteralPath $syncScript) {
    & $syncScript -PruneBundledExtras
    if ($LASTEXITCODE -ne 0) {
        throw "sync-bundled-vibe failed"
    }
}

if ($RunGates) {
    $gateScripts = @(
        "scripts\verify\vibe-version-consistency-gate.ps1",
        "scripts\verify\vibe-version-packaging-gate.ps1",
        "scripts\verify\vibe-config-parity-gate.ps1"
    )
    foreach ($rel in $gateScripts) {
        $gatePath = Join-Path $repoRoot $rel
        if (-not (Test-Path -LiteralPath $gatePath)) {
            throw "required gate script missing: $rel"
        }
        & $gatePath
        if ($LASTEXITCODE -ne 0) {
            throw "gate failed: $rel"
        }
    }
}

Write-Host "Release cut complete." -ForegroundColor Green
Write-Host ("version={0}, updated={1}" -f $Version, $Updated)
