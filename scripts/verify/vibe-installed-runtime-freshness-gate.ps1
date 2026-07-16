param(
    [string]$TargetRoot = '',
    [switch]$WriteArtifacts
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\common\vibe-governance-helpers.ps1')
if ([string]::IsNullOrWhiteSpace($TargetRoot)) {
    $TargetRoot = Resolve-VgoTargetRoot
}

$installedRoot = [System.IO.Path]::GetFullPath((Join-Path (Join-Path $TargetRoot 'skills') 'vibe'))
$receiptPath = Join-Path $installedRoot '.vibeskills\install-receipt.json'
if (-not (Test-Path -LiteralPath $receiptPath -PathType Leaf)) {
    throw "Vibe install receipt is missing: $receiptPath"
}

$receipt = Get-Content -LiteralPath $receiptPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ([string]$receipt.receipt_kind -ne 'vibe-skill-install') {
    throw "Unexpected Vibe install receipt kind: $($receipt.receipt_kind)"
}
if ([System.IO.Path]::GetFullPath([string]$receipt.install_root) -ne $installedRoot) {
    throw "Vibe install receipt root does not match the installed runtime: $($receipt.install_root)"
}

$files = @($receipt.files)
if ($files.Count -eq 0) {
    throw 'Vibe install receipt owns no runtime files.'
}

$failures = [System.Collections.Generic.List[string]]::new()
foreach ($entry in $files) {
    $relativePath = [string]$entry.path
    $expectedHash = [string]$entry.sha256
    if ([string]::IsNullOrWhiteSpace($relativePath) -or $expectedHash -notmatch '^[0-9a-fA-F]{64}$') {
        [void]$failures.Add("invalid receipt entry: $relativePath")
        continue
    }

    $filePath = [System.IO.Path]::GetFullPath((Join-Path $installedRoot $relativePath))
    if (-not (Test-VgoPathWithin -ParentPath $installedRoot -ChildPath $filePath)) {
        [void]$failures.Add("receipt path escapes installed runtime: $relativePath")
        continue
    }
    if (-not (Test-Path -LiteralPath $filePath -PathType Leaf)) {
        [void]$failures.Add("missing receipt-owned file: $relativePath")
        continue
    }
    $actualHash = (Get-FileHash -LiteralPath $filePath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualHash -ne $expectedHash.ToLowerInvariant()) {
        [void]$failures.Add("hash mismatch: $relativePath")
    }
}

if ($failures.Count -gt 0) {
    throw ("Installed runtime freshness check failed:`n- " + ($failures -join "`n- "))
}

if ($WriteArtifacts) {
    $artifactPath = Join-Path $installedRoot 'outputs\verify\installed-runtime-freshness.json'
    $artifact = [ordered]@{
        gate_result = 'PASS'
        install_root = $installedRoot
        receipt_path = $receiptPath
        verified_file_count = $files.Count
        package_digest_sha256 = [string]$receipt.package_digest_sha256
    }
    $artifactDirectory = Split-Path -Parent $artifactPath
    New-Item -ItemType Directory -Path $artifactDirectory -Force | Out-Null
    $artifact | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $artifactPath -Encoding UTF8
}

Write-Host ("[PASS] installed runtime receipt verified ({0} files)" -f $files.Count) -ForegroundColor Green
