param(
    [string]$SkillsRoot = "",
    [string]$PackManifestPath = "",
    [string]$SkillsLockPath = "",
    [switch]$SkipHash
)

$ErrorActionPreference = "Stop"

function New-CaseInsensitiveSet {
    return New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::OrdinalIgnoreCase)
}

function Get-BytesHash {
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [byte[]]$Bytes
    )

    $stream = [System.IO.MemoryStream]::new($Bytes)
    try {
        return (Get-FileHash -InputStream $stream -Algorithm SHA256).Hash.ToLower()
    } finally {
        $stream.Dispose()
    }
}

function Test-TextLikeFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [byte[]]$Bytes
    )

    $textExt = @(
        ".md", ".txt", ".json", ".ps1", ".psm1", ".sh",
        ".yml", ".yaml", ".toml", ".ini", ".cfg", ".xml",
        ".csv", ".tsv", ".js", ".ts", ".jsx", ".tsx",
        ".py", ".rb", ".go", ".rs", ".java", ".c", ".cpp", ".h", ".hpp",
        ".css", ".html", ".htm", ".sql"
    )

    $ext = [System.IO.Path]::GetExtension($Path).ToLowerInvariant()
    if ($textExt -contains $ext) {
        return $true
    }

    return -not ($Bytes -contains 0)
}

function Get-NormalizedFileHash {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $rawBytes = [System.IO.File]::ReadAllBytes($Path)
    if (-not (Test-TextLikeFile -Path $Path -Bytes $rawBytes)) {
        return Get-BytesHash -Bytes $rawBytes
    }

    $text = [System.Text.Encoding]::UTF8.GetString($rawBytes)
    $normalized = $text.Replace("`r`n", "`n").Replace("`r", "`n")
    $normalizedBytes = [System.Text.Encoding]::UTF8.GetBytes($normalized)
    return Get-BytesHash -Bytes $normalizedBytes
}

