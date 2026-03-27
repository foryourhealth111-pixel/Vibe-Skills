# Requirement: Converge the Built-In AI Governance Layer to One Model Key

## Goal

Make the active built-in AI governance path use one canonical model environment key only: `VCO_RUCNLPIR_MODEL`.

## User Intent

Users should not need to decide between multiple model-key names when configuring the built-in governance layer.

The active public path should present:

- one credential family
- one base-url family
- one model key

## Required Outcome

The active built-in governance path must:

1. treat `VCO_RUCNLPIR_MODEL` as the only supported model environment key on the active shipped path
2. stop presenting a second public model key as an equal configuration choice
3. stop presenting legacy fallback model-key wording in install and quick-check guidance
4. keep the OpenAI-compatible base URL and API key guidance unchanged
5. preserve the distinction between:
   - local install complete
   - governance online-ready
6. keep bundled mirrors synchronized with the same single-key contract

## In Scope

- active runtime-neutral AI connectivity probe
- active bootstrap/setup guidance
- active settings templates that expose built-in governance model wiring
- active install docs and install prompts
- active bundled mirrors of the same shipped assets

## Out of Scope

- rewriting historical change logs
- deleting every historical legacy key mention from archived or superseded artifacts
- changing the canonical OpenAI-compatible API key or base-url names

## Constraints

- do not break the current OpenAI-compatible governance path
- do not silently keep a second active model-key lane
- do not ask users to paste secrets into chat
- keep source and bundled shipped assets in sync

## Acceptance Criteria

1. Active runtime guidance resolves the built-in governance model from `VCO_RUCNLPIR_MODEL` only.
2. Active bootstrap/setup messages recommend only `VCO_RUCNLPIR_MODEL` for the model name.
3. Public active install docs and prompts describe one model key only.
4. Active shipped settings templates no longer advertise any retired secondary model-key lane for the built-in governance model slot.
5. Verification output for missing model configuration points to `VCO_RUCNLPIR_MODEL` only.
6. Source assets and bundled mirrors remain synchronized after the change.
