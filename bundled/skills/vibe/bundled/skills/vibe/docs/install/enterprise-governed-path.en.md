# Install Path: Enterprise Governance (Auditable / Reproducible / Rollback-Friendly)

This path is for team and organization delivery. The goal is not only to say "it installed", but also to prove what was installed, what gaps remain, who owns them, and how rollback should work.

Relevant distribution surfaces:

- `dist/manifests/vibeskills-codex.json` (Codex lane, supported-with-constraints)
- `dist/manifests/vibeskills-core.json` (contract layer)

And this path must still follow the anti-overcommit rules in `docs/universalization/platform-parity-contract.md`.

## Who This Is For

- platform engineering, DevOps, and internal AI infrastructure maintainers
- organizations that need install, verification, upgrade, and rollback to become standard operating procedures
- teams that need explicit ownership and audit around host-managed surfaces

## Core Enterprise Principles (Truth-First)

1. freeze version boundaries: do not treat `main` as a production delivery artifact
2. record evidence: every install should preserve logs, states, and version output that can be reviewed later
3. split ownership: repo-governed closure and host-managed provisioning must be accepted separately
4. platforms are not equivalent: the Windows authoritative lane and Linux/macOS degraded lanes must be written into the delivery wording

## Recommended Execution Order (Codex Lane)

### Step 0: Record Version And Environment State

```powershell
git rev-parse HEAD
git status -sb
```

### Step 1: Run The Recommended Full Install And Deep Check

Windows:

```powershell
pwsh -File .\scripts\bootstrap\one-shot-setup.ps1
pwsh -File .\check.ps1 -Profile full -Deep
```

Linux/macOS:

```bash
bash ./scripts/bootstrap/one-shot-setup.sh
bash ./check.sh --profile full --deep
```

> Important: on Linux/macOS, if `pwsh` is unavailable, authoritative PowerShell gates may not run. The delivery wording must explicitly acknowledge that degraded state.

### Step 2: Run Governance Gates

Prefer Windows, or Linux with working `pwsh`:

```powershell
pwsh -File .\scripts\verify\vibe-version-consistency-gate.ps1
pwsh -File .\scripts\verify\vibe-offline-skills-gate.ps1
pwsh -File .\scripts\verify\vibe-version-packaging-gate.ps1
```

## Host-Managed Surfaces That Must Enter The Enterprise Checklist

According to `docs/universalization/host-capability-matrix.md` and `adapters/*/host-profile.json`, your internal checklist should at least include the following items with clear ownership:

- whether host-side plugins are enabled and version-controlled
- whether MCP registration and authorization are complete, especially for plugin-backed MCP
- provider-secret distribution, rotation, and permission policy for values such as `OPENAI_API_KEY`
- whether external CLIs such as `node`, `npm`, and `gh` are consistent across target machines or images

If those items are incomplete, the final status should honestly remain `manual_actions_pending`. Do not describe it as "fully ready".

## Stop Rules (Stricter In Enterprise Environments)

- if `core_install_incomplete` appears, stop rollout immediately
- if version-consistency, offline-closure, or packaging-governance gates fail, stop the upgrade and roll back immediately
- if any public wording upgrades `supported-with-constraints` or `preview` into `full-authoritative`, withdraw that promise and fix the release wording immediately
