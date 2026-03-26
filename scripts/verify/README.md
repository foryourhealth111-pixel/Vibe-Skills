This directory stores optional verification scripts for CI and local smoke checks.

For a single entrypoint that ties route probing, semantic expansion, threshold tuning, and gates together, read:
- `..\..\docs\blackbox-probe-and-enhancement-playbook.md`

## Start Here

### Bootstrap Readiness

For the one-shot install/bootstrap path, the primary readiness gate is:

```powershell
pwsh -NoProfile -File .\vibe-bootstrap-doctor-gate.ps1 -WriteArtifacts
```

Pair it with MCP profile materialization when you need a fresh active MCP file:

```powershell
pwsh -NoProfile -File ..\setup\materialize-codex-mcp-profile.ps1 -Force
```

### Router AI Advice Connectivity Probe (#33)

This probe targets only the router AI advice path (intent/advice layer). It is advice-only and never rewrites canonical route decisions.

Run:

```powershell
pwsh -NoProfile -File .\vibe-router-ai-connectivity-gate.ps1 -WriteArtifacts
```

Typical states:
- `ok`
- `missing_credentials`
- `prefix_required`
- `provider_unreachable`
- `vector_diff_not_configured` / `vector_diff_missing_credentials` / `vector_diff_provider_unreachable` / `vector_diff_ok`

Result interpretation:
- Probe failures do not mean the whole platform is unusable.
- JSON artifact is machine-readable status + next steps.
- Markdown artifact is human-readable summary.
- Default JSON output: `outputs/verify/vibe-router-ai-connectivity-gate.json`
- Default Markdown output: `outputs/verify/vibe-router-ai-connectivity-gate.md`

- `gate-family-index.md`：verify family 导航入口；先按治理主题找 gate，再进入具体脚本。
- `../../docs/docs-information-architecture.md`：`docs/` 的正式信息架构与 cleanup-first 导航规则。
- `../../references/reference-asset-taxonomy.md`：`references/` 的 contract / registry / matrix / ledger 分类。
- `../../docs/plans/2026-03-08-repo-cleanliness-batch2-4-triage.md`：本轮 cleanup-first 的 Batch 2-4 拆分与 stop rules。
- `../../scripts/governance/README.md`：operator script surface；说明 sync / rollout / release / audit 的职责边界。
- `../../scripts/common/README.md`：shared helpers / wave runner / UTF-8 no BOM 写入原语。
## Cleanup-First Canonical Run Order

1. 触及 version / packaging / install / frontmatter 时，先跑 runtime integrity 家族 gate。
2. 每个 canonical 批次收口后，必跑 cleanliness / outputs / mirror hygiene 家族 gate。
3. 根据本次变更所属治理域，补跑对应 plane / overlay / capability / release family gate。
4. 只有在 planning board、promotion、release evidence 变化时，才补 closure / release-train / promotion gates。

## Phase-End Minimal Checklist

When the batch goal is "close the phase cleanly without regression", use this minimal sequence:

```powershell
pwsh -NoProfile -File .\..\governance\phase-end-cleanup.ps1 -WriteArtifacts
```

That wrapper keeps the cleanup order explicit:

1. purge `.tmp/`
2. refresh local excludes for `task_plan.md`, `findings.md`, `progress.md`
3. rerun `vibe-repo-cleanliness-gate.ps1`
4. rerun `vibe-output-artifact-boundary-gate.ps1`
5. run repo-safe node audit
6. run node cleanup in report-only mode

If the batch touched mirror / packaging surfaces, rerun the mirror-aware variant instead:

```powershell
pwsh -NoProfile -File .\..\governance\phase-end-cleanup.ps1 -WriteArtifacts -IncludeMirrorGates
```

## Gate Families

- **Runtime Integrity / Packaging**：`vibe-bom-frontmatter-gate.ps1`、`vibe-version-consistency-gate.ps1`、`vibe-version-packaging-gate.ps1`、`vibe-config-parity-gate.ps1`、`vibe-installed-runtime-freshness-gate.ps1`。
- **Cleanliness / Outputs / Mirror Hygiene**：`vibe-repo-cleanliness-gate.ps1`、`vibe-output-artifact-boundary-gate.ps1`、`vibe-mirror-edit-hygiene-gate.ps1`、`vibe-nested-bundled-parity-gate.ps1`。
- **Developer Entry / Contributor UX**：`vibe-developer-entry-gate.ps1`；验证 root README -> `CONTRIBUTING.md` -> zone / proof / plan surface 的开发者入口主链路。
- **Routing Core / Retro / Probe**：routing smoke / stability / retro / probe family。
- **Memory / Prompt / Overlay Governance**：memory、prompt、retrieval、data-scale、framework-interop、quality-debt、system-design、CUDA overlay family。
- **Plane Governance**：browserops、desktopops、docling、document、connector、discovery family。
- **Capability / Upstream / Release**：capability、role-pack、upstream value ops、promotion、release、observability family；upstream/distribution governance 新增 `vibe-third-party-disclosure-parity-gate.ps1`、`vibe-upstream-lock-coverage-gate.ps1`、`vibe-origin-provenance-gate.ps1`。

