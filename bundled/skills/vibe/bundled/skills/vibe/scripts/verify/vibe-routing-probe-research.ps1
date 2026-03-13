param(
    [string]$OutputDirectory,
    [switch]$DefaultIncludePrompt,
    [switch]$KeepFixtures
)

$ErrorActionPreference = "Stop"

function New-SmallCsvFixture {
    param([string]$Path)

    New-Item -ItemType Directory -Path (Split-Path -Parent $Path) -Force | Out-Null
    @(
        "city,product,amount",
        "shanghai,A,10",
        "shanghai,A,10",
        "beijing,B,20",
        "shenzhen,C,30",
        "beijing,B,20"
    ) | Set-Content -LiteralPath $Path -Encoding UTF8
}

function New-MediumSignalCsvFixture {
    param(
        [string]$Path,
        [int]$TargetBytes = 20971520
    )

    New-Item -ItemType Directory -Path (Split-Path -Parent $Path) -Force | Out-Null

    $writer = [System.IO.StreamWriter]::new($Path, $false, [System.Text.Encoding]::UTF8)
    try {
        $writer.WriteLine("city,product,amount")
        for ($i = 0; $i -lt 500; $i++) {
            $city = switch ($i % 4) {
                0 { "shanghai" }
                1 { "beijing" }
                2 { "shenzhen" }
                default { "hangzhou" }
            }
            $product = [char](65 + ($i % 5))
            $amount = (($i % 97) + 3)
            $writer.WriteLine([string]::Format("{0},{1},{2}", $city, $product, $amount))
        }
        $writer.Flush()

        $chunk = ("x" * 65536)
        while ((Get-Item -LiteralPath $Path).Length -lt $TargetBytes) {
            $writer.Write($chunk)
        }
    } finally {
        $writer.Dispose()
    }
}

function New-PythonFixture {
    param([string]$Path)

    New-Item -ItemType Directory -Path (Split-Path -Parent $Path) -Force | Out-Null
    @(
        "class GodObject:",
        "    def process(self, data, verbose=False):",
        "        result = []",
        "        for row in data:",
        "            if verbose:",
        "                print(row)",
        "            result.append(row)",
        "        return result"
    ) | Set-Content -LiteralPath $Path -Encoding UTF8
}

function New-CudaFixture {
    param([string]$Path)

    New-Item -ItemType Directory -Path (Split-Path -Parent $Path) -Force | Out-Null
    @(
        "__global__ void saxpy(int n, float a, float* x, float* y) {",
        "    int i = blockIdx.x * blockDim.x + threadIdx.x;",
        "    if (i < n) y[i] = a * x[i] + y[i];",
        "}",
        "",
        "int launch(int n, float a, float* x, float* y) {",
        "    saxpy<<<(n + 255) / 256, 256>>>(n, a, x, y);",
        "    return 0;",
        "}"
    ) | Set-Content -LiteralPath $Path -Encoding UTF8
}

function New-XlsxPlaceholder {
    param([string]$Path)

    New-Item -ItemType Directory -Path (Split-Path -Parent $Path) -Force | Out-Null
    # Placeholder content to provide a real .xlsx path signal for router probes.
    "PK`u0003`u0004PLACEHOLDER-XLSX" | Set-Content -LiteralPath $Path -Encoding UTF8
}

function Get-AdviceDigest {
    param([object]$Advice)

    if (-not $Advice) { return $null }
    $keys = @($Advice.PSObject.Properties.Name)
    $digest = [ordered]@{}
    $interesting = @(
        "enabled",
        "mode",
        "scope_applicable",
        "enforcement",
        "reason",
        "confirm_required",
        "auto_override",
        "override_candidate_allowed",
        "recommended_skill",
        "confidence",
        "route_override_applied",
        "would_override",
        "override_target_pack",
        "override_target_skill"
    )

    foreach ($key in $interesting) {
        if ($keys -contains $key) {
            $digest[$key] = $Advice.$key
        }
    }

    return [pscustomobject]$digest
}

function Test-StageOrder {
    param(
        [string[]]$Expected,
        [string[]]$Actual
    )

    if (-not $Expected -or $Expected.Count -eq 0) { return $true }
    if (-not $Actual -or $Actual.Count -eq 0) { return $false }

    $cursor = -1
    foreach ($stage in $Expected) {
        $idx = [Array]::IndexOf($Actual, $stage)
        if ($idx -lt 0) { return $false }
        if ($idx -lt $cursor) { return $false }
        $cursor = $idx
    }

    return $true
}

