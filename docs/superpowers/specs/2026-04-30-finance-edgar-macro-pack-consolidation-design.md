# Finance-EDGAR-Macro Pack Consolidation Design

日期：2026-04-30

## 1. 目标

本轮只治理 `finance-edgar-macro` pack 的第二轮收敛。

目标不是重做六阶段 Vibe runtime，也不是引入阶段助手、辅助专家、咨询态或主/次技能。总体架构继续保持：

```text
candidate skill -> selected skill -> used / unused
```

本轮目标是：

- 保留 `finance-edgar-macro` 当前 7 个直接 route owner。
- 把 7 个 owner 的用户任务边界写清楚。
- 收窄容易误触发的宽泛关键词，尤其是 `datacommons-client` 和 `market-research-reports`。
- 补充 pack 专属治理记录和 pack 专属测试。
- 确认 finance 数据源任务不会落到 generic science reporting / literature / docs routes。
- 确认 generic public data、generic report writing、PubMed/clinical/bio evidence 不会误进 finance pack。

本轮不物理删除 skill 目录。7 个候选都有 scripts、references 或较重文档资产，不能以“精简”为理由直接删。

## 2. 当前状态

当前 `config/pack-manifest.json` 中，`finance-edgar-macro` 为：

| 项目 | 当前值 |
|---|---:|
| `skill_candidates` | 7 |
| `route_authority_candidates` | 7 |
| `stage_assistant_candidates` | 0 |
| `defaults_by_task` | 3 |

当前直接 route owner：

```text
edgartools
alpha-vantage
fred-economic-data
usfiscaldata
hedgefundmonitor
market-research-reports
datacommons-client
```

当前默认任务映射：

```json
{
  "planning": "market-research-reports",
  "coding": "edgartools",
  "research": "edgartools"
}
```

这说明该 pack 已经不再是旧的 `0 route authority` 状态。它在 `zero-route-authority` 清理中已经被提升为 7 个直接 owner、0 个阶段助手。

## 3. 当前问题

### 3.1 只有零 route owner 修复，没有 pack 专属二次治理

现有治理记录 `docs/governance/zero-route-authority-pack-consolidation-2026-04-29.md` 只说明 `finance-edgar-macro` 从 0 个 route owner 修复为 7 个直接 owner。

现有回归覆盖也主要分布在：

```text
tests/runtime_neutral/test_zero_route_authority_pack_consolidation.py
scripts/verify/probe-scientific-packs.ps1
scripts/verify/vibe-skill-index-routing-audit.ps1
scripts/verify/vibe-pack-regression-matrix.ps1
```

这些能证明基本 direct owner 能命中，但还没有 pack 专属 problem map、误触发边界和治理记录。

### 3.2 `research -> edgartools` 默认过强

`edgartools` 是 SEC/EDGAR/filing 的强 owner，但不是所有金融研究的默认答案。

当前 `research` 默认到 `edgartools` 会带来两个风险：

- 用户只说“金融研究 / 市场研究 / 宏观研究”时，容易偏向 SEC filing。
- FRED、Treasury Fiscal Data、Data Commons 这类公共宏观/财政/统计数据源被弱化。

本轮不一定必须改默认值，但必须用 keyword/rule 和 regression 保护：只有出现 EDGAR、SEC、10-K、10-Q、8-K、13F、XBRL、上市公司官方披露、财报提取等明确触发时，才稳定选 `edgartools`。

### 3.3 `datacommons-client` 触发词太泛

`datacommons-client` 当前关键词包含：

```text
public data
open data
公共数据
开放数据
```

Data Commons 本身覆盖人口、经济、健康、环境等统计图谱。但放在 `finance-edgar-macro` 中，它不能吃掉所有“公共数据 / 开放数据”任务。

目标边界是：

- 明确提到 `Data Commons` / `datacommons` 时，稳定命中 `datacommons-client`。
- 提到人口经济指标、public statistical data、population indicators 等统计图谱任务时，可以命中。
- 泛泛的“公共数据下载 / 开放数据整理 / public dataset search”不能稳定进入 finance pack。

### 3.4 `market-research-reports` 和报告/论文写作类 pack 交叉

`market-research-reports` 是市场研究/行业报告/competitive analysis 的 owner，不是普通 scientific report、paper writing、PDF build 或 Markdown/HTML report owner。

它已经有一些负向关键词：

