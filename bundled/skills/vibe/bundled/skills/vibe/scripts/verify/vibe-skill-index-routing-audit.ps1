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
        [string]$TaskType
    )

    $repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
    $resolver = Join-Path $repoRoot "scripts\router\resolve-pack-route.ps1"

    $json = & $resolver -Prompt $Prompt -Grade $Grade -TaskType $TaskType
    return ($json | ConvertFrom-Json)
}

$cases = @(
    [pscustomobject]@{ Name = "xlsx formula retention"; Prompt = "请帮我修改xlsx工作簿并保留公式"; Grade = "M"; TaskType = "coding"; ExpectedPack = "docs-media"; ExpectedSkill = "xlsx" },
    [pscustomobject]@{ Name = "speech synthesis"; Prompt = "把这段文本做语音合成并输出mp3"; Grade = "M"; TaskType = "research"; ExpectedPack = "docs-media"; ExpectedSkill = "speech" },
    [pscustomobject]@{ Name = "meeting transcription"; Prompt = "请把会议录音转文字并区分说话人"; Grade = "M"; TaskType = "research"; ExpectedPack = "docs-media"; ExpectedSkill = "transcribe" },
    [pscustomobject]@{ Name = "pdf extraction"; Prompt = "读取pdf并提取章节正文"; Grade = "M"; TaskType = "coding"; ExpectedPack = "docs-media"; ExpectedSkill = "pdf" },
    [pscustomobject]@{ Name = "screenshot capture"; Prompt = "给我截一张当前桌面截图"; Grade = "M"; TaskType = "coding"; ExpectedPack = "docs-media"; ExpectedSkill = "screenshot" },

    [pscustomobject]@{ Name = "sklearn training"; Prompt = "用scikit-learn做分类训练和交叉验证"; Grade = "L"; TaskType = "research"; ExpectedPack = "data-ml"; ExpectedSkill = "scikit-learn" },
    [pscustomobject]@{ Name = "shap interpretation"; Prompt = "请计算SHAP解释并输出beeswarm图"; Grade = "L"; TaskType = "research"; ExpectedPack = "data-ml"; ExpectedSkill = "shap" },
    [pscustomobject]@{ Name = "umap reduction"; Prompt = "使用UMAP进行降维可视化"; Grade = "L"; TaskType = "research"; ExpectedPack = "data-ml"; ExpectedSkill = "umap-learn" },
    [pscustomobject]@{ Name = "data leakage guard"; Prompt = "做特征工程前先做数据泄漏检查"; Grade = "L"; TaskType = "research"; ExpectedPack = "data-ml"; ExpectedSkill = "ml-data-leakage-guard" },

    [pscustomobject]@{ Name = "scanpy single-cell"; Prompt = "做单细胞RNA-seq聚类与注释，使用scanpy"; Grade = "L"; TaskType = "research"; ExpectedPack = "bio-science"; ExpectedSkill = "scanpy" },
    [pscustomobject]@{ Name = "pydeseq2 de"; Prompt = "进行DESeq2差异表达分析"; Grade = "L"; TaskType = "research"; ExpectedPack = "bio-science"; ExpectedSkill = "pydeseq2" },
    [pscustomobject]@{ Name = "pysam bam vcf"; Prompt = "解析BAM和VCF文件并统计覆盖度"; Grade = "L"; TaskType = "research"; ExpectedPack = "bio-science"; ExpectedSkill = "pysam" },
    [pscustomobject]@{ Name = "biopython sequence"; Prompt = "用BioPython处理FASTA序列并做格式转换"; Grade = "L"; TaskType = "research"; ExpectedPack = "bio-science"; ExpectedSkill = "biopython" },

    [pscustomobject]@{ Name = "github ci fix"; Prompt = "排查GitHub Actions CI失败并修复"; Grade = "L"; TaskType = "debug"; ExpectedPack = "integration-devops"; ExpectedSkill = "gh-fix-ci" },
    [pscustomobject]@{ Name = "mcp integration"; Prompt = "需要接入MCP server并配置.mcp.json"; Grade = "L"; TaskType = "planning"; ExpectedPack = "integration-devops"; ExpectedSkill = "mcp-integration" },
    [pscustomobject]@{ Name = "sentry diagnostics"; Prompt = "查看Sentry线上报错并汇总根因"; Grade = "L"; TaskType = "debug"; ExpectedPack = "integration-devops"; ExpectedSkill = "sentry" },
    [pscustomobject]@{ Name = "vercel deploy"; Prompt = "请把应用部署到Vercel并返回访问链接"; Grade = "L"; TaskType = "coding"; ExpectedPack = "integration-devops"; ExpectedSkill = "vercel-deploy" },

    [pscustomobject]@{ Name = "openai docs"; Prompt = "查询OpenAI官方文档中的Responses API用法"; Grade = "M"; TaskType = "research"; ExpectedPack = "ai-llm"; ExpectedSkill = "openai-docs" },
    [pscustomobject]@{ Name = "prompt lookup"; Prompt = "帮我检索提示词模板并优化prompt"; Grade = "M"; TaskType = "research"; ExpectedPack = "ai-llm"; ExpectedSkill = "prompt-lookup" },
    [pscustomobject]@{ Name = "embedding strategy"; Prompt = "设计向量嵌入策略用于语义检索"; Grade = "M"; TaskType = "planning"; ExpectedPack = "ai-llm"; ExpectedSkill = "embedding-strategies" },
    [pscustomobject]@{ Name = "llm benchmark"; Prompt = "用MMLU和GSM8K做大模型评测"; Grade = "M"; TaskType = "research"; ExpectedPack = "ai-llm"; ExpectedSkill = "evaluating-llms-harness" },

    [pscustomobject]@{ Name = "tdd flow"; Prompt = "按TDD方式开发，先写失败测试再重构"; Grade = "M"; TaskType = "coding"; ExpectedPack = "code-quality"; ExpectedSkill = "tdd-guide" },
    [pscustomobject]@{ Name = "systematic debug"; Prompt = "请做系统化调试和根因定位"; Grade = "M"; TaskType = "debug"; ExpectedPack = "code-quality"; ExpectedSkill = "systematic-debugging" },
    [pscustomobject]@{ Name = "security review"; Prompt = "做一次OWASP安全审计并给出修复建议"; Grade = "M"; TaskType = "review"; ExpectedPack = "code-quality"; ExpectedSkill = "security-reviewer" },

    [pscustomobject]@{ Name = "brainstorming route"; Prompt = "先做头脑风暴，发散方案"; Grade = "L"; TaskType = "planning"; ExpectedPack = "orchestration-core"; ExpectedSkill = "brainstorming" },
    [pscustomobject]@{ Name = "writing plans route"; Prompt = "请输出实施计划并做任务拆解"; Grade = "L"; TaskType = "planning"; ExpectedPack = "orchestration-core"; ExpectedSkill = "writing-plans" },
    [pscustomobject]@{ Name = "subagent route"; Prompt = "把任务拆成多个子代理并行执行"; Grade = "XL"; TaskType = "planning"; ExpectedPack = "orchestration-core"; ExpectedSkill = "subagent-driven-development" },

    [pscustomobject]@{ Name = "scientific writing"; Prompt = "请按IMRAD结构写科研论文正文"; Grade = "L"; TaskType = "research"; ExpectedPack = "research-design"; ExpectedSkill = "scientific-writing" },
    [pscustomobject]@{ Name = "figma implementation"; Prompt = "把这个Figma设计稿还原为可运行代码"; Grade = "L"; TaskType = "planning"; ExpectedPack = "research-design"; ExpectedSkill = "figma-implement-design" },
    [pscustomobject]@{ Name = "experiment design"; Prompt = "帮我设计准实验方法，比较DiD和ITS"; Grade = "L"; TaskType = "planning"; ExpectedPack = "research-design"; ExpectedSkill = "designing-experiments" }
)

