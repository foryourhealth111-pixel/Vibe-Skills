# Skills Overlap Matrix

This matrix profiles high-overlap skills in VCO routing and classifies each pair as:
- `equivalent`: near-substitutable for the same task intent
- `complementary`: similar domain but different phase/depth/scope
- `conflicting`: workflow or governance assumptions can collide if selected together

Scoring uses the overlap of `When to Use`, `Boundaries`, and declared workflow/tool dependencies from each `SKILL.md`.

## Pairwise Matrix

| Skill Pair | Overlap Score | Class | Evidence (When/Boundary/Dependency) | Recommended Routing Strategy |
|---|---:|---|---|---|
| `code-review` ↔ `code-reviewer` | 0.89 | equivalent | Both target PR/code review quality; both include lint/style/issue finding. | Put in `equivalent_group=code-review-core`; canonical review skill = `code-reviewer`. |
| `code-reviewer` ↔ `reviewing-code` | 0.86 | equivalent | Both review code quality/correctness; `reviewing-code` emphasizes API/maintainability tone. | Same group; bias to `code-reviewer` for generic review, keep `reviewing-code` for maintainability-heavy wording. |
| `create-plan` ↔ `writing-plans` | 0.82 | equivalent | Both produce plans; `writing-plans` is multi-step/spec-oriented. | Same `equivalent_group=plan-authoring`; canonical planning skill = `writing-plans`. |
| `build-error-resolver` ↔ `error-resolver` | 0.95 | equivalent | `build-error-resolver` explicitly aliases to `error-resolver` workflow. | Always alias to canonical flow; keep build-specific keywords for entry. |
| `openai-docs` ↔ `openai-knowledge` | 0.88 | equivalent | Both require OpenAI docs MCP and up-to-date OpenAI platform/API facts. | Same `equivalent_group=openai-docs-surface`; canonical research skill = `openai-docs`. |
| `systematic-debugging` ↔ `debugging-strategies` | 0.73 | complementary | Both debug, but `systematic-debugging` enforces strict root-cause gate; `debugging-strategies` is broader and includes profiling/distributed debugging. | For bug/test failure choose `systematic-debugging`; for performance/profiling wording boost `debugging-strategies`. |
| `systematic-debugging` ↔ `error-resolver` | 0.71 | complementary | Both root-cause oriented; `error-resolver` adds 5-step error taxonomy and replay patterns. | Keep both in debug; use stack trace/error-code language to boost `error-resolver`. |
| `writing-plans` ↔ `planning-with-files` | 0.68 | complementary | Both planning; `planning-with-files` requires task artifacts (`task_plan.md`, `findings.md`, `progress.md`). | Planning default stays `writing-plans`; when file-based planning terms hit, route to `planning-with-files`. |
| `docs-write` ↔ `writing-docs` | 0.66 | conflicting | Both documentation authoring, but style systems differ (Metabase vs Remotion). | Hard-filter by repo/context keywords; add mutual negative keywords to avoid cross-repo misroute. |
| `docs-write` ↔ `docs-review` | 0.58 | complementary | Same docs domain, but write vs review phases differ. | Task hard-filter: `planning/coding/research` -> write, `review` -> `docs-review`. |
| `spreadsheet` ↔ `xlsx` | 0.77 | complementary | Both spreadsheet editing; `spreadsheet` general data workflow, `xlsx` includes strict model/finance formatting constraints. | Same `equivalent_group=tabular-processing`; use finance/model keywords to boost `xlsx`. |
| `doc` ↔ `docx` | 0.75 | complementary | Both DOCX operations; `doc` emphasizes layout fidelity rendering loop, `docx` adds OOXML/redlining tracked-change workflow. | Same `equivalent_group=doc-authoring`; tracked-changes/legal wording boosts `docx`. |
| `figma` ↔ `figma-implement-design` | 0.79 | complementary | Both require Figma MCP; `figma` is integration/setup + context fetch, `figma-implement-design` is production implementation workflow. | Use setup/troubleshooting wording for `figma`; code generation/1:1 fidelity wording for `figma-implement-design`. |
| `hypothesis-testing` ↔ `property-based-testing` | 0.72 | complementary | Both property-based testing; one Python/Hypothesis-centric, one JS/TS + Python cross-stack. | Same `equivalent_group=property-testing`; language keywords decide (`python` -> Hypothesis, `fast-check` -> property-based-testing). |
| `research-lookup` ↔ `comprehensive-research-agent` | 0.64 | complementary | Both research; `research-lookup` focuses retrieval, `comprehensive-research-agent` adds validation/error-recovery rigor. | Retrieval queries -> `research-lookup`; multi-step rigor/completeness wording boosts `comprehensive-research-agent`. |
| `scientific-writing` ↔ `content-research-writer` | 0.61 | complementary | Both writing with research; `scientific-writing` is manuscript/IMRAD specific. | Scientific paper/manuscript wording routes to `scientific-writing`; general article/content routes to `content-research-writer`. |
| `security-reviewer` ↔ `security-best-practices` | 0.57 | complementary | Both security, but one is audit/review and one is best-practice guidance. | `review/debug` security incidents -> `security-reviewer`; secure-by-default guidance -> `security-best-practices`. |
| `mcp-integration` ↔ `documentation-lookup` | 0.43 | complementary | Both may touch docs, but `mcp-integration` is MCP setup/integration specific. | Add negative keywords to prevent generic docs questions from selecting MCP integration. |
| `vibe` ↔ `aios-master` | 0.67 | conflicting | Both orchestration-level control planes and command systems. | Treat as mutually exclusive orchestrators per task; explicit user command decides. |
| `writing-plans` ↔ `aios-pm` | 0.55 | complementary | Both planning-heavy; `aios-pm` targets PRD/roadmap/product decisions, `writing-plans` targets implementation execution plans. | Product-planning keywords (`prd`, `epic`, `backlog`) route to `aios-pm`; implementation breakdown routes to `writing-plans`. |
| `code-reviewer` ↔ `aios-qa` | 0.59 | complementary | Both quality review; `aios-qa` is quality-gate persona with risk/NFR framing. | General code review -> `code-reviewer`; quality gate/risk matrix wording -> `aios-qa`. |

## Routing Policy Derived From This Matrix

1. Use `equivalent_group` + `canonical_for_task` to stabilize top-1 for true duplicates.
2. Use `task_allow` hard filter first, then `positive_keywords` and `negative_keywords` for complementary pairs.
3. For conflicting orchestrators (`vibe`, `aios-master`), keep explicit command priority and avoid automatic co-selection.
4. When top-1/top-2 separation is small, require confirmation instead of opportunistic auto-route.

## Notes

- This matrix intentionally focuses on high-impact overlaps (routing instability hot zones), not every possible pair in the repository.
- As new skills are added, append pair rows and update equivalent/conflict groups before enabling stricter routing gates.
