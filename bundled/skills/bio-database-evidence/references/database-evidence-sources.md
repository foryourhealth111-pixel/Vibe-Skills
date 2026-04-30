# Biological Database Evidence Sources

## Gene And Transcript Annotation

- Ensembl: gene, transcript, ortholog, coordinate, and VEP-style variant consequence lookup.
- NCBI Gene: gene symbol, RefSeq, GO, genomic location, phenotype, and batch gene metadata.
- gget-style quick lookup: fast gene symbol, Ensembl ID, transcript, BLAST-style lookup, and small evidence checks.
- BioServices-style cross-database mapping: ID mapping across UniProt, KEGG, Reactome, and other biological resources.

## Variant, Cancer, And Trait Evidence

- ClinVar: clinical significance, VUS, review status, condition names, and variant annotation evidence.
- COSMIC: cancer mutation, Cancer Gene Census, mutational signatures, gene fusion, and somatic evidence. Authentication may be required.
- GWAS Catalog: SNP-trait associations, rs IDs, p-values, summary statistics, disease/trait metadata, and genetic epidemiology evidence.

## Pathway, Target, And Systems Evidence

- KEGG: pathway mapping, ID conversion, metabolic pathway lookup, organism-specific gene-pathway mapping, and drug/pathway evidence. Respect academic-use restrictions.
- Reactome: pathway enrichment, gene-pathway mapping, reactions, disease pathways, and expression/pathway evidence.
- Open Targets: target-disease associations, tractability, safety, genetics evidence, omics evidence, known drugs, and therapeutic target support.
- STRING: protein-protein interaction networks, interaction partners, GO/KEGG enrichment, hub proteins, and network evidence.

## Protein Structure Evidence

- AlphaFold DB: predicted structures by UniProt ID, mmCIF/PDB downloads, pLDDT, PAE, and predicted model confidence.
- RCSB PDB: experimental structure search, sequence similarity search, structure metadata, ligand context, and coordinate downloads.

## Reference Single-Cell Evidence

- CELLxGENE Census: reference cell and tissue queries, disease metadata, expression retrieval, population-scale cell metadata, and source dataset evidence.
- Use `scanpy` after the task becomes downstream analysis such as QC, normalization, clustering, marker genes, or cell annotation.

## Evidence Output Pattern

For multi-source tasks, return a table with these columns:

```text
source
query
identifier
evidence_type
key_result
access_or_license_note
confidence_or_review_status
```
