# Auto-extracted router module. Keep function bodies behavior-identical.

$confirmUiHelperPath = Join-Path (Split-Path $PSScriptRoot -Parent) '..\common\vibe-governance-helpers.ps1'
if (-not (Get-Command Resolve-VgoInstalledSkillsRoot -ErrorAction SilentlyContinue) -and (Test-Path -LiteralPath $confirmUiHelperPath)) {
    . $confirmUiHelperPath
}

function Get-ConfirmUiPolicyDefaults {
    return [pscustomobject]@{
        enabled = $true
        emit_on_route_modes = @("confirm_required", "pack_overlay")
        options = [pscustomobject]@{
            max_skill_options = 5
            include_descriptions = $true
            include_scores = $true
            include_pack_alternatives = $true
            max_pack_alternatives = 2
        }
        unattended = [pscustomobject]@{
            enabled = $true
            sticky = [pscustomobject]@{
                enabled = $true
                ttl_minutes = 360
            }
            prompt_triggers = [pscustomobject]@{
                enable_patterns = @(
                    "进入无人值守",
                    "开启无人值守",
                    "无人值守模式",
                    "enter\s+unattended\s+mode",
                    "enable\s+unattended",
                    "unattended\s*(on|true|1)",
                    "auto\s*-?\s*route",
                    "skip\s+confirmation",
                    "自动路由",
                    "跳过确认",
                    "无需确认"
                )
                disable_patterns = @(
                    "退出无人值守",
                    "关闭无人值守",
                    "取消无人值守",
                    "exit\s+unattended\s+mode",
                    "disable\s+unattended",
                    "unattended\s*(off|false|0)"
                )
            }
            override_route_mode = $true
            override_target_route_mode = "pack_overlay"
        }
    }
}

function Get-ConfirmUiPolicy {
    param(
        [object]$Policy
    )

    $defaults = Get-ConfirmUiPolicyDefaults
    if (-not $Policy) { return $defaults }

    $enabled = if ($Policy.enabled -ne $null) { [bool]$Policy.enabled } else { [bool]$defaults.enabled }
    $emitOnModes = if ($Policy.emit_on_route_modes) { @($Policy.emit_on_route_modes) } else { @($defaults.emit_on_route_modes) }
    $options = if ($Policy.options) { $Policy.options } else { $defaults.options }
    $unattended = if ($Policy.unattended) { $Policy.unattended } else { $defaults.unattended }

    return [pscustomobject]@{
        enabled = $enabled
        emit_on_route_modes = @($emitOnModes)
        options = [pscustomobject]@{
            max_skill_options = if ($options.max_skill_options -ne $null) { [int]$options.max_skill_options } else { [int]$defaults.options.max_skill_options }
            include_descriptions = if ($options.include_descriptions -ne $null) { [bool]$options.include_descriptions } else { [bool]$defaults.options.include_descriptions }
            include_scores = if ($options.include_scores -ne $null) { [bool]$options.include_scores } else { [bool]$defaults.options.include_scores }
            include_pack_alternatives = if ($options.include_pack_alternatives -ne $null) { [bool]$options.include_pack_alternatives } else { [bool]$defaults.options.include_pack_alternatives }
            max_pack_alternatives = if ($options.max_pack_alternatives -ne $null) { [int]$options.max_pack_alternatives } else { [int]$defaults.options.max_pack_alternatives }
        }
        unattended = [pscustomobject]@{
            enabled = if ($unattended.enabled -ne $null) { [bool]$unattended.enabled } else { [bool]$defaults.unattended.enabled }
            sticky = [pscustomobject]@{
                enabled = if ($unattended.sticky -and $unattended.sticky.enabled -ne $null) { [bool]$unattended.sticky.enabled } else { [bool]$defaults.unattended.sticky.enabled }
                ttl_minutes = if ($unattended.sticky -and $unattended.sticky.ttl_minutes -ne $null) { [int]$unattended.sticky.ttl_minutes } else { [int]$defaults.unattended.sticky.ttl_minutes }
            }
            prompt_triggers = [pscustomobject]@{
                enable_patterns = if ($unattended.prompt_triggers -and $unattended.prompt_triggers.enable_patterns) { @($unattended.prompt_triggers.enable_patterns) } else { @($defaults.unattended.prompt_triggers.enable_patterns) }
                disable_patterns = if ($unattended.prompt_triggers -and $unattended.prompt_triggers.disable_patterns) { @($unattended.prompt_triggers.disable_patterns) } else { @($defaults.unattended.prompt_triggers.disable_patterns) }
            }
            override_route_mode = if ($unattended.override_route_mode -ne $null) { [bool]$unattended.override_route_mode } else { [bool]$defaults.unattended.override_route_mode }
            override_target_route_mode = if ($unattended.override_target_route_mode) { [string]$unattended.override_target_route_mode } else { [string]$defaults.unattended.override_target_route_mode }
        }
    }
}

