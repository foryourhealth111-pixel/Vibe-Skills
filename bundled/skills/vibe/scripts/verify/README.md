This directory stores optional verification scripts for CI and local smoke checks.

For a single entrypoint that ties route probing, semantic expansion, threshold tuning, and gates together, read:
- `..\..\docs\blackbox-probe-and-enhancement-playbook.md`

- `vibe-routing-smoke.ps1`: runtime-neutral terminology and M/L/XL routing behavior smoke tests.
- `vibe-pack-routing-smoke.ps1`: validates pack router config integrity, thresholds, and alias safety.
- `vibe-soft-migration-practice.ps1`: practical soft-migration checks for alias routing and legacy fallback behavior.
- `vibe-pack-regression-matrix.ps1`: broad pack-level regression matrix and determinism checks.
- `vibe-keyword-precision-audit.ps1`: bilingual keyword precision audit (EN/ZH), cross-pack interference gap checks, and full skill-by-skill routing sweep.
- `vibe-skill-index-routing-audit.ps1`: per-skill keyword index routing checks using common Chinese business phrases and ambiguous same-pack scenarios.
- `vibe-routing-stability-gate.ps1`: synonym-group and task-cross routing gate. Reports `route_stability`, `top1_top2_gap`, `fallback_rate`, and `misroute_rate`, with optional strict thresholds.
- `vibe-config-parity-gate.ps1`: config parity gate for main vs bundled VCO JSON configs using normalized structural comparison + hash + diff-path output.
- `vibe-version-consistency-gate.ps1`: release metadata consistency gate across `config/version-governance.json`, maintenance markers, changelog header, and release ledger.
- `vibe-version-packaging-gate.ps1`: validates version/source-of-truth and packaging mirror consistency between canonical root and `bundled/skills/vibe`.
- `vibe-context-retro-smoke.ps1`: validates Context Retro Advisor integration in SKILL/protocol/fallback docs and main/bundled sync for retro-critical files.
- `vibe-retro-context-regression-matrix.ps1`: fixed-case regression matrix for retro trigger thresholds and CF-1..CF-6 classification stability.
- `cer-compare.ps1`: compares two CER JSON reports and outputs Markdown/JSON delta summaries (pattern/fallback/stability/context-pressure/gap).
- `vibe-retro-safety-gate.ps1`: full retro safety gate (trigger/classification/routing/pack smoke + protected-file hash invariance) to prove retro flow does not degrade VCO configs/protocols.
- `vibe-external-corpus-gate.ps1`: baseline vs candidate gate for external-corpus-driven skill-index updates, with optional smoke chain execution.
- `vibe-openspec-governance-gate.ps1`: validates zero-conflict OpenSpec governance integration (routing unchanged + grade-based OpenSpec advice + M-lite governance script behavior).
- `vibe-gsd-overlay-gate.ps1`: validates GSD-Lite overlay trigger semantics through unified VCO route output (scope gating + mode enforcement + routing invariance).
- `vibe-prompt-overlay-gate.ps1`: validates prompts.chat-oriented prompt overlay semantics (prompt/doc ambiguity detection + confirm_required override + routing invariance outside collision cases).
- `vibe-memory-governance-gate.ps1`: validates memory governance advice semantics (state_store/Serena/ruflo/Cognee boundaries + episodic-memory disabled) and route invariance across rollout stages.
- `vibe-data-scale-overlay-gate.ps1`: validates data-scale overlay semantics (real file probe, small/large recommendation, soft confirm, strict auto-override, and off-stage invariance). Generated fixtures are cleaned up automatically unless `-KeepFixtures` is used.
- `vibe-llm-acceleration-overlay-gate.ps1`: validates GPT‑5.2 LLM acceleration overlay semantics (explicit `/vibe` gating + shadow-mode non-mutation) using a mock provider (no API key required).
- `vibe-retrieval-overlay-gate.ps1`: validates retrieval overlay semantics (profile selection + query/source/rerank plan + strict ambiguity confirmation) and ensures post-route non-mutating behavior.
- `vibe-exploration-overlay-gate.ps1`: validates exploration overlay semantics (intent/domain inference + soft recommendation + strict confirmation) and ensures post-route non-mutating behavior.
- `vibe-quality-debt-overlay-gate.ps1`: validates quality-debt overlay semantics (risk scoring + strict confirm advice + optional analyzer graceful degradation + route invariance).
- `vibe-framework-interop-gate.ps1`: validates Ivy framework-interop overlay semantics (cross-framework migration signal detection + strict confirm advice + optional analyzer graceful degradation + route invariance).
- `vibe-ml-lifecycle-overlay-gate.ps1`: validates Made-With-ML inspired lifecycle overlay semantics (stage detection + artifact evidence checks + strict confirm advice + route invariance).
- `vibe-python-clean-code-overlay-gate.ps1`: validates Python clean-code overlay semantics (Python file auto-trigger + principle/anti-pattern scoring + strict confirm advice + route invariance).
- `vibe-system-design-overlay-gate.ps1`: validates system-design-primer overlay semantics (architecture signal + coverage dimensions + strict confirm advice + route invariance).
- `vibe-cuda-kernel-overlay-gate.ps1`: validates LeetCUDA-inspired CUDA kernel overlay semantics (CUDA optimization signal + coverage dimensions + strict confirm advice + route invariance).
- `vibe-observability-gate.ps1`: validates observability policy behavior (privacy-safe telemetry fields + profile IDs + deterministic route event capture).
- `vibe-heartbeat-gate.ps1`: validates heartbeat runtime guard behavior (lifecycle pulse collection, strict stall signaling, and policy-off disable semantics).
- `vibe-routing-probe-trace.ps1`: runs multi-case route probes and emits per-stage data-flow traces plus runtime-state prompts to inspect pack and overlay injection behavior end-to-end.
- `vibe-routing-probe-research.ps1`: runs a larger engineering research matrix (ambiguous vs specific vs overlay-targeted cases), validates stage-chain integrity, summarizes overlay injection statistics, and emits report-ready Markdown/JSON artifacts.
- `vibe-deep-discovery-gate.ps1`: validates Deep Discovery mode semantics across `off/shadow/soft/strict` (trigger/interview/contract/filter, route mutation boundaries, and fallback safety).
- `vibe-deep-discovery-scenarios.ps1`: executes multi-scenario Deep Discovery probe runs and outputs stage integrity, contract completeness, filter-application status, and runtime digest snapshots for engineering analysis.
- `vibe-overlay-threshold-sensitivity-scan.ps1`: runs 0.05-step sensitivity scan for overlay `signal_relaxed_min_score` (`data_scale`, `framework_interop`, `ml_lifecycle`) and outputs an optimal-threshold recommendation table (optionally applies to config + bundled config).

