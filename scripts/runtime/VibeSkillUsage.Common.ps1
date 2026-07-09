Set-StrictMode -Version Latest

function Resolve-VibeSkillRootPath {
    param(
        [Parameter(Mandatory)] [string]$RawPath,
        [Parameter(Mandatory)] [string]$TargetRoot
    )

    $text = ([string]$RawPath).Trim()
    if ([string]::IsNullOrWhiteSpace($text)) {
        return $null
    }
    $targetRootPath = [System.IO.Path]::GetFullPath($TargetRoot)
    if ($text -eq '~' -or $text.StartsWith('~/') -or $text.StartsWith('~\')) {
        $homeRoot = Split-Path -Parent $targetRootPath
        $suffix = $text.Substring(1).TrimStart('/', '\')
        if ([string]::IsNullOrWhiteSpace($suffix)) {
            return [System.IO.Path]::GetFullPath($homeRoot)
        }
        return [System.IO.Path]::GetFullPath((Join-Path $homeRoot $suffix))
    }
    if ([System.IO.Path]::IsPathRooted($text)) {
        return [System.IO.Path]::GetFullPath($text)
    }
    return [System.IO.Path]::GetFullPath((Join-Path $targetRootPath $text))
}

function Get-VibeConfiguredSkillRoots {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [AllowEmptyString()] [string]$TargetRoot = '',
        [AllowEmptyString()] [string]$HostId = ''
    )

    $resolvedHostId = if (Get-Command -Name Resolve-VgoHostId -ErrorAction SilentlyContinue) {
        Resolve-VgoHostId -HostId $HostId
    } elseif ([string]::IsNullOrWhiteSpace($HostId)) {
        'codex'
    } else {
        ([string]$HostId).Trim().ToLowerInvariant()
    }
    $resolvedTargetRoot = if (Get-Command -Name Resolve-VgoTargetRoot -ErrorAction SilentlyContinue) {
        Resolve-VgoTargetRoot -TargetRoot $TargetRoot -HostId $resolvedHostId
    } elseif ([string]::IsNullOrWhiteSpace($TargetRoot)) {
        [System.IO.Path]::GetFullPath('.')
    } else {
        [System.IO.Path]::GetFullPath($TargetRoot)
    }
    $defaultSkillRoots = if ($resolvedHostId -eq 'claude-code') {
        @('~/.claude/skills')
    } else {
        @('~/.agents/skills', '~/.codex/skills')
    }
    $roots = New-Object System.Collections.Generic.List[string]
    $seen = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    $explicitSkillsRoot = [System.IO.Path]::GetFullPath((Join-Path $resolvedTargetRoot 'skills'))
    if ($seen.Add([string]$explicitSkillsRoot)) {
        $roots.Add([string]$explicitSkillsRoot) | Out-Null
    }
    foreach ($rawValue in $defaultSkillRoots) {
        $resolved = Resolve-VibeSkillRootPath -RawPath ([string]$rawValue) -TargetRoot $resolvedTargetRoot
        if ([string]::IsNullOrWhiteSpace([string]$resolved)) {
            continue
        }
        if ($seen.Add([string]$resolved)) {
            $roots.Add([string]$resolved) | Out-Null
        }
    }
    return [string[]]$roots.ToArray()
}

function Resolve-VibeSkillUsageSkillPath {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$SkillId,
        [AllowEmptyString()] [string]$TargetRoot = '',
        [AllowEmptyString()] [string]$HostId = ''
    )

    $candidates = @()
    if ([string]::Equals($SkillId, 'vibe', [System.StringComparison]::OrdinalIgnoreCase)) {
        $candidates += (Join-Path $RepoRoot 'SKILL.md')
    }
    foreach ($installedSkillsRoot in @(Get-VibeConfiguredSkillRoots -RepoRoot $RepoRoot -TargetRoot $TargetRoot -HostId $HostId)) {
        $candidates += @(
            (Join-Path $installedSkillsRoot (Join-Path $SkillId 'SKILL.md')),
            (Join-Path $installedSkillsRoot (Join-Path 'custom' (Join-Path $SkillId 'SKILL.md')))
        )
    }

    foreach ($candidate in $candidates) {
        if (-not [string]::IsNullOrWhiteSpace([string]$candidate) -and (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            return [System.IO.Path]::GetFullPath($candidate)
        }
    }
    return $null
}

function Resolve-VibeLocalSkillAuthority {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$SkillId,
        [AllowEmptyString()] [string]$NativeSkillEntrypoint = '',
        [AllowEmptyString()] [string]$TargetRoot = '',
        [AllowEmptyString()] [string]$HostId = '',
        [switch]$RequireProvidedEntrypoint
    )

    $skillIdText = ([string]$SkillId).Trim()
    if ([string]::IsNullOrWhiteSpace($skillIdText)) {
        return [pscustomobject]@{
            valid = $false
            reason = 'missing_skill_id'
            skill_id = $skillIdText
            canonical_entrypoint = $null
        }
    }
    if ($skillIdText -eq 'vibe') {
        return [pscustomobject]@{
            valid = $false
            reason = 'controller_entry_excluded'
            skill_id = $skillIdText
            canonical_entrypoint = $null
        }
    }

    $activePath = $null
    $activeSourceRoot = $null
    $activePriority = 0
    $rootIndex = 0
    foreach ($installedSkillsRoot in @(Get-VibeConfiguredSkillRoots -RepoRoot $RepoRoot -TargetRoot $TargetRoot -HostId $HostId)) {
        foreach ($candidatePath in @(
            (Join-Path $installedSkillsRoot (Join-Path $skillIdText 'SKILL.md')),
            (Join-Path $installedSkillsRoot (Join-Path 'custom' (Join-Path $skillIdText 'SKILL.md')))
        )) {
            if (Test-Path -LiteralPath $candidatePath -PathType Leaf) {
                $activePath = [System.IO.Path]::GetFullPath($candidatePath)
                $activeSourceRoot = [System.IO.Path]::GetFullPath($installedSkillsRoot)
                $activePriority = $rootIndex
                break
            }
        }
        if (-not [string]::IsNullOrWhiteSpace([string]$activePath)) {
            break
        }
        $rootIndex += 1
    }

    if ([string]::IsNullOrWhiteSpace([string]$activePath)) {
        return [pscustomobject]@{
            valid = $false
            reason = 'not_in_local_skill_index'
            skill_id = $skillIdText
            canonical_entrypoint = $null
        }
    }

    $providedPath = ''
    if (-not [string]::IsNullOrWhiteSpace([string]$NativeSkillEntrypoint)) {
        $providedPath = [System.IO.Path]::GetFullPath([string]$NativeSkillEntrypoint)
    }
    if ([string]::IsNullOrWhiteSpace($providedPath) -and $RequireProvidedEntrypoint) {
        return [pscustomobject]@{
            valid = $false
            reason = 'missing_native_entrypoint'
            skill_id = $skillIdText
            canonical_entrypoint = $activePath
            source_root = $activeSourceRoot
            source_kind = 'host_installed'
            source_priority = $activePriority
            active = $true
            duplicate_state = 'active'
        }
    }
    if (
        -not [string]::IsNullOrWhiteSpace($providedPath) -and
        -not [string]::Equals($providedPath, $activePath, [System.StringComparison]::OrdinalIgnoreCase)
    ) {
        return [pscustomobject]@{
            valid = $false
            reason = 'entrypoint_mismatch'
            skill_id = $skillIdText
            canonical_entrypoint = $activePath
            provided_entrypoint = $providedPath
            source_root = $activeSourceRoot
            source_kind = 'host_installed'
            source_priority = $activePriority
            active = $true
            duplicate_state = 'active'
        }
    }

    return [pscustomobject]@{
        valid = $true
        reason = 'ok'
        skill_id = $skillIdText
        canonical_entrypoint = $activePath
        native_skill_entrypoint = $activePath
        skill_root = [System.IO.Path]::GetFullPath((Split-Path -Parent $activePath))
        source_root = $activeSourceRoot
        source_kind = 'host_installed'
        source_priority = $activePriority
        active = $true
        duplicate_state = 'active'
    }
}

