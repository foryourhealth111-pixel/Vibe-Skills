# Memory Governance Integration (VCO)

## Purpose

Integrate a strict role-boundary model for memory systems in VCO without introducing route conflicts, a second control plane, or a second canonical memory truth-source.

This integration is designed to:
- Keep `/vibe` as the only routing entrypoint
- Keep pack selection unchanged
- Add post-route memory guidance to reduce overlap and context pollution
- Absorb `mem0` and `Letta` into governed extension planes without changing runtime ownership

## Governance Contract

VCO memory role boundaries are:

1. `state_store`: session state only
2. `Serena`: explicit project decisions only
3. `ruflo`: short-term session vector cache only
4. `Cognee`: long-term graph memory + relationship retrieval only
5. `mem0`: optional external preference backend only
6. `Letta`: policy / contract source only
7. `episodic-memory`: disabled in VCO governance path

## Memory Runtime v2

Wave20–22 将 memory 治理进一步固化为 `Memory Runtime v2`：

- 设计文档：`docs/design/memory-runtime-v2-integration.md`
- tier router：`config/memory-tier-router.json`
- memory block contract：`references/memory-block-contract.md`
- mem0 policy：`docs/design/mem0-optin-backend-integration.md` + `config/mem0-backend-policy.json`
- letta policy：`docs/design/letta-policy-integration.md` + `config/letta-governance-contract.json`

核心原则：
- `mem0` 只能记录用户偏好、长期风格、重复约束等外部 preference payload。
- `Letta` 只能提供 memory block / tool-rule / token-pressure 等合同语言。
- 任一扩展层都不能接管 session truth、project decisions、route assignment。

## Non-Conflict Design

1. **No routing override**: memory governance does not change `selected.pack_id` or `selected.skill`.
2. **Post-route advice only**: router emits `memory_governance_advice` metadata.
3. **Mode-ready without lock-in**: supports `off|shadow|soft|strict`, but default is `shadow`.
4. **Fallback-safe**: if governance config is missing, VCO keeps core routing path unchanged.
5. **Single truth-source preserved**: `state_store/Serena/ruflo/Cognee` remain canonical within their scopes.

## Config

Primary policy files:
- `config/memory-governance.json`
- `config/memory-tier-router.json`
- `config/mem0-backend-policy.json`
- `config/letta-governance-contract.json`

Legacy compatibility note:
- tracked repo bundled config copies are retired
- the canonical `config/*` paths above remain authoritative
- install/runtime may generate compatibility copies when legacy runtime layout needs them

## Router Integration

Router file:
- `scripts/router/resolve-pack-route.ps1`

Output addition:
- `memory_governance_advice`

Advice payload includes:
- scope applicability and enforcement level
- task-level memory defaults (`primary_memory`, `project_decision_memory`, `short_term_memory`, `long_term_memory`)
- disabled systems list
- extension boundary snapshot (`mem0`, `Letta`)

## Runtime Activation

Router advice is no longer the whole story.
`vibe` runtime now has a bounded adapter layer that can execute real lane actions for:

- `Serena`: project-decision recall/write
- `ruflo`: XL handoff recall/write
- `Cognee`: bounded relation recall/write

Primary adapter assets:

- `config/memory-backend-adapters.json`
- `scripts/runtime/VibeMemoryBackends.Common.ps1`
- `scripts/runtime/memory_backend_driver.py`

The runtime still preserves one truth-source per lane.
If an adapter is disabled, missing, or not relevant for the stage, the run degrades to `state_store` and local governed artifacts.

## Verification

Run dedicated memory governance gates:

```powershell
pwsh -File .\scripts\verify\vibe-memory-governance-gate.ps1
pwsh -File .\scripts\verify\vibe-memory-tier-gate.ps1
pwsh -File .\scripts\verify\vibe-mem0-backend-gate.ps1
pwsh -File .\scripts\verify\vibe-letta-contract-gate.ps1
```

Run legacy-named packaging gate:

```powershell
pwsh -File .\scripts\verify\vibe-config-parity-gate.ps1
```

## Failure Semantics

- Missing governance config: bypass overlay advice, keep routing unchanged
- Policy set to `off`: emit disabled advice object
- Hook/runtime errors: continue core VCO routing path
- Disabled memory request (`episodic-memory`): advise role-mapped alternative (`Cognee` or `Serena`)
- Forbidden `mem0` payload: reject / downgrade to advisory-only
- Forbidden `Letta` runtime takeover: gate failure

## Wave20-22 Extensions

为吸收 `mem0` 与 `Letta`，memory governance 现已扩展为 **Memory Runtime v2**，但仍保持既有 canonical owner 不变。

新增资产：
- `docs/design/memory-runtime-v2-integration.md`
- `config/memory-tier-router.json`
- `docs/design/mem0-optin-backend-integration.md`
- `config/mem0-backend-policy.json`
- `docs/design/letta-policy-integration.md`
- `config/letta-governance-contract.json`
- `references/memory-block-contract.md`
- `references/tool-rule-contract.md`

新增门禁：
- `pwsh -File .\scripts\verify\vibe-memory-tier-gate.ps1`
- `pwsh -File .\scripts\verify\vibe-mem0-backend-gate.ps1`
- `pwsh -File .\scripts\verify\vibe-letta-contract-gate.ps1`

新增规则：
1. `mem0` 只能作为 external preference backend，不得拥有 session truth 或 route authority。
2. `Letta` 只能作为 policy / contract source，不得拥有 runtime takeover 权。
3. 若任何 extension plane 与 `state_store` / `Serena` / `ruflo` / `Cognee` 出现 owner 重叠，必须立即降回 `off` 或 `shadow`。
