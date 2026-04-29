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
    [pscustomobject]@{ Name = "speech synthesis"; Prompt = "把这段文本做语音合成并输出mp3"; Grade = "M"; TaskType = "research"; ExpectedPack = "media-video"; ExpectedSkill = "speech" },
    [pscustomobject]@{ Name = "meeting transcription"; Prompt = "请把会议录音转文字并区分说话人"; Grade = "M"; TaskType = "research"; ExpectedPack = "media-video"; ExpectedSkill = "transcribe" },
    [pscustomobject]@{ Name = "pdf extraction"; Prompt = "读取pdf并提取章节正文"; Grade = "M"; TaskType = "coding"; ExpectedPack = "docs-media"; ExpectedSkill = "pdf" },
    [pscustomobject]@{ Name = "screenshot capture"; Prompt = "给我截一张当前桌面截图"; Grade = "M"; TaskType = "coding"; ExpectedPack = "screen-capture"; ExpectedSkill = "screenshot" },

    [pscustomobject]@{ Name = "sklearn training"; Prompt = "用scikit-learn做分类训练和交叉验证"; Grade = "L"; TaskType = "research"; ExpectedPack = "data-ml"; ExpectedSkill = "scikit-learn" },
    [pscustomobject]@{ Name = "shap interpretation"; Prompt = "请计算SHAP解释并输出beeswarm图"; Grade = "L"; TaskType = "research"; ExpectedPack = "data-ml"; ExpectedSkill = "shap" },
    [pscustomobject]@{ Name = "umap reduction"; Prompt = "使用UMAP进行降维可视化"; Grade = "L"; TaskType = "research"; ExpectedPack = "data-ml"; ExpectedSkill = "scikit-learn" },
    [pscustomobject]@{ Name = "data leakage guard"; Prompt = "做特征工程前先做数据泄漏检查"; Grade = "L"; TaskType = "research"; ExpectedPack = "data-ml"; ExpectedSkill = "ml-data-leakage-guard" },

    [pscustomobject]@{ Name = "scanpy single-cell"; Prompt = "做单细胞RNA-seq聚类与注释，使用scanpy"; Grade = "L"; TaskType = "research"; ExpectedPack = "bio-science"; ExpectedSkill = "scanpy" },
    [pscustomobject]@{ Name = "scanpy h5ad marker genes"; Prompt = "读取h5ad，做Leiden clustering和marker genes"; Grade = "L"; TaskType = "research"; ExpectedPack = "bio-science"; ExpectedSkill = "scanpy" },
    [pscustomobject]@{ Name = "pydeseq2 bulk de"; Prompt = "进行bulk RNA-seq差异表达分析并画volcano plot"; Grade = "L"; TaskType = "research"; ExpectedPack = "bio-science"; ExpectedSkill = "pydeseq2" },
    [pscustomobject]@{ Name = "pysam bam vcf coverage"; Prompt = "解析BAM和VCF文件并统计覆盖度"; Grade = "L"; TaskType = "research"; ExpectedPack = "bio-science"; ExpectedSkill = "pysam" },
    [pscustomobject]@{ Name = "biopython fasta genbank"; Prompt = "用BioPython处理FASTA序列并转换GenBank格式"; Grade = "L"; TaskType = "research"; ExpectedPack = "bio-science"; ExpectedSkill = "biopython" },
    [pscustomobject]@{ Name = "gget gene symbol"; Prompt = "用gget快速查询基因symbol和Ensembl ID"; Grade = "L"; TaskType = "research"; ExpectedPack = "bio-science"; ExpectedSkill = "gget" },
    [pscustomobject]@{ Name = "esm protein embeddings"; Prompt = "用ESM生成protein embeddings"; Grade = "L"; TaskType = "research"; ExpectedPack = "bio-science"; ExpectedSkill = "esm" },
    [pscustomobject]@{ Name = "cobrapy fba"; Prompt = "用COBRApy做FBA代谢通量分析"; Grade = "L"; TaskType = "research"; ExpectedPack = "bio-science"; ExpectedSkill = "cobrapy" },
    [pscustomobject]@{ Name = "flowio fcs"; Prompt = "读取FCS流式细胞文件并提取通道矩阵"; Grade = "L"; TaskType = "research"; ExpectedPack = "bio-science"; ExpectedSkill = "flowio" },
    [pscustomobject]@{ Name = "arboreto grn"; Prompt = "用pySCENIC/arboreto推断基因调控网络"; Grade = "L"; TaskType = "research"; ExpectedPack = "bio-science"; ExpectedSkill = "arboreto" },
    [pscustomobject]@{ Name = "geniml genome embedding"; Prompt = "用geniml做基因组机器学习和genome embedding"; Grade = "L"; TaskType = "research"; ExpectedPack = "bio-science"; ExpectedSkill = "geniml" },
    [pscustomobject]@{ Name = "rdkit smiles not bio"; Prompt = "用RDKit解析SMILES并计算Morgan fingerprint"; Grade = "L"; TaskType = "research"; ExpectedPack = "science-chem-drug"; ExpectedSkill = "rdkit" },
    [pscustomobject]@{ Name = "pubmed bibtex not bio"; Prompt = "在PubMed检索文献并导出BibTeX"; Grade = "L"; TaskType = "research"; ExpectedPack = "science-literature-citations"; ExpectedSkill = "pubmed-database" },
    [pscustomobject]@{ Name = "submission rebuttal not bio"; Prompt = "写论文投稿cover letter和rebuttal matrix"; Grade = "L"; TaskType = "planning"; ExpectedPack = "scholarly-publishing-workflow"; ExpectedSkill = "submission-checklist" },
    [pscustomobject]@{ Name = "sklearn cross validation not bio"; Prompt = "用scikit-learn训练分类模型并交叉验证"; Grade = "L"; TaskType = "research"; ExpectedPack = "data-ml"; ExpectedSkill = "scikit-learn" },
    [pscustomobject]@{ Name = "dicom tags not bio"; Prompt = "读取DICOM并提取tags"; Grade = "L"; TaskType = "research"; ExpectedPack = "science-medical-imaging"; ExpectedSkill = "pydicom" },

    [pscustomobject]@{ Name = "github ci fix"; Prompt = "排查GitHub Actions CI失败并修复"; Grade = "L"; TaskType = "debug"; ExpectedPack = "integration-devops"; ExpectedSkill = "gh-fix-ci" },
    [pscustomobject]@{ Name = "mcp integration"; Prompt = "需要接入MCP server并配置.mcp.json"; Grade = "L"; TaskType = "planning"; ExpectedPack = "integration-devops"; ExpectedSkill = "mcp-integration" },
    [pscustomobject]@{ Name = "sentry diagnostics"; Prompt = "查看Sentry线上报错并汇总根因"; Grade = "L"; TaskType = "debug"; ExpectedPack = "integration-devops"; ExpectedSkill = "sentry" },
    [pscustomobject]@{ Name = "vercel deploy"; Prompt = "请把应用部署到Vercel并返回访问链接"; Grade = "L"; TaskType = "coding"; ExpectedPack = "integration-devops"; ExpectedSkill = "vercel-deploy" },

    [pscustomobject]@{ Name = "openai docs"; Prompt = "查询OpenAI官方文档中的Responses API用法"; Grade = "M"; TaskType = "research"; ExpectedPack = "ai-llm"; ExpectedSkill = "openai-docs" },
    [pscustomobject]@{ Name = "prompt lookup"; Prompt = "帮我检索提示词模板并优化prompt"; Grade = "M"; TaskType = "research"; ExpectedPack = "ai-llm"; ExpectedSkill = "prompt-lookup" },
    [pscustomobject]@{ Name = "embedding strategy"; Prompt = "设计向量嵌入策略用于语义检索"; Grade = "M"; TaskType = "planning"; ExpectedPack = "ai-llm"; ExpectedSkill = "embedding-strategies" },
    [pscustomobject]@{ Name = "llm benchmark"; Prompt = "用MMLU和GSM8K做大模型评测"; Grade = "M"; TaskType = "research"; ExpectedPack = "ai-llm"; ExpectedSkill = "evaluating-llms-harness" },

    [pscustomobject]@{ Name = "tdd flow"; Prompt = "按TDD方式开发，先写失败测试再重构"; Grade = "M"; TaskType = "coding"; ExpectedPack = "code-quality"; ExpectedSkill = "tdd-guide" },
    [pscustomobject]@{ Name = "tdd feature test-first"; Prompt = "write failing tests first for this feature"; Grade = "M"; TaskType = "coding"; ExpectedPack = "code-quality"; ExpectedSkill = "tdd-guide" },
    [pscustomobject]@{ Name = "systematic debug"; Prompt = "请做系统化调试和根因定位"; Grade = "M"; TaskType = "debug"; ExpectedPack = "code-quality"; ExpectedSkill = "systematic-debugging" },
    [pscustomobject]@{ Name = "build compile debug"; Prompt = "构建失败，TypeScript compile error，帮我定位"; Grade = "M"; TaskType = "debug"; ExpectedPack = "code-quality"; ExpectedSkill = "systematic-debugging" },
    [pscustomobject]@{ Name = "general code review"; Prompt = "run code review and quality checks"; Grade = "M"; TaskType = "review"; ExpectedPack = "code-quality"; ExpectedSkill = "code-reviewer" },
    [pscustomobject]@{ Name = "review feedback handling"; Prompt = "收到CodeRabbit评审意见，帮我逐条判断是否要改"; Grade = "M"; TaskType = "review"; ExpectedPack = "code-quality"; ExpectedSkill = "receiving-code-review" },
    [pscustomobject]@{ Name = "completion verification"; Prompt = "准备收尾，确认测试通过并给出验收证据"; Grade = "M"; TaskType = "review"; ExpectedPack = "code-quality"; ExpectedSkill = "verification-before-completion" },
    [pscustomobject]@{ Name = "ai code cleanup"; Prompt = "清理AI生成代码里的废话注释和多余防御式检查"; Grade = "M"; TaskType = "coding"; ExpectedPack = "code-quality"; ExpectedSkill = "deslop" },
    [pscustomobject]@{ Name = "security review"; Prompt = "做一次OWASP安全审计并给出修复建议"; Grade = "M"; TaskType = "review"; ExpectedPack = "code-quality"; ExpectedSkill = "security-reviewer" },
    [pscustomobject]@{ Name = "security audit mixed review"; Prompt = "code review and security audit"; Grade = "M"; TaskType = "review"; ExpectedPack = "code-quality"; ExpectedSkill = "security-reviewer" },

    [pscustomobject]@{ Name = "brainstorming no orchestration core"; Prompt = "先做头脑风暴，发散方案"; Grade = "L"; TaskType = "planning"; BlockedPack = "orchestration-core"; BlockedSkill = "brainstorming" },
    [pscustomobject]@{ Name = "writing plan no orchestration core"; Prompt = "请输出实施计划并做任务拆解"; Grade = "L"; TaskType = "planning"; BlockedPack = "orchestration-core"; BlockedSkill = "writing-plans" },
    [pscustomobject]@{ Name = "subagent no orchestration core"; Prompt = "把任务拆成多个子代理并行执行"; Grade = "XL"; TaskType = "planning"; BlockedPack = "orchestration-core"; BlockedSkill = "subagent-driven-development" },
    [pscustomobject]@{ Name = "speckit explicit compatibility"; Prompt = "/speckit.plan 生成技术计划"; Grade = "L"; TaskType = "planning"; ExpectedPack = "workflow-compatibility"; ExpectedSkill = "spec-kit-vibe-compat" },

    [pscustomobject]@{ Name = "top journal figures"; Prompt = "顶级期刊作图：多面板figure，导出TIFF 600dpi，色盲友好配色，误差棒和显著性标注"; Grade = "L"; TaskType = "coding"; ExpectedPack = "science-figures-visualization"; ExpectedSkill = "scientific-visualization" },
    [pscustomobject]@{ Name = "scientific report"; Prompt = "科研技术报告：包含方法/结果/讨论，输出HTML+PDF，附录写清复现步骤"; Grade = "L"; TaskType = "planning"; ExpectedPack = "science-reporting"; ExpectedSkill = "scientific-reporting" },
    [pscustomobject]@{ Name = "rebuttal matrix"; Prompt = "回复审稿意见：生成rebuttal逐条回应矩阵，提供返修清单，并起草cover letter"; Grade = "L"; TaskType = "planning"; ExpectedPack = "scholarly-publishing-workflow"; ExpectedSkill = "submission-checklist" },

    [pscustomobject]@{ Name = "grant proposal"; Prompt = "请帮我写NSFC科研基金申请书（基金申请书），需要结构化标书与评审点对齐"; Grade = "L"; TaskType = "planning"; ExpectedPack = "research-design"; ExpectedSkill = "research-grants" },

    [pscustomobject]@{ Name = "top ppt deck"; Prompt = "顶级PPT制作：组会汇报slide deck，需要讲述结构与视觉规范"; Grade = "L"; TaskType = "planning"; ExpectedPack = "science-communication-slides"; ExpectedSkill = "scientific-slides" },
    [pscustomobject]@{ Name = "slidev slides as code"; Prompt = "用Slidev做组会汇报：slides as code，要求可复现导出PDF"; Grade = "L"; TaskType = "coding"; ExpectedPack = "science-communication-slides"; ExpectedSkill = "slides-as-code" },

    [pscustomobject]@{ Name = "scientific writing"; Prompt = "请按IMRAD结构写科研论文正文"; Grade = "L"; TaskType = "research"; ExpectedPack = "scholarly-publishing-workflow"; ExpectedSkill = "scientific-writing" },
    [pscustomobject]@{ Name = "figma implementation planning"; Prompt = "把这个Figma设计稿还原为可运行代码"; Grade = "L"; TaskType = "planning"; ExpectedPack = "design-implementation"; ExpectedSkill = "figma-implement-design" },
    [pscustomobject]@{ Name = "figma implementation coding"; Prompt = "把这个Figma设计稿还原为可运行代码"; Grade = "L"; TaskType = "coding"; ExpectedPack = "design-implementation"; ExpectedSkill = "figma-implement-design" },
    [pscustomobject]@{ Name = "experiment design"; Prompt = "帮我设计准实验方法，比较DiD和ITS"; Grade = "L"; TaskType = "planning"; ExpectedPack = "research-design"; ExpectedSkill = "designing-experiments" }
)

