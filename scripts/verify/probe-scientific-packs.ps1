param(
    [string]$OutputDirectory,
    [switch]$DefaultIncludePrompt,
    [switch]$Unattended
)

$ErrorActionPreference = "Stop"

function New-OutputDir {
    param([string]$Path)
    if (-not $Path) { return $null }
    New-Item -ItemType Directory -Path $Path -Force | Out-Null
    return (Resolve-Path -LiteralPath $Path).Path
}

function Get-CaseMetrics {
    param(
        [object]$Case,
        [object]$Result
    )

    $selectedPack = if ($Result -and $Result.selected) { [string]$Result.selected.pack_id } else { "" }
    $selectedSkill = if ($Result -and $Result.selected) { [string]$Result.selected.skill } else { "" }

    $expectedPack = if ($Case.expected_pack) { [string]$Case.expected_pack } else { "" }
    $expectedSkill = if ($Case.expected_skill) { [string]$Case.expected_skill } else { "" }

    $packMatch = if ($expectedPack) { ($selectedPack -eq $expectedPack) } else { $null }
    $skillMatch = if ($expectedSkill) { ($selectedSkill -eq $expectedSkill) } else { $null }

    return [pscustomobject]@{
        pack_match = $packMatch
        skill_match = $skillMatch
        selected_pack = $selectedPack
        selected_skill = $selectedSkill
    }
}

function Write-MarkdownReport {
    param(
        [string]$Path,
        [object[]]$Rows,
        [object[]]$GroupSummary,
        [hashtable]$Meta
    )

    $lines = @()
    $lines += "# VCO Scientific Pack Probe Report"
    $lines += ""
    $lines += ("- Generated (UTC): {0}" -f $Meta.generated_utc)
    $lines += ('- Output dir: `{0}`' -f $Meta.output_dir)
    $lines += ("- Cases: {0}" -f $Rows.Count)
    $lines += ("- Unattended: {0}" -f ([bool]$Meta.unattended))
    $lines += ""

    $lines += "## Group Summary"
    $lines += ""
    $lines += "| Group | Cases | Pack match | Skill match* | Confirm ratio | Avg conf |"
    $lines += "| --- | ---: | ---: | ---: | ---: | ---: |"
    foreach ($g in $GroupSummary) {
        $lines += ("| {0} | {1} | {2:P0} | {3} | {4:P0} | {5:N2} |" -f `
            $g.group, $g.case_count, $g.pack_match_ratio, $g.skill_match_text, $g.confirm_required_ratio, $g.avg_confidence)
    }
    $lines += ""
    $lines += '* Skill match is only computed for cases with an `expected_skill`.'
    $lines += ""

    $lines += "## Per-case Results"
    $lines += ""
    $lines += "| Case | Group | Grade/Task | Route | Selected pack/skill | Conf | Gap | Pack OK | Skill OK |"
    $lines += "| --- | --- | --- | --- | --- | ---: | ---: | --- | --- |"
    foreach ($r in $Rows) {
        $selected = if ($r.selected_pack) { '`{0}` / `{1}`' -f $r.selected_pack, $r.selected_skill } else { "-" }
        $packOk = if ($r.pack_match -eq $true) { "OK" } elseif ($r.pack_match -eq $false) { "FAIL" } else { "-" }
        $skillOk = if ($r.skill_match -eq $true) { "OK" } elseif ($r.skill_match -eq $false) { "FAIL" } else { "-" }
        $lines += ("| {0} | {1} | {2}/{3} | {4} | {5} | {6:N2} | {7:N2} | {8} | {9} |" -f `
            $r.name, $r.group, $r.grade, $r.task_type, ("{0} ({1})" -f $r.route_mode, $r.route_reason), $selected, $r.confidence, $r.top1_top2_gap, $packOk, $skillOk)
    }

    $lines -join "`n" | Set-Content -LiteralPath $Path -Encoding UTF8
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$routerPath = Join-Path $repoRoot "scripts\\router\\resolve-pack-route.ps1"

if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path $repoRoot "outputs\\verify\\route-probe-scientific"
}
if (-not [System.IO.Path]::IsPathRooted($OutputDirectory)) {
    $OutputDirectory = Join-Path $repoRoot $OutputDirectory
}
$OutputDirectory = New-OutputDir -Path $OutputDirectory
$caseDir = New-OutputDir -Path (Join-Path $OutputDirectory "cases")

