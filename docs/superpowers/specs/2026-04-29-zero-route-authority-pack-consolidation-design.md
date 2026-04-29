# Zero Route Authority Pack Consolidation Design

Date: 2026-04-29

## 1. Goal

This design defines the first cleanup pass for Vibe-Skills packs that have `skill_candidates` but no `route_authority_candidates`.

The goal is to make the manifest contract match the simplified routing model:

```text
selected / used
not selected / unused
```

This pass must not reintroduce `stage_assistant`, primary/secondary skill states, consult semantics, or hidden helper ownership. A skill that remains in the primary routing surface must own a clear user problem. A skill that does not own a clear user problem must be moved out of the main routing surface, converted to an alias, or marked for later deletion review.

## 2. Current Evidence

The current branch is `main`, with the latest cleanup commits:

```text
13e89ece fix: make bio science skills direct route owners
2585a1de chore: refresh skills lock after bio science cleanup
```

The working tree was clean before this design was written.

The manifest currently has 23 packs with non-empty `skill_candidates` and zero `route_authority_candidates`. This first pass covers only the high-value and structurally ambiguous subset:

```text
science-medical-imaging
finance-edgar-macro
science-zarr-polars
science-geospatial
web-scraping
```

These five packs already have routing rules and probe coverage in parts of the verification suite, so the problem is not that they are unusable. The problem is that manifest authority is unclear: the routing rules can select skills, but the pack manifest does not say which skills are allowed to directly own user tasks.

## 3. Scope

### 3.1 In Scope

This pass will:

- Add direct route ownership for clearly useful skills in the five selected packs.
- Remove or relocate obvious duplicate or misplaced candidates from these packs when the pack boundary is wrong.
- Add focused routing regression cases for each important direct owner and false-positive boundary.
- Write governance notes documenting before/after route ownership.
- Refresh `skills-lock.json` only after route and governance changes are stable.

### 3.2 Out Of Scope

This pass will not:

- Change the six-stage Vibe runtime.
- Add `stage_assistant_candidates`.
- Add primary/secondary skill states.
- Claim routed skills were materially used in an actual task.
- Physically delete skill directories unless a directory is proven to be a disposable alias or empty shell and the implementation plan explicitly calls it out.
- Process all 23 zero-authority packs at once.

## 4. Pack Decisions

### 4.1 `science-medical-imaging`

Current candidates:

```text
pydicom
imaging-data-commons
histolab
omero-integration
pathml
```

Target decision: keep all five as direct route owners.

Problem boundaries:

| Skill | Direct user problem |
| --- | --- |
| `pydicom` | Read, write, inspect, anonymize, and transform DICOM files and tags. |
| `imaging-data-commons` | Query and download public cancer imaging cohorts from NCI IDC. |
| `histolab` | Tile extraction and preprocessing for whole-slide pathology images. |
| `omero-integration` | Access and manage microscopy images, ROIs, annotations, and OMERO datasets. |
| `pathml` | Computational pathology workflows over WSI and multiparametric imaging data. |

Important boundaries:

- DICOM tags should route to `pydicom`, not generic docs or bio-science.
- Public cancer imaging cohort lookup should route to `imaging-data-commons`, not broad clinical-regulatory.
- Pathology WSI tiling should route to `histolab` or `pathml`, depending on whether the prompt is preprocessing-only or workflow-level pathology analysis.

### 4.2 `finance-edgar-macro`

Current candidates:

```text
edgartools
alpha-vantage
fred-economic-data
usfiscaldata
hedgefundmonitor
market-research-reports
datacommons-client
```

Target decision: keep all seven as direct route owners, but narrow each to a data source or deliverable boundary.

Problem boundaries:

