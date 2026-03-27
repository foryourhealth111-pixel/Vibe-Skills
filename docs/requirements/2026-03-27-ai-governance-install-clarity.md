# Requirement: Clarify AI Governance Install-Time API Configuration

## Goal

Remove install-time ambiguity around the AI governance online path so users can tell:

- what to configure locally
- which key names are the recommended path
- how to verify readiness after installation

## User Intent

After finishing install, users should not have to guess whether:

- the local install is already complete
- the governance AI advice path is online
- `OPENAI_*`, `ARK_*`, or `VCO_AI_PROVIDER_*` is the right configuration surface

## Required Outcome

The public install and configuration docs must:

1. distinguish `installed locally` from `governance AI online-ready`
2. present the common OpenAI-compatible path as:
   - `OPENAI_API_KEY`
   - optional `OPENAI_BASE_URL` or `OPENAI_API_BASE`
   - the project governance model key
3. present the Ark-compatible path as:
   - `ARK_API_KEY`
   - optional `ARK_BASE_URL` or `VOLC_ARK_BASE_URL`
   - `ARK_MODEL`
4. treat the older fallback model-key wording as legacy wording instead of the primary install-time model key
5. stop presenting `VCO_AI_PROVIDER_URL` and `VCO_AI_PROVIDER_API_KEY` as the default local install-time guidance for quick checks
6. explain where the quick check actually reads values from:
   - `<target-root>/settings.json` `env`
   - or the current process environment
7. provide one concrete quick-check command for Windows and one for Linux/macOS
8. align install-time console messaging with the same wording

## Scope

In scope:

- public install docs
- install prompts
- install rules
- runtime/bootstrap user-facing messages
- quick-check guidance

Out of scope:

- redesigning policy schema
- changing host adapter ownership boundaries
- changing provider routing strategy

## Constraints

- do not ask users to paste secrets into chat
- do not claim online readiness without matching local configuration
- keep the guidance compatible with the latest GitHub version
- keep OpenAI-compatible and Ark-compatible wording both explicit
- preserve existing advanced policy-driven provider configuration paths where they already exist

## Acceptance Criteria

1. Public install docs no longer imply that `VCO_AI_PROVIDER_URL` / `VCO_AI_PROVIDER_API_KEY` is the primary local install-time path.
2. The configuration guide matches the actual quick-check probe behavior.
3. Install prompts tell assistants exactly which local keys to recommend after install.
4. One-shot bootstrap messages use concrete key names instead of generic “url/apikey/model”.
5. Quick-check next-step guidance mentions the right model/base-url keys for OpenAI-compatible and Ark-compatible paths.
6. Updated source install docs are mirrored into both bundled install-doc trees.
