param(
    [Parameter(Mandatory = $true)]
    [string]$Prompt,
    [ValidateSet("M", "L", "XL")]
    [string]$Grade = "M",
    [ValidateSet("planning", "coding", "review", "debug", "research")]
    [string]$TaskType = "planning",
    [string]$RequestedSkill,
    [switch]$Probe,
    [string]$ProbeLabel,
    [string]$ProbeOutputDir,
    [switch]$ProbeIncludePrompt,
    [int]$ProbePromptMaxChars = 1600
)

$ErrorActionPreference = "Stop"
$routerModuleRoot = Join-Path $PSScriptRoot "modules"
$routerModules = @(
    "00-core-utils.ps1",
    "10-observability.ps1",
    "11-route-probe.ps1",
    "12-heartbeat.ps1",
    "20-routing-rules.ps1",
    "21-capability-interview.ps1",
    "22-intent-contract.ps1",
    "30-openspec.ps1",
    "31-gsd-overlay.ps1",
    "32-prompt-overlay.ps1",
    "33-memory-governance.ps1",
    "34-data-scale-overlay.ps1",
    "35-quality-debt-overlay.ps1",
    "36-framework-interop-overlay.ps1",
    "37-ml-lifecycle-overlay.ps1",
    "38-python-clean-code-overlay.ps1",
    "39-system-design-overlay.ps1",
    "40-cuda-kernel-overlay.ps1",
    "41-candidate-selection.ps1",
    "42-ai-rerank-overlay.ps1"
)

foreach ($routerModule in $routerModules) {
    $routerModulePath = Join-Path $routerModuleRoot $routerModule
    if (-not (Test-Path -LiteralPath $routerModulePath)) {
        throw "Router module missing: $routerModulePath"
    }
    . $routerModulePath
}
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$configRoot = Join-Path $repoRoot "config"

$packManifestPath = Join-Path $configRoot "pack-manifest.json"
$aliasMapPath = Join-Path $configRoot "skill-alias-map.json"
$thresholdPath = Join-Path $configRoot "router-thresholds.json"
$skillKeywordIndexPath = Join-Path $configRoot "skill-keyword-index.json"
$routingRulesPath = Join-Path $configRoot "skill-routing-rules.json"
$openSpecPolicyPath = Join-Path $configRoot "openspec-policy.json"
$gsdOverlayPolicyPath = Join-Path $configRoot "gsd-overlay.json"
$promptOverlayPolicyPath = Join-Path $configRoot "prompt-overlay.json"
$memoryGovernancePolicyPath = Join-Path $configRoot "memory-governance.json"
$dataScaleOverlayPolicyPath = Join-Path $configRoot "data-scale-overlay.json"
$qualityDebtOverlayPolicyPath = Join-Path $configRoot "quality-debt-overlay.json"
$frameworkInteropOverlayPolicyPath = Join-Path $configRoot "framework-interop-overlay.json"
$mlLifecycleOverlayPolicyPath = Join-Path $configRoot "ml-lifecycle-overlay.json"
$pythonCleanCodeOverlayPolicyPath = Join-Path $configRoot "python-clean-code-overlay.json"
$systemDesignOverlayPolicyPath = Join-Path $configRoot "system-design-overlay.json"
$cudaKernelOverlayPolicyPath = Join-Path $configRoot "cuda-kernel-overlay.json"
$observabilityPolicyPath = Join-Path $configRoot "observability-policy.json"
$heartbeatPolicyPath = Join-Path $configRoot "heartbeat-policy.json"
$aiRerankPolicyPath = Join-Path $configRoot "ai-rerank-policy.json"
$probePolicyPath = Join-Path $configRoot "router-probe-policy.json"
$deepDiscoveryPolicyPath = Join-Path $configRoot "deep-discovery-policy.json"
$capabilityCatalogPath = Join-Path $configRoot "capability-catalog.json"

$packManifest = Get-Content -LiteralPath $packManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$aliasMap = Get-Content -LiteralPath $aliasMapPath -Raw -Encoding UTF8 | ConvertFrom-Json
$thresholds = Get-Content -LiteralPath $thresholdPath -Raw -Encoding UTF8 | ConvertFrom-Json
$skillKeywordIndex = if (Test-Path -LiteralPath $skillKeywordIndexPath) {
    Get-Content -LiteralPath $skillKeywordIndexPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}
$routingRules = if (Test-Path -LiteralPath $routingRulesPath) {
    Get-Content -LiteralPath $routingRulesPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}
$openSpecPolicy = if (Test-Path -LiteralPath $openSpecPolicyPath) {
    Get-Content -LiteralPath $openSpecPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}
$gsdOverlayPolicy = if (Test-Path -LiteralPath $gsdOverlayPolicyPath) {
    Get-Content -LiteralPath $gsdOverlayPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}
$promptOverlayPolicy = if (Test-Path -LiteralPath $promptOverlayPolicyPath) {
    Get-Content -LiteralPath $promptOverlayPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}
$memoryGovernancePolicy = if (Test-Path -LiteralPath $memoryGovernancePolicyPath) {
    Get-Content -LiteralPath $memoryGovernancePolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}
$dataScaleOverlayPolicy = if (Test-Path -LiteralPath $dataScaleOverlayPolicyPath) {
    Get-Content -LiteralPath $dataScaleOverlayPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}
$qualityDebtOverlayPolicy = if (Test-Path -LiteralPath $qualityDebtOverlayPolicyPath) {
    Get-Content -LiteralPath $qualityDebtOverlayPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}