function Get-SkillDirHash {
    param(
        [Parameter(Mandatory = $true)]
        [string]$DirPath
    )

    $filesByRelative = @{}
    $relativePaths = [System.Collections.Generic.List[string]]::new()
    $entries = New-Object System.Collections.Generic.List[string]
    $totalBytes = 0

    foreach ($file in Get-ChildItem -LiteralPath $DirPath -Force -Recurse -File) {
        $relative = $file.FullName.Substring($DirPath.Length + 1).Replace('\', '/')
        if (
            $relative.Equals("config/skills-lock.json", [System.StringComparison]::OrdinalIgnoreCase) -or
            $relative.EndsWith("/config/skills-lock.json", [System.StringComparison]::OrdinalIgnoreCase)
        ) {
            continue
        }
        $filesByRelative[$relative] = $file
        $relativePaths.Add($relative)
    }

    $relativePaths.Sort([System.StringComparer]::Ordinal)
    foreach ($relative in $relativePaths) {
        $file = $filesByRelative[$relative]
        $fileHash = Get-NormalizedFileHash -Path $file.FullName
        $entries.Add("$relative`:$fileHash")
        $totalBytes += $file.Length
    }

    $joined = [string]::Join("`n", $entries)
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($joined)
    $dirHash = Get-BytesHash -Bytes $bytes

    return [pscustomobject]@{
        dir_hash   = $dirHash
        file_count = $relativePaths.Count
        bytes      = $totalBytes
    }
}

function Get-CanonicalSkillMap {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot
    )

    $map = @{}
    $coreSkillsRoot = Join-Path $RepoRoot 'core\skills'
    if (-not (Test-Path -LiteralPath $coreSkillsRoot)) {
        return $map
    }

    $skillDirs = @(Get-ChildItem -LiteralPath $coreSkillsRoot -Force -Directory | Sort-Object Name)
    foreach ($dir in $skillDirs) {
        $skillJsonPath = Join-Path $dir.FullName 'skill.json'
        if (-not (Test-Path -LiteralPath $skillJsonPath)) {
            continue
        }

        $skillJson = Get-Content -LiteralPath $skillJsonPath -Raw | ConvertFrom-Json
        $source = if ($skillJson.PSObject.Properties.Name -contains 'source_of_truth') { $skillJson.source_of_truth } else { $null }
        $sourceKind = if ($null -ne $source -and $source.PSObject.Properties.Name -contains 'kind') { [string]$source.kind } else { '' }
        $sourcePathSpec = if ($null -ne $source -and $source.PSObject.Properties.Name -contains 'path') { [string]$source.path } else { '' }
        $skillId = if ($skillJson.PSObject.Properties.Name -contains 'skill_id') { [string]$skillJson.skill_id } else { [string]$dir.Name }

        if ($sourceKind -ne 'canonical-skill' -or [string]::IsNullOrWhiteSpace($skillId) -or [string]::IsNullOrWhiteSpace($sourcePathSpec)) {
            continue
        }

        $resolvedSourcePath = Join-Path $RepoRoot ($sourcePathSpec.Replace('/', [System.IO.Path]::DirectorySeparatorChar))
        $skillDirectory = $resolvedSourcePath
        $skillMd = $resolvedSourcePath
        if (Test-Path -LiteralPath $resolvedSourcePath -PathType Leaf) {
            $skillDirectory = Split-Path -Parent $resolvedSourcePath
            $skillMd = $resolvedSourcePath
        } else {
            $leafName = [System.IO.Path]::GetFileName($resolvedSourcePath)
            if ($leafName.Equals('SKILL.md', [System.StringComparison]::OrdinalIgnoreCase)) {
                $skillDirectory = Split-Path -Parent $resolvedSourcePath
                $skillMd = $resolvedSourcePath
            } else {
                $skillDirectory = $resolvedSourcePath
                $skillMd = Join-Path $skillDirectory 'SKILL.md'
            }
        }

        $map[$skillId] = [pscustomobject]@{
            skill_id = $skillId
            source_kind = $sourceKind
            directory = $skillDirectory
            skill_md = $skillMd
        }
    }

    return $map
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
if ([string]::IsNullOrWhiteSpace($SkillsRoot)) {
    $SkillsRoot = Join-Path $repoRoot "bundled\skills"
}
if ([string]::IsNullOrWhiteSpace($PackManifestPath)) {
    $PackManifestPath = Join-Path $repoRoot "config\pack-manifest.json"
}
if ([string]::IsNullOrWhiteSpace($SkillsLockPath)) {
    $SkillsLockPath = Join-Path $repoRoot "config\skills-lock.json"
}

if (-not (Test-Path -LiteralPath $SkillsRoot)) {
    throw "Skills root not found: $SkillsRoot"
}
if (-not (Test-Path -LiteralPath $PackManifestPath)) {
    throw "Pack manifest not found: $PackManifestPath"
}
if (-not (Test-Path -LiteralPath $SkillsLockPath)) {
    throw "Skills lock not found: $SkillsLockPath"
}

$manifest = Get-Content -LiteralPath $PackManifestPath -Raw | ConvertFrom-Json
$lock = Get-Content -LiteralPath $SkillsLockPath -Raw | ConvertFrom-Json
$canonicalSkillMap = Get-CanonicalSkillMap -RepoRoot $repoRoot
$canonicalSkillSet = New-CaseInsensitiveSet
foreach ($canonicalSkillId in @($canonicalSkillMap.Keys)) {
    [void]$canonicalSkillSet.Add([string]$canonicalSkillId)
}

$requiredSet = New-CaseInsensitiveSet
$alwaysRequired = @(
    "vibe",
    "dialectic",
    "local-vco-roles",
    "spec-kit-vibe-compat",
    "superclaude-framework-compat",
    "ralph-loop",
    "cancel-ralph",
    "tdd-guide",
    "think-harder",
    "brainstorming",
    "writing-plans",
    "subagent-driven-development",
    "systematic-debugging"
)

foreach ($name in $alwaysRequired) {
    [void]$requiredSet.Add($name)
}

foreach ($pack in $manifest.packs) {
    foreach ($candidate in $pack.skill_candidates) {
        if (-not [string]::IsNullOrWhiteSpace($candidate)) {
            [void]$requiredSet.Add([string]$candidate)
        }
    }

    if ($pack.defaults_by_task) {
        foreach ($prop in $pack.defaults_by_task.PSObject.Properties) {
            $value = [string]$prop.Value
            if (-not [string]::IsNullOrWhiteSpace($value)) {
                [void]$requiredSet.Add($value)
            }
        }
    }
}

$presentSkills = Get-ChildItem -LiteralPath $SkillsRoot -Force -Directory | Select-Object -ExpandProperty Name
$presentSet = New-CaseInsensitiveSet
foreach ($name in $presentSkills) {
    [void]$presentSet.Add($name)
}

$lockSet = New-CaseInsensitiveSet
$lockMap = @{}
foreach ($item in $lock.skills) {
    $name = [string]$item.name
    if ([string]::IsNullOrWhiteSpace($name)) {
        continue
    }
    [void]$lockSet.Add($name)
    $lockMap[$name] = $item
}

$missingRequired = @()
$missingCanonicalRequired = @()
$missingRequiredSkillMd = @()
foreach ($name in $requiredSet | Sort-Object) {
    if ($canonicalSkillSet.Contains($name)) {
        $canonicalSkill = $canonicalSkillMap[$name]
        $canonicalSkillMdPath = if ($null -ne $canonicalSkill) { [string]$canonicalSkill.skill_md } else { '' }
        if ([string]::IsNullOrWhiteSpace($canonicalSkillMdPath) -or -not (Test-Path -LiteralPath $canonicalSkillMdPath)) {
            $missingCanonicalRequired += $name
        }
        continue
    }

    if (-not $presentSet.Contains($name)) {
        $missingRequired += $name
        continue
    }

    $skillMdPath = Join-Path $SkillsRoot "$name\SKILL.md"
    if (-not (Test-Path -LiteralPath $skillMdPath)) {
        $missingRequiredSkillMd += $name
    }
}

$missingInLock = @()
foreach ($name in $requiredSet | Sort-Object) {
    if ($canonicalSkillSet.Contains($name)) {
        continue
    }
    if (-not $lockSet.Contains($name)) {
        $missingInLock += $name
    }
}

$missingInSkills = @()
foreach ($name in $lockSet | Sort-Object) {
    if (-not $presentSet.Contains($name)) {
        $missingInSkills += $name
    }
}

$extraInSkills = @()
foreach ($name in $presentSet | Sort-Object) {
    if (-not $lockSet.Contains($name)) {
        $extraInSkills += $name
    }
}

$hashMismatches = @()
$skillMdMismatches = @()
if (-not $SkipHash) {
    foreach ($name in $lockSet | Sort-Object) {
        if (-not $presentSet.Contains($name)) {
            continue
        }

        $dirPath = Join-Path $SkillsRoot $name
        $actual = Get-SkillDirHash -DirPath $dirPath
        $expected = $lockMap[$name]

        if ($actual.dir_hash -ne ([string]$expected.dir_hash).ToLower()) {
            $hashMismatches += [pscustomobject]@{
                skill    = $name
                expected = ([string]$expected.dir_hash).ToLower()
                actual   = $actual.dir_hash
            }
        }

        $skillMdPath = Join-Path $dirPath "SKILL.md"
        $expectedSkillMdHash = [string]$expected.skill_md_hash
        if (-not [string]::IsNullOrWhiteSpace($expectedSkillMdHash)) {
            if (-not (Test-Path -LiteralPath $skillMdPath)) {
                $skillMdMismatches += [pscustomobject]@{
                    skill    = $name
                    expected = $expectedSkillMdHash.ToLower()
                    actual   = "<missing>"
                }
            } else {
                $actualSkillMdHash = Get-NormalizedFileHash -Path $skillMdPath
                if ($actualSkillMdHash -ne $expectedSkillMdHash.ToLower()) {
                    $skillMdMismatches += [pscustomobject]@{
                        skill    = $name
                        expected = $expectedSkillMdHash.ToLower()
                        actual   = $actualSkillMdHash
                    }
                }
            }
        }
    }
}

Write-Host "=== VCO Offline Skills Gate ==="
Write-Host ("skills_root={0}" -f $SkillsRoot)
Write-Host ("required_skills={0}" -f $requiredSet.Count)
Write-Host ("canonical_required_skills={0}" -f $canonicalSkillSet.Count)
Write-Host ("present_skills={0}" -f $presentSet.Count)
Write-Host ("lock_skills={0}" -f $lockSet.Count)
Write-Host ("skip_hash={0}" -f $SkipHash.IsPresent)

$failed = $false

if ($missingRequired.Count -gt 0) {
    $failed = $true
    Write-Host ("[FAIL] missing required routed skills: {0}" -f ($missingRequired -join ", ")) -ForegroundColor Red
}

if ($missingCanonicalRequired.Count -gt 0) {
    $failed = $true
    Write-Host ("[FAIL] missing required canonical skills: {0}" -f ($missingCanonicalRequired -join ", ")) -ForegroundColor Red
}

if ($missingRequiredSkillMd.Count -gt 0) {
    $failed = $true
    Write-Host ("[FAIL] required skills missing SKILL.md: {0}" -f ($missingRequiredSkillMd -join ", ")) -ForegroundColor Red
}

if ($missingInLock.Count -gt 0) {
    $failed = $true
    Write-Host ("[FAIL] required skills missing in skills-lock: {0}" -f ($missingInLock -join ", ")) -ForegroundColor Red
}

if ($missingInSkills.Count -gt 0) {
    $failed = $true
    Write-Host ("[FAIL] skills-lock entries missing in skills root: {0}" -f ($missingInSkills -join ", ")) -ForegroundColor Red
}

if ($extraInSkills.Count -gt 0) {
    $failed = $true
    Write-Host ("[FAIL] extra skills not listed in skills-lock: {0}" -f ($extraInSkills -join ", ")) -ForegroundColor Red
}

if ($hashMismatches.Count -gt 0) {
    $failed = $true
    $preview = @($hashMismatches | Select-Object -First 10)
    foreach ($row in $preview) {
        Write-Host ("[FAIL] dir hash mismatch {0} expected={1} actual={2}" -f $row.skill, $row.expected, $row.actual) -ForegroundColor Red
    }
    if ($hashMismatches.Count -gt $preview.Count) {
        Write-Host ("[FAIL] ... {0} more hash mismatches" -f ($hashMismatches.Count - $preview.Count)) -ForegroundColor Red
    }
}

if ($skillMdMismatches.Count -gt 0) {
    $failed = $true
    $preview = @($skillMdMismatches | Select-Object -First 10)
    foreach ($row in $preview) {
        Write-Host ("[FAIL] SKILL.md hash mismatch {0} expected={1} actual={2}" -f $row.skill, $row.expected, $row.actual) -ForegroundColor Red
    }
    if ($skillMdMismatches.Count -gt $preview.Count) {
        Write-Host ("[FAIL] ... {0} more SKILL.md hash mismatches" -f ($skillMdMismatches.Count - $preview.Count)) -ForegroundColor Red
    }
}

if ($failed) {
    exit 1
}

Write-Host "[PASS] offline skill closure gate passed." -ForegroundColor Green
exit 0