```text
edgar
sec
10-k
10q
xbrl
fred
cpi
alpha vantage
treasury
fiscal data
hedge fund monitor
data commons
```

本轮应继续强化这个方向：

- 市场研究报告、行业分析、竞争格局、consulting-style report -> `market-research-reports`
- 科研报告、论文写作、LaTeX/PDF 构建、实验结果报告 -> 不应进入 `finance-edgar-macro`
- SEC filing / FRED / Treasury / Data Commons 数据查询 -> 不应被 `market-research-reports` 抢走

### 3.5 FRED 与 U.S. Fiscal Data 有宏观语义交叉

`fred-economic-data` 与 `usfiscaldata` 都可能涉及 macro、interest rate、fiscal、government finance。

目标边界是：

| skill | 边界 |
|---|---|
| `fred-economic-data` | FRED、Federal Reserve Economic Data、CPI、PCE、GDP、unemployment、Fed funds rate、宏观经济时间序列 |
| `usfiscaldata` | U.S. Treasury Fiscal Data、national debt、federal spending、deficit、Treasury securities、Daily/Monthly Treasury Statement |

如果用户明确说 FRED，就不能落到 `usfiscaldata`。如果用户明确说 U.S. Treasury Fiscal Data、national debt、federal spending，就不能落到 `fred-economic-data`。

## 4. 范围

本轮可以处理：

```text
config/pack-manifest.json
config/skill-keyword-index.json
config/skill-routing-rules.json
config/skills-lock.json
bundled/skills/edgartools/**
bundled/skills/alpha-vantage/**
bundled/skills/fred-economic-data/**
bundled/skills/usfiscaldata/**
bundled/skills/hedgefundmonitor/**
bundled/skills/market-research-reports/**
bundled/skills/datacommons-client/**
tests/runtime_neutral/test_finance_edgar_macro_pack_consolidation.py
scripts/verify/probe-scientific-packs.ps1
scripts/verify/vibe-skill-index-routing-audit.ps1
scripts/verify/vibe-pack-regression-matrix.ps1
docs/governance/finance-edgar-macro-pack-consolidation-2026-04-30.md
```

本轮不处理：

- `bio-science`
- `code-quality`
- `data-ml`
- `docs-media`
- `science-medical-imaging`
- `science-reporting`
- `scholarly-publishing-workflow`
- 六阶段 Vibe runtime
- installed Codex host 部署
- 真实任务中的 material skill use 证明

## 5. 不做什么

本轮明确不做：

- 不新增 `stage_assistant_candidates`。
- 不新增“辅助专家”“咨询专家”“主技能/次技能”状态。
- 不拆分 `finance-edgar-macro` 为多个新 pack。
- 不把 `datacommons-client` 移出 pack。
- 不把 `market-research-reports` 移到 science reporting。
- 不物理删除 7 个保留 skill。
- 不把所有金融研究都默认解释成 EDGAR/SEC filing。
- 不声称这些 skills 已在真实 Vibe 任务中被物质使用。

## 6. 目标架构

目标仍是 7 个直接 owner，0 个阶段助手。

| problem_id | 用户问题 | 目标 owner |
|---|---|---|
| `sec_filing_analysis` | EDGAR、SEC filing、10-K、10-Q、8-K、13F、XBRL、上市公司披露、财报表格提取 | `edgartools` |
| `market_price_data` | Alpha Vantage、股票价格、OHLCV、技术指标、market data、行情 CSV | `alpha-vantage` |
| `macro_timeseries` | FRED、CPI、PCE、GDP、unemployment、Fed funds rate、宏观时间序列 | `fred-economic-data` |
| `us_treasury_fiscal_data` | U.S. Treasury Fiscal Data、national debt、federal spending、deficit、Treasury securities | `usfiscaldata` |
| `hedge_fund_monitoring` | OFR Hedge Fund Monitor、Form PF aggregated statistics、对冲基金监测 | `hedgefundmonitor` |
| `market_research_report` | 市场研究报告、行业报告、competitive analysis、consulting-style report | `market-research-reports` |
| `datacommons_statistical_graph` | Data Commons、datacommons、public statistical data、population/economic indicators | `datacommons-client` |

目标 `finance-edgar-macro` 保持：

```text
skill_candidates = 7
route_authority_candidates = 7
stage_assistant_candidates = 0
```

## 7. 路由边界设计

### 7.1 `edgartools`

