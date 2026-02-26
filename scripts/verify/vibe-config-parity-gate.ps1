param(
    [switch]$WriteArtifacts,
    [string]$OutputDirectory,
    [string[]]$IgnoreKeys = @("updated", "generated_at")
)

$ErrorActionPreference = "Stop"

function Get-IsDictionaryLike {
    param([object]$Value)

    if ($null -eq $Value) { return $false }
    return ($Value -is [System.Collections.IDictionary]) -or ($Value -is [pscustomobject])
}

function Get-IsListLike {
    param([object]$Value)

    if ($null -eq $Value) { return $false }
    if ($Value -is [string]) { return $false }
    return ($Value -is [System.Collections.IEnumerable])
}

function Normalize-JsonNode {
    param(
        [object]$Node,
        [string[]]$KeysToIgnore
    )

    if (Get-IsDictionaryLike -Value $Node) {
        $names = @()
        if ($Node -is [System.Collections.IDictionary]) {
            $names = @($Node.Keys)
        } else {
            $names = @($Node.PSObject.Properties.Name)
        }

        $filtered = @($names | Where-Object { $KeysToIgnore -notcontains [string]$_ } | Sort-Object)
        $ordered = [ordered]@{}
        foreach ($name in $filtered) {
            $value = if ($Node -is [System.Collections.IDictionary]) { $Node[$name] } else { $Node.$name }
            $ordered[[string]$name] = Normalize-JsonNode -Node $value -KeysToIgnore $KeysToIgnore
        }
        return $ordered
    }

    if (Get-IsListLike -Value $Node) {
        $arr = @()
        foreach ($item in $Node) {
            $arr += Normalize-JsonNode -Node $item -KeysToIgnore $KeysToIgnore
        }
        return $arr
    }

    return $Node
}

function Get-CanonicalJson {
    param([object]$Node)
    return ($Node | ConvertTo-Json -Depth 100 -Compress)
}

function Get-StringHash {
    param([string]$Input)

    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Input)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $hashBytes = $sha.ComputeHash($bytes)
    } finally {
        $sha.Dispose()
    }
    return ([BitConverter]::ToString($hashBytes)).Replace("-", "").ToLowerInvariant()
}

function Get-NodeTypeName {
    param([object]$Value)

    if ($null -eq $Value) { return "null" }
    if (Get-IsDictionaryLike -Value $Value) { return "object" }
    if (Get-IsListLike -Value $Value) { return "array" }
    return "scalar"
}

function Compare-NormalizedNode {
    param(
        [object]$Left,
        [object]$Right,
        [string]$Path,
        [ref]$DiffPaths
    )

    $leftType = Get-NodeTypeName -Value $Left
    $rightType = Get-NodeTypeName -Value $Right

    if ($leftType -ne $rightType) {
        $DiffPaths.Value += "$Path (type: $leftType != $rightType)"
        return
    }

    if ($leftType -eq "object") {
        $leftKeys = @($Left.Keys)
        $rightKeys = @($Right.Keys)
        $allKeys = @($leftKeys + $rightKeys | Sort-Object -Unique)
        foreach ($key in $allKeys) {
            $leftHas = $leftKeys -contains $key
            $rightHas = $rightKeys -contains $key
            $childPath = "$Path/$key"
            if (-not $leftHas) {
                $DiffPaths.Value += "$childPath (missing in main)"
                continue
            }
            if (-not $rightHas) {
                $DiffPaths.Value += "$childPath (missing in bundled)"
                continue
            }
            Compare-NormalizedNode -Left $Left[$key] -Right $Right[$key] -Path $childPath -DiffPaths $DiffPaths
        }
        return
    }

    if ($leftType -eq "array") {
        $leftCount = @($Left).Count
        $rightCount = @($Right).Count
        if ($leftCount -ne $rightCount) {
            $DiffPaths.Value += "$Path (length: $leftCount != $rightCount)"
        }

        $max = [Math]::Max($leftCount, $rightCount)
        for ($i = 0; $i -lt $max; $i++) {
            $childPath = "$Path[$i]"
            if ($i -ge $leftCount) {
                $DiffPaths.Value += "$childPath (missing in main)"
                continue
            }
            if ($i -ge $rightCount) {
                $DiffPaths.Value += "$childPath (missing in bundled)"
                continue
            }
            Compare-NormalizedNode -Left $Left[$i] -Right $Right[$i] -Path $childPath -DiffPaths $DiffPaths
        }
        return
    }

    $leftScalar = if ($null -eq $Left) { "null" } else { [string]$Left }
    $rightScalar = if ($null -eq $Right) { "null" } else { [string]$Right }
    if ($leftScalar -ne $rightScalar) {
        $DiffPaths.Value += "$Path ($leftScalar != $rightScalar)"
    }
}

