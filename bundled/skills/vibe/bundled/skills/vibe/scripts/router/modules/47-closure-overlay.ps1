# Auto-extracted router module. Keep function bodies behavior-identical.

function Get-ClosureKeywordCandidates {
    param(
        [string]$PromptLower,
        [int]$MaxKeywords = 3
    )

    if (-not $PromptLower) { return @() }

    $stop = @(
        "vibe", "codex", "router", "route", "pack", "skill",
        "please", "plz", "help", "need", "want", "make",
        "add", "fix", "bug", "error", "issue", "test", "debug",
        "implement", "refactor", "design", "plan", "research"
    )

    $candidates = New-Object System.Collections.Generic.List[string]

    # 1) File-like tokens (highest value)
    foreach ($m in [Regex]::Matches($PromptLower, '(?<![a-z0-9_./-])([a-z0-9_./-]+\.[a-z0-9]{1,6})(?![a-z0-9_./-])')) {
        $v = [string]$m.Groups[1].Value
        if ($v -and -not ($stop -contains $v)) { $candidates.Add($v) }
    }

    # 2) Backticked tokens
    foreach ($m in [Regex]::Matches($PromptLower, '`([^`]{2,64})`')) {
        $v = [string]$m.Groups[1].Value.Trim()
        if ($v -and -not ($stop -contains $v.ToLowerInvariant())) { $candidates.Add($v) }
    }

    # 3) Identifier-like tokens
    foreach ($m in [Regex]::Matches($PromptLower, '\b[a-z_][a-z0-9_]{2,}\b')) {
        $v = [string]$m.Value
        if ($v -and -not ($stop -contains $v)) { $candidates.Add($v) }
    }

    # 4) CJK sequences (fallback)
    foreach ($m in [Regex]::Matches($PromptLower, '[\p{IsCJKUnifiedIdeographs}]{2,}')) {
        $v = [string]$m.Value
        if ($v) { $candidates.Add($v) }
    }

    $unique = @($candidates | Where-Object { $_ } | Select-Object -Unique)
    if ($unique.Count -le 0) { return @() }

    return @($unique | Select-Object -First ([Math]::Max(1, $MaxKeywords)))
}

function New-ClosureSingleQuoted {
    param([string]$Text)
    if ($Text -eq $null) { return "''" }
    return ("'" + ([string]$Text).Replace("'", "''") + "'")
}

function New-ClosureRgFixedCommand {
    param(
        [string[]]$Keywords,
        [int]$MaxPatterns = 2
    )

    $patterns = @($Keywords | Where-Object { $_ } | Select-Object -First ([Math]::Max(1, $MaxPatterns)))
    if ($patterns.Count -eq 0) { return $null }

    $parts = @("rg", "-n", "-F")
    foreach ($p in $patterns) {
        $parts += "-e"
        $parts += (New-ClosureSingleQuoted -Text ([string]$p))
    }
    $parts += "."
    return ($parts -join " ")
}

