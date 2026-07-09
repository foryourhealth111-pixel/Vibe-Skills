Set-StrictMode -Version Latest

function Invoke-VibeOfflineRequiredSkillsAudit {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ScriptRoot,
        [string]$SkillsRoot = "",
        [string]$RuntimeCorePackagingPath = ""
    )

    $paths = Resolve-VibeOfflineAuditPaths -ScriptRoot $ScriptRoot -SkillsRoot $SkillsRoot -RuntimeCorePackagingPath $RuntimeCorePackagingPath
    if (-not (Test-Path -LiteralPath $paths.skills_root)) {
        throw "Skills root not found: $($paths.skills_root)"
    }
    if (-not (Test-Path -LiteralPath $paths.runtime_core_packaging_path)) {
        throw "Runtime-core packaging manifest not found: $($paths.runtime_core_packaging_path)"
    }

    $packaging = Read-VibeOfflineJsonUtf8 -Path $paths.runtime_core_packaging_path
    $requiredSet = Get-VibeOfflineManagedSkillSet -Packaging $packaging
    $presentSet = Get-VibeOfflinePresentSkillSet -SkillsRoot $paths.skills_root
    $canonicalSkillMap = Get-VibeOfflineCanonicalSkillMap -RepoRoot $paths.repo_root
    $canonicalSkillSet = New-VibeOfflineCaseInsensitiveSet
    foreach ($canonicalSkillId in @($canonicalSkillMap.Keys)) {
        [void]$canonicalSkillSet.Add([string]$canonicalSkillId)
    }

    Write-Host "=== Vibe Offline Required-Skills Audit ==="
    Write-Host ("skills_root={0}" -f $paths.skills_root)
    Write-Host ("runtime_core_packaging={0}" -f $paths.runtime_core_packaging_path)
    Write-Host ("managed_required_skills={0}" -f $requiredSet.Count)
    Write-Host ("canonical_skills={0}" -f $canonicalSkillSet.Count)
    Write-Host ("present_skills={0}" -f $presentSet.Count)

    $missingRequired = @()
    $missingCanonicalRequired = @()
    $missingRequiredSkillMd = @()

    foreach ($name in $requiredSet | Sort-Object) {
        if (-not $presentSet.Contains($name)) {
            $missingRequired += $name
        }

        if ($canonicalSkillSet.Contains($name)) {
            $canonicalSkill = $canonicalSkillMap[$name]
            $canonicalSkillMdPath = if ($null -ne $canonicalSkill) { [string]$canonicalSkill.skill_md } else { "" }
            if ([string]::IsNullOrWhiteSpace($canonicalSkillMdPath) -or -not (Test-Path -LiteralPath $canonicalSkillMdPath)) {
                $missingCanonicalRequired += $name
            }
        }

        if ($presentSet.Contains($name)) {
            $skillMdPath = Join-Path $paths.skills_root "$name\SKILL.md"
            if (-not (Test-Path -LiteralPath $skillMdPath)) {
                $missingRequiredSkillMd += $name
            }
        }
    }

    $results = @()
    $results += Assert-VibeOfflineTrue -Condition ($missingRequired.Count -eq 0) -Message "managed required skills are present"
    if ($missingRequired.Count -gt 0) {
        Write-Host ("       missing: {0}" -f ($missingRequired -join ", ")) -ForegroundColor DarkRed
    }
    $results += Assert-VibeOfflineTrue -Condition ($missingCanonicalRequired.Count -eq 0) -Message "managed canonical skills still resolve to live SKILL.md sources"
    if ($missingCanonicalRequired.Count -gt 0) {
        Write-Host ("       missing canonical: {0}" -f ($missingCanonicalRequired -join ", ")) -ForegroundColor DarkRed
    }
    $results += Assert-VibeOfflineTrue -Condition ($missingRequiredSkillMd.Count -eq 0) -Message "managed installed skills still ship SKILL.md"
    if ($missingRequiredSkillMd.Count -gt 0) {
        Write-Host ("       missing SKILL.md: {0}" -f ($missingRequiredSkillMd -join ", ")) -ForegroundColor DarkRed
    }

    return New-VibeOfflineSuiteSummary -Title "Vibe Offline Required-Skills Audit" -Assertions $results
}

