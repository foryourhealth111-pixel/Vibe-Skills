# Bio-Science Problem-First Consolidation

- Generated At: `2026-04-29T10:54:52.092637+00:00`
- Current Bio-Science Skills: 26
- Target Route Authorities: 26
- Stage assistants: 0
- Manual Review: 0
- Merge/Delete After Migration: 0

## Route Authorities

| skill_id | primary_problem_id | current_role | overlap_with | rationale |
| --- | --- | --- | --- | --- |
| alphafold-database | protein_structure_evidence | route_authority | pdb-database; esm | Structure evidence supports protein workflows but does not own the main task. |
| anndata | single_cell_data_container | route_authority | scanpy; scvi-tools; cellxgene-census | AnnData is a data structure layer used inside single-cell workflows. |
| biopython | sequence_io_entrez | route_authority | gget; pysam; database assistants | Biopython is broad and useful, but negative routing boundaries must stop it from swallowing single-cell, DESeq2, BAM/VCF, ESM, COBRApy, and flow cytometry prompts. |
| bioservices | cross_database_aggregation | route_authority | kegg-database; reactome-database; uniprot-like services | Cross-service lookup is valuable but must not override a more specific workflow owner. |
| cellxgene-census | single_cell_reference_evidence | route_authority | scanpy; anndata | Cellxgene Census supports single-cell reference lookup inside scanpy workflows. |
| clinvar-database | variant_clinical_evidence | route_authority | cosmic-database; gwas-database | ClinVar lookup is evidence retrieval inside a variant interpretation workflow. |
| cosmic-database | cancer_variant_evidence | route_authority | clinvar-database; gwas-database | COSMIC is supporting evidence for cancer variant work. |
| deeptools | genomics_track_processing | route_authority | pysam | deepTools is a genomics processing helper with a narrower route surface than pysam. |
| ensembl-database | ensembl_annotation_evidence | route_authority | gget; gene-database | Ensembl lookup should support gget and sequence workflows. |
| gene-database | gene_annotation_evidence | route_authority | ensembl-database; opentargets-database | Gene lookup supports annotation but should not own whole workflows. |
| gget | gene_symbol_lookup | route_authority | biopython; bioservices; ensembl-database; gene-database | Quick lookup is a separate user intent from full single-cell or differential-expression workflows. |
| gwas-database | gwas_trait_evidence | route_authority | clinvar-database; opentargets-database | GWAS evidence is supporting context for genetics workflows. |
| kegg-database | pathway_metabolism_evidence | route_authority | reactome-database; bioservices | KEGG is useful evidence for pathway and metabolism workflows. |
| opentargets-database | target_disease_evidence | route_authority | gene-database; gwas-database | OpenTargets supports target evidence, not the main computational workflow. |
| pdb-database | protein_structure_evidence | route_authority | alphafold-database; string-database | PDB lookup supports structural interpretation but is not the primary route for protein embeddings. |
| pydeseq2 | bulk_rnaseq_differential_expression | route_authority | scanpy; statistical-analysis | Bulk RNA-seq differential expression must not be absorbed by scanpy or biopython. |
| pysam | alignment_variant_files | route_authority | biopython; tiledbvcf | Alignment and variant files are concrete coding/research tasks with a dedicated Python owner. |
| reactome-database | pathway_evidence | route_authority | kegg-database; bioservices | Reactome supports pathway interpretation inside larger workflows. |
| scanpy | single_cell_rnaseq | route_authority | anndata; scvi-tools; cellxgene-census; pydeseq2 | Single-cell RNA-seq is a distinct high-value user problem and scanpy is the clearest owner. |
| scvi-tools | single_cell_latent_models | route_authority | scanpy; anndata | scVI is useful inside single-cell workflows but should not absorb broad single-cell prompts in the first split. |
| arboreto | gene_regulatory_networks | route_authority | scanpy; geniml | Gene regulatory network inference is distinct from ordinary single-cell clustering. |
| cobrapy | metabolic_flux_modeling | route_authority | kegg-database; reactome-database; bioservices | Metabolic flux modeling is a problem owner, not a generic pathway lookup. |
| esm | protein_language_models | route_authority | alphafold-database; pdb-database; string-database | Protein embedding tasks are bio-ML tasks and should not be routed to generic sequence handling. |
| flowio | flow_cytometry_fcs_io | route_authority | anndata | FCS/flow cytometry file IO is a specific task that should not fall back to biopython. |
| geniml | genomic_ml_embeddings | route_authority | esm; data-ml | Genome embeddings are a bio-specific ML surface and need a precise owner. |
| string-database | protein_interaction_evidence | route_authority | pdb-database; alphafold-database | STRING lookup is supporting evidence for protein workflows. |

## Manual Review

- none

## Merge/Delete After Migration

- none
