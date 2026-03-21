# 2026-03-22 Install Surface Simplification Requirement

- Topic: simplify the user-facing install surface and fix multi-agent selection before bootstrap.
- Mode: interactive_governed
- Goal: reduce the public install story to two main options while making bootstrap ask which agent the user wants before defaulting into a host lane.

## Deliverable

A working update that:

1. reduces the main install story to `prompt install` and `manual copy install`
2. makes `one-shot-setup` ask for the target agent when `host` is not explicitly provided
3. preserves explicit `--host` / `-HostId` behavior for automation
4. keeps non-interactive execution safe by requiring explicit host selection
5. reminds non-Codex lanes that `url`, `apikey`, and `model` are user-supplied
6. updates Chinese and English README/install docs to match the new install surface

## Constraints

- No false closure claims for `claude-code`, `generic`, or `opencode`
- Do not break existing explicit-host automation flows
- Keep advanced install matrices as secondary references, not the default user path
- Keep verification evidence fresh before claiming completion
- Complete phase cleanup after implementation and verification

## Acceptance Criteria

- `scripts/bootstrap/one-shot-setup.sh` prompts for host selection in interactive mode when no host is provided
- `scripts/bootstrap/one-shot-setup.ps1` prompts for host selection in interactive mode when no host is provided
- both scripts fail with a clear message in non-interactive mode when host is omitted
- README user-facing install section exposes exactly two primary options
- new manual copy install docs exist in Chinese and English
- prompt-install docs tell the AI to ask the user which agent to target before installation
- verification confirms syntax and targeted bootstrap host-selection behavior

## Non-Goals

- Replacing `install.*` / `check.*` with interactive prompts
- Full closure for hosts other than Codex
- Removing advanced truth/reference documents from the repo

## Inferred Assumptions

- The public install problem is mainly a UX/documentation issue plus a bootstrap host-default issue.
- Preserving explicit host flags is more important than making every lower-level script interactive.
- Manual copy install should stay minimal, truthful, and host-neutral.