$frameworkInteropOverlayPolicy = if (Test-Path -LiteralPath $frameworkInteropOverlayPolicyPath) {
    Get-Content -LiteralPath $frameworkInteropOverlayPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}
$mlLifecycleOverlayPolicy = if (Test-Path -LiteralPath $mlLifecycleOverlayPolicyPath) {
    Get-Content -LiteralPath $mlLifecycleOverlayPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}
$pythonCleanCodeOverlayPolicy = if (Test-Path -LiteralPath $pythonCleanCodeOverlayPolicyPath) {
    Get-Content -LiteralPath $pythonCleanCodeOverlayPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}
$systemDesignOverlayPolicy = if (Test-Path -LiteralPath $systemDesignOverlayPolicyPath) {
    Get-Content -LiteralPath $systemDesignOverlayPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}
$cudaKernelOverlayPolicy = if (Test-Path -LiteralPath $cudaKernelOverlayPolicyPath) {
    Get-Content -LiteralPath $cudaKernelOverlayPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}
$observabilityPolicy = if (Test-Path -LiteralPath $observabilityPolicyPath) {
    try {
        Get-Content -LiteralPath $observabilityPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        $null
    }
} else {
    $null
}
$heartbeatPolicy = if (Test-Path -LiteralPath $heartbeatPolicyPath) {
    try {
        Get-Content -LiteralPath $heartbeatPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        $null
    }
} else {
    $null
}
$aiRerankPolicy = if (Test-Path -LiteralPath $aiRerankPolicyPath) {
    try {
        Get-Content -LiteralPath $aiRerankPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        $null
    }
} else {
    $null
}
$probePolicy = if (Test-Path -LiteralPath $probePolicyPath) {
    try {
        Get-Content -LiteralPath $probePolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        $null
    }
} else {
    $null
}
$deepDiscoveryPolicy = if (Test-Path -LiteralPath $deepDiscoveryPolicyPath) {
    try {
        Get-Content -LiteralPath $deepDiscoveryPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        $null
    }
} else {
    $null
}
$capabilityCatalog = if (Test-Path -LiteralPath $capabilityCatalogPath) {
    try {
        Get-Content -LiteralPath $capabilityCatalogPath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        $null
    }
} else {
    $null
}

$weights = $thresholds.weights
$rules = $thresholds.safety
$th = $thresholds.thresholds
$weightSkillSignal = if ($weights.skill_keyword_signal -ne $null) { [double]$weights.skill_keyword_signal } else { 0.25 }
$candidateSelectionConfig = if ($thresholds.candidate_selection) { $thresholds.candidate_selection } else { $null }
$minTopGap = if ($th.min_top1_top2_gap -ne $null) { [double]$th.min_top1_top2_gap } else { 0.0 }
$minCandidateSignalForConfirmOverride = if ($th.min_candidate_signal_for_confirm_override -ne $null) { [double]$th.min_candidate_signal_for_confirm_override } else { 0.0 }

$probeContext = New-RouteProbeContext `
    -ProbeSwitch:$Probe `
    -PromptText $Prompt `
    -Grade $Grade `
    -TaskType $TaskType `
    -RepoRoot $repoRoot `
    -ProbeLabel $ProbeLabel `
    -ProbeOutputDir $ProbeOutputDir `
    -ProbeIncludePrompt:$ProbeIncludePrompt `
    -ProbePromptMaxChars $ProbePromptMaxChars `
    -ProbePolicy $probePolicy

$heartbeatContext = New-HeartbeatContext -HeartbeatPolicy $heartbeatPolicy -Grade $Grade -TaskType $TaskType

Add-RouteProbeEvent -Context $probeContext -Stage "router.init" -Note "router modules loaded" -Data @{
    module_count = $routerModules.Count
    modules = @($routerModules)
    config_root = $configRoot
    probe_policy_loaded = [bool]$probePolicy
}
$null = Add-HeartbeatPulse -Context $heartbeatContext -Stage "router.init" -Phase "router.init" -Note "router modules loaded" -Data @{
    module_count = $routerModules.Count
}

