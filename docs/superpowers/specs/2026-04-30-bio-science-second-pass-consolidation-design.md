# Bio-Science Second-Pass Consolidation Design

Date: 2026-04-30

## Goal

Shrink `bio-science` from a 26-owner database/tool list into a smaller task-owner pack.

This pass keeps the public six-stage Vibe runtime unchanged and keeps the simplified skill-use contract:

```text
candidate skill -> selected skill -> used / unused
```

It must not reintroduce helper experts, advisory routing, consultation routing, primary/secondary skill states, or stage assistants.

The target is to reduce `bio-science` from 26 direct route owners to about 13 direct owners:

- 12 biological workflow or data-analysis owners.
- 1 unified biological database/evidence owner.

## Current Evidence

The current `bio-science` pack has:

| Field | Current value |
| --- | ---: |
| `skill_candidates` | 26 |
| `route_authority_candidates` | 26 |
| `stage_assistant_candidates` | 0 |

All current candidates are also direct route authorities:

```text
alphafold-database
anndata
biopython
bioservices
cellxgene-census
clinvar-database
cosmic-database
deeptools
ensembl-database
gene-database
gget
gwas-database
kegg-database
opentargets-database
pdb-database
pydeseq2
pysam
reactome-database
scanpy
scvi-tools
arboreto
cobrapy
esm
flowio
geniml
string-database
```

The latest global pack audit still ranks `bio-science` as the top structural risk:

| Signal | Value |
| --- | ---: |
| skill candidates | 26 |
| route authorities | 26 |
| broad keyword count | 3 |
| tool-primary risk count | 15 |
| asset-heavy candidates | 26 |

The earlier 2026-04-30 boundary-hardening pass fixed false positives but intentionally did not shrink the pack. This second pass addresses the remaining structural issue.

## Problem

`bio-science` currently mixes two different kinds of skill:

1. Workflow owners that can solve a direct biological task.
2. Thin database/API wrappers that are useful evidence sources but should not each occupy a top-level route owner slot.

The database/API wrappers are useful, but keeping each one as a separate route authority makes the pack noisy:

- Similar evidence queries split across `gene-database`, `ensembl-database`, `gget`, and `bioservices`.
- Pathway evidence splits across `kegg-database`, `reactome-database`, and `bioservices`.
- Protein structure and interaction evidence splits across `alphafold-database`, `pdb-database`, and `string-database`.
- Variant and target evidence splits across `clinvar-database`, `cosmic-database`, `gwas-database`, and `opentargets-database`.
- `cellxgene-census` is a single-cell evidence/data-source surface, not usually a whole task route by itself.

The user-facing routing question should be simpler:

```text
What biological task is the user asking to do?
```

not:

```text
Which one of many database wrappers happened to match a keyword?
```

## Design Choice

Use a direct consolidation pass.

Recommended approach:

1. Keep task-level biological workflow skills as direct owners.
2. Create a single `bio-database-evidence` owner for biological database lookup, annotation, pathway, variant, target, structure, interaction, and reference-data evidence.
3. Migrate useful database-wrapper references/scripts into `bio-database-evidence`.
4. Physically delete the merged low-level database/API wrapper directories after migration review.
5. Keep `stage_assistant_candidates` empty.
6. Add regression tests that prove the new owner still routes concrete database/evidence prompts correctly.

Rejected alternatives:

| Alternative | Why rejected |
| --- | --- |
| Keep 26 owners and add more negatives | This preserves the noisy tool-list architecture. |
| Convert database wrappers to stage assistants | The user explicitly wants only use/unused, not helper or assistant roles. |
| Use `bioservices` as the unified owner | It is less readable than `bio-database-evidence` and sounds like one Python package rather than a problem owner. |
| Delete all narrow workflow skills too | Too aggressive. `anndata`, `scvi-tools`, `deeptools`, `arboreto`, and `flowio` each still map to concrete biological tasks. |

## Target Direct Owners

The target direct route owners are:

| Target owner | User problem owned |
| --- | --- |
| `biopython` | FASTA/FASTQ/GenBank/SeqIO/Entrez, sequence parsing, sequence conversion, BLAST workflows that need Python control. |
| `scanpy` | Single-cell RNA-seq analysis, QC, normalization, clustering, UMAP, marker genes, cell annotation, 10X/h5ad workflows. |
| `anndata` | AnnData and h5ad container work, obs/var/layers/raw metadata, backed mode, annotated matrix storage. |
| `scvi-tools` | scVI/scANVI, single-cell latent models, batch correction, probabilistic single-cell modeling, multimodal single-cell modeling. |
| `pydeseq2` | Bulk RNA-seq differential expression, DESeq2-style statistics, FDR, Wald tests, MA/volcano plots. |
| `pysam` | BAM/SAM/CRAM/VCF parsing, pileup, coverage, region extraction, alignment and variant-file processing. |
| `deeptools` | BAM to bigWig, computeMatrix, plotHeatmap, ChIP-seq/ATAC-seq/RNA-seq signal tracks and profile plots. |
| `esm` | Protein language models, protein embeddings, inverse folding, protein design, protein representation workflows. |
| `cobrapy` | Constraint-based metabolic modeling, FBA, FVA, gene knockouts, SBML metabolic models. |
| `geniml` | BED/genomic interval embeddings, Region2Vec, BEDspace, regulatory region similarity, genomic-region ML. |
| `arboreto` | Gene regulatory network inference, GRNBoost2, GENIE3, transcription-factor target networks. |
| `flowio` | FCS and flow cytometry file parsing, channel metadata, event matrices, FCS-to-table conversion. |
| `bio-database-evidence` | Biological database evidence and annotation across genes, variants, traits, pathways, targets, protein structures, protein interactions, reference single-cell data, and quick biological lookup. |

## Merge And Delete Candidates

The following skills should be merged into `bio-database-evidence` and then physically deleted after useful content is migrated:

| Skill | Merge target | Reason |
| --- | --- | --- |
| `alphafold-database` | `bio-database-evidence` | Predicted structure evidence belongs in the unified evidence owner. |
| `bioservices` | `bio-database-evidence` | Cross-service API access is an implementation method, not a separate user problem. |
| `cellxgene-census` | `bio-database-evidence` | Census lookup is reference-data evidence for single-cell workflows. |
| `clinvar-database` | `bio-database-evidence` | Variant clinical significance is evidence lookup. |
| `cosmic-database` | `bio-database-evidence` | Cancer mutation evidence is evidence lookup. |
| `ensembl-database` | `bio-database-evidence` | Ensembl annotation and VEP are evidence lookup. |
| `gene-database` | `bio-database-evidence` | NCBI Gene lookup is evidence lookup. |
| `gget` | `bio-database-evidence` | Quick biological lookup is better represented as an evidence mode than a separate owner. |
| `gwas-database` | `bio-database-evidence` | GWAS Catalog trait evidence is evidence lookup. |
| `kegg-database` | `bio-database-evidence` | KEGG pathway and ID mapping are evidence lookup. |
| `opentargets-database` | `bio-database-evidence` | Target-disease evidence belongs in the unified evidence owner. |
| `pdb-database` | `bio-database-evidence` | PDB structure evidence belongs in the unified evidence owner. |
| `reactome-database` | `bio-database-evidence` | Reactome pathway evidence belongs in the unified evidence owner. |
| `string-database` | `bio-database-evidence` | PPI network evidence belongs in the unified evidence owner. |

Deletion is allowed only after each directory is reviewed for useful references, scripts, examples, or assets. Useful material should be migrated into `bio-database-evidence/references/` or `bio-database-evidence/scripts/`.

## Target Manifest Shape

Target `skill_candidates`:

```text
biopython
scanpy
anndata
scvi-tools
pydeseq2
pysam
deeptools
esm
cobrapy
geniml
arboreto
flowio
bio-database-evidence
```

Target `route_authority_candidates` should mirror `skill_candidates` for compatibility with existing gates:

```text
biopython
scanpy
anndata
scvi-tools
pydeseq2
pysam
deeptools
esm
cobrapy
geniml
arboreto
flowio
bio-database-evidence
```

Target `stage_assistant_candidates`:

```text
[]
```

Target defaults:

```json
{
  "planning": "biopython",
  "coding": "biopython",
  "research": "scanpy"
}
```

The defaults can remain unchanged because they are broad fallback defaults, not evidence that those skills were used in execution.

## Routing Rules

### Workflow owners

Workflow owners should keep concrete, task-specific positive triggers:

| Owner | Positive route signals |
| --- | --- |
| `biopython` | `SeqIO`, `FASTA`, `FASTQ`, `GenBank`, `Entrez`, `BLAST`, `sequence conversion`, `sequence parsing`, `序列格式转换` |
| `scanpy` | `single-cell`, `scRNA-seq`, `h5ad`, `10X`, `Leiden`, `marker genes`, `cell annotation`, `单细胞`, `细胞注释` |
| `anndata` | `AnnData`, `h5ad`, `obs`, `var`, `layers`, `backed mode`, `annotated matrix` |
| `scvi-tools` | `scVI`, `scANVI`, `latent model`, `batch correction`, `single-cell probabilistic model` |
| `pydeseq2` | `DESeq2`, `PyDESeq2`, `bulk RNA-seq`, `differential expression`, `Wald test`, `padj`, `volcano plot` |
| `pysam` | `BAM`, `SAM`, `CRAM`, `VCF`, `pileup`, `coverage`, `region extraction`, `覆盖度` |
| `deeptools` | `deepTools`, `bamCoverage`, `bigWig`, `computeMatrix`, `plotHeatmap`, `TSS profile` |
| `esm` | `ESM`, `protein language model`, `protein embedding`, `inverse folding`, `protein design`, `蛋白嵌入` |
| `cobrapy` | `COBRApy`, `FBA`, `flux balance`, `FVA`, `SBML`, `metabolic model`, `通量平衡` |
| `geniml` | `BED`, `genomic interval`, `Region2Vec`, `BEDspace`, `regulatory region`, `genomic ML`, `基因组区间` |
| `arboreto` | `arboreto`, `GRNBoost2`, `GENIE3`, `gene regulatory network`, `pySCENIC`, `转录因子网络` |
| `flowio` | `FCS`, `flow cytometry`, `channel matrix`, `compensation`, `流式细胞` |

### Unified evidence owner

`bio-database-evidence` should own prompts that explicitly ask for biological evidence lookup, annotation, or database access across:

```text
AlphaFold
BioServices
CELLxGENE Census
ClinVar
COSMIC
Ensembl
NCBI Gene
gget-style quick lookup
GWAS Catalog
KEGG
Open Targets
PDB
Reactome
STRING
```

Expected positive signals include:

```text
biological database evidence
gene annotation
variant clinical significance
target-disease association
pathway mapping
protein structure lookup
protein interaction network
GWAS trait association
reference single-cell census
cross-database ID mapping
生物数据库证据
基因注释
变异临床意义
靶点疾病证据
通路映射
蛋白结构查询
蛋白互作网络
```

### Negative boundaries

The unified evidence owner must not steal concrete workflow prompts:

- `scanpy` wins single-cell analysis prompts even if gene annotation or CELLxGENE appears as later context.
- `pydeseq2` wins bulk differential-expression prompts even if pathway enrichment is a follow-up step.
- `pysam` wins BAM/VCF processing prompts even if ClinVar annotation is mentioned later.
- `esm` wins protein embedding/design prompts even if AlphaFold/PDB lookup is mentioned later.
- `cobrapy` wins FBA/metabolic modeling prompts even if KEGG/Reactome is mentioned later.
- `geniml` wins BED/genomic interval ML prompts even if Ensembl annotation is mentioned later.

Cross-pack protections must remain:

| Prompt class | Expected owner |
| --- | --- |
| Generic UMAP/dimensionality reduction | `data-ml / scikit-learn` |
| RDKit, SMILES, molecular fingerprints | `science-chem-drug / rdkit` |
| PubMed search, BibTeX, citations | `science-literature-citations` |
| DICOM or pydicom work | `science-medical-imaging / pydicom` |
| LaTeX manuscript build or submission ZIP | `scholarly-publishing-workflow / latex-submission-pipeline` |
| Scientific figures/results plots | `science-figures-visualization / scientific-visualization` |

## Asset Migration

Before deleting any merged directory, inspect:

```text
SKILL.md
references/
scripts/
examples/
assets/
agents/
```

Migration rules:

- Keep concise database access notes, API caveats, authentication notes, rate-limit notes, and example query snippets.
- Drop duplicated README-like prose when the unified owner already covers the task.
- Drop obsolete helper wrappers that only restate package documentation and have no route-specific value.
- Preserve scripts only if they perform a concrete reusable query or conversion.
- Do not migrate icons or decorative assets unless the unified owner needs them.

## Regression Tests

Add focused tests for the new target shape:

### Manifest and deletion tests

