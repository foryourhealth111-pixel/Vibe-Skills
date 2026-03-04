# Architecture

## Layers

1. Orchestration layer
- `bundled/skills/vibe`
- Protocol routing by task grade (M/L/XL)

2. Compatibility dependency layer
- `bundled/skills/*`
- `bundled/superpowers-skills/*`
- All adapted for Codex behavior

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
- `config/upstream-lock.json` records upstream references for traceability only.