function Get-ClosureOverlayAdvice {
    param(
        [string]$Prompt,
        [string]$PromptLower,
        [string]$Grade,
        [string]$TaskType,
        [string]$RouteMode,
        [string]$SelectedPackId,
        [string]$SelectedSkill,
        [string[]]$PackCandidates,
        [object]$ClosureOverlayPolicy,
        [object]$ExplorationAdvice
    )

    if (-not $ClosureOverlayPolicy) {
        return [pscustomobject]@{
            enabled = $false
            mode = "off"
            task_applicable = $false
            grade_applicable = $false
            route_mode_applicable = $false
            scope_applicable = $false
            enforcement = "none"
            reason = "policy_missing"
            preserve_routing_assignment = $true
            recommended_execution_mode = $null
            extracted_keywords = @()
            contract = $null
        }
    }

    $enabled = if ($ClosureOverlayPolicy.enabled -ne $null) { [bool]$ClosureOverlayPolicy.enabled } else { $true }
    $mode = if ($ClosureOverlayPolicy.mode) { [string]$ClosureOverlayPolicy.mode } else { "soft" }
    if ((-not $enabled) -or ($mode -eq "off")) {
        return [pscustomobject]@{
            enabled = $false
            mode = "off"
            task_applicable = $false
            grade_applicable = $false
            route_mode_applicable = $false
            scope_applicable = $false
            enforcement = "none"
            reason = "policy_off"
            preserve_routing_assignment = $true
            recommended_execution_mode = $null
            extracted_keywords = @()
            contract = $null
        }
    }

    $taskAllow = if ($ClosureOverlayPolicy.task_allow) { @($ClosureOverlayPolicy.task_allow) } else { @("coding", "debug", "planning", "research") }
    $gradeAllow = if ($ClosureOverlayPolicy.grade_allow) { @($ClosureOverlayPolicy.grade_allow) } else { @("M", "L", "XL") }
    $routeModeAllow = if ($ClosureOverlayPolicy.route_mode_allow) { @($ClosureOverlayPolicy.route_mode_allow) } else { @() }

    $taskApplicable = ($taskAllow -contains $TaskType)
    $gradeApplicable = ($gradeAllow -contains $Grade)
    $routeModeApplicable = $true
    if ($routeModeAllow.Count -gt 0) {
        $routeModeApplicable = ($routeModeAllow -contains $RouteMode)
    }

    $scopeApplicable = $taskApplicable -and $gradeApplicable -and $routeModeApplicable
    if (-not $scopeApplicable) {
        return [pscustomobject]@{
            enabled = $true
            mode = $mode
            task_applicable = [bool]$taskApplicable
            grade_applicable = [bool]$gradeApplicable
            route_mode_applicable = [bool]$routeModeApplicable
            scope_applicable = $false
            enforcement = "advisory"
            reason = "outside_scope"
            preserve_routing_assignment = $true
            recommended_execution_mode = $null
            extracted_keywords = @()
            contract = $null
        }
    }

    $contractCfg = if ($ClosureOverlayPolicy.contract) { $ClosureOverlayPolicy.contract } else { $null }
    $probeBudget = if ($contractCfg -and $contractCfg.probe_budget -ne $null) { [int]$contractCfg.probe_budget } else { 2 }
    $verifyBudget = if ($contractCfg -and $contractCfg.verify_budget -ne $null) { [int]$contractCfg.verify_budget } else { 1 }
    $includeRepoShapeProbe = if ($contractCfg -and $contractCfg.include_repo_shape_probe -ne $null) { [bool]$contractCfg.include_repo_shape_probe } else { $true }
    $keywordCfg = if ($contractCfg -and $contractCfg.keyword_extraction) { $contractCfg.keyword_extraction } else { $null }
    $maxKeywords = if ($keywordCfg -and $keywordCfg.max_keywords -ne $null) { [int]$keywordCfg.max_keywords } else { 3 }
    $maxRgPatterns = if ($keywordCfg -and $keywordCfg.max_rg_patterns -ne $null) { [int]$keywordCfg.max_rg_patterns } else { 2 }

    $keywords = @(Get-ClosureKeywordCandidates -PromptLower $PromptLower -MaxKeywords $maxKeywords)
    $rgCommand = New-ClosureRgFixedCommand -Keywords $keywords -MaxPatterns $maxRgPatterns
    if (-not $rgCommand) {
        $rgCommand = "rg -n --files ."
    }

    $probeSteps = @()
    if ($includeRepoShapeProbe) {
        $probeSteps += [pscustomobject]@{
            id = "probe_repo_shape"
            kind = "glob"
            description = "Probe #1 (fast): inspect repo shape (top-level files/dirs) to anchor next actions."
            commands = @(
                "Get-ChildItem -Force | Select-Object Name",
                "Get-ChildItem -Directory -Force | Select-Object Name"
            )
        }
    }

    $probeSteps += [pscustomobject]@{
        id = "probe_rg"
        kind = "rg"
        description = "Probe #2 (targeted): search the most relevant keyword(s) from the prompt."
        commands = @($rgCommand)
    }

    $probeSteps = @($probeSteps | Select-Object -First ([Math]::Max(1, $probeBudget)))

    $verifyCandidates = @()
    if ($ClosureOverlayPolicy.verify_command_candidates) {
        foreach ($c in @($ClosureOverlayPolicy.verify_command_candidates)) {
            if (-not $c) { continue }
            $verifyCandidates += [pscustomobject]@{
                id = if ($c.id) { [string]$c.id } else { "unknown" }
                when_files = if ($c.when_files) { @($c.when_files | ForEach-Object { [string]$_ }) } else { @() }
                command = if ($c.command) { [string]$c.command } else { $null }
                note = if ($c.note) { [string]$c.note } else { $null }
            }
        }
    }

    $verifySteps = @(
        [pscustomobject]@{
            id = "verify_1"
            kind = "verify"
            description = "Verify (pick the narrowest applicable): run the smallest relevant test/build command, based on probe outputs."
            candidates = @($verifyCandidates)
        }
    ) | Select-Object -First ([Math]::Max(1, $verifyBudget))

    $executionMode = $null
    if ($ExplorationAdvice -and $ExplorationAdvice.recommended_execution_mode) {
        $executionMode = [string]$ExplorationAdvice.recommended_execution_mode
    } else {
        $executionMode = if ($TaskType -in @("planning", "research")) { "analysis_first" } else { "direct_execution" }
    }

    return [pscustomobject]@{
        enabled = $true
        mode = $mode
        task_applicable = $true
        grade_applicable = $true
        route_mode_applicable = $true
        scope_applicable = $true
        enforcement = "closure_first"
        reason = "policy_enabled"
        preserve_routing_assignment = if ($ClosureOverlayPolicy.preserve_routing_assignment -ne $null) { [bool]$ClosureOverlayPolicy.preserve_routing_assignment } else { $true }
        recommended_execution_mode = $executionMode
        extracted_keywords = @($keywords)
        contract = [pscustomobject]@{
            probe_budget = [int]$probeBudget
            verify_budget = [int]$verifyBudget
            probes = @($probeSteps)
            verify = @($verifySteps)
        }
    }
}
