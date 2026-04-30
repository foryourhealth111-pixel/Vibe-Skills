# Finance-EDGAR-Macro Pack Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden `finance-edgar-macro` routing boundaries while keeping the current 7 direct owners and zero stage assistants.

**Architecture:** Keep the existing Vibe six-stage runtime unchanged and keep the simplified routing model as `candidate skill -> selected skill -> used / unused`. The implementation only adjusts route evidence, skill trigger text, pack-specific tests, verification scripts, and governance notes for `finance-edgar-macro`; it does not add advisory experts, main/sub-skill state, or stage assistants.

**Tech Stack:** Python `unittest`/`pytest`, PowerShell verification scripts, JSON route configuration, bundled Markdown skill docs, skills lock generation, Git.

---

## Scope

This plan implements the approved design in `docs/superpowers/specs/2026-04-30-finance-edgar-macro-pack-consolidation-design.md`.

Keep these 7 direct route owners:

```text
edgartools
alpha-vantage
fred-economic-data
usfiscaldata
hedgefundmonitor
market-research-reports
datacommons-client
```

Keep this pack invariant:

```text
skill_candidates = 7
route_authority_candidates = 7
stage_assistant_candidates = []
```

Do not physically delete any `bundled/skills/*` directory in this pass.

Do not claim real task material skill use from these changes. This work proves routing/config/bundled-doc cleanup and regression coverage only.

## File Map

- Create `tests/runtime_neutral/test_finance_edgar_macro_pack_consolidation.py`: pack-specific route/config/doc regression tests.
- Modify `config/skill-keyword-index.json`: narrow finance skill keyword triggers, especially `datacommons-client`.
- Modify `config/skill-routing-rules.json`: add positive and negative route boundaries for all 7 finance owners.
- Modify `bundled/skills/datacommons-client/SKILL.md`: add a routing boundary note that generic public/open data is insufficient.
- Modify `bundled/skills/market-research-reports/SKILL.md`: remove historical cross-skill invocation hints and constrain the skill to market/industry/competitive reports.
- Review and modify only if needed:
  - `bundled/skills/edgartools/SKILL.md`
  - `bundled/skills/alpha-vantage/SKILL.md`
  - `bundled/skills/fred-economic-data/SKILL.md`
  - `bundled/skills/usfiscaldata/SKILL.md`
  - `bundled/skills/hedgefundmonitor/SKILL.md`
- Modify `scripts/verify/vibe-pack-regression-matrix.ps1`: add finance positive and negative route cases.
- Modify `scripts/verify/vibe-skill-index-routing-audit.ps1`: add missing finance positive cases and blocked finance cases.
- Leave `scripts/verify/probe-scientific-packs.ps1` positive finance cases in place; add negative finance cases only if the script's existing assertion shape supports blocked-pack/blocked-skill checks cleanly.
- Create `docs/governance/finance-edgar-macro-pack-consolidation-2026-04-30.md`: pack governance note with results.
- Modify `config/skills-lock.json`: refresh after bundled skill file edits.

## Task 1: Add Failing Pack-Specific Tests

**Files:**
- Create: `tests/runtime_neutral/test_finance_edgar_macro_pack_consolidation.py`

- [ ] **Step 1: Create the test file**

Create `tests/runtime_neutral/test_finance_edgar_macro_pack_consolidation.py` with this exact content:

