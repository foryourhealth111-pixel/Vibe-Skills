Set-StrictMode -Version Latest

function Assert-VibeOfflineTrue {
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

function New-VibeOfflineCaseInsensitiveSet {
    return New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::OrdinalIgnoreCase)
}

function Read-VibeOfflineJsonUtf8 {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    return ([System.IO.File]::ReadAllText($Path, [System.Text.Encoding]::UTF8) | ConvertFrom-Json)
}

function Resolve-VibeOfflineAuditPaths {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ScriptRoot,
        [string]$SkillsRoot = "",
        [string]$RuntimeCorePackagingPath = "",
        [string]$SkillsLockPath = ""
    )

    $repoRoot = (Resolve-Path (Join-Path $ScriptRoot "..\..")).Path
    if ([string]::IsNullOrWhiteSpace($SkillsRoot)) {
        $SkillsRoot = Join-Path $repoRoot "skills"
    }
    if ([string]::IsNullOrWhiteSpace($RuntimeCorePackagingPath)) {
        $RuntimeCorePackagingPath = Join-Path $repoRoot "config\runtime-core-packaging.json"
    }
    if ([string]::IsNullOrWhiteSpace($SkillsLockPath)) {
        $SkillsLockPath = Join-Path $repoRoot "config\skills-lock.json"
    }

    return [pscustomobject]@{
        repo_root                  = $repoRoot
        skills_root                = $SkillsRoot
        runtime_core_packaging_path = $RuntimeCorePackagingPath
        skills_lock_path           = $SkillsLockPath
    }
}

function Resolve-VibeOfflineSkillsLockState {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SkillsLockPath,
        [switch]$RequireSkillsLock
    )

    if (Test-Path -LiteralPath $SkillsLockPath) {
        return [pscustomobject]@{
            available = $true
            path      = $SkillsLockPath
            reason    = ""
        }
    }

    $reason = "skills-lock audit requires a generated lock file; run scripts/verify/vibe-generate-skills-lock.ps1 or pass -SkillsLockPath."
    if ($RequireSkillsLock) {
        throw "Skills lock not found: $SkillsLockPath. $reason"
    }

    return [pscustomobject]@{
        available = $false
        path      = $SkillsLockPath
        reason    = $reason
    }
}

function Get-VibeOfflineBytesHash {
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [byte[]]$Bytes
    )

    $stream = [System.IO.MemoryStream]::new($Bytes)
    try {
        return (Get-FileHash -InputStream $stream -Algorithm SHA256).Hash.ToLowerInvariant()
    } finally {
        $stream.Dispose()
    }
}

function Test-VibeOfflineTextLikeFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [byte[]]$Bytes
    )

    $textExtensions = @(
        ".md", ".txt", ".json", ".ps1", ".psm1", ".sh",
        ".yml", ".yaml", ".toml", ".ini", ".cfg", ".xml",
        ".csv", ".tsv", ".js", ".ts", ".jsx", ".tsx",
        ".py", ".rb", ".go", ".rs", ".java", ".c", ".cpp", ".h", ".hpp",
        ".css", ".html", ".htm", ".sql"
    )

    $extension = [System.IO.Path]::GetExtension($Path).ToLowerInvariant()
    if ($textExtensions -contains $extension) {
        return $true
    }

    return -not ($Bytes -contains 0)
}

function Get-VibeOfflineNormalizedFileHash {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $rawBytes = [System.IO.File]::ReadAllBytes($Path)
    if (-not (Test-VibeOfflineTextLikeFile -Path $Path -Bytes $rawBytes)) {
        return Get-VibeOfflineBytesHash -Bytes $rawBytes
    }

    $text = [System.Text.Encoding]::UTF8.GetString($rawBytes)
    $normalized = $text.Replace("`r`n", "`n").Replace("`r", "`n")
    return Get-VibeOfflineBytesHash -Bytes ([System.Text.Encoding]::UTF8.GetBytes($normalized))
}

