# Global Pack Consolidation Audit

日期：2026-04-27

## 结论先看

本报告是只读体检，不修改 live routing，不删除 skill 目录。

- pack 总数：44
- P0：6
- P1：14
- P2：24
- 当前最高风险 pack：`bio-science`

## 全局排序

| priority | pack | score | skills | route authority | stage assistant | rationale |
|---|---|---:|---:|---:|---:|---|
| P0 | `bio-science` | 66.40 | 26 | 0 | 0 | 26 skill candidates; no explicit role split; 15 tool-like primary candidates; 26 candidates with scripts/references/assets |
| P0 | `research-design` | 64.40 | 24 | 14 | 3 | 24 skill candidates; 14 route authorities; 3 suspected overlap pairs; 1 shared broad keywords; 2 tool-like primary candidates; 15 candidates with scripts/references/assets |
| P0 | `science-literature-citations` | 61.40 | 12 | 10 | 2 | 12 skill candidates; 10 route authorities; 5 shared broad keywords; 9 tool-like primary candidates; 11 candidates with scripts/references/assets |
| P0 | `scholarly-publishing-workflow` | 59.70 | 13 | 0 | 0 | 13 skill candidates; no explicit role split; 13 shared broad keywords; 4 tool-like primary candidates; 9 candidates with scripts/references/assets |
| P0 | `science-chem-drug` | 57.70 | 13 | 0 | 0 | 13 skill candidates; no explicit role split; 6 shared broad keywords; 6 tool-like primary candidates; 13 candidates with scripts/references/assets |
| P0 | `science-lab-automation` | 47.90 | 7 | 0 | 0 | no explicit role split; 6 shared broad keywords; 6 tool-like primary candidates; 7 candidates with scripts/references/assets |
| P1 | `integration-devops` | 42.90 | 13 | 0 | 0 | 13 skill candidates; no explicit role split; 3 tool-like primary candidates; 12 candidates with scripts/references/assets |
| P1 | `science-communication-slides` | 40.20 | 8 | 0 | 0 | no explicit role split; 3 shared broad keywords; 4 tool-like primary candidates; 6 candidates with scripts/references/assets |
| P1 | `orchestration-core` | 39.60 | 27 | 1 | 26 | 27 skill candidates; 2 suspected overlap pairs; 1 shared broad keywords; 9 candidates with scripts/references/assets |
| P1 | `ai-llm` | 39.30 | 11 | 0 | 0 | no explicit role split; 1 shared broad keywords; 4 tool-like primary candidates; 6 candidates with scripts/references/assets |
| P1 | `science-clinical-regulatory` | 37.70 | 7 | 0 | 0 | no explicit role split; 1 shared broad keywords; 5 tool-like primary candidates; 7 candidates with scripts/references/assets |
| P1 | `code-quality` | 37.00 | 10 | 9 | 1 | 9 route authorities; 3 suspected overlap pairs; 2 candidates with scripts/references/assets |
| P1 | `docs-media` | 37.00 | 8 | 8 | 0 | 8 route authorities; 1 suspected overlap pairs; 5 tool-like primary candidates; 5 candidates with scripts/references/assets |
| P1 | `finance-edgar-macro` | 35.90 | 7 | 0 | 0 | no explicit role split; 5 tool-like primary candidates; 7 candidates with scripts/references/assets |
| P1 | `data-ml` | 29.40 | 8 | 7 | 1 | 7 route authorities; 1 tool-like primary candidates; 7 candidates with scripts/references/assets |
| P1 | `science-medical-imaging` | 28.30 | 5 | 0 | 0 | no explicit role split; 1 shared broad keywords; 5 candidates with scripts/references/assets |
| P1 | `aios-core` | 16.40 | 12 | 1 | 11 | 12 skill candidates; 1 suspected overlap pairs; 1 tool-like primary candidates |
| P1 | `science-quantum` | 15.80 | 4 | 0 | 0 | 3 shared broad keywords; 3 tool-like primary candidates; 4 candidates with scripts/references/assets |
| P1 | `media-video` | 15.30 | 3 | 3 | 0 | 3 tool-like primary candidates; 3 candidates with scripts/references/assets |
| P1 | `science-figures-visualization` | 15.10 | 5 | 2 | 3 | 1 shared broad keywords; 1 tool-like primary candidates; 4 candidates with scripts/references/assets |
| P2 | `science-reporting` | 13.30 | 5 | 2 | 3 | 1 tool-like primary candidates; 4 candidates with scripts/references/assets |
| P2 | `ml-torch-geometric` | 12.00 | 2 | 0 | 0 | 1 suspected overlap pairs; 4 shared broad keywords; 1 candidates with scripts/references/assets |
| P2 | `ruc-nlpir-augmentation` | 11.40 | 4 | 2 | 2 | 1 shared broad keywords; 2 candidates with scripts/references/assets |
| P2 | `science-geospatial` | 9.30 | 3 | 0 | 0 | 1 shared broad keywords; 2 tool-like primary candidates; 3 candidates with scripts/references/assets |
| P2 | `science-zarr-polars` | 9.00 | 4 | 0 | 0 | 1 shared broad keywords; 1 tool-like primary candidates; 3 candidates with scripts/references/assets |
| P2 | `science-peer-review` | 8.70 | 3 | 0 | 0 | 3 tool-like primary candidates; 3 candidates with scripts/references/assets |
| P2 | `web-scraping` | 4.60 | 2 | 0 | 0 | 1 tool-like primary candidates; 2 candidates with scripts/references/assets |
| P2 | `screen-capture` | 3.90 | 1 | 1 | 0 | 1 candidates with scripts/references/assets |
| P2 | `docs-markitdown-conversion` | 2.90 | 1 | 0 | 0 | 1 tool-like primary candidates; 1 candidates with scripts/references/assets |
| P2 | `ip-uspto-patents` | 2.90 | 1 | 0 | 0 | 1 tool-like primary candidates; 1 candidates with scripts/references/assets |
| P2 | `ml-stable-baselines3` | 2.90 | 1 | 0 | 0 | 1 tool-like primary candidates; 1 candidates with scripts/references/assets |
| P2 | `science-fluidsim-cfd` | 2.90 | 1 | 0 | 0 | 1 tool-like primary candidates; 1 candidates with scripts/references/assets |
| P2 | `science-pymoo-optimization` | 2.90 | 1 | 0 | 0 | 1 tool-like primary candidates; 1 candidates with scripts/references/assets |
| P2 | `science-rowan-chemistry` | 2.90 | 1 | 0 | 0 | 1 tool-like primary candidates; 1 candidates with scripts/references/assets |
| P2 | `science-simpy-simulation` | 2.90 | 1 | 0 | 0 | 1 tool-like primary candidates; 1 candidates with scripts/references/assets |
| P2 | `science-astropy` | 1.70 | 1 | 0 | 0 | 1 candidates with scripts/references/assets |
| P2 | `science-matchms-spectra` | 1.70 | 1 | 0 | 0 | 1 candidates with scripts/references/assets |
| P2 | `science-matlab-octave` | 1.70 | 1 | 0 | 0 | 1 candidates with scripts/references/assets |
| P2 | `science-neuropixels` | 1.70 | 1 | 0 | 0 | 1 candidates with scripts/references/assets |
| P2 | `science-pymatgen` | 1.70 | 1 | 0 | 0 | 1 candidates with scripts/references/assets |
| P2 | `science-pymc-bayesian` | 1.70 | 1 | 0 | 0 | 1 candidates with scripts/references/assets |
| P2 | `science-timesfm-forecasting` | 1.70 | 1 | 0 | 0 | 1 candidates with scripts/references/assets |
| P2 | `cloud-modalcom` | 0.90 | 1 | 0 | 0 | low structural risk |
| P2 | `science-tiledbvcf` | 0.90 | 1 | 0 | 0 | low structural risk |