```python
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "runtime-core" / "src"))

from vgo_runtime.router_contract_runtime import route_prompt  # noqa: E402


FINANCE_SKILLS = [
    "edgartools",
    "alpha-vantage",
    "fred-economic-data",
    "usfiscaldata",
    "hedgefundmonitor",
    "market-research-reports",
    "datacommons-client",
]


def route(prompt: str, task_type: str = "research", grade: str = "M") -> dict[str, object]:
    return route_prompt(prompt=prompt, grade=grade, task_type=task_type, repo_root=REPO_ROOT)


def selected(result: dict[str, object]) -> tuple[str, str]:
    selected_row = result.get("selected")
    assert isinstance(selected_row, dict), result
    return str(selected_row.get("pack_id") or ""), str(selected_row.get("skill") or "")


def ranked_summary(result: dict[str, object]) -> list[tuple[str, str, float, str]]:
    ranked = result.get("ranked")
    assert isinstance(ranked, list), result
    rows: list[tuple[str, str, float, str]] = []
    for row in ranked[:8]:
        assert isinstance(row, dict), row
        rows.append(
            (
                str(row.get("pack_id") or ""),
                str(row.get("selected_candidate") or ""),
                float(row.get("score") or 0.0),
                str(row.get("candidate_selection_reason") or ""),
            )
        )
    return rows


def pack_by_id(pack_id: str) -> dict[str, object]:
    manifest_path = REPO_ROOT / "config" / "pack-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    packs = manifest.get("packs")
    assert isinstance(packs, list), manifest
    for pack in packs:
        assert isinstance(pack, dict), pack
        if pack.get("id") == pack_id:
            return pack
    raise AssertionError(f"pack missing: {pack_id}")


def skill_keywords(skill_id: str) -> list[str]:
    path = REPO_ROOT / "config" / "skill-keyword-index.json"
    index = json.loads(path.read_text(encoding="utf-8-sig"))
    skill = index.get("skills", {}).get(skill_id)
    assert isinstance(skill, dict), skill_id
    keywords = skill.get("keywords")
    assert isinstance(keywords, list), skill
    return [str(keyword).lower() for keyword in keywords]


def routing_rule(skill_id: str) -> dict[str, object]:
    path = REPO_ROOT / "config" / "skill-routing-rules.json"
    rules = json.loads(path.read_text(encoding="utf-8-sig"))
    skill = rules.get("skills", {}).get(skill_id)
    assert isinstance(skill, dict), skill_id
    return skill


def positive_keywords(skill_id: str) -> list[str]:
    keywords = routing_rule(skill_id).get("positive_keywords")
    assert isinstance(keywords, list), skill_id
    return [str(keyword).lower() for keyword in keywords]


def negative_keywords(skill_id: str) -> list[str]:
    keywords = routing_rule(skill_id).get("negative_keywords")
    assert isinstance(keywords, list), skill_id
    return [str(keyword).lower() for keyword in keywords]


def skill_body(skill_id: str) -> str:
    path = REPO_ROOT / "bundled" / "skills" / skill_id / "SKILL.md"
    text = path.read_text(encoding="utf-8-sig")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            return parts[2].lower()
    return text.lower()


class FinanceEdgarMacroPackConsolidationTests(unittest.TestCase):
    def assert_selected(
        self,
        prompt: str,
        expected_pack: str,
        expected_skill: str,
        *,
        task_type: str = "research",
        grade: str = "M",
    ) -> None:
        result = route(prompt, task_type=task_type, grade=grade)
        self.assertEqual((expected_pack, expected_skill), selected(result), ranked_summary(result))

    def assert_not_selected(
        self,
        prompt: str,
        blocked_pack: str | None = None,
        blocked_skill: str | None = None,
        *,
        task_type: str = "research",
        grade: str = "M",
    ) -> None:
        result = route(prompt, task_type=task_type, grade=grade)
        chosen_pack, chosen_skill = selected(result)
        if blocked_pack is not None:
            self.assertNotEqual(blocked_pack, chosen_pack, ranked_summary(result))
        if blocked_skill is not None:
            self.assertNotEqual(blocked_skill, chosen_skill, ranked_summary(result))

    def test_manifest_keeps_seven_direct_owners_and_no_stage_assistants(self) -> None:
        pack = pack_by_id("finance-edgar-macro")
        self.assertEqual(FINANCE_SKILLS, pack.get("skill_candidates"))
        self.assertEqual(FINANCE_SKILLS, pack.get("route_authority_candidates"))
        self.assertEqual([], pack.get("stage_assistant_candidates"))
        defaults = pack.get("defaults_by_task")
        self.assertIsInstance(defaults, dict)
        for task_name in ["planning", "coding", "research"]:
            self.assertIn(defaults.get(task_name), FINANCE_SKILLS, defaults)

    def test_finance_positive_routes_hit_direct_owners(self) -> None:
        self.assert_selected(
            "用 EDGAR 拉取 AAPL 10-K，提取收入/毛利率/分部信息并输出表格",
            "finance-edgar-macro",
            "edgartools",
        )
        self.assert_selected(
            "用 Alpha Vantage 获取 AAPL 日线 OHLCV 行情和 technical indicators 并输出 CSV",
            "finance-edgar-macro",
            "alpha-vantage",
            task_type="coding",
        )
        self.assert_selected(
            "用 FRED 获取 CPI、PCE、GDP、unemployment 和 fed funds rate 时间序列",
            "finance-edgar-macro",
            "fred-economic-data",
        )
        self.assert_selected(
            "用 U.S. Treasury Fiscal Data 查询 national debt、federal spending 和 deficit",
            "finance-edgar-macro",
            "usfiscaldata",
        )
        self.assert_selected(
            "查询 OFR Hedge Fund Monitor 和 Form PF aggregate statistics",
            "finance-edgar-macro",
            "hedgefundmonitor",
        )
        self.assert_selected(
            "生成 consulting-style market research report、industry report 和 competitive analysis",
            "finance-edgar-macro",
            "market-research-reports",
            task_type="planning",
        )
        self.assert_selected(
            "用 Data Commons 查询 public statistical data、statistical variables 和人口经济指标",
            "finance-edgar-macro",
            "datacommons-client",
        )

    def test_generic_public_data_does_not_select_datacommons_client(self) -> None:
        self.assert_not_selected(
            "搜索公共数据集和 open dataset 下载链接，不限定 Data Commons 或人口经济指标",
            blocked_pack="finance-edgar-macro",
            blocked_skill="datacommons-client",
        )

    def test_scientific_and_publishing_reports_do_not_select_market_research(self) -> None:
        self.assert_not_selected(
            "写一篇科研报告，包含 methods results discussion 并导出 PDF",
            blocked_pack="finance-edgar-macro",
            blocked_skill="market-research-reports",
            task_type="planning",
            grade="L",
        )
        self.assert_not_selected(
            "写 LaTeX 论文并用 latexmk 构建 submission PDF",
            blocked_skill="market-research-reports",
            task_type="coding",
            grade="XL",
        )

    def test_biomedical_literature_and_clinical_prompts_do_not_select_finance(self) -> None:
        self.assert_not_selected(
            "查询 PubMed 文献并整理 evidence table 和 PMID citations",
            blocked_pack="finance-edgar-macro",
        )
        self.assert_not_selected(
            "从 ClinicalTrials.gov 查询 NCT01234567 试验终点和入排标准",
            blocked_pack="finance-edgar-macro",
        )

    def test_fred_and_treasury_do_not_cross_select_each_other(self) -> None:
        self.assert_not_selected(
            "用 FRED 获取 CPI from FRED 和 Federal Reserve Economic Data 时间序列",
            blocked_skill="usfiscaldata",
        )
        self.assert_not_selected(
            "用 U.S. Treasury Fiscal Data 查 national debt 和 federal spending",
            blocked_skill="fred-economic-data",
        )

    def test_sec_13f_does_not_select_hedgefundmonitor(self) -> None:
        self.assert_selected(
            "查询 SEC 13F holdings 和 institutional holdings",
            "finance-edgar-macro",
            "edgartools",
        )
        self.assert_not_selected(
            "查询 SEC 13F holdings 和 institutional holdings",
            blocked_skill="hedgefundmonitor",
        )

    def test_keyword_index_removes_broad_datacommons_triggers(self) -> None:
        keywords = skill_keywords("datacommons-client")
        self.assertNotIn("public data", keywords)
        self.assertNotIn("open data", keywords)
        self.assertNotIn("公共数据", keywords)
        self.assertNotIn("开放数据", keywords)
        for required in [
            "data commons",
            "datacommons",
            "public statistical data",
            "population indicators",
            "economic indicators",
            "statistical variables",
            "人口经济指标",
            "统计变量",
        ]:
            self.assertIn(required, keywords)

    def test_routing_rules_encode_finance_owner_boundaries(self) -> None:
        expected_negative = {
            "edgartools": [
                "alpha vantage",
                "fred",
                "treasury fiscal data",
                "data commons",
                "market research report",
                "pubmed",
                "clinicaltrials",
            ],
            "alpha-vantage": [
                "sec filing",
                "10-k",
                "fred",
                "treasury fiscal data",
                "data commons",
                "scientific report",
            ],
            "fred-economic-data": [
                "u.s. treasury fiscal data",
                "national debt",
                "federal spending",
                "sec filing",
                "stock price",
                "data commons",
            ],
            "usfiscaldata": [
                "fred",
                "cpi from fred",
                "federal reserve economic data",
                "stock price",
                "sec filing",
                "market research report",
            ],
            "hedgefundmonitor": [
                "13f",
                "13f holdings",
                "sec filing",
                "market research report",
                "stock price",
            ],
            "market-research-reports": [
                "scientific report",
                "paper writing",
                "latex",
                "pdf build",
                "submission pdf",
                "pubmed",
                "clinicaltrials",
                "data commons",
            ],
            "datacommons-client": [
                "generic public data",
                "open dataset search",
                "pubmed",
                "ncbi",
                "clinical data",
                "sec filing",
                "fred",
                "treasury fiscal data",
            ],
        }
        for skill_id, required_terms in expected_negative.items():
            with self.subTest(skill_id=skill_id):
                negatives = negative_keywords(skill_id)
                for term in required_terms:
                    self.assertIn(term, negatives)

    def test_kept_skill_docs_do_not_inline_cross_call_other_skills(self) -> None:
        market_body = skill_body("market-research-reports")
        forbidden_market_phrases = [
            "deep integration with research-lookup",
            "use `research-lookup`",
            "use research-lookup",
            "use `scientific-schematics`",
            "use scientific-schematics",
            "use `generate-image`",
            "use generate-image",
            "use the peer-review skill",
            "works synergistically with",
            "integration with other skills",
        ]
        for phrase in forbidden_market_phrases:
            self.assertNotIn(phrase, market_body)

        datacommons_body = skill_body("datacommons-client")
        self.assertIn("generic public data", datacommons_body)
        self.assertIn("not enough", datacommons_body)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the focused test and confirm it fails before implementation**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_finance_edgar_macro_pack_consolidation.py -q
```

