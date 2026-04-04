# Design And Playbooks

- Docs root: [`../README.md`](../README.md)
- Repo root: [`../../README.md`](../../README.md)

## What Lives Here

`docs/design/` stores long-lived design notes, integration designs, and reusable playbooks that explain how a capability should work without turning the docs root into a flat historical catch-all.

## Start Here

### Design Surfaces

| File | Purpose |
| --- | --- |
| [`deep-discovery-mode-design.md`](deep-discovery-mode-design.md) | Describe the governed deep-discovery chain and its routing-stage boundaries |
| [`node-zombie-guardian-design.md`](node-zombie-guardian-design.md) | Explain VCO-owned Node process health and cleanup design |
| [`memory-runtime-v2-integration.md`](memory-runtime-v2-integration.md) | Freeze the v2 memory runtime integration shape without keeping a root-level duplicate |
| [`xl-operator-playbook.md`](xl-operator-playbook.md) | Capture XL execution discipline as a reusable playbook instead of a root doc leaf |

### Integration Design Leaves

Representative leaves now grouped here include:

- `agency-agents-overlay.md`
- `ai-rerank-overlay-integration.md`
- `browserops-provider-integration.md`
- `data-scale-overlay-integration.md`
- `framework-interop-overlay-integration.md`
- `gitnexus-overlay.md`
- `gsd-vco-overlay-integration.md`
- `letta-policy-integration.md`
- `mem0-optin-backend-integration.md`
- `prompt-overlay-integration.md`
- `python-clean-code-overlay-integration.md`
- `retrieval-overlay-integration.md`

### Playbooks

| File | Purpose |
| --- | --- |
| [`blackbox-probe-and-enhancement-playbook.md`](blackbox-probe-and-enhancement-playbook.md) | Organize route probe, enhancement, and regression workflows |
| [`xl-operator-playbook.md`](xl-operator-playbook.md) | Document high-concurrency operator discipline without elevating it to a docs-root entry |

## Cross-Layer Handoff

- [`../docs-information-architecture.md`](../docs-information-architecture.md): docs taxonomy and placement rules
- [`../../scripts/verify/README.md`](../../scripts/verify/README.md): verify entry surface that consumes some design/playbook guidance
- [`../../references/index.md`](../../references/index.md): long-lived contracts and matrices that complement design docs
- [`../archive/root-docs/README.md`](../archive/root-docs/README.md): archived root-level playbooks, reports, and historical matrices

## Rules

- Put long-lived design notes, integration design leaves, and reusable playbooks here instead of adding more weakly linked root docs.
- Keep current runtime summary, release truth, and dated execution receipts out of this directory.
- If a design doc becomes obsolete, move it to archive instead of re-expanding the docs root.
