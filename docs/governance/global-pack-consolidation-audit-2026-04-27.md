# Global Pack Consolidation Audit

日期：2026-04-27

## 结论先看

本报告是只读体检，不修改 live routing，不删除 skill 目录。

- pack 总数：41
- P0：6
- P1：10
- P2：25
- 当前最高风险 pack：`code-quality`

## 全局排序

| priority | pack | score | skills | route authority | stage assistant | rationale |
|---|---|---:|---:|---:|---:|---|
| P0 | `code-quality` | 39.20 | 10 | 10 | 0 | 10 route authorities; 3 suspected overlap pairs; 2 candidates with scripts/references/assets |
| P0 | `docs-media` | 37.00 | 8 | 8 | 0 | 8 route authorities; 1 suspected overlap pairs; 5 tool-like primary candidates; 5 candidates with scripts/references/assets |
| P0 | `science-literature-citations` | 34.50 | 5 | 5 | 0 | 5 route authorities; 5 shared broad keywords; 5 tool-like primary candidates; 5 candidates with scripts/references/assets |
| P0 | `scholarly-publishing-workflow` | 34.20 | 8 | 8 | 0 | 8 route authorities; 1 shared broad keywords; 3 tool-like primary candidates; 5 candidates with scripts/references/assets |
| P0 | `finance-edgar-macro` | 33.30 | 7 | 7 | 0 | 7 route authorities; 5 tool-like primary candidates; 7 candidates with scripts/references/assets |
| P0 | `science-clinical-regulatory` | 33.30 | 7 | 7 | 0 | 7 route authorities; 5 tool-like primary candidates; 7 candidates with scripts/references/assets |
| P1 | `data-ml` | 31.60 | 8 | 8 | 0 | 8 route authorities; 1 tool-like primary candidates; 7 candidates with scripts/references/assets |
| P1 | `research-design` | 30.50 | 5 | 5 | 0 | 5 route authorities; 7 shared broad keywords; 3 candidates with scripts/references/assets |
| P1 | `integration-devops` | 23.80 | 6 | 6 | 0 | 6 route authorities; 1 tool-like primary candidates; 5 candidates with scripts/references/assets |
| P1 | `science-communication-slides` | 22.60 | 4 | 4 | 0 | 3 shared broad keywords; 2 tool-like primary candidates; 3 candidates with scripts/references/assets |
| P1 | `ai-llm` | 20.70 | 5 | 5 | 0 | 5 route authorities; 3 tool-like primary candidates; 2 candidates with scripts/references/assets |
| P1 | `science-medical-imaging` | 19.50 | 5 | 5 | 0 | 5 route authorities; 5 candidates with scripts/references/assets |
| P1 | `bio-science` | 18.00 | 4 | 4 | 0 | 2 tool-like primary candidates; 4 candidates with scripts/references/assets |
| P1 | `media-video` | 15.30 | 3 | 3 | 0 | 3 tool-like primary candidates; 3 candidates with scripts/references/assets |
| P1 | `science-peer-review` | 15.30 | 3 | 3 | 0 | 3 tool-like primary candidates; 3 candidates with scripts/references/assets |
| P1 | `science-zarr-polars` | 14.70 | 3 | 3 | 0 | 1 shared broad keywords; 1 tool-like primary candidates; 3 candidates with scripts/references/assets |
| P2 | `science-chem-drug` | 12.90 | 3 | 3 | 0 | 1 tool-like primary candidates; 3 candidates with scripts/references/assets |
| P2 | `science-geospatial` | 10.80 | 2 | 2 | 0 | 1 shared broad keywords; 1 tool-like primary candidates; 2 candidates with scripts/references/assets |
| P2 | `science-figures-visualization` | 9.00 | 2 | 2 | 0 | 1 tool-like primary candidates; 2 candidates with scripts/references/assets |
| P2 | `web-scraping` | 9.00 | 2 | 2 | 0 | 1 tool-like primary candidates; 2 candidates with scripts/references/assets |
| P2 | `science-reporting` | 8.20 | 2 | 2 | 0 | 1 tool-like primary candidates; 1 candidates with scripts/references/assets |
| P2 | `ruc-nlpir-augmentation` | 7.80 | 2 | 2 | 0 | 2 candidates with scripts/references/assets |
| P2 | `docs-markitdown-conversion` | 5.10 | 1 | 1 | 0 | 1 tool-like primary candidates; 1 candidates with scripts/references/assets |
| P2 | `ip-uspto-patents` | 5.10 | 1 | 1 | 0 | 1 tool-like primary candidates; 1 candidates with scripts/references/assets |
| P2 | `ml-stable-baselines3` | 5.10 | 1 | 1 | 0 | 1 tool-like primary candidates; 1 candidates with scripts/references/assets |
| P2 | `science-fluidsim-cfd` | 5.10 | 1 | 1 | 0 | 1 tool-like primary candidates; 1 candidates with scripts/references/assets |
| P2 | `science-pymoo-optimization` | 5.10 | 1 | 1 | 0 | 1 tool-like primary candidates; 1 candidates with scripts/references/assets |
| P2 | `science-rowan-chemistry` | 5.10 | 1 | 1 | 0 | 1 tool-like primary candidates; 1 candidates with scripts/references/assets |
| P2 | `science-simpy-simulation` | 5.10 | 1 | 1 | 0 | 1 tool-like primary candidates; 1 candidates with scripts/references/assets |
| P2 | `design-implementation` | 3.90 | 1 | 1 | 0 | 1 candidates with scripts/references/assets |
| P2 | `ml-torch-geometric` | 3.90 | 1 | 1 | 0 | 1 candidates with scripts/references/assets |
| P2 | `science-astropy` | 3.90 | 1 | 1 | 0 | 1 candidates with scripts/references/assets |
| P2 | `science-matchms-spectra` | 3.90 | 1 | 1 | 0 | 1 candidates with scripts/references/assets |
| P2 | `science-matlab-octave` | 3.90 | 1 | 1 | 0 | 1 candidates with scripts/references/assets |
| P2 | `science-neuropixels` | 3.90 | 1 | 1 | 0 | 1 candidates with scripts/references/assets |
| P2 | `science-pymatgen` | 3.90 | 1 | 1 | 0 | 1 candidates with scripts/references/assets |
| P2 | `science-pymc-bayesian` | 3.90 | 1 | 1 | 0 | 1 candidates with scripts/references/assets |
| P2 | `science-timesfm-forecasting` | 3.90 | 1 | 1 | 0 | 1 candidates with scripts/references/assets |
| P2 | `screen-capture` | 3.90 | 1 | 1 | 0 | 1 candidates with scripts/references/assets |
| P2 | `workflow-compatibility` | 3.90 | 1 | 1 | 0 | 1 candidates with scripts/references/assets |
| P2 | `science-tiledbvcf` | 3.10 | 1 | 1 | 0 | low structural risk |