function Get-DistributionObject {
    param(
        [object[]]$Rows,
        [string]$PropertyName
    )

    $distribution = [ordered]@{}
    foreach ($group in ($Rows | Group-Object -Property $PropertyName | Sort-Object Count -Descending)) {
        $distribution[[string]$group.Name] = [int]$group.Count
    }
    return [pscustomobject]$distribution
}

function Get-GroupMetrics {
    param(
        [object[]]$Rows,
        [string]$ScenarioGroup
    )

    $items = @($Rows | Where-Object { [string]$_.scenario_group -eq $ScenarioGroup })
    if ($items.Count -eq 0) {
        return [pscustomobject]@{
            scenario_group = $ScenarioGroup
            case_count = 0
            avg_confidence = 0.0
            avg_top1_top2_gap = 0.0
            confirm_required_ratio = 0.0
            pack_diversity = 0
            route_mode_distribution = [pscustomobject]@{}
        }
    }

    $avgConfidence = [Math]::Round([double](($items | Measure-Object -Property confidence -Average).Average), 4)
    $avgGap = [Math]::Round([double](($items | Measure-Object -Property top1_top2_gap -Average).Average), 4)
    $confirmCount = @($items | Where-Object { [string]$_.route_mode -eq "confirm_required" }).Count
    $confirmRatio = [Math]::Round(([double]$confirmCount / [double]$items.Count), 4)
    $packDiversity = @($items | ForEach-Object { [string]$_.selected_pack } | Sort-Object -Unique).Count

    return [pscustomobject]@{
        scenario_group = $ScenarioGroup
        case_count = $items.Count
        avg_confidence = $avgConfidence
        avg_top1_top2_gap = $avgGap
        confirm_required_ratio = $confirmRatio
        pack_diversity = $packDiversity
        route_mode_distribution = Get-DistributionObject -Rows $items -PropertyName "route_mode"
    }
}

function Get-OverlayStats {
    param(
        [object[]]$Rows,
        [string[]]$OverlayNames
    )

    $stats = @()
    foreach ($overlay in $OverlayNames) {
        $scopeCount = 0
        $confirmCount = 0
        $reasonCountMap = [ordered]@{}

        foreach ($row in $Rows) {
            $digest = $row.overlay_digests.$overlay
            if (-not $digest) { continue }

            if ($digest.scope_applicable -eq $true) { $scopeCount++ }
            if ($digest.confirm_required -eq $true) { $confirmCount++ }

            if ($digest.reason) {
                $key = [string]$digest.reason
                if ($reasonCountMap.Contains($key)) {
                    $reasonCountMap[$key] = [int]$reasonCountMap[$key] + 1
                } else {
                    $reasonCountMap[$key] = 1
                }
            }
        }

        $topReason = ""
        if ($reasonCountMap.Count -gt 0) {
            $topReason = ($reasonCountMap.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 1 | ForEach-Object { "{0}({1})" -f $_.Key, $_.Value })
        }

        $stats += [pscustomobject]@{
            overlay = $overlay
            scope_applicable_count = $scopeCount
            confirm_required_count = $confirmCount
            top_reason = $topReason
        }
    }
    return @($stats)
}