## P0

| priority | pack | score | skills | route authority | stage assistant | rationale |
|---|---|---:|---:|---:|---:|---|
| P0 | `bio-science` | 66.40 | 26 | 0 | 0 | 26 skill candidates; no explicit role split; 15 tool-like primary candidates; 26 candidates with scripts/references/assets |
| P0 | `research-design` | 64.40 | 24 | 14 | 3 | 24 skill candidates; 14 route authorities; 3 suspected overlap pairs; 1 shared broad keywords; 2 tool-like primary candidates; 15 candidates with scripts/references/assets |
| P0 | `science-literature-citations` | 61.40 | 12 | 10 | 2 | 12 skill candidates; 10 route authorities; 5 shared broad keywords; 9 tool-like primary candidates; 11 candidates with scripts/references/assets |
| P0 | `scholarly-publishing-workflow` | 59.70 | 13 | 0 | 0 | 13 skill candidates; no explicit role split; 13 shared broad keywords; 4 tool-like primary candidates; 9 candidates with scripts/references/assets |
| P0 | `science-chem-drug` | 57.70 | 13 | 0 | 0 | 13 skill candidates; no explicit role split; 6 shared broad keywords; 6 tool-like primary candidates; 13 candidates with scripts/references/assets |
| P0 | `science-lab-automation` | 47.90 | 7 | 0 | 0 | no explicit role split; 6 shared broad keywords; 6 tool-like primary candidates; 7 candidates with scripts/references/assets |