## P0

| priority | pack | score | skills | route authority | stage assistant | rationale |
|---|---|---:|---:|---:|---:|---|
| P0 | `code-quality` | 39.20 | 10 | 10 | 0 | 10 route authorities; 3 suspected overlap pairs; 2 candidates with scripts/references/assets |
| P0 | `docs-media` | 37.00 | 8 | 8 | 0 | 8 route authorities; 1 suspected overlap pairs; 5 tool-like primary candidates; 5 candidates with scripts/references/assets |
| P0 | `science-literature-citations` | 34.50 | 5 | 5 | 0 | 5 route authorities; 5 shared broad keywords; 5 tool-like primary candidates; 5 candidates with scripts/references/assets |
| P0 | `scholarly-publishing-workflow` | 34.20 | 8 | 8 | 0 | 8 route authorities; 1 shared broad keywords; 3 tool-like primary candidates; 5 candidates with scripts/references/assets |
| P0 | `finance-edgar-macro` | 33.30 | 7 | 7 | 0 | 7 route authorities; 5 tool-like primary candidates; 7 candidates with scripts/references/assets |
| P0 | `science-clinical-regulatory` | 33.30 | 7 | 7 | 0 | 7 route authorities; 5 tool-like primary candidates; 7 candidates with scripts/references/assets |

## P1

| priority | pack | score | skills | route authority | stage assistant | rationale |
|---|---|---:|---:|---:|---:|---|
| P1 | `data-ml` | 31.60 | 8 | 8 | 0 | 8 route authorities; 1 tool-like primary candidates; 7 candidates with scripts/references/assets |
| P1 | `research-design` | 30.50 | 5 | 5 | 0 | 5 route authorities; 7 shared broad keywords; 3 candidates with scripts/references/assets |
| P1 | `integration-devops` | 23.80 | 6 | 6 | 0 | 6 route authorities; 1 tool-like primary candidates; 5 candidates with scripts/references/assets |
| P1 | `science-communication-slides` | 22.60 | 4 | 4 | 0 | 3 shared broad keywords; 2 tool-like primary candidates; 3 candidates with scripts/references/assets |
| P1 | `ai-llm` | 20.70 | 5 | 5 | 0 | 5 route authorities; 3 tool-like primary candidates; 2 candidates with scripts/references/assets |
| P1 | `science-medical-imaging` | 19.50 | 5 | 5 | 0 | 5 route authorities; 5 candidates with scripts/references/assets |
| P1 | `bio-science` | 18.00 | 4 | 4 | 0 | 2 tool-like primary candidates; 4 candidates with scripts/references/assets |
| P1 | `media-video` | 15.30 | 3 | 3 | 0 | 3 tool-like primary candidates; 3 candidates with scripts/references/assets |
| P1 | `science-peer-review` | 15.30 | 3 | 3 | 0 | 3 tool-like primary candidates; 3 candidates with scripts/references/assets |
| P1 | `science-zarr-polars` | 14.70 | 3 | 3 | 0 | 1 shared broad keywords; 1 tool-like primary candidates; 3 candidates with scripts/references/assets |

