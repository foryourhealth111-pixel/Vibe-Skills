param(
    [ValidateSet("shadow", "soft", "strict")]
    [string]$Mode = "shadow",
    [string]$OutputDirectory,
    [switch]$IncludePrompt
)

$ErrorActionPreference = "Stop"

function Set-DeepDiscoveryStage {
    param(
        [string]$ConfigPath,
        [ValidateSet("shadow", "soft", "strict")]
        [string]$Stage
    )

    $policy = Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $policy.enabled = $true
    $policy.mode = $Stage
    $policy.preserve_routing_assignment = if ($Stage -eq "strict") { $false } else { $true }
    $policy.updated = (Get-Date).ToString("yyyy-MM-dd")
    $policy | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $ConfigPath -Encoding UTF8
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

function Write-ScenarioMarkdown {
    param(
        [string]$Path,
        [object]$Summary
    )

    $lines = @()
    $lines += "# VCO Deep Discovery Scenario Report"
    $lines += ""
    $lines += ("- generated_utc: {0}" -f $Summary.generated_utc)
    $lines += ("- mode: {0}" -f $Summary.mode)
    $lines += ("- case_count: {0}" -f $Summary.case_count)
    $lines += ("- expected_stage_chain: {0}" -f ($Summary.expected_stages -join " -> "))
    $lines += ""
    $lines += "## Scenario Outcomes"
    $lines += ""
    $lines += "| Case | Grade/Task | Route | Selected | Trigger | Completeness | Confirm | Filter Applied | Stage Integrity |"
    $lines += "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"

    foreach ($row in @($Summary.rows)) {
        $routeText = "{0} ({1})" -f $row.route_mode, $row.route_reason
        $selected = "{0}/{1}" -f $row.selected_pack, $row.selected_skill
        $gradeTask = "{0}/{1}" -f $row.grade, $row.task_type
        $integrity = if ($row.stage_order_ok -and $row.missing_stages.Count -eq 0) { "ok" } else { "problem" }
        $lines += ("| {0} | {1} | {2} | {3} | {4} | {5} | {6} | {7} | {8} |" -f `
            $row.case, $gradeTask, $routeText, $selected, $row.deep_trigger_active, `
            $row.contract_completeness, $row.confirm_required, $row.route_filter_applied, $integrity)
    }

    $lines += ""
    $lines += "## Aggregate"
    $lines += ""
    $lines += ("- trigger_active_count: {0}" -f $Summary.aggregate.trigger_active_count)
    $lines += ("- confirm_required_count: {0}" -f $Summary.aggregate.confirm_required_count)
    $lines += ("- route_filter_applied_count: {0}" -f $Summary.aggregate.route_filter_applied_count)
    $lines += ("- stage_integrity_success_count: {0}" -f $Summary.aggregate.stage_integrity_success_count)

    $lines += ""
    $lines += "## Runtime Digest Samples"
    foreach ($sample in @($Summary.runtime_digest_samples)) {
        $lines += ""
        $lines += ("### {0}" -f $sample.case)
        $lines += '```json'
        $lines += ($sample.digest | ConvertTo-Json -Depth 20)
        $lines += '```'
    }

    $lines += ""
    $lines += "## Artifacts"
    $lines += ("- summary_json: {0}" -f $Summary.summary_json_path)
    $lines += ("- output_directory: {0}" -f $Summary.output_directory)

    $lines -join "`n" | Set-Content -LiteralPath $Path -Encoding UTF8
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$routerPath = Join-Path $repoRoot "scripts\router\resolve-pack-route.ps1"
$policyPath = Join-Path $repoRoot "config\deep-discovery-policy.json"
$originalPolicyRaw = Get-Content -LiteralPath $policyPath -Raw -Encoding UTF8

if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path $repoRoot "outputs\verify\deep-discovery-scenarios"
}
if (-not [System.IO.Path]::IsPathRooted($OutputDirectory)) {
    $OutputDirectory = Join-Path $repoRoot $OutputDirectory
}
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null

$cases = @(
    [pscustomobject]@{
        name = "ambiguous_cross_domain"
        prompt = '$vibe 帮我把这个任务端到端做好：从生物数据库拿数据，做机器学习，然后给报告'
        grade = "L"
        task_type = "planning"
    },
    [pscustomobject]@{
        name = "specific_bio_ml_pipeline"
        prompt = '$vibe 设计并实现流程：抓取UniProt蛋白，训练scikit-learn模型，输出脚本与评估报告，并给验证门禁'
        grade = "L"
        task_type = "coding"
    },
    [pscustomobject]@{
        name = "single_domain_code_fix"
        prompt = '$vibe 修复前端登录表单校验 bug 并补测试'
        grade = "M"
        task_type = "coding"
    },
    [pscustomobject]@{
        name = "planning_plus_execution"
        prompt = '$vibe 先头脑风暴方案，再落地实现API并写文档'
        grade = "L"
        task_type = "planning"
    },
    [pscustomobject]@{
        name = "docs_prompt_combo"
        prompt = '$vibe 帮我优化 prompt 模板并整理 OpenAI API 文档说明'
        grade = "L"
        task_type = "research"
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

$rows = @()
try {
    Set-DeepDiscoveryStage -ConfigPath $policyPath -Stage $Mode

    foreach ($case in $cases) {
        $params = @{
            Prompt = [string]$case.prompt
            Grade = [string]$case.grade
            TaskType = [string]$case.task_type
            Probe = $true
            ProbeLabel = [string]$case.name
            ProbeOutputDir = [string]$OutputDirectory
            ProbePromptMaxChars = 3000
        }
        if ($IncludePrompt) {
            $params["ProbeIncludePrompt"] = $true
        }

        $route = & $routerPath @params | ConvertFrom-Json

        $stages = @()
        $probePayload = $null
        if ($route.probe_reference -and $route.probe_reference.json_path -and (Test-Path -LiteralPath ([string]$route.probe_reference.json_path))) {
            $probePayload = Get-Content -LiteralPath ([string]$route.probe_reference.json_path) -Raw -Encoding UTF8 | ConvertFrom-Json
            $stages = @($probePayload.events | ForEach-Object { [string]$_.stage })
        }
        $missingStages = @($expectedStages | Where-Object { $stages -notcontains $_ })
        $stageOrderOk = Test-StageOrder -Expected $expectedStages -Actual $stages

        $rows += [pscustomobject]@{
            case = [string]$case.name
            grade = [string]$route.grade
            task_type = [string]$route.task_type
            route_mode = [string]$route.route_mode
            route_reason = [string]$route.route_reason
            selected_pack = if ($route.selected) { [string]$route.selected.pack_id } else { "none" }
            selected_skill = if ($route.selected) { [string]$route.selected.skill } else { "none" }
            deep_trigger_active = [bool]($route.deep_discovery_advice -and $route.deep_discovery_advice.trigger_active)
            deep_trigger_score = if ($route.deep_discovery_advice) { [double]$route.deep_discovery_advice.trigger_score } else { 0.0 }
            contract_completeness = if ($route.intent_contract) { [double]$route.intent_contract.completeness } else { 0.0 }
            confirm_required = [bool]($route.deep_discovery_advice -and $route.deep_discovery_advice.confirm_required)
            route_filter_applied = [bool]$route.deep_discovery_route_filter_applied
            route_mode_override = [bool]$route.deep_discovery_route_mode_override
            stage_order_ok = [bool]$stageOrderOk
            missing_stages = @($missingStages)
            runtime_state_prompt_digest = if ($route.runtime_state_prompt_digest) { $route.runtime_state_prompt_digest } else { $null }
            probe_json_path = if ($route.probe_reference) { [string]$route.probe_reference.json_path } else { $null }
            probe_markdown_path = if ($route.probe_reference) { [string]$route.probe_reference.markdown_path } else { $null }
        }
    }
} finally {
    Set-Content -LiteralPath $policyPath -Value $originalPolicyRaw -Encoding UTF8
}

$runtimeSamples = @(
    $rows | Select-Object -First 3 | ForEach-Object {
        [pscustomobject]@{
            case = [string]$_.case
            digest = $_.runtime_state_prompt_digest
        }
    }
)

$summary = [pscustomobject]@{
    generated_utc = [DateTime]::UtcNow.ToString("o")
    mode = $Mode
    case_count = $rows.Count
    output_directory = $OutputDirectory
    expected_stages = @($expectedStages)
    aggregate = [pscustomobject]@{
        trigger_active_count = @($rows | Where-Object { $_.deep_trigger_active }).Count
        confirm_required_count = @($rows | Where-Object { $_.confirm_required }).Count
        route_filter_applied_count = @($rows | Where-Object { $_.route_filter_applied }).Count
        stage_integrity_success_count = @($rows | Where-Object { $_.stage_order_ok -and $_.missing_stages.Count -eq 0 }).Count
    }
    rows = @($rows)
    runtime_digest_samples = @($runtimeSamples)
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$jsonPath = Join-Path $OutputDirectory ("deep-discovery-scenarios-{0}.json" -f $timestamp)
$mdPath = Join-Path $OutputDirectory ("deep-discovery-scenarios-{0}.md" -f $timestamp)

$summary | Add-Member -NotePropertyName "summary_json_path" -NotePropertyValue $jsonPath -Force
$summary | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
Write-ScenarioMarkdown -Path $mdPath -Summary $summary

Write-Host "Deep discovery scenario run complete."
Write-Host ("Summary JSON: {0}" -f $jsonPath)
Write-Host ("Summary Markdown: {0}" -f $mdPath)


