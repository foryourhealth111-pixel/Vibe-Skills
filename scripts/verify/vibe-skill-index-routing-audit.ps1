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
    [pscustomobject]@{ Name = "quick gene symbol evidence"; Prompt = "快速查询基因symbol和Ensembl ID"; Grade = "L"; TaskType = "research"; ExpectedPack = "bio-science"; ExpectedSkill = "bio-database-evidence" },
    [pscustomobject]@{ Name = "esm protein embeddings"; Prompt = "用ESM生成protein embeddings"; Grade = "L"; TaskType = "research"; ExpectedPack = "bio-science"; ExpectedSkill = "esm" },
    [pscustomobject]@{ Name = "cobrapy fba"; Prompt = "用COBRApy做FBA代谢通量分析"; Grade = "L"; TaskType = "research"; ExpectedPack = "bio-science"; ExpectedSkill = "cobrapy" },
    [pscustomobject]@{ Name = "flowio fcs"; Prompt = "读取FCS流式细胞文件并提取通道矩阵"; Grade = "L"; TaskType = "research"; ExpectedPack = "bio-science"; ExpectedSkill = "flowio" },
    [pscustomobject]@{ Name = "arboreto grn"; Prompt = "用pySCENIC/arboreto推断基因调控网络"; Grade = "L"; TaskType = "research"; ExpectedPack = "bio-science"; ExpectedSkill = "arboreto" },
    [pscustomobject]@{ Name = "geniml genome embedding"; Prompt = "用geniml做基因组机器学习和genome embedding"; Grade = "L"; TaskType = "research"; ExpectedPack = "bio-science"; ExpectedSkill = "geniml" },
    [pscustomobject]@{ Name = "anndata h5ad container"; Prompt = "用 AnnData 读写 h5ad，管理 obs/var 元数据和 backed mode 稀疏矩阵"; Grade = "M"; TaskType = "research"; ExpectedPack = "bio-science"; ExpectedSkill = "anndata" },
    [pscustomobject]@{ Name = "scvi latent model"; Prompt = "用 scVI 和 scANVI 做 single-cell batch correction、latent model 和 cell type annotation"; Grade = "M"; TaskType = "research"; ExpectedPack = "bio-science"; ExpectedSkill = "scvi-tools" },
    [pscustomobject]@{ Name = "deeptools ngs tracks"; Prompt = "用 deepTools 把 BAM 转 bigWig，并围绕 TSS 画 ChIP-seq heatmap profile"; Grade = "M"; TaskType = "research"; ExpectedPack = "bio-science"; ExpectedSkill = "deeptools" },
    [pscustomobject]@{ Name = "cross database evidence"; Prompt = "同时查询 UniProt、KEGG、Reactome 并做 cross-database ID mapping"; Grade = "M"; TaskType = "research"; ExpectedPack = "bio-science"; ExpectedSkill = "bio-database-evidence" },
    [pscustomobject]@{ Name = "alphafold predicted structure"; Prompt = "从 AlphaFold Database 按 UniProt ID 下载 mmCIF，并检查 pLDDT 和 PAE"; Grade = "M"; TaskType = "research"; ExpectedPack = "bio-science"; ExpectedSkill = "bio-database-evidence" },
    [pscustomobject]@{ Name = "clinvar clinical significance"; Prompt = "查询 ClinVar 中 BRCA1 variant 的 clinical significance、VUS 和 review stars"; Grade = "M"; TaskType = "research"; ExpectedPack = "bio-science"; ExpectedSkill = "bio-database-evidence" },
    [pscustomobject]@{ Name = "cosmic cancer mutation"; Prompt = "查询 COSMIC cancer mutation、Cancer Gene Census 和 mutational signatures"; Grade = "M"; TaskType = "research"; ExpectedPack = "bio-science"; ExpectedSkill = "bio-database-evidence" },
    [pscustomobject]@{ Name = "ensembl vep orthologs"; Prompt = "用 Ensembl REST 查询 gene、orthologs、VEP variant effect 和坐标转换"; Grade = "M"; TaskType = "research"; ExpectedPack = "bio-science"; ExpectedSkill = "bio-database-evidence" },
    [pscustomobject]@{ Name = "ncbi gene metadata"; Prompt = "用 NCBI Gene 查询 TP53 symbol、RefSeq、GO annotation 和基因位置"; Grade = "M"; TaskType = "research"; ExpectedPack = "bio-science"; ExpectedSkill = "bio-database-evidence" },
    [pscustomobject]@{ Name = "gwas catalog traits"; Prompt = "查询 GWAS Catalog 中 rs ID、trait association、p-value 和 summary statistics"; Grade = "M"; TaskType = "research"; ExpectedPack = "bio-science"; ExpectedSkill = "bio-database-evidence" },
    [pscustomobject]@{ Name = "kegg pathway mapping"; Prompt = "用 KEGG REST 做 pathway mapping、ID conversion 和 metabolic pathway 查询"; Grade = "M"; TaskType = "research"; ExpectedPack = "bio-science"; ExpectedSkill = "bio-database-evidence" },
    [pscustomobject]@{ Name = "open targets evidence"; Prompt = "用 Open Targets 查询 target-disease association、tractability、safety 和 known drugs"; Grade = "M"; TaskType = "research"; ExpectedPack = "bio-science"; ExpectedSkill = "bio-database-evidence" },
    [pscustomobject]@{ Name = "rcsb pdb structure"; Prompt = "在 RCSB PDB 按 sequence similarity 搜索结构并下载 PDB/mmCIF 坐标"; Grade = "M"; TaskType = "research"; ExpectedPack = "bio-science"; ExpectedSkill = "bio-database-evidence" },
    [pscustomobject]@{ Name = "reactome enrichment"; Prompt = "用 Reactome 做 pathway enrichment、gene-pathway mapping 和 disease pathway 分析"; Grade = "M"; TaskType = "research"; ExpectedPack = "bio-science"; ExpectedSkill = "bio-database-evidence" },
    [pscustomobject]@{ Name = "string ppi network"; Prompt = "用 STRING API 查询 protein-protein interaction network、GO enrichment 和 hub proteins"; Grade = "M"; TaskType = "research"; ExpectedPack = "bio-science"; ExpectedSkill = "bio-database-evidence" },
    [pscustomobject]@{ Name = "cellxgene census"; Prompt = "查询 CZ CELLxGENE Census 的 human lung epithelial cells expression data 和 metadata"; Grade = "M"; TaskType = "research"; ExpectedPack = "bio-science"; ExpectedSkill = "bio-database-evidence" },
    [pscustomobject]@{ Name = "rdkit smiles not bio"; Prompt = "用RDKit解析SMILES并计算Morgan fingerprint"; Grade = "L"; TaskType = "research"; ExpectedPack = "science-chem-drug"; ExpectedSkill = "rdkit" },
    [pscustomobject]@{ Name = "drugbank interaction"; Prompt = "查询 DrugBank 药物相互作用、药物靶点和药理信息"; Grade = "L"; TaskType = "research"; ExpectedPack = "science-chem-drug"; ExpectedSkill = "drugbank-database" },
    [pscustomobject]@{ Name = "pubchem cid lookup"; Prompt = "查询 PubChem CID、SMILES、InChI 和化合物物性"; Grade = "L"; TaskType = "research"; ExpectedPack = "science-chem-drug"; ExpectedSkill = "pubchem-database" },
    [pscustomobject]@{ Name = "brenda enzyme kinetics"; Prompt = "在 BRENDA 查询 EC number 的 Km、kcat 和酶动力学参数"; Grade = "L"; TaskType = "research"; ExpectedPack = "science-chem-drug"; ExpectedSkill = "brenda-database" },
    [pscustomobject]@{ Name = "hmdb metabolite identification"; Prompt = "在 HMDB 里按 MS/MS 谱和代谢物名称做 metabolite identification"; Grade = "L"; TaskType = "research"; ExpectedPack = "science-chem-drug"; ExpectedSkill = "hmdb-database" },
    [pscustomobject]@{ Name = "deepchem molecular ml"; Prompt = "用 DeepChem 训练分子属性预测模型，做 scaffold split、ADMET 毒性预测和 GNN"; Grade = "L"; TaskType = "research"; ExpectedPack = "science-chem-drug"; ExpectedSkill = "deepchem" },
    [pscustomobject]@{ Name = "pytdc benchmark dataset"; Prompt = "用 Therapeutics Data Commons / PyTDC 加载 ADMET benchmark 数据集"; Grade = "L"; TaskType = "research"; ExpectedPack = "science-chem-drug"; ExpectedSkill = "pytdc" },
    [pscustomobject]@{ Name = "pubmed bibtex not bio"; Prompt = "在PubMed检索文献并导出BibTeX"; Grade = "L"; TaskType = "research"; ExpectedPack = "science-literature-citations"; ExpectedSkill = "pubmed-database" },
    [pscustomobject]@{ Name = "pyzotero library bibtex"; Prompt = "用 pyzotero 连接 Zotero library，批量整理条目并导出 BibTeX"; Grade = "M"; TaskType = "coding"; ExpectedPack = "science-literature-citations"; ExpectedSkill = "pyzotero" },
    [pscustomobject]@{ Name = "citation formatting"; Prompt = "整理参考文献格式，修正 DOI，生成 Nature 格式 bibliography"; Grade = "M"; TaskType = "planning"; ExpectedPack = "science-literature-citations"; ExpectedSkill = "citation-management" },
    [pscustomobject]@{ Name = "systematic review prisma"; Prompt = "做系统综述和 meta-analysis，输出 PRISMA 流程和纳排标准"; Grade = "L"; TaskType = "research"; ExpectedPack = "science-literature-citations"; ExpectedSkill = "literature-review" },
    [pscustomobject]@{ Name = "full text evidence table"; Prompt = "做 full-text 文献检索，提取样本量、effect size、方法学细节，生成系统综述证据表"; Grade = "L"; TaskType = "research"; ExpectedPack = "science-literature-citations"; ExpectedSkill = "bgpt-paper-search" },
    [pscustomobject]@{ Name = "scholareval paper quality"; Prompt = "用 ScholarEval rubric 评估这篇论文的问题 formulation、methodology、analysis 和 writing"; Grade = "L"; TaskType = "review"; ExpectedPack = "science-peer-review"; ExpectedSkill = "scholar-evaluation" },
    [pscustomobject]@{ Name = "critical evidence strength"; Prompt = "批判性分析这篇论文的证据强度、偏倚和混杂因素"; Grade = "L"; TaskType = "review"; ExpectedPack = "science-peer-review"; ExpectedSkill = "scientific-critical-thinking" },
    [pscustomobject]@{ Name = "submission rebuttal not bio"; Prompt = "写论文投稿cover letter和rebuttal matrix"; Grade = "L"; TaskType = "planning"; ExpectedPack = "scholarly-publishing-workflow"; ExpectedSkill = "submission-checklist" },
    [pscustomobject]@{ Name = "sklearn cross validation not bio"; Prompt = "用scikit-learn训练分类模型并交叉验证"; Grade = "L"; TaskType = "research"; ExpectedPack = "data-ml"; ExpectedSkill = "scikit-learn" },
    [pscustomobject]@{ Name = "medical pydicom dicom tags"; Prompt = "用 pydicom 读取 CT DICOM tags，匿名化 PatientName，并导出 pixel array"; Grade = "M"; TaskType = "coding"; ExpectedPack = "science-medical-imaging"; ExpectedSkill = "pydicom" },
    [pscustomobject]@{ Name = "medical imaging data commons"; Prompt = "从 NCI Imaging Data Commons 查询 TCIA cancer imaging cohort 并下载 DICOMWeb 样例"; Grade = "M"; TaskType = "research"; ExpectedPack = "science-medical-imaging"; ExpectedSkill = "imaging-data-commons" },
    [pscustomobject]@{ Name = "medical histolab wsi"; Prompt = "用 histolab 对 whole slide image 做 tissue detection 和 H&E tile extraction"; Grade = "M"; TaskType = "coding"; ExpectedPack = "science-medical-imaging"; ExpectedSkill = "histolab" },
    [pscustomobject]@{ Name = "medical omero microscopy"; Prompt = "用 OMERO server Python API 读取 microscopy image server 的 ROI annotations"; Grade = "M"; TaskType = "coding"; ExpectedPack = "science-medical-imaging"; ExpectedSkill = "omero-integration" },
    [pscustomobject]@{ Name = "medical pathml workflow"; Prompt = "用 PathML 构建 computational pathology WSI pipeline，包含 nucleus segmentation 和 spatial graph"; Grade = "M"; TaskType = "planning"; ExpectedPack = "science-medical-imaging"; ExpectedSkill = "pathml" },
    [pscustomobject]@{ Name = "medical generic datacommons blocked"; Prompt = "用 Data Commons 查询 population indicators、statistical variables 和 DCID，不涉及 Imaging Data Commons 或 DICOMWeb"; Grade = "M"; TaskType = "research"; BlockedPack = "science-medical-imaging"; BlockedSkill = "imaging-data-commons" },
    [pscustomobject]@{ Name = "medical pubmed evidence blocked"; Prompt = "查询 PubMed 文献并整理 PMID citation evidence table"; Grade = "M"; TaskType = "research"; BlockedPack = "science-medical-imaging" },
    [pscustomobject]@{ Name = "medical clinicaltrials blocked"; Prompt = "从 ClinicalTrials.gov 查询 NCT01234567 的终点和入排标准"; Grade = "M"; TaskType = "research"; BlockedPack = "science-medical-imaging" },
    [pscustomobject]@{ Name = "medical generic image processing blocked"; Prompt = "对普通 PNG 图片做 OCR、截图裁剪和图像增强，不涉及 DICOM、WSI、OMERO 或 PathML"; Grade = "M"; TaskType = "coding"; BlockedPack = "science-medical-imaging" },
    [pscustomobject]@{ Name = "longtail simpy explicit"; Prompt = "用 SimPy 建一个离散事件仿真 queue resource process，并输出 resource utilization"; Grade = "M"; TaskType = "coding"; ExpectedPack = "science-simpy-simulation"; ExpectedSkill = "simpy" },
    [pscustomobject]@{ Name = "longtail fluidsim explicit"; Prompt = "用 FluidSim 做 Navier-Stokes CFD turbulence spectra 分析"; Grade = "M"; TaskType = "coding"; ExpectedPack = "science-fluidsim-cfd"; ExpectedSkill = "fluidsim" },
    [pscustomobject]@{ Name = "longtail matchms explicit"; Prompt = "用 matchms 处理 MS/MS mass spectra 并计算 spectral similarity"; Grade = "M"; TaskType = "coding"; ExpectedPack = "science-matchms-spectra"; ExpectedSkill = "matchms" },
    [pscustomobject]@{ Name = "longtail matlab explicit"; Prompt = "写 MATLAB/Octave .m script 并连接 Simulink 模型"; Grade = "M"; TaskType = "coding"; ExpectedPack = "science-matlab-octave"; ExpectedSkill = "matlab" },
    [pscustomobject]@{ Name = "longtail neuropixels explicit"; Prompt = "分析 Neuropixels SpikeGLX 数据，运行 Kilosort spike sorting 并整理 probe channel map"; Grade = "M"; TaskType = "research"; ExpectedPack = "science-neuropixels"; ExpectedSkill = "neuropixels-analysis" },
    [pscustomobject]@{ Name = "longtail pymc explicit"; Prompt = "用 PyMC 建立 Bayesian hierarchical model，运行 NUTS MCMC 和 posterior predictive checks"; Grade = "M"; TaskType = "coding"; ExpectedPack = "science-pymc-bayesian"; ExpectedSkill = "pymc" },
    [pscustomobject]@{ Name = "longtail pymoo explicit"; Prompt = "用 pymoo 做 NSGA-II multi-objective optimization，输出 Pareto front"; Grade = "M"; TaskType = "coding"; ExpectedPack = "science-pymoo-optimization"; ExpectedSkill = "pymoo" },
    [pscustomobject]@{ Name = "longtail rowan explicit"; Prompt = "用 Rowan rowan-python 调用 labs.rowansci.com API 管理计算任务"; Grade = "M"; TaskType = "coding"; ExpectedPack = "science-rowan-chemistry"; ExpectedSkill = "rowan" },
    [pscustomobject]@{ Name = "longtail sb3 explicit"; Prompt = "用 Stable-Baselines3 SB3 训练 PPO reinforcement learning agent"; Grade = "M"; TaskType = "coding"; ExpectedPack = "ml-stable-baselines3"; ExpectedSkill = "stable-baselines3" },
    [pscustomobject]@{ Name = "longtail timesfm explicit"; Prompt = "用 TimesFM 做 zero-shot forecasting，设置 forecast horizon 和 prediction intervals"; Grade = "M"; TaskType = "coding"; ExpectedPack = "science-timesfm-forecasting"; ExpectedSkill = "timesfm-forecasting" },
    [pscustomobject]@{ Name = "longtail torch geometric explicit"; Prompt = "用 PyTorch Geometric torch_geometric 写 PyG GNN node classification pipeline"; Grade = "M"; TaskType = "coding"; ExpectedPack = "ml-torch-geometric"; ExpectedSkill = "torch-geometric" },
    [pscustomobject]@{ Name = "longtail blocks generic simulation"; Prompt = "设计一个普通 agent-based simulation 和 Monte Carlo simulation，不使用 SimPy 或离散事件资源队列"; Grade = "M"; TaskType = "planning"; BlockedPack = "science-simpy-simulation"; BlockedSkill = "simpy" },
    [pscustomobject]@{ Name = "longtail blocks numpy matlab"; Prompt = "用 NumPy 做 Python matrix multiplication，在 Jupyter 里做 scientific visualization，不使用 MATLAB 或 Octave"; Grade = "M"; TaskType = "coding"; BlockedPack = "science-matlab-octave"; BlockedSkill = "matlab" },
    [pscustomobject]@{ Name = "longtail blocks generic chemistry rowan"; Prompt = "用 RDKit、PubChem、ChEMBL 做 generic chemistry、docking、pKa、conformer search 和 molecular ML，不调用 Rowan"; Grade = "M"; TaskType = "research"; BlockedPack = "science-rowan-chemistry"; BlockedSkill = "rowan" },
    [pscustomobject]@{ Name = "longtail blocks sklearn sb3"; Prompt = "用 scikit-learn 训练 supervised classification 模型，不是 reinforcement learning 或 SB3"; Grade = "M"; TaskType = "coding"; BlockedPack = "ml-stable-baselines3"; BlockedSkill = "stable-baselines3" },
    [pscustomobject]@{ Name = "longtail blocks generic forecast timesfm"; Prompt = "做普通 business forecast、ARIMA baseline 和 tabular regression，不使用 TimesFM 或 foundation forecasting"; Grade = "M"; TaskType = "research"; BlockedPack = "science-timesfm-forecasting"; BlockedSkill = "timesfm-forecasting" },
    [pscustomobject]@{ Name = "finance edgar"; Prompt = "用 EDGAR 拉取 AAPL 10-K 并解析 XBRL financial statements"; Grade = "M"; TaskType = "research"; ExpectedPack = "finance-edgar-macro"; ExpectedSkill = "edgartools" },
    [pscustomobject]@{ Name = "finance alpha vantage"; Prompt = "用 Alpha Vantage 获取 AAPL 日线 OHLCV 行情和 technical indicators 并输出 CSV"; Grade = "M"; TaskType = "coding"; ExpectedPack = "finance-edgar-macro"; ExpectedSkill = "alpha-vantage" },
    [pscustomobject]@{ Name = "finance fred"; Prompt = "用 FRED 获取 CPI PCE GDP unemployment 和 fed funds rate 时间序列"; Grade = "M"; TaskType = "research"; ExpectedPack = "finance-edgar-macro"; ExpectedSkill = "fred-economic-data" },
    [pscustomobject]@{ Name = "finance us fiscal"; Prompt = "用 U.S. Treasury Fiscal Data 查询 national debt 和 federal spending"; Grade = "M"; TaskType = "research"; ExpectedPack = "finance-edgar-macro"; ExpectedSkill = "usfiscaldata" },
    [pscustomobject]@{ Name = "finance hedge fund monitor"; Prompt = "查询 OFR Hedge Fund Monitor 和 Form PF aggregate statistics"; Grade = "M"; TaskType = "research"; ExpectedPack = "finance-edgar-macro"; ExpectedSkill = "hedgefundmonitor" },
    [pscustomobject]@{ Name = "finance market report"; Prompt = "生成 consulting-style market research report industry report 和 competitive analysis"; Grade = "M"; TaskType = "planning"; ExpectedPack = "finance-edgar-macro"; ExpectedSkill = "market-research-reports" },
    [pscustomobject]@{ Name = "finance data commons"; Prompt = "用 Data Commons 查询 public statistical data statistical variables 和人口经济指标"; Grade = "M"; TaskType = "research"; ExpectedPack = "finance-edgar-macro"; ExpectedSkill = "datacommons-client" },
    [pscustomobject]@{ Name = "finance generic public data blocked"; Prompt = "搜索公共数据集和 open dataset 下载链接，不限定 Data Commons 或人口经济指标"; Grade = "M"; TaskType = "research"; BlockedPack = "finance-edgar-macro"; BlockedSkill = "datacommons-client" },
    [pscustomobject]@{ Name = "finance scientific report blocked"; Prompt = "写一篇科研报告，包含 methods results discussion 并导出 PDF"; Grade = "L"; TaskType = "planning"; BlockedPack = "finance-edgar-macro"; BlockedSkill = "market-research-reports" },
    [pscustomobject]@{ Name = "finance pubmed evidence blocked"; Prompt = "查询 PubMed 文献并整理 evidence table 和 PMID citations"; Grade = "M"; TaskType = "research"; BlockedPack = "finance-edgar-macro" },
    [pscustomobject]@{ Name = "finance clinicaltrials blocked"; Prompt = "从 ClinicalTrials.gov 查询 NCT01234567 试验终点和入排标准"; Grade = "M"; TaskType = "research"; BlockedPack = "finance-edgar-macro" },
    [pscustomobject]@{ Name = "zarr vaex"; Prompt = "用 Vaex 做 out-of-core big dataframe filtering"; Grade = "M"; TaskType = "coding"; ExpectedPack = "science-zarr-polars"; ExpectedSkill = "vaex" },
    [pscustomobject]@{ Name = "tiledbvcf owner"; Prompt = "用 TileDB-VCF 管理大规模 VCF BCF 并查询基因区域 variant"; Grade = "M"; TaskType = "coding"; ExpectedPack = "science-tiledbvcf"; ExpectedSkill = "tiledbvcf" },
    [pscustomobject]@{ Name = "ncbi geo not geospatial"; Prompt = "查询 NCBI GEO 的 GSE 和 GSM gene expression dataset"; Grade = "M"; TaskType = "research"; BlockedPack = "science-geospatial" },
    [pscustomobject]@{ Name = "clinical trials nct"; Prompt = "在 ClinicalTrials.gov 按 NCT 编号 NCT01234567 查询试验入排标准、终点和 trial phase"; Grade = "M"; TaskType = "research"; ExpectedPack = "science-clinical-regulatory"; ExpectedSkill = "clinicaltrials-database" },
    [pscustomobject]@{ Name = "fda label safety"; Prompt = "根据 FDA drug label 提取适应症、禁忌、不良反应、recall 和用法用量"; Grade = "M"; TaskType = "research"; ExpectedPack = "science-clinical-regulatory"; ExpectedSkill = "fda-database" },
    [pscustomobject]@{ Name = "clinpgx cpic lookup"; Prompt = "查询 CPIC 药物基因组指南，解释 CYP2C19 和 clopidogrel 的 gene-drug 用药建议"; Grade = "M"; TaskType = "research"; ExpectedPack = "science-clinical-regulatory"; ExpectedSkill = "clinpgx-database" },
    [pscustomobject]@{ Name = "clinical reports care"; Prompt = "撰写 CARE guidelines 病例报告，包含临床时间线、诊断、治疗、知情同意和去标识化检查"; Grade = "M"; TaskType = "planning"; ExpectedPack = "science-clinical-regulatory"; ExpectedSkill = "clinical-reports" },
    [pscustomobject]@{ Name = "clinical report review"; Prompt = "审查 clinical report 的 HIPAA 合规性、去标识化、完整性和医学术语规范"; Grade = "M"; TaskType = "review"; ExpectedPack = "science-clinical-regulatory"; ExpectedSkill = "clinical-reports" },
    [pscustomobject]@{ Name = "treatment plan"; Prompt = "为糖尿病患者生成一页式 treatment plan，包含 SMART 目标、用药方案和随访计划"; Grade = "M"; TaskType = "planning"; ExpectedPack = "science-clinical-regulatory"; ExpectedSkill = "treatment-plans" },
    [pscustomobject]@{ Name = "iso 13485 qms"; Prompt = "准备 ISO 13485 医疗器械 QMS 认证差距分析、质量手册和 CAPA 程序文件"; Grade = "M"; TaskType = "planning"; ExpectedPack = "science-clinical-regulatory"; ExpectedSkill = "iso-13485-certification" },
    [pscustomobject]@{ Name = "clinical decision support"; Prompt = "生成 clinical decision support 文档，包含 GRADE 证据、治疗算法、队列生存分析和 biomarker 分层"; Grade = "L"; TaskType = "planning"; ExpectedPack = "science-clinical-regulatory"; ExpectedSkill = "clinical-decision-support" },
    [pscustomobject]@{ Name = "scientific report not clinical regulatory"; Prompt = "科研技术报告：包含方法结果讨论，输出 HTML 和 PDF"; Grade = "L"; TaskType = "planning"; BlockedPack = "science-clinical-regulatory" },
    [pscustomobject]@{ Name = "code quality review not clinical regulatory"; Prompt = "审查代码质量、测试覆盖率和安全风险"; Grade = "M"; TaskType = "review"; BlockedPack = "science-clinical-regulatory" },

    [pscustomobject]@{ Name = "github ci fix"; Prompt = "排查GitHub Actions CI失败并修复"; Grade = "L"; TaskType = "debug"; ExpectedPack = "integration-devops"; ExpectedSkill = "gh-fix-ci" },
    [pscustomobject]@{ Name = "mcp integration"; Prompt = "需要接入MCP server并配置.mcp.json"; Grade = "L"; TaskType = "planning"; ExpectedPack = "integration-devops"; ExpectedSkill = "mcp-integration" },
    [pscustomobject]@{ Name = "sentry diagnostics"; Prompt = "查看Sentry线上报错并汇总根因"; Grade = "L"; TaskType = "debug"; ExpectedPack = "integration-devops"; ExpectedSkill = "sentry" },
    [pscustomobject]@{ Name = "vercel deploy"; Prompt = "请把应用部署到Vercel并返回访问链接"; Grade = "L"; TaskType = "coding"; ExpectedPack = "integration-devops"; ExpectedSkill = "vercel-deploy" },
    [pscustomobject]@{ Name = "netlify deploy"; Prompt = "请部署到Netlify并生成预览链接"; Grade = "L"; TaskType = "coding"; ExpectedPack = "integration-devops"; ExpectedSkill = "netlify-deploy" },
    [pscustomobject]@{ Name = "node zombie cleanup"; Prompt = "审计并清理VCO托管的僵尸node进程"; Grade = "L"; TaskType = "debug"; ExpectedPack = "integration-devops"; ExpectedSkill = "node-zombie-guardian" },
    [pscustomobject]@{ Name = "security best practices not devops"; Prompt = "做一次安全最佳实践审查"; Grade = "M"; TaskType = "review"; BlockedPack = "integration-devops" },
    [pscustomobject]@{ Name = "threat model not devops"; Prompt = "为这个仓库做威胁建模"; Grade = "M"; TaskType = "planning"; BlockedPack = "integration-devops" },
    [pscustomobject]@{ Name = "security ownership not devops"; Prompt = "分析安全所有权和bus factor"; Grade = "M"; TaskType = "review"; BlockedPack = "integration-devops" },
    [pscustomobject]@{ Name = "file permission not devops"; Prompt = "处理文件写入失败和Permission denied"; Grade = "M"; TaskType = "debug"; BlockedPack = "integration-devops" },
    [pscustomobject]@{ Name = "benchmarkdotnet not devops"; Prompt = "运行BenchmarkDotNet性能测试"; Grade = "M"; TaskType = "coding"; BlockedPack = "integration-devops" },
    [pscustomobject]@{ Name = "pr review comments not devops"; Prompt = "回复PR评审意见并修改代码"; Grade = "M"; TaskType = "coding"; BlockedPack = "integration-devops" },
    [pscustomobject]@{ Name = "yeet pr publish not devops"; Prompt = "一键提交commit push并打开PR"; Grade = "M"; TaskType = "coding"; BlockedPack = "integration-devops" },

    [pscustomobject]@{ Name = "openai docs"; Prompt = "查询OpenAI官方文档中的Responses API用法"; Grade = "M"; TaskType = "research"; ExpectedPack = "ai-llm"; ExpectedSkill = "openai-docs" },
    [pscustomobject]@{ Name = "prompt lookup"; Prompt = "帮我检索提示词模板并优化prompt"; Grade = "M"; TaskType = "research"; ExpectedPack = "ai-llm"; ExpectedSkill = "prompt-lookup" },
    [pscustomobject]@{ Name = "embedding strategy"; Prompt = "设计向量嵌入策略用于语义检索"; Grade = "M"; TaskType = "planning"; ExpectedPack = "ai-llm"; ExpectedSkill = "embedding-strategies" },
    [pscustomobject]@{ Name = "llm benchmark"; Prompt = "用MMLU和GSM8K做大模型评测"; Grade = "M"; TaskType = "research"; ExpectedPack = "ai-llm"; ExpectedSkill = "evaluating-llms-harness" },
    [pscustomobject]@{ Name = "similarity search patterns"; Prompt = "设计vector database nearest neighbor similarity search方案"; Grade = "M"; TaskType = "planning"; ExpectedPack = "ai-llm"; ExpectedSkill = "similarity-search-patterns" },
    [pscustomobject]@{ Name = "generic framework docs not ai llm"; Prompt = "查询React 19官方文档并给出useEffect示例"; Grade = "M"; TaskType = "coding"; BlockedPack = "ai-llm" },
    [pscustomobject]@{ Name = "code model eval not ai llm"; Prompt = "用HumanEval和MBPP评测代码生成模型"; Grade = "M"; TaskType = "research"; BlockedPack = "ai-llm" },
    [pscustomobject]@{ Name = "nowait not ai llm"; Prompt = "优化DeepSeek-R1推理，减少thinking tokens和反思token"; Grade = "M"; TaskType = "coding"; BlockedPack = "ai-llm" },
    [pscustomobject]@{ Name = "transformer lens not ai llm"; Prompt = "用TransformerLens做activation patching和circuit analysis"; Grade = "M"; TaskType = "research"; BlockedPack = "ai-llm" },
    [pscustomobject]@{ Name = "hf transformers not ai llm"; Prompt = "用Hugging Face Transformers微调BERT文本分类模型"; Grade = "M"; TaskType = "coding"; BlockedPack = "ai-llm" },

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
    [pscustomobject]@{ Name = "deleted modal generic gpu"; Prompt = "把 Python 任务部署到云端 GPU，不指定 Modal，用普通容器也可以"; Grade = "M"; TaskType = "coding"; BlockedPack = "cloud-modalcom"; BlockedSkill = "modal-labs" },
    [pscustomobject]@{ Name = "deleted modal explicit modal"; Prompt = "用 Modal.com 部署 serverless GPU Python function 和 batch job"; Grade = "M"; TaskType = "coding"; BlockedPack = "cloud-modalcom"; BlockedSkill = "modal-labs" },
    [pscustomobject]@{ Name = "deleted quantum qiskit"; Prompt = "用 Qiskit 创建 Bell state quantum circuit 并 transpile"; Grade = "M"; TaskType = "coding"; BlockedPack = "science-quantum"; BlockedSkill = "qiskit" },
    [pscustomobject]@{ Name = "deleted quantum chemistry"; Prompt = "调研 quantum chemistry 论文和 pKa 预测，不写量子电路"; Grade = "M"; TaskType = "research"; BlockedPack = "science-quantum"; BlockedSkill = "qiskit" },

    [pscustomobject]@{ Name = "top journal figures"; Prompt = "顶级期刊作图：多面板figure，导出TIFF 600dpi，色盲友好配色，误差棒和显著性标注"; Grade = "L"; TaskType = "coding"; ExpectedPack = "science-figures-visualization"; ExpectedSkill = "scientific-visualization" },
    [pscustomobject]@{ Name = "matplotlib library wording still visualizer"; Prompt = "用 matplotlib 绘制 publication-ready result figure，600dpi TIFF，带误差棒和显著性标注"; Grade = "L"; TaskType = "coding"; ExpectedPack = "science-figures-visualization"; ExpectedSkill = "scientific-visualization" },
    [pscustomobject]@{ Name = "seaborn library wording still visualizer"; Prompt = "用 seaborn 画模型评估结果图和投稿图，要求色盲友好配色"; Grade = "L"; TaskType = "coding"; ExpectedPack = "science-figures-visualization"; ExpectedSkill = "scientific-visualization" },
    [pscustomobject]@{ Name = "plotly library wording still visualizer"; Prompt = "用 plotly 做 interactive result figure，并导出 HTML figure 给科研报告使用"; Grade = "L"; TaskType = "coding"; ExpectedPack = "science-figures-visualization"; ExpectedSkill = "scientific-visualization" },
    [pscustomobject]@{ Name = "scientific report"; Prompt = "科研技术报告：包含方法/结果/讨论，输出HTML+PDF，附录写清复现步骤"; Grade = "L"; TaskType = "planning"; ExpectedPack = "science-reporting"; ExpectedSkill = "scientific-reporting" },
    [pscustomobject]@{ Name = "reporting html pdf direct owner"; Prompt = "科研技术报告：包含方法结果讨论，输出 HTML 和 PDF，附录写清复现步骤"; Grade = "L"; TaskType = "planning"; ExpectedPack = "science-reporting"; ExpectedSkill = "scientific-reporting" },
    [pscustomobject]@{ Name = "lab automation opentrons ot2"; Prompt = "写一个 Opentrons OT-2 protocol：96孔板分液 + 混匀，输出可运行脚本"; Grade = "M"; TaskType = "coding"; ExpectedPack = "science-lab-automation"; ExpectedSkill = "opentrons-integration" },
    [pscustomobject]@{ Name = "lab automation pylabrobot hamilton"; Prompt = "用 PyLabRobot 控制 Hamilton 和 Tecan 液体处理机器人"; Grade = "M"; TaskType = "coding"; ExpectedPack = "science-lab-automation"; ExpectedSkill = "pylabrobot" },
    [pscustomobject]@{ Name = "lab automation protocolsio publish"; Prompt = "用 protocols.io API 创建并发布一个实验 protocol"; Grade = "M"; TaskType = "coding"; ExpectedPack = "science-lab-automation"; ExpectedSkill = "protocolsio-integration" },
    [pscustomobject]@{ Name = "lab automation benchling registry"; Prompt = "查询 Benchling registry 里的 DNA sequence 和 inventory containers"; Grade = "M"; TaskType = "coding"; ExpectedPack = "science-lab-automation"; ExpectedSkill = "benchling-integration" },
    [pscustomobject]@{ Name = "lab automation labarchives backup"; Prompt = "备份 LabArchives notebook，导出 entries 和 attachments"; Grade = "M"; TaskType = "coding"; ExpectedPack = "science-lab-automation"; ExpectedSkill = "labarchive-integration" },
    [pscustomobject]@{ Name = "lab automation ginkgo cloud lab"; Prompt = "在 Ginkgo Cloud Lab / cloud.ginkgo.bio 准备下单输入"; Grade = "M"; TaskType = "planning"; ExpectedPack = "science-lab-automation"; ExpectedSkill = "ginkgo-cloud-lab" },
    [pscustomobject]@{ Name = "lab automation blocks latchbio"; Prompt = "用 LatchBio / Latch SDK 部署 Nextflow RNA-seq workflow"; Grade = "M"; TaskType = "coding"; BlockedPack = "science-lab-automation" },
    [pscustomobject]@{ Name = "lab automation blocks generic eln negated vendors"; Prompt = "帮我整理电子实验记录 ELN 模板，不指定 Benchling 或 LabArchives"; Grade = "M"; TaskType = "planning"; BlockedPack = "science-lab-automation" },
    [pscustomobject]@{ Name = "lab automation blocks generic attachments negated vendors"; Prompt = "把实验图片和 CSV 附件整理到实验记录里，不使用 LabArchives 或 Benchling"; Grade = "M"; TaskType = "planning"; BlockedPack = "science-lab-automation" },
    [pscustomobject]@{ Name = "lab automation blocks generic markdown protocol"; Prompt = "写一个普通 wet-lab protocol 的 Markdown 文档，不使用 protocols.io 或机器人"; Grade = "M"; TaskType = "planning"; BlockedPack = "science-lab-automation" },
    [pscustomobject]@{ Name = "rebuttal matrix"; Prompt = "回复审稿意见：生成rebuttal逐条回应矩阵，提供返修清单，并起草cover letter"; Grade = "L"; TaskType = "planning"; ExpectedPack = "scholarly-publishing-workflow"; ExpectedSkill = "submission-checklist" },
    [pscustomobject]@{ Name = "publishing workflow package"; Prompt = "规划一套期刊投稿工作流，包含投稿包、校样和 camera-ready"; Grade = "L"; TaskType = "planning"; ExpectedPack = "scholarly-publishing-workflow"; ExpectedSkill = "scholarly-publishing" },
    [pscustomobject]@{ Name = "submission checklist rebuttal matrix"; Prompt = "写 cover letter 和 response to reviewers rebuttal matrix"; Grade = "L"; TaskType = "planning"; ExpectedPack = "scholarly-publishing-workflow"; ExpectedSkill = "submission-checklist" },
    [pscustomobject]@{ Name = "manuscript as code reproducible build"; Prompt = "把论文仓库改成 manuscript-as-code，可复现构建 PDF"; Grade = "L"; TaskType = "planning"; ExpectedPack = "scholarly-publishing-workflow"; ExpectedSkill = "manuscript-as-code" },
    [pscustomobject]@{ Name = "latex submission zip build"; Prompt = "配置 latexmk/chktex/latexindent 编译论文 PDF 并打包 submission zip"; Grade = "XL"; TaskType = "coding"; ExpectedPack = "scholarly-publishing-workflow"; ExpectedSkill = "latex-submission-pipeline" },
    [pscustomobject]@{ Name = "venue template anonymous submission"; Prompt = "查 NeurIPS 模板和匿名投稿格式要求"; Grade = "L"; TaskType = "planning"; ExpectedPack = "scholarly-publishing-workflow"; ExpectedSkill = "venue-templates" },
    [pscustomobject]@{ Name = "latex academic poster"; Prompt = "用 beamerposter 做会议学术海报"; Grade = "L"; TaskType = "coding"; ExpectedPack = "scholarly-publishing-workflow"; ExpectedSkill = "latex-posters" },
    [pscustomobject]@{ Name = "paper2web video abstract"; Prompt = "把论文转换成 paper2web 项目主页和视频摘要"; Grade = "L"; TaskType = "planning"; ExpectedPack = "scholarly-publishing-workflow"; ExpectedSkill = "paper-2-web" },

    [pscustomobject]@{ Name = "grant proposal"; Prompt = "请帮我写NSFC科研基金申请书（基金申请书），需要结构化标书与评审点对齐"; Grade = "L"; TaskType = "planning"; ExpectedPack = "research-design"; ExpectedSkill = "research-grants" },
    [pscustomobject]@{ Name = "experiment failure analysis"; Prompt = "分析实验失败原因，判断是否继续优化还是放弃该方案"; Grade = "L"; TaskType = "review"; ExpectedPack = "research-design"; ExpectedSkill = "experiment-failure-analysis" },
    [pscustomobject]@{ Name = "hypogenic automated hypothesis"; Prompt = "用 HypoGeniC 从数据和文献中生成并测试科研假设"; Grade = "L"; TaskType = "research"; ExpectedPack = "research-design"; ExpectedSkill = "hypogenic" },
    [pscustomobject]@{ Name = "scientific hypothesis generation"; Prompt = "根据实验观察生成可检验的科研假设和预测"; Grade = "L"; TaskType = "planning"; ExpectedPack = "research-design"; ExpectedSkill = "hypothesis-generation" },
    [pscustomobject]@{ Name = "literature matrix research ideas"; Prompt = "构建论文组合矩阵，寻找 A+B 的研究创新点"; Grade = "L"; TaskType = "planning"; ExpectedPack = "research-design"; ExpectedSkill = "literature-matrix" },
    [pscustomobject]@{ Name = "causal analysis did synthetic control"; Prompt = "用 DID 和 synthetic control 做因果分析方案"; Grade = "L"; TaskType = "research"; ExpectedPack = "research-design"; ExpectedSkill = "performing-causal-analysis" },
    [pscustomobject]@{ Name = "regression coefficient confidence interval"; Prompt = "做回归分析并解释系数、置信区间和诊断结果"; Grade = "L"; TaskType = "research"; ExpectedPack = "research-design"; ExpectedSkill = "performing-regression-analysis" },
    [pscustomobject]@{ Name = "scientific brainstorming mechanisms"; Prompt = "围绕这个生物机制做科研头脑风暴，提出可能机制和实验方向"; Grade = "L"; TaskType = "planning"; ExpectedPack = "research-design"; ExpectedSkill = "scientific-brainstorming" },

    [pscustomobject]@{ Name = "top ppt deck"; Prompt = "顶级PPT制作：组会汇报slide deck，需要讲述结构与视觉规范"; Grade = "L"; TaskType = "planning"; ExpectedPack = "science-communication-slides"; ExpectedSkill = "scientific-slides" },
    [pscustomobject]@{ Name = "slidev slides as code"; Prompt = "用Slidev做组会汇报：slides as code，要求可复现导出PDF"; Grade = "L"; TaskType = "coding"; ExpectedPack = "science-communication-slides"; ExpectedSkill = "slides-as-code" },
    [pscustomobject]@{ Name = "pptx poster"; Prompt = "制作PowerPoint PPTX学术海报，需要可编辑PPT输出"; Grade = "L"; TaskType = "planning"; ExpectedPack = "science-communication-slides"; ExpectedSkill = "pptx-posters" },
    [pscustomobject]@{ Name = "plain conference poster"; Prompt = "制作学术海报 conference poster，准备会议展示"; Grade = "L"; TaskType = "planning"; ExpectedPack = "scholarly-publishing-workflow"; ExpectedSkill = "latex-posters" },
    [pscustomobject]@{ Name = "mermaid flowchart belongs to figures"; Prompt = "用Mermaid写一个实验流程图flowchart，并给出可复制markdown"; Grade = "M"; TaskType = "coding"; ExpectedPack = "science-figures-visualization"; ExpectedSkill = "scientific-schematics" },
    [pscustomobject]@{ Name = "web playwright automation"; Prompt = "用 Playwright 做 browser automation，登录表单并截图调试动态页面"; Grade = "M"; TaskType = "debug"; ExpectedPack = "web-scraping"; ExpectedSkill = "playwright" },
    [pscustomobject]@{ Name = "generic pubmed website not scraping"; Prompt = "检索 PubMed website 上的文献并整理 citation references"; Grade = "M"; TaskType = "research"; BlockedPack = "web-scraping" },

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
    $results += Assert-True -Condition ($route.selected.selection_reason -in @("keyword_ranked", "requested_skill", "fallback_first_candidate", "fallback_task_default", "fallback_task_default_after_task_filter", "fallback_first_candidate_after_task_filter", "host_selection_candidate")) -Message "[$($case.Name)] selection reason is valid"
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
