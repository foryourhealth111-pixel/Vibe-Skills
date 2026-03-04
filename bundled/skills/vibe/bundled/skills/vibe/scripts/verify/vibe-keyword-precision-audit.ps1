param()

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

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$configRoot = Join-Path $repoRoot "config"
$packManifestPath = Join-Path $configRoot "pack-manifest.json"
$thresholdPath = Join-Path $configRoot "router-thresholds.json"

$packManifest = Get-Content -LiteralPath $packManifestPath -Raw | ConvertFrom-Json
$thresholds = Get-Content -LiteralPath $thresholdPath -Raw | ConvertFrom-Json

$fallbackThreshold = [double]$thresholds.thresholds.fallback_to_legacy_below
$interferenceGapMin = 0.03

$total = 0
$pass = 0
$fail = 0
$failures = New-Object System.Collections.Generic.List[string]

function Record-Check {
    param(
        [bool]$Condition,
        [string]$Message
    )

    $script:total++
    if ($Condition) {
        $script:pass++
        return
    }

    $script:fail++
    $script:failures.Add($Message)
    Write-Host "[FAIL] $Message" -ForegroundColor Red
}

Write-Host "=== VCO Keyword Precision Audit (Bilingual + Interference) ==="

# 1) Keyword health: each pack must contain at least one English and one Chinese trigger.
foreach ($pack in $packManifest.packs) {
    $hasEnglish = ($pack.trigger_keywords | Where-Object { $_ -match "[A-Za-z]" }).Count -gt 0
    $hasChinese = ($pack.trigger_keywords | Where-Object { $_ -match "[\u4E00-\u9FFF]" }).Count -gt 0
    Record-Check -Condition $hasEnglish -Message "pack '$($pack.id)' lacks English trigger keywords"
    Record-Check -Condition $hasChinese -Message "pack '$($pack.id)' lacks Chinese trigger keywords"
}

# 2) Pack-level bilingual routing and interference gap checks.
$probeCases = @(
    [pscustomobject]@{ Pack = "orchestration-core"; Grade = "L"; Task = "planning"; En = "Need workflow orchestration and subagent planning for this system"; Zh = "请做工作流编排和子代理规划方案" },
    [pscustomobject]@{ Pack = "code-quality"; Grade = "M"; Task = "review"; En = "Run code review, lint, and debugging quality checks"; Zh = "请做代码审查、调试和质量检查" },
    [pscustomobject]@{ Pack = "data-ml"; Grade = "L"; Task = "research"; En = "Machine learning model training with regression and feature engineering"; Zh = "请做机器学习模型训练、回归和特征工程分析" },
    [pscustomobject]@{ Pack = "bio-science"; Grade = "L"; Task = "research"; En = "Bioinformatics genomics sequencing pathway analysis"; Zh = "请做生物信息基因组测序和通路分析" },
    [pscustomobject]@{ Pack = "docs-media"; Grade = "M"; Task = "coding"; En = "Process spreadsheet xlsx and generate docx pdf output"; Zh = "请处理表格xlsx并生成docx和pdf文档" },
    [pscustomobject]@{ Pack = "integration-devops"; Grade = "L"; Task = "debug"; En = "Debug github ci cd deployment pipeline with sentry"; Zh = "请排查github持续集成部署流水线并结合sentry" },
    [pscustomobject]@{ Pack = "ai-llm"; Grade = "M"; Task = "research"; En = "Optimize llm prompt and rag embedding retrieval with openai"; Zh = "请做大模型提示词和rag嵌入检索优化" },
    [pscustomobject]@{ Pack = "research-design"; Grade = "L"; Task = "planning"; En = "Research methodology, hypothesis, and experimental design"; Zh = "请做研究方法学、假设与实验设计规划" }
)

