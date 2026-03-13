# Core Skill Contract (Batch A)

This repository uses a **skill contract** layer to stabilize core skill metadata without rewriting or replacing any upstream `SKILL.md`.

## Scope (v1, conservative)

The first contract version intentionally enforces only invariants that are:

- Derived from the current `SKILL.md` structure in this repository.
- Stable across normal content edits (e.g., adding examples/sections).
- Cheap to validate offline.

### What v1 enforces

- `SKILL.md` must start with YAML frontmatter delimited by `---` on the first line and a closing `---`.
- Frontmatter must contain `name` and `description`.
- `frontmatter.name` must equal the canonical `skill_id` (directory name).
- Optional packaging parity: alternate `SKILL.md` copies declared in the contract must match the primary file (normalized newlines).

### What v1 does NOT enforce (by design)

- Any specific headings/section structure in `SKILL.md`.
- Trigger keyword lists, prompt templates, or content semantics beyond the stable frontmatter.
- Runtime provider credentials, MCP connectivity, or execution behavior.

## Files

- Contracts live under `core/skill-contracts/v1/*.json`.
- The contract index lives at `core/skill-contracts/index.json`.
- Schemas (documentation + future validation support) live under `schemas/`.
- Gates live under `scripts/verify/`:
  - `vibe-skill-contract-schema-gate.ps1`
  - `vibe-skill-contract-parity-gate.ps1`

## Adding a new canonical contract

1. Create a new JSON contract in `core/skill-contracts/v1/<skill_id>.json`.
2. Add an entry to `core/skill-contracts/index.json`.
3. Run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-skill-contract-schema-gate.ps1 -WriteArtifacts
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-skill-contract-parity-gate.ps1 -WriteArtifacts
```