function Write-ResearchMarkdown {
    param(
        [string]$Path,
        [object]$Summary
    )

    $lines = @()
    $lines += "# VCO Routing Probe Research Report"
    $lines += ""
    $lines += "- Generated (UTC): $($Summary.generated_utc)"
    $lines += "- Total cases: $($Summary.case_count)"
    $lines += ("- Expected stage chain: {0}" -f ($Summary.expected_stage_chain -join " -> "))
    $lines += ""
    $lines += "## Route Outcomes"
    $lines += ""
    $lines += "| Case | Group | Grade/Task | Route | Selected | Confidence | Gap | Stage Integrity |"
    $lines += "| --- | --- | --- | --- | --- | --- | --- | --- |"
    foreach ($row in @($Summary.rows)) {
        $routeText = "{0} ({1})" -f $row.route_mode, $row.route_reason
        $selected = "{0}/{1}" -f $row.selected_pack, $row.selected_skill
        $gradeTask = "{0}/{1}" -f $row.grade, $row.task_type
        $integrity = if ($row.stage_order_ok -and $row.missing_stages.Count -eq 0) { "ok" } else { "problem" }
        $lines += ("| {0} | {1} | {2} | {3} | {4} | {5} | {6} | {7} |" -f $row.case, $row.scenario_group, $gradeTask, $routeText, $selected, $row.confidence, $row.top1_top2_gap, $integrity)
    }

    $lines += ""
    $lines += "## Stage Integrity"
    $lines += ""
    $lines += ("- Full stage-chain success: {0}/{1}" -f $Summary.stage_integrity.full_chain_success_count, $Summary.case_count)
    $lines += ("- Ordered-stage success: {0}/{1}" -f $Summary.stage_integrity.ordered_success_count, $Summary.case_count)
    if ($Summary.stage_integrity.problem_cases.Count -gt 0) {
        $lines += "- Problem cases:"
        foreach ($problem in @($Summary.stage_integrity.problem_cases)) {
            $lines += ("  - {0}: missing=[{1}], order_ok={2}" -f $problem.case, ($problem.missing_stages -join ", "), $problem.stage_order_ok)
        }
    } else {
        $lines += "- Problem cases: none"
    }

    $lines += ""
    $lines += "## Ambiguous vs Specific"
    $lines += ""
    $lines += "| Group | Cases | Avg Confidence | Avg Gap | Confirm Ratio | Pack Diversity |"
    $lines += "| --- | --- | --- | --- | --- | --- |"
    foreach ($metric in @($Summary.group_metrics)) {
        $lines += ("| {0} | {1} | {2} | {3} | {4} | {5} |" -f $metric.scenario_group, $metric.case_count, $metric.avg_confidence, $metric.avg_top1_top2_gap, $metric.confirm_required_ratio, $metric.pack_diversity)
    }

    $lines += ""
    $lines += "## Overlay Injection Stats"
    $lines += ""
    $lines += "| Overlay | Scope Applicable | Confirm Required | Top Reason |"
    $lines += "| --- | --- | --- | --- |"
    foreach ($item in @($Summary.overlay_stats)) {
        $reason = if ($item.top_reason) { $item.top_reason } else { "-" }
        $lines += ("| {0} | {1} | {2} | {3} |" -f $item.overlay, $item.scope_applicable_count, $item.confirm_required_count, $reason)
    }

    $lines += ""
    $lines += "## Route Override Counters"
    $lines += ""
    $lines += ("- deep_discovery_route_filter_applied=true: {0}" -f $Summary.override_stats.deep_discovery_route_filter_applied_count)
    $lines += ("- deep_discovery_route_mode_override=true: {0}" -f $Summary.override_stats.deep_discovery_route_mode_override_count)
    $lines += ("- prompt_overlay_route_override=true: {0}" -f $Summary.override_stats.prompt_overlay_route_override_count)
    $lines += ("- ai_rerank_route_override=true: {0}" -f $Summary.override_stats.ai_rerank_route_override_count)
    $lines += ("- data_scale_route_override=true: {0}" -f $Summary.override_stats.data_scale_route_override_count)

    $lines += ""
    $lines += "## Runtime State Prompt Samples"
    foreach ($sample in @($Summary.runtime_prompt_samples)) {
        $lines += ""
        $lines += ("### {0}" -f $sample.case)
        $lines += ("- prompt_included: {0}" -f $sample.prompt_included)
        $lines += '```text'
        $lines += [string]$sample.runtime_state_prompt
        $lines += '```'
    }

    $lines += ""
    $lines += "## Representative Stage Traces"
    foreach ($trace in @($Summary.representative_traces)) {
        $lines += ""
        $lines += ("### {0}" -f $trace.case)
        $lines += "| Seq | Stage | Data Keys |"
        $lines += "| --- | --- | --- |"
        foreach ($event in @($trace.events)) {
            $keyText = if ($event.data_keys.Count -gt 0) { $event.data_keys -join ", " } else { "-" }
            $lines += ("| {0} | {1} | {2} |" -f $event.seq, $event.stage, $keyText.Replace("|", "\|"))
        }
    }

    $lines += ""
    $lines += "## Artifacts"
    $lines += ""
    $lines += ('- Summary JSON: `{0}`' -f $Summary.summary_json_path)
    $lines += ('- Output directory: `{0}`' -f $Summary.output_directory)
    $lines += "- Per-case probe files are listed in the JSON summary."

    $lines -join "`n" | Set-Content -LiteralPath $Path -Encoding UTF8
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$routerPath = Join-Path $repoRoot "scripts\router\resolve-pack-route.ps1"

if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path $repoRoot "outputs\verify\route-probe-research"
}
if (-not [System.IO.Path]::IsPathRooted($OutputDirectory)) {
    $OutputDirectory = Join-Path $repoRoot $OutputDirectory
}
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null