Add-RouteProbeEvent -Context $probeContext -Stage "router.config" -Note "core router and overlay policies loaded" -Data @{
    thresholds = @{
        auto_route = [double]$th.auto_route
        confirm_required = [double]$th.confirm_required
        fallback_to_legacy_below = [double]$th.fallback_to_legacy_below
        min_top1_top2_gap = [double]$minTopGap
    }
    policies = @{
        openspec_mode = if ($openSpecPolicy -and $openSpecPolicy.mode) { [string]$openSpecPolicy.mode } else { "off" }
        gsd_mode = if ($gsdOverlayPolicy -and $gsdOverlayPolicy.mode) { [string]$gsdOverlayPolicy.mode } else { "off" }
        prompt_mode = if ($promptOverlayPolicy -and $promptOverlayPolicy.mode) { [string]$promptOverlayPolicy.mode } else { "off" }
        memory_mode = if ($memoryGovernancePolicy -and $memoryGovernancePolicy.mode) { [string]$memoryGovernancePolicy.mode } else { "off" }
        data_scale_mode = if ($dataScaleOverlayPolicy -and $dataScaleOverlayPolicy.mode) { [string]$dataScaleOverlayPolicy.mode } else { "off" }
        quality_debt_mode = if ($qualityDebtOverlayPolicy -and $qualityDebtOverlayPolicy.mode) { [string]$qualityDebtOverlayPolicy.mode } else { "off" }
        framework_interop_mode = if ($frameworkInteropOverlayPolicy -and $frameworkInteropOverlayPolicy.mode) { [string]$frameworkInteropOverlayPolicy.mode } else { "off" }
        ml_lifecycle_mode = if ($mlLifecycleOverlayPolicy -and $mlLifecycleOverlayPolicy.mode) { [string]$mlLifecycleOverlayPolicy.mode } else { "off" }
        python_clean_code_mode = if ($pythonCleanCodeOverlayPolicy -and $pythonCleanCodeOverlayPolicy.mode) { [string]$pythonCleanCodeOverlayPolicy.mode } else { "off" }
        system_design_mode = if ($systemDesignOverlayPolicy -and $systemDesignOverlayPolicy.mode) { [string]$systemDesignOverlayPolicy.mode } else { "off" }
        cuda_kernel_mode = if ($cudaKernelOverlayPolicy -and $cudaKernelOverlayPolicy.mode) { [string]$cudaKernelOverlayPolicy.mode } else { "off" }
        ai_rerank_mode = if ($aiRerankPolicy -and $aiRerankPolicy.mode) { [string]$aiRerankPolicy.mode } else { "off" }
        observability_mode = if ($observabilityPolicy -and $observabilityPolicy.mode) { [string]$observabilityPolicy.mode } else { "off" }
        heartbeat_mode = if ($heartbeatPolicy -and $heartbeatPolicy.mode) { [string]$heartbeatPolicy.mode } else { "off" }
        deep_discovery_mode = if ($deepDiscoveryPolicy -and $deepDiscoveryPolicy.mode) { [string]$deepDiscoveryPolicy.mode } else { "off" }
    }
}
$null = Add-HeartbeatPulse -Context $heartbeatContext -Stage "router.config" -Phase "router.config" -Note "router config and policy load completed"

$aliasResult = Resolve-Alias -Skill $RequestedSkill -AliasMap $aliasMap
$requestedCanonical = [string]$aliasResult.canonical
$promptNormalization = Get-RoutingPromptNormalization -PromptText $Prompt
$promptLower = [string]$promptNormalization.normalized_lower
$openSpecAdvice = Get-OpenSpecGovernanceAdvice -PromptLower $promptLower -Grade $Grade -TaskType $TaskType -RequestedCanonical $requestedCanonical -OpenSpecPolicy $openSpecPolicy
$gsdOverlayAdvice = Get-GsdOverlayAdvice -PromptLower $promptLower -Grade $Grade -TaskType $TaskType -GsdOverlayPolicy $gsdOverlayPolicy
$promptOverlayAdvice = Get-PromptOverlayAdvice -PromptLower $promptLower -Grade $Grade -TaskType $TaskType -PromptOverlayPolicy $promptOverlayPolicy
$memoryGovernanceAdvice = Get-MemoryGovernanceAdvice -Grade $Grade -TaskType $TaskType -MemoryGovernancePolicy $memoryGovernancePolicy

Add-RouteProbeEvent -Context $probeContext -Stage "router.prepack" -Note "base advice prepared before pack scoring" -Data @{
    alias = $aliasResult
    requested_canonical = $requestedCanonical
    prompt_language_mix = (Get-LanguageMixTag -PromptText $Prompt)
    prompt_normalization = @{
        prefix_detected = [bool]$promptNormalization.prefix_detected
        prefix_token = if ($promptNormalization.prefix_token) { [string]$promptNormalization.prefix_token } else { $null }
        changed = [bool]$promptNormalization.changed
        normalized_length = if ($promptNormalization.normalized) { ([string]$promptNormalization.normalized).Length } else { 0 }
        normalized_hash = Get-HashHex -InputText ([string]$promptNormalization.normalized)
    }
    base_advice = @{
        openspec = Get-RouteProbeAdviceSummary -Advice $openSpecAdvice
        gsd = Get-RouteProbeAdviceSummary -Advice $gsdOverlayAdvice
        prompt = Get-RouteProbeAdviceSummary -Advice $promptOverlayAdvice
        memory = Get-RouteProbeAdviceSummary -Advice $memoryGovernanceAdvice
    }
}
$null = Add-HeartbeatPulse -Context $heartbeatContext -Stage "router.prepack" -Phase "router.prepack" -Note "base route advice prepared"

$deepDiscoveryAdvice = Get-DeepDiscoveryInterviewAdvice `
    -PromptText $Prompt `
    -PromptLower $promptLower `
    -Grade $Grade `
    -TaskType $TaskType `
    -DeepDiscoveryPolicy $deepDiscoveryPolicy `
    -CapabilityCatalog $capabilityCatalog

Add-RouteProbeEvent -Context $probeContext -Stage "deep_discovery.trigger" -Note "deep discovery trigger evaluated" -Data @{
    advice = Get-RouteProbeAdviceSummary -Advice $deepDiscoveryAdvice
    capability_hits = if ($deepDiscoveryAdvice -and $deepDiscoveryAdvice.capability_hits) {
        @($deepDiscoveryAdvice.capability_hits | Select-Object -First 6 | ForEach-Object {
            [pscustomobject]@{
                capability_id = [string]$_.capability_id
                score = [double]$_.score
                matched_keywords = @($_.matched_keywords | Select-Object -First 5)
            }
        })
    } else {
        @()
    }
}
$null = Add-HeartbeatPulse -Context $heartbeatContext -Stage "deep_discovery.trigger" -Phase "deep_discovery" -Note "deep discovery trigger evaluated" -Data @{
    trigger_active = [bool]($deepDiscoveryAdvice -and $deepDiscoveryAdvice.trigger_active)
    confirm_required = [bool]($deepDiscoveryAdvice -and $deepDiscoveryAdvice.confirm_required)
}