function Get-VibeOfflineSkillDirHash {
    param(
        [Parameter(Mandatory = $true)]
        [string]$DirPath
    )

    $files = @(Get-ChildItem -LiteralPath $DirPath -Recurse -File | Sort-Object FullName)
    $entries = New-Object System.Collections.Generic.List[string]
    $totalBytes = 0

    foreach ($file in $files) {
        $relative = $file.FullName.Substring($DirPath.Length + 1).Replace('\', '/')
        if (
            $relative.Equals("config/skills-lock.json", [System.StringComparison]::OrdinalIgnoreCase) -or
            $relative.EndsWith("/config/skills-lock.json", [System.StringComparison]::OrdinalIgnoreCase)
        ) {
            continue
        }

        $entries.Add(("{0}:{1}" -f $relative, (Get-VibeOfflineNormalizedFileHash -Path $file.FullName)))
        $totalBytes += $file.Length
    }

    $dirHash = Get-VibeOfflineBytesHash -Bytes ([System.Text.Encoding]::UTF8.GetBytes([string]::Join("`n", $entries)))
    return [pscustomobject]@{
        dir_hash   = $dirHash
        file_count = $files.Count
        bytes      = $totalBytes
    }
}

function Get-VibeOfflineCanonicalSkillMap {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot
    )

    $map = @{}
    $coreSkillsRoot = Join-Path $RepoRoot "core\skills"
    if (-not (Test-Path -LiteralPath $coreSkillsRoot)) {
        return $map
    }

    foreach ($dir in @(Get-ChildItem -LiteralPath $coreSkillsRoot -Force -Directory | Sort-Object Name)) {
        $skillJsonPath = Join-Path $dir.FullName "skill.json"
        if (-not (Test-Path -LiteralPath $skillJsonPath)) {
            continue
        }

        $skillJson = Read-VibeOfflineJsonUtf8 -Path $skillJsonPath
        $source = if ($skillJson.PSObject.Properties.Name -contains "source_of_truth") { $skillJson.source_of_truth } else { $null }
        $sourceKind = if ($null -ne $source -and $source.PSObject.Properties.Name -contains "kind") { [string]$source.kind } else { "" }
        $sourcePathSpec = if ($null -ne $source -and $source.PSObject.Properties.Name -contains "path") { [string]$source.path } else { "" }
        $skillId = if ($skillJson.PSObject.Properties.Name -contains "skill_id") { [string]$skillJson.skill_id } else { [string]$dir.Name }

        if ($sourceKind -ne "canonical-skill" -or [string]::IsNullOrWhiteSpace($skillId) -or [string]::IsNullOrWhiteSpace($sourcePathSpec)) {
            continue
        }

        $resolvedSourcePath = Join-Path $RepoRoot ($sourcePathSpec.Replace("/", [System.IO.Path]::DirectorySeparatorChar))
        $skillDirectory = $resolvedSourcePath
        $skillMd = $resolvedSourcePath
        if (Test-Path -LiteralPath $resolvedSourcePath -PathType Leaf) {
            $skillDirectory = Split-Path -Parent $resolvedSourcePath
            $skillMd = $resolvedSourcePath
        } else {
            $leafName = [System.IO.Path]::GetFileName($resolvedSourcePath)
            if ($leafName.Equals("SKILL.md", [System.StringComparison]::OrdinalIgnoreCase)) {
                $skillDirectory = Split-Path -Parent $resolvedSourcePath
                $skillMd = $resolvedSourcePath
            } else {
                $skillDirectory = $resolvedSourcePath
                $skillMd = Join-Path $skillDirectory "SKILL.md"
            }
        }

        $map[$skillId] = [pscustomobject]@{
            skill_id  = $skillId
            directory = $skillDirectory
            skill_md  = $skillMd
        }
    }

    return $map
}

function Get-VibeOfflineCanonicalVibeSkillName {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Packaging
    )

    $canonicalPayload = $Packaging.canonical_vibe_payload
    $targetRelpath = "skills/vibe"
    if ($null -ne $canonicalPayload -and $canonicalPayload.PSObject.Properties.Name -contains "target_relpath") {
        $candidate = [string]$canonicalPayload.target_relpath
        if (-not [string]::IsNullOrWhiteSpace($candidate)) {
            $targetRelpath = $candidate
        }
    }

    return [System.IO.Path]::GetFileName($targetRelpath)
}

