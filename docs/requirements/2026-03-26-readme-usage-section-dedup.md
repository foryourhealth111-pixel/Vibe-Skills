# README Usage Section Dedup Requirement

## Goal

Remove the duplicated usage subsection from the English and Chinese READMEs where the same `/vibe` invocation idea is already covered later in the getting-started area.

## Deliverable

- updated [`README.md`](../../../README.md)
- updated [`README.zh.md`](../../../README.zh.md)

## Constraints

- keep the install section concise
- preserve the single public install entry wording
- remove only the duplicated usage subsection, not the surrounding install or customize sections

## Acceptance Criteria

1. `README.md` no longer contains `### Usage: No need to remember any skill names`.
2. `README.zh.md` no longer contains `### 使用：不需要记住任何技能名称`.
3. The duplicated genomics example snippet is removed from both files.
4. The install section flows directly from install entry to customize guidance.
