---
name: bio-database-evidence
description: "Unified biological database evidence owner. Use for gene annotation, variant clinical significance, cancer mutation evidence, GWAS trait associations, pathway mapping, target-disease evidence, protein structures, protein interaction networks, reference single-cell census queries, and cross-database biological ID mapping. Do not use for full single-cell analysis, bulk RNA-seq differential expression, BAM/VCF processing, protein embedding models, metabolic flux modeling, or genomic interval ML."
---

# Bio Database Evidence

## Use This Skill For

Use this skill when the main task is biological database lookup, annotation, or evidence gathering across one or more biological sources:

- Gene annotation, identifiers, RefSeq, Ensembl IDs, orthologs, VEP, GO, and genomic coordinates.
- Variant clinical significance, VUS interpretation support, ClinVar review status, cancer mutations, and COSMIC evidence.
- GWAS Catalog trait associations, rs IDs, p-values, summary statistics, and genetic epidemiology evidence.
- Pathway mapping, ID conversion, KEGG pathways, Reactome enrichment, disease pathways, and pathway evidence.
- Target-disease association evidence, tractability, safety, known drugs, and Open Targets evidence.
- Protein structure evidence from AlphaFold DB or RCSB PDB, including UniProt IDs, mmCIF/PDB downloads, pLDDT, PAE, and structure metadata.
- Protein-protein interaction evidence, STRING networks, hub proteins, and enrichment evidence.
- Reference single-cell data lookup from CELLxGENE Census when the user asks for census metadata or expression data, not full downstream analysis.
- Cross-database biological ID mapping and evidence tables across multiple resources.

## Do Not Use This Skill For

- Single-cell RNA-seq analysis, clustering, UMAP, marker genes, or cell annotation. Use `scanpy`.
- AnnData or h5ad container editing. Use `anndata`.
- scVI/scANVI latent models and batch correction. Use `scvi-tools`.
- Bulk RNA-seq differential expression. Use `pydeseq2`.
- BAM, SAM, CRAM, VCF, pileup, coverage, or region extraction. Use `pysam`.
- deepTools signal-track processing and heatmaps. Use `deeptools`.
- Protein language models, embeddings, inverse folding, or design. Use `esm`.
- Constraint-based metabolic modeling or FBA. Use `cobrapy`.
- BED/genomic interval embeddings or genomic-region ML. Use `geniml`.
- Gene regulatory network inference. Use `arboreto`.
- FCS or flow cytometry file parsing. Use `flowio`.

## Workflow

1. Identify the biological entity type: gene, transcript, variant, pathway, target, protein structure, protein interaction, trait association, or reference cell population.
2. Pick the narrowest source that answers the evidence question.
3. Preserve source names, query terms, access dates, identifiers, and API caveats in the result.
4. Return evidence in a table when comparing multiple sources.
5. State when authentication, license, rate limits, or non-public access restricts a source.

## Source Guide

See `references/database-evidence-sources.md` for source-specific boundaries and query notes.