Expected result before implementation:

```text
FAILED
```

Expected failures include at least:

```text
test_keyword_index_removes_broad_datacommons_triggers
test_routing_rules_encode_finance_owner_boundaries
test_kept_skill_docs_do_not_inline_cross_call_other_skills
```

The route negative tests may also fail before implementation. That is acceptable; do not weaken the test to make current behavior pass.

- [ ] **Step 3: Commit the failing test**

Run:

```powershell
git add tests/runtime_neutral/test_finance_edgar_macro_pack_consolidation.py
git diff --cached --check
git commit -m "test: add finance edgar macro consolidation coverage"
```

Expected result:

```text
Git creates a commit with message: test: add finance edgar macro consolidation coverage
```

## Task 2: Harden Finance Keyword Index and Routing Rules

**Files:**
- Modify: `config/skill-keyword-index.json`
- Modify: `config/skill-routing-rules.json`
- Test: `tests/runtime_neutral/test_finance_edgar_macro_pack_consolidation.py`

- [ ] **Step 1: Update `config/skill-keyword-index.json` finance entries**

Replace the finance skill keyword blocks with these exact arrays:

```json
"edgartools": {
  "keywords": ["edgar", "sec", "sec filing", "10-k", "10-q", "10q", "8-k", "13f", "xbrl", "company filings", "annual report from sec", "财报", "美国证监会", "上市公司披露"]
},
"alpha-vantage": {
  "keywords": ["alpha vantage", "alphavantage", "stock price", "ohlcv", "technical indicators", "daily price", "intraday", "market data", "美股行情", "股票数据", "股票时间序列"]
},
"fred-economic-data": {
  "keywords": ["fred", "federal reserve economic data", "cpi", "pce", "gdp", "unemployment", "fed funds rate", "interest rate time series", "inflation", "宏观数据", "宏观经济时间序列", "经济数据", "利率"]
},
"usfiscaldata": {
  "keywords": ["u.s. treasury fiscal data", "us treasury fiscal data", "fiscaldata treasury", "us fiscal data", "national debt", "federal spending", "deficit", "treasury securities", "daily treasury statement", "monthly treasury statement", "财政数据", "美国财政", "国债", "美国财政支出"]
},
"hedgefundmonitor": {
  "keywords": ["ofr hedge fund monitor", "hedge fund monitor", "form pf aggregate statistics", "form pf aggregated statistics", "ofr", "hedge fund", "对冲基金", "对冲基金监测"]
},
"market-research-reports": {
  "keywords": ["market research report", "market research", "industry report", "competitive analysis", "consulting-style report", "consulting-style market research report", "consulting report", "market sizing", "tam sam som", "市场研究", "行业报告", "市场调研", "竞争格局分析", "咨询式报告"]
},
"datacommons-client": {
  "keywords": ["data commons", "datacommons", "public statistical data", "population indicators", "economic indicators", "statistical variables", "data commons statistical variables", "data commons population", "人口经济指标", "统计变量"]
}
```

Check that these standalone keywords are not present in `datacommons-client`:

```text
public data
open data
公共数据
开放数据
```

- [ ] **Step 2: Update `config/skill-routing-rules.json` finance entries**

In the top-level `"skills"` object, replace each of these 7 finance skill objects with the following exact objects. Preserve the surrounding JSON structure and commas.