Add-RouteProbeEvent -Context $probeContext -Stage "deep_discovery.interview" -Note "deep discovery interview advice prepared" -Data @{
    interview_required = [bool]($deepDiscoveryAdvice -and $deepDiscoveryAdvice.interview_required)
    confirm_required = [bool]($deepDiscoveryAdvice -and $deepDiscoveryAdvice.confirm_required)
    questions = if ($deepDiscoveryAdvice -and $deepDiscoveryAdvice.interview_questions) { @($deepDiscoveryAdvice.interview_questions) } else { @() }
}
$null = Add-HeartbeatPulse -Context $heartbeatContext -Stage "deep_discovery.interview" -Phase "deep_discovery" -Note "deep discovery interview advice prepared"

$intentContract = Get-DeepDiscoveryIntentContract `
    -PromptText $Prompt `
    -PromptLower $promptLower `
    -DeepDiscoveryAdvice $deepDiscoveryAdvice `
    -DeepDiscoveryPolicy $deepDiscoveryPolicy `
    -CapabilityCatalog $capabilityCatalog

Add-RouteProbeEvent -Context $probeContext -Stage "deep_discovery.contract" -Note "intent contract synthesized from prompt and capability signals" -Data @{
    completeness = if ($intentContract) { [double]$intentContract.completeness } else { 0.0 }
    deliverable = if ($intentContract) { [string]$intentContract.deliverable } else { "unknown" }
    execution_mode = if ($intentContract) { [string]$intentContract.execution_mode } else { "unspecified" }
    missing_fields = if ($intentContract) { @($intentContract.missing_fields) } else { @("goal", "deliverable", "constraints", "capabilities") }
    capabilities = if ($intentContract) { @($intentContract.capabilities) } else { @() }
}
$null = Add-HeartbeatPulse -Context $heartbeatContext -Stage "deep_discovery.contract" -Phase "deep_discovery" -Note "intent contract synthesized"

$deepDiscoveryFilter = Get-DeepDiscoveryCandidateFilter `
    -Packs @($packManifest.packs) `
    -IntentContract $intentContract `
    -DeepDiscoveryAdvice $deepDiscoveryAdvice `
    -DeepDiscoveryPolicy $deepDiscoveryPolicy `
    -TaskType $TaskType
$deepDiscoveryFilterSummary = Get-DeepDiscoveryFilterSummary -DeepDiscoveryFilter $deepDiscoveryFilter

Add-RouteProbeEvent -Context $probeContext -Stage "deep_discovery.filter" -Note "deep discovery candidate filter evaluated" -Data $deepDiscoveryFilterSummary
$null = Add-HeartbeatPulse -Context $heartbeatContext -Stage "deep_discovery.filter" -Phase "deep_discovery" -Note "candidate filter evaluated" -Data @{
    route_filter_applied = [bool]($deepDiscoveryFilter -and $deepDiscoveryFilter.route_filter_applied)
}

$packsForScoring = if ($deepDiscoveryFilter -and $deepDiscoveryFilter.route_filter_applied -and $deepDiscoveryFilter.filtered_packs -and @($deepDiscoveryFilter.filtered_packs).Count -gt 0) {
    @($deepDiscoveryFilter.filtered_packs)
} else {
    @($packManifest.packs)
}

$packResults = @()
foreach ($pack in $packsForScoring) {
    $gradeAllowed = ($pack.grade_allow -contains $Grade)
    $taskAllowed = ($pack.task_allow -contains $TaskType)

    if ($rules.enforce_grade_boundary -and -not $gradeAllowed) { continue }
    if ($rules.enforce_task_boundary -and -not $taskAllowed) { continue }

    $intent = Get-IntentScore -PromptLower $promptLower -PackId $pack.id -Candidates $pack.skill_candidates
    $trigger = Get-TriggerKeywordScore -PromptLower $promptLower -Keywords $pack.trigger_keywords
    $workspace = Get-WorkspaceSignalScore -PromptLower $promptLower -RequestedCanonical $requestedCanonical -Candidates $pack.skill_candidates
    $skillSignal = Get-PackSkillSignalScore -PromptLower $promptLower -Candidates $pack.skill_candidates -SkillKeywordIndex $skillKeywordIndex
    $prior = [double]$pack.priority / 100.0
    $conflictInverse = if ($gradeAllowed -and $taskAllowed) { 1.0 } else { 0.0 }

    $score =
        ([double]$weights.intent_match * $intent) +
        ([double]$weights.trigger_keyword_match * $trigger) +
        ([double]$weights.workspace_signal_match * $workspace) +
        ($weightSkillSignal * $skillSignal) +
        ([double]$weights.recent_success_prior * $prior) +
        ([double]$weights.conflict_penalty_inverse * $conflictInverse)

    $selection = Select-PackCandidate -PromptLower $promptLower -Candidates $pack.skill_candidates -TaskType $TaskType -RequestedCanonical $requestedCanonical -SkillKeywordIndex $skillKeywordIndex -RoutingRules $routingRules -Pack $pack -CandidateSelectionConfig $candidateSelectionConfig
    $candidateSignal = ([double]$selection.score * 0.75) + ([double]$selection.top1_top2_gap * 0.25)
    $candidateSignal = [Math]::Round([Math]::Min(1.0, [Math]::Max(0.0, $candidateSignal)), 4)

    $packResults += [pscustomobject]@{
        pack_id = [string]$pack.id
        score = [Math]::Round($score, 4)
        intent = [Math]::Round($intent, 4)
        trigger = [Math]::Round($trigger, 4)
        workspace = [Math]::Round($workspace, 4)
        skill_signal = [Math]::Round($skillSignal, 4)
        prior = [Math]::Round($prior, 4)
        grade_allowed = $gradeAllowed
        task_allowed = $taskAllowed
        candidates = @($pack.skill_candidates)
        selected_candidate = $selection.selected
        candidate_selection_reason = $selection.reason
        candidate_selection_score = [Math]::Round([double]$selection.score, 4)
        candidate_ranking = @($selection.ranking)
        candidate_top1_top2_gap = [Math]::Round([double]$selection.top1_top2_gap, 4)
        candidate_signal = $candidateSignal
        candidate_filtered_out_by_task = @($selection.filtered_out_by_task)
    }
}

