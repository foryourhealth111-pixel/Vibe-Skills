# Bio-Science High-Prune Consolidation - 2026-04-30

> Historical / Retired Note: This document discusses retired or cleanup-context routing terminology. The current routing model is `skill_candidates -> skill_routing.selected -> module_skill_dispatch -> skill_usage`; old terms here are historical only and are not current runtime states.

## Scope

This pass applies a high-strength simplification to `bio-science` after the earlier boundary-hardening and second-pass database consolidation work.

It does not change the six-stage Vibe runtime. It does not add helper experts, advisory routing, consultation routing, primary/secondary skill states, or stage assistants.

The live skill-use model remains:

```text
candidate skill -> selected skill -> used / unused
```

## Counts

| Metric | Before this pass | After this pass |
| --- | ---: | ---: |
| `skill_candidates` | 13 | 4 |
| `route_authority_candidates` | 13 | 4 |
| `stage_assistant_candidates` | 0 | 0 |
| physically deleted skill directories in this pass | 0 | 9 |

## Retained Route Authorities

| Skill | Retained problem owner |
| --- | --- |
| `biopython` | Sequence files, FASTA/FASTQ/GenBank, SeqIO, Entrez, BLAST, sequence conversion, alignments, structures, and phylogenetics. |
| `scanpy` | Single-cell RNA-seq workflows, h5ad/AnnData container handling, and scVI/scANVI batch-correction planning. |
| `pydeseq2` | Bulk RNA-seq differential expression, DESeq2-style statistics, FDR, volcano plots, and MA plots. |
| `bio-database-evidence` | Biological database evidence, gene/variant/pathway/target/protein-structure/PPI/census lookup, and cross-database ID mapping. |

## Deleted Or Absorbed

| Deleted skill | Decision |
| --- | --- |
| `anndata` | Absorbed into `scanpy`; AnnData/h5ad is a data structure inside retained single-cell workflows. |
| `scvi-tools` | Absorbed into `scanpy`; scVI/scANVI is retained as workflow planning language, not a separate route owner. |
| `pysam` | Physically deleted as a narrow NGS file-processing expert. |
| `deeptools` | Physically deleted as a narrow NGS track/heatmap helper. |
| `esm` | Physically deleted as a heavy/cold protein language-model expert. |
| `cobrapy` | Physically deleted as a cold metabolic-flux modeling expert. |
| `geniml` | Physically deleted as a narrow genomic-interval embedding expert. |
| `arboreto` | Physically deleted as a narrow GRN inference expert. |
| `flowio` | Physically deleted as a narrow FCS parsing expert. |

## Routing Contract

- AnnData/h5ad prompts now route to `bio-science / scanpy`.
- scVI/scANVI latent-model and batch-correction prompts now route to `bio-science / scanpy`.
- Bulk RNA-seq differential-expression prompts remain `bio-science / pydeseq2`.
- Gene, variant, pathway, target, protein-structure, PPI, GWAS, and CELLxGENE Census evidence prompts remain `bio-science / bio-database-evidence`.
- The deleted cold experts must not appear in `pack-manifest.json`, `skill-keyword-index.json`, `skill-routing-rules.json`, `skills-lock.json`, or `bundled/skills`.

## Verification

Verification is recorded in the implementation closeout for this pass. The required gates are:

```text
python -m pytest tests/runtime_neutral/test_bio_science_second_pass_consolidation.py tests/runtime_neutral/test_bio_science_boundary_hardening.py tests/runtime_neutral/test_bio_science_direct_owner_routing.py tests/runtime_neutral/test_bio_science_pack_consolidation_audit.py -q
.\scripts\verify\vibe-bio-science-pack-consolidation-audit-gate.ps1
.\scripts\verify\vibe-skill-index-routing-audit.ps1
.\scripts\verify\probe-scientific-packs.ps1
.\scripts\verify\vibe-pack-regression-matrix.ps1
.\scripts\verify\vibe-pack-routing-smoke.ps1
.\scripts\verify\vibe-offline-skills-gate.ps1
.\scripts\verify\vibe-config-parity-gate.ps1 -WriteArtifacts
.\scripts\verify\vibe-global-pack-consolidation-audit-gate.ps1 -WriteArtifacts -OutputDirectory outputs\skills-audit-latest
git diff --check
```

## Caveats

- This is routing/config and bundled-skill cleanup, not proof that any retained skill was materially used in a real task.
- Historical governance documents may still mention deleted skill IDs as prior state.
- Explicit future tasks for deleted cold frameworks can still be handled by normal coding/research work, but they are no longer bundled route authorities.