| Skill | Direct user problem |
| --- | --- |
| `edgartools` | SEC EDGAR filings, 10-K/10-Q extraction, XBRL statements, company facts. |
| `alpha-vantage` | Market prices, indicators, FX, crypto, commodities, and market API data. |
| `fred-economic-data` | FRED macroeconomic time series and economic indicators. |
| `usfiscaldata` | U.S. Treasury fiscal data, debt, spending, revenue, and rates. |
| `hedgefundmonitor` | OFR hedge fund monitor data and Form PF aggregate evidence. |
| `market-research-reports` | Consulting-style market research report generation. |
| `datacommons-client` | Public statistical data from Data Commons. |

Important boundaries:

- Financial report generation must not swallow raw data acquisition tasks.
- EDGAR filing extraction belongs to `edgartools`, not `market-research-reports`.
- Macro time series belongs to `fred-economic-data`, not generic data-ml.

### 4.3 `science-zarr-polars`

Current candidates:

```text
polars
vaex
zarr-python
tiledbvcf
```

Target decision:

- Keep `polars`, `vaex`, and `zarr-python` as direct route owners.
- Remove `tiledbvcf` from this pack's primary ownership, because `science-tiledbvcf` already owns the same skill and the domain is genomic variant storage, not general Zarr/Polars data handling.

Problem boundaries:

| Skill | Direct user problem |
| --- | --- |
| `polars` | Fast in-memory DataFrame processing for tabular data that fits in memory. |
| `vaex` | Out-of-core tabular analytics for very large datasets. |
| `zarr-python` | Chunked N-D arrays, cloud storage, compressed arrays, and large scientific array data. |
| `tiledbvcf` | Move to or keep under `science-tiledbvcf` as the direct owner for genomic variant storage/query. |

Important boundaries:

- General large tabular analytics should not route to `tiledbvcf`.
- VCF/BCF population-genomics storage should route to `science-tiledbvcf / tiledbvcf`.

### 4.4 `science-geospatial`

Current candidates:

```text
geopandas
geo-database
geomaster
```

Target decision:

- Keep `geopandas` and `geomaster` as direct route owners.
- Remove `geo-database` from `science-geospatial`, because it is NCBI GEO gene expression/genomics data, not geographic or GIS data.
- Rehome `geo-database` in a bio/literature/data-source surface only if a later pass proves it should remain in main routing; otherwise mark it as an explicit review candidate.

Problem boundaries:

| Skill | Direct user problem |
| --- | --- |
| `geopandas` | Vector geospatial data, shapefiles, GeoJSON, GeoPackage, spatial joins, and GIS tables. |
| `geomaster` | Broad geospatial science, remote sensing, earth observation, and spatial analysis workflows. |
| `geo-database` | NCBI GEO expression datasets; not a geospatial skill. |

Important boundaries:

- GIS prompts should never route to NCBI GEO.
- GEO gene-expression prompts should not be owned by a geospatial pack.

### 4.5 `web-scraping`

Current candidates:

```text
scrapling
playwright
```

Target decision: keep both as direct route owners with narrow boundaries.

Problem boundaries:

| Skill | Direct user problem |
| --- | --- |
| `scrapling` | CLI-first scraping and selector-based content extraction from target URLs. |
| `playwright` | Browser automation, dynamic pages, form flows, screenshots, and browser-debug workflows. |

Important boundaries:

- Static selector extraction should prefer `scrapling`.
- Real browser interaction, JS-heavy pages, login flows, screenshots, and debugging should prefer `playwright`.
- Generic research or citation lookup must not route to web scraping just because the prompt contains "website" or "search".

## 5. Options Considered

### Option A: Mark Every Candidate As A Route Owner

This is fast, but it preserves misplaced skills such as `geo-database` in the geospatial pack and duplicate `tiledbvcf` ownership. It would make the manifest superficially consistent while leaving incorrect boundaries.

### Option B: Problem-First Direct Owner Cleanup

This keeps direct route owners where the user problem is clear, removes duplicate or misplaced candidates from the pack surface, and adds regression cases for each decision.

This is the recommended option.

### Option C: Delete All Cold Or Ambiguous Skills Immediately