function Get-VibeOfflineManagedSkillSet {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Packaging
    )

    $managedSet = New-VibeOfflineCaseInsensitiveSet
    $canonicalVibe = Get-VibeOfflineCanonicalVibeSkillName -Packaging $Packaging
    if (-not [string]::IsNullOrWhiteSpace($canonicalVibe)) {
        [void]$managedSet.Add($canonicalVibe)
    }

    $inventory = $null
    if ($Packaging.PSObject.Properties.Name -contains "managed_skill_inventory") {
        $inventory = $Packaging.managed_skill_inventory
    }

    if ($null -eq $inventory -or $null -eq $inventory.public_entry_skills) {
        $defaultProfile = ""
        if ($Packaging.PSObject.Properties.Name -contains "default_profile") {
            $defaultProfile = [string]$Packaging.default_profile
        }
        if (
            -not [string]::IsNullOrWhiteSpace($defaultProfile) -and
            $Packaging.PSObject.Properties.Name -contains "profiles" -and
            $Packaging.profiles.PSObject.Properties.Name -contains $defaultProfile
        ) {
            $selectedProfile = $Packaging.profiles.$defaultProfile
            if ($null -ne $selectedProfile -and $selectedProfile.PSObject.Properties.Name -contains "managed_skill_inventory") {
                $inventory = $selectedProfile.managed_skill_inventory
            }
        }
    }

    if ($null -eq $inventory) {
        throw "Runtime-core packaging manifest missing managed_skill_inventory contract."
    }

    foreach ($field in @("public_entry_skills", "starter_skill_names", "optional_skill_names")) {
        if ($inventory.PSObject.Properties.Name -notcontains $field) {
            continue
        }
        foreach ($name in @($inventory.$field)) {
            $candidate = [string]$name
            if (-not [string]::IsNullOrWhiteSpace($candidate)) {
                [void]$managedSet.Add($candidate)
            }
        }
    }

    Write-Output -NoEnumerate $managedSet
}

function Get-VibeOfflinePresentSkillSet {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SkillsRoot
    )

    $presentSet = New-VibeOfflineCaseInsensitiveSet
    foreach ($name in @(Get-ChildItem -LiteralPath $SkillsRoot -Force -Directory | Select-Object -ExpandProperty Name)) {
        [void]$presentSet.Add([string]$name)
    }
    Write-Output -NoEnumerate $presentSet
}

function Get-VibeOfflineLockIndex {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SkillsLockPath
    )

    $lock = Read-VibeOfflineJsonUtf8 -Path $SkillsLockPath
    $lockSet = New-VibeOfflineCaseInsensitiveSet
    $lockMap = @{}
    foreach ($item in @($lock.skills)) {
        $name = [string]$item.name
        if ([string]::IsNullOrWhiteSpace($name)) {
            continue
        }
        [void]$lockSet.Add($name)
        $lockMap[$name] = $item
    }

    return [pscustomobject]@{
        lock     = $lock
        lock_set = $lockSet
        lock_map = $lockMap
    }
}

function New-VibeOfflineSuiteSummary {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Title,
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [bool[]]$Assertions
    )

    $passed = @($Assertions | Where-Object { $_ }).Count
    $failed = @($Assertions | Where-Object { -not $_ }).Count

    Write-Host ""
    Write-Host ("=== {0} Summary ===" -f $Title)
    Write-Host ("Total assertions: {0}" -f $Assertions.Count)
    Write-Host ("Passed: {0}" -f $passed)
    Write-Host ("Failed: {0}" -f $failed)

    return [pscustomobject]@{
        title       = $Title
        total       = $Assertions.Count
        passed      = $passed
        failed      = $failed
        skipped     = $false
        skip_reason = ""
        gate_passed = ($failed -eq 0)
    }
}

function New-VibeOfflineSkippedSuiteSummary {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Title,
        [Parameter(Mandatory = $true)]
        [string]$Reason
    )

    Write-Host ""
    Write-Host ("=== {0} Summary ===" -f $Title)
    Write-Host "Total assertions: 0"
    Write-Host "Passed: 0"
    Write-Host "Failed: 0"
    Write-Host ("Skipped: {0}" -f $Reason)

    return [pscustomobject]@{
        title       = $Title
        total       = 0
        passed      = 0
        failed      = 0
        skipped     = $true
        skip_reason = $Reason
        gate_passed = $true
    }
}