$results = @()
Write-Host "=== VCO Skill-Index Routing Audit ==="

foreach ($case in $cases) {
    $route = Invoke-Route -Prompt $case.Prompt -Grade $case.Grade -TaskType $case.TaskType

    if ($case.PSObject.Properties.Name -contains "ExpectedPack" -and $case.ExpectedPack) {
        $results += Assert-True -Condition ($route.selected.pack_id -eq $case.ExpectedPack) -Message "[$($case.Name)] pack expected=$($case.ExpectedPack), actual=$($route.selected.pack_id)"
    }
    if ($case.PSObject.Properties.Name -contains "ExpectedSkill" -and $case.ExpectedSkill) {
        $results += Assert-True -Condition ($route.selected.skill -eq $case.ExpectedSkill) -Message "[$($case.Name)] skill expected=$($case.ExpectedSkill), actual=$($route.selected.skill)"
    }
    if ($case.PSObject.Properties.Name -contains "BlockedPack" -and $case.BlockedPack) {
        $results += Assert-True -Condition ($route.selected.pack_id -ne $case.BlockedPack) -Message "[$($case.Name)] blocked pack $($case.BlockedPack) not selected"
    }
    if ($case.PSObject.Properties.Name -contains "BlockedSkill" -and $case.BlockedSkill) {
        $results += Assert-True -Condition ($route.selected.skill -ne $case.BlockedSkill) -Message "[$($case.Name)] blocked skill $($case.BlockedSkill) not selected"
    }
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
