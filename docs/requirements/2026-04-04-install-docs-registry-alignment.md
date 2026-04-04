# Install Docs Registry Alignment

## Goal

Align the user-facing installation documentation on `release/v2.3.56-architecture-closure-baseline` with the registry-driven install architecture that now exists in the branch.

## Deliverable

A documentation-only correction pass across the public install entry surfaces so readers can tell:

- which hosts are currently supported
- which host mode each install path actually uses
- when `one-shot-setup.*` is available
- when `direct install/check` remains the thinner recommended path

## Constraints

- Do not change install or check implementation in this wave.
- Treat [`config/adapter-registry.json`](../../config/adapter-registry.json) as the host-mode source of truth.
- Keep cross-platform command examples valid for PowerShell and shell entrypoints.
- Keep wording honest about bounded closure, preview-guidance, and runtime-core boundaries.
- Do not claim that a host is fully managed when the runtime keeps host-local settings or credentials outside repo ownership.

## Acceptance Criteria

- Root README surfaces no longer imply that install guidance is static or hand-maintained when it is now registry-driven.
- Install docs no longer claim that one-shot bootstrap only covers `codex` and `claude-code`.
- Install docs no longer describe `opencode` as one-shot-unsupported when the registry-driven wrapper can bootstrap preview-guidance hosts.
- Public prompt documents stop using "direct install/check instead of one-shot bootstrap" as if one-shot were unavailable; if direct install remains preferred, the docs must say it is the thinner path, not the only path.
- Chinese and English install entry docs stay semantically aligned.

## Product Acceptance

- A new reader can start from `README.md` or `README.zh.md` and reach the correct install path without conflicting host-mode descriptions.
- A reader comparing `docs/install/README*`, `docs/one-shot-setup.md`, and `docs/cold-start-install-paths*` sees the same host-mode model.
- Prompt-based install guidance and command-reference pages no longer contradict the live bootstrap scripts.

## Non-Goals

- Expanding support to new hosts.
- Rewriting historical release notes or old requirement archives.
- Changing install semantics, bootstrap behavior, or verification gates in this wave.