稳定触发：

```text
EDGAR
SEC
10-K
10-Q
8-K
13F
XBRL
company filings
annual report from SEC
上市公司财报
美国证监会披露
```

负向边界：

```text
Alpha Vantage
FRED
Treasury Fiscal Data
Data Commons
market research report
PubMed
clinical trials
```

### 7.2 `alpha-vantage`

稳定触发：

```text
Alpha Vantage
alphavantage
stock price
OHLCV
technical indicators
daily price
intraday
美股行情
股票时间序列
```

负向边界：

```text
SEC filing
10-K
FRED
Treasury Fiscal Data
Data Commons
scientific report
```

### 7.3 `fred-economic-data`

稳定触发：

```text
FRED
Federal Reserve Economic Data
CPI
PCE
GDP
unemployment
Fed funds rate
interest rate time series
宏观经济时间序列
```

负向边界：

```text
U.S. Treasury Fiscal Data
national debt
federal spending
SEC filing
stock price
Data Commons
```

### 7.4 `usfiscaldata`

稳定触发：

```text
U.S. Treasury Fiscal Data
FiscalData Treasury
national debt
federal spending
deficit
Treasury securities
Daily Treasury Statement
Monthly Treasury Statement
国债
美国财政支出
```

负向边界：

```text
FRED
CPI from FRED
stock price
SEC filing
market research report
```

### 7.5 `hedgefundmonitor`

稳定触发：

```text
OFR Hedge Fund Monitor
Form PF aggregate statistics
hedge fund monitor
对冲基金监测
```

负向边界：

```text
13F holdings
SEC filing
market research report
stock price
```

13F 属于 SEC filing/holdings 路径，优先 `edgartools`。Form PF aggregated statistics / OFR monitor 才属于 `hedgefundmonitor`。

### 7.6 `market-research-reports`

稳定触发：

```text
market research report
industry report
competitive analysis
consulting-style report
市场研究
行业报告
市场调研
竞争格局分析
```

负向边界：

```text
EDGAR
SEC
10-K
XBRL
FRED
Alpha Vantage
Treasury Fiscal Data
Data Commons
scientific report
paper writing
LaTeX
PDF build
```

### 7.7 `datacommons-client`

稳定触发：

```text
Data Commons
datacommons
public statistical data
population indicators
economic indicators in Data Commons
人口经济指标
```

负向边界：

```text
generic public data
open dataset search
PubMed
NCBI
clinical data
SEC filing
FRED
Treasury Fiscal Data
```

`public data` 和 `open data` 这类短词不应单独作为强触发；需要和 Data Commons、statistical variables、population/economic indicators 等上下文绑定。

## 8. 回归设计

需要保留或新增这些正向 probes：

| prompt | 应命中 |
|---|---|
| `用 EDGAR 拉取 AAPL 10-K，提取收入/毛利率/分部信息并输出表格` | `finance-edgar-macro / edgartools` |
| `用 Alpha Vantage 获取 AAPL 日线行情并输出 CSV` | `finance-edgar-macro / alpha-vantage` |
| `用 FRED 获取 CPI 和联邦基金利率时间序列，并画趋势图` | `finance-edgar-macro / fred-economic-data` |
| `用 U.S. Treasury Fiscal Data 查询 national debt 和 federal spending` | `finance-edgar-macro / usfiscaldata` |
| `查询 OFR Hedge Fund Monitor 和 Form PF aggregate statistics` | `finance-edgar-macro / hedgefundmonitor` |
| `生成 consulting-style market research report 和 competitive analysis` | `finance-edgar-macro / market-research-reports` |
| `用 Data Commons 查询 public statistical data 和人口经济指标` | `finance-edgar-macro / datacommons-client` |

需要新增这些负向 probes：

| prompt | 不应命中 |
|---|---|
| `搜索公共数据集，整理下载链接，不限定 Data Commons 或人口经济指标` | 不应稳定命中 `finance-edgar-macro / datacommons-client` |
| `写一篇科研报告，包含 methods/results/discussion 并导出 PDF` | 不应命中 `finance-edgar-macro / market-research-reports` |
| `写 LaTeX 论文并构建 submission PDF` | 不应命中 `market-research-reports` |
| `查询 PubMed 文献并整理证据表` | 不应命中 `finance-edgar-macro` |
| `从 ClinicalTrials.gov 查询 NCT 试验` | 不应命中 `finance-edgar-macro` |
| `用 FRED 获取 CPI` | 不应命中 `usfiscaldata` |
| `用 U.S. Treasury Fiscal Data 查 national debt` | 不应命中 `fred-economic-data` |
| `查询 SEC 13F holdings` | 不应命中 `hedgefundmonitor` |

