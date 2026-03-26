# README Usage Section Dedup Plan

## Scope

Make a narrow README cleanup in English and Chinese by removing the duplicated usage subsection from the install area.

## Steps

1. Locate the duplicated usage subsection in [`README.md`](../../../README.md) and [`README.zh.md`](../../../README.zh.md).
2. Remove the subsection title, explanatory text, and example block in both files.
3. Verify the install section now moves directly from install entry to customize guidance.

## Verification

- `git diff -- README.md README.zh.md docs/requirements/2026-03-26-readme-usage-section-dedup.md docs/plans/2026-03-26-readme-usage-section-dedup-plan.md`
- `git diff --check -- README.md README.zh.md docs/requirements/2026-03-26-readme-usage-section-dedup.md docs/plans/2026-03-26-readme-usage-section-dedup-plan.md`
- `rg -n "Usage: No need to remember any skill names|使用：不需要记住任何技能名称|genomics analysis pipeline|基因组分析流程" README.md README.zh.md`
