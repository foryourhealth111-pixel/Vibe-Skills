# Auto-extracted router module. Keep function bodies behavior-identical.

$customAdmissionHelperPath = Join-Path (Split-Path $PSScriptRoot -Parent) '..\common\vibe-governance-helpers.ps1'
if (-not (Get-Command Resolve-VgoTargetRoot -ErrorAction SilentlyContinue) -and (Test-Path -LiteralPath $customAdmissionHelperPath)) {
    . $customAdmissionHelperPath
}

function Resolve-CustomAdmissionTargetRoot {
    param(
        [AllowEmptyString()] [string]$TargetRoot = '',
        [AllowEmptyString()] [string]$HostId = ''
    )

    try {
        return Resolve-VgoTargetRoot -TargetRoot $TargetRoot -HostId $HostId
    } catch {
        return $null
    }
}

function Test-CustomAdmissionPathWithin {
    param(
        [Parameter(Mandatory)] [string]$BasePath,
        [Parameter(Mandatory)] [string]$CandidatePath
    )

    try {
        $baseFull = [System.IO.Path]::GetFullPath($BasePath)
        $candidateFull = [System.IO.Path]::GetFullPath($CandidatePath)
    } catch {
        return $false
    }

    if (-not $baseFull.EndsWith([System.IO.Path]::DirectorySeparatorChar)) {
        $baseFull += [System.IO.Path]::DirectorySeparatorChar
    }

    return $candidateFull.StartsWith($baseFull, [System.StringComparison]::OrdinalIgnoreCase)
}

function Resolve-CustomAdmissionSkillMdPath {
    param(
        [Parameter(Mandatory)] [string]$TargetRoot,
        [Parameter(Mandatory)] [string]$RelativePath
    )

    $rawPath = [System.IO.Path]::GetFullPath((Join-Path $TargetRoot $RelativePath))
    if (-not (Test-CustomAdmissionPathWithin -BasePath $TargetRoot -CandidatePath $rawPath)) {
        return $null
    }
    if ([System.IO.Path]::GetExtension($rawPath).ToLowerInvariant() -eq '.md') {
        return $rawPath
    }
    return [System.IO.Path]::GetFullPath((Join-Path $rawPath 'SKILL.md'))
}

function Get-CustomAdmissionDescription {
    param(
        [AllowEmptyString()] [string]$SkillMdPath = ''
    )

    if ([string]::IsNullOrWhiteSpace($SkillMdPath) -or -not (Test-Path -LiteralPath $SkillMdPath)) {
        return $null
    }

    $lines = @()
    try {
        $lines = Get-Content -LiteralPath $SkillMdPath -Encoding UTF8 -TotalCount 20
    } catch {
        return $null
    }

    if (-not $lines -or $lines.Count -lt 3 -or [string]$lines[0] -ne '---') {
        return $null
    }

    foreach ($line in @($lines | Select-Object -Skip 1)) {
        $trimmed = [string]$line
        if ($trimmed -eq '---') {
            break
        }
        if ($trimmed -match '^\s*description:\s*(.+?)\s*$') {
            return $Matches[1].Trim()
        }
    }

    return $null
}

function Resolve-CustomAdmissionDependencyPath {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$TargetRoot,
        [Parameter(Mandatory)] [string]$SkillId
    )

    $normalizedSkillId = Normalize-Key -InputText $SkillId
    $candidates = @(
        (Join-Path $TargetRoot (Join-Path 'skills' (Join-Path $SkillId 'SKILL.md'))),
        (Join-Path $TargetRoot (Join-Path 'skills' (Join-Path 'custom' (Join-Path $SkillId 'SKILL.md'))))
    )
    if ($normalizedSkillId -eq 'vibe') {
        $candidates += (Join-Path $RepoRoot 'SKILL.md')
    }
    $candidates += (Join-Path $RepoRoot (Join-Path 'bundled\skills' (Join-Path $SkillId 'SKILL.md')))
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return [System.IO.Path]::GetFullPath($candidate)
        }
    }
    return $null
}