## P1

| priority | pack | score | skills | route authority | stage assistant | rationale |
|---|---|---:|---:|---:|---:|---|
| P1 | `integration-devops` | 42.90 | 13 | 0 | 0 | 13 skill candidates; no explicit role split; 3 tool-like primary candidates; 12 candidates with scripts/references/assets |
| P1 | `science-communication-slides` | 40.20 | 8 | 0 | 0 | no explicit role split; 3 shared broad keywords; 4 tool-like primary candidates; 6 candidates with scripts/references/assets |
| P1 | `orchestration-core` | 39.60 | 27 | 1 | 26 | 27 skill candidates; 2 suspected overlap pairs; 1 shared broad keywords; 9 candidates with scripts/references/assets |
| P1 | `ai-llm` | 39.30 | 11 | 0 | 0 | no explicit role split; 1 shared broad keywords; 4 tool-like primary candidates; 6 candidates with scripts/references/assets |
| P1 | `science-clinical-regulatory` | 37.70 | 7 | 0 | 0 | no explicit role split; 1 shared broad keywords; 5 tool-like primary candidates; 7 candidates with scripts/references/assets |
| P1 | `code-quality` | 37.00 | 10 | 9 | 1 | 9 route authorities; 3 suspected overlap pairs; 2 candidates with scripts/references/assets |
| P1 | `docs-media` | 37.00 | 8 | 8 | 0 | 8 route authorities; 1 suspected overlap pairs; 5 tool-like primary candidates; 5 candidates with scripts/references/assets |
| P1 | `finance-edgar-macro` | 35.90 | 7 | 0 | 0 | no explicit role split; 5 tool-like primary candidates; 7 candidates with scripts/references/assets |
| P1 | `data-ml` | 29.40 | 8 | 7 | 1 | 7 route authorities; 1 tool-like primary candidates; 7 candidates with scripts/references/assets |
| P1 | `science-medical-imaging` | 28.30 | 5 | 0 | 0 | no explicit role split; 1 shared broad keywords; 5 candidates with scripts/references/assets |
| P1 | `aios-core` | 16.40 | 12 | 1 | 11 | 12 skill candidates; 1 suspected overlap pairs; 1 tool-like primary candidates |
| P1 | `science-quantum` | 15.80 | 4 | 0 | 0 | 3 shared broad keywords; 3 tool-like primary candidates; 4 candidates with scripts/references/assets |
| P1 | `media-video` | 15.30 | 3 | 3 | 0 | 3 tool-like primary candidates; 3 candidates with scripts/references/assets |
| P1 | `science-figures-visualization` | 15.10 | 5 | 2 | 3 | 1 shared broad keywords; 1 tool-like primary candidates; 4 candidates with scripts/references/assets |