This would reduce manifest size quickly, but it risks deleting useful skills with references, scripts, or examples before migration. It also mixes routing cleanup with physical deletion, which should remain a separate migration step.

## 6. Recommended Design

Use Option B.

Implementation should edit the routing configs in this order:

1. Update `config/pack-manifest.json`:
   - Add direct `route_authority_candidates` for kept owners.
   - Remove `tiledbvcf` from `science-zarr-polars` if `science-tiledbvcf` remains the owner.
   - Remove `geo-database` from `science-geospatial` unless the implementation plan chooses a better immediate home.
   - Keep `stage_assistant_candidates` empty for all five packs.
2. Update `config/skill-keyword-index.json`:
   - Add or narrow keywords so each direct owner has concrete English and Chinese triggers.
   - Avoid broad words like `data`, `research`, `report`, `website`, or `analysis` as decisive signals.
3. Update `config/skill-routing-rules.json`:
   - Add positive keywords for each owner.
   - Add negative keywords for known false positives.
   - Make `scrapling` and `playwright` distinguish static extraction from browser automation.
4. Add or extend route regression tests and scripts:
   - Include one positive route case per direct owner.
   - Include false-positive cases for `geo-database`, `tiledbvcf`, report generation, and generic website research.
5. Write governance notes under `docs/governance/`.
6. Refresh `config/skills-lock.json` after content changes.

## 7. Testing

Focused tests should cover at least these cases:

| Prompt type | Expected owner |
| --- | --- |
| Read DICOM tags | `science-medical-imaging / pydicom` |
| Query NCI IDC cohort | `science-medical-imaging / imaging-data-commons` |
| Extract WSI tiles | `science-medical-imaging / histolab` or `pathml`, depending on scope |
| Query SEC 10-K filings | `finance-edgar-macro / edgartools` |
| Get FRED unemployment or CPI series | `finance-edgar-macro / fred-economic-data` |
| Generate a market research report | `finance-edgar-macro / market-research-reports` |
| Process large table with Polars | `science-zarr-polars / polars` |
| Store chunked N-D arrays in Zarr | `science-zarr-polars / zarr-python` |
| Query VCF/BCF with TileDB-VCF | `science-tiledbvcf / tiledbvcf` |
| Work with shapefiles or GeoJSON | `science-geospatial / geopandas` |
| Remote sensing or earth observation workflow | `science-geospatial / geomaster` |
| Query NCBI GEO gene expression | not `science-geospatial` |
| CSS selector scraping | `web-scraping / scrapling` |
| Browser automation or screenshot flow | `web-scraping / playwright` |

Expected verification commands:

```powershell
python -m pytest tests/runtime_neutral/test_zero_route_authority_pack_consolidation.py -q
.\scripts\verify\probe-scientific-packs.ps1
.\scripts\verify\vibe-skill-index-routing-audit.ps1
.\scripts\verify\vibe-pack-regression-matrix.ps1
.\scripts\verify\vibe-pack-routing-smoke.ps1
.\scripts\verify\vibe-generate-skills-lock.ps1
.\scripts\verify\vibe-offline-skills-gate.ps1
.\scripts\verify\vibe-config-parity-gate.ps1 -WriteArtifacts
git diff --check
```

## 8. Acceptance Criteria

This pass is accepted when:

- The five selected packs no longer have empty `route_authority_candidates` when they retain direct routeable skills.
- None of the five selected packs has `stage_assistant_candidates`.
- `geo-database` no longer appears as a geospatial route owner.
- `tiledbvcf` has one clear primary pack owner.
- Each retained owner has at least one regression case proving its route.
- False-positive boundaries are covered for GEO, TileDB-VCF, generic market reports, and generic website research.
- Focused tests and broader routing/config gates pass.

## 9. Non-Goals

This pass will not clean up:

```text
aios-core
science-figures-visualization
science-reporting
ruc-nlpir-augmentation
all remaining one-skill science packs
```

Those remain separate cleanup passes.