$ranked = $packResults | Sort-Object -Property @(
    @{ Expression = "score"; Descending = $true },
    @{ Expression = "pack_id"; Descending = $false }
)
$top = $ranked | Select-Object -First 1
$confidence = if ($top) { [double]$top.score } else { 0.0 }

# Soft-migration behavior: explicit legacy/canonical skill request mapped to a pack
# is treated as a strong routing signal to avoid unnecessary legacy fallback.
if ($top -and $requestedCanonical -and ($top.candidates -contains $requestedCanonical)) {
    $confidence = [Math]::Max($confidence, ([double]$th.confirm_required + 0.05))
}

$topGap = if ($top) { [double]$top.candidate_top1_top2_gap } else { 0.0 }
$candidateSignal = if ($top) { [double]$top.candidate_signal } else { 0.0 }
$canOverrideLegacyFallback = $false
if ($top -and ($top.candidate_selection_reason -in @("keyword_ranked", "requested_skill")) -and ($candidateSignal -ge $minCandidateSignalForConfirmOverride)) {
    $canOverrideLegacyFallback = $true
}
$routeReason = ""
if (-not $top) {
    $routeMode = "legacy_fallback"
    $routeReason = "no_eligible_pack"
} elseif ($confidence -lt [double]$th.fallback_to_legacy_below) {
    if ($canOverrideLegacyFallback) {
        $routeMode = "confirm_required"
        $routeReason = "candidate_signal_override"
        $confidence = [Math]::Max($confidence, [double]$th.confirm_required)
    } else {
        $routeMode = "legacy_fallback"
        $routeReason = "confidence_below_fallback"
    }
} elseif ($topGap -lt $minTopGap) {
    $routeMode = "confirm_required"
    $routeReason = "top_candidates_too_close"
} elseif ($confidence -lt [double]$th.auto_route) {
    $routeMode = "confirm_required"
    $routeReason = "confidence_requires_confirmation"
} else {
    $routeMode = "pack_overlay"
    $routeReason = "auto_route"
}

$deepDiscoveryRouteModeOverride = $false
if ($routeMode -eq "pack_overlay" -and $deepDiscoveryAdvice -and $deepDiscoveryAdvice.scope_applicable -and $deepDiscoveryAdvice.confirm_required) {
    $routeMode = "confirm_required"
    $routeReason = "deep_discovery_confirm_required"
    $confidence = [Math]::Max($confidence, [double]$th.confirm_required)
    $deepDiscoveryRouteModeOverride = $true
}

$rankedPreview = @(
    $ranked | Select-Object -First 3 | ForEach-Object {
        [pscustomobject]@{
            pack_id = [string]$_.pack_id
            score = [double]$_.score
            selected_candidate = [string]$_.selected_candidate
            selection_reason = [string]$_.candidate_selection_reason
            candidate_signal = [double]$_.candidate_signal
            top1_top2_gap = [double]$_.candidate_top1_top2_gap
        }
    }
)

Add-RouteProbeEvent -Context $probeContext -Stage "router.pack_scoring" -Note "pack ranking and initial route mode" -Data @{
    pack_count = $packResults.Count
    pack_source_count = $packsForScoring.Count
    deep_discovery_filter = $deepDiscoveryFilterSummary
    ranked_top = @($rankedPreview)
    initial_route_mode = $routeMode
    initial_route_reason = $routeReason
    confidence = [double]$confidence
    top1_top2_gap = [double]$topGap
    candidate_signal = [double]$candidateSignal
    deep_discovery_route_mode_override = [bool]$deepDiscoveryRouteModeOverride
}
$null = Add-HeartbeatPulse -Context $heartbeatContext -Stage "router.pack_scoring" -Phase "router.pack_scoring" -Note "pack scoring complete" -Data @{
    route_mode = $routeMode
    confidence = [double]$confidence
    candidate_signal = [double]$candidateSignal
}

$aiRerankAdvice = Get-AiRerankAdvice `
    -PromptText $Prompt `
    -PromptLower $promptLower `
    -Grade $Grade `
    -TaskType $TaskType `
    -RouteMode $routeMode `
    -RequestedCanonical $requestedCanonical `
    -Ranked $ranked `
    -TopGap $topGap `
    -Confidence $confidence `
    -AiRerankPolicy $aiRerankPolicy

$aiRerankRouteOverride = [bool]($aiRerankAdvice -and $aiRerankAdvice.route_override_applied)
$effectiveTop = $top
if ($aiRerankRouteOverride -and $aiRerankAdvice -and $aiRerankAdvice.override_target_pack) {
    $overridePackId = [string]$aiRerankAdvice.override_target_pack
    $overrideTop = $ranked | Where-Object { [string]$_.pack_id -eq $overridePackId } | Select-Object -First 1
    if ($overrideTop) {
        $effectiveTop = $overrideTop
        if ($routeMode -eq "pack_overlay") {
            $routeReason = "ai_rerank_override"
        }
    }
}