function Test-AnyRegexHit {
    param(
        [string]$Text,
        [string[]]$Patterns
    )

    if (-not $Text -or -not $Patterns -or $Patterns.Count -eq 0) { return $false }
    foreach ($pattern in @($Patterns)) {
        if (-not $pattern) { continue }
        try {
            if ([Regex]::IsMatch($Text, [string]$pattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)) {
                return $true
            }
        } catch {
            continue
        }
    }
    return $false
}

function Get-ConfirmUiStatePath {
    param(
        [string]$RepoRoot
    )

    $root = if ($RepoRoot) { [string]$RepoRoot } else { "" }
    if (-not $root) { return $null }
    return (Join-Path (Join-Path $root "outputs") (Join-Path "runtime" "confirm-ui-state.json"))
}

function Read-ConfirmUiState {
    param(
        [string]$RepoRoot
    )

    $path = Get-ConfirmUiStatePath -RepoRoot $RepoRoot
    if (-not $path) { return $null }
    if (-not (Test-Path -LiteralPath $path)) { return $null }

    try {
        return (Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json)
    } catch {
        return $null
    }
}

function Write-ConfirmUiState {
    param(
        [string]$RepoRoot,
        [object]$State
    )

    $path = Get-ConfirmUiStatePath -RepoRoot $RepoRoot
    if (-not $path) { return $false }

    $dir = Split-Path -Parent $path
    if (-not (Test-Path -LiteralPath $dir)) {
        $null = New-Item -ItemType Directory -Path $dir -Force
    }

    try {
        $json = $State | ConvertTo-Json -Depth 8
        $json | Set-Content -LiteralPath $path -Encoding UTF8
        return $true
    } catch {
        return $false
    }
}