- `bio-science.skill_candidates` has exactly 13 entries.
- `bio-science.route_authority_candidates` mirrors the same 13 entries.
- `bio-science.stage_assistant_candidates` is empty.
- Merged directories no longer exist under `bundled/skills/`.
- `skills-lock.json` no longer lists deleted skills.
- `skill-keyword-index.json` and `skill-routing-rules.json` no longer expose deleted skill IDs.

### Positive routing tests

| Prompt | Expected route |
| --- | --- |
| `用 Biopython SeqIO 转换 FASTA 和 GenBank` | `bio-science / biopython` |
| `做 single-cell RNA-seq 聚类、UMAP 和 marker genes` | `bio-science / scanpy` |
| `编辑 AnnData h5ad 的 obs var layers backed mode` | `bio-science / anndata` |
| `用 scVI 做 batch correction 和 latent model` | `bio-science / scvi-tools` |
| `bulk RNA-seq count matrix 做 DESeq2 差异表达` | `bio-science / pydeseq2` |
| `读取 BAM VCF 做 pileup 和 coverage` | `bio-science / pysam` |
| `deepTools bamCoverage computeMatrix plotHeatmap` | `bio-science / deeptools` |
| `用 ESM 做 protein embedding 和 inverse folding` | `bio-science / esm` |
| `用 COBRApy 做 FBA flux balance analysis` | `bio-science / cobrapy` |
| `对 BED genomic intervals 做 Region2Vec embedding` | `bio-science / geniml` |
| `用 GRNBoost2 推断 gene regulatory network` | `bio-science / arboreto` |
| `解析 FCS flow cytometry channel matrix` | `bio-science / flowio` |
| `查询 ClinVar COSMIC Ensembl GWAS KEGG Reactome Open Targets PDB STRING 的生物数据库证据` | `bio-science / bio-database-evidence` |

### Boundary tests

| Prompt | Expected boundary |
| --- | --- |
| `用 scikit-learn 对普通表格数据做 UMAP 降维` | `data-ml / scikit-learn` |
| `用 RDKit 处理 SMILES 和 Morgan fingerprint` | `science-chem-drug / rdkit` |
| `检索 PubMed 并导出 BibTeX` | `science-literature-citations` |
| `用 pydicom 读取 DICOM metadata` | `science-medical-imaging / pydicom` |
| `用 LaTeX 构建论文 PDF 和 submission zip` | `scholarly-publishing-workflow / latex-submission-pipeline` |
| `绘制论文结果图和统计图` | `science-figures-visualization / scientific-visualization` |

## Verification

Focused verification:

```powershell
python -m pytest tests/runtime_neutral/test_bio_science_second_pass_consolidation.py tests/runtime_neutral/test_bio_science_boundary_hardening.py -q
```

Routing verification:

```powershell
.\scripts\verify\vibe-skill-index-routing-audit.ps1
.\scripts\verify\vibe-pack-routing-smoke.ps1
.\scripts\verify\vibe-bio-science-pack-consolidation-audit-gate.ps1
.\scripts\verify\vibe-global-pack-consolidation-audit-gate.ps1
```

Packaging verification:

```powershell
.\scripts\verify\vibe-generate-skills-lock.ps1
.\scripts\verify\vibe-offline-skills-gate.ps1
git diff --check
```

The implementation may need to update the bio-science audit gate because its current expected target still accepts all 26 candidates.

## Acceptance Criteria

This pass is complete only when all of the following are true:

- `bio-science` has about 13 skill candidates, not 26.
- `route_authority_candidates` mirrors the simplified direct-owner list.
- `stage_assistant_candidates` remains empty.
- The database/API wrapper skills listed in the merge table are physically deleted after migration review.
- `bio-database-evidence` contains the useful migrated evidence/database material.
- Deleted skill IDs are removed from manifest, keyword index, routing rules, and skills lock.
- Existing positive workflow routes still work.
- Cross-pack false-positive boundaries still work.
- The governance note separates routing/config cleanup, physical deletion, and real runtime skill use.

## Non-Goals

This pass will not:

- Rewrite the six-stage Vibe runtime.
- Add helper experts, advisory mode, primary/secondary skills, consultation routing, or stage assistants.
- Claim that a selected skill was materially used in a task. Material use still requires task artifacts.
- Clean all remaining science packs.
- Merge `bio-science` with `science-chem-drug`, `science-medical-imaging`, `science-literature-citations`, or `scholarly-publishing-workflow`.