function Load-JsonFile {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "File not found: $Path"
    }
    return (Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json)
}

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

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")

$pairs = @(
    [pscustomobject]@{ id = "pack-manifest"; main = "config/pack-manifest.json"; bundled = "bundled/skills/vibe/config/pack-manifest.json" },
    [pscustomobject]@{ id = "router-thresholds"; main = "config/router-thresholds.json"; bundled = "bundled/skills/vibe/config/router-thresholds.json" },
    [pscustomobject]@{ id = "skill-keyword-index"; main = "config/skill-keyword-index.json"; bundled = "bundled/skills/vibe/config/skill-keyword-index.json" },
    [pscustomobject]@{ id = "skill-routing-rules"; main = "config/skill-routing-rules.json"; bundled = "bundled/skills/vibe/config/skill-routing-rules.json" },
    [pscustomobject]@{ id = "openspec-policy"; main = "config/openspec-policy.json"; bundled = "bundled/skills/vibe/config/openspec-policy.json" },
    [pscustomobject]@{ id = "gsd-overlay"; main = "config/gsd-overlay.json"; bundled = "bundled/skills/vibe/config/gsd-overlay.json" },
    [pscustomobject]@{ id = "prompt-overlay"; main = "config/prompt-overlay.json"; bundled = "bundled/skills/vibe/config/prompt-overlay.json" },
    [pscustomobject]@{ id = "memory-governance"; main = "config/memory-governance.json"; bundled = "bundled/skills/vibe/config/memory-governance.json" },
    [pscustomobject]@{ id = "data-scale-overlay"; main = "config/data-scale-overlay.json"; bundled = "bundled/skills/vibe/config/data-scale-overlay.json" },
    [pscustomobject]@{ id = "quality-debt-overlay"; main = "config/quality-debt-overlay.json"; bundled = "bundled/skills/vibe/config/quality-debt-overlay.json" },
    [pscustomobject]@{ id = "framework-interop-overlay"; main = "config/framework-interop-overlay.json"; bundled = "bundled/skills/vibe/config/framework-interop-overlay.json" },
    [pscustomobject]@{ id = "ml-lifecycle-overlay"; main = "config/ml-lifecycle-overlay.json"; bundled = "bundled/skills/vibe/config/ml-lifecycle-overlay.json" },
    [pscustomobject]@{ id = "python-clean-code-overlay"; main = "config/python-clean-code-overlay.json"; bundled = "bundled/skills/vibe/config/python-clean-code-overlay.json" },
    [pscustomobject]@{ id = "system-design-overlay"; main = "config/system-design-overlay.json"; bundled = "bundled/skills/vibe/config/system-design-overlay.json" },
    [pscustomobject]@{ id = "cuda-kernel-overlay"; main = "config/cuda-kernel-overlay.json"; bundled = "bundled/skills/vibe/config/cuda-kernel-overlay.json" }
)

$results = @()
$assertions = @()

Write-Host "=== VCO Config Parity Gate ==="
Write-Host ("Ignore keys: {0}" -f ($IgnoreKeys -join ", "))
Write-Host ""