function Invoke-VibeOfflineLockParityAudit {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ScriptRoot,
        [string]$SkillsRoot = "",
        [string]$RuntimeCorePackagingPath = "",
        [string]$SkillsLockPath = "",
        [switch]$RequireSkillsLock
    )

    $paths = Resolve-VibeOfflineAuditPaths -ScriptRoot $ScriptRoot -SkillsRoot $SkillsRoot -RuntimeCorePackagingPath $RuntimeCorePackagingPath -SkillsLockPath $SkillsLockPath
    if (-not (Test-Path -LiteralPath $paths.skills_root)) {
        throw "Skills root not found: $($paths.skills_root)"
    }
    if (-not (Test-Path -LiteralPath $paths.runtime_core_packaging_path)) {
        throw "Runtime-core packaging manifest not found: $($paths.runtime_core_packaging_path)"
    }

    Write-Host "=== Vibe Offline Lock-Parity Audit ==="
    $lockState = Resolve-VibeOfflineSkillsLockState -SkillsLockPath $paths.skills_lock_path -RequireSkillsLock:$RequireSkillsLock
    if (-not $lockState.available) {
        Write-Host ("skills_lock={0}" -f $paths.skills_lock_path)
        Write-Host ("[SKIP] {0}" -f $lockState.reason) -ForegroundColor Yellow
        return New-VibeOfflineSkippedSuiteSummary -Title "Vibe Offline Lock-Parity Audit" -Reason $lockState.reason
    }

    $packaging = Read-VibeOfflineJsonUtf8 -Path $paths.runtime_core_packaging_path
    $requiredSet = Get-VibeOfflineManagedSkillSet -Packaging $packaging
    $presentSet = Get-VibeOfflinePresentSkillSet -SkillsRoot $paths.skills_root
    $lockIndex = Get-VibeOfflineLockIndex -SkillsLockPath $paths.skills_lock_path

    Write-Host ("skills_root={0}" -f $paths.skills_root)
    Write-Host ("runtime_core_packaging={0}" -f $paths.runtime_core_packaging_path)
    Write-Host ("skills_lock={0}" -f $paths.skills_lock_path)
    Write-Host ("managed_required_skills={0}" -f $requiredSet.Count)
    Write-Host ("lock_skills={0}" -f $lockIndex.lock_set.Count)
    Write-Host ("present_skills={0}" -f $presentSet.Count)

    $managedInLock = @()
    foreach ($name in $lockIndex.lock_set | Sort-Object) {
        if ($requiredSet.Contains($name)) {
            $managedInLock += $name
        }
    }

    $missingInSkills = @()
    foreach ($name in $lockIndex.lock_set | Sort-Object) {
        if ($requiredSet.Contains($name)) {
            continue
        }
        if (-not $presentSet.Contains($name)) {
            $missingInSkills += $name
        }
    }

    $extraInSkills = @()
    foreach ($name in $presentSet | Sort-Object) {
        if ($requiredSet.Contains($name)) {
            continue
        }
        if (-not $lockIndex.lock_set.Contains($name)) {
            $extraInSkills += $name
        }
    }

    $results = @()
    $results += Assert-VibeOfflineTrue -Condition ($managedInLock.Count -eq 0) -Message "managed public skills are excluded from skills-lock"
    if ($managedInLock.Count -gt 0) {
        Write-Host ("       managed entries in lock: {0}" -f ($managedInLock -join ", ")) -ForegroundColor DarkRed
    }
    $results += Assert-VibeOfflineTrue -Condition ($missingInSkills.Count -eq 0) -Message "skills-lock entries still exist under the tracked skills root"
    if ($missingInSkills.Count -gt 0) {
        Write-Host ("       missing in skills root: {0}" -f ($missingInSkills -join ", ")) -ForegroundColor DarkRed
    }
    $results += Assert-VibeOfflineTrue -Condition ($extraInSkills.Count -eq 0) -Message "tracked skills root contains no unlocked extras"
    if ($extraInSkills.Count -gt 0) {
        Write-Host ("       extra skills: {0}" -f ($extraInSkills -join ", ")) -ForegroundColor DarkRed
    }

    return New-VibeOfflineSuiteSummary -Title "Vibe Offline Lock-Parity Audit" -Assertions $results
}

