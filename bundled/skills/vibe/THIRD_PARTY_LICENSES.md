# Third-Party Licenses and Distribution Boundaries

This repository is licensed under **Apache-2.0**. See [`LICENSE`](./LICENSE).

This file is the human-readable disclosure surface for third-party and upstream
sources tracked canonically in [config/upstream-lock.json](./config/upstream-lock.json).
It does not relicense upstream code, prompts, datasets, or services.

## Canonical Rules

1. The canonical machine-readable source of truth is
  [config/upstream-lock.json](./config/upstream-lock.json).
2. This file must disclose every lock entry that has `disclosure_required: true`.
3. `reference-only` entries are governance, research, or methodology sources and
   must not be treated as redistributable upstream code.
4. `external-optional` entries are optional providers, CLIs, services, or
   operator-local mirrors and are not shipped by default unless explicitly stated.
5. `distributed-local` entries are local bundled integrations that require
   notice preservation and provenance tracking.

## Upstream Disclosure Matrix

| Upstream Project | SPDX License | Canonical Slug | Distribution Tier | Distribution Boundary |
|---|---|---|---|---|
| `obra/superpowers` | `MIT` | `superpowers` | `distributed-local` | Bundled/local distribution allowed with notice preservation |
| `frankbria/ralph-claude-code` | `MIT` | `ralph-claude-code` | `distributed-local` | Bundled/local distribution allowed with notice preservation |
| `f/prompts.chat` | `CC0-1.0` | `prompts-chat` | `external-optional` | External service only; follow provider terms |
| `SuperClaude-Org/SuperClaude_Framework` | `MIT` | `superclaude-framework` | `external-optional` | Optional external install; not shipped by default |
| `feiskyer/claude-code-settings` | `MIT` | `claude-code-settings` | `distributed-local` | Bundled/local distribution allowed with notice preservation |
| `github/spec-kit` | `MIT` | `spec-kit` | `distributed-local` | Bundled/local distribution allowed with notice preservation |
| `ruvnet/claude-flow` | `MIT` | `claude-flow` | `external-optional` | Optional external install; not shipped by default |
| `medialab/xan` | `Unlicense` | `xan` | `external-optional` | Optional external install; not shipped by default |
| `Done-0/fuck-u-code` | `MIT` | `fuck-u-code` | `external-optional` | Optional external install; not shipped by default |
| `ivy-llc/ivy` | `NOASSERTION` | `ivy` | `external-optional` | Optional external install; not shipped by default |
| `GokuMohandas/Made-With-ML` | `MIT` | `made-with-ml` | `reference-only` | Reference-only; no upstream code redistribution in core |
| `zedr/clean-code-python` | `MIT` | `clean-code-python` | `reference-only` | Reference-only; no upstream code redistribution in core |
| `donnemartin/system-design-primer` | `NOASSERTION` | `system-design-primer` | `reference-only` | Reference-only; no upstream code redistribution in core |
| `xlite-dev/LeetCUDA` | `GPL-3.0` | `leetcuda` | `reference-only` | Reference-only; no upstream code redistribution in core |
| `RUC-NLPIR/FlashRAG` | `MIT` | `flashrag` | `external-optional` | Operator-local retention only; not shipped by default |
| `RUC-NLPIR/WebThinker` | `MIT` | `webthinker` | `external-optional` | Operator-local retention only; not shipped by default |
| `RUC-NLPIR/DeepAgent` | `MIT` | `deepagent` | `external-optional` | Operator-local retention only; not shipped by default |
| `mem0ai/mem0` | `Apache-2.0` | `mem0` | `external-optional` | Optional external backend; not canonical truth source |
| `letta-ai/letta` | `Apache-2.0` | `letta` | `reference-only` | Reference-only; no upstream code redistribution in core |
| `dair-ai/Prompt-Engineering-Guide` | `MIT` | `prompt-engineering-guide` | `reference-only` | Reference-only; no upstream code redistribution in core |
| `browser-use/browser-use` | `MIT` | `browser-use` | `external-optional` | Optional external provider; VCO stays control plane |
| `simular-ai/Agent-S` | `Apache-2.0` | `agent-s` | `reference-only` | Reference-only; no upstream code redistribution in core |
| `SynkraAI/aios-core` | `NOASSERTION` | `aios-core` | `reference-only` | Reference-only; no upstream code redistribution in core |
| `x1xhlol/system-prompts-and-models-of-ai-tools` | `GPL-3.0` | `system-prompts-and-models-of-ai-tools` | `reference-only` | Reference-only; no upstream code redistribution in core |
| `muratcankoylan/Agent-Skills-for-Context-Engineering` | `MIT` | `agent-skills-for-context-engineering` | `reference-only` | Reference-only; no upstream code redistribution in core |

## Operator Notes

- `NOASSERTION` means the canonical registry does not currently assert an SPDX
  identifier. Inspect the upstream repository before vendoring or redistributing
  any upstream material.
- `GPL-3.0` sources in this repository are tracked as reference-only inputs. Do
  not fold raw GPL corpus or source into Apache-2.0 distributed runtime assets
  without a separate compliance review and explicit redistribution boundary.
- Operator-local mirrors and vendored clones must keep upstream notices, commit
  provenance, and origin records under the governed vendor surface.

## Operational References

- Distribution governance policy:
  [docs/distribution-governance.md](https://github.com/foryourhealth111-pixel/Vibe-Skills/blob/main/docs/distribution-governance.md)
- Upstream governance policy:
  [docs/upstream-distribution-governance.md](https://github.com/foryourhealth111-pixel/Vibe-Skills/blob/main/docs/upstream-distribution-governance.md)
- Provenance policy:
  [docs/origin-provenance-policy.md](https://github.com/foryourhealth111-pixel/Vibe-Skills/blob/main/docs/origin-provenance-policy.md)
- Canonical upstream registry:
  [config/upstream-lock.json](./config/upstream-lock.json)
- Bundled package notice:
  [NOTICE](./NOTICE)
