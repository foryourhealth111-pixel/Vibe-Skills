param(
    [switch]$Strict,
    [switch]$WriteArtifacts,
    [string]$OutputDirectory
)

$ErrorActionPreference = "Stop"

function Invoke-Route {
    param(
        [string]$Prompt,
        [string]$Grade,
        [string]$TaskType,
        [string]$RequestedSkill
    )

    $repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
    $resolver = Join-Path $repoRoot "scripts\router\resolve-pack-route.ps1"

    $routeArgs = @{
        Prompt = $Prompt
        Grade = $Grade
        TaskType = $TaskType
    }
    if ($RequestedSkill) {
        $routeArgs["RequestedSkill"] = $RequestedSkill
    }

    $json = & $resolver @routeArgs
    return ($json | ConvertFrom-Json)
}

function New-TestCase {
    param(
        [string]$Group,
        [string]$Prompt,
        [string]$Grade,
        [string]$TaskType,
        [string]$ExpectedPack,
        [string]$RequestedSkill
    )

    return [pscustomobject]@{
        group = $Group
        prompt = $Prompt
        grade = $Grade
        task_type = $TaskType
        expected_pack = $ExpectedPack
        requested_skill = $RequestedSkill
    }
}

function Get-SelectedRouteInfo {
    param([object]$Route)

    $selected = $null
    if ($Route -and ($Route.PSObject.Properties.Name -contains "selected")) {
        $selected = @($Route.selected)[0]
    }

    $packId = $null
    $skill = $null
    $selectionReason = $null
    if ($selected) {
        if ($selected.PSObject.Properties.Name -contains "pack_id") {
            $packId = [string]$selected.pack_id
        }
        if ($selected.PSObject.Properties.Name -contains "skill") {
            $skill = [string]$selected.skill
        }
        if ($selected.PSObject.Properties.Name -contains "selection_reason") {
            $selectionReason = [string]$selected.selection_reason
        }
    }

    return [pscustomobject]@{
        pack_id = $packId
        skill = $skill
        selection_reason = $selectionReason
    }
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$thresholdPath = Join-Path $repoRoot "config\router-thresholds.json"
$thresholds = Get-Content -LiteralPath $thresholdPath -Raw -Encoding UTF8 | ConvertFrom-Json
$minGapBaseline = if ($thresholds -and ($thresholds.PSObject.Properties.Name -contains "thresholds") -and $thresholds.thresholds -and ($thresholds.thresholds.PSObject.Properties.Name -contains "min_top1_top2_gap")) {
    [double]$thresholds.thresholds.min_top1_top2_gap
} else {
    0.06
}

$testCases = @(
    # Synonym groups (same task/grade)
    (New-TestCase -Group "orchestration-planning" -Prompt "create implementation plan and task breakdown" -Grade "L" -TaskType "planning" -ExpectedPack "orchestration-core"),
    (New-TestCase -Group "orchestration-planning" -Prompt "请输出实施计划和任务拆解" -Grade "L" -TaskType "planning" -ExpectedPack "orchestration-core"),
    (New-TestCase -Group "orchestration-planning" -Prompt "need milestone roadmap and execution plan" -Grade "L" -TaskType "planning" -ExpectedPack "orchestration-core"),

    (New-TestCase -Group "code-quality-review" -Prompt "run code review and quality checks" -Grade "M" -TaskType "review" -ExpectedPack "code-quality"),
    (New-TestCase -Group "code-quality-review" -Prompt "做一次代码评审和质量检查" -Grade "M" -TaskType "review" -ExpectedPack "code-quality"),
    (New-TestCase -Group "code-quality-review" -Prompt "review this change for maintainability and bugs" -Grade "M" -TaskType "review" -ExpectedPack "code-quality"),

    (New-TestCase -Group "data-ml-research" -Prompt "train classification model with scikit-learn and evaluate metrics" -Grade "L" -TaskType "research" -ExpectedPack "data-ml"),
    (New-TestCase -Group "data-ml-research" -Prompt "用scikit-learn训练分类模型并评估" -Grade "L" -TaskType "research" -ExpectedPack "data-ml"),
    (New-TestCase -Group "data-ml-research" -Prompt "machine learning feature engineering and model evaluation" -Grade "L" -TaskType "research" -ExpectedPack "data-ml"),

    (New-TestCase -Group "docs-media-coding-xlsx" -Prompt "edit xlsx workbook and preserve formulas" -Grade "M" -TaskType "coding" -ExpectedPack "docs-media"),
    (New-TestCase -Group "docs-media-coding-xlsx" -Prompt "修改电子表格并保留公式" -Grade "M" -TaskType "coding" -ExpectedPack "docs-media"),
    (New-TestCase -Group "docs-media-coding-xlsx" -Prompt "apply xlsx workbook formatting with formula-safe updates" -Grade "M" -TaskType "coding" -ExpectedPack "docs-media"),
    (New-TestCase -Group "docs-media-coding-tabular" -Prompt "process spreadsheet csv formatting and column cleanup" -Grade "M" -TaskType "coding" -ExpectedPack "docs-media"),
    (New-TestCase -Group "docs-media-coding-tabular" -Prompt "整理csv/tsv表格并统一字段格式" -Grade "M" -TaskType "coding" -ExpectedPack "docs-media"),

    (New-TestCase -Group "integration-devops-ci-debug" -Prompt "debug github actions ci pipeline failure" -Grade "L" -TaskType "debug" -ExpectedPack "integration-devops"),
    (New-TestCase -Group "integration-devops-ci-debug" -Prompt "排查CI流水线失败并检查日志" -Grade "L" -TaskType "debug" -ExpectedPack "integration-devops"),
    (New-TestCase -Group "integration-devops-ci-debug" -Prompt "investigate github actions workflow logs for failed ci pipeline" -Grade "L" -TaskType "debug" -ExpectedPack "integration-devops"),
    (New-TestCase -Group "integration-devops-sentry-debug" -Prompt "investigate sentry production errors and deployment issues" -Grade "L" -TaskType "debug" -ExpectedPack "integration-devops"),
    (New-TestCase -Group "integration-devops-sentry-debug" -Prompt "排查Sentry线上告警并汇总生产错误根因" -Grade "L" -TaskType "debug" -ExpectedPack "integration-devops"),

    (New-TestCase -Group "ai-llm-research-openai-docs" -Prompt "look up OpenAI Responses API docs" -Grade "M" -TaskType "research" -ExpectedPack "ai-llm"),
    (New-TestCase -Group "ai-llm-research-openai-docs" -Prompt "查询OpenAI官方文档和模型限制" -Grade "M" -TaskType "research" -ExpectedPack "ai-llm"),
    (New-TestCase -Group "ai-llm-research-openai-docs" -Prompt "need official OpenAI API reference for chat completions and limits" -Grade "M" -TaskType "research" -ExpectedPack "ai-llm"),
    (New-TestCase -Group "ai-llm-research-embedding" -Prompt "need embedding strategy for semantic retrieval" -Grade "M" -TaskType "research" -ExpectedPack "ai-llm"),
    (New-TestCase -Group "ai-llm-research-embedding" -Prompt "design chunking and embedding pipeline for vector search" -Grade "M" -TaskType "research" -ExpectedPack "ai-llm"),
    (New-TestCase -Group "ai-llm-research-embedding" -Prompt "向量检索场景下如何设计embedding策略和分块" -Grade "M" -TaskType "research" -ExpectedPack "ai-llm"),

    (New-TestCase -Group "research-design-planning" -Prompt "design quasi-experiment with DiD and ITS" -Grade "L" -TaskType "planning" -ExpectedPack "research-design"),
    (New-TestCase -Group "research-design-planning" -Prompt "设计准实验方案，比较DiD和ITS" -Grade "L" -TaskType "planning" -ExpectedPack "research-design"),
    (New-TestCase -Group "research-design-planning" -Prompt "research methodology and experimental design" -Grade "L" -TaskType "planning" -ExpectedPack "research-design"),

    (New-TestCase -Group "aios-core-planning-pm" -Prompt "create PRD and backlog with user stories" -Grade "L" -TaskType "planning" -ExpectedPack "aios-core"),
    (New-TestCase -Group "aios-core-planning-pm" -Prompt "输出用户故事和产品需求文档" -Grade "L" -TaskType "planning" -ExpectedPack "aios-core"),
    (New-TestCase -Group "aios-core-planning-pm" -Prompt "draft product roadmap and PRD scope for next release" -Grade "L" -TaskType "planning" -ExpectedPack "aios-core"),
    (New-TestCase -Group "aios-core-planning-po" -Prompt "product owner style backlog prioritization and acceptance criteria" -Grade "L" -TaskType "planning" -ExpectedPack "aios-core"),
    (New-TestCase -Group "aios-core-planning-po" -Prompt "按PO视角做backlog优先级排序和验收标准" -Grade "L" -TaskType "planning" -ExpectedPack "aios-core"),

    # Task-type cross checks
    (New-TestCase -Group "cross-ml-planning" -Prompt "build ML workflow and rollout plan" -Grade "L" -TaskType "planning" -ExpectedPack "data-ml"),
    (New-TestCase -Group "cross-ml-coding" -Prompt "build ML workflow and rollout plan" -Grade "L" -TaskType "coding" -ExpectedPack "data-ml"),
    (New-TestCase -Group "cross-ml-review" -Prompt "build ML workflow and rollout plan" -Grade "L" -TaskType "review" -ExpectedPack "data-ml"),

    (New-TestCase -Group "cross-devops-planning" -Prompt "integrate MCP server and CI pipeline" -Grade "L" -TaskType "planning" -ExpectedPack "integration-devops"),
    (New-TestCase -Group "cross-devops-coding" -Prompt "integrate MCP server and CI pipeline" -Grade "L" -TaskType "coding" -ExpectedPack "integration-devops"),
    (New-TestCase -Group "cross-devops-debug" -Prompt "integrate MCP server and CI pipeline" -Grade "L" -TaskType "debug" -ExpectedPack "integration-devops"),

    # Low-signal baseline
    (New-TestCase -Group "low-signal" -Prompt "help me with this" -Grade "M" -TaskType "research" -ExpectedPack $null)
)

$results = @()
foreach ($case in $testCases) {
    $route = Invoke-Route -Prompt $case.prompt -Grade $case.grade -TaskType $case.task_type -RequestedSkill $case.requested_skill
    $selected = Get-SelectedRouteInfo -Route $route
    $selectedPack = $selected.pack_id
    $selectedSkill = $selected.skill
    $selectionReason = $selected.selection_reason

    $isMisroute = $false
    if ($case.expected_pack) {
        $isMisroute = ($selectedPack -ne $case.expected_pack)
    } else {
        $isMisroute = ($route.route_mode -ne "legacy_fallback")
    }

    $isFallback = ($route.route_mode -eq "legacy_fallback")

    $results += [pscustomobject]@{
        group = $case.group
        prompt = $case.prompt
        grade = $case.grade
        task_type = $case.task_type
        expected_pack = $case.expected_pack
        route_mode = [string]$route.route_mode
        route_reason = [string]$route.route_reason
        selected_pack = $selectedPack
        selected_skill = $selectedSkill
        selection_reason = $selectionReason
        confidence = [double]$route.confidence
        top1_top2_gap = [double]$route.top1_top2_gap
        is_fallback = $isFallback
        is_misroute = $isMisroute
    }
}

$groupStabilityRows = @()
$stabilityValues = @()
$groups = $results | Group-Object -Property group
foreach ($group in $groups) {
    $groupRows = @($group.Group)
    if ($groupRows.Count -le 1) {
        continue
    }

    $labels = @($groupRows | ForEach-Object { "$($_.selected_pack)|$($_.selected_skill)" })
    $labelCounts = @($labels | Group-Object | Sort-Object -Property Count -Descending)
    $dominant = @($labelCounts | Select-Object -First 1)[0]
    $stability = if ($groupRows.Count -gt 0) { [double]$dominant.Count / [double]$groupRows.Count } else { 0.0 }

    $groupStabilityRows += [pscustomobject]@{
        group = $group.Name
        total = $groupRows.Count
        dominant_route = [string]$dominant.Name
        stability = [Math]::Round($stability, 4)
    }
    $stabilityValues += $stability
}

$routeStability = if (@($stabilityValues).Count -gt 0) { (@($stabilityValues) | Measure-Object -Average).Average } else { 1.0 }
$avgGap = ($results | Measure-Object -Property top1_top2_gap -Average).Average
$fallbackCases = @($results | Where-Object { $_.is_fallback })
$misrouteCases = @($results | Where-Object { $_.is_misroute })
$fallbackRate = $fallbackCases.Count / [double]$results.Count
$misrouteRate = $misrouteCases.Count / [double]$results.Count

$defaultGate = [pscustomobject]@{
    route_stability_min = 0.75
    top1_top2_gap_min = [Math]::Max(0.05, $minGapBaseline * 0.85)
    fallback_rate_max = 0.85
    misroute_rate_max = 0.30
}
$strictGate = [pscustomobject]@{
    route_stability_min = 0.88
    top1_top2_gap_min = $minGapBaseline
    fallback_rate_max = 0.30
    misroute_rate_max = 0.15
}
$gate = if ($Strict) { $strictGate } else { $defaultGate }

$gateChecks = [pscustomobject]@{
    route_stability = ([double]$routeStability -ge [double]$gate.route_stability_min)
    top1_top2_gap = ([double]$avgGap -ge [double]$gate.top1_top2_gap_min)
    fallback_rate = ([double]$fallbackRate -le [double]$gate.fallback_rate_max)
    misroute_rate = ([double]$misrouteRate -le [double]$gate.misroute_rate_max)
}

$gatePassed = $gateChecks.route_stability -and $gateChecks.top1_top2_gap -and $gateChecks.fallback_rate -and $gateChecks.misroute_rate
$strictChecks = [pscustomobject]@{
    route_stability = ([double]$routeStability -ge [double]$strictGate.route_stability_min)
    top1_top2_gap = ([double]$avgGap -ge [double]$strictGate.top1_top2_gap_min)
    fallback_rate = ([double]$fallbackRate -le [double]$strictGate.fallback_rate_max)
    misroute_rate = ([double]$misrouteRate -le [double]$strictGate.misroute_rate_max)
}
$strictReady = $strictChecks.route_stability -and $strictChecks.top1_top2_gap -and $strictChecks.fallback_rate -and $strictChecks.misroute_rate

Write-Host "=== VCO Routing Stability Gate ==="
Write-Host "Mode: $(if ($Strict) { 'strict' } else { 'default' })"
Write-Host ""
Write-Host ("route_stability: {0:N4} (>= {1:N4}) => {2}" -f $routeStability, $gate.route_stability_min, $(if ($gateChecks.route_stability) { 'PASS' } else { 'FAIL' }))
Write-Host ("top1_top2_gap: {0:N4} (>= {1:N4}) => {2}" -f $avgGap, $gate.top1_top2_gap_min, $(if ($gateChecks.top1_top2_gap) { 'PASS' } else { 'FAIL' }))
Write-Host ("fallback_rate: {0:N4} (<= {1:N4}) => {2}" -f $fallbackRate, $gate.fallback_rate_max, $(if ($gateChecks.fallback_rate) { 'PASS' } else { 'FAIL' }))
Write-Host ("misroute_rate: {0:N4} (<= {1:N4}) => {2}" -f $misrouteRate, $gate.misroute_rate_max, $(if ($gateChecks.misroute_rate) { 'PASS' } else { 'FAIL' }))
Write-Host ""
Write-Host ("Gate Result: {0}" -f $(if ($gatePassed) { 'PASS' } else { 'FAIL' }))
if (-not $Strict) {
    Write-Host ("Stricter Rules Ready: {0}" -f $(if ($strictReady) { 'YES' } else { 'NO' }))
}

$report = [pscustomobject]@{
    mode = if ($Strict) { "strict" } else { "default" }
    generated_at = (Get-Date).ToString("s")
    metrics = [pscustomobject]@{
        route_stability = [Math]::Round([double]$routeStability, 4)
        top1_top2_gap = [Math]::Round([double]$avgGap, 4)
        fallback_rate = [Math]::Round([double]$fallbackRate, 4)
        misroute_rate = [Math]::Round([double]$misrouteRate, 4)
    }
    thresholds = $gate
    gate_checks = $gateChecks
    gate_passed = $gatePassed
    stricter_rules_ready = $strictReady
    strict_gate_checks = $strictChecks
    group_stability = $groupStabilityRows
    total_cases = $results.Count
    cases = $results
}

if ($WriteArtifacts) {
    if (-not $OutputDirectory) {
        $OutputDirectory = Join-Path $repoRoot "outputs\verify"
    }
    New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null

    $jsonPath = Join-Path $OutputDirectory "vibe-routing-stability-gate.json"
    $mdPath = Join-Path $OutputDirectory "vibe-routing-stability-gate.md"

    $report | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

    $lines = @()
    $lines += "# VCO Routing Stability Gate"
    $lines += ""
    $lines += "- Mode: ``$($report.mode)``"
    $lines += "- Generated: ``$($report.generated_at)``"
    $lines += "- Gate Passed: ``$($report.gate_passed)``"
    $lines += "- Stricter Rules Ready: ``$($report.stricter_rules_ready)``"
    $lines += ""
    $lines += "## Metrics"
    $lines += ""
    $lines += "- route_stability: ``$($report.metrics.route_stability)`` (threshold ``$($report.thresholds.route_stability_min)``)"
    $lines += "- top1_top2_gap: ``$($report.metrics.top1_top2_gap)`` (threshold ``$($report.thresholds.top1_top2_gap_min)``)"
    $lines += "- fallback_rate: ``$($report.metrics.fallback_rate)`` (threshold ``$($report.thresholds.fallback_rate_max)``)"
    $lines += "- misroute_rate: ``$($report.metrics.misroute_rate)`` (threshold ``$($report.thresholds.misroute_rate_max)``)"
    $lines += ""
    $lines += "## Group Stability"
    $lines += ""
    foreach ($row in $groupStabilityRows) {
        $lines += "- ``$($row.group)``: stability=``$($row.stability)`` dominant=``$($row.dominant_route)``"
    }

    $lines -join "`n" | Set-Content -LiteralPath $mdPath -Encoding UTF8
    Write-Host "Artifacts written:"
    Write-Host "- $jsonPath"
    Write-Host "- $mdPath"
}

if (-not $gatePassed) {
    exit 1
}

exit 0