$fixtureDir = Join-Path $OutputDirectory "fixtures"
$smallCsvPath = Join-Path $fixtureDir "small_ops.csv"
$mediumCsvPath = Join-Path $fixtureDir "medium_ops.csv"
$pythonFixturePath = Join-Path $fixtureDir "sample_module.py"
$cudaFixturePath = Join-Path $fixtureDir "kernel.cu"
$xlsxFixturePath = Join-Path $fixtureDir "metrics.xlsx"

New-SmallCsvFixture -Path $smallCsvPath
New-MediumSignalCsvFixture -Path $mediumCsvPath -TargetBytes 20971520
New-PythonFixture -Path $pythonFixturePath
New-CudaFixture -Path $cudaFixturePath
New-XlsxPlaceholder -Path $xlsxFixturePath

$cases = @(
    [pscustomobject]@{
        name = "ambiguous_generic_short"
        scenario_group = "ambiguous"
        prompt = "/vibe make this project better"
        grade = "M"
        task_type = "coding"
        requested_skill = $null
        include_prompt = $null
    },
    [pscustomobject]@{
        name = "ambiguous_cross_domain"
        scenario_group = "ambiguous"
        prompt = "/vibe improve workflow quality and architecture for this app"
        grade = "L"
        task_type = "planning"
        requested_skill = $null
        include_prompt = $null
    },
    [pscustomobject]@{
        name = "ambiguous_open_task"
        scenario_group = "ambiguous"
        prompt = "/vibe handle this task end to end"
        grade = "L"
        task_type = "research"
        requested_skill = $null
        include_prompt = $null
    },
    [pscustomobject]@{
        name = "specific_data_ml_requested"
        scenario_group = "specific"
        prompt = "/vibe build a classification pipeline with feature engineering and model evaluation"
        grade = "M"
        task_type = "coding"
        requested_skill = "scikit-learn"
        include_prompt = $null
    },
    [pscustomobject]@{
        name = "specific_docs_xlsx_requested"
        scenario_group = "specific"
        prompt = ("/vibe summarize workbook '{0}' and produce pivot insights" -f $xlsxFixturePath)
        grade = "M"
        task_type = "research"
        requested_skill = "xlsx"
        include_prompt = $null
    },
    [pscustomobject]@{
        name = "specific_mcp_integration_requested"
        scenario_group = "specific"
        prompt = "/vibe configure MCP server in plugin with .mcp.json using stdio transport"
        grade = "L"
        task_type = "planning"
        requested_skill = "mcp-integration"
        include_prompt = $null
    },
    [pscustomobject]@{
        name = "specific_embedding_requested"
        scenario_group = "specific"
        prompt = "/vibe design embedding chunking and vector retrieval strategy for rag"
        grade = "L"
        task_type = "planning"
        requested_skill = "embedding-strategies"
        include_prompt = $null
    },
    [pscustomobject]@{
        name = "overlay_prompt_doc_collision"
        scenario_group = "overlay"
        prompt = "/vibe research prompts.chat prompt template for responses api official docs and api reference"
        grade = "L"
        task_type = "research"
        requested_skill = $null
        include_prompt = $null
    },
    [pscustomobject]@{
        name = "overlay_data_scale_small_csv"
        scenario_group = "overlay"
        prompt = ("/vibe analyze '{0}' with groupby and dedup pipeline" -f $smallCsvPath)
        grade = "M"
        task_type = "research"
        requested_skill = "spreadsheet"
        include_prompt = $null
    },
    [pscustomobject]@{
        name = "overlay_data_scale_medium_csv"
        scenario_group = "overlay"
        prompt = ("/vibe analyze '{0}' with groupby dedup aggregate pipeline and parallel merge" -f $mediumCsvPath)
        grade = "M"
        task_type = "research"
        requested_skill = "spreadsheet"
        include_prompt = $null
    },
    [pscustomobject]@{
        name = "overlay_python_clean_code"
        scenario_group = "overlay"
        prompt = ("/vibe refactor python file '{0}' to fix god class long function boolean parameter and duplicate logic" -f $pythonFixturePath)
        grade = "L"
        task_type = "coding"
        requested_skill = $null
        include_prompt = $null
    },
    [pscustomobject]@{
        name = "overlay_framework_interop"
        scenario_group = "overlay"
        prompt = "/vibe migrate model from pytorch to tensorflow with ivy transpile and numerical parity validation"
        grade = "L"
        task_type = "coding"
        requested_skill = $null
        include_prompt = $null
    },
    [pscustomobject]@{
        name = "overlay_ml_lifecycle"
        scenario_group = "overlay"
        prompt = "/vibe design ml pipeline with model evaluation baseline compare canary rollout drift monitoring and retraining policy"
        grade = "L"
        task_type = "planning"
        requested_skill = $null
        include_prompt = $null
    },
    [pscustomobject]@{
        name = "overlay_system_design"
        scenario_group = "overlay"
        prompt = "/vibe design high availability distributed system with qps p99 sharding replication failover rto rpo and observability"
        grade = "L"
        task_type = "planning"
        requested_skill = $null
        include_prompt = $null
    },
    [pscustomobject]@{
        name = "overlay_cuda_kernel"
        scenario_group = "overlay"
        prompt = ("/vibe optimize cuda kernel '{0}' with tensor core shared memory bank conflict occupancy warp tuning and nsight metrics" -f $cudaFixturePath)
        grade = "L"
        task_type = "coding"
        requested_skill = $null
        include_prompt = $null
    },
    [pscustomobject]@{
        name = "overlay_quality_debt"
        scenario_group = "overlay"
        prompt = "/vibe review code quality debt with duplicate logic maintainability risk test debt and security risk"
        grade = "L"
        task_type = "review"
        requested_skill = $null
        include_prompt = $null
    },
    [pscustomobject]@{
        name = "overlay_ai_rerank_confusion"
        scenario_group = "overlay"
        prompt = "/vibe create machine learning training pipeline and deploy through github actions ci release workflow"
        grade = "L"
        task_type = "planning"
        requested_skill = $null
        include_prompt = $null
    },
    [pscustomobject]@{
        name = "runtime_prompt_redacted"
        scenario_group = "runtime"
        prompt = "/vibe optimize prompt templates for responses api and evaluate retrieval chunking"
        grade = "L"
        task_type = "research"
        requested_skill = "embedding-strategies"
        include_prompt = $false
    },
    [pscustomobject]@{
        name = "runtime_prompt_included"
        scenario_group = "runtime"
        prompt = "/vibe optimize prompt templates for responses api and evaluate retrieval chunking"
        grade = "L"
        task_type = "research"
        requested_skill = "embedding-strategies"
        include_prompt = $true
    }
)

