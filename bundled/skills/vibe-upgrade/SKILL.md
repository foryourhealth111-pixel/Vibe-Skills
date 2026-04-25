---
name: vibe-upgrade
description: Upgrade the local Vibe-Skills installation to the latest official default-branch state while keeping canonical vibe as the only governed runtime.
---

Use canonical `vibe` as the only governed runtime authority for this request.

Entry bias:

- upgrade the local Vibe-Skills installation for a supported host
- use the official repository default branch only
- run reinstall and verification through shared product pathways

Execution rules:

- delegate to canonical `vibe`
- keep `vibe` as the only runtime authority
- do not create a second requirement surface
- do not create a second plan surface
- do not create a parallel runtime
- do not preflight-scan the current workspace or repository for canonical proof files before launch
- Launch canonical-entry first; validate receipts only after it returns a session root
- do not upgrade from arbitrary remotes, branches, or filesystem roots

When this wrapper is chosen, bias canonical `vibe` toward:

- shared `vgo-cli upgrade` execution
- overwrite-style upgrade for the selected supported host
- post-upgrade verification and concise before/after reporting

If invoked with no arguments, default the request to upgrading the current host installation through shared `vgo-cli upgrade` and verifying the result.

Request:
$ARGUMENTS
