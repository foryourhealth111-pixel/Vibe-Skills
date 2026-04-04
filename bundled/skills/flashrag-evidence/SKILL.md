---
name: flashrag-evidence
description: "Local evidence retrieval (FlashRAG-style) for VCO/vibe: search protocols/config/skills docs and return citeable snippets with file+line anchors."
---

# FlashRAG Evidence (VCO)

## When to use

Use this skill when you need **grounded, citeable evidence** from local documentation/configuration to support VCO decisions or recommendations, especially for:

- VCO routing / pack selection rationale
- Protocol compliance (think/do/review/team/retro)
- Config semantics (thresholds, overlays, governance)
- “Show me where this rule comes from” / “give me the exact snippet”

This skill is **not** a replacement for GitNexus (code dependency graph) or web search. It focuses on **local docs and config**.

## Inputs

- Query: what you’re trying to verify (short, concrete)
- Optional: corpus root(s) to search (defaults below)

## Default corpus (evidence plane)

1. VCO core docs/config inside `~/.codex/skills/vibe/`:
   - `protocols/`, `config/`, `references/`, `scripts/router/`
2. Skills catalog (`~/.codex/skills/**/SKILL.md`) for tool capability evidence
3. (Optional) Project-local VCO overlays under the current workspace, if present

## Workflow (Lite, no heavy deps)

1. Run the evidence retriever script:

   - Windows PowerShell:
     - `python C:\Users\羽裳\.codex\skills\flashrag-evidence\scripts\flashrag_evidence.py --query "…" --topk 8`

2. (Optional) Enable a faster FlashRAG-style BM25 backend (`bm25s`)

   - Preflight:
     - validate vendoring and runtime env manually before using the optional bm25s path
   - Manually create an isolated venv for the vendored runtime and install only the minimal packages you need. The old `install-upstreams.ps1` auto-install path has been removed on purpose.
   - Use bm25s engine:
     - `C:\Users\羽裳\.codex\_external\ruc-nlpir\.venv\Scripts\python.exe C:\Users\羽裳\.codex\skills\flashrag-evidence\scripts\flashrag_evidence.py --engine bm25s --query "…" --topk 8`

3. Use the returned snippets as P5 evidence:
   - **[Command]** the exact command you ran
   - **[Output]** the top snippets (path + line anchor)
   - **[Claim]** the conclusion you draw (only what the evidence supports)

4. If coverage is low:
   - Expand `--roots` to include the project workspace
   - Increase `--topk`
   - Fallback: targeted `rg -n` on the most likely file(s)

## Outputs

The script prints ranked evidence items:

- `path` + `line` (1-based) for quick navigation
- `score` for ranking
- `snippet` (short, safe to quote)

## Notes (non-redundancy)

- If you need **code call chains / blast radius**, use GitNexus overlays (not this).
- If you need **latest web facts**, use web search / deep research tools (not this).
