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
    [int]$ProbePromptMaxChars = 1600,
    [switch]$Unattended
)

$ErrorActionPreference = "Stop"
$routerModuleRoot = Join-Path $PSScriptRoot "modules"
$routerModules = @(
    "00-core-utils.ps1",
    "01-openai-responses.ps1",
    "02-volc-ark.ps1",
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
    "42-ai-rerank-overlay.ps1",
    "43-retrieval-overlay.ps1",
    "44-exploration-overlay.ps1",
    "44-dialectic-team-gate.ps1",
    "45-daily-dialectic-guard.ps1",
    "46-confirm-ui.ps1",
    "47-closure-overlay.ps1",
    "48-llm-acceleration-overlay.ps1",
    "49-prompt-asset-boost.ps1"
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
$promptAssetBoostPolicyPath = Join-Path $configRoot "prompt-asset-boost.json"
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
$retrievalPolicyPath = Join-Path $configRoot "retrieval-policy.json"
$retrievalIntentProfilesPath = Join-Path $configRoot "retrieval-intent-profiles.json"
$retrievalSourceRegistryPath = Join-Path $configRoot "retrieval-source-registry.json"
$retrievalRerankWeightsPath = Join-Path $configRoot "retrieval-rerank-weights.json"
$explorationPolicyPath = Join-Path $configRoot "exploration-policy.json"
$explorationIntentProfilesPath = Join-Path $configRoot "exploration-intent-profiles.json"
$explorationDomainMapPath = Join-Path $configRoot "exploration-domain-map.json"
$closureOverlayPolicyPath = Join-Path $configRoot "closure-overlay.json"
$probePolicyPath = Join-Path $configRoot "router-probe-policy.json"
$deepDiscoveryPolicyPath = Join-Path $configRoot "deep-discovery-policy.json"
$capabilityCatalogPath = Join-Path $configRoot "capability-catalog.json"
$dialecticTeamPolicyPath = Join-Path $configRoot "dialectic-team-policy.json"
$dailyDialecticPolicyPath = Join-Path $configRoot "daily-dialectic-guard.json"
$confirmUiPolicyPath = Join-Path $configRoot "confirm-ui-policy.json"
$llmAccelerationPolicyPath = Join-Path $configRoot "llm-acceleration-policy.json"

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
$promptAssetBoostPolicy = if (Test-Path -LiteralPath $promptAssetBoostPolicyPath) {
    Get-Content -LiteralPath $promptAssetBoostPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
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
$retrievalPolicy = if (Test-Path -LiteralPath $retrievalPolicyPath) {
    try {
        Get-Content -LiteralPath $retrievalPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        $null
    }
} else {
    $null
}
$retrievalIntentProfiles = if (Test-Path -LiteralPath $retrievalIntentProfilesPath) {
    try {
        Get-Content -LiteralPath $retrievalIntentProfilesPath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        $null
    }
} else {
    $null
}
$retrievalSourceRegistry = if (Test-Path -LiteralPath $retrievalSourceRegistryPath) {
    try {
        Get-Content -LiteralPath $retrievalSourceRegistryPath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        $null
    }
} else {
    $null
}
$retrievalRerankWeights = if (Test-Path -LiteralPath $retrievalRerankWeightsPath) {
    try {
        Get-Content -LiteralPath $retrievalRerankWeightsPath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        $null
    }
} else {
    $null
}
$explorationPolicy = if (Test-Path -LiteralPath $explorationPolicyPath) {
    try {
        Get-Content -LiteralPath $explorationPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        $null
    }
} else {
    $null
}
$explorationIntentProfiles = if (Test-Path -LiteralPath $explorationIntentProfilesPath) {
    try {
        Get-Content -LiteralPath $explorationIntentProfilesPath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        $null
    }
} else {
    $null
}
$explorationDomainMap = if (Test-Path -LiteralPath $explorationDomainMapPath) {
    try {
        Get-Content -LiteralPath $explorationDomainMapPath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        $null
    }
} else {
    $null
}
$closureOverlayPolicy = if (Test-Path -LiteralPath $closureOverlayPolicyPath) {
    try {
        Get-Content -LiteralPath $closureOverlayPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
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
$dialecticTeamPolicy = if (Test-Path -LiteralPath $dialecticTeamPolicyPath) {
    try {
        Get-Content -LiteralPath $dialecticTeamPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        $null
    }
} else {
    $null
}
$dailyDialecticPolicy = if (Test-Path -LiteralPath $dailyDialecticPolicyPath) {
    try {
        Get-Content -LiteralPath $dailyDialecticPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        $null
    }
} else {
    $null
}
$confirmUiPolicy = if (Test-Path -LiteralPath $confirmUiPolicyPath) {
    try {
        Get-Content -LiteralPath $confirmUiPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        $null
    }
} else {
    $null
}
$llmAccelerationPolicy = if (Test-Path -LiteralPath $llmAccelerationPolicyPath) {
    try {
        Get-Content -LiteralPath $llmAccelerationPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
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
$enforceConfirmOnLegacyFallback = if ($rules.enforce_confirm_on_legacy_fallback -ne $null) { [bool]$rules.enforce_confirm_on_legacy_fallback } else { $false }

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
        enforce_confirm_on_legacy_fallback = [bool]$enforceConfirmOnLegacyFallback
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
        retrieval_mode = if ($retrievalPolicy -and $retrievalPolicy.mode) { [string]$retrievalPolicy.mode } else { "off" }
        exploration_mode = if ($explorationPolicy -and $explorationPolicy.mode) { [string]$explorationPolicy.mode } else { "off" }
        closure_mode = if ($closureOverlayPolicy -and $closureOverlayPolicy.mode) { [string]$closureOverlayPolicy.mode } else { "off" }
        observability_mode = if ($observabilityPolicy -and $observabilityPolicy.mode) { [string]$observabilityPolicy.mode } else { "off" }
        heartbeat_mode = if ($heartbeatPolicy -and $heartbeatPolicy.mode) { [string]$heartbeatPolicy.mode } else { "off" }
        deep_discovery_mode = if ($deepDiscoveryPolicy -and $deepDiscoveryPolicy.mode) { [string]$deepDiscoveryPolicy.mode } else { "off" }
        dialectic_team_mode = if ($dialecticTeamPolicy -and $dialecticTeamPolicy.mode) { [string]$dialecticTeamPolicy.mode } else { "off" }
        daily_dialectic_mode = if ($dailyDialecticPolicy -and $dailyDialecticPolicy.mode) { [string]$dailyDialecticPolicy.mode } else { "off" }
        llm_acceleration_mode = if ($llmAccelerationPolicy -and $llmAccelerationPolicy.mode) { [string]$llmAccelerationPolicy.mode } else { "off" }
        prompt_asset_boost_mode = if ($promptAssetBoostPolicy -and $promptAssetBoostPolicy.mode) { [string]$promptAssetBoostPolicy.mode } else { "off" }
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

$llmAccelerationAdvice = Get-LlmAccelerationAdvice `
    -PromptText $Prompt `
    -PromptNormalization $promptNormalization `
    -Grade $Grade `
    -TaskType $TaskType `
    -RouteMode $routeMode `
    -RouteReason $routeReason `
    -Ranked $ranked `
    -TopGap $topGap `
    -Confidence $confidence `
    -LlmAccelerationPolicy $llmAccelerationPolicy `
    -RepoRoot ([string]$repoRoot)

$llmAccelerationConfirmOverride = $false
if ($routeMode -eq "pack_overlay" -and $llmAccelerationAdvice -and $llmAccelerationAdvice.scope_applicable -and $llmAccelerationAdvice.confirm_required -and ([string]$llmAccelerationAdvice.mode -in @("soft", "strict"))) {
    $routeMode = "confirm_required"
    $routeReason = "llm_acceleration_confirm_required"
    $confidence = [Math]::Max($confidence, [double]$th.confirm_required)
    $llmAccelerationConfirmOverride = $true
}

$llmAccelerationRouteOverride = [bool]($llmAccelerationAdvice -and $llmAccelerationAdvice.route_override_applied)
if ($llmAccelerationRouteOverride -and $llmAccelerationAdvice -and $llmAccelerationAdvice.override_target_pack) {
    $overridePackId = [string]$llmAccelerationAdvice.override_target_pack
    $overrideTop = $ranked | Where-Object { [string]$_.pack_id -eq $overridePackId } | Select-Object -First 1
    if ($overrideTop) {
        $effectiveTop = $overrideTop
        if ($routeMode -eq "pack_overlay") {
            $routeReason = "llm_acceleration_override"
        }
    }
}

Add-RouteProbeEvent -Context $probeContext -Stage "overlay.llm_acceleration" -Note "llm acceleration overlay evaluated" -Data @{
    advice = Get-RouteProbeAdviceSummary -Advice $llmAccelerationAdvice
    route_override_applied = [bool]$llmAccelerationRouteOverride
    confirm_override_applied = [bool]$llmAccelerationConfirmOverride
    top_pack_after = if ($effectiveTop) { [string]$effectiveTop.pack_id } else { $null }
    route_mode_after = $routeMode
    route_reason_after = $routeReason
}
$null = Add-HeartbeatPulse -Context $heartbeatContext -Stage "overlay.llm_acceleration" -Phase "overlay" -Note "llm acceleration overlay evaluated" -Data @{
    route_override_applied = [bool]$llmAccelerationRouteOverride
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

$dialecticTeamAdvice = Get-DialecticTeamAdvice `
    -PromptText $Prompt `
    -PromptLower $promptLower `
    -Grade $Grade `
    -TaskType $TaskType `
    -RequestedCanonical $requestedCanonical `
    -SelectedPackId $(if ($effectiveTop) { [string]$effectiveTop.pack_id } else { $null }) `
    -SelectedSkill $effectiveSelectedSkill `
    -PackCandidates $(if ($effectiveTop) { @($effectiveTop.candidates) } else { @() }) `
    -DialecticTeamPolicy $dialecticTeamPolicy

$dialecticTeamRouteOverride = $false
if ($dialecticTeamAdvice -and $dialecticTeamAdvice.scope_applicable) {
    if ($dialecticTeamAdvice.override_selected_skill -and $dialecticTeamAdvice.recommended_skill -and ($dialecticTeamAdvice.recommended_skill -ne $effectiveSelectedSkill)) {
        $effectiveSelectedSkill = [string]$dialecticTeamAdvice.recommended_skill
        $effectiveSelectionReason = if ($dialecticTeamAdvice.explicit_requested) { "dialectic_team_explicit_override" } else { "dialectic_team_explicit_only_fallback" }
        $effectiveSelectionScore = if ($effectiveTop) {
            [Math]::Round([Math]::Max([double]$effectiveTop.candidate_selection_score, [double]$confidence), 4)
        } else {
            [Math]::Round([double]$confidence, 4)
        }
        $dialecticTeamRouteOverride = $true
        if ($routeMode -eq "pack_overlay") {
            $routeReason = if ($dialecticTeamAdvice.explicit_requested) { "dialectic_team_explicit_override" } else { "dialectic_team_explicit_only_fallback" }
        }
    }

    if ($dialecticTeamAdvice.confirm_required -and $routeMode -eq "pack_overlay") {
        $routeMode = "confirm_required"
        $routeReason = "dialectic_team_confirm_required"
        $confidence = [Math]::Max($confidence, [double]$th.confirm_required)
    }
}

Add-RouteProbeEvent -Context $probeContext -Stage "overlay.dialectic_team" -Note "dialectic team gate evaluated" -Data @{
    advice = Get-RouteProbeAdviceSummary -Advice $dialecticTeamAdvice
    selected_skill_after = $effectiveSelectedSkill
    route_override_applied = [bool]$dialecticTeamRouteOverride
    route_mode_after = $routeMode
    route_reason_after = $routeReason
}
$null = Add-HeartbeatPulse -Context $heartbeatContext -Stage "overlay.dialectic_team" -Phase "overlay" -Note "dialectic team gate evaluated" -Data @{
    explicit_requested = if ($dialecticTeamAdvice) { [bool]$dialecticTeamAdvice.explicit_requested } else { $false }
    confirm_required = if ($dialecticTeamAdvice) { [bool]$dialecticTeamAdvice.confirm_required } else { $false }
    route_override_applied = [bool]$dialecticTeamRouteOverride
}

$dailyDialecticAdvice = Get-DailyDialecticAdvice `
    -PromptText $Prompt `
    -PromptLower $promptLower `
    -Grade $Grade `
    -TaskType $TaskType `
    -RouteMode $routeMode `
    -SelectedPackId $(if ($effectiveTop) { [string]$effectiveTop.pack_id } else { $null }) `
    -SelectedSkill $effectiveSelectedSkill `
    -IntentContract $intentContract `
    -DailyDialecticPolicy $dailyDialecticPolicy `
    -DialecticTeamAdvice $dialecticTeamAdvice

if ($dailyDialecticAdvice -and $dailyDialecticAdvice.confirm_required -and $routeMode -eq "pack_overlay") {
    $routeMode = "confirm_required"
    $routeReason = "daily_dialectic_confirm_required"
    $confidence = [Math]::Max($confidence, [double]$th.confirm_required)
}

Add-RouteProbeEvent -Context $probeContext -Stage "overlay.daily_dialectic" -Note "daily dialectic guard evaluated" -Data @{
    advice = Get-RouteProbeAdviceSummary -Advice $dailyDialecticAdvice
    route_mode_after = $routeMode
    route_reason_after = $routeReason
}
$null = Add-HeartbeatPulse -Context $heartbeatContext -Stage "overlay.daily_dialectic" -Phase "overlay" -Note "daily dialectic guard evaluated" -Data @{
    confirm_required = if ($dailyDialecticAdvice) { [bool]$dailyDialecticAdvice.confirm_required } else { $false }
    scope_applicable = if ($dailyDialecticAdvice) { [bool]$dailyDialecticAdvice.scope_applicable } else { $false }
}

$explorationAdvice = Get-ExplorationOverlayAdvice `
    -Prompt $Prompt `
    -PromptLower $promptLower `
    -Grade $Grade `
    -TaskType $TaskType `
    -RouteMode $routeMode `
    -SelectedPackId $(if ($effectiveTop) { [string]$effectiveTop.pack_id } else { $null }) `
    -SelectedSkill $effectiveSelectedSkill `
    -PackCandidates $(if ($effectiveTop) { @($effectiveTop.candidates) } else { @() }) `
    -ExplorationPolicy $explorationPolicy `
    -ExplorationIntentProfiles $explorationIntentProfiles `
    -ExplorationDomainMap $explorationDomainMap

Add-RouteProbeEvent -Context $probeContext -Stage "overlay.exploration" -Note "exploration intent overlay evaluated" -Data @{
    advice = Get-RouteProbeAdviceSummary -Advice $explorationAdvice
    selected_skill = $effectiveSelectedSkill
    route_mode_after = $routeMode
    route_reason_after = $routeReason
}
$null = Add-HeartbeatPulse -Context $heartbeatContext -Stage "overlay.exploration" -Phase "overlay" -Note "exploration intent overlay evaluated" -Data @{
    enabled = if ($explorationAdvice) { [bool]$explorationAdvice.enabled } else { $false }
    scope_applicable = if ($explorationAdvice) { [bool]$explorationAdvice.scope_applicable } else { $false }
    intent_id = if ($explorationAdvice -and $explorationAdvice.intent_id) { [string]$explorationAdvice.intent_id } else { "none" }
    confirm_required = if ($explorationAdvice) { [bool]$explorationAdvice.confirm_required } else { $false }
}

$closureAdvice = Get-ClosureOverlayAdvice `
    -Prompt $Prompt `
    -PromptLower $promptLower `
    -Grade $Grade `
    -TaskType $TaskType `
    -RouteMode $routeMode `
    -SelectedPackId $(if ($effectiveTop) { [string]$effectiveTop.pack_id } else { $null }) `
    -SelectedSkill $effectiveSelectedSkill `
    -PackCandidates $(if ($effectiveTop) { @($effectiveTop.candidates) } else { @() }) `
    -ClosureOverlayPolicy $closureOverlayPolicy `
    -ExplorationAdvice $explorationAdvice

Add-RouteProbeEvent -Context $probeContext -Stage "overlay.closure" -Note "closure-first overlay evaluated" -Data @{
    advice = Get-RouteProbeAdviceSummary -Advice $closureAdvice
    selected_skill = $effectiveSelectedSkill
    route_mode_after = $routeMode
    route_reason_after = $routeReason
}
$null = Add-HeartbeatPulse -Context $heartbeatContext -Stage "overlay.closure" -Phase "overlay" -Note "closure-first overlay evaluated" -Data @{
    enabled = if ($closureAdvice) { [bool]$closureAdvice.enabled } else { $false }
    scope_applicable = if ($closureAdvice) { [bool]$closureAdvice.scope_applicable } else { $false }
    enforcement = if ($closureAdvice -and $closureAdvice.enforcement) { [string]$closureAdvice.enforcement } else { "none" }
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

$retrievalAdvice = Get-RetrievalOverlayAdvice `
    -Prompt $Prompt `
    -PromptLower $promptLower `
    -Grade $Grade `
    -TaskType $TaskType `
    -RouteMode $routeMode `
    -SelectedPackId $(if ($effectiveTop) { [string]$effectiveTop.pack_id } else { $null }) `
    -SelectedSkill $effectiveSelectedSkill `
    -PackCandidates $(if ($effectiveTop) { @($effectiveTop.candidates) } else { @() }) `
    -RetrievalPolicy $retrievalPolicy `
    -RetrievalIntentProfiles $retrievalIntentProfiles `
    -RetrievalSourceRegistry $retrievalSourceRegistry `
    -RetrievalRerankWeights $retrievalRerankWeights

Add-RouteProbeEvent -Context $probeContext -Stage "overlay.retrieval" -Note "retrieval overlay evaluated" -Data @{
    advice = Get-RouteProbeAdviceSummary -Advice $retrievalAdvice
    selected_pack = if ($effectiveTop) { [string]$effectiveTop.pack_id } else { $null }
    selected_skill = $effectiveSelectedSkill
    route_mode_after = $routeMode
    route_reason_after = $routeReason
}
$null = Add-HeartbeatPulse -Context $heartbeatContext -Stage "overlay.retrieval" -Phase "overlay" -Note "retrieval overlay evaluated" -Data @{
    confirm_required = if ($retrievalAdvice) { [bool]$retrievalAdvice.confirm_required } else { $false }
    profile_id = if ($retrievalAdvice -and $retrievalAdvice.profile_id) { [string]$retrievalAdvice.profile_id } else { "none" }
}

$promptAssetBoostAdvice = Get-PromptAssetBoostAdvice `
    -PromptText $Prompt `
    -PromptNormalization $promptNormalization `
    -PromptLower $promptLower `
    -Grade $Grade `
    -TaskType $TaskType `
    -RouteMode $routeMode `
    -SelectedPackId $(if ($effectiveTop) { [string]$effectiveTop.pack_id } else { $null }) `
    -SelectedSkill $effectiveSelectedSkill `
    -PromptOverlayAdvice $promptOverlayAdvice `
    -PromptAssetBoostPolicy $promptAssetBoostPolicy `
    -RepoRoot ([string]$repoRoot)

Add-RouteProbeEvent -Context $probeContext -Stage "overlay.prompt_asset_boost" -Note "prompt asset boost overlay evaluated" -Data @{
    advice = Get-RouteProbeAdviceSummary -Advice $promptAssetBoostAdvice
    selected_pack = if ($effectiveTop) { [string]$effectiveTop.pack_id } else { $null }
    selected_skill = $effectiveSelectedSkill
    route_mode_after = $routeMode
    route_reason_after = $routeReason
}
$null = Add-HeartbeatPulse -Context $heartbeatContext -Stage "overlay.prompt_asset_boost" -Phase "overlay" -Note "prompt asset boost overlay evaluated" -Data @{
    enabled = if ($promptAssetBoostAdvice) { [bool]$promptAssetBoostAdvice.enabled } else { $false }
    scope_applicable = if ($promptAssetBoostAdvice) { [bool]$promptAssetBoostAdvice.scope_applicable } else { $false }
    confirm_required = if ($promptAssetBoostAdvice) { [bool]$promptAssetBoostAdvice.confirm_required } else { $false }
    recommended_skill = if ($promptAssetBoostAdvice -and $promptAssetBoostAdvice.recommended_skill) { [string]$promptAssetBoostAdvice.recommended_skill } else { "none" }
}

Add-RouteProbeEvent -Context $probeContext -Stage "overlay.bundle" -Note "post-route advisory overlays evaluated" -Data @{
    dialectic_team = Get-RouteProbeAdviceSummary -Advice $dialecticTeamAdvice
    daily_dialectic = Get-RouteProbeAdviceSummary -Advice $dailyDialecticAdvice
    exploration = Get-RouteProbeAdviceSummary -Advice $explorationAdvice
    closure = Get-RouteProbeAdviceSummary -Advice $closureAdvice
    prompt_asset_boost = Get-RouteProbeAdviceSummary -Advice $promptAssetBoostAdvice
    quality_debt = Get-RouteProbeAdviceSummary -Advice $qualityDebtAdvice
    framework_interop = Get-RouteProbeAdviceSummary -Advice $frameworkInteropAdvice
    ml_lifecycle = Get-RouteProbeAdviceSummary -Advice $mlLifecycleAdvice
    python_clean_code = Get-RouteProbeAdviceSummary -Advice $pythonCleanCodeAdvice
    system_design = Get-RouteProbeAdviceSummary -Advice $systemDesignAdvice
    cuda_kernel = Get-RouteProbeAdviceSummary -Advice $cudaKernelAdvice
    retrieval = Get-RouteProbeAdviceSummary -Advice $retrievalAdvice
}
$null = Add-HeartbeatPulse -Context $heartbeatContext -Stage "overlay.bundle" -Phase "overlay" -Note "post-route advisory overlays evaluated"

$legacyFallbackOriginalReason = $null
$legacyFallbackGuardApplied = $false
if ($routeMode -eq "legacy_fallback" -and $enforceConfirmOnLegacyFallback) {
    $legacyFallbackOriginalReason = [string]$routeReason
    $routeMode = "confirm_required"
    $routeReason = "legacy_fallback_guard"
    $confidence = [Math]::Max($confidence, [double]$th.confirm_required)
    $legacyFallbackGuardApplied = $true
}

Add-RouteProbeEvent -Context $probeContext -Stage "router.legacy_fallback_guard" -Note "legacy fallback visibility guard evaluated" -Data @{
    enabled = [bool]$enforceConfirmOnLegacyFallback
    applied = [bool]$legacyFallbackGuardApplied
    original_reason = $legacyFallbackOriginalReason
    route_mode_after = $routeMode
    route_reason_after = $routeReason
}
$null = Add-HeartbeatPulse -Context $heartbeatContext -Stage "router.legacy_fallback_guard" -Phase "router.guard" -Note "legacy fallback guard evaluated" -Data @{
    enabled = [bool]$enforceConfirmOnLegacyFallback
    applied = [bool]$legacyFallbackGuardApplied
}

$confirmUiPolicyResolved = Get-ConfirmUiPolicy -Policy $confirmUiPolicy
$unattendedDecision = Get-UnattendedModeDecision -Prompt $Prompt -ConfirmUiPolicy $confirmUiPolicyResolved -RepoRoot ([string]$repoRoot) -UnattendedParam ([bool]$Unattended)
$routeModeBeforeUnattended = [string]$routeMode
$routeReasonBeforeUnattended = [string]$routeReason
$unattendedOverrideApplied = $false
if ($unattendedDecision -and [bool]$unattendedDecision.unattended -and $confirmUiPolicyResolved -and [bool]$confirmUiPolicyResolved.unattended.override_route_mode) {
    if ($routeMode -eq "confirm_required" -and $effectiveTop) {
        $overrideTarget = if ($confirmUiPolicyResolved.unattended.override_target_route_mode) { [string]$confirmUiPolicyResolved.unattended.override_target_route_mode } else { "pack_overlay" }
        if ($overrideTarget) {
            $routeMode = $overrideTarget
            $routeReason = "unattended_auto_route_override"
            $unattendedOverrideApplied = $true
        }
    }
}

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
    route_mode_before_unattended_override = if ($unattendedOverrideApplied) { $routeModeBeforeUnattended } else { $null }
    route_reason_before_unattended_override = if ($unattendedOverrideApplied) { $routeReasonBeforeUnattended } else { $null }
    unattended_decision = $unattendedDecision
    unattended_override_applied = [bool]$unattendedOverrideApplied
    confidence = [Math]::Round($confidence, 4)
    top1_top2_gap = [Math]::Round($topGap, 4)
    candidate_signal = [Math]::Round($candidateSignal, 4)
    legacy_fallback_guard_applied = [bool]$legacyFallbackGuardApplied
    legacy_fallback_original_reason = $legacyFallbackOriginalReason
    thresholds = [pscustomobject]@{
        auto_route = [double]$th.auto_route
        confirm_required = [double]$th.confirm_required
        fallback_to_legacy_below = [double]$th.fallback_to_legacy_below
        min_top1_top2_gap = [double]$minTopGap
        min_candidate_signal_for_confirm_override = [double]$minCandidateSignalForConfirmOverride
        enforce_confirm_on_legacy_fallback = [bool]$enforceConfirmOnLegacyFallback
    }
    alias = $aliasResult
    openspec_advice = $openSpecAdvice
    gsd_overlay_advice = $gsdOverlayAdvice
    prompt_overlay_advice = $promptOverlayAdvice
    prompt_asset_boost_advice = $promptAssetBoostAdvice
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
    retrieval_advice = $retrievalAdvice
    exploration_advice = $explorationAdvice
    closure_advice = $closureAdvice
    dialectic_team_advice = $dialecticTeamAdvice
    dialectic_team_route_override = $dialecticTeamRouteOverride
    daily_dialectic_advice = $dailyDialecticAdvice
    llm_acceleration_advice = $llmAccelerationAdvice
    llm_acceleration_route_override = $llmAccelerationRouteOverride
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

$confirmSkillOptions = Build-ConfirmSkillOptions -Result $result -ConfirmUiPolicy $confirmUiPolicyResolved -RepoRoot ([string]$repoRoot)
if ($confirmSkillOptions) {
    $confirmText = Build-ConfirmUiText -ConfirmSkillOptions $confirmSkillOptions -UnattendedDecision $unattendedDecision
    $result | Add-Member -NotePropertyName "confirm_ui" -NotePropertyValue ([pscustomobject]@{
        enabled = $true
        pack_id = [string]$confirmSkillOptions.selected_pack
        selected_skill = [string]$confirmSkillOptions.selected_skill
        options = @($confirmSkillOptions.options)
        rendered_text = $confirmText
    })
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
    legacy_fallback_guard_applied = [bool]$result.legacy_fallback_guard_applied
    legacy_fallback_original_reason = $result.legacy_fallback_original_reason
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
    retrieval = [pscustomobject]@{
        profile_id = if ($result.retrieval_advice -and $result.retrieval_advice.profile_id) { [string]$result.retrieval_advice.profile_id } else { "none" }
        profile_confidence = if ($result.retrieval_advice -and $result.retrieval_advice.profile_confidence -ne $null) { [double]$result.retrieval_advice.profile_confidence } else { 0.0 }
        profile_ambiguous = if ($result.retrieval_advice) { [bool]$result.retrieval_advice.profile_ambiguous } else { $false }
        needs_requery = if ($result.retrieval_advice -and $result.retrieval_advice.coverage_gate) { [bool]$result.retrieval_advice.coverage_gate.needs_requery } else { $false }
        confirm_required = if ($result.retrieval_advice) { [bool]$result.retrieval_advice.confirm_required } else { $false }
    }
    dialectic = [pscustomobject]@{
        explicit_requested = if ($result.dialectic_team_advice) { [bool]$result.dialectic_team_advice.explicit_requested } else { $false }
        team_mode_allowed = if ($result.dialectic_team_advice) { [bool]$result.dialectic_team_advice.team_mode_allowed } else { $false }
        should_apply_team_mode = if ($result.dialectic_team_advice) { [bool]$result.dialectic_team_advice.should_apply_team_mode } else { $false }
        confirm_required = if ($result.dialectic_team_advice) { [bool]$result.dialectic_team_advice.confirm_required } else { $false }
        route_override_applied = [bool]$result.dialectic_team_route_override
        daily_guard_scope = if ($result.daily_dialectic_advice) { [bool]$result.daily_dialectic_advice.scope_applicable } else { $false }
        daily_guard_confirm_required = if ($result.daily_dialectic_advice) { [bool]$result.daily_dialectic_advice.confirm_required } else { $false }
    }
    observability = if ($observabilityWrite) { $observabilityWrite } else { $null }
}

$probeArtifact = Write-RouteProbeArtifact -Context $probeContext -PromptText $Prompt -Result $result
if ($probeArtifact) {
    $result | Add-Member -NotePropertyName "probe_reference" -NotePropertyValue $probeArtifact
}

$result | ConvertTo-Json -Depth 12


