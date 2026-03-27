# Requirement: Clean Residual Historical Multi-Key Wording From Vibe Governance Docs

## Goal

Remove the remaining exact legacy model-key names from `vibe` governance history and current governance artifacts, while preserving the factual meaning of those documents.

## User Intent

After the active built-in governance path has converged to one model key, the repo should not keep avoidable residual old key-name strings in `vibe` documentation and planning artifacts.

## Required Outcome

The cleanup pass must:

1. rewrite residual `vibe` historical docs so they describe the older multi-key model wording generically instead of naming the retired secondary model keys verbatim
2. rewrite current governance requirement and plan artifacts so they describe the removed lanes generically where exact legacy names are no longer needed
3. keep the current single-key contract unchanged:
   - `OPENAI_API_KEY`
   - optional `OPENAI_BASE_URL` or `OPENAI_API_BASE`
   - `VCO_RUCNLPIR_MODEL`
4. keep unrelated non-`vibe` skills out of scope
5. keep bundled mirrors synchronized for any shipped `vibe` docs that change

## In Scope

- `docs/changes/**` entries for `vibe`
- `docs/plans/**` legacy `vibe` planning artifacts that still spell out retired model keys
- current `docs/requirements/**` and `docs/plans/**` artifacts created during this governance tightening run
- bundled mirrors of changed `vibe` history docs

## Out of Scope

- unrelated skills outside the `vibe` shipped path
- external examples that intentionally document generic OpenAI usage in other skills
- rewriting unrelated historical provider notes that do not contain the retired model-key names

## Constraints

- preserve document meaning
- do not reintroduce a second active model-key lane
- do not modify unrelated skill documentation just to satisfy a broad grep

## Acceptance Criteria

1. Repo-wide search for the retired secondary model-key strings returns no matches inside `vibe` source docs, bundled `vibe` docs, or current governance artifacts for this run.
2. The single-key active contract remains unchanged.
3. Any remaining matches outside `vibe` are explicitly identified as out of scope.
