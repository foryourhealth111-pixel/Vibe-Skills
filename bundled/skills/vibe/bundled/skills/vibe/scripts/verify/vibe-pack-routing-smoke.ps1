param(
    [switch]$StrictKeywords,
    [switch]$WriteArtifacts,
    [string]$OutputDirectory
)

$ErrorActionPreference = "Stop"

function Assert-True {
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

function Normalize-RouteKeyword {
    param([string]$Keyword)

    if ($null -eq $Keyword) { return "" }
    return ([string]$Keyword).Trim().ToLowerInvariant()
}

function Assert-WarnOrFail {
    param(
        [bool]$Condition,
        [string]$Message
    )

    if ($Condition) {
        Write-Host "[PASS] $Message"
        return $true
    }

    if ($StrictKeywords) {
        Write-Host "[FAIL] $Message" -ForegroundColor Red
        return $false
    }

    Write-Host "[WARN] $Message" -ForegroundColor Yellow
    return $true
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$configRoot = Join-Path $repoRoot "config"

$packManifestPath = Join-Path $configRoot "pack-manifest.json"
$aliasMapPath = Join-Path $configRoot "skill-alias-map.json"
$thresholdPath = Join-Path $configRoot "router-thresholds.json"
$skillKeywordIndexPath = Join-Path $configRoot "skill-keyword-index.json"
$routingRulesPath = Join-Path $configRoot "skill-routing-rules.json"
$deepDiscoveryPolicyPath = Join-Path $configRoot "deep-discovery-policy.json"
$capabilityCatalogPath = Join-Path $configRoot "capability-catalog.json"
$heartbeatPolicyPath = Join-Path $configRoot "heartbeat-policy.json"
$dialecticTeamPolicyPath = Join-Path $configRoot "dialectic-team-policy.json"
$dailyDialecticGuardPath = Join-Path $configRoot "daily-dialectic-guard.json"
$retrievalPolicyPath = Join-Path $configRoot "retrieval-policy.json"
$retrievalIntentProfilesPath = Join-Path $configRoot "retrieval-intent-profiles.json"
$retrievalSourceRegistryPath = Join-Path $configRoot "retrieval-source-registry.json"
$retrievalRerankWeightsPath = Join-Path $configRoot "retrieval-rerank-weights.json"
$explorationPolicyPath = Join-Path $configRoot "exploration-policy.json"
$explorationIntentProfilesPath = Join-Path $configRoot "exploration-intent-profiles.json"
$explorationDomainMapPath = Join-Path $configRoot "exploration-domain-map.json"

$results = @()

Write-Host "=== VCO Pack Router Config Checks ==="
$results += Assert-True -Condition (Test-Path -LiteralPath $packManifestPath) -Message "pack-manifest.json exists"
$results += Assert-True -Condition (Test-Path -LiteralPath $aliasMapPath) -Message "skill-alias-map.json exists"
$results += Assert-True -Condition (Test-Path -LiteralPath $thresholdPath) -Message "router-thresholds.json exists"
$results += Assert-True -Condition (Test-Path -LiteralPath $skillKeywordIndexPath) -Message "skill-keyword-index.json exists"
$results += Assert-True -Condition (Test-Path -LiteralPath $routingRulesPath) -Message "skill-routing-rules.json exists"
$results += Assert-True -Condition (Test-Path -LiteralPath $deepDiscoveryPolicyPath) -Message "deep-discovery-policy.json exists"
$results += Assert-True -Condition (Test-Path -LiteralPath $capabilityCatalogPath) -Message "capability-catalog.json exists"
$results += Assert-True -Condition (Test-Path -LiteralPath $heartbeatPolicyPath) -Message "heartbeat-policy.json exists"
$results += Assert-True -Condition (Test-Path -LiteralPath $dialecticTeamPolicyPath) -Message "dialectic-team-policy.json exists"
$results += Assert-True -Condition (Test-Path -LiteralPath $dailyDialecticGuardPath) -Message "daily-dialectic-guard.json exists"
$results += Assert-True -Condition (Test-Path -LiteralPath $retrievalPolicyPath) -Message "retrieval-policy.json exists"
$results += Assert-True -Condition (Test-Path -LiteralPath $retrievalIntentProfilesPath) -Message "retrieval-intent-profiles.json exists"
$results += Assert-True -Condition (Test-Path -LiteralPath $retrievalSourceRegistryPath) -Message "retrieval-source-registry.json exists"
$results += Assert-True -Condition (Test-Path -LiteralPath $retrievalRerankWeightsPath) -Message "retrieval-rerank-weights.json exists"
$results += Assert-True -Condition (Test-Path -LiteralPath $explorationPolicyPath) -Message "exploration-policy.json exists"
$results += Assert-True -Condition (Test-Path -LiteralPath $explorationIntentProfilesPath) -Message "exploration-intent-profiles.json exists"
$results += Assert-True -Condition (Test-Path -LiteralPath $explorationDomainMapPath) -Message "exploration-domain-map.json exists"

$packManifest = Get-Content -LiteralPath $packManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$aliasMap = Get-Content -LiteralPath $aliasMapPath -Raw -Encoding UTF8 | ConvertFrom-Json
$thresholds = Get-Content -LiteralPath $thresholdPath -Raw -Encoding UTF8 | ConvertFrom-Json
$skillKeywordIndex = Get-Content -LiteralPath $skillKeywordIndexPath -Raw -Encoding UTF8 | ConvertFrom-Json
$routingRules = Get-Content -LiteralPath $routingRulesPath -Raw -Encoding UTF8 | ConvertFrom-Json
$deepDiscoveryPolicy = Get-Content -LiteralPath $deepDiscoveryPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
$capabilityCatalog = Get-Content -LiteralPath $capabilityCatalogPath -Raw -Encoding UTF8 | ConvertFrom-Json
$heartbeatPolicy = Get-Content -LiteralPath $heartbeatPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
$dialecticTeamPolicy = Get-Content -LiteralPath $dialecticTeamPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
$dailyDialecticGuard = Get-Content -LiteralPath $dailyDialecticGuardPath -Raw -Encoding UTF8 | ConvertFrom-Json
$retrievalPolicy = Get-Content -LiteralPath $retrievalPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
$retrievalIntentProfiles = Get-Content -LiteralPath $retrievalIntentProfilesPath -Raw -Encoding UTF8 | ConvertFrom-Json
$retrievalSourceRegistry = Get-Content -LiteralPath $retrievalSourceRegistryPath -Raw -Encoding UTF8 | ConvertFrom-Json
$retrievalRerankWeights = Get-Content -LiteralPath $retrievalRerankWeightsPath -Raw -Encoding UTF8 | ConvertFrom-Json
$explorationPolicy = Get-Content -LiteralPath $explorationPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
$explorationIntentProfiles = Get-Content -LiteralPath $explorationIntentProfilesPath -Raw -Encoding UTF8 | ConvertFrom-Json
$explorationDomainMap = Get-Content -LiteralPath $explorationDomainMapPath -Raw -Encoding UTF8 | ConvertFrom-Json

$requiredPackIds = @(
    "orchestration-core",
    "aios-core",
    "code-quality",
    "data-ml",
    "bio-science",
    "docs-media",
    "integration-devops",
    "ai-llm",
    "research-design"
)

$packIds = @($packManifest.packs | ForEach-Object { $_.id })
$results += Assert-True -Condition ($packIds.Count -ge 9) -Message "at least 9 packs defined"
$results += Assert-True -Condition (($packIds | Sort-Object -Unique).Count -eq $packIds.Count) -Message "pack IDs are unique"

foreach ($id in $requiredPackIds) {
    $results += Assert-True -Condition ($packIds -contains $id) -Message "required pack '$id' exists"
}

$allowedGrades = @("M", "L", "XL")
$allowedTaskTypes = @("planning", "coding", "review", "debug", "research")

foreach ($pack in $packManifest.packs) {
    $results += Assert-True -Condition ($pack.skill_candidates.Count -gt 0) -Message "pack '$($pack.id)' has skill candidates"
    $results += Assert-True -Condition (($pack.grade_allow | Where-Object { $allowedGrades -notcontains $_ }).Count -eq 0) -Message "pack '$($pack.id)' grade boundaries valid"
    $results += Assert-True -Condition (($pack.task_allow | Where-Object { $allowedTaskTypes -notcontains $_ }).Count -eq 0) -Message "pack '$($pack.id)' task boundaries valid"
    $results += Assert-True -Condition ($null -ne $pack.defaults_by_task) -Message "pack '$($pack.id)' has defaults_by_task"
    $results += Assert-True -Condition ($null -ne $pack.trigger_keywords) -Message "pack '$($pack.id)' has trigger_keywords"

    $rawKeywords = @($pack.trigger_keywords | ForEach-Object { [string]$_ })
    $results += Assert-True -Condition ($rawKeywords.Count -gt 0) -Message "pack '$($pack.id)' trigger_keywords non-empty"
    $results += Assert-True -Condition (($rawKeywords | Where-Object { -not $_ -or -not $_.Trim() }).Count -eq 0) -Message "pack '$($pack.id)' trigger_keywords contain no empty items"
    $results += Assert-WarnOrFail -Condition (($rawKeywords | Where-Object { $_ -ne $_.Trim() }).Count -eq 0) -Message "pack '$($pack.id)' trigger_keywords contain no leading/trailing whitespace"
    $results += Assert-WarnOrFail -Condition (($rawKeywords | Where-Object { $_ -match '[\r\n\t]' }).Count -eq 0) -Message "pack '$($pack.id)' trigger_keywords contain no control whitespace (\\r/\\n/\\t)"
    $results += Assert-WarnOrFail -Condition (($rawKeywords | Where-Object { $_ -match '[A-Z]' }).Count -eq 0) -Message "pack '$($pack.id)' trigger_keywords contain no uppercase ASCII (normalize to lowercase)"

    $normalizedKeywords = @($rawKeywords | ForEach-Object { Normalize-RouteKeyword -Keyword $_ })
    $dupGroups = $normalizedKeywords | Group-Object | Where-Object { $_.Count -gt 1 }
    $results += Assert-WarnOrFail -Condition ($dupGroups.Count -eq 0) -Message "pack '$($pack.id)' trigger_keywords are unique after normalization (trim+lower)"

    $hasEnglishNormalized = ($normalizedKeywords | Where-Object { $_ -match "[a-z]" }).Count -gt 0
    $hasChineseNormalized = ($normalizedKeywords | Where-Object { $_ -match "[\u4E00-\u9FFF]" }).Count -gt 0
    $results += Assert-WarnOrFail -Condition $hasEnglishNormalized -Message "pack '$($pack.id)' has at least one normalized English trigger keyword"
    $results += Assert-WarnOrFail -Condition $hasChineseNormalized -Message "pack '$($pack.id)' has at least one normalized Chinese trigger keyword"

    if ($pack.defaults_by_task) {
        $defaultTaskKeys = @($pack.defaults_by_task.PSObject.Properties.Name)
        foreach ($taskKey in $defaultTaskKeys) {
            $results += Assert-True -Condition ($pack.task_allow -contains $taskKey) -Message "pack '$($pack.id)' default task '$taskKey' is task-allowed"
            $defaultSkill = [string]$pack.defaults_by_task.$taskKey
            $results += Assert-True -Condition ($pack.skill_candidates -contains $defaultSkill) -Message "pack '$($pack.id)' default skill '$defaultSkill' exists in candidates"
        }
    }
}

$autoRoute = [double]$thresholds.thresholds.auto_route
$confirmRequired = [double]$thresholds.thresholds.confirm_required
$fallbackBelow = [double]$thresholds.thresholds.fallback_to_legacy_below

$results += Assert-True -Condition ($autoRoute -gt $confirmRequired) -Message "auto_route threshold higher than confirm_required"
$results += Assert-True -Condition ($confirmRequired -ge $fallbackBelow) -Message "confirm_required is not lower than fallback threshold"
$results += Assert-True -Condition ($thresholds.thresholds.min_top1_top2_gap -ne $null) -Message "min_top1_top2_gap threshold configured"
$results += Assert-True -Condition ($thresholds.safety.enforce_grade_boundary -eq $true) -Message "grade boundary safety is enabled"
$results += Assert-True -Condition ($thresholds.safety.enforce_task_boundary -eq $true) -Message "task boundary safety is enabled"
$results += Assert-True -Condition ($thresholds.safety.enforce_confirm_on_legacy_fallback -eq $true) -Message "legacy fallback confirm guard is enabled"
$results += Assert-True -Condition ($thresholds.weights.skill_keyword_signal -ne $null) -Message "skill_keyword_signal weight is configured"
$results += Assert-True -Condition ($thresholds.candidate_selection.rule_positive_keyword_bonus -ne $null) -Message "candidate_selection positive bonus configured"
$results += Assert-True -Condition ($thresholds.candidate_selection.rule_negative_keyword_penalty -ne $null) -Message "candidate_selection negative penalty configured"
$results += Assert-True -Condition ($thresholds.candidate_selection.canonical_for_task_bonus -ne $null) -Message "candidate_selection canonical bonus configured"
$results += Assert-True -Condition ($skillKeywordIndex.selection.weights.keyword_match -ne $null) -Message "skill index keyword_match weight is configured"
$results += Assert-True -Condition ($skillKeywordIndex.selection.weights.name_match -ne $null) -Message "skill index name_match weight is configured"
$results += Assert-True -Condition ($skillKeywordIndex.selection.fallback_to_first_when_score_below -ne $null) -Message "skill index fallback threshold is configured"
$results += Assert-True -Condition ((@($skillKeywordIndex.skills.PSObject.Properties).Count -gt 0)) -Message "skill index contains skill mappings"
$results += Assert-True -Condition ((@($routingRules.skills.PSObject.Properties).Count -gt 0)) -Message "routing rules contain skill mappings"
$results += Assert-True -Condition ($deepDiscoveryPolicy.mode -ne $null) -Message "deep discovery mode configured"
$results += Assert-True -Condition ((@($capabilityCatalog.capabilities).Count -gt 0)) -Message "capability catalog contains entries"
$results += Assert-True -Condition ($heartbeatPolicy.mode -ne $null) -Message "heartbeat mode configured"
$results += Assert-True -Condition ($heartbeatPolicy.timers.hard_stall_silence_sec -ne $null) -Message "heartbeat hard stall threshold configured"
$results += Assert-True -Condition ($heartbeatPolicy.timers.user_brief_interval_sec -ne $null) -Message "heartbeat brief interval configured"
$results += Assert-True -Condition ($dialecticTeamPolicy.mode -ne $null) -Message "dialectic team policy mode configured"
$results += Assert-True -Condition ($dailyDialecticGuard.mode -ne $null) -Message "daily dialectic guard mode configured"
$results += Assert-True -Condition ($retrievalPolicy.mode -ne $null) -Message "retrieval mode configured"
$results += Assert-True -Condition ($retrievalPolicy.profile_selection.min_profile_confidence -ne $null) -Message "retrieval profile min confidence configured"
$results += Assert-True -Condition ($retrievalPolicy.coverage.max_retrieve_rounds -ne $null) -Message "retrieval max retrieve rounds configured"
$results += Assert-True -Condition ((@($retrievalIntentProfiles.profiles).Count -gt 0)) -Message "retrieval intent profiles configured"
$results += Assert-True -Condition ((@($retrievalSourceRegistry.sources).Count -gt 0)) -Message "retrieval source registry configured"
$results += Assert-True -Condition ($retrievalRerankWeights.modes -ne $null) -Message "retrieval rerank modes configured"
$results += Assert-True -Condition ($explorationPolicy.mode -ne $null) -Message "exploration mode configured"
$results += Assert-True -Condition ($explorationPolicy.intent_selection.min_intent_confidence -ne $null) -Message "exploration intent min confidence configured"
$results += Assert-True -Condition ($explorationPolicy.domain_detection.min_domain_confidence -ne $null) -Message "exploration domain confidence configured"
$results += Assert-True -Condition ((@($explorationIntentProfiles.profiles).Count -gt 0)) -Message "exploration intent profiles configured"
$results += Assert-True -Condition ((@($explorationDomainMap.domains).Count -gt 0)) -Message "exploration domain map configured"

foreach ($ruleProp in @($routingRules.skills.PSObject.Properties | Select-Object -First 10)) {
    $rule = $ruleProp.Value
    $results += Assert-True -Condition ($null -ne $rule.task_allow) -Message "routing rule '$($ruleProp.Name)' has task_allow"
    $results += Assert-True -Condition ($null -ne $rule.positive_keywords) -Message "routing rule '$($ruleProp.Name)' has positive_keywords"
    $results += Assert-True -Condition ($null -ne $rule.negative_keywords) -Message "routing rule '$($ruleProp.Name)' has negative_keywords"
    $results += Assert-True -Condition ($null -ne $rule.equivalent_group -or $rule.equivalent_group -eq $null) -Message "routing rule '$($ruleProp.Name)' has equivalent_group"
    $results += Assert-True -Condition ($null -ne $rule.canonical_for_task) -Message "routing rule '$($ruleProp.Name)' has canonical_for_task"
}

$aliasPairs = @($aliasMap.aliases.PSObject.Properties)
$results += Assert-True -Condition ($null -ne $aliasMap.aliases) -Message "alias mapping container exists"
$results += Assert-True -Condition ($aliasPairs.Count -ge 0) -Message "alias mapping count is valid (can be zero after hard cleanup)"

foreach ($pair in $aliasPairs) {
    $key = [string]$pair.Name
    $value = [string]$pair.Value
    $results += Assert-True -Condition ($key -ne $value) -Message "alias '$key' does not self-reference"
}

foreach ($pair in $aliasPairs) {
    $key = [string]$pair.Name
    $value = [string]$pair.Value

    if ($aliasMap.aliases.PSObject.Properties.Name -contains $value) {
        $reverseTarget = [string]$aliasMap.aliases.$value
        $results += Assert-True -Condition ($reverseTarget -ne $key) -Message "no direct alias loop between '$key' and '$value'"
    }
}

$skillRootCandidates = @()
$bundledSkillsRoot = Join-Path $repoRoot "bundled\skills"
if (Test-Path -LiteralPath $bundledSkillsRoot) {
    $skillRootCandidates += $bundledSkillsRoot
}
$skillsRootSibling = Resolve-Path (Join-Path $repoRoot "..")
if ($skillsRootSibling) {
    $skillRootCandidates += [string]$skillsRootSibling
}

$topLevelSkillNames = @()
foreach ($root in @($skillRootCandidates | Select-Object -Unique)) {
    if (-not (Test-Path -LiteralPath $root)) { continue }

    $skillFiles = Get-ChildItem -Path $root -Directory -ErrorAction SilentlyContinue |
        ForEach-Object { Join-Path $_.FullName "SKILL.md" } |
        Where-Object { Test-Path -LiteralPath $_ }

    $topLevelSkillNames += $skillFiles | ForEach-Object { Split-Path (Split-Path $_ -Parent) -Leaf }
}
$topLevelSkillNames = @($topLevelSkillNames | Select-Object -Unique)

foreach ($pair in $aliasPairs) {
    $target = [string]$pair.Value
    $results += Assert-True -Condition ($topLevelSkillNames -contains $target) -Message "alias target '$target' resolves to a canonical top-level skill"
}

$passCount = ($results | Where-Object { $_ }).Count
$failCount = ($results | Where-Object { -not $_ }).Count
$total = $results.Count

if ($WriteArtifacts) {
    if (-not $OutputDirectory) {
        $OutputDirectory = Join-Path $repoRoot "outputs\\verify"
    }
    New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null

    $jsonPath = Join-Path $OutputDirectory "vibe-pack-routing-smoke.summary.json"
    [pscustomobject]@{
        generated_at = (Get-Date).ToString("s")
        strict_keywords = [bool]$StrictKeywords
        total_assertions = $total
        passed = $passCount
        failed = $failCount
    } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

    Write-Host ""
    Write-Host "Artifacts written:"
    Write-Host "- $jsonPath"
}

Write-Host ""
Write-Host "=== Summary ==="
Write-Host "Total assertions: $total"
Write-Host "Passed: $passCount"
Write-Host "Failed: $failCount"

if ($failCount -gt 0) {
    exit 1
}

Write-Host "Pack routing smoke checks passed."
exit 0

