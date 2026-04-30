# Bio-Science Second-Pass Consolidation - 2026-04-30

## Scope

This pass shrinks `bio-science` from a broad database/tool list into a smaller direct-owner pack. It does not change the six-stage Vibe runtime and does not introduce helper experts, advisory routing, consultation routing, primary/secondary skill states, or stage assistants.

The live skill-use model remains:

```text
candidate skill -> selected skill -> used / unused
```

## Counts

| Metric | Before | After |
| --- | ---: | ---: |
| `skill_candidates` | 26 | 13 |
| `route_authority_candidates` | 26 | 13 |
| `stage_assistant_candidates` | 0 | 0 |
| physically deleted skill directories | 0 | 14 |

## Retained Direct Owners

| Skill | Problem owner |
| --- | --- |
| `biopython` | Sequence files, SeqIO, Entrez, FASTA/GenBank conversion. |
| `scanpy` | Single-cell RNA-seq analysis. |
| `anndata` | AnnData/h5ad container work. |
| `scvi-tools` | Single-cell latent models and batch correction. |
| `pydeseq2` | Bulk RNA-seq differential expression. |
| `pysam` | BAM/VCF alignment and variant-file processing. |
| `deeptools` | Genomics signal tracks and heatmap/profile workflows. |
| `esm` | Protein language models and embeddings. |
| `cobrapy` | Metabolic flux modeling and FBA. |
| `geniml` | Genomic interval embeddings and genomic-region ML. |
| `arboreto` | Gene regulatory network inference. |
| `flowio` | FCS and flow cytometry file parsing. |
| `bio-database-evidence` | Biological database evidence, annotation, pathway, variant, target, structure, interaction, reference census, and cross-database lookup. |

## Merged And Deleted

| Deleted skill | New owner |
| --- | --- |
| `alphafold-database` | `bio-database-evidence` |
| `bioservices` | `bio-database-evidence` |
| `cellxgene-census` | `bio-database-evidence` |
| `clinvar-database` | `bio-database-evidence` |
| `cosmic-database` | `bio-database-evidence` |
| `ensembl-database` | `bio-database-evidence` |
| `gene-database` | `bio-database-evidence` |
| `gget` | `bio-database-evidence` |
| `gwas-database` | `bio-database-evidence` |
| `kegg-database` | `bio-database-evidence` |
| `opentargets-database` | `bio-database-evidence` |
| `pdb-database` | `bio-database-evidence` |
| `reactome-database` | `bio-database-evidence` |
| `string-database` | `bio-database-evidence` |

## Verification

Final closeout checks:

```text
python -m pytest tests/runtime_neutral/test_bio_science_second_pass_consolidation.py tests/runtime_neutral/test_bio_science_boundary_hardening.py tests/runtime_neutral/test_bio_science_direct_owner_routing.py tests/runtime_neutral/test_bio_science_pack_consolidation_audit.py -q
57 passed

python -m pytest tests/runtime_neutral/test_bio_science_pack_consolidation_audit.py -q
7 passed

python -m pytest tests/runtime_neutral/test_bio_science_second_pass_consolidation.py::BioScienceSecondPassConsolidationTests::test_merged_database_skills_are_removed_from_live_surfaces -q
1 passed

.\scripts\verify\vibe-skill-index-routing-audit.ps1
Total assertions: 436
Passed: 436
Failed: 0
Skill-index routing audit passed.

.\scripts\verify\vibe-pack-regression-matrix.ps1
Total assertions: 317
Passed: 317
Failed: 0
Pack regression matrix checks passed.

.\scripts\verify\vibe-pack-routing-smoke.ps1
Total assertions: 958
Passed: 958
Failed: 0
Pack routing smoke checks passed.

.\scripts\verify\vibe-bio-science-pack-consolidation-audit-gate.ps1
summary.target_route_authority_count = 13
summary.target_stage_assistant_count = 0
summary.target_merge_delete_count = 14
[PASS] vibe-bio-science-pack-consolidation-audit-gate passed

.\scripts\verify\vibe-global-pack-consolidation-audit-gate.ps1
bio-science.skill_candidate_count = 13
bio-science.route_authority_count = 13
[PASS] vibe-global-pack-consolidation-audit-gate passed

.\scripts\verify\vibe-offline-skills-gate.ps1
[PASS] offline skill closure gate passed.

.\scripts\verify\probe-scientific-packs.ps1
bio-science case_count = 18
bio-science pack_match_ratio = 1.0
bio-science skill_match_ratio = 1.0

git diff --check
exit code 0
```

## Caveats

- This is routing/config and bundled-skill cleanup, not proof that `bio-database-evidence` was materially used in a real task.
- Old governance notes may mention deleted skill IDs as historical state.
- Deleted skill IDs remain only in governance history, deletion assertions, and the pack-consolidation audit's merge/delete list. They should not appear as live config skill keys, pack candidates, lock entries, verification-script expected skills, or bundled skill directories.
- Cross-pack boundaries for chemistry, literature, imaging, LaTeX submission, and scientific figures remain protected by regression tests.
