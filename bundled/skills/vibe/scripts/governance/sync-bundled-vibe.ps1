param(
    [switch]$PruneBundledExtras
)

$ErrorActionPreference = "Stop"

function Copy-DirContent {
    param(
        [string]$Source,
        [string]$Destination
    )

    if (-not (Test-Path -LiteralPath $Source)) { return }
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    Copy-Item -Path (Join-Path $Source '*') -Destination $Destination -Recurse -Force
}

function Get-RelativePathPortable {
    param(
        [string]$BasePath,
        [string]$TargetPath
    )

    $baseFull = [System.IO.Path]::GetFullPath($BasePath)
    $targetFull = [System.IO.Path]::GetFullPath($TargetPath)
    if (-not $baseFull.EndsWith([System.IO.Path]::DirectorySeparatorChar)) {
        $baseFull = $baseFull + [System.IO.Path]::DirectorySeparatorChar
    }
    if ($targetFull.StartsWith($baseFull, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $targetFull.Substring($baseFull.Length).Replace("\", "/")
    }

    $baseUri = New-Object System.Uri($baseFull)
    $targetUri = New-Object System.Uri($targetFull)
    return [System.Uri]::UnescapeDataString($baseUri.MakeRelativeUri($targetUri).ToString()).Replace("\", "/")
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$governancePath = Join-Path $repoRoot "config\version-governance.json"
if (-not (Test-Path -LiteralPath $governancePath)) {
    throw "version governance config not found: $governancePath"
}

$governance = Get-Content -LiteralPath $governancePath -Raw -Encoding UTF8 | ConvertFrom-Json
$canonicalRoot = Join-Path $repoRoot ([string]$governance.source_of_truth.canonical_root)
$bundledRoot = Join-Path $repoRoot ([string]$governance.source_of_truth.bundled_root)
$nestedBundledRoot = Join-Path $bundledRoot "bundled\skills\vibe"
$mirrorFiles = @($governance.packaging.mirror.files)
$mirrorDirs = @($governance.packaging.mirror.directories)
$allowBundledOnly = @($governance.packaging.allow_bundled_only)

Write-Host "=== Sync Bundled Vibe ===" -ForegroundColor Cyan
Write-Host ("Canonical root: {0}" -f $canonicalRoot)
Write-Host ("Bundled root  : {0}" -f $bundledRoot)
if (Test-Path -LiteralPath $nestedBundledRoot) {
    Write-Host ("Nested root   : {0}" -f $nestedBundledRoot)
}

function Sync-ToBundledRoot {
    param([string]$TargetRoot)

    foreach ($rel in $mirrorFiles) {
        $src = Join-Path $canonicalRoot $rel
        $dst = Join-Path $TargetRoot $rel
        if (-not (Test-Path -LiteralPath $src)) {
            Write-Warning ("Skip missing canonical file: {0}" -f $rel)
            continue
        }
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dst) | Out-Null
        Copy-Item -LiteralPath $src -Destination $dst -Force
        Write-Host ("[SYNC] file {0} -> {1}" -f $rel, $TargetRoot)
    }

    foreach ($dir in $mirrorDirs) {
        $srcDir = Join-Path $canonicalRoot $dir
        $dstDir = Join-Path $TargetRoot $dir
        if (-not (Test-Path -LiteralPath $srcDir)) {
            Write-Warning ("Skip missing canonical dir: {0}" -f $dir)
            continue
        }
        Copy-DirContent -Source $srcDir -Destination $dstDir
        Write-Host ("[SYNC] dir  {0} -> {1}" -f $dir, $TargetRoot)

        if ($PruneBundledExtras) {
            $srcFiles = @(
                Get-ChildItem -LiteralPath $srcDir -Recurse -File | ForEach-Object {
                    Get-RelativePathPortable -BasePath $srcDir -TargetPath $_.FullName
                }
            )
            $dstFiles = @(
                Get-ChildItem -LiteralPath $dstDir -Recurse -File | ForEach-Object {
                    Get-RelativePathPortable -BasePath $dstDir -TargetPath $_.FullName
                }
            )

            foreach ($relPath in @($dstFiles | Where-Object { $_ -notin $srcFiles })) {
                $allowRel = "{0}/{1}" -f $dir, $relPath
                if ($allowBundledOnly -contains $allowRel) { continue }
                $target = Join-Path $dstDir $relPath
                Remove-Item -LiteralPath $target -Force -ErrorAction SilentlyContinue
                Write-Host ("[PRUNE] {0} -> {1}" -f $allowRel, $TargetRoot)
            }
        }
    }
}

Sync-ToBundledRoot -TargetRoot $bundledRoot
if (Test-Path -LiteralPath $nestedBundledRoot) {
    Sync-ToBundledRoot -TargetRoot $nestedBundledRoot
}

Write-Host "Sync complete." -ForegroundColor Green
