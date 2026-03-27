# Requirement: Consolidate Built-In AI Governance to a Stable Single-Path Contract

## Goal

Consolidate all active built-in AI governance changes so runtime behavior, verification surfaces, bootstrap guidance, and install docs all reflect one stable contract.

## User Intent

The built-in AI governance layer should be:

- OpenAI-compatible only
- single-model-key only
- correctly verifiable
- documented without conflicting or stale active-path wording

## Required Outcome

The active built-in governance path must:

1. support only the OpenAI-compatible provider family on the active shipped path
2. use `VCO_RUCNLPIR_MODEL` as the only active built-in governance model key
3. make bootstrap doctor / readiness surfaces report both credential and model readiness for the built-in governance path
4. stop treating Ark helper modules or Ark-specific install helpers as active built-in governance surfaces
5. keep install entry docs aligned with the same credential + base URL + model-key contract
6. keep bundled mirrors synchronized with the corrected active source assets

## In Scope

- active runtime-neutral verification scripts
- active PowerShell doctor gate
- active bootstrap/setup docs
- active router verification helpers
- active shipped helper scripts for built-in governance configuration
- bundled mirrors of the changed active assets

## Out of Scope

- historical release notes
- proof bundles
- unrelated non-vibe skills

## Constraints

- do not break the current OpenAI-compatible runtime path
- do not reintroduce a second provider lane
- preserve honest readiness reporting

## Acceptance Criteria

1. Active doctor outputs expose both `OPENAI_API_KEY` and `VCO_RUCNLPIR_MODEL` readiness.
2. Active built-in governance verification scripts no longer test or clear Ark-specific built-in provider paths.
3. Ark-specific built-in governance helper scripts are no longer present on the active shipped path.
4. Install docs and one-shot docs consistently tell users to configure `OPENAI_API_KEY`, optional base URL, and `VCO_RUCNLPIR_MODEL`.
5. Source and bundled mirrors stay in sync after the consolidation.
