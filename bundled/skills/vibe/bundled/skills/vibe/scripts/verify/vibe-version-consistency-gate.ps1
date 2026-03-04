param(
    [switch]$WriteArtifacts
)

$ErrorActionPreference = "Stop"

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

function Read-Text {
    param([string]$Path)
    return Get-Content -LiteralPath $Path -Raw -Encoding UTF8
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$governancePath = Join-Path $repoRoot "config\version-governance.json"

Write-Host "=== VCO Version Consistency Gate ==="

if (-not (Test-Path -LiteralPath $governancePath)) {
    Write-Host "[FAIL] version-governance config missing: $governancePath" -ForegroundColor Red
    exit 1
}

$governance = Get-Content -LiteralPath $governancePath -Raw -Encoding UTF8 | ConvertFrom-Json
$releaseVersion = [string]$governance.release.version
$releaseUpdated = [string]$governance.release.updated
$maintenanceFiles = @($governance.version_markers.maintenance_files)
$changelogPath = Join-Path $repoRoot ([string]$governance.version_markers.changelog_path)
$ledgerPath = Join-Path $repoRoot ([string]$governance.logs.release_ledger_jsonl)

$assertions = @()
$details = [ordered]@{
    release = [ordered]@{
        version = $releaseVersion
        updated = $releaseUpdated
    }
    maintenance = @()
    changelog = [ordered]@{}
    ledger = [ordered]@{}
}

$assertions += Assert-True -Condition (-not [string]::IsNullOrWhiteSpace($releaseVersion)) -Message "release.version set"
$assertions += Assert-True -Condition ($releaseUpdated -match "^\d{4}-\d{2}-\d{2}$") -Message "release.updated uses YYYY-MM-DD"

foreach ($rel in $maintenanceFiles) {
    $path = Join-Path $repoRoot $rel
    $exists = Test-Path -LiteralPath $path
    $verOk = $false
    $dateOk = $false

    if ($exists) {
        $text = Read-Text -Path $path
        $verOk = $text -match ("(?m)^- Version:\s*" + [regex]::Escape($releaseVersion) + "\s*$")
        $dateOk = $text -match ("(?m)^- Updated:\s*" + [regex]::Escape($releaseUpdated) + "\s*$")
    }

    $assertions += Assert-True -Condition $exists -Message "[maintenance:$rel] file exists"
    $assertions += Assert-True -Condition $verOk -Message "[maintenance:$rel] version marker matches"
    $assertions += Assert-True -Condition $dateOk -Message "[maintenance:$rel] updated marker matches"

    $details.maintenance += [ordered]@{
        path = $rel
        exists = $exists
        version_match = $verOk
        updated_match = $dateOk
    }
}

$changelogExists = Test-Path -LiteralPath $changelogPath
$changelogHeadOk = $false
if ($changelogExists) {
    $changelog = Read-Text -Path $changelogPath
    $expectedHeader = "## v$releaseVersion ($releaseUpdated)"
    # Accept both LF and CRLF line endings to avoid false negatives across platforms.
    $changelogHeadOk = $changelog -match ("(?m)^" + [regex]::Escape($expectedHeader) + "\r?$")
}
$assertions += Assert-True -Condition $changelogExists -Message "[changelog] exists"
$assertions += Assert-True -Condition $changelogHeadOk -Message "[changelog] release header exists"
$details.changelog = [ordered]@{
    path = [string]$governance.version_markers.changelog_path
    exists = $changelogExists
    header_match = $changelogHeadOk
}

$ledgerExists = Test-Path -LiteralPath $ledgerPath
$ledgerVersionOk = $false
$ledgerDateOk = $false
$latestLedger = $null
if ($ledgerExists) {
    $lines = @(Get-Content -LiteralPath $ledgerPath -Encoding UTF8 | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    if ($lines.Count -gt 0) {
        try {
            $latestLedger = $lines[-1] | ConvertFrom-Json
            $ledgerVersionOk = ([string]$latestLedger.version -eq $releaseVersion)
            $ledgerDateOk = ([string]$latestLedger.updated -eq $releaseUpdated)
        } catch {
            $latestLedger = $null
        }
    }
}
$assertions += Assert-True -Condition $ledgerExists -Message "[ledger] exists"
$assertions += Assert-True -Condition $ledgerVersionOk -Message "[ledger] latest version matches"
$assertions += Assert-True -Condition $ledgerDateOk -Message "[ledger] latest updated matches"
$details.ledger = [ordered]@{
    path = [string]$governance.logs.release_ledger_jsonl
    exists = $ledgerExists
    latest_entry = $latestLedger
    version_match = $ledgerVersionOk
    updated_match = $ledgerDateOk
}

$total = $assertions.Count
$passed = @($assertions | Where-Object { $_ }).Count
$failed = $total - $passed
$gatePass = ($failed -eq 0)

Write-Host ""
Write-Host "=== Summary ==="
Write-Host ("Total assertions: {0}" -f $total)
Write-Host ("Passed: {0}" -f $passed)
Write-Host ("Failed: {0}" -f $failed)
Write-Host ("Gate Result: {0}" -f $(if ($gatePass) { "PASS" } else { "FAIL" }))

if ($WriteArtifacts) {
    $outDir = Join-Path $repoRoot "outputs\verify"
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null
    $jsonPath = Join-Path $outDir "vibe-version-consistency-gate.json"
    $mdPath = Join-Path $outDir "vibe-version-consistency-gate.md"

    $artifact = [ordered]@{
        generated_at = [DateTime]::UtcNow.ToString("o")
        gate_result = if ($gatePass) { "PASS" } else { "FAIL" }
        assertions = [ordered]@{
            total = $total
            passed = $passed
            failed = $failed
        }
        details = $details
    }

    $artifact | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
    $md = @(
        "# VCO Version Consistency Gate",
        "",
        ("- Gate Result: **{0}**" -f $artifact.gate_result),
        ("- Assertions: total={0}, passed={1}, failed={2}" -f $total, $passed, $failed),
        ('- release.version: `{0}`' -f $releaseVersion),
        ('- release.updated: `{0}`' -f $releaseUpdated)
    ) -join "`n"
    Set-Content -LiteralPath $mdPath -Value $md -Encoding UTF8
}

if (-not $gatePass) {
    exit 1
}