foreach ($pair in $pairs) {
    $mainPath = Join-Path $repoRoot $pair.main
    $bundledPath = Join-Path $repoRoot $pair.bundled
    $existsMain = Test-Path -LiteralPath $mainPath
    $existsBundled = Test-Path -LiteralPath $bundledPath

    $assertions += Assert-True -Condition $existsMain -Message "[$($pair.id)] main config exists"
    $assertions += Assert-True -Condition $existsBundled -Message "[$($pair.id)] bundled config exists"

    if (-not ($existsMain -and $existsBundled)) {
        $results += [pscustomobject]@{
            id = $pair.id
            main_path = $mainPath
            bundled_path = $bundledPath
            main_exists = $existsMain
            bundled_exists = $existsBundled
            hash_match = $false
            diff_paths_count = $null
            diff_paths = @("missing_file")
            parse_error = $null
        }
        continue
    }

    $parseError = $null
    $mainHash = $null
    $bundledHash = $null
    $hashMatch = $false
    $diffPaths = @()

    try {
        $mainJson = Load-JsonFile -Path $mainPath
        $bundledJson = Load-JsonFile -Path $bundledPath

        $normMain = Normalize-JsonNode -Node $mainJson -KeysToIgnore $IgnoreKeys
        $normBundled = Normalize-JsonNode -Node $bundledJson -KeysToIgnore $IgnoreKeys

        $mainCanonical = Get-CanonicalJson -Node $normMain
        $bundledCanonical = Get-CanonicalJson -Node $normBundled
        $mainHash = Get-StringHash -Input $mainCanonical
        $bundledHash = Get-StringHash -Input $bundledCanonical
        $hashMatch = ($mainHash -eq $bundledHash)

        if (-not $hashMatch) {
            Compare-NormalizedNode -Left $normMain -Right $normBundled -Path "$" -DiffPaths ([ref]$diffPaths)
        }
    } catch {
        $parseError = $_.Exception.Message
        $hashMatch = $false
        if ($diffPaths.Count -eq 0) {
            $diffPaths = @("parse_error")
        }
    }

    $assertions += Assert-True -Condition $hashMatch -Message "[$($pair.id)] normalized hash parity"

    $results += [pscustomobject]@{
        id = $pair.id
        main_path = $mainPath
        bundled_path = $bundledPath
        main_exists = $existsMain
        bundled_exists = $existsBundled
        main_hash = $mainHash
        bundled_hash = $bundledHash
        hash_match = $hashMatch
        diff_paths_count = $diffPaths.Count
        diff_paths = @($diffPaths | Select-Object -First 40)
        parse_error = $parseError
    }
}

$pairsTotal = $pairs.Count
$pairsMatched = (@($results | Where-Object { $_.hash_match }).Count)
$hashMatchRate = if ($pairsTotal -gt 0) { [double]$pairsMatched / [double]$pairsTotal } else { 1.0 }
$totalDiffPaths = (@($results | ForEach-Object { if ($_.diff_paths_count) { $_.diff_paths_count } else { 0 } } | Measure-Object -Sum).Sum)
$gatePassed = ($pairsMatched -eq $pairsTotal) -and (($assertions | Where-Object { -not $_ }).Count -eq 0)

Write-Host ""
Write-Host "=== Summary ==="
Write-Host ("Pairs total: {0}" -f $pairsTotal)
Write-Host ("Pairs matched: {0}" -f $pairsMatched)
Write-Host ("Hash match rate: {0:N4}" -f $hashMatchRate)
Write-Host ("Total diff paths: {0}" -f $totalDiffPaths)
Write-Host ("Gate Result: {0}" -f $(if ($gatePassed) { "PASS" } else { "FAIL" }))

$report = [pscustomobject]@{
    generated_at = (Get-Date).ToString("s")
    ignore_keys = $IgnoreKeys
    metrics = [pscustomobject]@{
        pairs_total = $pairsTotal
        pairs_matched = $pairsMatched
        hash_match_rate = [Math]::Round([double]$hashMatchRate, 4)
        total_diff_paths = [int]$totalDiffPaths
    }
    thresholds = [pscustomobject]@{
        parity_critical_files = 1.0
        hash_match_rate = 1.0
        total_diff_paths = 0
    }
    gate_passed = $gatePassed
    results = $results
}

if ($WriteArtifacts) {
    if (-not $OutputDirectory) {
        $OutputDirectory = Join-Path $repoRoot "outputs/verify"
    }
    New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null

    $jsonPath = Join-Path $OutputDirectory "vibe-config-parity-gate.json"
    $mdPath = Join-Path $OutputDirectory "vibe-config-parity-gate.md"

    $report | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

    $lines = @()
    $lines += "# VCO Config Parity Gate"
    $lines += ""
    $lines += "- generated_at: ``$($report.generated_at)``"
    $lines += "- gate_passed: ``$($report.gate_passed)``"
    $lines += "- pairs_total: ``$($report.metrics.pairs_total)``"
    $lines += "- pairs_matched: ``$($report.metrics.pairs_matched)``"
    $lines += "- hash_match_rate: ``$($report.metrics.hash_match_rate)``"
    $lines += "- total_diff_paths: ``$($report.metrics.total_diff_paths)``"
    $lines += ""
    $lines += "## Pair Details"
    $lines += ""
    foreach ($row in $results) {
        $lines += "- ``$($row.id)``: match=``$($row.hash_match)`` diff_paths=``$($row.diff_paths_count)``"
    }

    $lines -join "`n" | Set-Content -LiteralPath $mdPath -Encoding UTF8
    Write-Host ""
    Write-Host "Artifacts written:"
    Write-Host "- $jsonPath"
    Write-Host "- $mdPath"
}

if (-not $gatePassed) {
    exit 1
}

exit 0