## 9. 审计设计

新增 pack 专属审计测试：

```text
tests/runtime_neutral/test_finance_edgar_macro_pack_consolidation.py
```

该测试应检查：

- `skill_candidates` 正好是 7 个保留 owner。
- `route_authority_candidates` 正好是同一组 7 个 owner。
- `stage_assistant_candidates == []`。
- 默认任务映射存在且 owner 均在候选集中。
- `datacommons-client` 不把 generic `public data` / `open data` 作为无条件强触发。
- `market-research-reports` 对 EDGAR/FRED/Treasury/Data Commons/scientific writing/LaTeX/PDF 有负向边界。
- `edgartools`、`fred-economic-data`、`usfiscaldata`、`hedgefundmonitor` 的关键边界有明确正负关键词。

如有必要，可新增轻量 audit helper；但优先保持简单，用 runtime-neutral test 直接读取 JSON 配置即可。

## 10. 文档设计

新增治理记录：

```text
docs/governance/finance-edgar-macro-pack-consolidation-2026-04-30.md
```

治理记录应包含：

- 当前 7 个 direct route owner。
- 每个 owner 的用户问题边界。
- 明确写出 `stage_assistant_candidates = 0`。
- 明确写出本轮不删除 skill 目录。
- 记录 `datacommons-client` 和 `market-research-reports` 的误触发修复。
- 记录验证命令和结果。
- 明确边界：本轮证明的是 routing/config/bundled cleanup，不证明真实任务中的 material skill use。

## 11. 验证设计

实现后至少运行：

```powershell
python -m pytest tests/runtime_neutral/test_finance_edgar_macro_pack_consolidation.py -q
.\scripts\verify\probe-scientific-packs.ps1
.\scripts\verify\vibe-skill-index-routing-audit.ps1
.\scripts\verify\vibe-pack-regression-matrix.ps1
.\scripts\verify\vibe-pack-routing-smoke.ps1
.\scripts\verify\vibe-generate-skills-lock.ps1
.\scripts\verify\vibe-offline-skills-gate.ps1
git diff --check
```

如果修改了 `skills-lock.json`，需要确认：

```text
present_skills == lock_skills
```

如果没有物理删除 skill 目录，`skill_count` 不应因为本轮变化下降。

## 12. 风险和缓解

| 风险 | 缓解 |
|---|---|
| 把所有金融研究都推给 `edgartools` | 收窄 EDGAR/SEC filing 的强触发，并为 FRED/Treasury/Data Commons/market report 补正向 probes。 |
| `datacommons-client` 吞掉所有公共数据任务 | 移除或弱化 generic public/open data 强触发，要求 Data Commons 或统计图谱上下文。 |
| `market-research-reports` 抢科研报告/论文/PDF 任务 | 增加 scientific report、paper writing、LaTeX、PDF build 的负向边界。 |
| FRED 与 Treasury Fiscal Data 互相抢路由 | 用数据源名和指标类型划清：FRED 宏观时间序列，Treasury FiscalData 财政/国债/证券数据。 |
| 为精简而误删资产重 skill | 本轮不删除 7 个保留 skill，只做边界硬化。 |
| 回归只覆盖正向命中，不覆盖误触发 | 新增负向 route probes 和 pack 专属测试。 |

## 13. 成功标准

本轮完成后应满足：

- `finance-edgar-macro.skill_candidates` 保持 7 个。
- `finance-edgar-macro.route_authority_candidates` 保持 7 个。
- `finance-edgar-macro.stage_assistant_candidates = []`。
- 7 个 owner 均有清楚的问题边界。
- `datacommons-client` 不再被 generic public/open data 单独强触发。
- `market-research-reports` 不抢 scientific report、paper writing、LaTeX/PDF 构建任务。
- EDGAR/FRED/Treasury/OFR/Alpha Vantage/Data Commons/market report 正向 probes 通过。
- 关键负向 probes 通过。
- governance note 记录本轮结论和验证结果。
- 最终报告区分“routing/config/bundled cleanup”与“真实任务中的 material skill use”。
