# Prompt Overlay Integration (prompts.chat x VCO)

## Purpose

Integrate prompt assets into VCO without introducing a second orchestrator or a second prompt control surface.

This overlay family is designed to:
- Keep `/vibe` as the only routing entrypoint
- Provide prompt-template discovery/refinement hints post-route
- Reduce prompt-vs-doc routing ambiguity through semantic confirm gates
- Absorb `Prompt-Engineering-Guide` as pattern/risk/governance assets, not as a parallel prompt router

## Prompt Plane Layers

VCO prompt plane now has three governed layers:

1. **Prompt overlay** — `prompts.chat`-style prompt asset discovery and ambiguity guard
2. **Prompt asset boost** — GPT-5.2 × prompt assets协作增强，输出候选 prompt advice
3. **Prompt intelligence** — `Prompt-Engineering-Guide` 吸收后的 pattern cards、risk checklist、policy contract

对应资产：
- `config/prompt-overlay.json`
- `config/prompt-asset-boost.json`
- `config/prompt-intelligence-policy.json`
- `references/prompt-pattern-cards.md`
- `references/prompt-risk-checklist.md`
- `docs/governance/prompt-intelligence-governance.md`

## Non-Redundancy Boundaries

1. **Single routing authority**: VCO pack router remains the control plane.
2. **Post-route advisory/guard only**: prompt layers emit advice metadata; they do not replace pack selection.
3. **No second workflow surface**: no new `/prompt:*` lifecycle is introduced into VCO.
4. **Asset-plane responsibility**: prompt assets are used for template/rewrite/chaining/risk analysis, not for general docs retrieval or route takeover.
5. **Pattern, not power**: `Prompt-Engineering-Guide` enriches prompt thinking, but cannot widen route authority beyond configured caps.

## Config

Primary policy files:
- `config/prompt-overlay.json`
- `config/prompt-asset-boost.json`
- `config/prompt-intelligence-policy.json`

Legacy compatibility note:
- tracked repo bundled config copies are retired
- the canonical config paths above are authoritative
- install/runtime may still generate compatibility copies outside repo truth when legacy layout is required

## Runtime Behavior

Router file:
- `scripts/router/resolve-pack-route.ps1`

Output additions:
- `prompt_overlay_advice`
- `prompt_asset_boost_advice`
- `prompt_intelligence_advice`
- `prompt_overlay_route_override`

Semantics:
- In `shadow`: advisory only.
- In `soft`: prompt/doc collision or high-risk prompt scenario can upgrade route to `confirm_required` within configured scope.
- In `strict`: same collision triggers `confirm_required`; prompt-heavy in-scope requests become `required` only in advice metadata.
- Outside configured collision/risk conditions, routing remains unchanged.

## Conflict Control

To avoid prompt/doc cross-talk:
- `prompt-lookup` gains stronger prompt-intent positive keywords.
- `prompt-lookup` gets doc-surface negative keywords.
- `openai-docs` / `documentation-lookup` / `openai-knowledge` receive prompt-intent negative keywords.
- Prompt intelligence only injects cards/checklists/reference text; it does not replace the selected pack/skill.

This ensures:
- prompt template/refine requests prefer `prompt-lookup`
- official API/doc requests stay in doc-focused skills
- ambiguous requests are explicitly confirmed instead of silently misrouted
- high-risk prompt constructions get extra checklist coverage without adding a second control surface

## Verification

Run dedicated overlay gates:

```powershell
pwsh -File .\scripts\verify\vibe-prompt-overlay-gate.ps1
pwsh -File .\scripts\verify\vibe-prompt-asset-boost-gate.ps1
pwsh -File .\scripts\verify\vibe-prompt-intelligence-assets-gate.ps1
```

Run legacy-named packaging gate:

```powershell
pwsh -File .\scripts\verify\vibe-config-parity-gate.ps1
```

## Failure Semantics

Overlay failures are non-fatal by default:
- missing config -> bypass overlay advice
- policy disabled -> no effect on route decision
- no prompt signals -> no overlay-driven escalation
- asset retrieval failure -> keep selected route and emit empty or degraded advice object

Only configured prompt/doc ambiguity or high-risk prompt scenarios can enforce `confirm_required`.

## Wave23 Prompt Intelligence Extension

为吸收 `Prompt-Engineering-Guide`，VCO 新增 **Prompt Intelligence** 资产层，但仍保持 prompt overlay 为 post-route advisory path。

新增资产：
- `references/prompt-pattern-cards.md`
- `references/prompt-risk-checklist.md`
- `docs/governance/prompt-intelligence-governance.md`
- `config/prompt-intelligence-policy.json`

关键约束：
1. `allow_route_override = false`
2. `allow_second_prompt_surface = false`
3. Prompt intelligence 只能注入 pattern / checklist / risk reference，不得替换 selected pack/skill。

新增门禁：
- `pwsh -File .\scripts\verify\vibe-prompt-intelligence-assets-gate.ps1`
