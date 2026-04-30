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
    [pscustomobject]@{ Name = "bio-science anndata direct owner"; Prompt = "用 AnnData 读写 h5ad，管理 obs/var 元数据和 backed mode 稀疏矩阵"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "bio-science"; ExpectedSkill = "anndata"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "bio-science clinvar evidence owner"; Prompt = "查询 ClinVar 中 BRCA1 variant 的 clinical significance、VUS 和 review stars"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "bio-science"; ExpectedSkill = "bio-database-evidence"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "bio-science kegg evidence owner"; Prompt = "用 KEGG REST 做 pathway mapping、ID conversion 和 metabolic pathway 查询"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "bio-science"; ExpectedSkill = "bio-database-evidence"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "clinical-regulatory clinicaltrials"; Prompt = "在 ClinicalTrials.gov 按 NCT 编号 NCT01234567 查询试验入排标准、终点和 trial phase"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "science-clinical-regulatory"; ExpectedSkill = "clinicaltrials-database"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "clinical-regulatory fda label"; Prompt = "根据 FDA drug label 提取适应症、禁忌、不良反应、recall 和用法用量"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "science-clinical-regulatory"; ExpectedSkill = "fda-database"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "clinical-regulatory clinpgx"; Prompt = "查询 CPIC 药物基因组指南，解释 CYP2C19 和 clopidogrel 的 gene-drug 用药建议"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "science-clinical-regulatory"; ExpectedSkill = "clinpgx-database"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "clinical-regulatory report writing"; Prompt = "撰写 CARE guidelines 病例报告，包含临床时间线、诊断、治疗、知情同意和去标识化检查"; Grade = "M"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = "science-clinical-regulatory"; ExpectedSkill = "clinical-reports"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "clinical-regulatory report review"; Prompt = "审查 clinical report 的 HIPAA 合规性、去标识化、完整性和医学术语规范"; Grade = "M"; TaskType = "review"; RequestedSkill = $null; ExpectedPack = "science-clinical-regulatory"; ExpectedSkill = "clinical-reports"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "clinical-regulatory treatment plan"; Prompt = "为糖尿病患者生成一页式 treatment plan，包含 SMART 目标、用药方案和随访计划"; Grade = "M"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = "science-clinical-regulatory"; ExpectedSkill = "treatment-plans"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "clinical-regulatory iso 13485"; Prompt = "准备 ISO 13485 医疗器械 QMS 认证差距分析、质量手册和 CAPA 程序文件"; Grade = "M"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = "science-clinical-regulatory"; ExpectedSkill = "iso-13485-certification"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "clinical-regulatory cds"; Prompt = "生成 clinical decision support 文档，包含 GRADE 证据、治疗算法、队列生存分析和 biomarker 分层"; Grade = "L"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = "science-clinical-regulatory"; ExpectedSkill = "clinical-decision-support"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "clinical-regulatory blocks generic scientific report"; Prompt = "科研技术报告：包含方法结果讨论，输出 HTML 和 PDF"; Grade = "L"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "science-clinical-regulatory"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "clinical-regulatory blocks code quality review"; Prompt = "审查代码质量、测试覆盖率和安全风险"; Grade = "M"; TaskType = "review"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "science-clinical-regulatory"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },

    [pscustomobject]@{ Name = "docs-media coding canonical"; Prompt = "process xlsx workbook and preserve formulas"; Grade = "M"; TaskType = "coding"; RequestedSkill = "xlsx"; ExpectedPack = "docs-media"; ExpectedSkill = "xlsx"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "media-video research transcribe"; Prompt = "请把会议录音转文字并区分说话人"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "media-video"; ExpectedSkill = "transcribe"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "docs-media spreadsheet analysis owner"; Prompt = "分析这个Excel表格并生成数据透视表"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "docs-media"; ExpectedSkill = "spreadsheet"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "docs-media docx layout owner"; Prompt = "检查这个 Word 文档的排版和 layout fidelity"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "docs-media"; ExpectedSkill = "docx"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "screen-capture screenshot owner"; Prompt = "给我截一张当前桌面截图"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "screen-capture"; ExpectedSkill = "screenshot"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "docs-media jupyter not owned"; Prompt = "创建一个Jupyter notebook教程"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = $null; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback"); BlockedPack = "docs-media" },

    [pscustomobject]@{ Name = "medical imaging pydicom direct owner"; Prompt = "用 pydicom 读取 CT DICOM tags，匿名化 PatientName，并导出 pixel array"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "science-medical-imaging"; ExpectedSkill = "pydicom"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "medical imaging idc direct owner"; Prompt = "从 NCI Imaging Data Commons 查询 TCIA cancer imaging cohort 并下载 DICOMWeb 样例"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "science-medical-imaging"; ExpectedSkill = "imaging-data-commons"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "medical imaging histolab direct owner"; Prompt = "用 histolab 对 whole slide image 做 tissue detection 和 H&E tile extraction"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "science-medical-imaging"; ExpectedSkill = "histolab"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "medical imaging omero direct owner"; Prompt = "用 OMERO server Python API 读取 microscopy image server 的 ROI annotations"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "science-medical-imaging"; ExpectedSkill = "omero-integration"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "medical imaging pathml direct owner"; Prompt = "用 PathML 构建 computational pathology WSI pipeline，包含 nucleus segmentation 和 spatial graph"; Grade = "M"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = "science-medical-imaging"; ExpectedSkill = "pathml"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "medical imaging blocks generic datacommons"; Prompt = "用 Data Commons 查询 population indicators、statistical variables 和 DCID，不涉及 Imaging Data Commons 或 DICOMWeb"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "science-medical-imaging"; BlockedSkill = "imaging-data-commons"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "medical imaging blocks pubmed evidence"; Prompt = "查询 PubMed 文献并整理 PMID citation evidence table"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "science-medical-imaging"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "medical imaging blocks clinicaltrials"; Prompt = "从 ClinicalTrials.gov 查询 NCT01234567 的终点和入排标准"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "science-medical-imaging"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "medical imaging blocks latex submission pdf"; Prompt = "写 LaTeX 论文并用 latexmk 构建 submission PDF"; Grade = "XL"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "scholarly-publishing-workflow"; ExpectedSkill = "latex-submission-pipeline"; BlockedPack = "science-medical-imaging"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "medical imaging blocks generic image processing"; Prompt = "对普通 PNG 图片做 OCR、截图裁剪和图像增强，不涉及 DICOM、WSI、OMERO 或 PathML"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "science-medical-imaging"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "medical imaging histolab not pathml"; Prompt = "用 histolab 做 WSI tile extraction、tissue detection 和 H&E tile dataset preparation"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "science-medical-imaging"; ExpectedSkill = "histolab"; BlockedSkill = "pathml"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "medical imaging pathml not histolab"; Prompt = "用 PathML 构建 digital pathology workflow，包含 nucleus segmentation、multiplex pathology 和 tissue graph"; Grade = "M"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = "science-medical-imaging"; ExpectedSkill = "pathml"; BlockedSkill = "histolab"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "longtail simpy explicit"; Prompt = "用 SimPy 建一个离散事件仿真 queue resource process，并输出 resource utilization"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "science-simpy-simulation"; ExpectedSkill = "simpy"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "longtail fluidsim explicit"; Prompt = "用 FluidSim 做 Navier-Stokes CFD turbulence spectra 分析"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "science-fluidsim-cfd"; ExpectedSkill = "fluidsim"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "longtail matchms explicit"; Prompt = "用 matchms 处理 MS/MS mass spectra 并计算 spectral similarity"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "science-matchms-spectra"; ExpectedSkill = "matchms"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "longtail matlab explicit"; Prompt = "写 MATLAB/Octave .m script 并连接 Simulink 模型"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "science-matlab-octave"; ExpectedSkill = "matlab"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "longtail neuropixels explicit"; Prompt = "分析 Neuropixels SpikeGLX 数据，运行 Kilosort spike sorting 并整理 probe channel map"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "science-neuropixels"; ExpectedSkill = "neuropixels-analysis"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "longtail pymc explicit"; Prompt = "用 PyMC 建立 Bayesian hierarchical model，运行 NUTS MCMC 和 posterior predictive checks"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "science-pymc-bayesian"; ExpectedSkill = "pymc"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "longtail pymoo explicit"; Prompt = "用 pymoo 做 NSGA-II multi-objective optimization，输出 Pareto front"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "science-pymoo-optimization"; ExpectedSkill = "pymoo"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "longtail rowan explicit"; Prompt = "用 Rowan rowan-python 调用 labs.rowansci.com API 管理计算任务"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "science-rowan-chemistry"; ExpectedSkill = "rowan"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "longtail sb3 explicit"; Prompt = "用 Stable-Baselines3 SB3 训练 PPO reinforcement learning agent"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "ml-stable-baselines3"; ExpectedSkill = "stable-baselines3"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "longtail timesfm explicit"; Prompt = "用 TimesFM 做 zero-shot forecasting，设置 forecast horizon 和 prediction intervals"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "science-timesfm-forecasting"; ExpectedSkill = "timesfm-forecasting"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "longtail torch geometric explicit"; Prompt = "用 PyTorch Geometric torch_geometric 写 PyG GNN node classification pipeline"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "ml-torch-geometric"; ExpectedSkill = "torch-geometric"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "longtail blocks generic simulation"; Prompt = "设计一个普通 agent-based simulation 和 Monte Carlo simulation，不使用 SimPy 或离散事件资源队列"; Grade = "M"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "science-simpy-simulation"; BlockedSkill = "simpy"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "longtail blocks numpy matlab"; Prompt = "用 NumPy 做 Python matrix multiplication，在 Jupyter 里做 scientific visualization，不使用 MATLAB 或 Octave"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "science-matlab-octave"; BlockedSkill = "matlab"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "longtail blocks generic chemistry rowan"; Prompt = "用 RDKit、PubChem、ChEMBL 做 generic chemistry、docking、pKa、conformer search 和 molecular ML，不调用 Rowan"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "science-rowan-chemistry"; BlockedSkill = "rowan"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "longtail blocks sklearn sb3"; Prompt = "用 scikit-learn 训练 supervised classification 模型，不是 reinforcement learning 或 SB3"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "ml-stable-baselines3"; BlockedSkill = "stable-baselines3"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "longtail blocks generic forecast timesfm"; Prompt = "做普通 business forecast、ARIMA baseline 和 tabular regression，不使用 TimesFM 或 foundation forecasting"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "science-timesfm-forecasting"; BlockedSkill = "timesfm-forecasting"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "finance edgar direct owner"; Prompt = "用 EDGAR 拉取 AAPL 10-K 并解析 XBRL financial statements"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "finance-edgar-macro"; ExpectedSkill = "edgartools"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "finance alpha vantage direct owner"; Prompt = "用 Alpha Vantage 获取 AAPL 日线 OHLCV 行情和 technical indicators 并输出 CSV"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "finance-edgar-macro"; ExpectedSkill = "alpha-vantage"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "finance fred direct owner"; Prompt = "用 FRED 获取 CPI PCE GDP unemployment 和 fed funds rate 时间序列"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "finance-edgar-macro"; ExpectedSkill = "fred-economic-data"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "finance treasury fiscal direct owner"; Prompt = "用 U.S. Treasury Fiscal Data 查询 national debt federal spending 和 deficit"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "finance-edgar-macro"; ExpectedSkill = "usfiscaldata"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "finance hedge fund monitor direct owner"; Prompt = "查询 OFR Hedge Fund Monitor 和 Form PF aggregate statistics"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "finance-edgar-macro"; ExpectedSkill = "hedgefundmonitor"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "finance market report direct owner"; Prompt = "生成 consulting-style market research report industry report 和 competitive analysis"; Grade = "M"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = "finance-edgar-macro"; ExpectedSkill = "market-research-reports"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "finance data commons direct owner"; Prompt = "用 Data Commons 查询 public statistical data statistical variables 和人口经济指标"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "finance-edgar-macro"; ExpectedSkill = "datacommons-client"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "finance blocks generic public data"; Prompt = "搜索公共数据集和 open dataset 下载链接，不限定 Data Commons 或人口经济指标"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "finance-edgar-macro"; BlockedSkill = "datacommons-client"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "finance blocks scientific report pdf"; Prompt = "写一篇科研报告，包含 methods results discussion 并导出 PDF"; Grade = "L"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "finance-edgar-macro"; BlockedSkill = "market-research-reports"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "finance blocks latex submission pdf"; Prompt = "写 LaTeX 论文并用 latexmk 构建 submission PDF"; Grade = "XL"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "scholarly-publishing-workflow"; ExpectedSkill = "latex-submission-pipeline"; BlockedSkill = "market-research-reports"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "finance blocks pubmed evidence"; Prompt = "查询 PubMed 文献并整理 evidence table 和 PMID citations"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "finance-edgar-macro"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "finance blocks clinicaltrials nct"; Prompt = "从 ClinicalTrials.gov 查询 NCT01234567 试验终点和入排标准"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "finance-edgar-macro"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "finance fred not us fiscal"; Prompt = "用 FRED 获取 CPI from FRED 和 Federal Reserve Economic Data 时间序列"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "finance-edgar-macro"; ExpectedSkill = "fred-economic-data"; BlockedSkill = "usfiscaldata"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "finance treasury not fred"; Prompt = "用 U.S. Treasury Fiscal Data 查 national debt 和 federal spending"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "finance-edgar-macro"; ExpectedSkill = "usfiscaldata"; BlockedSkill = "fred-economic-data"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "finance sec 13f not hedgefundmonitor"; Prompt = "查询 SEC 13F holdings 和 institutional holdings"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "finance-edgar-macro"; ExpectedSkill = "edgartools"; BlockedSkill = "hedgefundmonitor"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "zarr polars direct owner"; Prompt = "用 Polars 读取 Parquet 并做 lazy groupby aggregation"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "science-zarr-polars"; ExpectedSkill = "polars"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "tiledbvcf single owner"; Prompt = "用 TileDB-VCF 管理大规模 VCF BCF 并查询基因区域 variant"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "science-tiledbvcf"; ExpectedSkill = "tiledbvcf"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "geospatial geopandas direct owner"; Prompt = "用 GeoPandas 读取 Shapefile 并导出 GeoJSON，做 spatial join"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "science-geospatial"; ExpectedSkill = "geopandas"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "geospatial blocks ncbi geo"; Prompt = "查询 NCBI GEO 的 GSE 和 GSM gene expression dataset"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = $null; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback"); BlockedPack = "science-geospatial" },
    [pscustomobject]@{ Name = "web-scraping research ZH"; Prompt = "请用爬虫抓取 https://example.com ，并用 CSS selector '#main a' 提取所有链接（scrape / 抓取 / selector）"; Grade = "L"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "web-scraping"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "web-scraping canonical scrapling"; Prompt = "scrape https://nopecha.com/demo/cloudflare and extract '#padded_content a' (Cloudflare / Turnstile) to markdown"; Grade = "M"; TaskType = "coding"; RequestedSkill = "scrapling"; ExpectedPack = "web-scraping"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "web scraping playwright direct owner"; Prompt = "用 Playwright 做 browser automation，登录表单并截图调试动态页面"; Grade = "M"; TaskType = "debug"; RequestedSkill = $null; ExpectedPack = "web-scraping"; ExpectedSkill = "playwright"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "web scraping blocks generic website research"; Prompt = "检索 PubMed website 上的文献并整理 citation references"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = $null; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback"); BlockedPack = "web-scraping" },

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

    [pscustomobject]@{ Name = "ai-llm research"; Prompt = "query OpenAI official docs for Responses API and model limits"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "ai-llm"; ExpectedSkill = "openai-docs"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "ai-llm prompt lookup"; Prompt = "帮我检索提示词模板并优化prompt"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "ai-llm"; ExpectedSkill = "prompt-lookup"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "ai-llm embedding strategy"; Prompt = "设计向量嵌入策略用于语义检索"; Grade = "M"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = "ai-llm"; ExpectedSkill = "embedding-strategies"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "ai-llm similarity search"; Prompt = "设计vector database nearest neighbor similarity search方案"; Grade = "M"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = "ai-llm"; ExpectedSkill = "similarity-search-patterns"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "ai-llm benchmark"; Prompt = "用MMLU和GSM8K做大模型评测"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "ai-llm"; ExpectedSkill = "evaluating-llms-harness"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "ai-llm blocks generic framework docs"; Prompt = "查询React 19官方文档并给出useEffect示例"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "ai-llm"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "ai-llm blocks code model eval"; Prompt = "用HumanEval和MBPP评测代码生成模型"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "ai-llm"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "ai-llm blocks nowait"; Prompt = "优化DeepSeek-R1推理，减少thinking tokens和反思token"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "ai-llm"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "ai-llm blocks transformer lens"; Prompt = "用TransformerLens做activation patching和circuit analysis"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "ai-llm"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "ai-llm blocks hf transformers"; Prompt = "用Hugging Face Transformers微调BERT文本分类模型"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "ai-llm"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },

    [pscustomobject]@{ Name = "research-design planning"; Prompt = "design quasi-experimental methodology with DiD and ITS"; Grade = "L"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = "research-design"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "research-design hypothesis generation"; Prompt = "根据实验观察生成可检验的科研假设和预测"; Grade = "L"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = "research-design"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "research-design causal analysis"; Prompt = "用 DID 和 synthetic control 做因果分析方案"; Grade = "L"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "research-design"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "research-design grant proposal"; Prompt = "写 NSF 科研基金申请书的 significance 和 innovation"; Grade = "L"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = "research-design"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "publishing workflow package"; Prompt = "规划一套期刊投稿工作流，包含投稿包、校样和 camera-ready"; Grade = "L"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = "scholarly-publishing-workflow"; ExpectedSkill = "scholarly-publishing"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "publishing latex pipeline"; Prompt = "配置 latexmk/chktex/latexindent 编译论文 PDF 并打包 submission zip"; Grade = "XL"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "scholarly-publishing-workflow"; ExpectedSkill = "latex-submission-pipeline"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "publishing venue template"; Prompt = "查 NeurIPS 模板和匿名投稿格式要求"; Grade = "L"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = "scholarly-publishing-workflow"; ExpectedSkill = "venue-templates"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "figures matplotlib wording direct owner"; Prompt = "用 matplotlib 绘制 publication-ready result figure，600dpi TIFF，带误差棒和显著性标注"; Grade = "L"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "science-figures-visualization"; ExpectedSkill = "scientific-visualization"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "figures mermaid schematic direct owner"; Prompt = "用 Mermaid 写一个实验流程图 flowchart，并给出可复制 markdown"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "science-figures-visualization"; ExpectedSkill = "scientific-schematics"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "science reporting html pdf direct owner"; Prompt = "科研技术报告：包含方法结果讨论，输出 HTML 和 PDF，附录写清复现步骤"; Grade = "L"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = "science-reporting"; ExpectedSkill = "scientific-reporting"; AllowedModes = @("pack_overlay", "confirm_required") },

    [pscustomobject]@{ Name = "aios-core removed planning"; Prompt = "create PRD and user story backlog with quality gate"; Grade = "L"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "aios-core"; BlockedSkill = "aios-master"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },

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
$detA = Invoke-Route -Prompt "run code review and security scan" -Grade "M" -TaskType "review" -RequestedSkill "code-reviewer"
$detB = Invoke-Route -Prompt "run code review and security scan" -Grade "M" -TaskType "review" -RequestedSkill "code-reviewer"
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