function Get-CustomAdmissionTaskAllow {
    param(
        [AllowNull()] [object]$Entry
    )

    $standard = @('planning', 'coding', 'review', 'debug', 'research')
    if ($Entry -and $Entry.PSObject.Properties.Name -contains 'task_allow' -and $null -ne $Entry.task_allow) {
        $explicit = @($Entry.task_allow | ForEach-Object { Normalize-Key -InputText ([string]$_) } | Where-Object { $_ -in $standard } | Select-Object -Unique)
        if (@($explicit).Count -gt 0) {
            return @($explicit)
        }
    }

    $intentTags = if ($Entry -and $Entry.PSObject.Properties.Name -contains 'intent_tags' -and $null -ne $Entry.intent_tags) {
        @($Entry.intent_tags | ForEach-Object { Normalize-Key -InputText ([string]$_) } | Select-Object -Unique)
    } else {
        @()
    }

    $derived = @($standard | Where-Object { $intentTags -contains $_ })
    if (@($derived).Count -gt 0) {
        return @($derived)
    }

    return @($standard)
}

function Get-CustomAdmissionDispatchPhase {
    param(
        [AllowNull()] [object[]]$PreferredStages = @()
    )

    $mapping = @{
        skeleton_check = 'pre_execution'
        deep_interview = 'pre_execution'
        requirement_doc = 'pre_execution'
        xl_plan = 'pre_execution'
        plan_execute = 'in_execution'
        phase_cleanup = 'post_execution'
        pre_execution = 'pre_execution'
        in_execution = 'in_execution'
        post_execution = 'post_execution'
        verification = 'verification'
    }

    foreach ($stage in @($PreferredStages)) {
        $normalized = Normalize-Key -InputText ([string]$stage)
        if ($mapping.ContainsKey($normalized)) {
            return [string]$mapping[$normalized]
        }
    }

    return 'in_execution'
}

function Test-CustomAdmissionRouteAuthorityEligible {
    param(
        [Parameter(Mandatory)] [string]$TriggerMode,
        [AllowEmptyString()] [string]$RequestedCanonical = '',
        [Parameter(Mandatory)] [string]$SkillId
    )

    if ($TriggerMode -eq 'auto') {
        return $true
    }

    if (-not [string]::IsNullOrWhiteSpace($RequestedCanonical) -and
        [string]::Equals((Normalize-Key -InputText $RequestedCanonical), (Normalize-Key -InputText $SkillId), [System.StringComparison]::OrdinalIgnoreCase)) {
        return $true
    }

    return $false
}

