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

function Remove-IgnoredKeys {
    param(
        [object]$Node,
        [string[]]$IgnoreKeys
    )

    if ($null -eq $Node) { return $null }

    if ($Node -is [System.Management.Automation.PSCustomObject] -or ($Node -isnot [string] -and $Node.PSObject -and $Node.PSObject.Properties.Count -gt 0 -and $Node -isnot [System.Collections.IEnumerable])) {
        $ordered = [ordered]@{}
        foreach ($prop in @($Node.PSObject.Properties) | Sort-Object -Property Name) {
            $key = [string]$prop.Name
            if ($IgnoreKeys -contains $key) { continue }
            $ordered[$key] = Remove-IgnoredKeys -Node $prop.Value -IgnoreKeys $IgnoreKeys
        }
        return $ordered
    }

    if ($Node -is [System.Collections.IDictionary]) {
        $ordered = [ordered]@{}
        foreach ($key in @($Node.Keys) | Sort-Object) {
            $keyText = [string]$key
            if ($IgnoreKeys -contains $keyText) { continue }
            $ordered[$keyText] = Remove-IgnoredKeys -Node $Node[$key] -IgnoreKeys $IgnoreKeys
        }
        return $ordered
    }

    if ($Node -is [System.Collections.IEnumerable] -and -not ($Node -is [string])) {
        $items = @()
        foreach ($item in $Node) {
            $items += Remove-IgnoredKeys -Node $item -IgnoreKeys $IgnoreKeys
        }
        return $items
    }

    return $Node
}

