# Architecture

## Layers

1. Orchestration layer
- repo-root `SKILL.md`
- `core/skills/vibe`
- Protocol routing by task grade (M/L/XL)

2. Compatibility dependency layer
- `bundled/skills/*`
- compatibility-first workflow skills also ship from `bundled/skills/*`; there is no separate live `bundled/superpowers-skills/*` tree anymore
- All adapted for Codex behavior
- `bundled/skills/vibe` is not a tracked repo mirror anymore; compatibility materialization happens only at install/runtime boundaries when explicitly required.

3. Governance layer
- `rules/`
- `hooks/`

4. Execution layer
- `agents/templates/`
- `mcp/profiles/`
- `config/plugins-manifest.codex.json`

5. Operations layer
- install/check scripts
- lock and sync manifests

## Compatibility Contract

- Never overwrite bundled local rewrites with raw upstream content.
- Upstream updates must be reviewed and merged manually.
- `config/upstream-lock.json` records upstream references plus distribution-governance metadata; it remains a traceability surface, not a second runtime owner.