foreach ($case in $probeCases) {
    $enRoute = Invoke-Route -Prompt $case.En -Grade $case.Grade -TaskType $case.Task -RequestedSkill $null
    $zhRoute = Invoke-Route -Prompt $case.Zh -Grade $case.Grade -TaskType $case.Task -RequestedSkill $null

    Record-Check -Condition ($enRoute.selected.pack_id -eq $case.Pack) -Message "[EN] expected pack '$($case.Pack)', got '$($enRoute.selected.pack_id)'"
    Record-Check -Condition ($zhRoute.selected.pack_id -eq $case.Pack) -Message "[ZH] expected pack '$($case.Pack)', got '$($zhRoute.selected.pack_id)'"
    Record-Check -Condition ($enRoute.route_mode -in @("pack_overlay", "legacy_fallback")) -Message "[EN] '$($case.Pack)' route mode is invalid: '$($enRoute.route_mode)'"
    Record-Check -Condition ($zhRoute.route_mode -in @("pack_overlay", "legacy_fallback")) -Message "[ZH] '$($case.Pack)' route mode is invalid: '$($zhRoute.route_mode)'"

    $enTop = [double]$enRoute.ranked[0].score
    $enSecond = if ($enRoute.ranked.Count -gt 1) { [double]$enRoute.ranked[1].score } else { 0.0 }
    $zhTop = [double]$zhRoute.ranked[0].score
    $zhSecond = if ($zhRoute.ranked.Count -gt 1) { [double]$zhRoute.ranked[1].score } else { 0.0 }

    $enGap = [Math]::Round($enTop - $enSecond, 4)
    $zhGap = [Math]::Round($zhTop - $zhSecond, 4)
    Record-Check -Condition ($enGap -ge $interferenceGapMin) -Message "[EN] '$($case.Pack)' interference gap too small: $enGap"
    Record-Check -Condition ($zhGap -ge $interferenceGapMin) -Message "[ZH] '$($case.Pack)' interference gap too small: $zhGap"
}

# 3) Skill-level sweep: every migrated skill should stably map to its pack in EN/ZH prompts.
$packContext = @{
    "orchestration-core" = @{ Grade = "L"; Task = "planning" }
    "code-quality"       = @{ Grade = "M"; Task = "review" }
    "data-ml"            = @{ Grade = "L"; Task = "research" }
    "bio-science"        = @{ Grade = "L"; Task = "research" }
    "docs-media"         = @{ Grade = "M"; Task = "coding" }
    "integration-devops" = @{ Grade = "L"; Task = "debug" }
    "ai-llm"             = @{ Grade = "M"; Task = "research" }
    "research-design"    = @{ Grade = "L"; Task = "planning" }
}

$skillTotal = 0
foreach ($pack in $packManifest.packs) {
    $ctx = $packContext[$pack.id]
    if (-not $ctx) { continue }

    foreach ($skill in $pack.skill_candidates) {
        $skillTotal++
        $enPrompt = "please use $skill for this task"
        $zhPrompt = "请使用 $skill 处理这个任务"

        $enRoute = Invoke-Route -Prompt $enPrompt -Grade $ctx.Grade -TaskType $ctx.Task -RequestedSkill $skill
        $zhRoute = Invoke-Route -Prompt $zhPrompt -Grade $ctx.Grade -TaskType $ctx.Task -RequestedSkill $skill

        Record-Check -Condition ($enRoute.selected.pack_id -eq $pack.id) -Message "[EN skill] $skill expected pack '$($pack.id)', got '$($enRoute.selected.pack_id)'"
        Record-Check -Condition ($zhRoute.selected.pack_id -eq $pack.id) -Message "[ZH skill] $skill expected pack '$($pack.id)', got '$($zhRoute.selected.pack_id)'"
        Record-Check -Condition ($enRoute.selected.skill -eq $skill) -Message "[EN skill] $skill selected skill mismatch: '$($enRoute.selected.skill)'"
        Record-Check -Condition ($zhRoute.selected.skill -eq $skill) -Message "[ZH skill] $skill selected skill mismatch: '$($zhRoute.selected.skill)'"
        Record-Check -Condition ($enRoute.route_mode -eq "pack_overlay") -Message "[EN skill] $skill route mode is '$($enRoute.route_mode)'"
        Record-Check -Condition ($zhRoute.route_mode -eq "pack_overlay") -Message "[ZH skill] $skill route mode is '$($zhRoute.route_mode)'"
    }
}

Write-Host ""
Write-Host "=== Summary ==="
Write-Host "Skill candidates checked: $skillTotal"
Write-Host "Total assertions: $total"
Write-Host "Passed: $pass"
Write-Host "Failed: $fail"

if ($fail -gt 0) {
    Write-Host ""
    Write-Host "Top failures:"
    $failures | Select-Object -First 20 | ForEach-Object { Write-Host " - $_" }
    exit 1
}

Write-Host "Keyword precision audit passed."
exit 0