function Invoke-VibeOfflineHashAudit {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ScriptRoot,
        [string]$SkillsRoot = "",
        [string]$RuntimeCorePackagingPath = "",
        [string]$SkillsLockPath = "",
        [switch]$RequireSkillsLock
    )

    $paths = Resolve-VibeOfflineAuditPaths -ScriptRoot $ScriptRoot -SkillsRoot $SkillsRoot -RuntimeCorePackagingPath $RuntimeCorePackagingPath -SkillsLockPath $SkillsLockPath
    if (-not (Test-Path -LiteralPath $paths.skills_root)) {
        throw "Skills root not found: $($paths.skills_root)"
    }
    if (-not (Test-Path -LiteralPath $paths.runtime_core_packaging_path)) {
        throw "Runtime-core packaging manifest not found: $($paths.runtime_core_packaging_path)"
    }

    Write-Host "=== Vibe Offline Hash Audit ==="
    $lockState = Resolve-VibeOfflineSkillsLockState -SkillsLockPath $paths.skills_lock_path -RequireSkillsLock:$RequireSkillsLock
    if (-not $lockState.available) {
        Write-Host ("skills_lock={0}" -f $paths.skills_lock_path)
        Write-Host ("[SKIP] {0}" -f $lockState.reason) -ForegroundColor Yellow
        return New-VibeOfflineSkippedSuiteSummary -Title "Vibe Offline Hash Audit" -Reason $lockState.reason
    }

    $packaging = Read-VibeOfflineJsonUtf8 -Path $paths.runtime_core_packaging_path
    $requiredSet = Get-VibeOfflineManagedSkillSet -Packaging $packaging
    $presentSet = Get-VibeOfflinePresentSkillSet -SkillsRoot $paths.skills_root
    $lockIndex = Get-VibeOfflineLockIndex -SkillsLockPath $paths.skills_lock_path

    Write-Host ("skills_root={0}" -f $paths.skills_root)
    Write-Host ("runtime_core_packaging={0}" -f $paths.runtime_core_packaging_path)
    Write-Host ("skills_lock={0}" -f $paths.skills_lock_path)
    Write-Host ("present_skills={0}" -f $presentSet.Count)
    Write-Host ("lock_skills={0}" -f $lockIndex.lock_set.Count)

    $hashMismatches = @()
    $skillMdMismatches = @()
    foreach ($name in $lockIndex.lock_set | Sort-Object) {
        if ($requiredSet.Contains($name)) {
            continue
        }
        if (-not $presentSet.Contains($name)) {
            continue
        }

        $dirPath = Join-Path $paths.skills_root $name
        $actual = Get-VibeOfflineSkillDirHash -DirPath $dirPath
        $expected = $lockIndex.lock_map[$name]
        $expectedDirHash = ([string]$expected.dir_hash).ToLowerInvariant()
        if ($actual.dir_hash -ne $expectedDirHash) {
            $hashMismatches += [pscustomobject]@{
                skill    = $name
                expected = $expectedDirHash
                actual   = $actual.dir_hash
            }
        }

        $expectedSkillMdHash = [string]$expected.skill_md_hash
        if (-not [string]::IsNullOrWhiteSpace($expectedSkillMdHash)) {
            $skillMdPath = Join-Path $dirPath "SKILL.md"
            if (-not (Test-Path -LiteralPath $skillMdPath)) {
                $skillMdMismatches += [pscustomobject]@{
                    skill    = $name
                    expected = $expectedSkillMdHash.ToLowerInvariant()
                    actual   = "<missing>"
                }
            } else {
                $actualSkillMdHash = Get-VibeOfflineNormalizedFileHash -Path $skillMdPath
                if ($actualSkillMdHash -ne $expectedSkillMdHash.ToLowerInvariant()) {
                    $skillMdMismatches += [pscustomobject]@{
                        skill    = $name
                        expected = $expectedSkillMdHash.ToLowerInvariant()
                        actual   = $actualSkillMdHash
                    }
                }
            }
        }
    }

    $results = @()
    $results += Assert-VibeOfflineTrue -Condition ($hashMismatches.Count -eq 0) -Message "bundle directory hashes match skills-lock"
    foreach ($row in @($hashMismatches | Select-Object -First 10)) {
        Write-Host ("       dir hash mismatch {0} expected={1} actual={2}" -f $row.skill, $row.expected, $row.actual) -ForegroundColor DarkRed
    }
    if ($hashMismatches.Count -gt 10) {
        Write-Host ("       ... {0} more dir hash mismatches" -f ($hashMismatches.Count - 10)) -ForegroundColor DarkRed
    }

    $results += Assert-VibeOfflineTrue -Condition ($skillMdMismatches.Count -eq 0) -Message "SKILL.md hashes match skills-lock when declared"
    foreach ($row in @($skillMdMismatches | Select-Object -First 10)) {
        Write-Host ("       SKILL.md hash mismatch {0} expected={1} actual={2}" -f $row.skill, $row.expected, $row.actual) -ForegroundColor DarkRed
    }
    if ($skillMdMismatches.Count -gt 10) {
        Write-Host ("       ... {0} more SKILL.md hash mismatches" -f ($skillMdMismatches.Count - 10)) -ForegroundColor DarkRed
    }

    return New-VibeOfflineSuiteSummary -Title "Vibe Offline Hash Audit" -Assertions $results
}
