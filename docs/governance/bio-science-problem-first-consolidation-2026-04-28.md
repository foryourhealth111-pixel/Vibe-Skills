# Bio-Science Problem-First Consolidation

Date: 2026-04-28
Updated: 2026-04-29

## Summary

`bio-science` is consolidated as a direct-owner routing pack for bioinformatics,
genomics, single-cell analysis, sequence handling, variant evidence, protein
structure, pathway analysis, systems biology, and bio-specific ML tasks.

The six-stage Vibe runtime is unchanged, and skill use remains binary:

```text
skill_candidates -> skill_routing.selected -> skill_usage.used / unused
```

No advisory, consult, primary/secondary, or stage-assistant execution model is
introduced.

## Counts

| Field | Before first cleanup | After first cleanup | Current |
| --- | ---: | ---: | ---: |
| `skill_candidates` | 26 | 26 | 26 |
| `route_authority_candidates` | 0 | 10 | 26 |
| `stage_assistant_candidates` | 0 | 16 | 0 |
| physical directory deletion | 0 | 0 | 0 |

The 2026-04-29 update removes the old stage-assistant split. Every retained
candidate is now either a direct route owner or not selected. No physical skill
directory is deleted in this pass.

## Direct Route Owners

| User problem | Skill |
| --- | --- |
| AlphaFold predicted protein structures, UniProt lookup, mmCIF/PDB downloads, pLDDT/PAE | `alphafold-database` |
| AnnData/h5ad containers, obs/var metadata, backed mode, sparse annotated matrices | `anndata` |
| FASTA/GenBank/SeqIO, NCBI Entrez, sequence conversion and sequence parsing | `biopython` |
| BioServices cross-database workflows, UniProt/QuickGO/BioMart-style service access, ID mapping | `bioservices` |
| CZ CELLxGENE Census queries, cell/tissue/disease filters, expression data and metadata | `cellxgene-census` |
| ClinVar clinical significance, pathogenicity, VUS, review status, variant annotation evidence | `clinvar-database` |
| COSMIC cancer mutations, Cancer Gene Census, mutational signatures, somatic variants | `cosmic-database` |
| deepTools BAM-to-bigWig, NGS signal tracks, QC, heatmaps and profile plots | `deeptools` |
| Ensembl REST, VEP, orthologs, comparative genomics, coordinate conversion | `ensembl-database` |
| NCBI Gene search, gene symbols, RefSeqs, GO annotations, gene metadata | `gene-database` |
| Quick gene, transcript, BLAST, Ensembl ID, or symbol lookup | `gget` |
| GWAS Catalog SNP-trait associations, rs IDs, p-values, summary statistics | `gwas-database` |
| KEGG REST, pathway mapping, ID conversion, metabolic pathway lookup | `kegg-database` |
| Open Targets target-disease associations, tractability, safety, known drugs | `opentargets-database` |
| RCSB PDB structure search, sequence similarity, metadata, coordinate downloads | `pdb-database` |
| Bulk RNA-seq differential expression, DESeq2-style statistics, volcano/MA plots | `pydeseq2` |
| BAM/SAM/CRAM/VCF parsing, pileup, coverage, variant-file handling | `pysam` |
| Reactome pathway enrichment, gene-pathway mapping, reactions, disease pathways | `reactome-database` |
| Single-cell RNA-seq clustering, annotation, marker genes, UMAP/t-SNE, 10X workflow | `scanpy` |
| scVI/scANVI, single-cell batch correction, latent models, transfer learning | `scvi-tools` |
| Gene regulatory network inference, pySCENIC, transcription-factor networks | `arboreto` |
| Metabolic network modeling, FBA, constraint-based metabolic models | `cobrapy` |
| Protein language models and protein embeddings | `esm` |
| FCS / flow cytometry file reading and channel matrix handling | `flowio` |
| Genomic ML and genome embedding tasks | `geniml` |
| STRING protein-protein interaction networks, enrichment, interaction partners | `string-database` |

## Removed Stage-Assistant Semantics

The previous helper list is intentionally retired:

```text
anndata, scvi-tools, deeptools, bioservices, alphafold-database,
clinvar-database, cosmic-database, ensembl-database, gene-database,
gwas-database, kegg-database, opentargets-database, pdb-database,
reactome-database, string-database, cellxgene-census
```

These skills are not deleted. They are direct route owners when the prompt names
their specific user problem. They are not silently injected as auxiliary experts.

## Protected Boundaries

| Prompt class | Expected route |
| --- | --- |
| AnnData/h5ad container and metadata handling | `bio-science / anndata` |
| scVI/scANVI batch correction or latent modeling | `bio-science / scvi-tools` |
| deepTools BAM-to-bigWig, heatmap/profile plotting | `bio-science / deeptools` |
| ClinVar clinical significance or VUS lookup | `bio-science / clinvar-database` |
| KEGG REST pathway mapping or ID conversion | `bio-science / kegg-database` |
| Reactome pathway enrichment | `bio-science / reactome-database` |
| AlphaFold predicted structure confidence | `bio-science / alphafold-database` |
| RCSB PDB structure search and coordinate download | `bio-science / pdb-database` |
| STRING PPI network and enrichment | `bio-science / string-database` |
| CELLxGENE Census expression/metadata query | `bio-science / cellxgene-census` |
| RDKit / SMILES / Morgan fingerprint | `science-chem-drug / rdkit` |
| ClinicalTrials.gov / FDA / CPIC | `science-clinical-regulatory` |
| PubMed / BibTeX / citation export | `science-literature-citations` |
| DICOM / medical image tags | `science-medical-imaging / pydicom` |

## Deletion Boundary

No bundled skill directory is physically deleted. A later deletion pass must
prove all of the following before removing any directory:

1. The skill has no distinct user problem after direct-owner review.
2. Useful references, scripts, examples, and assets have been migrated or
   intentionally rejected.
3. No live route, profile, test, lockfile, or packaging surface depends on the
   directory.
4. Offline skills, config parity, and route regression gates pass after removal.

## Verification

Required checks:

```powershell
python -m pytest tests/runtime_neutral/test_bio_science_pack_consolidation_audit.py -q
python -m pytest tests/runtime_neutral/test_bio_science_direct_owner_routing.py -q
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-bio-science-pack-consolidation-audit-gate.ps1 -WriteArtifacts -OutputDirectory outputs\skills-audit
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-skill-index-routing-audit.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\verify\probe-scientific-packs.ps1 -Unattended
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-pack-regression-matrix.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-pack-routing-smoke.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-generate-skills-lock.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-offline-skills-gate.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-config-parity-gate.ps1 -WriteArtifacts
git diff --check
```