$cases = @(
    # science-literature-citations
    [pscustomobject]@{
        name = "lit_pubmed_pmid_bibtex"
        group = "science-literature-citations"
        prompt = "/vibe 用 PubMed 根据 PMID 12345 拉取文献信息，并导出 BibTeX 引用"
        grade = "M"
        task_type = "research"
        expected_pack = "science-literature-citations"
        expected_skill = "pubmed-database"
        requested_skill = $null
    },
    [pscustomobject]@{
        name = "lit_zotero_bibtex"
        group = "science-literature-citations"
        prompt = "/vibe 用 Zotero 管理参考文献，去重并导出 BibTeX"
        grade = "M"
        task_type = "planning"
        expected_pack = "science-literature-citations"
        expected_skill = $null
        requested_skill = $null
    },
    [pscustomobject]@{
        name = "lit_peer_review"
        group = "science-literature-citations"
        prompt = "/vibe 请对这篇论文做 peer review：指出方法学缺陷、统计问题和可复现性风险"
        grade = "L"
        task_type = "review"
        expected_pack = "science-peer-review"
        expected_skill = "peer-review"
        requested_skill = $null
    },

    # science-chem-drug
    [pscustomobject]@{
        name = "chem_rdkit_fingerprint"
        group = "science-chem-drug"
        prompt = "/vibe 用 RDKit 解析 SMILES，计算 Morgan fingerprint，并做相似度检索"
        grade = "M"
        task_type = "coding"
        expected_pack = "science-chem-drug"
        expected_skill = "rdkit"
        requested_skill = $null
    },
    [pscustomobject]@{
        name = "chem_chembl_ic50"
        group = "science-chem-drug"
        prompt = "/vibe 在 ChEMBL 查询某靶点的 IC50 / Ki 活性数据，并输出结构化表格"
        grade = "M"
        task_type = "research"
        expected_pack = "science-chem-drug"
        expected_skill = "chembl-database"
        requested_skill = $null
    },
    [pscustomobject]@{
        name = "chem_diffdock_pose"
        group = "science-chem-drug"
        prompt = "/vibe 用 DiffDock 做 docking pose prediction：给定 PDB + SMILES 输出结合构象"
        grade = "M"
        task_type = "coding"
        expected_pack = "science-chem-drug"
        expected_skill = "diffdock"
        requested_skill = $null
    },

    # science-clinical-regulatory
    [pscustomobject]@{
        name = "clinical_trials_nct"
        group = "science-clinical-regulatory"
        prompt = "/vibe 在 ClinicalTrials.gov 按 NCT 编号 NCT01234567 查询试验入排标准与终点"
        grade = "M"
        task_type = "research"
        expected_pack = "science-clinical-regulatory"
        expected_skill = "clinicaltrials-database"
        requested_skill = $null
    },
    [pscustomobject]@{
        name = "clinical_fda_label"
        group = "science-clinical-regulatory"
        prompt = "/vibe 根据 FDA drug label 提取适应症、禁忌、不良反应和用法用量"
        grade = "M"
        task_type = "research"
        expected_pack = "science-clinical-regulatory"
        expected_skill = "fda-database"
        requested_skill = $null
    },
    [pscustomobject]@{
        name = "clinical_pgx_cpic"
        group = "science-clinical-regulatory"
        prompt = "/vibe 基于 CPIC 指南生成药物基因组(Pharmacogenomics/PGx)用药建议，给出证据等级"
        grade = "L"
        task_type = "planning"
        expected_pack = "science-clinical-regulatory"
        expected_skill = "clinical-decision-support"
        requested_skill = $null
    },

    # science-medical-imaging
    [pscustomobject]@{
        name = "imaging_pydicom_tags"
        group = "science-medical-imaging"
        prompt = "/vibe 用 pydicom 读取 DICOM，提取关键 tags，并批量转换为 PNG"
        grade = "M"
        task_type = "coding"
        expected_pack = "science-medical-imaging"
        expected_skill = "pydicom"
        requested_skill = $null
    },
    [pscustomobject]@{
        name = "imaging_idc_dataset"
        group = "science-medical-imaging"
        prompt = "/vibe 从 Imaging Data Commons 搜索 TCIA 影像数据集，并下载 DICOMWeb 样例"
        grade = "M"
        task_type = "research"
        expected_pack = "science-medical-imaging"
        expected_skill = "imaging-data-commons"
        requested_skill = $null
    },
    [pscustomobject]@{
        name = "imaging_pathml_wsi"
        group = "science-medical-imaging"
        prompt = "/vibe 用 PathML 做 WSI patch extraction，并准备一个最小可复现实验脚本"
        grade = "L"
        task_type = "coding"
        expected_pack = "science-medical-imaging"
        expected_skill = "pathml"
        requested_skill = $null
    },

    # science-lab-automation
    [pscustomobject]@{
        name = "lab_opentrons_ot2_protocol"
        group = "science-lab-automation"
        prompt = "/vibe 写一个 Opentrons OT-2 protocol：96孔板分液 + 混匀，输出可运行脚本"
        grade = "M"
        task_type = "coding"
        expected_pack = "science-lab-automation"
        expected_skill = "opentrons-integration"
        requested_skill = $null
    },
    [pscustomobject]@{
        name = "lab_protocolsio_pcr"
        group = "science-lab-automation"
        prompt = "/vibe 在 protocols.io 查找 PCR protocol，并总结关键步骤与关键试剂"
        grade = "M"
        task_type = "research"
        expected_pack = "science-lab-automation"
        expected_skill = "protocolsio-integration"
        requested_skill = $null
    },

    # science-communication-slides
    [pscustomobject]@{
        name = "comm_scientific_slides"
        group = "science-communication-slides"
        prompt = "/vibe 把这篇论文做成 10 页学术汇报 slides（pptx），包含方法/结果/局限性"
        grade = "L"
        task_type = "planning"
        expected_pack = "science-communication-slides"
        expected_skill = "scientific-slides"
        requested_skill = $null
    },
    [pscustomobject]@{
        name = "comm_mermaid_flowchart"
        group = "science-communication-slides"
        prompt = "/vibe 用 Mermaid 写一个实验流程图（flowchart），并给出可复制的 markdown"
        grade = "M"
        task_type = "coding"
        expected_pack = "science-communication-slides"
        expected_skill = "markdown-mermaid-writing"
        requested_skill = $null
    },
    [pscustomobject]@{
        name = "comm_pdf_to_markdown"
        group = "science-communication-slides"
        prompt = "/vibe 把 PDF 转成 Markdown，要求尽量保留表格与标题结构（markitdown）"
        grade = "M"
        task_type = "coding"
        expected_pack = "docs-markitdown-conversion"
        expected_skill = "markitdown"
        requested_skill = $null
    },

    # finance-edgar-macro
    [pscustomobject]@{
        name = "finance_edgar_10k"
        group = "finance-edgar-macro"
        prompt = "/vibe 用 EDGAR 拉取 AAPL 10-K，提取收入/毛利率/分部信息并输出表格"
        grade = "M"
        task_type = "research"
        expected_pack = "finance-edgar-macro"
        expected_skill = "edgartools"
        requested_skill = $null
    },
    [pscustomobject]@{
        name = "finance_fred_cpi_rate"
        group = "finance-edgar-macro"
        prompt = "/vibe 用 FRED 获取 CPI 和联邦基金利率时间序列，并画趋势图"
        grade = "M"
        task_type = "research"
        expected_pack = "finance-edgar-macro"
        expected_skill = "fred-economic-data"
        requested_skill = $null
    },
    [pscustomobject]@{
        name = "finance_alpha_vantage_price"
        group = "finance-edgar-macro"
        prompt = "/vibe 用 Alpha Vantage 获取 AAPL 日线行情并输出 CSV"
        grade = "M"
        task_type = "coding"
        expected_pack = "finance-edgar-macro"
        expected_skill = "alpha-vantage"
        requested_skill = $null
    },

    # science-quantum
    [pscustomobject]@{
        name = "quantum_qiskit_bell"
        group = "science-quantum"
        prompt = "/vibe 用 Qiskit 创建 Bell state quantum circuit，并在模拟器上运行"
        grade = "M"
        task_type = "coding"
        expected_pack = "science-quantum"
        expected_skill = "qiskit"
        requested_skill = $null
    },
    [pscustomobject]@{
        name = "quantum_pennylane_qml"
        group = "science-quantum"
        prompt = "/vibe 用 PennyLane 做 quantum machine learning 的最小示例（QML）"
        grade = "M"
        task_type = "coding"
        expected_pack = "science-quantum"
        expected_skill = "pennylane"
        requested_skill = $null
    },

    # ip-uspto-patents
    [pscustomobject]@{
        name = "ip_uspto_crispr"
        group = "ip-uspto-patents"
        prompt = "/vibe 在 USPTO 检索 CRISPR 的专利，按申请人筛选并汇总关键权利要求"
        grade = "M"
        task_type = "research"
        expected_pack = "ip-uspto-patents"
        expected_skill = "uspto-database"
        requested_skill = $null
    },

    # science-astropy
    [pscustomobject]@{
        name = "astro_astropy_fits_wcs"
        group = "science-astropy"
        prompt = "/vibe 用 Astropy 打开 FITS 文件并做 WCS 坐标转换，输出 RA/DEC"
        grade = "M"
        task_type = "coding"
        expected_pack = "science-astropy"
        expected_skill = "astropy"
        requested_skill = $null
    },

    # science-pymatgen
    [pscustomobject]@{
        name = "materials_pymatgen_poscar"
        group = "science-pymatgen"
        prompt = "/vibe 用 pymatgen 读取 POSCAR，计算结构晶格参数与体积"
        grade = "M"
        task_type = "coding"
        expected_pack = "science-pymatgen"
        expected_skill = "pymatgen"
        requested_skill = $null
    },

    # science-geospatial
    [pscustomobject]@{
        name = "geo_geopandas_shp_to_geojson"
        group = "science-geospatial"
        prompt = "/vibe 用 GeoPandas 读 Shapefile 并导出 GeoJSON，同时做属性表清洗"
        grade = "M"
        task_type = "coding"
        expected_pack = "science-geospatial"
        expected_skill = "geopandas"
        requested_skill = $null
    },
    [pscustomobject]@{
        name = "geo_epsg_transform"
        group = "science-geospatial"
        prompt = "/vibe 做坐标系转换：EPSG:4326 -> EPSG:3857，并解释投影差异"
        grade = "M"
        task_type = "planning"
        expected_pack = "science-geospatial"
        expected_skill = "geomaster"
        requested_skill = $null
    },

    # science-zarr-polars
    [pscustomobject]@{
        name = "bigdata_polars_parquet_groupby"
        group = "science-zarr-polars"
        prompt = "/vibe 用 Polars 读取 Parquet，做 groupby 聚合并优化性能"
        grade = "M"
        task_type = "coding"
        expected_pack = "science-zarr-polars"
        expected_skill = "polars"
        requested_skill = $null
    },
    [pscustomobject]@{
        name = "bigdata_zarr_chunked_array"
        group = "science-zarr-polars"
        prompt = "/vibe 用 Zarr 存储 chunked array 并进行 out-of-core 计算"
        grade = "M"
        task_type = "coding"
        expected_pack = "science-zarr-polars"
        expected_skill = "zarr-python"
        requested_skill = $null
    },
    [pscustomobject]@{
        name = "bigdata_tiledbvcf_query"
        group = "science-zarr-polars"
        prompt = "/vibe 用 TileDB-VCF 管理大规模 VCF，并查询某个基因区域的变异"
        grade = "M"
        task_type = "research"
        expected_pack = "science-tiledbvcf"
        expected_skill = "tiledbvcf"
        requested_skill = $null
    },

    # research-design extensions
    [pscustomobject]@{
        name = "research_hypothesis_generation"
        group = "research-design"
        prompt = "/vibe 基于现有结果提出 3 个可检验的 research hypothesis，并给出最小实验设计"
        grade = "L"
        task_type = "planning"
        expected_pack = "research-design"
        expected_skill = "hypothesis-generation"
        requested_skill = $null
    },
    [pscustomobject]@{
        name = "research_grant_outline"
        group = "research-design"
        prompt = "/vibe 写一份 NIH grant proposal outline：Specific Aims + Significance + Approach"
        grade = "L"
        task_type = "planning"
        expected_pack = "research-design"
        expected_skill = "research-grants"
        requested_skill = $null
    },

    # bio-science extensions
    [pscustomobject]@{
        name = "bio_esm_embeddings"
        group = "bio-science"
        prompt = "/vibe 用 ESM 生成 protein embeddings，并说明输出向量如何用于下游任务"
        grade = "M"
        task_type = "coding"
        expected_pack = "bio-science"
        expected_skill = "esm"
        requested_skill = $null
    },
    [pscustomobject]@{
        name = "bio_cobrapy_fba"
        group = "bio-science"
        prompt = "/vibe 用 COBRApy 做 FBA 代谢通量分析，并解释约束条件"
        grade = "M"
        task_type = "coding"
        expected_pack = "bio-science"
        expected_skill = "cobrapy"
        requested_skill = $null
    },
    [pscustomobject]@{
        name = "bio_scanpy_h5ad_marker_genes"
        group = "bio-science"
        prompt = "/vibe 读取 h5ad，做 Leiden clustering 和 marker genes"
        grade = "M"
        task_type = "research"
        expected_pack = "bio-science"
        expected_skill = "scanpy"
        requested_skill = $null
    },
    [pscustomobject]@{
        name = "bio_pydeseq2_bulk_de"
        group = "bio-science"
        prompt = "/vibe 进行 bulk RNA-seq 差异表达分析并画 volcano plot"
        grade = "M"
        task_type = "research"
        expected_pack = "bio-science"
        expected_skill = "pydeseq2"
        requested_skill = $null
    },
    [pscustomobject]@{
        name = "bio_pysam_bam_vcf_coverage"
        group = "bio-science"
        prompt = "/vibe 解析 BAM 和 VCF 文件并统计 coverage"
        grade = "M"
        task_type = "research"
        expected_pack = "bio-science"
        expected_skill = "pysam"
        requested_skill = $null
    },
    [pscustomobject]@{
        name = "bio_gget_gene_symbol"
        group = "bio-science"
        prompt = "/vibe 用 gget 快速查询 gene symbol 和 Ensembl ID"
        grade = "M"
        task_type = "research"
        expected_pack = "bio-science"
        expected_skill = "gget"
        requested_skill = $null
    },
    [pscustomobject]@{
        name = "bio_flowio_fcs"
        group = "bio-science"
        prompt = "/vibe 读取 FCS 流式细胞文件并提取通道矩阵"
        grade = "M"
        task_type = "coding"
        expected_pack = "bio-science"
        expected_skill = "flowio"
        requested_skill = $null
    },
    [pscustomobject]@{
        name = "bio_arboreto_grn"
        group = "bio-science"
        prompt = "/vibe 用 pySCENIC 和 arboreto 推断 gene regulatory network"
        grade = "M"
        task_type = "research"
        expected_pack = "bio-science"
        expected_skill = "arboreto"
        requested_skill = $null
    },
    [pscustomobject]@{
        name = "bio_geniml_embedding"
        group = "bio-science"
        prompt = "/vibe 用 geniml 做 genomic ML 和 genome embedding"
        grade = "M"
        task_type = "research"
        expected_pack = "bio-science"
        expected_skill = "geniml"
        requested_skill = $null
    }
)

