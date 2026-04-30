# Bio-Science Boundary Hardening - 2026-04-30

## Scope

This pass hardens the `bio-science` routing boundary. It does not change the public six-stage Vibe runtime and does not introduce helper experts, advisory routing, consultation routing, primary/secondary skill states, or stage assistants.

The live skill-use model remains:

```text
candidate skill -> selected skill -> used / unused
```

## Counts

| Metric | Before | After |
| --- | ---: | ---: |
| `skill_candidates` | 26 | 26 |
| `route_authority_candidates` | 26 | 26 |
| `stage_assistant_candidates` | 0 | 0 |
| physically deleted skill directories | 0 | 0 |

## Retained Direct Owners

All current `bio-science` candidates remain direct route owners:

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

## Boundary Decisions

| Problem family | Direct owners |
| --- | --- |
| Sequence and general bio Python | `biopython` |
| Single-cell analysis and containers | `scanpy`, `anndata`, `scvi-tools`, `cellxgene-census` |
| Bulk RNA-seq and NGS files | `pydeseq2`, `pysam`, `deeptools` |
| Gene, variant, and target evidence | `clinvar-database`, `cosmic-database`, `ensembl-database`, `gene-database`, `gget`, `gwas-database`, `opentargets-database` |
| Pathway, interaction, and systems biology | `kegg-database`, `reactome-database`, `string-database`, `cobrapy`, `arboreto` |
| Protein structure and protein ML | `alphafold-database`, `pdb-database`, `esm` |
| Specialized bio data and genomic ML | `flowio`, `geniml`, `bioservices` |

## Changes

- Added Chinese `不是`-family negation handling so negated biomedical terms do not count as positive routing evidence.
- Added narrow `geniml` triggers for BED/genomic interval embeddings and regulatory region similarity.
- Added `geniml` negatives for ordinary tabular ML, scikit-learn/random forest prompts, and explicit non-genomic ML prompts.
- Added cross-pack negatives so generic similarity search and RDKit do not capture BED/genomic interval embedding tasks.
- Added Scanpy single-cell RNA-seq analysis triggers so explicit scRNA-seq clustering remains with `scanpy` even when flow cytometry/FCS terms are negated.

## Protected Probes

Positive bio-science ownership:

- `biopython`: FASTA/GenBank/SeqIO/Entrez conversion.
- `scanpy`: single-cell RNA-seq QC, clustering, UMAP, and marker genes.
- `anndata`: h5ad container metadata and backed mode.
- `scvi-tools`: scVI/scANVI latent modeling and batch correction.
- `cellxgene-census`: CELLxGENE Census cell/tissue/disease queries.
- `pydeseq2`: bulk RNA-seq differential expression.
- `pysam`: BAM/CRAM/VCF pileup and coverage.
- `deeptools`: BAM-to-bigWig, computeMatrix, and plotHeatmap.
- `bioservices`: explicit BioServices multi-service aggregation.
- `gget`: explicit gget quick lookup.
- `geniml`: BED/genomic interval embeddings and regulatory region similarity.
- `flowio`: real FCS flow cytometry parsing.

False-positive boundaries:

- `geniml` must not own ordinary clinical-table random forest prompts that say the task is not genomic ML.
- `flowio` must not own single-cell RNA-seq prompts that only mention flow cytometry/FCS under `不是` negation.
- `scanpy` must lose to AnnData, scVI, and CELLxGENE when those explicit owner signals appear.
- `biopython` must lose to pysam, ESM, and COBRApy when those explicit owner signals appear.
- `bioservices` must lose to KEGG and Reactome when the prompt names those deeper database workflows.
- `gget` must lose to Open Targets when the prompt names target-disease evidence.
- RDKit, PubMed/citations, ClinicalTrials.gov, DICOM, generic scikit-learn, scientific visualization, and LaTeX PDF build remain in their neighboring packs.

## Remaining Caveats

- This pass does not shrink the 26-skill candidate count.
- This pass does not claim that a selected skill was materially used in a real task. Material use still requires task artifacts or execution evidence.
- Physical deletion remains deferred because every retained directory already had a distinct route owner role or asset-bearing content.
