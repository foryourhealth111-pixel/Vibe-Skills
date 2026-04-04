# Memory Runtime v2 Integration

## Purpose

Memory Runtime v2 extends VCO's memory governance so external memory-related projects can be absorbed without creating a second canonical memory plane.

## Canonical Owners

| Memory Need | Canonical Owner | Notes |
|---|---|---|
| Session state | `state_store` | Always-available default runtime memory |
| Explicit project decisions | `Serena` | Architecture decisions, conventions, durable project choices |
| Short-term semantic retrieval | `ruflo` | Session-scoped vector cache |
| Long-term relationship memory | `Cognee` | Graph memory and entity linking |
| External preference memory | `mem0` | Optional, opt-in backend only |
| Policy contracts | `Letta` | Rule vocabulary only, not runtime authority |

## Non-Negotiable Rules

1. `state_store` remains the primary memory for active execution.
2. `Serena` remains the only canonical home for explicit project decisions.
3. `mem0` can never become `defaults_by_task.primary`.
4. `Letta` can never become a second orchestrator or memory truth-source.
5. `episodic-memory` remains disabled.

## Tier Router

Memory Runtime v2 is materialized by `config/memory-tier-router.json`.
The tier router does not replace `config/memory-governance.json`; it clarifies extension lanes.

## External Extensions

### `mem0`
- allowed: recurring user preferences, style hints, reusable personal constraints
- forbidden: route assignment, canonical project decisions, primary execution state
- support intake: OpenAI-compatible embedder `baseURL` is allowed only inside the optional backend lane
- storage rule: backend state must use an operator-controlled durable path, not an implicit writable `cwd`
- payload rule: structured content inside code fences must be preserved for admission review, not silently stripped

### `Letta`
- allowed: memory block mapping, archival search contract, tool-rule contract, token-pressure policy
- forbidden: runtime takeover, autonomous route mutation, second workflow surface

## Rollout

- `off`: external extensions ignored
- `shadow`: classify and report only
- `soft`: allow guarded suggestions, no truth-source mutation
- `strict`: only for policy checks, never for authority transfer

## Verification

Required gates:
- `scripts/verify/vibe-memory-governance-gate.ps1`
- `scripts/verify/vibe-memory-tier-gate.ps1`
- `scripts/verify/vibe-mem0-backend-gate.ps1`
- `scripts/verify/vibe-letta-contract-gate.ps1`