$rows = @()
foreach ($case in $cases) {
    $routerArgs = @{
        Prompt = [string]$case.prompt
        Grade = [string]$case.grade
        TaskType = [string]$case.task_type
        Probe = $true
        ProbeLabel = [string]$case.name
        ProbeOutputDir = $caseDir
        ProbeIncludePrompt = [bool]$DefaultIncludePrompt
    }
    if ($case.requested_skill) {
        $routerArgs.RequestedSkill = [string]$case.requested_skill
    }
    if ($Unattended) {
        $routerArgs.Unattended = $true
    }

    $result = $null
    $errorText = ""
    try {
        $json = & $routerPath @routerArgs
        $result = $json | ConvertFrom-Json
    } catch {
        $errorText = [string]$_.Exception.Message
    }

    $metrics = Get-CaseMetrics -Case $case -Result $result

    $rows += [pscustomobject]@{
        name = [string]$case.name
        group = [string]$case.group
        grade = [string]$case.grade
        task_type = [string]$case.task_type
        route_mode = if ($result) { [string]$result.route_mode } else { "error" }
        route_reason = if ($result) { [string]$result.route_reason } else { $errorText }
        confidence = if ($result -and $result.confidence -ne $null) { [double]$result.confidence } else { 0.0 }
        top1_top2_gap = if ($result -and $result.top1_top2_gap -ne $null) { [double]$result.top1_top2_gap } else { 0.0 }
        candidate_signal = if ($result -and $result.candidate_signal -ne $null) { [double]$result.candidate_signal } else { 0.0 }
        selected_pack = $metrics.selected_pack
        selected_skill = $metrics.selected_skill
        pack_match = $metrics.pack_match
        skill_match = $metrics.skill_match
        probe_reference = if ($result -and $result.probe_reference) { [string]$result.probe_reference } else { "" }
        expected_pack = [string]$case.expected_pack
        expected_skill = [string]$case.expected_skill
    }
}