```json
"edgartools": {
  "task_allow": ["research", "coding"],
  "positive_keywords": [
    "edgar",
    "sec",
    "sec filing",
    "10-k",
    "10-q",
    "10q",
    "13f",
    "13f holdings",
    "8-k",
    "xbrl",
    "company filings",
    "annual report from sec",
    "财报",
    "美国证监会",
    "上市公司披露"
  ],
  "negative_keywords": [
    "pubmed",
    "pmid",
    "ncbi geo",
    "gene expression omnibus",
    "gse",
    "gsm",
    "gene expression",
    "alpha vantage",
    "alphavantage",
    "fred",
    "federal reserve economic data",
    "treasury fiscal data",
    "u.s. treasury fiscal data",
    "data commons",
    "datacommons",
    "market research report",
    "scientific report",
    "clinicaltrials",
    "clinical trials"
  ],
  "equivalent_group": "finance-data",
  "canonical_for_task": ["research", "coding"]
},
"alpha-vantage": {
  "task_allow": ["research", "coding"],
  "positive_keywords": [
    "alpha vantage",
    "alphavantage",
    "stock price",
    "ohlcv",
    "technical indicators",
    "daily price",
    "intraday",
    "market data",
    "美股行情",
    "股票数据",
    "股票时间序列"
  ],
  "negative_keywords": [
    "pubmed",
    "pmid",
    "sec filing",
    "edgar",
    "10-k",
    "10-q",
    "xbrl",
    "fred",
    "federal reserve economic data",
    "treasury fiscal data",
    "u.s. treasury fiscal data",
    "data commons",
    "datacommons",
    "scientific report"
  ],
  "equivalent_group": "finance-data",
  "canonical_for_task": []
},
"fred-economic-data": {
  "task_allow": ["research", "coding"],
  "positive_keywords": [
    "fred",
    "federal reserve economic data",
    "cpi",
    "pce",
    "gdp",
    "unemployment",
    "fed funds rate",
    "interest rate time series",
    "inflation",
    "宏观数据",
    "宏观经济时间序列",
    "经济数据",
    "利率"
  ],
  "negative_keywords": [
    "pubmed",
    "pmid",
    "u.s. treasury fiscal data",
    "us treasury fiscal data",
    "treasury fiscal data",
    "fiscaldata treasury",
    "national debt",
    "federal spending",
    "daily treasury statement",
    "monthly treasury statement",
    "sec filing",
    "edgar",
    "stock price",
    "alpha vantage",
    "data commons",
    "datacommons"
  ],
  "equivalent_group": "finance-data",
  "canonical_for_task": ["research"]
},
"usfiscaldata": {
  "task_allow": ["research", "coding"],
  "positive_keywords": [
    "u.s. treasury fiscal data",
    "us treasury fiscal data",
    "fiscaldata treasury",
    "us fiscal data",
    "national debt",
    "federal spending",
    "deficit",
    "treasury securities",
    "daily treasury statement",
    "monthly treasury statement",
    "财政数据",
    "国债",
    "美国财政支出"
  ],
  "negative_keywords": [
    "pubmed",
    "pmid",
    "fred",
    "cpi from fred",
    "federal reserve economic data",
    "stock price",
    "alpha vantage",
    "sec filing",
    "edgar",
    "market research report"
  ],
  "equivalent_group": "finance-data",
  "canonical_for_task": ["research"]
},
"hedgefundmonitor": {
  "task_allow": ["research", "coding"],
  "positive_keywords": [
    "ofr hedge fund monitor",
    "hedge fund monitor",
    "form pf aggregate statistics",
    "form pf aggregated statistics",
    "ofr",
    "hedge fund",
    "对冲基金",
    "对冲基金监测"
  ],
  "negative_keywords": [
    "pubmed",
    "pmid",
    "13f",
    "13f holdings",
    "sec filing",
    "edgar",
    "market research report",
    "stock price",
    "alpha vantage"
  ],
  "equivalent_group": "finance-data",
  "canonical_for_task": ["research"]
},
"market-research-reports": {
  "task_allow": ["planning", "research"],
  "positive_keywords": [
    "market research report",
    "market research",
    "industry report",
    "competitive analysis",
    "consulting-style report",
    "consulting-style market research report",
    "consulting report",
    "market sizing",
    "tam sam som",
    "市场研究",
    "行业报告",
    "市场调研",
    "竞争格局分析",
    "咨询式报告"
  ],
  "negative_keywords": [
    "pubmed",
    "pmid",
    "clinicaltrials",
    "clinical trials",
    "edgar",
    "sec",
    "sec filing",
    "10-k",
    "10q",
    "xbrl",
    "fred",
    "cpi",
    "alpha vantage",
    "treasury",
    "treasury fiscal data",
    "fiscal data",
    "hedge fund monitor",
    "data commons",
    "datacommons",
    "scientific report",
    "technical report",
    "paper writing",
    "manuscript",
    "latex",
    "pdf build",
    "submission pdf"
  ],
  "equivalent_group": "finance-strategy",
  "canonical_for_task": ["planning"]
},
"datacommons-client": {
  "task_allow": ["research", "coding"],
  "positive_keywords": [
    "data commons",
    "datacommons",
    "public statistical data",
    "population indicators",
    "economic indicators",
    "statistical variables",
    "data commons statistical variables",
    "data commons population",
    "人口经济指标",
    "统计变量"
  ],
  "negative_keywords": [
    "pubmed",
    "pmid",
    "ncbi",
    "clinical data",
    "generic public data",
    "open dataset search",
    "public dataset search",
    "sec filing",
    "edgar",
    "fred",
    "federal reserve economic data",
    "treasury fiscal data",
    "u.s. treasury fiscal data",
    "market research report"
  ],
  "equivalent_group": "public-data",
  "canonical_for_task": ["research", "coding"]
}
```

- [ ] **Step 3: Validate JSON syntax**

Run:

```powershell
python -m json.tool config/skill-keyword-index.json > $null
python -m json.tool config/skill-routing-rules.json > $null
```

Expected result:

```text
no output and exit code 0
```

- [ ] **Step 4: Run focused tests**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_finance_edgar_macro_pack_consolidation.py -q
```

Expected result at this point:

```text
some route/doc tests may still fail, but JSON syntax and keyword/rule boundary assertions should pass
```

- [ ] **Step 5: Commit JSON route hardening**

Run:

```powershell
git add config/skill-keyword-index.json config/skill-routing-rules.json
git diff --cached --check
git commit -m "fix: harden finance edgar macro route boundaries"
```

Expected result:

```text
Git creates a commit with message: fix: harden finance edgar macro route boundaries
```

## Task 3: Clean Kept Skill Docs Without Adding Cross-Skill Hints

**Files:**
- Modify: `bundled/skills/datacommons-client/SKILL.md`
- Modify: `bundled/skills/market-research-reports/SKILL.md`
- Review: `bundled/skills/edgartools/SKILL.md`
- Review: `bundled/skills/alpha-vantage/SKILL.md`
- Review: `bundled/skills/fred-economic-data/SKILL.md`
- Review: `bundled/skills/usfiscaldata/SKILL.md`
- Review: `bundled/skills/hedgefundmonitor/SKILL.md`
- Test: `tests/runtime_neutral/test_finance_edgar_macro_pack_consolidation.py`

- [ ] **Step 1: Add a routing boundary section to `datacommons-client`**

In `bundled/skills/datacommons-client/SKILL.md`, after the `## Overview` paragraph, insert:

```markdown
## Routing Boundary

Use this skill when the user explicitly asks for Data Commons/datacommons, Data Commons statistical variables, Data Commons entities/DCIDs, or population/economic indicators that fit the Data Commons knowledge graph.

Generic public data, open data, public dataset search, or public download-link collection by itself is not enough to select this skill. Those requests need a clearer Data Commons/statistical-graph signal before this skill becomes the route owner.
```

- [ ] **Step 2: Replace the `market-research-reports` frontmatter description**

In `bundled/skills/market-research-reports/SKILL.md`, replace the current `description:` value with:

```yaml
description: Generate comprehensive market research reports and industry/competitive analysis in the style of top consulting firms. Use for market sizing, competitive landscape, market entry, investment thesis, strategic recommendations, and consulting-style business reports. Do not use for scientific reports, paper writing, LaTeX submission/PDF builds, EDGAR/FRED/Treasury/Data Commons data retrieval, or biomedical literature evidence work.
```

- [ ] **Step 3: Replace the `market-research-reports` key features block**

