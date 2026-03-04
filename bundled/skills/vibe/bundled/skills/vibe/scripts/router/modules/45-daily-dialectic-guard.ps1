# Auto-extracted router module. Keep function bodies behavior-identical.

function Get-DailyDialecticAdvice {
    param(
        [string]$PromptText,
        [string]$PromptLower,
        [string]$Grade,
        [string]$TaskType,
        [string]$RouteMode,
        [string]$SelectedPackId,
        [string]$SelectedSkill,
        [object]$IntentContract,
        [object]$DailyDialecticPolicy,
        [object]$DialecticTeamAdvice
    )

    $base = [pscustomobject]@{
        enabled = $false
        mode = "off"
        grade_applicable = $false
        task_applicable = $false
        scope_applicable = $false
        preserve_routing_assignment = $true
        team_mode_active = $false
        sections = @("thesis", "antithesis", "synthesis")
        require_antithesis_min = 2
        require_rollback_trigger = $true
        require_verification_plan = $true
        strict_required_contract_fields = @("goal", "deliverable", "capabilities")
        contract_completeness = 0.0
        contract_missing_fields = @()
        runtime_contract = @()
        enforcement = "none"
        reason = "policy_off"
        confirm_required = $false
        should_apply_hook = $false
    }

    if (-not $DailyDialecticPolicy) {
        return $base
    }

    $enabled = $true
    if ($DailyDialecticPolicy.enabled -ne $null) {
        $enabled = [bool]$DailyDialecticPolicy.enabled
    }
    if (-not $enabled) {
        return $base
    }

    $mode = if ($DailyDialecticPolicy.mode) { [string]$DailyDialecticPolicy.mode } else { "soft" }
    $preserveRoutingAssignment = if ($DailyDialecticPolicy.preserve_routing_assignment -ne $null) { [bool]$DailyDialecticPolicy.preserve_routing_assignment } else { $true }

    $gradeAllow = @("M", "L", "XL")
    $taskAllow = @("planning", "research", "review")
    if ($DailyDialecticPolicy.scope) {
        if ($DailyDialecticPolicy.scope.grade_allow) { $gradeAllow = @($DailyDialecticPolicy.scope.grade_allow) }
        if ($DailyDialecticPolicy.scope.task_allow) { $taskAllow = @($DailyDialecticPolicy.scope.task_allow) }
    }

    $gradeApplicable = ($gradeAllow -contains $Grade)
    $taskApplicable = ($taskAllow -contains $TaskType)
    $scopeApplicable = $gradeApplicable -and $taskApplicable

    $sections = @("thesis", "antithesis", "synthesis")
    $antithesisMin = 2
    $requireRollbackTrigger = $true
    $requireVerificationPlan = $true
    if ($DailyDialecticPolicy.requirements) {
        if ($DailyDialecticPolicy.requirements.sections) { $sections = @($DailyDialecticPolicy.requirements.sections) }
        if ($DailyDialecticPolicy.requirements.require_antithesis_min -ne $null) { $antithesisMin = [int]$DailyDialecticPolicy.requirements.require_antithesis_min }
        if ($DailyDialecticPolicy.requirements.require_rollback_trigger -ne $null) { $requireRollbackTrigger = [bool]$DailyDialecticPolicy.requirements.require_rollback_trigger }
        if ($DailyDialecticPolicy.requirements.require_verification_plan -ne $null) { $requireVerificationPlan = [bool]$DailyDialecticPolicy.requirements.require_verification_plan }
    }

    $strictFields = @("goal", "deliverable", "capabilities")
    $strictMinCompleteness = 0.6
    if ($DailyDialecticPolicy.strict_confirm) {
        if ($DailyDialecticPolicy.strict_confirm.require_contract_fields) { $strictFields = @($DailyDialecticPolicy.strict_confirm.require_contract_fields) }
        if ($DailyDialecticPolicy.strict_confirm.min_intent_contract_completeness -ne $null) { $strictMinCompleteness = [double]$DailyDialecticPolicy.strict_confirm.min_intent_contract_completeness }
    }

    $contractCompleteness = if ($IntentContract -and $IntentContract.completeness -ne $null) { [double]$IntentContract.completeness } else { 0.0 }
    $contractMissingFields = if ($IntentContract -and $IntentContract.missing_fields) { @($IntentContract.missing_fields) } else { @() }

    $teamModeActive = [bool]($DialecticTeamAdvice -and $DialecticTeamAdvice.should_apply_team_mode)

    $runtimeContract = @(
        "thesis: explain proposed path and assumptions",
        ("antithesis: provide at least {0} concrete failure modes" -f $antithesisMin),
        "synthesis: provide final choice and trade-off rationale"
    )
    if ($requireRollbackTrigger) {
        $runtimeContract += "synthesis: include rollback trigger"
    }
    if ($requireVerificationPlan) {
        $runtimeContract += "synthesis: include verification plan"
    }

    $enforcement = "advisory"
    $reason = "outside_scope"
    $confirmRequired = $false
    $shouldApplyHook = $false

    if (-not $scopeApplicable) {
        $enforcement = "none"
        $reason = "outside_scope"
    } elseif ($teamModeActive) {
        $enforcement = "advisory"
        $reason = "team_mode_active"
        $shouldApplyHook = $false
    } else {
        $shouldApplyHook = $true
        if ($mode -eq "shadow") {
            $enforcement = "advisory"
            $reason = "shadow_advisory"
        } elseif ($mode -eq "strict") {
            $missingStrict = @()
            foreach ($field in $strictFields) {
                if ($contractMissingFields -contains [string]$field) {
                    $missingStrict += [string]$field
                }
            }
            if ($missingStrict.Count -gt 0 -or $contractCompleteness -lt $strictMinCompleteness) {
                $enforcement = "confirm_required"
                $reason = "strict_contract_incomplete"
                $confirmRequired = $true
            } else {
                $enforcement = "advisory"
                $reason = "strict_contract_ready"
            }
        } else {
            $enforcement = "advisory"
            $reason = "soft_always_on_guard"
        }
    }

    $base.enabled = $true
    $base.mode = $mode
    $base.grade_applicable = [bool]$gradeApplicable
    $base.task_applicable = [bool]$taskApplicable
    $base.scope_applicable = [bool]$scopeApplicable
    $base.preserve_routing_assignment = [bool]$preserveRoutingAssignment
    $base.team_mode_active = [bool]$teamModeActive
    $base.sections = @($sections)
    $base.require_antithesis_min = [int]$antithesisMin
    $base.require_rollback_trigger = [bool]$requireRollbackTrigger
    $base.require_verification_plan = [bool]$requireVerificationPlan
    $base.strict_required_contract_fields = @($strictFields)
    $base.contract_completeness = [Math]::Round([double]$contractCompleteness, 4)
    $base.contract_missing_fields = @($contractMissingFields)
    $base.runtime_contract = @($runtimeContract)
    $base.enforcement = $enforcement
    $base.reason = $reason
    $base.confirm_required = [bool]$confirmRequired
    $base.should_apply_hook = [bool]$shouldApplyHook

    return $base
}