$groupSummary = @()
foreach ($groupName in ($rows | Select-Object -ExpandProperty group | Sort-Object -Unique)) {
    $items = @($rows | Where-Object { $_.group -eq $groupName })
    if ($items.Count -eq 0) { continue }

    $packMatchItems = @($items | Where-Object { $_.pack_match -ne $null })
    $packMatchRatio = if ($packMatchItems.Count -gt 0) {
        [double](@($packMatchItems | Where-Object { $_.pack_match -eq $true }).Count) / [double]$packMatchItems.Count
    } else { 0.0 }

    $skillMatchItems = @($items | Where-Object { $_.skill_match -ne $null })
    $skillMatchRatio = if ($skillMatchItems.Count -gt 0) {
        [double](@($skillMatchItems | Where-Object { $_.skill_match -eq $true }).Count) / [double]$skillMatchItems.Count
    } else { 0.0 }

    $confirmCount = @($items | Where-Object { $_.route_mode -eq "confirm_required" }).Count
    $confirmRatio = [double]$confirmCount / [double]$items.Count
    $avgConfidence = [double](($items | Measure-Object -Property confidence -Average).Average)

    $skillMatchText = if ($skillMatchItems.Count -gt 0) { "{0:P0}" -f $skillMatchRatio } else { "-" }

    $groupSummary += [pscustomobject]@{
        group = $groupName
        case_count = [int]$items.Count
        pack_match_ratio = [Math]::Round($packMatchRatio, 4)
        skill_match_ratio = [Math]::Round($skillMatchRatio, 4)
        skill_match_text = $skillMatchText
        confirm_required_ratio = [Math]::Round($confirmRatio, 4)
        avg_confidence = [Math]::Round($avgConfidence, 4)
    }
}

$meta = @{
    generated_utc = [DateTime]::UtcNow.ToString("o")
    output_dir = $OutputDirectory
    unattended = [bool]$Unattended
}

$summaryPath = Join-Path $OutputDirectory "summary.json"
$reportPath = Join-Path $OutputDirectory "report.md"

([pscustomobject]@{
    meta = $meta
    group_summary = $groupSummary
    rows = $rows
    report_path = $reportPath
}) | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $summaryPath -Encoding UTF8

Write-MarkdownReport -Path $reportPath -Rows $rows -GroupSummary $groupSummary -Meta $meta

Write-Host ("Probe complete: {0}" -f $reportPath)
Write-Host ("Summary JSON: {0}" -f $summaryPath)