In `bundled/skills/market-research-reports/SKILL.md`, replace the current `**Key Features:**` bullet list with:

```markdown
**Key Features:**
- **Comprehensive length**: Reports are designed to be 50+ pages with no token constraints
- **Visual-rich content**: Plan the core market, competitive, risk, and roadmap visuals before drafting
- **Data-driven analysis**: Ground market claims in cited public, company, industry, and government sources
- **Multi-framework approach**: Porter's Five Forces, PESTLE, SWOT, BCG Matrix, TAM/SAM/SOM
- **Professional formatting**: Consulting-firm quality typography, colors, and layout
- **Actionable recommendations**: Strategic focus with implementation roadmaps
```

- [ ] **Step 4: Insert a routing boundary section into `market-research-reports`**

In `bundled/skills/market-research-reports/SKILL.md`, immediately after `## When to Use This Skill`, insert:

```markdown
## Routing Boundary

Use this skill for market research report, industry report, competitive analysis, market sizing, market entry, due diligence, investment thesis, and consulting-style strategic report tasks.

Do not use this skill for:

- Scientific reports, technical reports, IMRAD papers, or experimental results reports
- LaTeX manuscript construction, submission PDF builds, journal templates, or paper packaging
- EDGAR/SEC filings, 10-K/10-Q/XBRL/13F extraction
- FRED macro time series
- U.S. Treasury Fiscal Data, national debt, federal spending, or deficit queries
- Data Commons statistical graph queries
- PubMed, ClinicalTrials.gov, biomedical evidence tables, or literature reviews
```

- [ ] **Step 5: Replace cross-skill visual generation wording**

In `bundled/skills/market-research-reports/SKILL.md`, replace the section from `## Visual Enhancement Requirements` through the end of `### Visual Generation Tools` with:

```markdown
## Visual Enhancement Requirements

Market research reports should include key visual content. Plan 6 essential visuals at the start, then add only the visuals required by the report's actual sections.

Use the repository's available figure-generation or plotting approach for the current execution environment. Do not route to, invoke, or inline another skill from inside this skill document. Treat visual creation as part of this market-report deliverable, not as an auxiliary expert call.

Recommended starting visuals:

- Market growth trajectory chart
- TAM/SAM/SOM breakdown diagram
- Porter's Five Forces diagram
- Competitive positioning matrix
- Risk heatmap
- Executive summary infographic or dashboard
```

Keep the later table `### Recommended Visuals by Section (Generate as Needed)` if it still reads as deliverable guidance. Remove any command examples that call paths such as:

```text
skills/scientific-schematics/scripts/generate_schematic.py
skills/generate-image/scripts/generate_image.py
```

- [ ] **Step 6: Replace research lookup workflow wording**

In `bundled/skills/market-research-reports/SKILL.md`, replace any instruction that says to use or call `research-lookup` with source-collection wording:

```markdown
Gather market data from relevant public, company, government, industry association, and academic sources. Store source notes under `sources/`, record citations, and mark unsupported claims as assumptions.
```

Remove command examples that call:

```text
skills/research-lookup/scripts/research_lookup.py
```

- [ ] **Step 7: Replace the integration section**

Replace the `## Integration with Other Skills` section with:

```markdown
## Boundary With Neighboring Work

This skill produces market and industry strategy reports. It can include citations, figures, and LaTeX/PDF output as part of the market-report deliverable, but those are internal deliverable requirements here and not a signal to invoke another skill.

Route scientific reports, journal manuscripts, submission packages, generic PDF extraction, and biomedical literature evidence work to their own direct owners outside this skill.
```

- [ ] **Step 8: Check for remaining cross-skill call hints**

Run:

```powershell
rg -n "research-lookup|scientific-schematics|generate-image|peer-review|works synergistically|Integration with Other Skills" bundled/skills/market-research-reports/SKILL.md
```

Expected result:

```text
no matches
```

- [ ] **Step 9: Check the other finance skill docs for cross-skill route hints**

Run:

```powershell
rg -n "Integration with Other Skills|works synergistically|use .* skill|research-lookup|scientific-schematics|generate-image|peer-review" bundled/skills/edgartools/SKILL.md bundled/skills/alpha-vantage/SKILL.md bundled/skills/fred-economic-data/SKILL.md bundled/skills/usfiscaldata/SKILL.md bundled/skills/hedgefundmonitor/SKILL.md
```

Expected result:

```text
no matches, or only prose that describes a library feature instead of calling another Vibe skill
```

If a matched line tells the agent to call another Vibe skill, rewrite it into direct deliverable guidance and rerun the command.

