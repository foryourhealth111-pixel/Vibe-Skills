# Cold-Start Install Paths

This document is for first-time users and teams evaluating `vco-skills-codex`.

The goal is not to force everyone into one install mode. The goal is to answer four practical questions first:

- do you only want to get it running quickly, or do you want the closest thing to a full-featured setup
- can you accept `manual_actions_pending`
- are you able to provision host plugins, MCP services, and provider secrets
- are you operating on a personal machine, a shared team environment, or an enterprise-governed surface

If you only remember one thing:

`minimum viable` is about getting the system running quickly.  
`recommended full-featured` is about closing the repo-governed surface.  
`enterprise-governed` is about repeatable, auditable, rollback-safe delivery.

## Path 1: Minimum Viable

### Best for

- first-time users exploring VibeSkills
- users who want to test VCO, routing, docs, and the shipped payload first
- users who are not ready to provision every host plugin, MCP surface, or API key yet

### Goal

Install the minimum runtime surface owned by the repo and confirm the core scripts and local governance layer work.

### Prerequisites

- `git`
- `python3` or `python`
- Windows: `powershell` or `pwsh`
- Linux / macOS: `bash`

### Recommended commands

Windows:

```powershell
pwsh -File .\scripts\bootstrap\one-shot-setup.ps1 -SkipExternalInstall
```

Linux / macOS:

```bash
bash ./scripts/bootstrap/one-shot-setup.sh --skip-external-install
```

### What you get

- the shipped runtime payload installed under the target Codex root
- the active MCP profile materialized
- the basic doctor flow executed
- clarity on whether the remaining gap is repo-owned or host-owned

### What you should not expect

- external CLIs are not guaranteed to be installed
- plugin-backed MCP surfaces are not guaranteed to be ready
- online provider execution is not guaranteed to be available

### Acceptance criteria

- install command exits `0`
- `check.ps1` / `check.sh` can complete
- `manual_actions_pending` is acceptable when host plugins, MCP, or secrets are still missing
- `core_install_incomplete` is not acceptable

### Stop rules

If this is only an initial evaluation, you can stop here.

Do not move to the next path until you confirm the repo-owned surface is healthy.

## Path 2: Recommended Full-Featured

### Best for

- heavy users who want the full shipped payload and governance surface installed in one pass
- individual developers who want fuller doctor and gate coverage
- team leads who want the closest thing to a real full-featured setup

### Goal

Install, sync, and verify everything the repo is responsible for, while explicitly surfacing the remaining host-side work.

### Prerequisites

- `git`
- `node` and `npm`
- `python3` or `python`
- Windows: `powershell` or `pwsh`
- Linux / macOS: `bash`
- on Linux / macOS, `pwsh` is strongly recommended for authoritative PowerShell doctor parity

### Recommended commands

Windows:

```powershell
pwsh -File .\scripts\bootstrap\one-shot-setup.ps1
pwsh -File .\check.ps1 -Profile full -Deep
```

Linux / macOS:

```bash
bash ./scripts/bootstrap/one-shot-setup.sh
bash ./check.sh --profile full --deep
```

### Reality boundary

Here, "full-featured" means full closure of the repo-governed surface. It does not mean the entire platform is magically fully ready.

The repo will try to automate:

- shipped payload installation
- bundled mirror alignment
- MCP active profile materialization
- deep doctor and runtime coherence verification
- scriptable external CLI installation where supported

The repo will not fake:

- host plugin provisioning
- host registration and authorization for plugin-backed MCP surfaces
- your provider secrets such as `OPENAI_API_KEY`

### Acceptance criteria

- install command exits `0`
- deep doctor completes
- repo-governed surfaces do not produce false warnings or misleading failures
- if host-managed prerequisites are still missing, `manual_actions_pending` is acceptable
- `fully_ready` should only be pursued after the host-side prerequisites are also complete

### Common misreads

- `npm install` for `claude-flow` can be slow without being broken
- `npm` deprecation warnings can be noisy without meaning failure
- on Linux / macOS, shell warnings caused by missing `pwsh` do not automatically mean the repo closure failed
- reusing provider keys already present in `settings.json` is expected behavior, not lost configuration

## Path 3: Enterprise-Governed

### Best for

- team leads
- platform engineering and DevOps owners
- organizations that need installation, verification, upgrades, and rollback to become institutionalized processes

### Goal

Go beyond "it works" and require:

- repeatable installation
- explicit version boundaries
- auditable manual follow-up
- provable upgrade and rollback hygiene

### Recommended practice

1. Pin a release version instead of following `main` directly
2. Run the one-shot bootstrap against a standard target root
3. Run the deep doctor and keep the resulting artifacts
4. Maintain a host-side provisioning checklist
5. Mark the environment production-ready only after that checklist is complete

### Minimum governance checklist

- record the release version and commit
- record the install target root
- record the install and doctor commands used
- record the missing host plugins, MCP surfaces, and provider secrets
- record who completed each manual provisioning step and when

### Recommended verification commands

Windows:

```powershell
pwsh -File .\scripts\bootstrap\one-shot-setup.ps1
pwsh -File .\check.ps1 -Profile full -Deep
pwsh -File .\scripts\verify\vibe-version-consistency-gate.ps1
pwsh -File .\scripts\verify\vibe-offline-skills-gate.ps1
pwsh -File .\scripts\verify\vibe-version-packaging-gate.ps1
```

Linux / macOS:

```bash
bash ./scripts/bootstrap/one-shot-setup.sh
bash ./check.sh --profile full --deep
```

### Enterprise stop rules

- if `core_install_incomplete`, stop rollout immediately
- if version consistency, offline closure, or packaging governance gates fail, stop the upgrade
- if host-side provisioning ownership is unclear, do not claim the team is ready
- if no doctor artifacts were captured, do not treat the installation as a formal delivery

## How to choose

| Your goal | Recommended path | Decision rule |
| --- | --- | --- |
| I just want to see it run | Minimum viable | `manual_actions_pending` is acceptable |
| I want full repo-owned closure | Recommended full-featured | you accept slower installs and deeper verification |
| I need to deliver this to a team or org | Enterprise-governed | you need auditability, repeatability, and rollback safety |

## Shared interpretation after install

After the install, do not only ask "did the command fail".

Ask instead:

- is the repo-governed surface now closed
- did the deep doctor explicitly tell us what manual actions remain
- should the state be `fully_ready`, `manual_actions_pending`, or `core_install_incomplete`

That framing is more important than "it looked mostly fine".

## Related entry points

- [`../README.en.md`](../README.en.md)
- [`one-shot-setup.md`](./one-shot-setup.md)
- [`runtime-freshness-install-sop.md`](./runtime-freshness-install-sop.md)
- [`external-tooling/README.md`](./external-tooling/README.md)