## P2

| priority | pack | score | skills | route authority | stage assistant | rationale |
|---|---|---:|---:|---:|---:|---|
| P2 | `science-chem-drug` | 12.90 | 3 | 3 | 0 | 1 tool-like primary candidates; 3 candidates with scripts/references/assets |
| P2 | `science-geospatial` | 10.80 | 2 | 2 | 0 | 1 shared broad keywords; 1 tool-like primary candidates; 2 candidates with scripts/references/assets |
| P2 | `science-figures-visualization` | 9.00 | 2 | 2 | 0 | 1 tool-like primary candidates; 2 candidates with scripts/references/assets |
| P2 | `web-scraping` | 9.00 | 2 | 2 | 0 | 1 tool-like primary candidates; 2 candidates with scripts/references/assets |
| P2 | `science-reporting` | 8.20 | 2 | 2 | 0 | 1 tool-like primary candidates; 1 candidates with scripts/references/assets |
| P2 | `ruc-nlpir-augmentation` | 7.80 | 2 | 2 | 0 | 2 candidates with scripts/references/assets |
| P2 | `docs-markitdown-conversion` | 5.10 | 1 | 1 | 0 | 1 tool-like primary candidates; 1 candidates with scripts/references/assets |
| P2 | `ip-uspto-patents` | 5.10 | 1 | 1 | 0 | 1 tool-like primary candidates; 1 candidates with scripts/references/assets |
| P2 | `ml-stable-baselines3` | 5.10 | 1 | 1 | 0 | 1 tool-like primary candidates; 1 candidates with scripts/references/assets |
| P2 | `science-fluidsim-cfd` | 5.10 | 1 | 1 | 0 | 1 tool-like primary candidates; 1 candidates with scripts/references/assets |
| P2 | `science-pymoo-optimization` | 5.10 | 1 | 1 | 0 | 1 tool-like primary candidates; 1 candidates with scripts/references/assets |
| P2 | `science-rowan-chemistry` | 5.10 | 1 | 1 | 0 | 1 tool-like primary candidates; 1 candidates with scripts/references/assets |
| P2 | `science-simpy-simulation` | 5.10 | 1 | 1 | 0 | 1 tool-like primary candidates; 1 candidates with scripts/references/assets |
| P2 | `design-implementation` | 3.90 | 1 | 1 | 0 | 1 candidates with scripts/references/assets |
| P2 | `ml-torch-geometric` | 3.90 | 1 | 1 | 0 | 1 candidates with scripts/references/assets |
| P2 | `science-astropy` | 3.90 | 1 | 1 | 0 | 1 candidates with scripts/references/assets |
| P2 | `science-matchms-spectra` | 3.90 | 1 | 1 | 0 | 1 candidates with scripts/references/assets |
| P2 | `science-matlab-octave` | 3.90 | 1 | 1 | 0 | 1 candidates with scripts/references/assets |
| P2 | `science-neuropixels` | 3.90 | 1 | 1 | 0 | 1 candidates with scripts/references/assets |
| P2 | `science-pymatgen` | 3.90 | 1 | 1 | 0 | 1 candidates with scripts/references/assets |
| P2 | `science-pymc-bayesian` | 3.90 | 1 | 1 | 0 | 1 candidates with scripts/references/assets |
| P2 | `science-timesfm-forecasting` | 3.90 | 1 | 1 | 0 | 1 candidates with scripts/references/assets |
| P2 | `screen-capture` | 3.90 | 1 | 1 | 0 | 1 candidates with scripts/references/assets |
| P2 | `workflow-compatibility` | 3.90 | 1 | 1 | 0 | 1 candidates with scripts/references/assets |
| P2 | `science-tiledbvcf` | 3.10 | 1 | 1 | 0 | low structural risk |

## 边界说明

- 本报告只说明治理优先级，不代表删除建议。
- 具体 pack 收敛需要下一轮 problem-first 设计。
- 带 scripts、references、examples 或 assets 的 skill 不能直接删除。
- 若后续修改路由，需要补对应 route regression probe。