Add-RouteProbeEvent -Context $probeContext -Stage "overlay.ai_rerank" -Note "ai rerank overlay evaluated" -Data @{
    advice = Get-RouteProbeAdviceSummary -Advice $aiRerankAdvice
    route_override_applied = [bool]$aiRerankRouteOverride
    top_pack_before = if ($top) { [string]$top.pack_id } else { $null }
    top_pack_after = if ($effectiveTop) { [string]$effectiveTop.pack_id } else { $null }
    route_mode_after = $routeMode
    route_reason_after = $routeReason
}
$null = Add-HeartbeatPulse -Context $heartbeatContext -Stage "overlay.ai_rerank" -Phase "overlay" -Note "ai rerank overlay evaluated" -Data @{
    route_override_applied = [bool]$aiRerankRouteOverride
}

$promptOverlayRouteOverride = $false
if ($routeMode -eq "pack_overlay" -and $promptOverlayAdvice -and $promptOverlayAdvice.scope_applicable -and $promptOverlayAdvice.confirm_required) {
    $routeMode = "confirm_required"
    $routeReason = "prompt_overlay_confirm_required"
    $confidence = [Math]::Max($confidence, [double]$th.confirm_required)
    $promptOverlayRouteOverride = $true
}

Add-RouteProbeEvent -Context $probeContext -Stage "overlay.prompt" -Note "prompt overlay guard check" -Data @{
    advice = Get-RouteProbeAdviceSummary -Advice $promptOverlayAdvice
    route_override_applied = [bool]$promptOverlayRouteOverride
    route_mode_after = $routeMode
    route_reason_after = $routeReason
}
$null = Add-HeartbeatPulse -Context $heartbeatContext -Stage "overlay.prompt" -Phase "overlay" -Note "prompt overlay evaluated" -Data @{
    route_override_applied = [bool]$promptOverlayRouteOverride
}

$dataScaleAdvice = Get-DataScaleOverlayAdvice `
    -Prompt $Prompt `
    -PromptLower $promptLower `
    -Grade $Grade `
    -TaskType $TaskType `
    -RouteMode $routeMode `
    -SelectedPackId $(if ($effectiveTop) { [string]$effectiveTop.pack_id } else { $null }) `
    -SelectedSkill $(if ($effectiveTop) { [string]$effectiveTop.selected_candidate } else { $null }) `
    -PackCandidates $(if ($effectiveTop) { @($effectiveTop.candidates) } else { @() }) `
    -DataScaleOverlayPolicy $dataScaleOverlayPolicy

$dataScaleRouteOverride = $false
$effectiveSelectedSkill = if ($effectiveTop) { [string]$effectiveTop.selected_candidate } else { $null }
$effectiveSelectionReason = if ($effectiveTop) { [string]$effectiveTop.candidate_selection_reason } else { $null }
$effectiveSelectionScore = if ($effectiveTop) { [double]$effectiveTop.candidate_selection_score } else { 0.0 }

if ($effectiveTop -and $dataScaleAdvice -and $dataScaleAdvice.scope_applicable -and $dataScaleAdvice.override_candidate_allowed -and $dataScaleAdvice.recommended_skill -and ($dataScaleAdvice.recommended_skill -ne $effectiveSelectedSkill)) {
    if ($dataScaleAdvice.auto_override) {
        $effectiveSelectedSkill = [string]$dataScaleAdvice.recommended_skill
        $effectiveSelectionReason = "data_scale_overlay_override"
        $effectiveSelectionScore = [Math]::Round([Math]::Max([double]$effectiveSelectionScore, [double]$dataScaleAdvice.confidence), 4)
        $dataScaleRouteOverride = $true
        if ($routeMode -eq "pack_overlay") {
            $routeReason = "data_scale_auto_override"
        }
    } elseif ($dataScaleAdvice.confirm_required -and $routeMode -eq "pack_overlay") {
        $routeMode = "confirm_required"
        $routeReason = "data_scale_confirm_required"
        $confidence = [Math]::Max($confidence, [double]$th.confirm_required)
        $dataScaleRouteOverride = $true
    }
}

Add-RouteProbeEvent -Context $probeContext -Stage "overlay.data_scale" -Note "data-scale overlay evaluated" -Data @{
    advice = Get-RouteProbeAdviceSummary -Advice $dataScaleAdvice
    selected_skill_before = if ($effectiveTop) { [string]$effectiveTop.selected_candidate } else { $null }
    selected_skill_after = $effectiveSelectedSkill
    route_override_applied = [bool]$dataScaleRouteOverride
    route_mode_after = $routeMode
    route_reason_after = $routeReason
}
$null = Add-HeartbeatPulse -Context $heartbeatContext -Stage "overlay.data_scale" -Phase "overlay" -Note "data-scale overlay evaluated" -Data @{
    route_override_applied = [bool]$dataScaleRouteOverride
}

$qualityDebtAdvice = Get-QualityDebtOverlayAdvice `
    -Prompt $Prompt `
    -PromptLower $promptLower `
    -Grade $Grade `
    -TaskType $TaskType `
    -RouteMode $routeMode `
    -SelectedPackId $(if ($effectiveTop) { [string]$effectiveTop.pack_id } else { $null }) `
    -SelectedSkill $effectiveSelectedSkill `
    -PackCandidates $(if ($effectiveTop) { @($effectiveTop.candidates) } else { @() }) `
    -QualityDebtOverlayPolicy $qualityDebtOverlayPolicy