详见：`gate-family-index.md`
**Managed Runtime / Process Hygiene**: `vibe-node-zombie-gate.ps1` validates VCO-managed Node ownership, stale-process classification, and report-only cleanup safety boundaries.

**Platform Promotion Proof**: `vibe-platform-support-contract-gate.ps1`, `vibe-platform-doctor-parity-gate.ps1`, `vibe-linux-pwsh-proof-gate.ps1`, and `vibe-platform-promotion-bundle.ps1` form the platform-proof closure chain. They validate evidence wiring and truth-contract alignment from the canonical repo root; they do not auto-promote a platform lane and are not installed-runtime self-checks.

**Fallback Governance / Truth Honesty**: `vibe-no-silent-fallback-contract-gate.ps1`, `vibe-no-self-introduced-fallback-gate.ps1`, and `vibe-release-truth-consistency-gate.ps1` prove that degraded paths stay explicit, requirement-backed, and non-authoritative.

**Remediation Foundation / Proof Classes**: `vibe-remediation-foundation-gate.ps1` validates the remediation baseline: frozen runtime input packet, proof-class registry, shadow executor artifact, cleanup taxonomy, messy-task corpus, path ecology board, and promotion board.

## Fixture Taxonomy

- **Wave28 canonical pilot fixtures**: `fixtures/pilot-memory.json`, `fixtures/pilot-prompt.json`, `fixtures/pilot-browserops.json`, `fixtures/pilot-desktopops.json`. These are the only pilot inputs consumed by `vibe-pilot-scenarios.ps1` and referenced by `config/promotion-board.json`.
- **Gate-only mock fixtures**: `fixtures/prompt-asset-boost.mock.json` and `fixtures/llm-acceleration.mock.json`. They exist only to support their corresponding mock-provider gates and are not pilot assets.
- **Deprecated shadow fixtures**: legacy `*-shadow.json` pilot-name variants are intentionally removed from the active fixture set to prevent canonical/shadow naming ambiguity.

- `vibe-routing-smoke.ps1`: runtime-neutral terminology and M/L/XL routing behavior smoke tests.
- `vibe-pack-routing-smoke.ps1`: validates pack router config integrity, thresholds, and alias safety.
- `vibe-soft-migration-practice.ps1`: practical soft-migration checks for alias routing and legacy fallback behavior.
- `vibe-pack-regression-matrix.ps1`: broad pack-level regression matrix and determinism checks.
- `vibe-keyword-precision-audit.ps1`: bilingual keyword precision audit (EN/ZH), cross-pack interference gap checks, and full skill-by-skill routing sweep.
- `vibe-trigger-keyword-hygiene-gate.ps1`: trigger keyword hygiene gate (empty/whitespace/case-duplicate detection + cross-pack collision report, optional strict collision fail).
- `vibe-skill-index-routing-audit.ps1`: per-skill keyword index routing checks using common Chinese business phrases and ambiguous same-pack scenarios.
- `vibe-routing-stability-gate.ps1`: synonym-group and task-cross routing gate. Reports `route_stability`, `top1_top2_gap`, `fallback_rate`, and `misroute_rate`, with optional strict thresholds.
- `vibe-node-zombie-gate.ps1`: validates node zombie guardian safety (audit/report usefulness + cleanup never targets `external` or `unknown`) and emits proof artifacts.
- `vibe-config-parity-gate.ps1`: config parity gate for main vs bundled VCO JSON configs using normalized structural comparison + hash + diff-path output.
- `vibe-version-consistency-gate.ps1`: release metadata consistency gate across `config/version-governance.json`, maintenance markers, changelog header, and release ledger.
- `vibe-version-packaging-gate.ps1`: validates version/source-of-truth and packaging mirror consistency between canonical root and `bundled/skills/vibe`.
- `vibe-repo-cleanliness-gate.ps1`: classifies dirty working-tree entries, blocks visible local noise/runtime artifacts, and reports governed workset pressure separately from local hygiene.
- `vibe-output-artifact-boundary-gate.ps1`: governs the legacy tracked `outputs/**` allowlist so runtime outputs and long-term fixtures stay explicitly separated.
- `vibe-installed-runtime-freshness-gate.ps1`: validates installed runtime freshness between canonical root and `${TARGET_ROOT}/skills/vibe`, and can write a runtime freshness receipt after install.
- `vibe-bootstrap-doctor-gate.ps1`: classifies one-shot bootstrap readiness across settings, plugins, external tools, MCP surfaces, and secret-bound follow-up actions.
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
- `probe-scientific-packs.ps1`: runs a pack-focused scientific routing probe matrix and emits report-ready Markdown/JSON summaries for pack-selection validation.
- `vibe-routing-probe-research.ps1`: runs a larger engineering research matrix (ambiguous vs specific vs overlay-targeted cases), validates stage-chain integrity, summarizes overlay injection statistics, and emits report-ready Markdown/JSON artifacts.
- `vibe-deep-discovery-gate.ps1`: validates Deep Discovery mode semantics across `off/shadow/soft/strict` (trigger/interview/contract/filter, route mutation boundaries, and fallback safety).
- `vibe-deep-discovery-scenarios.ps1`: executes multi-scenario Deep Discovery probe runs and outputs stage integrity, contract completeness, filter-application status, and runtime digest snapshots for engineering analysis.
- `vibe-router-contract-gate.ps1`: validates router contract invariants, advice shape, and governed route output structure before higher-layer rollout or promotion work.

