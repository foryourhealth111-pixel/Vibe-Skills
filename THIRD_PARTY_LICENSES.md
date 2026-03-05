# Third-Party Licenses and Boundaries

This repository is licensed under **Apache-2.0** (see `LICENSE`).

This file documents notable upstream sources used in the VCO ecosystem and how they are integrated.

## Upstream Sources

| Upstream Project | Upstream License | How VCO Uses It | Distribution Boundary |
|---|---|---|---|
| `SynkraAI/aios-core` | Upstream project license applies | Methodology and role-pattern integration into the `aios-core` pack and routing config | Use follows upstream license terms; review upstream repo for exact obligations |
| `f/prompts.chat` | Upstream project license applies | Prompt asset lookup/refine/publish integration via `prompt-lookup` and `prompt-overlay` policy | Treated as optional external service/MCP capability; review upstream terms before redistribution |
| `GokuMohandas/Made-With-ML` | Upstream project license applies | ML lifecycle methodology source for `ml-lifecycle-overlay` stage/evidence advisory design | Used as governance methodology reference (post-route advisory); review upstream terms before redistribution |
| `zedr/clean-code-python` | Upstream project license applies | Python clean-code methodology source for `python-clean-code-overlay` principle/anti-pattern advisory design | Used as methodology reference (post-route advisory); review upstream terms before redistribution |
| `donnemartin/system-design-primer` | CC BY 4.0 (upstream) | Architecture methodology source for `system-design-overlay` coverage/quality advisory design | Used as methodology reference (post-route advisory); preserve attribution and review CC BY obligations before redistribution |
| `xlite-dev/LeetCUDA` | GPL-3.0 (upstream) | CUDA optimization methodology source for `cuda-kernel-overlay` coverage/evidence advisory design | Methodology-level advisory only; do not vendor/copy upstream GPL source into Apache-2.0 core without separate compliance review |
| `x1xhlol/system-prompts-and-models-of-ai-tools` | GPL-3.0 (upstream) | Read-only external corpus input for signal extraction (`scripts/research/*`) and candidate routing suggestions | Raw upstream prompt corpus is not bundled as distributable VCO runtime content; if mirrored locally under `third_party/`, users are responsible for GPL compliance |
| `muratcankoylan/Agent-Skills-for-Context-Engineering` | MIT (upstream) | Advisory knowledge source for Context Retro Advisor and CER-based retrospectives | Attribution and license notice should be preserved when redistributing derived integrations |
| `SuperClaude-Org/SuperClaude_Framework` | Upstream project license applies | Optional external enhancement (`sc` command compatibility) | Installed optionally; review upstream license before redistribution |
| `ruvnet/claude-flow` | Upstream project license applies | Optional external runtime enhancement | Installed optionally; review upstream license before redistribution |
| `RUC-NLPIR/FlashRAG` | MIT (upstream) | Vendored upstream repo (local clone) used as a reference + optional BM25 backend (`bm25s`) for local evidence retrieval | License copy: `third_party/licenses/ruc-nlpir/FlashRAG-LICENSE.txt` |
| `RUC-NLPIR/WebThinker` | MIT (upstream) | Vendored upstream repo (local clone) used as reference for WebThinker-style deep research deliverables (report + sources + trace) | License copy: `third_party/licenses/ruc-nlpir/WebThinker-LICENSE.txt` |
| `RUC-NLPIR/DeepAgent` | MIT (upstream) | Vendored upstream repo (local clone) used as reference for toolchain planning + context folding patterns under VCO governance | License copy: `third_party/licenses/ruc-nlpir/DeepAgent-LICENSE.txt` |

## Policy

1. Core VCO repository content is released under Apache-2.0.
2. Third-party projects keep their own licenses; this file does not relicense upstream code or content.
3. External corpora are treated as research inputs by default; avoid committing verbatim third-party prompt sets into core orchestration files.
4. Before distributing bundled third-party files, ensure compatible license obligations are met.

## Operational References

- External corpus workflow: `docs/external-corpus-integration.md`
- Upstream mapping lockfile: `config/upstream-lock.json`
- Third-party notice: `third_party/NOTICE.md`
