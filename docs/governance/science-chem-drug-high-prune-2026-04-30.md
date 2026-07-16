# Science Chem Drug High-Prune Pass

> Historical / Retired Note: This document discusses retired or cleanup-context routing terminology. The current routing model is `skill_candidates -> skill_routing.selected -> module_skill_dispatch -> skill_usage`; old terms here are historical only and are not current runtime states.

Date: 2026-04-30

## Summary

`science-chem-drug` was reduced to a small core pack for common chemistry and medicinal chemistry work. The intent is high-resource discipline for a cold project area: keep only skills that can clearly own common user tasks, and physically delete narrow database or heavyweight framework skills that should not consume routing or bundle surface.

This pass keeps the six-stage Vibe runtime unchanged and preserves the binary usage model:

```text
skill_routing.selected -> skill_usage.used / unused
```

No `primary/secondary`, `consult`, `advisory`, or stage-assistant execution semantics were added.

## Before And After

| Field | Before | After |
| --- | ---: | ---: |
| `skill_candidates` | 11 | 3 |
| `route_authority_candidates` | 11 | 3 |
| `stage_assistant_candidates` | 0 | 0 |
| physical directory deletion | 0 | 10 |

## Kept Route Authorities

| Skill | Boundary |
| --- | --- |
| `rdkit` | Core cheminformatics implementation: SMILES/SDF/InChI parsing, descriptors, ECFP/Morgan fingerprints, similarity, substructure, reactions, and molecule standardization |
| `medchem` | Medicinal chemistry decision support: SAR, PAINS, Lipinski, drug-likeness, structural alerts, ADMET risk discussion, hit-to-lead and lead optimization |
| `chembl-database` | Target-ligand bioactivity evidence: ChEMBL assays, IC50/Ki/Kd activity tables, and target activity lookup |

`route_authority_candidates` mirrors `skill_candidates`. There are no stage assistants in this pack.

## Deleted Skill Directories

| Skill | Reason |
| --- | --- |
| `drugbank-database` | Credentialed/narrow pharmacology and interaction database; too cold to remain bundled as a main route authority |
| `pubchem-database` | Mostly simple identifier/property lookup; does not justify a dedicated bundled expert in this reduced pack |
| `brenda-database` | Narrow enzyme-kinetics database; useful only for specialized biochemical database work |
| `hmdb-database` | Narrow metabolomics database; overlaps better with metabolomics-specific surfaces if needed later |
| `zinc-database` | Narrow screening-library source; virtual-screening library lookup is too cold for ordinary routing |
| `deepchem` | Heavy molecular ML framework; overlaps general ML routing and is too specialized for the compact chem pack |
| `diffdock` | Heavy docking environment and narrow pose-prediction route; high maintenance cost for cold usage |
| `pytdc` | Dataset/benchmark helper, not a broad route owner; overlaps general ML dataset handling |
| `datamol` | RDKit wrapper with no distinct user problem after `rdkit` remains as core owner |
| `molfeat` | Feature-extraction helper overlapping RDKit and general ML; no distinct route authority |

## Protected Route Boundaries

| Prompt | Expected route |
| --- | --- |
| `用RDKit解析SMILES并计算Morgan fingerprint` | `science-chem-drug / rdkit` |
| `在 ChEMBL 查询 EGFR 靶点的 IC50 / Ki / Kd 活性数据` | `science-chem-drug / chembl-database` |
| `做药物化学 SAR 分析、PAINS 过滤、Lipinski 规则和先导化合物优化建议` | `science-chem-drug / medchem` |
| `用 datamol 批量标准化 SMILES 并生成分子指纹` | `science-chem-drug / rdkit` |
| `DrugBank / PubChem / BRENDA / HMDB / ZINC / DiffDock / DeepChem / PyTDC / MolFeat` direct prompts | not `science-chem-drug` |
| `bulk RNA-seq 差异表达 / GO KEGG 富集` | not `science-chem-drug` |
| `PubMed 检索 / BibTeX / 文献综述` | not `science-chem-drug` |
| `ClinicalTrials.gov / NCT / FDA label` | not `science-chem-drug` |

## Verification Targets

Focused:

```powershell
python -m pytest tests/runtime_neutral/test_science_chem_drug_pack_consolidation.py -q
```

Broader probes and gates:

```powershell
.\scripts\verify\probe-scientific-packs.ps1
.\scripts\verify\vibe-skill-index-routing-audit.ps1
.\scripts\verify\vibe-pack-regression-matrix.ps1
.\scripts\verify\vibe-offline-skills-gate.ps1
.\scripts\verify\vibe-config-parity-gate.ps1 -WriteArtifacts
git diff --check
```

## Reintroduction Rule

If one of the deleted databases or frameworks becomes necessary later, it should return as an explicit optional long-tail pack or user-installed skill, not as an ordinary `science-chem-drug` route authority by default.