Related rollout utility:

- `..\governance\set-openspec-rollout.ps1`: stage switch helper for `off | shadow | soft-lxl-planning | strict-lxl-planning`.
- `..\governance\publish-openspec-soft-rollout.ps1`: single-command soft rollout with precheck -> switch -> postcheck. Automatic rollback is disabled; failures emit manual rollback command and require explicit user confirmation.
- `..\governance\set-gsd-overlay-rollout.ps1`: GSD-Lite overlay stage switch helper for `off | shadow | soft-lxl-planning | strict-lxl-planning`.

## Quick Start (Retro Checks)

Run context retro smoke + deterministic matrix:

```powershell
& ".\vibe-context-retro-smoke.ps1"
& ".\vibe-retro-context-regression-matrix.ps1"
& ".\vibe-retro-safety-gate.ps1"
```

## Quick Start (Routing Stability Gate)

Run default gate (recommended first pass):

```powershell
& ".\vibe-routing-stability-gate.ps1" -WriteArtifacts
```

Run strict gate (after default gate is passing consistently):

```powershell
& ".\vibe-routing-stability-gate.ps1" -Strict -WriteArtifacts
```

Run config parity gate (main vs bundled):

```powershell
& ".\vibe-config-parity-gate.ps1" -WriteArtifacts
```

Run version consistency gate:

```powershell
& ".\vibe-version-consistency-gate.ps1" -WriteArtifacts
```

Run version + packaging governance gate:

```powershell
& ".\vibe-version-packaging-gate.ps1" -WriteArtifacts
```

Run OpenSpec governance gate:

```powershell
& ".\vibe-openspec-governance-gate.ps1"
```

Run GSD overlay trigger gate:

```powershell
& ".\vibe-gsd-overlay-gate.ps1"
```

Run Prompt overlay trigger gate:

```powershell
& ".\vibe-prompt-overlay-gate.ps1"
```

Run Memory governance trigger gate:

```powershell
& ".\vibe-memory-governance-gate.ps1"
```

Run Data scale overlay trigger gate:

```powershell
& ".\vibe-data-scale-overlay-gate.ps1"
```

Run LLM acceleration overlay trigger gate (mock provider):

```powershell
& ".\vibe-llm-acceleration-overlay-gate.ps1"
```

Run Retrieval overlay trigger gate:

```powershell
& ".\vibe-retrieval-overlay-gate.ps1"
```