$frameworkInteropAdvice = Get-FrameworkInteropOverlayAdvice `
    -Prompt $Prompt `
    -PromptLower $promptLower `
    -Grade $Grade `
    -TaskType $TaskType `
    -RouteMode $routeMode `
    -SelectedPackId $(if ($effectiveTop) { [string]$effectiveTop.pack_id } else { $null }) `
    -SelectedSkill $effectiveSelectedSkill `
    -PackCandidates $(if ($effectiveTop) { @($effectiveTop.candidates) } else { @() }) `
    -FrameworkInteropOverlayPolicy $frameworkInteropOverlayPolicy

$mlLifecycleAdvice = Get-MlLifecycleOverlayAdvice `
    -Prompt $Prompt `
    -PromptLower $promptLower `
    -Grade $Grade `
    -TaskType $TaskType `
    -RouteMode $routeMode `
    -SelectedPackId $(if ($effectiveTop) { [string]$effectiveTop.pack_id } else { $null }) `
    -SelectedSkill $effectiveSelectedSkill `
    -PackCandidates $(if ($effectiveTop) { @($effectiveTop.candidates) } else { @() }) `
    -MlLifecycleOverlayPolicy $mlLifecycleOverlayPolicy

$pythonCleanCodeAdvice = Get-PythonCleanCodeAdvice `
    -Prompt $Prompt `
    -PromptLower $promptLower `
    -Grade $Grade `
    -TaskType $TaskType `
    -RouteMode $routeMode `
    -SelectedPackId $(if ($effectiveTop) { [string]$effectiveTop.pack_id } else { $null }) `
    -SelectedSkill $effectiveSelectedSkill `
    -PackCandidates $(if ($effectiveTop) { @($effectiveTop.candidates) } else { @() }) `
    -PythonCleanCodeOverlayPolicy $pythonCleanCodeOverlayPolicy

$systemDesignAdvice = Get-SystemDesignOverlayAdvice `
    -Prompt $Prompt `
    -PromptLower $promptLower `
    -Grade $Grade `
    -TaskType $TaskType `
    -RouteMode $routeMode `
    -SelectedPackId $(if ($effectiveTop) { [string]$effectiveTop.pack_id } else { $null }) `
    -SelectedSkill $effectiveSelectedSkill `
    -PackCandidates $(if ($effectiveTop) { @($effectiveTop.candidates) } else { @() }) `
    -SystemDesignOverlayPolicy $systemDesignOverlayPolicy