$results = @()
Write-Host "=== VCO Skill-Index Routing Audit ==="

foreach ($case in $cases) {
    $route = Invoke-Route -Prompt $case.Prompt -Grade $case.Grade -TaskType $case.TaskType

    $results += Assert-True -Condition ($route.selected.pack_id -eq $case.ExpectedPack) -Message "[$($case.Name)] pack expected=$($case.ExpectedPack), actual=$($route.selected.pack_id)"
    $results += Assert-True -Condition ($route.selected.skill -eq $case.ExpectedSkill) -Message "[$($case.Name)] skill expected=$($case.ExpectedSkill), actual=$($route.selected.skill)"
    $results += Assert-True -Condition ($route.selected.selection_reason -in @("keyword_ranked", "requested_skill", "fallback_first_candidate", "fallback_task_default", "fallback_task_default_after_task_filter", "fallback_first_candidate_after_task_filter")) -Message "[$($case.Name)] selection reason is valid"
}

# Determinism check for per-skill selection.
$detA = Invoke-Route -Prompt "请帮我修改xlsx工作簿并保留公式" -Grade "M" -TaskType "coding"
$detB = Invoke-Route -Prompt "请帮我修改xlsx工作簿并保留公式" -Grade "M" -TaskType "coding"
$results += Assert-True -Condition ($detA.selected.skill -eq $detB.selected.skill) -Message "[determinism] selected skill is stable"
$results += Assert-True -Condition ($detA.selected.pack_id -eq $detB.selected.pack_id) -Message "[determinism] selected pack is stable"
$results += Assert-True -Condition ($detA.confidence -eq $detB.confidence) -Message "[determinism] confidence is stable"

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

Write-Host "Skill-index routing audit passed."
exit 0

