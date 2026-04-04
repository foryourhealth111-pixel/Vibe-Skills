---
name: webthinker-deep-research
description: "Deep web research for VCO: multi-hop search+browse+extract with an auditable action trace and a structured report (WebThinker-style)."
---

# WebThinker Deep Research (VCO)

## When to use

Use this skill when the task requires **deep web research** (not just one-shot search), for example:

- Multi-hop questions (“find → open → follow links → verify”)
- “Deep research report” / “调研报告” / “竞品调研” / “技术调研”
- Need an **auditable trace** of web actions and sources
- Need to merge findings into a structured deliverable (report / brief / spec)

## Non-goals (avoid redundancy)

- For **quick citations** or “give me 3 sources”, prefer `research-lookup`.
- For **interactive UI flows** (login / forms / downloads), prefer `playwright` or `turix-cua` overlays.
- For **codebase structure / call chains**, prefer GitNexus overlays (not web research).

## Output contract (must)

Produce a folder with:

- `report.md` — structured report (problem → findings → implications → next steps)
- `sources.json` — all sources (URL/title/access time/snippet)
- `trace.jsonl` — append-only action trace (search/open/extract/decision)
- `notes.md` — working notes with per-source anchors

Use `scripts/init_webthinker_run.py` to scaffold the folder.

## Runtime (Upstream vendoring)

This VCO skill supports a **stable Lite mode** by default, and keeps the upstream WebThinker repo **vendored** for optional advanced use.

- Vendored upstream paths:
  - `C:\Users\羽裳\.codex\_external\ruc-nlpir\WebThinker\`
- Runtime config (no secrets stored):
  - `C:\Users\羽裳\.codex\skills\vibe\config\ruc-nlpir-runtime.json`
- Preflight / install (no secrets echoed):
  - validate vendoring and runtime env manually before enabling the optional upstream path
  - Manually create an isolated venv for the vendored runtime and install only the minimal packages you need. The old `install-upstreams.ps1` auto-install path has been removed on purpose.

LLM endpoint conventions (recommended):

- Base URL: `OPENAI_BASE_URL` (or runtime default)
- API key: `OPENAI_API_KEY` (**env var only; never write into files or CLI args**)

## Modes

### Mode A (Recommended): Lite — tool-orchestrated deep research

Use existing tools (no heavy model hosting):

1. Scaffold outputs:
   - `python C:\Users\羽裳\.codex\skills\webthinker-deep-research\scripts\init_webthinker_run.py --topic "…" --out outputs/webthinker`
2. Search (broad → narrow):
   - Use `web.run` search queries or `mcp__tavily__tavily_search` if available.
3. Browse/extract:
   - Use `web.run open/click/find` for structured pages
   - Use `playwright` when pages require dynamic rendering / interactions
4. Draft + iterate:
   - Update `notes.md` and `sources.json` continuously
   - Write `report.md` as you go (think-search-and-draft), not only at the end
5. Verification:
   - Triangulate key claims across ≥2 sources when possible
   - Flag uncertainties explicitly

### Mode B (Optional): Full WebThinker stack

Only choose this if you want to run the upstream system end-to-end and you have the environment:

- Requires heavy deps (`torch`, `transformers`, `vllm`) + a served reasoning model
- Requires a search API (Serper recommended by upstream)
- Optional: Crawl4AI parser client for JS-heavy pages

This mode is for **high-throughput** deep research runs; for most VCO tasks, Lite mode is enough and cheaper.

## Action trace format (trace.jsonl)

Each line is one JSON object, e.g.:

- `{"ts":"…","type":"search","query":"…","provider":"web.run"}`
- `{"ts":"…","type":"open","url":"…"}`
- `{"ts":"…","type":"extract","url":"…","highlights":["…","…"]}`
- `{"ts":"…","type":"decision","reason":"why this source matters","next":"…"}`

## Quality gates

- Every major claim in `report.md` links back to at least one entry in `sources.json`.
- `sources.json` contains the exact URLs you used (no “I saw somewhere…”).
- Keep the report actionable: add “Next steps” with concrete verification tasks.