$cudaKernelAdvice = Get-CudaKernelOverlayAdvice `
    -Prompt $Prompt `
    -PromptLower $promptLower `
    -Grade $Grade `
    -TaskType $TaskType `
    -RouteMode $routeMode `
    -SelectedPackId $(if ($effectiveTop) { [string]$effectiveTop.pack_id } else { $null }) `
    -SelectedSkill $effectiveSelectedSkill `
    -PackCandidates $(if ($effectiveTop) { @($effectiveTop.candidates) } else { @() }) `
    -CudaKernelOverlayPolicy $cudaKernelOverlayPolicy

Add-RouteProbeEvent -Context $probeContext -Stage "overlay.bundle" -Note "post-route advisory overlays evaluated" -Data @{
    quality_debt = Get-RouteProbeAdviceSummary -Advice $qualityDebtAdvice
    framework_interop = Get-RouteProbeAdviceSummary -Advice $frameworkInteropAdvice
    ml_lifecycle = Get-RouteProbeAdviceSummary -Advice $mlLifecycleAdvice
    python_clean_code = Get-RouteProbeAdviceSummary -Advice $pythonCleanCodeAdvice
    system_design = Get-RouteProbeAdviceSummary -Advice $systemDesignAdvice
    cuda_kernel = Get-RouteProbeAdviceSummary -Advice $cudaKernelAdvice
}
$null = Add-HeartbeatPulse -Context $heartbeatContext -Stage "overlay.bundle" -Phase "overlay" -Note "post-route advisory overlays evaluated"
$heartbeatFinalizeStatus = Finalize-HeartbeatContext -Context $heartbeatContext -FinalPhase "router.final" -Succeeded $true -Note "route output assembled"
$heartbeatAdvice = Get-HeartbeatAdvice -Context $heartbeatContext
$heartbeatStatus = if ($heartbeatFinalizeStatus) { $heartbeatFinalizeStatus } else { Get-HeartbeatStatus -Context $heartbeatContext }
$heartbeatRuntimeDigestEnabled = [bool]($heartbeatContext -and $heartbeatContext.runtime_digest_enabled)
$heartbeatRuntimeDigest = if ($heartbeatRuntimeDigestEnabled) {
    Get-HeartbeatRuntimeDigest -Context $heartbeatContext -RecentPulseCount ([int]$heartbeatContext.runtime_digest_recent_pulses)
} else {
    $null
}

$result = [pscustomobject]@{
    prompt = $Prompt
    grade = $Grade
    task_type = $TaskType
    route_mode = $routeMode
    route_reason = $routeReason
    confidence = [Math]::Round($confidence, 4)
    top1_top2_gap = [Math]::Round($topGap, 4)
    candidate_signal = [Math]::Round($candidateSignal, 4)
    thresholds = [pscustomobject]@{
        auto_route = [double]$th.auto_route
        confirm_required = [double]$th.confirm_required
        fallback_to_legacy_below = [double]$th.fallback_to_legacy_below
        min_top1_top2_gap = [double]$minTopGap
        min_candidate_signal_for_confirm_override = [double]$minCandidateSignalForConfirmOverride
    }
    alias = $aliasResult
    openspec_advice = $openSpecAdvice
    gsd_overlay_advice = $gsdOverlayAdvice
    prompt_overlay_advice = $promptOverlayAdvice
    memory_governance_advice = $memoryGovernanceAdvice
    deep_discovery_advice = $deepDiscoveryAdvice
    intent_contract = $intentContract
    deep_discovery_filter = $deepDiscoveryFilterSummary
    deep_discovery_route_filter_applied = [bool]($deepDiscoveryFilter -and $deepDiscoveryFilter.route_filter_applied)
    deep_discovery_route_mode_override = [bool]$deepDiscoveryRouteModeOverride
    prompt_overlay_route_override = $promptOverlayRouteOverride
    ai_rerank_advice = $aiRerankAdvice
    ai_rerank_route_override = $aiRerankRouteOverride
    data_scale_advice = $dataScaleAdvice
    data_scale_route_override = $dataScaleRouteOverride
    quality_debt_advice = $qualityDebtAdvice
    framework_interop_advice = $frameworkInteropAdvice
    ml_lifecycle_advice = $mlLifecycleAdvice
    python_clean_code_advice = $pythonCleanCodeAdvice
    system_design_advice = $systemDesignAdvice
    cuda_kernel_advice = $cudaKernelAdvice
    heartbeat_advice = $heartbeatAdvice
    heartbeat_status = $heartbeatStatus
    heartbeat_runtime_digest = $heartbeatRuntimeDigest
    selected = if ($effectiveTop) {
        [pscustomobject]@{
            pack_id = $effectiveTop.pack_id
            skill = $effectiveSelectedSkill
            selection_reason = $effectiveSelectionReason
            selection_score = $effectiveSelectionScore
            top1_top2_gap = $effectiveTop.candidate_top1_top2_gap
            candidate_signal = $effectiveTop.candidate_signal
            filtered_out_by_task = @($effectiveTop.candidate_filtered_out_by_task)
        }
    } else {
        $null
    }
    ranked = @($ranked | Select-Object -First 3)
}

$runtimeDigestEnabled = $false
if ($deepDiscoveryPolicy -and $deepDiscoveryPolicy.runtime_prompt -and $deepDiscoveryPolicy.runtime_prompt.include_digest -ne $null) {
    $runtimeDigestEnabled = [bool]$deepDiscoveryPolicy.runtime_prompt.include_digest
}
if ($runtimeDigestEnabled) {
    $runtimeStatePromptDigest = Get-RouteRuntimeStatePromptDigest -Result $result -PromptText $Prompt -FoldOutsideScope $true
    $result | Add-Member -NotePropertyName "runtime_state_prompt_digest" -NotePropertyValue $runtimeStatePromptDigest
}

$observabilityWrite = Write-ObservabilityRouteEvent -PromptText $Prompt -Result $result -ObservabilityPolicy $observabilityPolicy -RepoRoot $repoRoot

Add-RouteProbeEvent -Context $probeContext -Stage "router.final" -Note "final route output assembled" -Data @{
    route_mode = $result.route_mode
    route_reason = $result.route_reason
    selected_pack = if ($result.selected) { [string]$result.selected.pack_id } else { $null }
    selected_skill = if ($result.selected) { [string]$result.selected.skill } else { $null }
    confidence = [double]$result.confidence
    deep_discovery = [pscustomobject]@{
        trigger_active = [bool]($result.deep_discovery_advice -and $result.deep_discovery_advice.trigger_active)
        trigger_score = if ($result.deep_discovery_advice -and $result.deep_discovery_advice.trigger_score -ne $null) { [double]$result.deep_discovery_advice.trigger_score } else { 0.0 }
        contract_completeness = if ($result.intent_contract -and $result.intent_contract.completeness -ne $null) { [double]$result.intent_contract.completeness } else { 0.0 }
        route_filter_applied = [bool]$result.deep_discovery_route_filter_applied
        route_mode_override = [bool]$result.deep_discovery_route_mode_override
    }
    heartbeat = [pscustomobject]@{
        mode = if ($result.heartbeat_advice) { [string]$result.heartbeat_advice.mode } else { "off" }
        status = if ($result.heartbeat_status) { [string]$result.heartbeat_status.current_status } else { "disabled" }
        lifecycle_status = if ($result.heartbeat_status) { [string]$result.heartbeat_status.lifecycle_status } else { "disabled" }
        pulse_count = if ($result.heartbeat_status -and $result.heartbeat_status.pulse_count -ne $null) { [int]$result.heartbeat_status.pulse_count } else { 0 }
        stall_score = if ($result.heartbeat_status -and $result.heartbeat_status.stall_score -ne $null) { [double]$result.heartbeat_status.stall_score } else { 0.0 }
        hard_stall = if ($result.heartbeat_status) { [bool]$result.heartbeat_status.hard_stall } else { $false }
        suspect_stall = if ($result.heartbeat_status) { [bool]$result.heartbeat_status.suspect_stall } else { $false }
        confirm_required = if ($result.heartbeat_advice) { [bool]$result.heartbeat_advice.confirm_required } else { $false }
        auto_diagnosis_triggered = if ($result.heartbeat_advice) { [bool]$result.heartbeat_advice.auto_diagnosis_triggered } else { $false }
    }
    observability = if ($observabilityWrite) { $observabilityWrite } else { $null }
}

$probeArtifact = Write-RouteProbeArtifact -Context $probeContext -PromptText $Prompt -Result $result
if ($probeArtifact) {
    $result | Add-Member -NotePropertyName "probe_reference" -NotePropertyValue $probeArtifact
}

$result | ConvertTo-Json -Depth 12