## Wave40-63 Gates (Stop-Ship / Governance)

- `vibe-bom-frontmatter-gate.ps1`: validates frontmatter-sensitive files (`SKILL.md` 等) 在 byte 0 直接可见 `---`，并检查 UTF-8 BOM 是否会遮挡解析器。
- `vibe-wave40-63-board-gate.ps1`: validates the formal Wave40-63 execution board, contiguous wave coverage, bound gates, and required evidence assets.
- `vibe-capability-dedup-gate.ps1`: validates capability dedup clusters, canonical owners, overlap closure anchors, and dedup governance evidence.
- `vibe-adaptive-routing-readiness-gate.ps1`: validates adaptive routing shadow-ready governance, replay contract linkage, telemetry presence, and readiness support assets.
- `vibe-upstream-value-ops-gate.ps1`: validates continuous value-extraction workstreams, quality-bar linkage, and upstream value-ops evidence coverage.

### Quick Start (Wave40-63)

Run the runtime-hardening gate first, then the Wave40-63 governance closure gates:

```powershell
& ".\\vibe-bom-frontmatter-gate.ps1" -WriteArtifacts
& ".\\vibe-wave40-63-board-gate.ps1" -WriteArtifacts
& ".\\vibe-capability-dedup-gate.ps1" -WriteArtifacts
& ".\\vibe-adaptive-routing-readiness-gate.ps1" -WriteArtifacts
& ".\\vibe-upstream-value-ops-gate.ps1" -WriteArtifacts
```

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

Run node zombie guardian safety gate (when touching `node-zombie-guardian`):

```powershell
& ".\vibe-node-zombie-gate.ps1" -WriteArtifacts
```

Notes:
- If you added/edited `bundled/skills/node-zombie-guardian/`, regenerate `config/skills-lock.json` via `vibe-generate-skills-lock.ps1` before running offline-skill parity gates.

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

Run managed Node zombie safety gate:

```powershell
& ".\vibe-node-zombie-gate.ps1" -WriteArtifacts
```

Run repo cleanliness gate (local hygiene first):

```powershell
& ".\..\governance\install-local-worktree-excludes.ps1"
& ".\vibe-repo-cleanliness-gate.ps1" -WriteArtifacts
& ".\vibe-output-artifact-boundary-gate.ps1" -WriteArtifacts
```

Run developer-entry gate (contributor entry surface only):

```powershell
& ".\vibe-developer-entry-gate.ps1" -WriteArtifacts
```

Notes:
- This gate validates the documentation entry contract only; it does not mutate runtime state.
- Current contract source: `..\..\references\developer-entry-contract.md`

Run installed runtime freshness gate (canonical repo only):

```powershell
& ".\vibe-installed-runtime-freshness-gate.ps1" -WriteReceipt
```