## P2

| priority | pack | score | skills | route authority | stage assistant | rationale |
|---|---|---:|---:|---:|---:|---|
| P2 | `science-reporting` | 13.30 | 5 | 2 | 3 | 1 tool-like primary candidates; 4 candidates with scripts/references/assets |
| P2 | `ml-torch-geometric` | 12.00 | 2 | 0 | 0 | 1 suspected overlap pairs; 4 shared broad keywords; 1 candidates with scripts/references/assets |
| P2 | `ruc-nlpir-augmentation` | 11.40 | 4 | 2 | 2 | 1 shared broad keywords; 2 candidates with scripts/references/assets |
| P2 | `science-geospatial` | 9.30 | 3 | 0 | 0 | 1 shared broad keywords; 2 tool-like primary candidates; 3 candidates with scripts/references/assets |
| P2 | `science-zarr-polars` | 9.00 | 4 | 0 | 0 | 1 shared broad keywords; 1 tool-like primary candidates; 3 candidates with scripts/references/assets |
| P2 | `science-peer-review` | 8.70 | 3 | 0 | 0 | 3 tool-like primary candidates; 3 candidates with scripts/references/assets |
| P2 | `web-scraping` | 4.60 | 2 | 0 | 0 | 1 tool-like primary candidates; 2 candidates with scripts/references/assets |
| P2 | `screen-capture` | 3.90 | 1 | 1 | 0 | 1 candidates with scripts/references/assets |
| P2 | `docs-markitdown-conversion` | 2.90 | 1 | 0 | 0 | 1 tool-like primary candidates; 1 candidates with scripts/references/assets |
| P2 | `ip-uspto-patents` | 2.90 | 1 | 0 | 0 | 1 tool-like primary candidates; 1 candidates with scripts/references/assets |
| P2 | `ml-stable-baselines3` | 2.90 | 1 | 0 | 0 | 1 tool-like primary candidates; 1 candidates with scripts/references/assets |
| P2 | `science-fluidsim-cfd` | 2.90 | 1 | 0 | 0 | 1 tool-like primary candidates; 1 candidates with scripts/references/assets |
| P2 | `science-pymoo-optimization` | 2.90 | 1 | 0 | 0 | 1 tool-like primary candidates; 1 candidates with scripts/references/assets |
| P2 | `science-rowan-chemistry` | 2.90 | 1 | 0 | 0 | 1 tool-like primary candidates; 1 candidates with scripts/references/assets |
| P2 | `science-simpy-simulation` | 2.90 | 1 | 0 | 0 | 1 tool-like primary candidates; 1 candidates with scripts/references/assets |
| P2 | `science-astropy` | 1.70 | 1 | 0 | 0 | 1 candidates with scripts/references/assets |
| P2 | `science-matchms-spectra` | 1.70 | 1 | 0 | 0 | 1 candidates with scripts/references/assets |
| P2 | `science-matlab-octave` | 1.70 | 1 | 0 | 0 | 1 candidates with scripts/references/assets |
| P2 | `science-neuropixels` | 1.70 | 1 | 0 | 0 | 1 candidates with scripts/references/assets |
| P2 | `science-pymatgen` | 1.70 | 1 | 0 | 0 | 1 candidates with scripts/references/assets |
| P2 | `science-pymc-bayesian` | 1.70 | 1 | 0 | 0 | 1 candidates with scripts/references/assets |
| P2 | `science-timesfm-forecasting` | 1.70 | 1 | 0 | 0 | 1 candidates with scripts/references/assets |
| P2 | `cloud-modalcom` | 0.90 | 1 | 0 | 0 | low structural risk |
| P2 | `science-tiledbvcf` | 0.90 | 1 | 0 | 0 | low structural risk |

## 边界说明

- 本报告只说明治理优先级，不代表删除建议。
- 具体 pack 收敛需要下一轮 problem-first 设计。
- 带 scripts、references、examples 或 assets 的 skill 不能直接删除。
- 若后续修改路由，需要补对应 route regression probe。