function Get-NormalizedJsonHash {
    param(
        [string]$Path,
        [string[]]$IgnoreKeys
    )

    $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    $obj = $raw | ConvertFrom-Json
    $normalizedObj = Remove-IgnoredKeys -Node $obj -IgnoreKeys $IgnoreKeys
    $normalized = $normalizedObj | ConvertTo-Json -Depth 100 -Compress
    return (Get-FileHash -InputStream ([System.IO.MemoryStream]::new([System.Text.Encoding]::UTF8.GetBytes($normalized))) -Algorithm SHA256).Hash
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

function Get-FileParity {
    param(
        [string]$MainPath,
        [string]$BundledPath,
        [string[]]$IgnoreJsonKeys
    )

    if (-not (Test-Path -LiteralPath $MainPath) -or -not (Test-Path -LiteralPath $BundledPath)) {
        return $false
    }

    $mainExt = [System.IO.Path]::GetExtension($MainPath).ToLowerInvariant()
    $bundledExt = [System.IO.Path]::GetExtension($BundledPath).ToLowerInvariant()
    if ($mainExt -eq ".json" -and $bundledExt -eq ".json") {
        return (Get-NormalizedJsonHash -Path $MainPath -IgnoreKeys $IgnoreJsonKeys) -eq (Get-NormalizedJsonHash -Path $BundledPath -IgnoreKeys $IgnoreJsonKeys)
    }

    return (Get-FileHash -LiteralPath $MainPath -Algorithm SHA256).Hash -eq (Get-FileHash -LiteralPath $BundledPath -Algorithm SHA256).Hash
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$governancePath = Join-Path $repoRoot "config\version-governance.json"

Write-Host "=== VCO Version Packaging Gate ==="

if (-not (Test-Path -LiteralPath $governancePath)) {
    Write-Host "[FAIL] version governance config missing: $governancePath" -ForegroundColor Red
    exit 1
}

$governance = Get-Content -LiteralPath $governancePath -Raw -Encoding UTF8 | ConvertFrom-Json
$canonicalRoot = Join-Path $repoRoot ([string]$governance.source_of_truth.canonical_root)
$bundledRoot = Join-Path $repoRoot ([string]$governance.source_of_truth.bundled_root)
$mirrorFiles = @($governance.packaging.mirror.files)
$mirrorDirs = @($governance.packaging.mirror.directories)
$allowBundledOnly = @($governance.packaging.allow_bundled_only)
$ignoreJsonKeys = @($governance.packaging.normalized_json_ignore_keys)

$assertions = @()
$results = [ordered]@{
    release_version = [string]$governance.release.version
    release_updated = [string]$governance.release.updated
    files = @()
    directories = @()
}

$assertions += Assert-True -Condition (Test-Path -LiteralPath $canonicalRoot) -Message "canonical root exists"
$assertions += Assert-True -Condition (Test-Path -LiteralPath $bundledRoot) -Message "bundled root exists"

foreach ($rel in $mirrorFiles) {
    $mainPath = Join-Path $canonicalRoot $rel
    $bundledPath = Join-Path $bundledRoot $rel

    $mainExists = Test-Path -LiteralPath $mainPath
    $bundledExists = Test-Path -LiteralPath $bundledPath
    $parity = $false
    if ($mainExists -and $bundledExists) {
        $parity = Get-FileParity -MainPath $mainPath -BundledPath $bundledPath -IgnoreJsonKeys $ignoreJsonKeys
    }

    $assertions += Assert-True -Condition $mainExists -Message "[file:$rel] canonical exists"
    $assertions += Assert-True -Condition $bundledExists -Message "[file:$rel] bundled exists"
    if ($mainExists -and $bundledExists) {
        $assertions += Assert-True -Condition $parity -Message "[file:$rel] parity"
    }

    $results.files += [pscustomobject]@{
        path = [string]$rel
        canonical_exists = [bool]$mainExists
        bundled_exists = [bool]$bundledExists
        parity = [bool]$parity
    }
}

foreach ($dir in $mirrorDirs) {
    $mainDir = Join-Path $canonicalRoot $dir
    $bundledDir = Join-Path $bundledRoot $dir

    $mainExists = Test-Path -LiteralPath $mainDir
    $bundledExists = Test-Path -LiteralPath $bundledDir
    $assertions += Assert-True -Condition $mainExists -Message "[dir:$dir] canonical exists"
    $assertions += Assert-True -Condition $bundledExists -Message "[dir:$dir] bundled exists"

    $onlyMain = @()
    $onlyBundled = @()
    $diffFiles = @()

    if ($mainExists -and $bundledExists) {
        $mainFiles = @(
            Get-ChildItem -LiteralPath $mainDir -Recurse -File | ForEach-Object {
                Get-RelativePathPortable -BasePath $mainDir -TargetPath $_.FullName
            }
        )
        $bundledFiles = @(
            Get-ChildItem -LiteralPath $bundledDir -Recurse -File | ForEach-Object {
                Get-RelativePathPortable -BasePath $bundledDir -TargetPath $_.FullName
            }
        )

        $onlyMain = @($mainFiles | Where-Object { $_ -notin $bundledFiles } | Sort-Object)
        $onlyBundledRaw = @($bundledFiles | Where-Object { $_ -notin $mainFiles })
        $onlyBundled = @(
            $onlyBundledRaw | Where-Object {
                $fullRel = "{0}/{1}" -f $dir, $_
                $allowBundledOnly -notcontains $fullRel
            } | Sort-Object
        )

        $common = @($mainFiles | Where-Object { $_ -in $bundledFiles } | Sort-Object)
        foreach ($relPath in $common) {
            $mainPath = Join-Path $mainDir $relPath
            $bundledPath = Join-Path $bundledDir $relPath
            $same = Get-FileParity -MainPath $mainPath -BundledPath $bundledPath -IgnoreJsonKeys $ignoreJsonKeys
            if (-not $same) {
                $diffFiles += $relPath
            }
        }
    }

    $assertions += Assert-True -Condition ($onlyMain.Count -eq 0) -Message "[dir:$dir] no files missing in bundled"
    $assertions += Assert-True -Condition ($onlyBundled.Count -eq 0) -Message "[dir:$dir] no unexpected bundled-only files"
    $assertions += Assert-True -Condition ($diffFiles.Count -eq 0) -Message "[dir:$dir] file parity"

    $results.directories += [pscustomobject]@{
        path = [string]$dir
        only_in_canonical = @($onlyMain)
        only_in_bundled = @($onlyBundled)
        diff_files = @($diffFiles)
    }
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
    $jsonPath = Join-Path $outDir "vibe-version-packaging-gate.json"
    $mdPath = Join-Path $outDir "vibe-version-packaging-gate.md"

    $artifact = [ordered]@{
        generated_at = [DateTime]::UtcNow.ToString("o")
        gate_result = if ($gatePass) { "PASS" } else { "FAIL" }
        assertions = [ordered]@{
            total = $total
            passed = $passed
            failed = $failed
        }
        results = $results
    }

    $artifact | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

    $md = @(
        "# VCO Version Packaging Gate",
        "",
        ("- Generated: {0}" -f $artifact.generated_at),
        ("- Gate Result: **{0}**" -f $artifact.gate_result),
        ("- Assertions: total={0}, passed={1}, failed={2}" -f $total, $passed, $failed),
        "",
        "## Directory Summary"
    )
    foreach ($d in @($results.directories)) {
        $md += ("- {0}: only_in_canonical={1}, only_in_bundled={2}, diff_files={3}" -f $d.path, @($d.only_in_canonical).Count, @($d.only_in_bundled).Count, @($d.diff_files).Count)
    }
    $md -join "`n" | Set-Content -LiteralPath $mdPath -Encoding UTF8

    Write-Host ""
    Write-Host "Artifacts written:"
    Write-Host ("- {0}" -f $jsonPath)
    Write-Host ("- {0}" -f $mdPath)
}

if (-not $gatePass) { exit 1 }