function New-VibeSkillUsageLoadedSkill {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$SkillId,
        [Parameter(Mandatory)] [string]$LoadedAtStage,
        [AllowEmptyString()] [string]$TargetRoot = '',
        [AllowEmptyString()] [string]$HostId = ''
    )

    $skillPath = Resolve-VibeSkillUsageSkillPath -RepoRoot $RepoRoot -SkillId $SkillId -TargetRoot $TargetRoot -HostId $HostId
    if ([string]::IsNullOrWhiteSpace([string]$skillPath)) {
        return [pscustomobject]@{
            skill_id = $SkillId
            skill_md_path = $null
            skill_md_sha256 = $null
            load_status = 'missing_skill_md'
            loaded_at_stage = $LoadedAtStage
            loaded_byte_count = 0
            loaded_line_count = 0
            unused_reason = 'not_loaded_full_skill_md'
        }
    }

    $content = Get-Content -LiteralPath $skillPath -Raw -Encoding UTF8
    $hash = (Get-FileHash -LiteralPath $skillPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $lines = if ([string]::IsNullOrEmpty($content)) { @() } else { @($content -split "`r?`n") }
    if (@($lines).Count -gt 0 -and [string]$lines[-1] -eq '') {
        $lines = @($lines | Select-Object -First (@($lines).Count - 1))
    }
    $lineCount = @($lines).Count
    $byteCount = [System.Text.Encoding]::UTF8.GetByteCount($content)
    return [pscustomobject]@{
        skill_id = $SkillId
        skill_md_path = [System.IO.Path]::GetFullPath($skillPath)
        skill_md_sha256 = $hash
        load_status = 'loaded_full_skill_md'
        loaded_at_stage = $LoadedAtStage
        loaded_byte_count = [int]$byteCount
        loaded_line_count = [int]$lineCount
    }
}