- [ ] **Step 10: Run focused tests**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_finance_edgar_macro_pack_consolidation.py -q
```

Expected result:

```text
all doc and config assertions pass; route assertions pass or identify one remaining route score conflict to fix in Task 4
```

- [ ] **Step 11: Commit skill doc cleanup**

Run:

```powershell
git add bundled/skills/datacommons-client/SKILL.md bundled/skills/market-research-reports/SKILL.md bundled/skills/edgartools/SKILL.md bundled/skills/alpha-vantage/SKILL.md bundled/skills/fred-economic-data/SKILL.md bundled/skills/usfiscaldata/SKILL.md bundled/skills/hedgefundmonitor/SKILL.md
git diff --cached --check
git commit -m "docs: clarify finance skill routing boundaries"
```

If the review files did not change, Git will stage only the changed files. Confirm with `git status --short` before committing.

Expected result:

```text
Git creates a commit with message: docs: clarify finance skill routing boundaries
```

## Task 4: Extend Route Verification Scripts

**Files:**
- Modify: `scripts/verify/vibe-pack-regression-matrix.ps1`
- Modify: `scripts/verify/vibe-skill-index-routing-audit.ps1`
- Optionally modify: `scripts/verify/probe-scientific-packs.ps1`

- [ ] **Step 1: Add finance cases to `vibe-pack-regression-matrix.ps1`**

In the `$cases = @(` list near the existing finance cases, replace the two current finance rows with this block:

```powershell
    [pscustomobject]@{ Name = "finance edgar direct owner"; Prompt = "用 EDGAR 拉取 AAPL 10-K 并解析 XBRL financial statements"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "finance-edgar-macro"; ExpectedSkill = "edgartools"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "finance alpha vantage direct owner"; Prompt = "用 Alpha Vantage 获取 AAPL 日线 OHLCV 行情和 technical indicators 并输出 CSV"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "finance-edgar-macro"; ExpectedSkill = "alpha-vantage"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "finance fred direct owner"; Prompt = "用 FRED 获取 CPI PCE GDP unemployment 和 fed funds rate 时间序列"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "finance-edgar-macro"; ExpectedSkill = "fred-economic-data"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "finance treasury fiscal direct owner"; Prompt = "用 U.S. Treasury Fiscal Data 查询 national debt federal spending 和 deficit"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "finance-edgar-macro"; ExpectedSkill = "usfiscaldata"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "finance hedge fund monitor direct owner"; Prompt = "查询 OFR Hedge Fund Monitor 和 Form PF aggregate statistics"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "finance-edgar-macro"; ExpectedSkill = "hedgefundmonitor"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "finance market report direct owner"; Prompt = "生成 consulting-style market research report industry report 和 competitive analysis"; Grade = "M"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = "finance-edgar-macro"; ExpectedSkill = "market-research-reports"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "finance data commons direct owner"; Prompt = "用 Data Commons 查询 public statistical data statistical variables 和人口经济指标"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "finance-edgar-macro"; ExpectedSkill = "datacommons-client"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "finance blocks generic public data"; Prompt = "搜索公共数据集和 open dataset 下载链接，不限定 Data Commons 或人口经济指标"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "finance-edgar-macro"; BlockedSkill = "datacommons-client"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "finance blocks scientific report pdf"; Prompt = "写一篇科研报告，包含 methods results discussion 并导出 PDF"; Grade = "L"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "finance-edgar-macro"; BlockedSkill = "market-research-reports"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "finance blocks latex submission pdf"; Prompt = "写 LaTeX 论文并用 latexmk 构建 submission PDF"; Grade = "XL"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "scholarly-publishing-workflow"; ExpectedSkill = "latex-submission-pipeline"; BlockedSkill = "market-research-reports"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "finance blocks pubmed evidence"; Prompt = "查询 PubMed 文献并整理 evidence table 和 PMID citations"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "finance-edgar-macro"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "finance blocks clinicaltrials nct"; Prompt = "从 ClinicalTrials.gov 查询 NCT01234567 试验终点和入排标准"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "finance-edgar-macro"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "finance fred not us fiscal"; Prompt = "用 FRED 获取 CPI from FRED 和 Federal Reserve Economic Data 时间序列"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "finance-edgar-macro"; ExpectedSkill = "fred-economic-data"; BlockedSkill = "usfiscaldata"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "finance treasury not fred"; Prompt = "用 U.S. Treasury Fiscal Data 查 national debt 和 federal spending"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "finance-edgar-macro"; ExpectedSkill = "usfiscaldata"; BlockedSkill = "fred-economic-data"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "finance sec 13f not hedgefundmonitor"; Prompt = "查询 SEC 13F holdings 和 institutional holdings"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "finance-edgar-macro"; ExpectedSkill = "edgartools"; BlockedSkill = "hedgefundmonitor"; AllowedModes = @("pack_overlay", "confirm_required") },
```

- [ ] **Step 2: Add missing finance audit cases to `vibe-skill-index-routing-audit.ps1`**

Near the existing finance rows, replace the current three finance rows with:

```powershell
    [pscustomobject]@{ Name = "finance edgar"; Prompt = "用 EDGAR 拉取 AAPL 10-K 并解析 XBRL financial statements"; Grade = "M"; TaskType = "research"; ExpectedPack = "finance-edgar-macro"; ExpectedSkill = "edgartools" },
    [pscustomobject]@{ Name = "finance alpha vantage"; Prompt = "用 Alpha Vantage 获取 AAPL 日线 OHLCV 行情和 technical indicators 并输出 CSV"; Grade = "M"; TaskType = "coding"; ExpectedPack = "finance-edgar-macro"; ExpectedSkill = "alpha-vantage" },
    [pscustomobject]@{ Name = "finance fred"; Prompt = "用 FRED 获取 CPI PCE GDP unemployment 和 fed funds rate 时间序列"; Grade = "M"; TaskType = "research"; ExpectedPack = "finance-edgar-macro"; ExpectedSkill = "fred-economic-data" },
    [pscustomobject]@{ Name = "finance us fiscal"; Prompt = "用 U.S. Treasury Fiscal Data 查询 national debt 和 federal spending"; Grade = "M"; TaskType = "research"; ExpectedPack = "finance-edgar-macro"; ExpectedSkill = "usfiscaldata" },
    [pscustomobject]@{ Name = "finance hedge fund monitor"; Prompt = "查询 OFR Hedge Fund Monitor 和 Form PF aggregate statistics"; Grade = "M"; TaskType = "research"; ExpectedPack = "finance-edgar-macro"; ExpectedSkill = "hedgefundmonitor" },
    [pscustomobject]@{ Name = "finance market report"; Prompt = "生成 consulting-style market research report industry report 和 competitive analysis"; Grade = "M"; TaskType = "planning"; ExpectedPack = "finance-edgar-macro"; ExpectedSkill = "market-research-reports" },
    [pscustomobject]@{ Name = "finance data commons"; Prompt = "用 Data Commons 查询 public statistical data statistical variables 和人口经济指标"; Grade = "M"; TaskType = "research"; ExpectedPack = "finance-edgar-macro"; ExpectedSkill = "datacommons-client" },
    [pscustomobject]@{ Name = "finance generic public data blocked"; Prompt = "搜索公共数据集和 open dataset 下载链接，不限定 Data Commons 或人口经济指标"; Grade = "M"; TaskType = "research"; BlockedPack = "finance-edgar-macro"; BlockedSkill = "datacommons-client" },
    [pscustomobject]@{ Name = "finance scientific report blocked"; Prompt = "写一篇科研报告，包含 methods results discussion 并导出 PDF"; Grade = "L"; TaskType = "planning"; BlockedPack = "finance-edgar-macro"; BlockedSkill = "market-research-reports" },
    [pscustomobject]@{ Name = "finance pubmed evidence blocked"; Prompt = "查询 PubMed 文献并整理 evidence table 和 PMID citations"; Grade = "M"; TaskType = "research"; BlockedPack = "finance-edgar-macro" },
    [pscustomobject]@{ Name = "finance clinicaltrials blocked"; Prompt = "从 ClinicalTrials.gov 查询 NCT01234567 试验终点和入排标准"; Grade = "M"; TaskType = "research"; BlockedPack = "finance-edgar-macro" },
```

If the script does not already assert `BlockedSkill`, add this check in the same style as `vibe-pack-regression-matrix.ps1`:

```powershell
    if ($case.BlockedSkill) {
        $results += Assert-True -Condition ($route.selected.skill -ne $case.BlockedSkill) -Message "[$($case.Name)] blocked skill $($case.BlockedSkill) not selected"
    }
```

- [ ] **Step 3: Check whether `probe-scientific-packs.ps1` supports blocked cases**

Run:

```powershell
rg -n "BlockedPack|BlockedSkill|blocked_pack|blocked_skill|expected_pack|expected_skill" scripts/verify/probe-scientific-packs.ps1
```

If it only supports positive `expected_pack` / `expected_skill`, do not add negative cases there. The pack-specific Python test and the two route scripts cover finance negatives.

If it already supports blocked assertions, add these two cases near the finance group:

```powershell
    [pscustomobject]@{
        name = "finance_generic_public_data_blocked"
        group = "finance-edgar-macro"
        prompt = "/vibe 搜索公共数据集和 open dataset 下载链接，不限定 Data Commons 或人口经济指标"
        grade = "M"
        task_type = "research"
        blocked_pack = "finance-edgar-macro"
        blocked_skill = "datacommons-client"
        requested_skill = $null
    },
    [pscustomobject]@{
        name = "finance_scientific_report_pdf_blocked"
        group = "finance-edgar-macro"
        prompt = "/vibe 写一篇科研报告，包含 methods results discussion 并导出 PDF"
        grade = "L"
        task_type = "planning"
        blocked_pack = "finance-edgar-macro"
        blocked_skill = "market-research-reports"
        requested_skill = $null
    },
```

- [ ] **Step 4: Run route script checks**

Run:

```powershell
.\scripts\verify\vibe-pack-regression-matrix.ps1
.\scripts\verify\vibe-skill-index-routing-audit.ps1
```

Expected result:

```text
all cases pass
```

If a route fails because the new prompt now correctly selects a neighboring owner but the script expected `$null`, update the expected pack/skill to the actual correct neighbor only when the neighbor is clearly right. Do not allow `finance-edgar-macro` to own generic public-data, scientific-report, PubMed, or ClinicalTrials prompts.

- [ ] **Step 5: Commit verification script expansion**

Run:

```powershell
git add scripts/verify/vibe-pack-regression-matrix.ps1 scripts/verify/vibe-skill-index-routing-audit.ps1 scripts/verify/probe-scientific-packs.ps1
git diff --cached --check
git commit -m "test: expand finance pack route regressions"
```

If `probe-scientific-packs.ps1` did not change, Git will stage only the changed files. Confirm with `git status --short` before committing.

Expected result:

```text
Git creates a commit with message: test: expand finance pack route regressions
```

## Task 5: Add Governance Note

**Files:**
- Create: `docs/governance/finance-edgar-macro-pack-consolidation-2026-04-30.md`

- [ ] **Step 1: Create the governance note**

Create `docs/governance/finance-edgar-macro-pack-consolidation-2026-04-30.md` with this content:

```markdown
# Finance-EDGAR-Macro Pack Consolidation

Date: 2026-04-30

## Conclusion

`finance-edgar-macro` remains a 7-owner direct routing pack with no stage assistants.

This pass hardens route boundaries for EDGAR/SEC filings, Alpha Vantage market prices, FRED macro time series, U.S. Treasury Fiscal Data, OFR Hedge Fund Monitor, market research reports, and Data Commons statistical graph queries.

This pass does not physically delete any of the 7 retained skill directories.

## Direct Owners

| Problem ID | User Task Boundary | Direct Owner |
|---|---|---|
| `sec_filing_analysis` | EDGAR, SEC filing, 10-K, 10-Q, 8-K, 13F, XBRL, listed-company disclosure, financial statement extraction | `edgartools` |
| `market_price_data` | Alpha Vantage, stock price, OHLCV, technical indicators, intraday/daily price CSV | `alpha-vantage` |
| `macro_timeseries` | FRED, Federal Reserve Economic Data, CPI, PCE, GDP, unemployment, Fed funds rate | `fred-economic-data` |
| `us_treasury_fiscal_data` | U.S. Treasury Fiscal Data, national debt, federal spending, deficit, Treasury securities | `usfiscaldata` |
| `hedge_fund_monitoring` | OFR Hedge Fund Monitor and Form PF aggregate statistics | `hedgefundmonitor` |
| `market_research_report` | Market research report, industry report, competitive analysis, consulting-style strategic report | `market-research-reports` |
| `datacommons_statistical_graph` | Data Commons/datacommons, public statistical data, statistical variables, population/economic indicators | `datacommons-client` |

## Simplified Routing State

```text
candidate skill -> selected skill -> used / unused
```

No extra routing state was added:

```text
stage_assistant_candidates = 0
advisory / consultation state = not used
primary / secondary skill hierarchy = not used
```

## Boundary Fixes

### Data Commons

`datacommons-client` no longer uses standalone `public data`, `open data`, `公共数据`, or `开放数据` as strong keyword-index triggers.

Generic public/open dataset search is not enough to select this skill. The route now needs Data Commons/datacommons, public statistical data, statistical variables, or population/economic indicator context.

### Market Research Reports

`market-research-reports` is limited to market/industry/competitive/consulting-style strategy reports.

It should not own scientific reports, paper writing, LaTeX manuscript construction, submission PDF builds, PubMed evidence tables, ClinicalTrials.gov lookups, EDGAR/FRED/Treasury/Data Commons retrieval, or generic PDF/document tasks.

### FRED vs Treasury Fiscal Data

`fred-economic-data` owns FRED/Federal Reserve Economic Data macro time series.

`usfiscaldata` owns U.S. Treasury Fiscal Data, national debt, federal spending, deficit, and Treasury securities.

Explicit FRED prompts must not select `usfiscaldata`; explicit Treasury Fiscal Data prompts must not select `fred-economic-data`.

### SEC 13F vs OFR Monitor

SEC 13F holdings stay under `edgartools`.

OFR Hedge Fund Monitor and Form PF aggregate statistics stay under `hedgefundmonitor`.

## Verification Results

Run after implementation:

```powershell
python -m pytest tests/runtime_neutral/test_finance_edgar_macro_pack_consolidation.py -q
.\scripts\verify\probe-scientific-packs.ps1
.\scripts\verify\vibe-skill-index-routing-audit.ps1
.\scripts\verify\vibe-pack-regression-matrix.ps1
.\scripts\verify\vibe-pack-routing-smoke.ps1
.\scripts\verify\vibe-offline-skills-gate.ps1
git diff --check
```

Record exact pass counts and any important route snippets here before the final commit.

## Evidence Boundary

This governance note proves routing configuration, bundled skill documentation, tests, and verification scripts were consolidated.

It does not prove that these skills were materially used in a real Vibe task. Material use still requires task-run artifacts such as specialist execution records, produced files, scripts, logs, figures, reports, or final deliverables.
```

- [ ] **Step 2: Commit the initial governance note**

Run:

```powershell
git add docs/governance/finance-edgar-macro-pack-consolidation-2026-04-30.md
git diff --cached --check
git commit -m "docs: record finance edgar macro consolidation"
```

Expected result:

```text
Git creates a commit with message: docs: record finance edgar macro consolidation
```

## Task 6: Refresh Skills Lock

**Files:**
- Modify: `config/skills-lock.json`

- [ ] **Step 1: Regenerate the skills lock**

Run:

```powershell
.\scripts\verify\vibe-generate-skills-lock.ps1
```

Expected result:

```text
skills lock generated successfully
```

The exact count should remain stable for this pass because no skill directory is deleted.

- [ ] **Step 2: Inspect the lock diff**

Run:

```powershell
git diff -- config/skills-lock.json
```

Expected result:

```text
only hashes or metadata tied to edited skill files changed
```

If the diff shows removed skill entries, stop and inspect before committing. This pass does not delete skills.

- [ ] **Step 3: Run the offline skills gate**

Run:

```powershell
.\scripts\verify\vibe-offline-skills-gate.ps1
```

Expected result:

```text
present_skills equals lock_skills
```

- [ ] **Step 4: Commit the refreshed lock**

Run:

```powershell
git add config/skills-lock.json
git diff --cached --check
git commit -m "chore: refresh finance skill lock"
```

Expected result:

```text
Git creates a commit with message: chore: refresh finance skill lock
```

## Task 7: Full Verification and Final Governance Update

**Files:**
- Modify: `docs/governance/finance-edgar-macro-pack-consolidation-2026-04-30.md`

- [ ] **Step 1: Run full verification**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_finance_edgar_macro_pack_consolidation.py -q
.\scripts\verify\probe-scientific-packs.ps1
.\scripts\verify\vibe-skill-index-routing-audit.ps1
.\scripts\verify\vibe-pack-regression-matrix.ps1
.\scripts\verify\vibe-pack-routing-smoke.ps1
.\scripts\verify\vibe-offline-skills-gate.ps1
git diff --check
```

Expected result:

```text
all commands pass
```

- [ ] **Step 2: Update the governance verification section**

Replace the `## Verification Results` section in `docs/governance/finance-edgar-macro-pack-consolidation-2026-04-30.md` with the exact commands and observed pass summaries from Step 1.

Use this format:

```markdown
## Verification Results

Passed on 2026-04-30:

| Command | Result |
|---|---|
| `python -m pytest tests/runtime_neutral/test_finance_edgar_macro_pack_consolidation.py -q` | paste the observed pytest pass summary, for example `12 passed in 1.23s` |
| `.\scripts\verify\probe-scientific-packs.ps1` | paste the observed script pass summary |
| `.\scripts\verify\vibe-skill-index-routing-audit.ps1` | paste the observed script pass summary |
| `.\scripts\verify\vibe-pack-regression-matrix.ps1` | paste the observed script pass summary |
| `.\scripts\verify\vibe-pack-routing-smoke.ps1` | paste the observed script pass summary |
| `.\scripts\verify\vibe-offline-skills-gate.ps1` | paste the observed script pass summary |
| `git diff --check` | `no whitespace errors` |
```

Replace each instruction cell with the actual observed summary text from the command output before committing.

- [ ] **Step 3: Confirm no draft instruction text leaked into committed docs**

Run:

```powershell
rg -n "paste the observed|instruction cell|draft instruction" docs/governance/finance-edgar-macro-pack-consolidation-2026-04-30.md tests/runtime_neutral/test_finance_edgar_macro_pack_consolidation.py config/skill-keyword-index.json config/skill-routing-rules.json bundled/skills/datacommons-client/SKILL.md bundled/skills/market-research-reports/SKILL.md
```

Expected result:

```text
no matches
```

- [ ] **Step 4: Commit final verification evidence**

Run:

```powershell
git add docs/governance/finance-edgar-macro-pack-consolidation-2026-04-30.md
git diff --cached --check
git commit -m "docs: add finance consolidation verification evidence"
```

Expected result:

```text
Git creates a commit with message: docs: add finance consolidation verification evidence
```

## Task 8: Final State Report

**Files:**
- No file changes.

- [ ] **Step 1: Confirm clean worktree and recent commits**

Run:

```powershell
git status --short --branch
git log --oneline -8
```

Expected result:

```text
status output reports branch main against origin/main with a clean worktree
```

and the recent log includes the finance consolidation commits from this plan.

- [ ] **Step 2: Final answer to the user**

Report in Chinese with:

```text
已完成 finance-edgar-macro 的实际整治。

保留：7 个 direct route owner。
保持：stage_assistant_candidates = []。
删除：本轮没有物理删除 skill 目录。
简化状态：仍然是 candidate skill -> selected skill -> used / unused。

已修复：
- datacommons-client 不再吃泛泛 public/open data。
- market-research-reports 不再抢科研报告、论文、LaTeX/PDF、PubMed、ClinicalTrials。
- FRED 与 U.S. Treasury Fiscal Data 边界已加硬。
- SEC 13F 归 edgartools，OFR/Form PF 归 hedgefundmonitor。

已验证：
- list the exact passed commands and summaries from Task 7

边界说明：这证明路由和 bundled skills 清理完成，不证明真实 Vibe 任务中已经 material use。

提交：
- list the commit hashes and messages created during execution
```

Use real output from Task 7 and Task 8. Do not report this work as installed into Codex unless a separate install/deploy task is performed.

## Self-Review Checklist

- [ ] The plan keeps the existing six-stage Vibe runtime unchanged.
- [ ] The plan keeps routing semantics simple: `candidate skill -> selected skill -> used / unused`.
- [ ] The plan does not add `stage_assistant_candidates`, advisory mode, auxiliary experts, or main/sub-skill hierarchy.
- [ ] The plan keeps all 7 finance skills and physically deletes none.
- [ ] The plan adds a failing test before implementation.
- [ ] The plan hardens `datacommons-client` against generic public/open data.
- [ ] The plan hardens `market-research-reports` against scientific report, paper writing, LaTeX/PDF, PubMed, and ClinicalTrials prompts.
- [ ] The plan hardens FRED vs U.S. Treasury Fiscal Data.
- [ ] The plan hardens SEC 13F vs OFR Hedge Fund Monitor.
- [ ] The plan includes focused tests, script regressions, skills lock refresh, and governance evidence.
- [ ] The plan separates routing/config cleanup from real task material skill use.