function Get-UnattendedModeDecision {
    param(
        [string]$Prompt,
        [object]$ConfirmUiPolicy,
        [string]$RepoRoot,
        [bool]$UnattendedParam = $false
    )

    $policy = Get-ConfirmUiPolicy -Policy $ConfirmUiPolicy
    if (-not $policy.unattended.enabled) {
        return [pscustomobject]@{
            enabled = $false
            unattended = $false
            source = "disabled"
            sticky_active = $false
            state_path = Get-ConfirmUiStatePath -RepoRoot $RepoRoot
        }
    }

    if ($UnattendedParam) {
        return [pscustomobject]@{
            enabled = $true
            unattended = $true
            source = "param"
            sticky_active = $false
            state_path = Get-ConfirmUiStatePath -RepoRoot $RepoRoot
        }
    }

    $promptText = if ($Prompt) { [string]$Prompt } else { "" }
    $disableHit = Test-AnyRegexHit -Text $promptText -Patterns @($policy.unattended.prompt_triggers.disable_patterns)
    $enableHit = if (-not $disableHit) { Test-AnyRegexHit -Text $promptText -Patterns @($policy.unattended.prompt_triggers.enable_patterns) } else { $false }

    $stickyEnabled = [bool]($policy.unattended.sticky -and $policy.unattended.sticky.enabled)
    $ttlMinutes = if ($policy.unattended.sticky -and $policy.unattended.sticky.ttl_minutes -ne $null) { [int]$policy.unattended.sticky.ttl_minutes } else { 360 }

    if ($stickyEnabled -and ($disableHit -or $enableHit)) {
        $nowUtc = [DateTime]::UtcNow
        $expiresUtc = $nowUtc.AddMinutes($ttlMinutes)
        $newState = [pscustomobject]@{
            version = 1
            updated_at_utc = $nowUtc.ToString("o")
            unattended = [bool]$enableHit
            expires_at_utc = $expiresUtc.ToString("o")
            source = if ($disableHit) { "prompt_disable" } else { "prompt_enable" }
        }
        $null = Write-ConfirmUiState -RepoRoot $RepoRoot -State $newState
    }

    if ($disableHit) {
        return [pscustomobject]@{
            enabled = $true
            unattended = $false
            source = "prompt_disable"
            sticky_active = $false
            state_path = Get-ConfirmUiStatePath -RepoRoot $RepoRoot
        }
    }
    if ($enableHit) {
        return [pscustomobject]@{
            enabled = $true
            unattended = $true
            source = "prompt_enable"
            sticky_active = $stickyEnabled
            state_path = Get-ConfirmUiStatePath -RepoRoot $RepoRoot
        }
    }

    if ($stickyEnabled) {
        $state = Read-ConfirmUiState -RepoRoot $RepoRoot
        if ($state -and $state.unattended -ne $null -and $state.expires_at_utc) {
            try {
                $expires = [DateTime]::Parse([string]$state.expires_at_utc).ToUniversalTime()
                if ([DateTime]::UtcNow -lt $expires) {
                    return [pscustomobject]@{
                        enabled = $true
                        unattended = [bool]$state.unattended
                        source = "sticky_state"
                        sticky_active = $true
                        state_path = Get-ConfirmUiStatePath -RepoRoot $RepoRoot
                    }
                }
            } catch {
            }
        }
    }

    return [pscustomobject]@{
        enabled = $true
        unattended = $false
        source = "default"
        sticky_active = $false
        state_path = Get-ConfirmUiStatePath -RepoRoot $RepoRoot
    }
}

function Read-SkillFrontMatter {
    param(
        [string]$SkillMdPath
    )

    if (-not $SkillMdPath) { return $null }
    if (-not (Test-Path -LiteralPath $SkillMdPath)) { return $null }

    $lines = @()
    try {
        $lines = Get-Content -LiteralPath $SkillMdPath -Encoding UTF8 -TotalCount 40
    } catch {
        return $null
    }

    if (-not $lines -or $lines.Count -lt 3) { return $null }
    if ([string]$lines[0] -ne "---") { return $null }

    $end = -1
    for ($i = 1; $i -lt $lines.Count; $i++) {
        if ([string]$lines[$i] -eq "---") {
            $end = $i
            break
        }
    }
    if ($end -lt 0) { return $null }

    $map = @{}
    for ($j = 1; $j -lt $end; $j++) {
        $line = [string]$lines[$j]
        if (-not $line) { continue }
        $idx = $line.IndexOf(":")
        if ($idx -le 0) { continue }
        $k = $line.Substring(0, $idx).Trim()
        $v = $line.Substring($idx + 1).Trim()
        if ($k) { $map[$k] = $v }
    }
    return $map
}

