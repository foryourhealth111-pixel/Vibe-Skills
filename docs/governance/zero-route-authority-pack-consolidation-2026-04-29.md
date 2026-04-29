# Zero Route Authority Pack Consolidation

Date: 2026-04-29

## Scope

This pass cleans the approved first batch of packs that had `skill_candidates` but no direct `route_authority_candidates`.

In scope:

| Pack | Before | After |
| --- | --- | --- |
| `science-medical-imaging` | 5 skill candidates, 0 route owners | 5 direct route owners, 0 stage assistants |
| `finance-edgar-macro` | 7 skill candidates, 0 route owners | 7 direct route owners, 0 stage assistants |
| `science-zarr-polars` | 4 skill candidates including misplaced `tiledbvcf` | 3 direct route owners, `tiledbvcf` moved out |
| `science-tiledbvcf` | Existing specialist pack without direct-owner role for this split | 1 direct route owner, 0 stage assistants |
| `science-geospatial` | 3 skill candidates including misplaced `geo-database` | 2 direct route owners, `geo-database` removed from geospatial |
| `web-scraping` | 2 skill candidates, 0 route owners | 2 direct route owners, 0 stage assistants |

Out of scope:

- Physical deletion of skill directories.
- Adding auxiliary expert, consultation, primary/secondary, or stage-assistant semantics.
- Expanding cleanup to lower-priority long-tail packs.

## Direct Owners

| Pack | Direct route owners | Boundary decision |
| --- | --- | --- |
| `science-medical-imaging` | `pydicom`, `imaging-data-commons`, `histolab`, `omero-integration`, `pathml` | Each owner maps to a distinct medical-imaging task surface. |
| `finance-edgar-macro` | `edgartools`, `alpha-vantage`, `fred-economic-data`, `usfiscaldata`, `hedgefundmonitor`, `market-research-reports`, `datacommons-client` | Finance data sources and market-report generation are direct owners; finance-source prompts should not fall into generic science reporting. |
| `science-zarr-polars` | `polars`, `vaex`, `zarr-python` | Tabular/out-of-core/chunked-array work stays here. |
| `science-tiledbvcf` | `tiledbvcf` | VCF/BCF and population-genomics storage is isolated from generic Zarr/Polars routing. |
| `science-geospatial` | `geopandas`, `geomaster` | GIS/vector work routes to `geopandas`; projection, remote sensing, and earth-observation workflows route to `geomaster`. |
| `web-scraping` | `scrapling`, `playwright` | Static scraping/extraction routes to `scrapling`; browser automation, login flow, dynamic pages, and screenshot debugging route to `playwright`. |

## Removed From Pack Surfaces

| Skill | Previous issue | New boundary |
| --- | --- | --- |
| `tiledbvcf` | Appeared inside `science-zarr-polars` despite owning genomic variant storage. | Removed from `science-zarr-polars`; owned by `science-tiledbvcf`. |
| `geo-database` | Appeared inside `science-geospatial`, where `GEO` could mean either GIS or NCBI Gene Expression Omnibus. | Removed from `science-geospatial`; narrowed to NCBI GEO / expression-dataset routing rules. |

## Verification Coverage

Focused regression:

```powershell
python -m pytest tests/runtime_neutral/test_zero_route_authority_pack_consolidation.py -q
```

Route gates extended:

```powershell
.\scripts\verify\probe-scientific-packs.ps1
.\scripts\verify\vibe-skill-index-routing-audit.ps1
.\scripts\verify\vibe-pack-regression-matrix.ps1
```

Covered boundaries:

- Medical imaging direct owners: `pydicom`, `imaging-data-commons`, `histolab`, `omero-integration`, `pathml`.
- Finance direct owners: EDGAR, Alpha Vantage, FRED, U.S. Treasury Fiscal Data, Hedge Fund Monitor, market research reports, Data Commons.
- Zarr/Polars versus TileDB-VCF split.
- Geospatial routing blocks NCBI GEO expression-dataset prompts.
- Web scraping splits `scrapling` from `playwright` and blocks generic PubMed/citation research.

## Deletion Position

No skill directory is physically deleted in this pass. The cleanup is a live routing/config change: route owners are explicit, stage assistants are empty, and misplaced skills are removed from the pack surfaces where they caused ambiguity.