$expectedStages = @(
    "router.init",
    "router.config",
    "router.prepack",
    "deep_discovery.trigger",
    "deep_discovery.interview",
    "deep_discovery.contract",
    "deep_discovery.filter",
    "router.pack_scoring",
    "overlay.ai_rerank",
    "overlay.prompt",
    "overlay.data_scale",
    "overlay.exploration",
    "overlay.retrieval",
    "overlay.bundle",
    "router.final"
)

$overlayPropertyMap = [ordered]@{
    deep_discovery = "deep_discovery_advice"
    openspec = "openspec_advice"
    gsd = "gsd_overlay_advice"
    prompt = "prompt_overlay_advice"
    memory = "memory_governance_advice"
    ai_rerank = "ai_rerank_advice"
    data_scale = "data_scale_advice"
    quality_debt = "quality_debt_advice"
    framework_interop = "framework_interop_advice"
    ml_lifecycle = "ml_lifecycle_advice"
    python_clean_code = "python_clean_code_advice"
    system_design = "system_design_advice"
    cuda_kernel = "cuda_kernel_advice"
    exploration = "exploration_advice"
    retrieval = "retrieval_advice"
}

$rows = @()

Push-Location $repoRoot
try {
    foreach ($case in $cases) {
        $effectiveIncludePrompt = if ($null -ne $case.include_prompt) {
            [bool]$case.include_prompt
        } else {
            [bool]$DefaultIncludePrompt
        }

        $invokeParams = @{
            Prompt = [string]$case.prompt
            Grade = [string]$case.grade
            TaskType = [string]$case.task_type
            Probe = $true
            ProbeLabel = [string]$case.name
            ProbeOutputDir = [string]$OutputDirectory
            ProbePromptMaxChars = 3000
        }
        if ($effectiveIncludePrompt) {
            $invokeParams["ProbeIncludePrompt"] = $true
        }
        if ($case.requested_skill) {
            $invokeParams["RequestedSkill"] = [string]$case.requested_skill
        }

        $route = & $routerPath @invokeParams | ConvertFrom-Json

        $probePayload = $null
        if ($route.probe_reference -and $route.probe_reference.json_path -and (Test-Path -LiteralPath ([string]$route.probe_reference.json_path))) {
            $probePayload = Get-Content -LiteralPath ([string]$route.probe_reference.json_path) -Raw -Encoding UTF8 | ConvertFrom-Json
        }

        $stages = @()
        if ($probePayload -and $probePayload.events) {
            $stages = @($probePayload.events | ForEach-Object { [string]$_.stage })
        }
        $missingStages = @($expectedStages | Where-Object { $stages -notcontains $_ })
        $stageOrderOk = Test-StageOrder -Expected $expectedStages -Actual $stages

        $overlayDigests = [ordered]@{}
        foreach ($overlayName in @($overlayPropertyMap.Keys)) {
            $propName = [string]$overlayPropertyMap[$overlayName]
            $overlayDigests[$overlayName] = Get-AdviceDigest -Advice $route.$propName
        }

        $eventTrace = @()
        if ($probePayload -and $probePayload.events) {
            foreach ($event in @($probePayload.events)) {
                $keys = @()
                if ($event.data) {
                    $keys = @($event.data.PSObject.Properties.Name | ForEach-Object { [string]$_ })
                }
                $eventTrace += [pscustomobject]@{
                    seq = [int]$event.seq
                    stage = [string]$event.stage
                    data_keys = @($keys)
                }
            }
        }

        $rows += [pscustomobject]@{
            case = [string]$case.name
            scenario_group = [string]$case.scenario_group
            grade = [string]$route.grade
            task_type = [string]$route.task_type
            route_mode = [string]$route.route_mode
            route_reason = [string]$route.route_reason
            confidence = [double]$route.confidence
            top1_top2_gap = [double]$route.top1_top2_gap
            selected_pack = if ($route.selected) { [string]$route.selected.pack_id } else { "none" }
            selected_skill = if ($route.selected) { [string]$route.selected.skill } else { "none" }
            deep_discovery_trigger_active = [bool]($route.deep_discovery_advice -and $route.deep_discovery_advice.trigger_active)
            deep_discovery_confirm_required = [bool]($route.deep_discovery_advice -and $route.deep_discovery_advice.confirm_required)
            deep_discovery_contract_completeness = if ($route.intent_contract) { [double]$route.intent_contract.completeness } else { 0.0 }
            deep_discovery_route_filter_applied = [bool]$route.deep_discovery_route_filter_applied
            deep_discovery_route_mode_override = [bool]$route.deep_discovery_route_mode_override
            prompt_overlay_route_override = [bool]$route.prompt_overlay_route_override
            ai_rerank_route_override = [bool]$route.ai_rerank_route_override
            data_scale_route_override = [bool]$route.data_scale_route_override
            prompt_included = $effectiveIncludePrompt
            probe_id = if ($route.probe_reference) { [string]$route.probe_reference.probe_id } else { $null }
            probe_json_path = if ($route.probe_reference) { [string]$route.probe_reference.json_path } else { $null }
            probe_markdown_path = if ($route.probe_reference) { [string]$route.probe_reference.markdown_path } else { $null }
            runtime_state_prompt = if ($route.probe_reference) { [string]$route.probe_reference.runtime_state_prompt } else { $null }
            runtime_state_prompt_digest = if ($route.runtime_state_prompt_digest) { $route.runtime_state_prompt_digest } else { $null }
            stage_chain = @($stages)
            missing_stages = @($missingStages)
            stage_order_ok = [bool]$stageOrderOk
            overlay_digests = [pscustomobject]$overlayDigests
            event_trace = @($eventTrace)
        }
    }
} finally {
    Pop-Location
}

