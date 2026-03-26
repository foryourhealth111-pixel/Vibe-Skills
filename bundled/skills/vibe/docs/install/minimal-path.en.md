# Install Path: Minimal Viable (Truth-First / Degradation Accepted)

The goal of this path is to get the smallest repo-owned closure working as quickly as possible, while honestly exposing which capabilities still belong to host-managed surfaces instead of pretending that "it runs" means "full-featured parity".

Relevant distribution surfaces: `dist/manifests/vibeskills-core.json` and, for Codex, `dist/manifests/vibeskills-codex.json`.

## Who This Is For

- users seeing this repository for the first time who only want to verify whether repo-governed surfaces close correctly
- users who can accept a final `manual_actions_pending` state because host plugins, MCP, or provider secrets are still missing
- users who do not plan to provision every external dependency yet

## What You Should Not Expect

- no guarantee that host-side plugins are enabled
- no guarantee that plugin-backed MCP has been registered or authorized
- no guarantee that provider secrets such as `OPENAI_API_KEY` are ready
- no claim that a runnable bash flow on Linux/macOS is equal to the full Windows path

## Host / Platform Prerequisite Judgment

### Strongest Reference Lane (Codex)

According to `docs/universalization/host-capability-matrix.md`, Codex is currently the `supported-with-constraints` reference lane, which still includes host-managed surfaces.

According to `docs/universalization/platform-parity-contract.md`:

- Windows is the current authoritative reference path
- Linux gets close to that path only when `pwsh` is installed and PowerShell gates can run; otherwise it is explicitly **degraded**
- macOS remains `not-yet-proven`

### Claude Code / Generic Host

- Claude Code: `preview` in the current repository, with templates and guidance but without a Codex-equivalent repo-governed install/check closure
- Generic Host: `advisory-only`, meaning contract and document consumption only, with no runtime promise

If you are not running on Codex, treat this path as document/contract consumption plus minimal self-check, not as an official runtime install.

## Recommended Commands

### Windows (Preferred: `pwsh`)

```powershell
pwsh -File .\scripts\bootstrap\one-shot-setup.ps1 -SkipExternalInstall
pwsh -File .\check.ps1
```

### Linux (Bash Path; Degraded Without `pwsh`)

```bash
bash ./scripts/bootstrap/one-shot-setup.sh --skip-external-install
bash ./check.sh
```

> Tip: if you want Linux doctor/gate behavior to move closer to the authoritative path, install `pwsh`. Otherwise some PowerShell governance gates may be skipped with explicit warnings. That is an expected degraded path, not a disguised success.

## Truth-First Acceptance Criteria

- install/check exits with status code `0`
- the final state may honestly remain `manual_actions_pending` when host-side capabilities are missing
- `core_install_incomplete` must not appear

## Stop Rules

If you are only trying the repository for the first time, stopping here is fine.

Move on to these documents only after you confirm that repo-governed surfaces close properly and the remaining work is host-side provisioning:

- `docs/install/recommended-full-path.en.md`
- `docs/install/enterprise-governed-path.en.md`
