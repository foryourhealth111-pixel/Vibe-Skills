# Auto-extracted router module. Keep function bodies behavior-identical.

function Get-DialecticTaskFallbackSkill {
    param(
        [string]$TaskType,
        [string[]]$PackCandidates,
        [object]$DialecticTeamPolicy,
        [string[]]$BlockedSkills
    )

    $fallback = $null
    if ($DialecticTeamPolicy -and $DialecticTeamPolicy.fallback_skill_by_task) {
        $mapKeys = @($DialecticTeamPolicy.fallback_skill_by_task.PSObject.Properties.Name)
        if ($mapKeys -contains $TaskType) {
            $fallback = [string]$DialecticTeamPolicy.fallback_skill_by_task.$TaskType
        }
    }

    if ($fallback) {
        if ((-not $PackCandidates) -or ($PackCandidates.Count -eq 0) -or ($PackCandidates -contains $fallback)) {
            return $fallback
        }
    }

    if ($PackCandidates -and $PackCandidates.Count -gt 0) {
        foreach ($candidate in $PackCandidates) {
            $name = [string]$candidate
            if (-not $name) { continue }
            if ($BlockedSkills -and ($BlockedSkills -contains $name)) { continue }
            return $name
        }
        return [string]$PackCandidates[0]
    }

    return $fallback
}