Notes:
- `vibe-version-consistency-gate.ps1`, `vibe-version-packaging-gate.ps1`, `vibe-config-parity-gate.ps1`, `release-cut.ps1`, and `sync-bundled-vibe.ps1` are protected by the execution-context lock and must run from the canonical repo tree.
- Runtime freshness is a separate post-install governance layer; it does not replace repo parity gates.
- Installed-runtime directory comparisons inherit `packaging.allow_bundled_only`, so intentionally packaged bundled-only files remain allowed after install.
- `check.ps1` / `check.sh` now verify the runtime freshness receipt and invoke the freshness gate when canonical repo execution is available.
- In shell-only environments without `pwsh`, `check.sh` warns and skips authoritative runtime freshness execution instead of emitting a false receipt hard-fail.

Run Linux promotion proof gates (evidence closure only, no implied promotion):

```powershell
& ".\vibe-linux-pwsh-proof-gate.ps1" -WriteArtifacts
& ".\vibe-platform-promotion-bundle.ps1" -WriteArtifacts
```

Notes:
- These gates verify that Linux promotion prerequisites, replay contracts, and proof-bundle wiring are aligned.
- They do not by themselves upgrade `codex/linux` to `full-authoritative`.
- Actual promotion still requires frozen fresh-machine Linux evidence and replay allowlist synchronization.

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

Run scientific pack probe (pack-focused route study):

```powershell
& ".\probe-scientific-packs.ps1" -DefaultIncludePrompt
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

Run router contract gate:

```powershell
& ".\vibe-router-contract-gate.ps1" -WriteArtifacts
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

## Additional Governance / Utility Gates

- `vibe-manual-apply-policy-gate.ps1`: validates manual apply policy boundaries and exception handling.
- `vibe-release-evidence-bundle-gate.ps1`: validates release evidence bundle completeness.
- `vibe-rollout-proposal-boundedness-gate.ps1`: validates rollout proposals stay bounded and evidence-backed.
- `vibe-upstream-reaudit-matrix-gate.ps1`: validates upstream re-audit matrix completeness and linkage.
- `vibe-ops-dashboard-gate.ps1`: validates ops dashboard governance assets.
- `vibe-wave83-100-closure-gate.ps1`: validates Wave83-100 closure board and evidence completeness.
- `vibe-subagent-handoff-gate.ps1`: validates subagent handoff governance artifacts.
- `vibe-secret-scan.ps1`: lightweight secret scanning utility for governed verification runs.
- `vibe-generate-skills-lock.ps1`: emits / validates generated skills lock metadata.
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

## Wave19-30 Governance Gates

新增的 Wave19-30 门禁如下：

```powershell
& ".\vibe-ecosystem-absorption-contract-gate.ps1"
& ".\vibe-memory-tier-gate.ps1"
& ".\vibe-mem0-backend-gate.ps1"
& ".\vibe-letta-contract-gate.ps1"
& ".\vibe-prompt-intelligence-assets-gate.ps1"
& ".\vibe-browserops-gate.ps1"
& ".\vibe-desktopops-shadow-gate.ps1"
& ".\vibe-cross-plane-conflict-gate.ps1"
& ".\vibe-promotion-board-gate.ps1"
& ".\vibe-pilot-scenarios.ps1"
```

建议执行顺序：
1. admission / memory / prompt 基础 gates
2. browser / desktop / conflict gates
3. promotion board / pilot gates
4. config parity / version packaging gates


## Wave19-30 Absorption Gates

Run ecosystem admission and new four-plane governance gates:

```powershell
& ".\vibe-ecosystem-absorption-contract-gate.ps1"
& ".\vibe-memory-tier-gate.ps1"
& ".\vibe-mem0-backend-gate.ps1"
& ".\vibe-letta-contract-gate.ps1"
& ".\vibe-prompt-intelligence-assets-gate.ps1"
& ".\vibe-browserops-gate.ps1"
& ".\vibe-desktopops-shadow-gate.ps1"
& ".\vibe-cross-plane-conflict-gate.ps1"
& ".\vibe-promotion-board-gate.ps1"
& ".\vibe-pilot-scenarios.ps1"
```

Recommended sequence for Wave29-30 packaging closure:

```powershell
& ".\vibe-config-parity-gate.ps1"
& ".\vibe-version-packaging-gate.ps1"
```

## Wave31-33 Governance Gates

Mirror topology and runtime coherence additions:

```powershell
& ".\vibe-nested-bundled-parity-gate.ps1" -WriteArtifacts
& ".\vibe-mirror-edit-hygiene-gate.ps1" -WriteArtifacts
& ".\vibe-release-install-runtime-coherence-gate.ps1" -WriteArtifacts
```

Operational notes:

- `vibe-nested-bundled-parity-gate.ps1` is the blocking gate for `nested_bundled` drift.
- `vibe-mirror-edit-hygiene-gate.ps1` is intended for dirty-tree / PR hygiene; it may fail while mirror sync is intentionally pending.
- `vibe-release-install-runtime-coherence-gate.ps1` checks the config + docs + install/check script contract for release/install/runtime boundaries.
- `check.ps1` and `check.sh` invoke runtime freshness and coherence; they do **not** invoke mirror edit hygiene by default.
- runtime freshness and coherence stay authoritative only when the scripts run from the canonical repo root.

## Wave34-39 Governance Gates

Upstream corpus / productization / release-closure additions:

```powershell
& ".\vibe-upstream-corpus-manifest-gate.ps1" -WriteArtifacts
& ".\vibe-upstream-mirror-freshness-gate.ps1" -WriteArtifacts
& ".\vibe-third-party-disclosure-parity-gate.ps1" -WriteArtifacts
& ".\vibe-upstream-lock-coverage-gate.ps1" -WriteArtifacts
& ".\vibe-origin-provenance-gate.ps1" -WriteArtifacts
& ".\vibe-docling-contract-gate.ps1" -WriteArtifacts
& ".\vibe-connector-admission-gate.ps1" -WriteArtifacts
& ".\vibe-role-pack-governance-gate.ps1" -WriteArtifacts
& ".\vibe-capability-catalog-gate.ps1" -WriteArtifacts
& ".\vibe-promotion-board-gate.ps1" -WriteArtifacts
& ".\vibe-pilot-scenarios.ps1"
& ".\vibe-deep-extraction-pilot-gate.ps1" -WriteArtifacts
```

Operational notes:

- `vibe-upstream-corpus-manifest-gate.ps1` and `vibe-upstream-mirror-freshness-gate.ps1` together define the 15-project corpus baseline plus runtime mirror freshness evidence.
- `vibe-third-party-disclosure-parity-gate.ps1` validates that public disclosure stays traceable to canonical upstream registries.
- `vibe-upstream-lock-coverage-gate.ps1` validates upstream-lock governance metadata coverage (license / tier / redistribution posture / disclosure flags).
- `vibe-origin-provenance-gate.ps1` validates the `ORIGIN.md` provenance contract and allows policy-only mode while `vendor/**` contains scaffolding only.
- `vibe-docling-contract-gate.ps1`, `vibe-connector-admission-gate.ps1`, `vibe-role-pack-governance-gate.ps1`, and `vibe-capability-catalog-gate.ps1` validate that absorbed value lands as governance/product surfaces rather than second execution owners.
- `vibe-promotion-board-gate.ps1` is the bridge from Wave31-38 governance assets into Wave39 release evidence; it should be part of release-cut, not an optional afterthought.
- `vibe-pilot-scenarios.ps1` covers the execution-plane fixtures plus `pilot-deep-extraction.json`; `vibe-deep-extraction-pilot-gate.ps1` is the release-closure rollup gate.

## Quick Start (Wave64-82)

Run the Wave64-82 gate chain after the prior runtime / Wave40-63 gates are green:

```powershell
& ".\vibe-memory-runtime-v3-gate.ps1" -WriteArtifacts
& ".\vibe-mem0-softrollout-gate.ps1" -WriteArtifacts
& ".\vibe-letta-policy-conformance-gate.ps1" -WriteArtifacts
& ".\vibe-browserops-scorecard-gate.ps1" -WriteArtifacts
& ".\vibe-browserops-softrollout-gate.ps1" -WriteArtifacts
& ".\vibe-desktopops-replay-gate.ps1" -WriteArtifacts
& ".\vibe-desktopops-softrollout-gate.ps1" -WriteArtifacts
& ".\vibe-docling-contract-v2-gate.ps1" -WriteArtifacts
& ".\vibe-document-plane-benchmark-gate.ps1" -WriteArtifacts
& ".\vibe-connector-scorecard-gate.ps1" -WriteArtifacts
& ".\vibe-connector-action-ledger-gate.ps1" -WriteArtifacts
& ".\vibe-prompt-intelligence-productization-gate.ps1" -WriteArtifacts
& ".\vibe-cross-plane-task-contract-gate.ps1" -WriteArtifacts
& ".\vibe-cross-plane-replay-gate.ps1" -WriteArtifacts
& ".\vibe-promotion-scorecard-gate.ps1" -WriteArtifacts
& ".\vibe-ops-cockpit-gate.ps1" -WriteArtifacts
& ".\vibe-rollback-drill-gate.ps1" -WriteArtifacts
& ".\vibe-release-train-v2-gate.ps1" -WriteArtifacts
```

Run closure only after the board is marked complete:

```powershell
& ".\vibe-wave64-82-closure-gate.ps1" -WriteArtifacts
```