function Resolve-SkillMdPath {
    param(
        [string]$RepoRoot,
        [string]$Skill,
        [AllowEmptyString()] [string]$TargetRoot = '',
        [AllowEmptyString()] [string]$HostId = ''
    )

    if (-not $Skill) { return $null }
    $skillId = [string]$Skill

    if ($RepoRoot) {
        $bundled = Join-Path (Join-Path (Join-Path $RepoRoot "bundled") "skills") (Join-Path $skillId "SKILL.md")
        if (Test-Path -LiteralPath $bundled) { return $bundled }
    }

    $userRoot = Resolve-VgoInstalledSkillsRoot -TargetRoot $TargetRoot -HostId $HostId
    $installed = Join-Path $userRoot (Join-Path $skillId "SKILL.md")
    if (Test-Path -LiteralPath $installed) { return $installed }

    $customInstalled = Join-Path $userRoot (Join-Path 'custom' (Join-Path $skillId 'SKILL.md'))
    if (Test-Path -LiteralPath $customInstalled) { return $customInstalled }

    return $null
}

function Get-SkillDescriptor {
    param(
        [string]$RepoRoot,
        [string]$Skill,
        [AllowEmptyString()] [string]$TargetRoot = '',
        [AllowEmptyString()] [string]$HostId = ''
    )

    $mdPath = Resolve-SkillMdPath -RepoRoot $RepoRoot -Skill $Skill -TargetRoot $TargetRoot -HostId $HostId
    $frontMatter = if ($mdPath) { Read-SkillFrontMatter -SkillMdPath $mdPath } else { $null }

    return [pscustomobject]@{
        skill = [string]$Skill
        skill_md_path = $mdPath
        name = if ($frontMatter -and $frontMatter.ContainsKey("name")) { [string]$frontMatter["name"] } else { [string]$Skill }
        description = if ($frontMatter -and $frontMatter.ContainsKey("description")) { [string]$frontMatter["description"] } else { $null }
        has_front_matter = [bool]($frontMatter -ne $null)
    }
}

