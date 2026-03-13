# Router Model Neutrality

> Status baseline: 2026-03-13  
> Goal: include GPT-backed routing intelligence in universalization governance without turning GPT into the ecosystem's hidden single point of truth.

## Executive Position

`VibeSkills` can keep using GPT-class models for routing governance, but only if the system is redefined so that:

- the canonical router stays authoritative
- the model provider is replaceable
- provider absence has an explicit degraded state
- host universalization does not imply provider lock-in

This document defines the model-level boundary. The provider-level contract is defined in:

- `docs/universalization/router-provider-layer.md`
- `config/router-provider-registry.json`
- `config/router-provider-defaults.json`

This is the only route that keeps your current governance advantage **and** makes the ecosystem truly general-purpose.

## Current Reality

The current repository already contains provider-coupled routing intelligence assets.

Observed examples:

- `scripts/router/modules/01-openai-responses.ps1`
- `config/settings.template.codex.json`
- `config/ruc-nlpir-runtime.json`

These assets prove two things:

1. GPT / OpenAI-compatible inference is already part of the real system.
2. The system still lacks a formal, provider-neutral contract for that layer.

Without that contract, universalization would be blocked by:

- enterprise environments that ban a given provider
- host environments that cannot assume the same env vars
- offline or region-constrained users
- future provider swaps that would otherwise force router rewrites

## Separation of Concerns

The universalized architecture must separate:

### 1. Routing Authority

This is the only layer allowed to decide route ownership.

Current representative assets:

- `scripts/router/resolve-pack-route.ps1`
- `config/pack-manifest.json`
- `config/router-thresholds.json`
- `config/skill-routing-rules.json`

Responsibilities:

- pack assignment
- skill candidate selection
- confirm-required behavior
- legacy fallback behavior
- replay contract

### 2. Routing Intelligence Provider

This layer may help the authority layer but must not replace it.

Allowed responsibilities:

- semantic extraction
- candidate rerank
- advice generation
- replay comparison
- shadow evaluation
- route explainability

Forbidden responsibilities:

- canonical assignment ownership
- second-router behavior
- bypassing explicit user commands
- mutating live router semantics by itself

Provider bindings and offline behavior MUST be governed as a separate contract:

- `config/router-provider-registry.json`
- `config/router-provider-defaults.json`
- `schemas/router-provider.schema.json`

## Runtime States

The provider layer must be labeled with truthful states:

| State | Meaning |
| --- | --- |
| `provider-assisted` | model provider available and allowed for routing intelligence enhancement |
| `heuristic-only` | deterministic router continues without live model assistance |
| `offline-frozen` | no provider assistance allowed; replay and routing stay on frozen deterministic behavior |
| `unsupported` | a feature requires provider assistance but no truthful degraded path exists |

The system must never silently pretend that `heuristic-only` equals `provider-assisted`.

## Non-Regression Rule

This refactor must preserve the current single-router doctrine:

- no second router
- no provider takeover
- no direct live-router mutation from adaptive outputs
- no provider-specific contract becoming the new ecosystem truth

In other words:

`GPT is an intelligence backend, not the constitution.`

## Cross-Host Implications

Once `VibeSkills` is universalized, host support and provider support become different questions.

Examples:

- a host may support the canonical router but only allow `heuristic-only`
- a host may allow provider-assisted routing but only on Windows or only with enterprise proxy settings
- a host adapter may map provider config differently, but it must not rewrite canonical semantics

Therefore all future support claims should follow this structure:

`<host> on <platform> with <provider-state> => <support-level>`

## Governance Requirements

The provider-neutral contract must enforce:

1. provider assistance is optional to the ecosystem, even if valuable to the premium path
2. provider-specific env vars are runtime bindings, not canonical truth
3. route replay can compare provider-assisted and heuristic-only outputs
4. fallback labels are visible in docs, install outputs, and diagnostics

Provider-layer verification gates:

- `scripts/verify/vibe-router-provider-neutrality-gate.ps1`
- `scripts/verify/vibe-router-offline-degrade-contract-gate.ps1`

## What This Solves

If governed correctly, you keep the current strength of GPT-enhanced intelligent routing while removing the biggest universalization blocker:

- no hidden provider monopoly
- no fake "general ecosystem" claim
- no forced rewrite every time provider strategy changes
- no silent regression when a host cannot use the same model stack

## Non-Regression Clause (Hard)

This universalization slice is governance-only:

- Do not modify `scripts/router/**` to satisfy this document.
- Do not introduce a new runtime control plane.
- Do not create a second router.