Run Exploration overlay trigger gate:

```powershell
& ".\vibe-exploration-overlay-gate.ps1"
```

Run Quality debt overlay trigger gate:

```powershell
& ".\vibe-quality-debt-overlay-gate.ps1"
```

Run Framework interop overlay trigger gate:

```powershell
& ".\vibe-framework-interop-gate.ps1"
```

Run ML lifecycle overlay trigger gate:

```powershell
& ".\vibe-ml-lifecycle-overlay-gate.ps1"
```

Run Python clean-code overlay trigger gate:

```powershell
& ".\vibe-python-clean-code-overlay-gate.ps1"
```

Run System design overlay trigger gate:

```powershell
& ".\vibe-system-design-overlay-gate.ps1"
```

Run CUDA kernel overlay trigger gate:

```powershell
& ".\vibe-cuda-kernel-overlay-gate.ps1"
```

Run observability gate:

```powershell
& ".\vibe-observability-gate.ps1"
```

Run heartbeat gate:

```powershell
& ".\vibe-heartbeat-gate.ps1"
```

Run route probe trace (white-box data-flow inspection):

```powershell
& ".\vibe-routing-probe-trace.ps1" -IncludePrompt
```

Run route probe research matrix (engineering report):

```powershell
& ".\vibe-routing-probe-research.ps1" -DefaultIncludePrompt
```

Run Deep Discovery gate:

```powershell
& ".\vibe-deep-discovery-gate.ps1"
```

Run Deep Discovery scenarios:

```powershell
& ".\vibe-deep-discovery-scenarios.ps1" -Mode shadow
& ".\vibe-deep-discovery-scenarios.ps1" -Mode soft
& ".\vibe-deep-discovery-scenarios.ps1" -Mode strict
```

Run overlay threshold sensitivity scan (0.05 step):

```powershell
& ".\vibe-overlay-threshold-sensitivity-scan.ps1" -Step 0.05
```

Keep generated fixture files for manual inspection:

```powershell
& ".\vibe-data-scale-overlay-gate.ps1" -KeepFixtures
```

Compare two CER reports and emit delta artifacts:

```powershell
& ".\cer-compare.ps1" `
  -BaselineCerPath "..\..\outputs\retro\cer\baseline.json" `
  -CurrentCerPath "..\..\outputs\retro\cer\current.json" `
  -OutputMarkdownPath "..\..\outputs\retro\compare\delta.md" `
  -OutputJsonPath "..\..\outputs\retro\compare\delta.json" `
  -UpdateCurrentComparison
```

Interpretation:
- `fallback_rate` delta < 0 is better.
- `stability` delta > 0 is better.
- `context_pressure` delta < 0 is better.
- `route_gap` delta > 0 usually means better route separability.

## External Corpus Gate

Build candidate suggestions from external prompt corpus and evaluate them safely:

```powershell
& "..\research\extract-prompt-signals.ps1" `
  -SourceRoot "..\..\third_party\system-prompts-mirror" `
  -OutputPath "..\..\outputs\external-corpus\prompt-signals.json"

& "..\research\generate-vco-suggestions.ps1" `
  -SignalPath "..\..\outputs\external-corpus\prompt-signals.json" `
  -SourceRoot "..\..\third_party\system-prompts-mirror" `
  -OutputDirectory "..\..\outputs\external-corpus"

& ".\vibe-external-corpus-gate.ps1" `
  -CandidateSkillIndexPath "..\..\outputs\external-corpus\skill-keyword-index.candidate.json" `
  -RunExistingSmoke
```

For strict CI mode (smoke errors block merge):

```powershell
& ".\vibe-external-corpus-gate.ps1" `
  -CandidateSkillIndexPath "..\..\outputs\external-corpus\skill-keyword-index.candidate.json" `
  -RunExistingSmoke `
  -FailOnSmokeError
```

Output artifacts:
- `outputs/external-corpus/prompt-signals.json`
- `outputs/external-corpus/vco-suggestions.json`
- `outputs/external-corpus/vco-suggestions.md`
- `outputs/external-corpus/skill-keyword-index.candidate.json`
- `outputs/external-corpus/external-corpus-gate.json`
- `outputs/external-corpus/external-corpus-gate.md`

## Offline Adaptive Suggestions

Build environment/user-profile-aware threshold suggestions from telemetry (manual apply only):

```powershell
& "..\learn\vibe-adaptive-train.ps1" -LookbackDays 7
```

Output artifacts:
- `outputs/learn/vibe-adaptive-suggestions.json`
- `outputs/learn/vibe-adaptive-suggestions.md`
