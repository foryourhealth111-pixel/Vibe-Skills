# VCO Blackbox Probe & Enhancement Playbook

This document organizes the VCO blackbox inspection and enhancement scripts into one reusable engineering workflow.

## 1. What This Module Set Solves

- Make route/overlay behavior observable (no more blackbox guesswork).
- Mine user-style task language from route records and convert it into safe overlay vocabulary expansion.
- Keep probe-and-enhancement guidance honest to the current canonical tool surface, so historical utilities are clearly marked instead of treated as active scripts.
- Keep canonical config truth and generated-compatibility assumptions consistent after updates.

## 2. Module Map

| Module | Script | Purpose | Primary Outputs |
| --- | --- | --- | --- |
| Scientific Pack Probe | `scripts/verify/probe-scientific-packs.ps1` | Pack-focused routing probe matrix with per-case pack/skill match summaries | `outputs/verify/route-probe-scientific/*` |
| Research Matrix Probe | `scripts/verify/vibe-routing-probe-research.ps1` | Multi-scenario routing study (ambiguous/specific/overlay-targeted/runtime prompt) with stage integrity checks | `outputs/verify/route-probe-research/*` |
| Deep Discovery Gate | `scripts/verify/vibe-deep-discovery-gate.ps1` | Validate Deep Discovery rollout semantics (`off/shadow/soft/strict`) and route mutation boundaries | terminal assertions + optional probe artifacts |
| Deep Discovery Scenarios | `scripts/verify/vibe-deep-discovery-scenarios.ps1` | Scenario-based study for Deep Discovery trigger/interview/contract/filter behavior | `outputs/verify/deep-discovery-scenarios/*` |
| User Semantic Mining | `scripts/research/mine-user-semantic-overlay-signals.ps1` | Mine local route probe history and propose/apply overlay phrase additions | `outputs/user-semantic/user-overlay-lexicon.{json,md}` |
| Threshold Sensitivity Scan | _historical utility (not shipped in current canonical tree)_ | Keep as changelog/reference context only; do not use as an active runbook command | historical references only |
| Regression and Consistency Gates | `scripts/verify/vibe-config-parity-gate.ps1`, `scripts/verify/vibe-pack-routing-smoke.ps1`, `scripts/verify/vibe-routing-smoke.ps1` | Prevent canonical config drift and routing regressions | `outputs/verify/*` |

## 3. Runtime Injection Chain (How Data Actually Flows)

Expected stage chain:

`router.init -> router.config -> router.prepack -> deep_discovery.trigger -> deep_discovery.interview -> deep_discovery.contract -> deep_discovery.filter -> router.pack_scoring -> overlay.ai_rerank -> overlay.prompt -> overlay.data_scale -> overlay.exploration -> overlay.retrieval -> overlay.bundle -> router.final`

Key injection points:

- `router.prepack`:
  - prompt normalization (including `/vibe` and `$vibe` prefix handling for scoring),
  - alias/canonical resolution,
  - language-mix and requested-skill signals.
- `deep_discovery.*`:
  - capability hit detection and trigger scoring,
  - interview question proposal,
  - intent contract synthesis (goal/deliverable/constraints/capabilities),
  - mode-gated candidate filtering simulation/application.
- `overlay.*` stages:
  - each overlay emits `*_advice` (and optional route override metadata by policy),
  - bundled summary can fold outside-scope overlays in runtime prompt.
- `router.final`:
  - selected pack/skill, confidence, route mode, reason, and observability metadata.

Model-visible final text:

- Look at runtime prompt / route evidence samples in:
  - `outputs/verify/route-probe-research/route-probe-research-summary-*.md`
  - `outputs/verify/route-probe-scientific/*`

## 4. Standard Repro Workflow

### Step A: Observe current routing and injection behavior

```powershell
& ".\scripts\verify\vibe-routing-probe-research.ps1" -DefaultIncludePrompt
```

### Step A2: Validate Deep Discovery behavior

```powershell
& ".\scripts\verify\vibe-deep-discovery-gate.ps1"
& ".\scripts\verify\vibe-deep-discovery-scenarios.ps1" -Mode shadow
& ".\scripts\verify\vibe-deep-discovery-scenarios.ps1" -Mode soft
& ".\scripts\verify\vibe-deep-discovery-scenarios.ps1" -Mode strict
```

### Step B: Mine user semantics and expand overlay vocabulary

```powershell
& ".\scripts\research\mine-user-semantic-overlay-signals.ps1" -MinHits 2 -ApplyToConfig
```

If local history is small, use:

```powershell
& ".\scripts\research\mine-user-semantic-overlay-signals.ps1" -MinHits 1 -ApplyToConfig
```

### Step C: Historical threshold-scan note

The prior fixed-step threshold scan utility is referenced in changelog history, but it is not currently shipped in the canonical `scripts/verify/` tree. Treat those references as historical context until the utility is restored or replaced by a new governed operator.

### Step D: Run gates

```powershell
& ".\scripts\verify\vibe-config-parity-gate.ps1" -WriteArtifacts
& ".\scripts\verify\vibe-pack-routing-smoke.ps1"
& ".\scripts\verify\vibe-routing-smoke.ps1"
```

## 5. Where to Find Results Quickly

| Need | File |
| --- | --- |
| Stage integrity + per-case route outcomes | `outputs/verify/route-probe-research/route-probe-research-summary-*.md` |
| Model-visible runtime prompt examples | `outputs/verify/route-probe-research/route-probe-research-summary-*.md` (`Runtime State Prompt Samples`) |
| User semantic mining result | `outputs/user-semantic/user-overlay-lexicon.md` |
| Applied overlay phrase additions | `outputs/user-semantic/user-overlay-lexicon.json` (`accepted_additions`) |
| Threshold recommendation table | `outputs/verify/overlay-threshold-scan/overlay-threshold-scan.md` |
| Canonical config / compatibility topology check | `outputs/verify/vibe-config-parity-gate.md` |

## 6. Reuse Notes

- Routing/scoring now supports both `/vibe` and `$vibe` prefix normalization for robust probe experiments.
- Semantic mining script normalizes route command prefixes and ignores redacted prompts before phrase extraction.
- Threshold scan uses conservative tie-break by default: if metrics are equal, pick a higher threshold to reduce false positives.
