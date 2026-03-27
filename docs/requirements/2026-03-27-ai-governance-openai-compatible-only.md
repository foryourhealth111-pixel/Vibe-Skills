# Requirement: Restrict the Built-In AI Governance Layer to OpenAI-Compatible Integration

## Goal

Make the built-in AI governance layer support only OpenAI-compatible integration on the active shipped path.

## User Intent

Users should not see, configure, or depend on multiple provider lanes for the built-in governance layer.

The built-in path should stay:

- one provider shape
- one credential family
- one model/base-url story

## Required Outcome

The active built-in governance path must:

1. standardize on OpenAI-compatible integration for built-in advice and governance online capability
2. stop presenting Ark-compatible configuration as an equal built-in option in install docs and prompts
3. remove Ark-compatible provider registration from active provider authority surfaces
4. stop using Ark-specific defaults for built-in vector diff / embeddings
5. stop advertising or seeding Ark-specific bootstrap settings in active install/setup scripts
6. keep the install-time distinction between:
   - local install complete
   - governance online-ready
7. preserve OpenAI-compatible quick-check and doctor behavior

## In Scope

- active install docs
- active configuration defaults
- active bootstrap and doctor scripts
- active runtime-neutral governance connectivity probe
- active router provider registry and llm acceleration defaults
- active bundled mirrors of the same shipped assets

## Out of Scope

- historical release notes
- old archived proof bundles
- deleting every historical Ark-related file from the repo

## Constraints

- do not silently widen provider support again
- do not break the current OpenAI-compatible path
- keep bundled mirrors synchronized with source assets
- do not ask users to paste secrets into chat

## Acceptance Criteria

1. Public install docs for the built-in governance layer describe only OpenAI-compatible integration.
2. Active bootstrap/setup output no longer suggests Ark-compatible configuration.
3. Active policy defaults no longer use Ark-specific embedding provider settings.
4. Active provider registry no longer advertises an Ark-compatible built-in provider lane.
5. The router AI connectivity probe and doctor outputs align with OpenAI-compatible-only guidance.
6. Source and bundled active assets remain in sync.