function ConvertTo-CustomAdmissionCandidate {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$TargetRoot,
        [Parameter(Mandatory)] [string]$ManifestKind,
        [Parameter(Mandatory)] [object]$Entry,
        [AllowEmptyString()] [string]$RequestedCanonical = ''
    )

    $skillId = Normalize-Key -InputText ([string]$Entry.id)
    $relativePath = [string]$Entry.path
    $keywords = @($Entry.keywords | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    $intentTags = @($Entry.intent_tags | ForEach-Object { Normalize-Key -InputText ([string]$_) } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    $nonGoals = @($Entry.non_goals | ForEach-Object { Normalize-Key -InputText ([string]$_) } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    $requires = @($Entry.requires | ForEach-Object { Normalize-Key -InputText ([string]$_) } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)

    $missingFields = @()
    if ([string]::IsNullOrWhiteSpace($skillId)) { $missingFields += 'id' }
    if ([string]::IsNullOrWhiteSpace($relativePath)) { $missingFields += 'path' }
    if (@($keywords).Count -eq 0) { $missingFields += 'keywords' }
    if (@($intentTags).Count -eq 0) { $missingFields += 'intent_tags' }
    if (@($nonGoals).Count -eq 0) { $missingFields += 'non_goals' }
    if (@($requires).Count -eq 0) { $missingFields += 'requires' }
    if (@($missingFields).Count -gt 0) {
        return [pscustomobject]@{
            admitted = $false
            failure = [pscustomobject]@{
                manifest_kind = $ManifestKind
                entry_id = if ($skillId) { $skillId } else { $null }
                reason = 'missing_required_fields'
                missing_fields = @($missingFields)
            }
        }
    }

    $skillMdPath = Resolve-CustomAdmissionSkillMdPath -TargetRoot $TargetRoot -RelativePath $relativePath
    if ([string]::IsNullOrWhiteSpace($skillMdPath)) {
        return [pscustomobject]@{
            admitted = $false
            failure = [pscustomobject]@{
                manifest_kind = $ManifestKind
                entry_id = $skillId
                reason = 'path_outside_target_root'
                path = $relativePath
            }
        }
    }
    if (-not (Test-Path -LiteralPath $skillMdPath)) {
        return [pscustomobject]@{
            admitted = $false
            failure = [pscustomobject]@{
                manifest_kind = $ManifestKind
                entry_id = $skillId
                reason = 'skill_md_missing'
                path = $relativePath
                skill_md_path = $skillMdPath
            }
        }
    }

    $missingDependencies = @()
    foreach ($dependency in @($requires)) {
        if (-not (Resolve-CustomAdmissionDependencyPath -RepoRoot $RepoRoot -TargetRoot $TargetRoot -SkillId $dependency)) {
            $missingDependencies += $dependency
        }
    }
    if (@($missingDependencies).Count -gt 0) {
        return [pscustomobject]@{
            admitted = $false
            failure = [pscustomobject]@{
                manifest_kind = $ManifestKind
                entry_id = $skillId
                reason = 'custom_dependencies_missing'
                missing_dependencies = @($missingDependencies)
            }
        }
    }

    $triggerMode = Normalize-Key -InputText ([string]$Entry.trigger_mode)
    if ($triggerMode -notin @('explicit_only', 'advisory', 'auto')) {
        $triggerMode = 'advisory'
    }
    $priority = 60
    if ($Entry.PSObject.Properties.Name -contains 'priority' -and $null -ne $Entry.priority) {
        try {
            $priority = [Math]::Max(0, [Math]::Min(89, [int]$Entry.priority))
        } catch {
            $priority = 60
        }
    }
    $preferredStages = @($Entry.preferred_stages | ForEach-Object { Normalize-Key -InputText ([string]$_) } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    $taskAllow = Get-CustomAdmissionTaskAllow -Entry $Entry
    $dispatchPhase = Get-CustomAdmissionDispatchPhase -PreferredStages @($preferredStages)
    $description = Get-CustomAdmissionDescription -SkillMdPath $skillMdPath
    $routeAuthorityEligible = Test-CustomAdmissionRouteAuthorityEligible -TriggerMode $triggerMode -RequestedCanonical $RequestedCanonical -SkillId $skillId

    $customSummary = [pscustomobject]@{
        skill_id = $skillId
        manifest_kind = $ManifestKind
        pack_id = "custom-$ManifestKind-$skillId"
        trigger_mode = $triggerMode
        dispatch_phase = $dispatchPhase
        binding_profile = $ManifestKind
        lane_policy = 'bounded_native_custom_skill'
        parallelizable_in_root_xl = [bool]($Entry.PSObject.Properties.Name -contains 'parallelizable_in_root_xl' -and $Entry.parallelizable_in_root_xl)
        native_usage_required = $true
        must_preserve_workflow = $true
        route_authority_eligible = [bool]$routeAuthorityEligible
        skill_md_path = $skillMdPath
        description = $description
    }

    $candidate = [pscustomobject]@{
        skill_id = $skillId
        manifest_kind = $ManifestKind
        pack_id = "custom-$ManifestKind-$skillId"
        path = $relativePath
        skill_md_path = $skillMdPath
        description = $description
        enabled = $true
        trigger_mode = $triggerMode
        priority = $priority
        keywords = @($keywords)
        intent_tags = @($intentTags)
        non_goals = @($nonGoals)
        requires = @($requires)
        task_allow = @($taskAllow)
        preferred_stages = @($preferredStages)
        dispatch_phase = $dispatchPhase
        binding_profile = $ManifestKind
        lane_policy = 'bounded_native_custom_skill'
        parallelizable_in_root_xl = [bool]($Entry.PSObject.Properties.Name -contains 'parallelizable_in_root_xl' -and $Entry.parallelizable_in_root_xl)
        native_usage_required = $true
        must_preserve_workflow = $true
        route_authority_eligible = [bool]$routeAuthorityEligible
        pack = [pscustomobject]@{
            id = "custom-$ManifestKind-$skillId"
            priority = $priority
            grade_allow = @('M', 'L', 'XL')
            task_allow = @($taskAllow)
            trigger_keywords = @($keywords)
            skill_candidates = @($skillId)
            defaults_by_task = [pscustomobject]@{}
            custom_admission = $null
        }
    }

    foreach ($task in @($taskAllow)) {
        $candidate.pack.defaults_by_task | Add-Member -NotePropertyName $task -NotePropertyValue $skillId
    }
    $candidate.pack.custom_admission = $customSummary

    return [pscustomobject]@{
        admitted = $true
        candidate = $candidate
        failure = $null
    }
}

function Get-CustomAdmissionResult {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [AllowEmptyString()] [string]$TargetRoot = '',
        [AllowEmptyString()] [string]$HostId = '',
        [AllowEmptyString()] [string]$RequestedCanonical = ''
    )

    $resolvedTargetRoot = Resolve-CustomAdmissionTargetRoot -TargetRoot $TargetRoot -HostId $HostId
    $result = [ordered]@{
        enabled = -not [string]::IsNullOrWhiteSpace($resolvedTargetRoot)
        target_root = $resolvedTargetRoot
        manifest_paths = [pscustomobject]@{}
        manifests_present = [pscustomobject]@{}
        invalid_entries = @()
        dependency_failures = @()
        admitted_candidates = @()
        admitted_packs = @()
        skill_index = [pscustomobject]@{}
        status = 'target_root_unavailable'
    }

    if ([string]::IsNullOrWhiteSpace($resolvedTargetRoot)) {
        return [pscustomobject]$result
    }

    $manifests = @(
        [pscustomobject]@{ kind = 'workflow'; path = (Join-Path $resolvedTargetRoot 'config\custom-workflows.json'); collection = 'workflows' },
        [pscustomobject]@{ kind = 'skill'; path = (Join-Path $resolvedTargetRoot 'config\custom-skills.json'); collection = 'skills' }
    )

    foreach ($manifest in $manifests) {
        $result.manifest_paths | Add-Member -NotePropertyName $manifest.kind -NotePropertyValue ([System.IO.Path]::GetFullPath($manifest.path))
        $exists = Test-Path -LiteralPath $manifest.path
        $result.manifests_present | Add-Member -NotePropertyName $manifest.kind -NotePropertyValue ([bool]$exists)
        if (-not $exists) {
            continue
        }

        $json = $null
        try {
            $json = Get-Content -LiteralPath $manifest.path -Raw -Encoding UTF8 | ConvertFrom-Json
        } catch {
            $result.invalid_entries += [pscustomobject]@{
                manifest_kind = $manifest.kind
                entry_id = $null
                reason = 'manifest_parse_error'
                message = $_.Exception.Message
            }
            continue
        }

        $rows = if ($json.PSObject.Properties.Name -contains $manifest.collection) { @($json.$($manifest.collection)) } else { $null }
        if ($null -eq $rows) {
            $result.invalid_entries += [pscustomobject]@{
                manifest_kind = $manifest.kind
                entry_id = $null
                reason = 'manifest_missing_collection'
                expected_key = [string]$manifest.collection
            }
            continue
        }

        foreach ($entry in @($rows)) {
            if ($null -eq $entry) { continue }
            $enabled = $true
            if ($entry.PSObject.Properties.Name -contains 'enabled' -and $null -ne $entry.enabled) {
                $enabled = [bool]$entry.enabled
            }
            if (-not $enabled) { continue }

            $conversion = ConvertTo-CustomAdmissionCandidate `
                -RepoRoot $RepoRoot `
                -TargetRoot $resolvedTargetRoot `
                -ManifestKind ([string]$manifest.kind) `
                -Entry $entry `
                -RequestedCanonical $RequestedCanonical
            if (-not [bool]$conversion.admitted) {
                if ($conversion.failure.reason -eq 'custom_dependencies_missing') {
                    $result.dependency_failures += $conversion.failure
                } else {
                    $result.invalid_entries += $conversion.failure
                }
                continue
            }

            $candidate = $conversion.candidate
            $result.admitted_candidates += $candidate
            $result.admitted_packs += $candidate.pack
            $result.skill_index | Add-Member -NotePropertyName $candidate.skill_id -NotePropertyValue $candidate
        }
    }

    if (@($result.invalid_entries).Count -gt 0) {
        $result.status = 'custom_manifest_invalid'
    } elseif (@($result.dependency_failures).Count -gt 0) {
        $result.status = 'custom_dependencies_missing'
    } elseif (@($result.admitted_candidates).Count -gt 0) {
        $result.status = 'admitted'
    } else {
        $result.status = 'no_custom_manifests'
    }

    return [pscustomobject]$result
}
