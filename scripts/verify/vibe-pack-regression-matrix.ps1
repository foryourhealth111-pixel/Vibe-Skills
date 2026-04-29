param()

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

function Invoke-Route {
    param(
        [string]$Prompt,
        [string]$Grade,
        [string]$TaskType,
        [string]$RequestedSkill
    )

    $repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
    $resolver = Join-Path $repoRoot "scripts\router\resolve-pack-route.ps1"
    $confirmUiState = Join-Path (Join-Path $repoRoot "outputs\\runtime") "confirm-ui-state.json"
    if (Test-Path -LiteralPath $confirmUiState) {
        Remove-Item -LiteralPath $confirmUiState -Force -ErrorAction SilentlyContinue
    }

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

$cases = @(
    [pscustomobject]@{ Name = "generic planning no orchestration core EN"; Prompt = "create implementation plan and task breakdown with milestones"; Grade = "L"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "orchestration-core"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "generic planning no orchestration core ZH"; Prompt = "请给我实施计划和任务拆解"; Grade = "L"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "orchestration-core"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "generic brainstorming no orchestration core ZH"; Prompt = "先做头脑风暴，比较几个方案"; Grade = "L"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "orchestration-core"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "generic subagent no orchestration core ZH"; Prompt = "把任务拆成多个子代理并行执行"; Grade = "XL"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "orchestration-core"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "generic coding M not subagent"; Prompt = "实现这个功能并修改代码"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = $null; BlockedSkill = "subagent-driven-development"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "generic coding L not subagent"; Prompt = "实现这个功能并修改代码"; Grade = "L"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = $null; BlockedSkill = "subagent-driven-development"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "generic coding XL not silent subagent"; Prompt = "实现这个功能并修改代码"; Grade = "XL"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = $null; BlockedSkill = "subagent-driven-development"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "explicit speckit compatibility"; Prompt = "/speckit.plan 生成技术计划"; Grade = "L"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = "workflow-compatibility"; ExpectedSkill = "spec-kit-vibe-compat"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },

    [pscustomobject]@{ Name = "code-quality review canonical"; Prompt = "run code review and quality checks"; Grade = "M"; TaskType = "review"; RequestedSkill = "code-reviewer"; ExpectedPack = "code-quality"; ExpectedSkill = "code-reviewer"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "code-quality review feedback"; Prompt = "收到CodeRabbit评审意见，帮我逐条判断是否要改"; Grade = "M"; TaskType = "review"; RequestedSkill = $null; ExpectedPack = "code-quality"; ExpectedSkill = "receiving-code-review"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "code-quality completion verification"; Prompt = "准备收尾，确认测试通过并给出验收证据"; Grade = "M"; TaskType = "review"; RequestedSkill = $null; ExpectedPack = "code-quality"; ExpectedSkill = "verification-before-completion"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "code-quality ai cleanup"; Prompt = "清理AI生成代码里的废话注释和多余防御式检查"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "code-quality"; ExpectedSkill = "deslop"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "code-quality tdd test-first"; Prompt = "write failing tests first for this feature"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "code-quality"; ExpectedSkill = "tdd-guide"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "code-quality security audit owns mixed review"; Prompt = "code review and security audit"; Grade = "M"; TaskType = "review"; RequestedSkill = $null; ExpectedPack = "code-quality"; ExpectedSkill = "security-reviewer"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "code-quality debug"; Prompt = "do root cause debugging for failing tests"; Grade = "M"; TaskType = "debug"; RequestedSkill = $null; ExpectedPack = "code-quality"; ExpectedSkill = "systematic-debugging"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "code-quality build compile debug"; Prompt = "构建失败，TypeScript compile error，帮我定位"; Grade = "M"; TaskType = "debug"; RequestedSkill = $null; ExpectedPack = "code-quality"; ExpectedSkill = "systematic-debugging"; AllowedModes = @("pack_overlay", "confirm_required") },

    [pscustomobject]@{ Name = "data-ml coding"; Prompt = "build machine learning model with scikit-learn feature engineering and training"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "data-ml"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "data-ml research ZH"; Prompt = "使用scikit-learn做分类训练并交叉验证"; Grade = "L"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "data-ml"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "data-ml leakage review ZH"; Prompt = "请检查这个机器学习流程是否存在数据泄漏，尤其是归一化是否在划分前fit了"; Grade = "M"; TaskType = "review"; RequestedSkill = $null; ExpectedPack = "data-ml"; ExpectedSkill = "ml-data-leakage-guard"; AllowedModes = @("pack_overlay", "confirm_required") },

    [pscustomobject]@{ Name = "bio-science research"; Prompt = "single-cell scRNA analysis with scanpy clustering and marker genes"; Grade = "L"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "bio-science"; AllowedModes = @("pack_overlay", "confirm_required") },

    [pscustomobject]@{ Name = "docs-media coding canonical"; Prompt = "process xlsx workbook and preserve formulas"; Grade = "M"; TaskType = "coding"; RequestedSkill = "xlsx"; ExpectedPack = "docs-media"; ExpectedSkill = "xlsx"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "media-video research transcribe"; Prompt = "请把会议录音转文字并区分说话人"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "media-video"; ExpectedSkill = "transcribe"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "docs-media spreadsheet analysis owner"; Prompt = "分析这个Excel表格并生成数据透视表"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "docs-media"; ExpectedSkill = "spreadsheet"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "docs-media docx layout owner"; Prompt = "检查这个 Word 文档的排版和 layout fidelity"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "docs-media"; ExpectedSkill = "docx"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "screen-capture screenshot owner"; Prompt = "给我截一张当前桌面截图"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "screen-capture"; ExpectedSkill = "screenshot"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "docs-media jupyter not owned"; Prompt = "创建一个Jupyter notebook教程"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = $null; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback"); BlockedPack = "docs-media" },

    [pscustomobject]@{ Name = "web-scraping research ZH"; Prompt = "请用爬虫抓取 https://example.com ，并用 CSS selector '#main a' 提取所有链接（scrape / 抓取 / selector）"; Grade = "L"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "web-scraping"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "web-scraping canonical scrapling"; Prompt = "scrape https://nopecha.com/demo/cloudflare and extract '#padded_content a' (Cloudflare / Turnstile) to markdown"; Grade = "M"; TaskType = "coding"; RequestedSkill = "scrapling"; ExpectedPack = "web-scraping"; AllowedModes = @("pack_overlay", "confirm_required") },

    [pscustomobject]@{ Name = "integration-devops debug"; Prompt = "debug github actions ci failure and inspect sentry errors"; Grade = "L"; TaskType = "debug"; RequestedSkill = $null; ExpectedPack = "integration-devops"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "integration-devops netlify deploy"; Prompt = "请部署到Netlify并生成预览链接"; Grade = "L"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "integration-devops"; ExpectedSkill = "netlify-deploy"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "integration-devops node zombie cleanup"; Prompt = "审计并清理VCO托管的僵尸node进程"; Grade = "L"; TaskType = "debug"; RequestedSkill = $null; ExpectedPack = "integration-devops"; ExpectedSkill = "node-zombie-guardian"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "integration-devops blocks security best practices"; Prompt = "做一次安全最佳实践审查"; Grade = "M"; TaskType = "review"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "integration-devops"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "integration-devops blocks threat model"; Prompt = "为这个仓库做威胁建模"; Grade = "M"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "integration-devops"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "integration-devops blocks security ownership"; Prompt = "分析安全所有权和bus factor"; Grade = "M"; TaskType = "review"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "integration-devops"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "integration-devops blocks file permission"; Prompt = "处理文件写入失败和Permission denied"; Grade = "M"; TaskType = "debug"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "integration-devops"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "integration-devops blocks benchmarkdotnet"; Prompt = "运行BenchmarkDotNet性能测试"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "integration-devops"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "integration-devops blocks pr review comments"; Prompt = "回复PR评审意见并修改代码"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "integration-devops"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "integration-devops blocks yeet pr publish"; Prompt = "一键提交commit push并打开PR"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "integration-devops"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },

    [pscustomobject]@{ Name = "ai-llm research"; Prompt = "query OpenAI official docs for Responses API and model limits"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "ai-llm"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },

    [pscustomobject]@{ Name = "research-design planning"; Prompt = "design quasi-experimental methodology with DiD and ITS"; Grade = "L"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = "research-design"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "research-design hypothesis generation"; Prompt = "根据实验观察生成可检验的科研假设和预测"; Grade = "L"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = "research-design"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "research-design causal analysis"; Prompt = "用 DID 和 synthetic control 做因果分析方案"; Grade = "L"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "research-design"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "research-design grant proposal"; Prompt = "写 NSF 科研基金申请书的 significance 和 innovation"; Grade = "L"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = "research-design"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "publishing workflow package"; Prompt = "规划一套期刊投稿工作流，包含投稿包、校样和 camera-ready"; Grade = "L"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = "scholarly-publishing-workflow"; ExpectedSkill = "scholarly-publishing"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "publishing latex pipeline"; Prompt = "配置 latexmk/chktex/latexindent 编译论文 PDF 并打包 submission zip"; Grade = "XL"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "scholarly-publishing-workflow"; ExpectedSkill = "latex-submission-pipeline"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "publishing venue template"; Prompt = "查 NeurIPS 模板和匿名投稿格式要求"; Grade = "L"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = "scholarly-publishing-workflow"; ExpectedSkill = "venue-templates"; AllowedModes = @("pack_overlay", "confirm_required") },

    [pscustomobject]@{ Name = "aios-core planning"; Prompt = "create PRD and user story backlog with quality gate"; Grade = "L"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = "aios-core"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },

    [pscustomobject]@{ Name = "lab automation generic eln negated vendors blocked"; Prompt = "帮我整理电子实验记录 ELN 模板，不指定 Benchling 或 LabArchives"; Grade = "M"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "science-lab-automation"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "lab automation generic attachments negated vendors blocked"; Prompt = "把实验图片和 CSV 附件整理到实验记录里，不使用 LabArchives 或 Benchling"; Grade = "M"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "science-lab-automation"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "lab automation generic markdown protocol blocked"; Prompt = "写一个普通 wet-lab protocol 的 Markdown 文档，不使用 protocols.io 或机器人"; Grade = "M"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "science-lab-automation"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },

    [pscustomobject]@{ Name = "low-signal fallback"; Prompt = "help me with this"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = $null; AllowedModes = @("pack_overlay", "legacy_fallback", "confirm_required") },

    [pscustomobject]@{ Name = "docs-media explicit requested xlsx XL"; Prompt = "process xlsx workbook and preserve formulas"; Grade = "XL"; TaskType = "coding"; RequestedSkill = "xlsx"; ExpectedPack = "docs-media"; ExpectedSkill = "xlsx"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "docs-media generic multi-doc XL not weak owner"; Prompt = "xlsx and docx parallel processing"; Grade = "XL"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = $null; AllowedModes = @("pack_overlay", "legacy_fallback", "confirm_required"); BlockedPack = "docs-media" },

    [pscustomobject]@{ Name = "gap-driven confirm"; Prompt = "code review and security audit"; Grade = "M"; TaskType = "review"; RequestedSkill = $null; ExpectedPack = "code-quality"; ExpectedSkill = "security-reviewer"; AllowedModes = @("pack_overlay", "confirm_required") }
)

$results = @()

Write-Host "=== VCO Pack Regression Matrix ==="
foreach ($case in $cases) {
    $route = Invoke-Route -Prompt $case.Prompt -Grade $case.Grade -TaskType $case.TaskType -RequestedSkill $case.RequestedSkill

    $results += Assert-True -Condition ($case.AllowedModes -contains $route.route_mode) -Message "[$($case.Name)] route mode '$($route.route_mode)' is allowed"

    if ($case.ExpectedPack) {
        $results += Assert-True -Condition ($route.selected.pack_id -eq $case.ExpectedPack) -Message "[$($case.Name)] selected pack is $($case.ExpectedPack)"
    }

    if ($case.ExpectedSkill) {
        $results += Assert-True -Condition ($route.selected.skill -eq $case.ExpectedSkill) -Message "[$($case.Name)] selected skill is $($case.ExpectedSkill)"
    }

    if ($case.BlockedPack) {
        $results += Assert-True -Condition ($route.selected.pack_id -ne $case.BlockedPack) -Message "[$($case.Name)] blocked pack $($case.BlockedPack) not selected"
    }

    if ($case.BlockedSkill) {
        $results += Assert-True -Condition ($route.selected.skill -ne $case.BlockedSkill) -Message "[$($case.Name)] blocked skill $($case.BlockedSkill) not selected"
    }

    if ($case.BlockedPackAndSkill) {
        $pair = [string]$case.BlockedPackAndSkill
        $actualPair = "{0}/{1}" -f $route.selected.pack_id, $route.selected.skill
        $results += Assert-True -Condition ($actualPair -ne $pair) -Message "[$($case.Name)] blocked pair $pair not selected"
    }

    $results += Assert-True -Condition ($route.top1_top2_gap -ge 0) -Message "[$($case.Name)] top1_top2_gap is non-negative"

    if ($case.Name -eq "low-signal fallback") {
        if ($route.legacy_fallback_guard_applied) {
            $results += Assert-True -Condition ($route.route_mode -eq "confirm_required") -Message "[$($case.Name)] legacy fallback guard maps to confirm_required"
            $results += Assert-True -Condition ($route.legacy_fallback_original_reason -in @("confidence_below_fallback", "no_eligible_pack")) -Message "[$($case.Name)] legacy fallback original reason recorded"
        } else {
            $results += Assert-True -Condition ([double]$route.confidence -lt [double]$route.thresholds.fallback_to_legacy_below) -Message "[$($case.Name)] confidence below fallback threshold"
        }
    }
}

# Determinism check: same input, same output.
$detA = Invoke-Route -Prompt "run code review and security scan" -Grade "M" -TaskType "review" -RequestedSkill "code-review"
$detB = Invoke-Route -Prompt "run code review and security scan" -Grade "M" -TaskType "review" -RequestedSkill "code-review"
$results += Assert-True -Condition ($detA.selected.pack_id -eq $detB.selected.pack_id) -Message "[determinism] selected pack is stable"
$results += Assert-True -Condition ($detA.route_mode -eq $detB.route_mode) -Message "[determinism] route mode is stable"
$results += Assert-True -Condition ($detA.confidence -eq $detB.confidence) -Message "[determinism] confidence is stable"
$results += Assert-True -Condition ($detA.top1_top2_gap -eq $detB.top1_top2_gap) -Message "[determinism] top1_top2_gap is stable"

$passCount = ($results | Where-Object { $_ }).Count
$failCount = ($results | Where-Object { -not $_ }).Count
$total = $results.Count

Write-Host ""
Write-Host "=== Summary ==="
Write-Host "Total assertions: $total"
Write-Host "Passed: $passCount"
Write-Host "Failed: $failCount"

if ($failCount -gt 0) {
    exit 1
}

Write-Host "Pack regression matrix checks passed."
exit 0