$groupMetrics = @(
    Get-GroupMetrics -Rows $rows -ScenarioGroup "ambiguous"
    Get-GroupMetrics -Rows $rows -ScenarioGroup "specific"
)

$overlayStats = Get-OverlayStats -Rows $rows -OverlayNames @($overlayPropertyMap.Keys)

$problemCases = @(
    $rows |
        Where-Object { $_.missing_stages.Count -gt 0 -or -not $_.stage_order_ok } |
        ForEach-Object {
            [pscustomobject]@{
                case = [string]$_.case
                missing_stages = @($_.missing_stages)
                stage_order_ok = [bool]$_.stage_order_ok
            }
        }
)

$runtimePromptSamples = @()
$redactedSample = $rows | Where-Object { $_.case -eq "runtime_prompt_redacted" } | Select-Object -First 1
$includedSample = $rows | Where-Object { $_.case -eq "runtime_prompt_included" } | Select-Object -First 1
if ($redactedSample) {
    $runtimePromptSamples += [pscustomobject]@{
        case = [string]$redactedSample.case
        prompt_included = [bool]$redactedSample.prompt_included
        runtime_state_prompt = [string]$redactedSample.runtime_state_prompt
    }
}
if ($includedSample) {
    $runtimePromptSamples += [pscustomobject]@{
        case = [string]$includedSample.case
        prompt_included = [bool]$includedSample.prompt_included
        runtime_state_prompt = [string]$includedSample.runtime_state_prompt
    }
}