function Get-DialecticTeamAdvice {
    param(
        [string]$PromptText,
        [string]$PromptLower,
        [string]$Grade,
        [string]$TaskType,
        [string]$RequestedCanonical,
        [string]$SelectedPackId,
        [string]$SelectedSkill,
        [string[]]$PackCandidates,
        [object]$DialecticTeamPolicy
    )

    $base = [pscustomobject]@{
        enabled = $false
        mode = "off"
        grade_applicable = $false
        task_applicable = $false
        scope_applicable = $false
        preserve_routing_assignment = $true
        explicit_requested = $false
        requested_by_prompt = $false
        requested_by_skill = $false
        explicit_matches = @()
        team_mode_allowed = $false
        should_apply_team_mode = $false
        selected_skill_is_dialectic_candidate = $false
        implicit_blocked_skills = @("dialectic", "dialectic-design")
        fallback_skill = $null
        recommended_skill = $null
        override_selected_skill = $false
        enforcement = "none"
        reason = "policy_off"
        confirm_required = $false
    }

    if (-not $DialecticTeamPolicy) {
        return $base
    }

    $enabled = $true
    if ($DialecticTeamPolicy.enabled -ne $null) {
        $enabled = [bool]$DialecticTeamPolicy.enabled
    }
    if (-not $enabled) {
        return $base
    }

    $mode = if ($DialecticTeamPolicy.mode) { [string]$DialecticTeamPolicy.mode } else { "explicit_only" }
    $preserveRoutingAssignment = if ($DialecticTeamPolicy.preserve_routing_assignment -ne $null) { [bool]$DialecticTeamPolicy.preserve_routing_assignment } else { $true }

    $gradeAllow = @("L", "XL")
    $taskAllow = @("planning", "research", "review")
    if ($DialecticTeamPolicy.scope) {
        if ($DialecticTeamPolicy.scope.grade_allow) { $gradeAllow = @($DialecticTeamPolicy.scope.grade_allow) }
        if ($DialecticTeamPolicy.scope.task_allow) { $taskAllow = @($DialecticTeamPolicy.scope.task_allow) }
    }

    $gradeApplicable = ($gradeAllow -contains $Grade)
    $taskApplicable = ($taskAllow -contains $TaskType)
    $scopeApplicable = $gradeApplicable -and $taskApplicable

    $explicitPatterns = @()
    if ($DialecticTeamPolicy.explicit_patterns) {
        $explicitPatterns = @($DialecticTeamPolicy.explicit_patterns)
    }

    $explicitMatches = @()
    foreach ($pattern in $explicitPatterns) {
        $patternText = [string]$pattern
        if (-not $patternText) { continue }
        if ($PromptLower -and $PromptLower.Contains($patternText.ToLowerInvariant())) {
            $explicitMatches += $patternText
        }
    }

    $explicitSkillIds = @("dialectic", "dialectic-design")
    if ($DialecticTeamPolicy.explicit_skill_ids) {
        $explicitSkillIds = @($DialecticTeamPolicy.explicit_skill_ids)
    }

    $requestedBySkill = $false
    if ($RequestedCanonical) {
        $requestedBySkill = ($explicitSkillIds -contains [string]$RequestedCanonical)
    }

    $requestedByPrompt = ($explicitMatches.Count -gt 0)
    $explicitRequested = $requestedByPrompt -or $requestedBySkill

    $blockedSkills = @("dialectic", "dialectic-design")
    if ($DialecticTeamPolicy.implicit_blocked_skills) {
        $blockedSkills = @($DialecticTeamPolicy.implicit_blocked_skills)
    }

    $selectedSkillIsDialectic = $false
    if ($SelectedSkill) {
        $selectedSkillIsDialectic = ($blockedSkills -contains [string]$SelectedSkill)
    }

    $fallbackSkill = Get-DialecticTaskFallbackSkill -TaskType $TaskType -PackCandidates @($PackCandidates) -DialecticTeamPolicy $DialecticTeamPolicy -BlockedSkills @($blockedSkills)

    $teamSkill = if ($DialecticTeamPolicy.team_skill) { [string]$DialecticTeamPolicy.team_skill } else { "dialectic" }
    $secondConfirm = if ($DialecticTeamPolicy.require_second_confirm -ne $null) { [bool]$DialecticTeamPolicy.require_second_confirm } else { $true }

    $recommendedSkill = $null
    $overrideSelected = $false
    $enforcement = "advisory"
    $reason = "outside_scope"
    $confirmRequired = $false
    $teamModeAllowed = $scopeApplicable
    $shouldApplyTeamMode = $false

    if (-not $scopeApplicable) {
        if ($explicitRequested) {
            $reason = "explicit_requested_outside_scope"
            $recommendedSkill = $fallbackSkill
            $overrideSelected = [bool]($selectedSkillIsDialectic -and $fallbackSkill -and ($fallbackSkill -ne $SelectedSkill))
        } else {
            $reason = "outside_scope"
        }
    } elseif ($mode -ne "explicit_only") {
        $reason = "unsupported_mode_fallback_explicit_only"
    } else {
        if ($explicitRequested) {
            $shouldApplyTeamMode = $true
            $recommendedSkill = $teamSkill
            $overrideSelected = [bool]($teamSkill -and ($teamSkill -ne $SelectedSkill))
            if ($secondConfirm) {
                $enforcement = "confirm_required"
                $confirmRequired = $true
            } else {
                $enforcement = "advisory"
            }
            $reason = "explicit_team_requested"
        } else {
            $shouldApplyTeamMode = $false
            $recommendedSkill = $fallbackSkill
            if ($selectedSkillIsDialectic -and $fallbackSkill -and ($fallbackSkill -ne $SelectedSkill)) {
                $overrideSelected = $true
                $reason = "explicit_only_block_implicit"
            } else {
                $reason = "explicit_not_requested"
            }
        }
    }

    $base.enabled = $true
    $base.mode = $mode
    $base.grade_applicable = [bool]$gradeApplicable
    $base.task_applicable = [bool]$taskApplicable
    $base.scope_applicable = [bool]$scopeApplicable
    $base.preserve_routing_assignment = [bool]$preserveRoutingAssignment
    $base.explicit_requested = [bool]$explicitRequested
    $base.requested_by_prompt = [bool]$requestedByPrompt
    $base.requested_by_skill = [bool]$requestedBySkill
    $base.explicit_matches = @($explicitMatches)
    $base.team_mode_allowed = [bool]$teamModeAllowed
    $base.should_apply_team_mode = [bool]$shouldApplyTeamMode
    $base.selected_skill_is_dialectic_candidate = [bool]$selectedSkillIsDialectic
    $base.implicit_blocked_skills = @($blockedSkills)
    $base.fallback_skill = $fallbackSkill
    $base.recommended_skill = $recommendedSkill
    $base.override_selected_skill = [bool]$overrideSelected
    $base.enforcement = $enforcement
    $base.reason = $reason
    $base.confirm_required = [bool]$confirmRequired

    return $base
}