function Build-ConfirmSkillOptions {
    param(
        [object]$Result,
        [object]$ConfirmUiPolicy,
        [string]$RepoRoot,
        [AllowEmptyString()] [string]$PromptText = '',
        [AllowNull()] [object]$SkillPromotionPolicy = $null,
        [AllowEmptyString()] [string]$TargetRoot = '',
        [AllowEmptyString()] [string]$HostId = ''
    )

    $policy = Get-ConfirmUiPolicy -Policy $ConfirmUiPolicy
    if (-not $policy.enabled) { return $null }
    if (-not $Result) { return $null }
    if (-not ($policy.emit_on_route_modes -contains [string]$Result.route_mode)) { return $null }
    if (-not $Result.selected) { return $null }

    $selectedPack = [string]$Result.selected.pack_id
    $selectedSkill = [string]$Result.selected.skill

    $packRow = $null
    if ($Result.ranked) {
        $packRow = @($Result.ranked | Where-Object { [string]$_.pack_id -eq $selectedPack } | Select-Object -First 1)
        if (-not $packRow) { $packRow = @($Result.ranked | Select-Object -First 1) }
    }

    $ranking = if ($packRow -and $packRow.candidate_ranking) { Get-ArraySafe -Value $packRow.candidate_ranking } else { Get-ArraySafe -Value $null }
    if ($ranking.Count -eq 0 -and $selectedSkill) {
        $ranking = @(
            [pscustomobject]@{
                skill = $selectedSkill
                score = if ($Result.selected.selection_score -ne $null) { [double]$Result.selected.selection_score } else { 0.0 }
            }
        )
    }
    $selectedRow = $null
    if ($selectedSkill) {
        $selectedRow = @($ranking | Where-Object { [string]$_.skill -eq $selectedSkill } | Select-Object -First 1)
        if (-not $selectedRow -and $packRow -and $packRow.candidate_ranking) {
            $selectedRow = @($packRow.candidate_ranking | Where-Object { [string]$_.skill -eq $selectedSkill } | Select-Object -First 1)
        }
        if (-not $selectedRow) {
            $selectedRow = [pscustomobject]@{
                skill = $selectedSkill
                score = if ($Result.selected.selection_score -ne $null) { [double]$Result.selected.selection_score } else { 0.0 }
            }
        }
    }

    $orderedRanking = @()
    $seenSkills = @{}
    if ($selectedRow) {
        $selectedRowSkill = [string]$selectedRow.skill
        if (-not [string]::IsNullOrWhiteSpace($selectedRowSkill)) {
            $orderedRanking += $selectedRow
            $seenSkills[$selectedRowSkill] = $true
        }
    }
    foreach ($row in @($ranking)) {
        $skillId = [string]$row.skill
        if ([string]::IsNullOrWhiteSpace($skillId) -or $seenSkills.ContainsKey($skillId)) {
            continue
        }
        $orderedRanking += $row
        $seenSkills[$skillId] = $true
    }
    $ranking = @($orderedRanking)

    $limit = [Math]::Max(1, [int]$policy.options.max_skill_options)
    $rows = @($ranking | Select-Object -First $limit)

    $options = @()
    $idx = 0
    foreach ($row in $rows) {
        $idx++
        $skillId = [string]$row.skill
        $desc = if ($policy.options.include_descriptions) {
            Get-SkillDescriptor -RepoRoot $RepoRoot -Skill $skillId -TargetRoot $TargetRoot -HostId $HostId
        } else {
            $null
        }
        $promotionMetadata = Get-VgoSkillPromotionMetadata `
            -Prompt $PromptText `
            -SkillMdPath $(if ($desc) { [string]$desc.skill_md_path } else { '' }) `
            -Description $(if ($desc) { [string]$desc.description } else { '' }) `
            -RequiredInputs @('bounded specialist subtask contract') `
            -ExpectedOutputs @('bounded specialist result') `
            -VerificationExpectation 'Preserve the selected skill native workflow.' `
            -PromotionPolicy $SkillPromotionPolicy

        $options += [pscustomobject]@{
            option_id = $idx
            skill = $skillId
            pack_id = if ($packRow) { [string]$packRow.pack_id } else { $selectedPack }
            is_primary = [bool]([string]::Equals($skillId, $selectedSkill, [System.StringComparison]::OrdinalIgnoreCase))
            score = if ($row.score -ne $null) { [double]$row.score } else { $null }
            keyword_score = if ($row.keyword_score -ne $null) { [double]$row.keyword_score } else { $null }
            name_score = if ($row.name_score -ne $null) { [double]$row.name_score } else { $null }
            positive_score = if ($row.positive_score -ne $null) { [double]$row.positive_score } else { $null }
            negative_score = if ($row.negative_score -ne $null) { [double]$row.negative_score } else { $null }
            canonical_for_task_hit = if ($row.canonical_for_task_hit -ne $null) { [double]$row.canonical_for_task_hit } else { $null }
            description = if ($desc) { [string]$desc.description } else { $null }
            skill_md_path = if ($desc) { [string]$desc.skill_md_path } else { $null }
            promotion_eligible = [bool]$promotionMetadata.promotion_eligible
            destructive = [bool]$promotionMetadata.destructive
            destructive_reason_codes = [object[]]@($promotionMetadata.destructive_reason_codes)
            rollback_possible = [bool]$promotionMetadata.rollback_possible
            snapshot_required = [bool]$promotionMetadata.snapshot_required
            contract_complete = [bool]$promotionMetadata.contract_complete
            recommended_promotion_action = [string]$promotionMetadata.recommended_promotion_action
        }
    }

    $routeDecisionContract = [pscustomobject]@{
        protocol_version = 'v1'
        decision_kind = 'route_selection'
        decision_context = 'routing_confirmation'
        selected_pack = $selectedPack
        primary_skill = $selectedSkill
        allowed_decision_actions = @('accept_primary', 'select_skill')
        allowed_skill_ids = @($options | ForEach-Object { [string]$_.skill } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
        options = @($options | ForEach-Object {
            [pscustomobject]@{
                option_id = if ($_.PSObject.Properties.Name -contains 'option_id') { [int]$_.option_id } else { $null }
                skill = if ($_.PSObject.Properties.Name -contains 'skill') { [string]$_.skill } else { $null }
                pack_id = if ($_.PSObject.Properties.Name -contains 'pack_id') { [string]$_.pack_id } else { $selectedPack }
                is_primary = if ($_.PSObject.Properties.Name -contains 'is_primary') { [bool]$_.is_primary } else { $false }
            }
        })
        preferred_payload = [pscustomobject]@{
            decision_kind = 'route_selection'
            decision_action = 'accept_primary'
            selected_pack = $selectedPack
            selected_skill = $selectedSkill
        }
        selection_payload_template = [pscustomobject]@{
            decision_kind = 'route_selection'
            decision_action = 'select_skill'
            selected_pack = $selectedPack
            selected_skill = '<allowed-skill>'
        }
    }

    return [pscustomobject]@{
        selected_pack = $selectedPack
        selected_skill = $selectedSkill
        options = @($options)
        route_decision_contract = $routeDecisionContract
    }
}

function Resolve-StructuredRouteDecision {
    param(
        [AllowEmptyString()] [string]$HostDecisionJson = '',
        [AllowNull()] [object]$ConfirmSkillOptions = $null
    )

    if ([string]::IsNullOrWhiteSpace($HostDecisionJson) -or -not $ConfirmSkillOptions) { return $null }

    try {
        $decision = $HostDecisionJson | ConvertFrom-Json -ErrorAction Stop
    } catch {
        throw "invalid JSON in -HostDecisionJson"
    }
    if (-not $decision -or -not $decision.PSObject) {
        throw "structured host decision must be a JSON object"
    }

    $decisionKind = ''
    if ($decision.PSObject.Properties.Name -contains 'decision_kind') {
        $decisionKind = [string]$decision.decision_kind
    }
    if ([string]::IsNullOrWhiteSpace($decisionKind)) { return $null }
    $decisionKind = $decisionKind.Trim().ToLowerInvariant()

    $decisionAction = ''
    if ($decision.PSObject.Properties.Name -contains 'decision_action') {
        $decisionAction = [string]$decision.decision_action
    }
    $decisionAction = $decisionAction.Trim().ToLowerInvariant()
    $approvalDecision = ''
    if ($decision.PSObject.Properties.Name -contains 'approval_decision') {
        $approvalDecision = [string]$decision.approval_decision
    }
    $approvalDecision = $approvalDecision.Trim().ToLowerInvariant()
    $selectedPack = ''
    if ($decision.PSObject.Properties.Name -contains 'selected_pack') {
        $selectedPack = [string]$decision.selected_pack
    }
    $requestedSkill = ''
    if ($decision.PSObject.Properties.Name -contains 'selected_skill') {
        $requestedSkill = [string]$decision.selected_skill
    }
    $requestedSkill = $requestedSkill.Trim()
    $primarySkill = [string]$ConfirmSkillOptions.selected_skill
    $currentPack = [string]$ConfirmSkillOptions.selected_pack
    $allowedSkills = @($ConfirmSkillOptions.options | ForEach-Object { [string]$_.skill } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)

    if (-not [string]::IsNullOrWhiteSpace($selectedPack) -and -not [string]::Equals($selectedPack, $currentPack, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw ('structured host route decision selected_pack `{0}` is outside the current confirm surface `{1}`' -f $selectedPack, $currentPack)
    }

    $normalizedAction = $null
    if ($decisionKind -in @('route_selection', 'routing_selection', 'routing_decision')) {
        if ($decisionAction -in @('accept_primary', 'accept_primary_route', 'accept_route', 'approve_route')) {
            $normalizedAction = 'accept_primary'
            $requestedSkill = $primarySkill
        } elseif ($decisionAction -in @('select_skill', 'select_route_skill', 'choose_skill', 'switch_skill')) {
            $normalizedAction = 'select_skill'
        } elseif (-not [string]::IsNullOrWhiteSpace($requestedSkill)) {
            $normalizedAction = 'select_skill'
        } else {
            return $null
        }
    } elseif ($decisionKind -eq 'approval_response') {
        $normalizedAction = 'accept_primary'
        $requestedSkill = $primarySkill
        $revisionAction = (
            $approvalDecision -in @('revise', 'request_changes', 'request_revise') -or
            $decisionAction -in @('revise', 'request_changes', 'request_revise', 'revise_requirement', 'revise_requirement_doc', 'revise_requirements', 'revise_plan', 'revise_execution_plan', 'revise_xl_plan')
        )
        $hasRevisionDelta = (
            ($decision.PSObject.Properties.Name -contains 'revision_delta' -and $null -ne $decision.revision_delta -and @($decision.revision_delta).Count -gt 0) -or
            ($decision.PSObject.Properties.Name -contains 'requested_changes' -and $null -ne $decision.requested_changes -and @($decision.requested_changes).Count -gt 0) -or
            ($decision.PSObject.Properties.Name -contains 'change_requests' -and $null -ne $decision.change_requests -and @($decision.change_requests).Count -gt 0)
        )
        if ($revisionAction -and $hasRevisionDelta) {
            return $null
        }
        if (
            $approvalDecision -ne 'approve' -and
            $decisionAction -notin @('approve', 'approve_requirement', 'approve_requirement_doc', 'approve_requirements', 'approve_plan', 'approve_execution_plan', 'request_execute')
        ) {
            return $null
        }
    } else {
        return $null
    }

    if ([string]::IsNullOrWhiteSpace($requestedSkill)) {
        throw "structured host route decision must include selected_skill"
    }

    $selectedOption = $ConfirmSkillOptions.options |
        Where-Object { [string]::Equals([string]$_.skill, $requestedSkill, [System.StringComparison]::OrdinalIgnoreCase) } |
        Select-Object -First 1
    if (-not $selectedOption) {
        throw ('structured host route decision selected_skill `{0}` is outside the current confirm surface' -f $requestedSkill)
    }

    if ([string]::Equals($requestedSkill, $primarySkill, [System.StringComparison]::OrdinalIgnoreCase)) {
        $normalizedAction = 'accept_primary'
    }

    return [pscustomobject]@{
        applied = $true
        decision_kind = 'route_selection'
        decision_action = $normalizedAction
        selected_pack = if ($selectedOption.PSObject.Properties.Name -contains 'pack_id') { [string]$selectedOption.pack_id } else { $currentPack }
        selected_skill = [string]$selectedOption.skill
        selected_option = $selectedOption
        allowed_skill_ids = @($allowedSkills)
    }
}

function Get-ConfirmUiClarificationQuestions {
    param(
        [object]$Result,
        [int]$MaxQuestions = 8
    )

    if (-not $Result) { return @() }
    $clarificationRequired = $false

    try {
        if ($Result.deep_discovery_advice -and [bool]$Result.deep_discovery_advice.confirm_required) {
            $clarificationRequired = $true
        }
    } catch { }

    try {
        if ($Result.llm_acceleration_advice -and [bool]$Result.llm_acceleration_advice.confirm_required) {
            $clarificationRequired = $true
        }
    } catch { }

    try {
        if ($Result.prompt_asset_boost_advice -and [bool]$Result.prompt_asset_boost_advice.confirm_required) {
            $clarificationRequired = $true
        }
    } catch { }

    if (-not $clarificationRequired) {
        return @()
    }

    $limit = [Math]::Max(1, [int]$MaxQuestions)
    $sources = @()

    try {
        if ($Result.deep_discovery_advice -and $Result.deep_discovery_advice.interview_questions) {
            $sources += ,@($Result.deep_discovery_advice.interview_questions)
        }
    } catch { }

    try {
        if ($Result.llm_acceleration_advice -and $Result.llm_acceleration_advice.confirm_questions) {
            $sources += ,@($Result.llm_acceleration_advice.confirm_questions)
        }
    } catch { }

    try {
        if ($Result.prompt_asset_boost_advice -and $Result.prompt_asset_boost_advice.confirm_questions) {
            $sources += ,@($Result.prompt_asset_boost_advice.confirm_questions)
        }
    } catch { }

    $questions = @()
    foreach ($source in @($sources)) {
        foreach ($item in @($source)) {
            $question = [string]$item
            if (-not $question) { continue }
            $question = $question.Trim()
            if (-not $question) { continue }
            if (-not ($questions -contains $question)) {
                $questions += $question
            }
            if ($questions.Count -ge $limit) {
                return @($questions)
            }
        }
    }

    return @($questions)
}

function Build-ConfirmUiText {
    param(
        [object]$ConfirmSkillOptions,
        [object]$UnattendedDecision,
        [object]$Result
    )

    if (-not $ConfirmSkillOptions -or -not $ConfirmSkillOptions.options) { return $null }
    $lines = @()
    $clarificationQuestions = @(Get-ConfirmUiClarificationQuestions -Result $Result)
    if ($Result -and [bool]$Result.hazard_alert_required -and $Result.hazard_alert) {
        $lines += [string]$Result.hazard_alert.title
        $lines += [string]$Result.hazard_alert.message
        if ($Result.hazard_alert.reason) {
            $lines += ("Trigger reason: `{0}`." -f [string]$Result.hazard_alert.reason)
        }
        if ($Result.hazard_alert.recovery_action) {
            $lines += [string]$Result.hazard_alert.recovery_action
        }
        $lines += ''
    }
    if ($clarificationQuestions.Count -gt 0) {
        $lines += "Please answer the following questions in one reply when possible:"
        $questionIndex = 0
        foreach ($question in @($clarificationQuestions)) {
            $questionIndex++
            $lines += ("Q{0}. {1}" -f $questionIndex, [string]$question)
        }
        $lines += ''
    }
    if ($Result -and [string]$Result.route_mode -eq 'confirm_required') {
        $lines += ('Routing confirmation required: current candidate pack `{0}`. Available skills:' -f [string]$ConfirmSkillOptions.selected_pack)
    } else {
        $lines += ('Routing suggested candidate skills: current primary pack `{0}`. The host may keep the default primary choice or switch to another skill:' -f [string]$ConfirmSkillOptions.selected_pack)
    }

    foreach ($opt in @($ConfirmSkillOptions.options)) {
        $desc = if ($opt.description) { [string]$opt.description } else { "" }
        $score = if ($opt.score -ne $null) { (" (score={0})" -f ([Math]::Round([double]$opt.score, 4))) } else { "" }
        if ($desc) {
            $lines += ('{0}. `{1}`{2} - {3}' -f $opt.option_id, $opt.skill, $score, $desc)
        } else {
            $lines += ('{0}. `{1}`{2}' -f $opt.option_id, $opt.skill, $score)
        }
    }

    if ($clarificationQuestions.Count -gt 0) {
        $lines += 'You can answer the questions above and select a skill in the same reply by entering an option number (for example `1`) or `$<skill>` (for example `$tdd-guide`). If you do not specify one, the host may use the current primary choice.'
    } else {
        $lines += 'Reply with an option number (for example `1`) or `$<skill>` (for example `$tdd-guide`) to choose. If you do not specify one, the host may use the current primary choice.'
    }
    $lines += "The host may translate your natural-language reply into a structured route decision. Fixed keywords are not required."
    if ($UnattendedDecision -and [bool]$UnattendedDecision.unattended) {
        $lines += ('Unattended mode is active: selection will be skipped and `{0}` will be used automatically.' -f [string]$ConfirmSkillOptions.selected_skill)
    } else {
        $lines += 'If you want unattended auto-routing, add "enter unattended mode" to this prompt or the next one.'
    }

    return ($lines -join "`n")
}