$traceSelection = @("ambiguous_generic_short", "specific_data_ml_requested", "overlay_data_scale_medium_csv", "overlay_framework_interop")
$representativeTraces = @()
foreach ($name in $traceSelection) {
    $row = $rows | Where-Object { $_.case -eq $name } | Select-Object -First 1
    if (-not $row) { continue }
    $representativeTraces += [pscustomobject]@{
        case = [string]$name
        events = @($row.event_trace)
    }
}

$summary = [pscustomobject]@{
    generated_utc = [DateTime]::UtcNow.ToString("o")
    output_directory = $OutputDirectory
    case_count = $rows.Count
    expected_stage_chain = @($expectedStages)
    route_mode_distribution = Get-DistributionObject -Rows $rows -PropertyName "route_mode"
    route_reason_distribution = Get-DistributionObject -Rows $rows -PropertyName "route_reason"
    selected_pack_distribution = Get-DistributionObject -Rows $rows -PropertyName "selected_pack"
    stage_integrity = [pscustomobject]@{
        full_chain_success_count = @($rows | Where-Object { $_.missing_stages.Count -eq 0 }).Count
        ordered_success_count = @($rows | Where-Object { $_.stage_order_ok }).Count
        problem_cases = @($problemCases)
    }
    group_metrics = @($groupMetrics)
    overlay_stats = @($overlayStats)
    override_stats = [pscustomobject]@{
        deep_discovery_route_filter_applied_count = @($rows | Where-Object { $_.deep_discovery_route_filter_applied }).Count
        deep_discovery_route_mode_override_count = @($rows | Where-Object { $_.deep_discovery_route_mode_override }).Count
        prompt_overlay_route_override_count = @($rows | Where-Object { $_.prompt_overlay_route_override }).Count
        ai_rerank_route_override_count = @($rows | Where-Object { $_.ai_rerank_route_override }).Count
        data_scale_route_override_count = @($rows | Where-Object { $_.data_scale_route_override }).Count
    }
    runtime_prompt_samples = @($runtimePromptSamples)
    representative_traces = @($representativeTraces)
    rows = @($rows)
    fixtures = [pscustomobject]@{
        small_csv = $smallCsvPath
        medium_csv = $mediumCsvPath
        python_file = $pythonFixturePath
        cuda_file = $cudaFixturePath
        xlsx_file = $xlsxFixturePath
    }
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$summaryJsonPath = Join-Path $OutputDirectory ("route-probe-research-summary-{0}.json" -f $timestamp)
$summaryMdPath = Join-Path $OutputDirectory ("route-probe-research-summary-{0}.md" -f $timestamp)

$summary | Add-Member -NotePropertyName "summary_json_path" -NotePropertyValue $summaryJsonPath -Force
$summary | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $summaryJsonPath -Encoding UTF8
Write-ResearchMarkdown -Path $summaryMdPath -Summary $summary

Write-Host "Route probe research complete."
Write-Host ("Summary JSON: {0}" -f $summaryJsonPath)
Write-Host ("Summary Markdown: {0}" -f $summaryMdPath)

if (-not $KeepFixtures) {
    if (Test-Path -LiteralPath $fixtureDir) {
        Remove-Item -LiteralPath $fixtureDir -Recurse -Force
    }
}

