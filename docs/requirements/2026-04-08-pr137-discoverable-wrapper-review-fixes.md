# PR137 Discoverable Wrapper Review Fixes

## Goal
Bring PR `#137` back into a truthful, mergeable state by fixing the two blocking review defects in discoverable wrapper projection and discoverable-entry verification.

## Problem Statement
The branch currently claims multi-host discoverable `vibe` entry projection, but only `codex` and `opencode` actually materialize host-visible wrappers. The other supported hosts silently install zero discoverable wrappers while metadata and docs still declare generated wrapper entry support.

The branch also mixes two different inventories into one ledger field: host-visible discoverable entries and host specialist bridge launchers. That makes `check.sh` and `check.ps1` misreport missing bridge launchers as missing discoverable entries.

## Required Outcomes
1. `codex`, `claude-code`, `cursor`, `windsurf`, `openclaw`, and `opencode` must all materialize the shared discoverable `vibe`, `vibe-want`, `vibe-how`, and `vibe-do` entry set into a host-visible install surface.
2. Skill-only hosts must materialize discoverable entries as generated wrapper skills instead of silently emitting no wrapper inventory.
3. The installer must fail if a host with a declared discoverable-entry surface produces zero host-visible wrappers.
4. The install ledger must separate discoverable entry inventory from host specialist bridge launcher inventory.
5. `check.sh` and `check.ps1` must validate discoverable entries against discoverable-entry inventory only, and must keep bridge-launcher validation separate.
6. Linux and Windows verification paths must agree on the same truth model.

## Constraints
- Keep `config/vibe-entry-surfaces.json` as the single source of truth for discoverable entry ids and stage-stop semantics.
- Do not introduce a second runtime authority beyond canonical `vibe`.
- Do not regress existing codex/opencode discoverable entry behavior.
- Do not claim host visibility from docs or metadata unless install/check now prove it.

## Acceptance Criteria
- Fresh installs for `claude-code`, `cursor`, `windsurf`, and `openclaw` contain generated discoverable wrapper skills for the four public entries.
- Fresh installs for `codex` and `opencode` still contain the four discoverable wrapper command files.
- Removing a bridge launcher causes only bridge-launcher validation to fail; discoverable-entry validation remains green if entry wrappers still exist.
- Targeted unit/runtime-neutral tests cover both the materialization contract and the split inventory contract.