function New-VibeInitialSkillUsage {
    param(
        [AllowNull()] [object[]]$LoadedSkills = @(),
        [AllowNull()] [object[]]$TouchedSkills = @()
    )

    $loaded = @($LoadedSkills | Where-Object { $null -ne $_ })
    $loadedIds = @($loaded | ForEach-Object { [string]$_.skill_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    $unusedRows = New-Object System.Collections.Generic.List[object]
    $seen = @{}
    foreach ($touch in @($TouchedSkills)) {
        if ($null -eq $touch) {
            continue
        }
        $skillId = if ($touch.PSObject.Properties.Name -contains 'skill_id') { [string]$touch.skill_id } else { '' }
        if ([string]::IsNullOrWhiteSpace($skillId) -or $seen.ContainsKey($skillId)) {
            continue
        }
        $reason = if ($touch.PSObject.Properties.Name -contains 'reason' -and -not [string]::IsNullOrWhiteSpace([string]$touch.reason)) {
            [string]$touch.reason
        } elseif ($loadedIds -contains $skillId) {
            'selected_but_no_artifact_impact'
        } else {
            'candidate_only'
        }
        $unusedRows.Add([pscustomobject]@{ skill_id = $skillId; reason = $reason }) | Out-Null
        $seen[$skillId] = $true
    }

    foreach ($loadedSkill in $loaded) {
        $skillId = [string]$loadedSkill.skill_id
        if (-not [string]::IsNullOrWhiteSpace($skillId) -and -not $seen.ContainsKey($skillId)) {
            $unusedRows.Add([pscustomobject]@{ skill_id = $skillId; reason = 'selected_but_no_artifact_impact' }) | Out-Null
            $seen[$skillId] = $true
        }
    }

    return [pscustomobject]@{
        schema_version = 2
        state_model = 'binary_used_unused'
        used = @()
        unused = [object[]]$unusedRows.ToArray()
        used_skills = @()
        unused_skills = [object[]]@($unusedRows.ToArray() | ForEach-Object { [string]$_.skill_id })
        loaded_skills = [object[]]@($loaded)
        evidence = @()
        unused_reasons = [object[]]$unusedRows.ToArray()
    }
}

function Select-VibeSkillUsageRowsExceptSkill {
    param(
        [AllowNull()] [object]$Rows = $null,
        [Parameter(Mandatory)] [string]$SkillId
    )

    $selectedRows = @()
    foreach ($row in @($Rows)) {
        if ($null -eq $row) {
            continue
        }
        $rowSkillId = if ($row.PSObject.Properties.Name -contains 'skill_id') { [string]$row.skill_id } else { '' }
        if ([string]::IsNullOrWhiteSpace($rowSkillId)) {
            continue
        }
        if (-not [string]::Equals($rowSkillId, $SkillId, [System.StringComparison]::OrdinalIgnoreCase)) {
            $selectedRows += $row
        }
    }

    return [object[]]@($selectedRows)
}

function Update-VibeSkillUsageArtifactImpact {
    param(
        [Parameter(Mandatory)] [object]$SkillUsage,
        [Parameter(Mandatory)] [string]$SkillId,
        [Parameter(Mandatory)] [string]$Stage,
        [Parameter(Mandatory)] [string]$ArtifactRef,
        [Parameter(Mandatory)] [string]$ImpactSummary
    )

    $loaded = @($SkillUsage.loaded_skills)
    $loadedRecord = @($loaded | Where-Object { [string]$_.skill_id -eq $SkillId } | Select-Object -First 1)
    $usedRows = if ($SkillUsage.PSObject.Properties.Name -contains 'used' -and $null -ne $SkillUsage.used) {
        @(Select-VibeSkillUsageRowsExceptSkill -Rows $SkillUsage.used -SkillId $SkillId)
    } else {
        @()
    }
    $unusedRows = if ($SkillUsage.PSObject.Properties.Name -contains 'unused' -and $null -ne $SkillUsage.unused) {
        @(Select-VibeSkillUsageRowsExceptSkill -Rows $SkillUsage.unused -SkillId $SkillId)
    } elseif ($SkillUsage.PSObject.Properties.Name -contains 'unused_reasons' -and $null -ne $SkillUsage.unused_reasons) {
        @(Select-VibeSkillUsageRowsExceptSkill -Rows $SkillUsage.unused_reasons -SkillId $SkillId)
    } else {
        @()
    }
    $evidence = @($SkillUsage.evidence)
    $impactRecord = [pscustomobject]@{
        stage = $Stage
        artifact_path = $ArtifactRef
        impact = $ImpactSummary
    }
    $legacyEvidenceRecord = [pscustomobject]@{
        skill_id = $SkillId
        stage = $Stage
        artifact_ref = $ArtifactRef
        impact_summary = $ImpactSummary
        skill_md_path = if (@($loadedRecord).Count -gt 0) { [string]$loadedRecord[0].skill_md_path } else { $null }
        skill_md_sha256 = if (@($loadedRecord).Count -gt 0) { [string]$loadedRecord[0].skill_md_sha256 } else { $null }
    }
    $evidence += $legacyEvidenceRecord
    $usedRows += [pscustomobject]@{
        skill_id = $SkillId
        skill_md_path = if (@($loadedRecord).Count -gt 0) { [string]$loadedRecord[0].skill_md_path } else { $null }
        skill_md_sha256 = if (@($loadedRecord).Count -gt 0) { [string]$loadedRecord[0].skill_md_sha256 } else { $null }
        evidence = @($impactRecord)
    }

    return [pscustomobject]@{
        schema_version = 2
        state_model = 'binary_used_unused'
        used = [object[]]$usedRows
        unused = [object[]]$unusedRows
        used_skills = [object[]]@($usedRows | ForEach-Object { [string]$_.skill_id } | Select-Object -Unique)
        unused_skills = [object[]]@($unusedRows | ForEach-Object { [string]$_.skill_id } | Select-Object -Unique)
        loaded_skills = [object[]]$loaded
        evidence = [object[]]$evidence
        unused_reasons = [object[]]$unusedRows
    }
}

function Get-VibeSkillUsagePath {
    param(
        [Parameter(Mandatory)] [string]$SessionRoot
    )
    return [System.IO.Path]::GetFullPath((Join-Path $SessionRoot 'skill-usage.json'))
}

function Read-VibeSkillUsageArtifact {
    param(
        [Parameter(Mandatory)] [string]$SessionRoot,
        [AllowNull()] [object]$Fallback = $null
    )
    $path = Get-VibeSkillUsagePath -SessionRoot $SessionRoot
    if (Test-Path -LiteralPath $path -PathType Leaf) {
        return Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json
    }
    return $Fallback
}
