# Public Skill Surface Decoupling Execution Plan

## Internal Grade

L

The work spans multiple ownership domains, but it should stay serial and proof-driven because packaging, install, uninstall, and verification semantics are tightly coupled.

## Objective

Shift Vibe-Skills from "broad top-level official skill projection" to "small public runtime surface with internal specialist corpus" without regressing host behavior or uninstall safety.

## Current Evidence

- `config/runtime-core-packaging.json` makes `full` the default profile and currently maps it to `bundled/skills -> skills`.
- `config/runtime-core-packaging.minimal.json` already implements `allowlist_only_plus_canonical_vibe`.
- `packages/installer-core/src/vgo_installer/materializer.py` already supports canonical `skills/vibe`, allowlisted top-level materialization, and generated nested compatibility.
- `packages/skill-catalog/catalog/profiles/*.json` already separate minimal allowlist selection from full-corpus selection.
- uninstall still relies primarily on created-file and static inventory recovery rather than one authoritative owned root model.
- current representative host/runtime probe baseline:
  - `pytest -q tests/runtime_neutral/test_router_bridge.py tests/runtime_neutral/test_openclaw_runtime_core.py tests/runtime_neutral/test_claude_preview_scaffold.py tests/runtime_neutral/test_opencode_managed_preview.py`
  - result: `14 passed, 4 subtests passed`
- current representative governance/memory probe baseline:
  - `pytest -q tests/runtime_neutral/test_governed_runtime_bridge.py tests/runtime_neutral/test_root_child_hierarchy_bridge.py tests/runtime_neutral/test_memory_runtime_activation.py`
  - result: `10 passed, 11 subtests passed`

## Target Topology

### Public Surface

- `skills/vibe/` remains the canonical public runtime root
- optional host-required public companions may exist only when explicitly declared
- peer top-level official skills are no longer the default broad install outcome

### Internal Surface

- broad bundled specialist corpus lives under a Vibe-owned internal root, for example `skills/vibe/catalog/skills/` or `skills/vibe/bundled/skills/`
- internal catalog metadata is resolved from the canonical Vibe-owned root instead of assuming host-visible peer directories

### Compatibility Surface

- generated nested compatibility remains optional and derived
- any extra public skill projection becomes an explicit compatibility layer with its own allowlist contract

### Ownership Surface

- authoritative runtime ownership is centered on `skills/vibe/`
- authoritative sidecar ownership is centered on `.vibeskills/`
- managed JSON/config mutations are treated as rollback records, not owned file trees
- legacy broad public skill directories are migration cleanup targets, not future steady-state runtime truth

## Design Decisions

1. Separate "managed capability breadth" from "public top-level projection breadth".
2. Introduce a packaging mode that installs the full internal corpus without copying it to `<TARGET_ROOT>/skills/*`.
3. Keep `managed_skill_inventory` for runtime-critical public skills, but add a separate contract for internal specialist corpus ownership.
4. Convert uninstall to remove Vibe-owned roots by authoritative ledger ownership, not by reconstructing broad peer directories heuristically.
5. Keep host-visible compatibility projections opt-in and host-scoped.
6. Change runtime descriptor resolution before changing the default full-profile topology.
7. Preserve one explicit compatibility toggle so rollback can restore legacy public projection without undoing the internal corpus work.

## Implementation Standards

### Subjective Standards

- Prefer designs where ownership is obvious from the module boundary.
- Prefer contracts and descriptors over path conventions and fallback guesses.
- Treat public host-visible directories as product API surface and minimize them deliberately.
- Treat compatibility layers as temporary, explicit, and auditable.
- Keep runtime authority singular: routing, catalog metadata, and install topology must not create parallel truth surfaces.

### Objective Standards

- `skills/vibe` remains the canonical public runtime root across all supported hosts.
- The default broad profile no longer relies on `bundled/skills -> skills` as its steady-state delivery model.
- Runtime-core can resolve official skill descriptors from the internal corpus without requiring top-level installed official skill directories.
- Installer-core writes authoritative ownership records sufficient for uninstall to delete by root class.
- Uninstall preview and actual uninstall must agree on managed ownership outcomes.
- Legacy fallback usage must be observable during migration.
- Every phase must have at least one automated verification gate before the next phase begins.
- `codex`, `claude-code`, `openclaw`, and `opencode` must each pass at least one host-realistic installed-runtime task probe before the topology cutover is considered complete.
- Routing, governance, and memory behavior must be validated both by contract tests and by task-style runtime probes.

## Multi-Host Validation Matrix

The following hosts are mandatory for acceptance:

| Host | Required Surface | Required Behaviors | Existing Baseline Assets | New Deep-Probe Requirement |
|:---|:---|:---|:---|:---|
| `codex` | governed lane, installed runtime, duplicate-surface hygiene | installed `skills/vibe` entry, routing, governed execution, cleanup, uninstall | `test_installed_runtime_scripts.py`, install/check path docs | add task probes for planning/debug/governed execution under narrow public surface |
| `claude-code` | preview-guidance install/use path with managed settings preservation | managed closure materialization, settings preservation, host closure correctness, installed runtime smoke | `test_claude_preview_scaffold.py`, uninstall coverage | add task probes that execute routed governed tasks after install |
| `openclaw` | runtime-core preview lane | `vibe` visibility, runtime-core install/check, host-neutral specialist execution, uninstall | `test_openclaw_runtime_core.py`, `test_multi_host_specialist_execution.py` | add multi-task installed-runtime probes after internal-corpus cutover |
| `opencode` | preview-guidance install/use path with command/agent scaffolding | `vibe` skill visibility, agent visibility, config safety, check flow | `test_opencode_managed_preview.py`, `opencode_preview_smoke_support.py` | add routed installed-runtime task probes and post-install smoke under narrow public surface |

## Task Probe Matrix

Each mandatory host should run the following task classes during the rollout:

### Planning Task

Example shape:

- "Create a PRD and backlog for a small feature with quality gate requirements `$vibe`"

Expected proof:

- route decision is stable
- `confirm_required` or equivalent planning path behaves correctly
- requirement and plan artifacts are emitted
- runtime authority remains `vibe`

### Debug Task

Example shape:

- "I have a failing test and a stack trace. Debug systematically before proposing fixes `$vibe`"

Expected proof:

- router may select a specialist such as `systematic-debugging`
- runtime authority still remains `vibe`
- specialist dispatch is bounded and traceable
- delivery acceptance and cleanup artifacts exist

### Governed Execution Task

Example shape:

- "Implement a bounded runtime enhancement with verification and cleanup `$vibe`"

Expected proof:

- six governed stages execute
- execution manifest and cleanup receipt are emitted
- completion-claim policy remains enforced

### Memory Continuity Task

Example shape:

- first run: establish project decisions and graph-like relationships
- second run: request follow-up work that should recall prior decisions `$vibe`

Expected proof:

- stage-aware memory activation report exists
- requirement/plan include injected memory context when configured
- explicit-write semantics remain intact

## Layer Probe Matrix

### Routing Layer

Must validate:

- route mode selection
- primary skill choice
- explicit `$vibe` authority preservation when specialist help is selected
- behavior when official skills move under internal corpus only

Primary assets:

- `tests/runtime_neutral/test_router_bridge.py`
- `tests/integration/test_router_core_cutover.py`
- new internal-corpus routing probes

### Governance Layer

Must validate:

- six-stage governed lifecycle
- root/child hierarchy rules
- specialist approval boundaries
- delivery acceptance and cleanup truth

Primary assets:

- `tests/runtime_neutral/test_governed_runtime_bridge.py`
- `tests/runtime_neutral/test_root_child_hierarchy_bridge.py`
- `tests/runtime_neutral/test_runtime_delivery_acceptance.py`

### Memory Layer

Must validate:

- stage-aware activation
- cross-run read/write continuity
- context fold behavior
- explicit-write-only project decision semantics

Primary assets:

- `tests/runtime_neutral/test_memory_runtime_activation.py`
- future user-story probes for fold and handoff continuity

### Host Install/Runtime Layer

Must validate:

- install/check behavior
- host closure behavior
- settings/config preservation
- runtime smoke and uninstall cleanliness

Primary assets:

- `tests/runtime_neutral/test_installed_runtime_scripts.py`
- `tests/runtime_neutral/test_installed_runtime_uninstall.py`
- host-specific preview/runtime-core tests

## README Claim-To-Proof Standard

Before declaring the refactor complete, the project must maintain an explicit claim-to-proof mapping for these README promise groups:

1. intelligent routing
2. governed runtime workflow
3. root/child governance
4. memory system continuity
5. host install/use paths
6. owned-only uninstall and sidecar separation

For each claim group, the plan must state one of:

- covered by automated tests
- covered by runtime/task probes
- partially covered with an explicit gap and follow-up item

## Current Baseline Evidence

Representative baseline run completed during planning:

```bash
pytest -q tests/runtime_neutral/test_router_bridge.py \
  tests/runtime_neutral/test_governed_runtime_bridge.py \
  tests/runtime_neutral/test_memory_runtime_activation.py \
  tests/runtime_neutral/test_root_child_hierarchy_bridge.py \
  tests/runtime_neutral/test_openclaw_runtime_core.py \
  tests/runtime_neutral/test_opencode_managed_preview.py \
  tests/runtime_neutral/test_claude_preview_scaffold.py
```

Observed result:

- `24 passed, 15 subtests passed in 103.77s`

This baseline currently proves that routing, governed runtime staging, root/child governance, memory activation, and several supported host install/use paths are live and test-backed before the topology refactor begins.
- The acceptance plan must include deep validation on `codex`, `claude-code`, `openclaw`, and `opencode`.
- The acceptance plan must test real task classes across routing, governance, memory, and cleanup behavior.
- Final acceptance must include host coverage on `codex`, `claude-code`, `openclaw`, and `opencode`.
- Final acceptance must include separate evidence for routing, governance runtime, memory runtime, host install surfaces, and README-claim parity.

## Detailed Workstreams

### Workstream A: Contract and Packaging Semantics

Introduce new topology semantics without changing runtime behavior yet.

- Extend runtime packaging semantics with explicit groups:
  - `public_skill_surface`
  - `internal_skill_corpus`
  - `compatibility_skill_projections`
- Add an internal corpus descriptor contract consumed by runtime-core.
- Keep current `minimal` and `full` profile names, but redefine them around capability breadth rather than public top-level skill count.
- Preserve detached skill-catalog metadata ownership.
- Add a compatibility toggle such as `legacy_public_skill_projection_enabled` or equivalent host-scoped projections contract.

Deliverables:

- updated packaging contract in `config/runtime-core-packaging.json`
- generated compatibility projections in `.minimal.json` and `.full.json`
- contract updates in `packages/contracts`
- tests updated to validate the new semantic split

### Workstream B: Runtime Descriptor Source Refactor

Teach runtime-core to read specialist descriptors from a contract-driven internal source instead of depending on top-level installed official skill directories.

- Refactor `read_skill_descriptor()` and `resolve_skill_md_path()` into a descriptor-driven resolver.
- Keep candidate selection logic unchanged unless a separate issue is found.
- Resolve descriptors in this order:
  - internal corpus entry
  - explicit public compatibility projection
  - custom installed skill
- Keep a temporary fallback to legacy installed top-level official skill directories during migration.
- Add instrumentation or assertions that make continued legacy fallback usage visible in tests and smoke runs.

Deliverables:

- runtime-core resolver changes
- internal corpus descriptor loader
- regression tests proving routing descriptions still resolve under narrow public surface installs

### Workstream C: Installer Materialization and Ledger v2

Replace "track created path and guess later" with an ownership-class model.

- Introduce a ledger v2 schema that records:
  - `runtime_roots`
  - `compatibility_roots`
  - `sidecar_roots`
  - `config_rollbacks`
  - `legacy_cleanup_candidates`
- Keep install-time support for reading older ledger data.
- Make each materialization path explicitly declare ownership class.
- Materialize the full corpus under `skills/vibe/...` instead of exposing it as peer top-level skills by default.
- Keep explicit compatibility projections where required by host behavior.

Deliverables:

- contract/schema changes for install ledger
- installer-core changes in materialization and host closure
- updated payload summary logic

### Workstream D: Uninstall and Upgrade Migration

Move uninstall to authoritative deletion and deterministic rollback.

- Uninstall order becomes:
  - load authoritative ledger
  - delete owned runtime/compatibility/sidecar roots
  - apply config rollback records
  - use legacy inventory only as compatibility cleanup
- Make JSON parsing uniformly BOM-safe.
- Add upgrade/reinstall logic that prunes broad legacy public skill directories when moving to the new topology.
- Ensure generated nested compatibility never survives uninstall as managed residue.

Deliverables:

- uninstall-service changes
- upgrade/reinstall pruning logic
- uninstall preview that reflects owned topology truth

### Workstream E: Verification, Docs, and Rollout Safety

Update proof surfaces so product truth matches the new topology.

- Rewrite tests that currently assume full profile means a larger top-level `skills/` surface.
- Update install docs and governance docs to describe narrow public surface + internal corpus.
- Keep OpenCode and other host smoke checks centered on `vibe`, installed agents, config parsing, and uninstall cleanliness.
- Add staged rollout gates and explicit rollback criteria.

Deliverables:

- updated documentation
- rollout toggle behavior
- acceptance matrix and release gate checklist

## Execution Phases

### Phase A: Add New Contracts Without Changing Defaults

Goal:
Introduce the new semantic vocabulary while leaving the existing broad full-profile public projection in place.

Tasks:

- add `public_skill_surface`, `internal_skill_corpus`, and `compatibility_skill_projections` semantics
- add internal corpus descriptor contract
- add compatibility toggle contract
- add ledger v2 schema alongside v1-compatible reads
- keep full profile behavior functionally unchanged in this phase

Acceptance:

- contract tests pass
- generated packaging projections remain coherent
- no host behavior changes yet

### Phase B: Make Runtime Descriptor Resolution Descriptor-Driven

Goal:
Allow runtime-core to operate independently of legacy top-level official skill directories.

Tasks:

- refactor runtime descriptor loading
- load internal corpus from canonical Vibe-owned descriptor
- preserve temporary legacy fallback
- add tests that prove descriptor resolution succeeds when the full corpus is internalized under `skills/vibe/...`

Acceptance:

- routing/recommendation descriptions still resolve
- no host smoke regression
- legacy fallback usage is observable, not silent

### Phase C: Move Full Profile to Narrow Public Surface

Goal:
Change the full profile so it installs a full internal corpus but only a small public host-visible surface by default.

Tasks:

- stop using broad `bundled/skills -> skills` projection as the full-profile meaning
- materialize full corpus under `skills/vibe/...`
- keep explicit public companions only where the contract says so
- update payload summary and install differentiation tests

Acceptance:

- full profile still has broader capability coverage than minimal
- fresh installs no longer create hundreds of top-level official skill directories
- hosts still discover `vibe` and required agents/config surfaces

### Phase D: Switch Uninstall to Authoritative Ownership

Goal:
Delete only what Vibe owns, but do so deterministically and completely.

Tasks:

- uninstall consumes ledger v2 first
- delete runtime, compatibility, and sidecar roots by ownership class
- apply config rollback records
- use legacy inventory only as cleanup fallback
- normalize all JSON reads/writes to BOM-safe behavior

Acceptance:

- no residual managed nested/runtime-mirror files
- uninstall preview matches actual uninstall outcome
- legacy broad installs upgrade cleanly into narrow-surface installs

### Phase E: Cut Over Docs, Gates, and Rollout Policy

Goal:
Align product truth, verification truth, and release truth with the new topology.

Tasks:

- update install docs
- update governance docs
- update smoke notes and host-specific install expectations
- define release gates and rollback criteria
- keep compatibility toggle available until host matrix is stable

Acceptance:

- docs no longer imply that broad public top-level projection is the intended default
- release gates reflect new topology
- rollback is limited to legacy public projection re-enablement, not whole-architecture revert

## Ownership Boundaries

- `contracts`: topology, installed-runtime, and packaging contracts
- `skill-catalog`: official corpus and profile selection semantics
- `installer-core`: materialization, ledger, uninstall, host-closure application
- `runtime-core`: internal catalog/corpus consumption where needed
- `verification-core` and tests: proof that the new topology preserves behavior
- `vgo-cli`: thin orchestration only

## Module-Level Change Map

### `packages/contracts`

- extend installed-runtime and install-ledger contracts
- add internal corpus descriptor support
- keep mirror-topology and detached-catalog boundaries intact

### `packages/runtime-core`

- refactor descriptor resolution in `router_contract_support.py`
- avoid reworking candidate scoring unless needed
- add internal corpus loader utilities

### `packages/installer-core`

- update packaging resolution
- classify owned roots during install
- write ledger v2
- consume ledger v2 in uninstall
- keep v1 compatibility during migration

### `packages/verification-core`

- update freshness/coherence expectations where topology semantics change
- keep `skills/vibe` as the core host-visible proof point
- add residue and upgrade-cleanup assertions

### `docs/install` and architecture docs

- change default product explanation from "broad skill install" to "one governed runtime plus internal capability packs"
- document compatibility toggle and rollback policy

## Risk Register

1. Host tooling may implicitly scan peer top-level skills.
   Mitigation: preserve `vibe` as the public root; keep any additional host-required projections explicit and test-backed.
2. Internal corpus relocation may break runtime recommendation flows.
   Mitigation: switch catalog resolution to explicit descriptor paths before removing broad public projection.
3. Legacy installs may leave stranded public skills after upgrade.
   Mitigation: add migration pruning logic driven by authoritative prior-ledger ownership.
4. Uninstall may continue to misclassify generated files as foreign.
   Mitigation: move to owned-root deletion and BOM-safe JSON parsing before claiming simplification complete.
5. Contract/test drift may leave docs and code describing different products.
   Mitigation: require docs/truth gate before final cutover.
6. Legacy fallback may become permanent if not observed.
   Mitigation: instrument fallback usage and gate later removal on host-matrix proof.

## Verification Matrix

### Contract and Packaging Gates

- `tests/integration/test_runtime_core_packaging_roles.py`
- `tests/integration/test_catalog_contract_consumption.py`
- unit tests covering new contract readers and ledger v2 parsing

### Runtime and Topology Gates

- `tests/runtime_neutral/test_install_profile_differentiation.py`
- `tests/runtime_neutral/test_install_generated_nested_bundled.py`
- `tests/runtime_neutral/test_installed_runtime_scripts.py`
- host-specific probe suites for:
  - `codex`
  - `claude-code`
  - `openclaw`
  - `opencode`

### Uninstall and Upgrade Gates

- `tests/runtime_neutral/test_installed_runtime_uninstall.py`
- new coverage for:
  - BOM JSON uninstall
  - legacy broad-install prune on reinstall/upgrade
  - nested compatibility residue absence

### Docs and Truth Gates

- targeted checks for:
  - `docs/install/opencode-path.en.md`
  - `docs/install/custom-skill-governance-rules.en.md`
  - any default install path docs that still describe broad public skill projection
- README claim-to-proof review for routing, governance, memory, and host behavior promises

## Deep Validation Standard

The topology refactor is not considered trustworthy unless it survives practice-like probes that resemble real Vibe usage.
Static contract tests are necessary but not sufficient.

### Layer Coverage Required

- Router layer:
  canonical route selection, confirm-required behavior, explicit `/vibe` or `$vibe` authority preservation, graceful fallback
- Governed runtime layer:
  six-stage execution, requirement freeze, plan emission, root/child hierarchy integrity, specialist dispatch accounting
- Memory layer:
  stage-aware memory activation, backend read/write behavior, fold generation, requirement/plan memory context injection
- Host integration layer:
  install/check behavior, host closure sidecars, preview/runtime-core boundaries, wrapper readiness
- Uninstall layer:
  ledger-first cleanup, managed JSON/config rollback, sidecar cleanup, residue absence

### Host Matrix Required

The final acceptance run must explicitly cover these hosts:

- `codex`
- `claude-code`
- `openclaw`
- `opencode`

### Task Classes Required

Each acceptance cycle must include at least these task classes:

- `debug`:
  example shape: failing test plus stack trace
- `planning`:
  example shape: PRD, backlog, or execution-plan request
- `research` or `analysis`:
  example shape: multi-step investigation with evidence gathering
- `governed multi-step execution`:
  example shape: XL-style workflow requiring hierarchy or specialist dispatch

### Probe Types Required

- contract tests
- runtime-neutral router probes
- installed-runtime probes
- host preview/runtime-core smoke probes
- memory activation probes
- uninstall residue probes
- README claim alignment review

## Practice-Like Probe Matrix

### Codex

- Install/check/uninstall with real target roots
- Route a debug task through `/vibe` while preserving runtime authority
- Run governed runtime to verify stage receipts, requirement/plan outputs, and memory activation
- Run upgrade/profile-switch path to ensure legacy broad projections prune correctly

Representative assets:

- `tests/runtime_neutral/test_router_bridge.py`
- `tests/runtime_neutral/test_governed_runtime_bridge.py`
- `tests/runtime_neutral/test_memory_runtime_activation.py`
- `tests/runtime_neutral/test_installed_runtime_uninstall.py`

### Claude Code

- Verify managed `settings.json` mutation is bounded and preserves preexisting user settings
- Verify preview-guidance lane still exposes discoverable `vibe` and bounded host closure
- Run install/check/uninstall with preserved settings scenarios

Representative assets:

- `tests/runtime_neutral/test_claude_preview_scaffold.py`
- `tests/runtime_neutral/test_installed_runtime_uninstall.py`
- `tests/runtime_neutral/test_installed_runtime_scripts.py`

### OpenClaw

- Verify runtime-core preview lane boundaries
- Verify `skills/vibe` remains discoverable while host-local config is untouched
- Verify native specialist execution or honest degradation
- Verify uninstall removes only managed runtime-core payload

Representative assets:

- `tests/runtime_neutral/test_openclaw_runtime_core.py`
- `tests/runtime_neutral/test_multi_host_specialist_execution.py`
- `tests/runtime_neutral/test_installed_runtime_uninstall.py`

### OpenCode

- Verify preview-guidance wrappers and `vibe`/agent discovery
- Run preview smoke and parity checks
- Verify config example generation and no unintended mutation of real config
- Verify uninstall preserves user JSON while removing managed preview assets

Representative assets:

- `tests/runtime_neutral/test_opencode_managed_preview.py`
- `tests/runtime_neutral/test_opencode_preview_parity.py`
- `packages/verification-core/src/vgo_verify/opencode_preview_smoke_support.py`
- `tests/runtime_neutral/test_installed_runtime_uninstall.py`

## README Claim Alignment Standard

The release must prove alignment with README claims in four areas:

- intelligent routing:
  determinism, conflict handling, explicit `/vibe` authority, specialist composition
- governed workflow:
  clarify -> plan -> execute -> verify outputs and receipts
- memory system:
  stage-aware activation and explicit governance rules
- install/uninstall management:
  host-specific bounded state handling and owned-only cleanup

If any README-level claim is no longer supportable by tests or probes, either:

- add the missing test/probe, or
- narrow the README claim before release

### Host and Runtime Probe Gates

- `tests/runtime_neutral/test_openclaw_runtime_core.py`
- `tests/runtime_neutral/test_claude_preview_scaffold.py`
- `tests/runtime_neutral/test_opencode_managed_preview.py`
- targeted Codex coverage from `tests/runtime_neutral/test_installed_runtime_scripts.py`

### Governance and Memory Gates

- `tests/runtime_neutral/test_governed_runtime_bridge.py`
- `tests/runtime_neutral/test_root_child_hierarchy_bridge.py`
- `tests/runtime_neutral/test_phase_cleanup_policy_contract.py`
- `tests/runtime_neutral/test_memory_runtime_activation.py`
- `tests/runtime_neutral/test_runtime_delivery_acceptance.py`

### README Truth Gates

- routing claims vs:
  - `tests/runtime_neutral/test_router_bridge.py`
  - `tests/integration/test_router_core_cutover.py`
- governance/runtime claims vs:
  - `tests/runtime_neutral/test_governed_runtime_bridge.py`
  - `tests/runtime_neutral/test_root_child_hierarchy_bridge.py`
- memory claims vs:
  - `tests/runtime_neutral/test_memory_runtime_activation.py`
- install/uninstall claims vs:
  - `tests/runtime_neutral/test_installed_runtime_uninstall.py`
  - host-specific preview/runtime-core tests

## Phase Exit Standards

### Phase A Exit

- New contract fields exist and are normalized by code.
- Existing install behavior remains unchanged.
- Packaging and catalog contract tests pass.
- A future host/test matrix is already encoded in the plan so later phases do not silently narrow validation scope.

### Phase B Exit

- Runtime descriptor resolution works through the new descriptor-driven path.
- Legacy fallback is still available but observable.
- No host smoke regression is introduced.
- At least one routed task probe still passes on each mandatory host using the pre-cutover topology.
- At least one governed runtime probe and one router probe still pass after the descriptor source change.
- At least one routing probe and one governed-runtime probe still pass after the resolver change.

### Phase C Exit

- Fresh full installs present a narrow public surface.
- Full remains broader than minimal in internal capability coverage.
- Host-visible `vibe` and required agents/config surfaces still work.
- Host task probes show that `$vibe` still routes and governs correctly after the internal-corpus move.
- Codex, Claude Code, OpenClaw, and OpenCode each have at least one passing install/check/runtime probe after the topology shift.
- `codex`, `claude-code`, `openclaw`, and `opencode` each retain at least one passing install/check/runtime probe path.

### Phase D Exit

- Uninstall consumes authoritative ownership records first.
- No managed nested/runtime-mirror residue remains after uninstall.
- BOM-encoded managed JSON/config files uninstall cleanly.
- Multi-host uninstall probes confirm that managed closure/config cleanup still matches README-described behavior.
- Multi-host uninstall probes confirm no regression in bounded cleanup behavior.
- Host uninstall proof exists for all targeted public hosts in scope of this change.

### Phase E Exit

- Docs, tests, and contracts all describe the same steady-state topology.
- Rollback and compatibility-toggle rules are documented and test-backed.
- Release gate checklist matches the new architecture.
- README claim-to-proof mapping is current and identifies no untracked critical promise gaps.
- README-level claims used in installation, routing, governance, and memory messaging are still demonstrably true.
- README-level routing, governance, memory, and host-install claims have an explicit proof mapping.

## Verification Commands

Run at minimum:

```bash
pytest -q tests/unit/test_runtime_packaging_resolver.py tests/unit/test_installer_profile_inventory.py tests/unit/test_installer_ledger_service.py
pytest -q tests/integration/test_runtime_core_packaging_roles.py tests/integration/test_catalog_contract_consumption.py tests/integration/test_cli_installer_core_cutover.py
pytest -q tests/runtime_neutral/test_install_profile_differentiation.py tests/runtime_neutral/test_install_generated_nested_bundled.py tests/runtime_neutral/test_installed_runtime_scripts.py tests/runtime_neutral/test_installed_runtime_uninstall.py
pytest -q tests/runtime_neutral/test_router_bridge.py tests/runtime_neutral/test_governed_runtime_bridge.py tests/runtime_neutral/test_root_child_hierarchy_bridge.py tests/runtime_neutral/test_memory_runtime_activation.py tests/runtime_neutral/test_runtime_delivery_acceptance.py
pytest -q tests/runtime_neutral/test_openclaw_runtime_core.py tests/runtime_neutral/test_claude_preview_scaffold.py tests/runtime_neutral/test_opencode_managed_preview.py
```

Run targeted manual checks with fresh temp roots for:

```bash
bash ./install.sh --host codex --profile full --target-root /tmp/vgo-full
bash ./check.sh --host codex --profile full --target-root /tmp/vgo-full
bash ./uninstall.sh --host codex --profile full --target-root /tmp/vgo-full --preview
bash ./uninstall.sh --host codex --profile full --target-root /tmp/vgo-full
```

Run host-focused probe checks for:

```bash
bash ./install.sh --host claude-code --profile full --target-root /tmp/vgo-claude
bash ./check.sh --host claude-code --profile full --target-root /tmp/vgo-claude
bash ./install.sh --host openclaw --profile full --target-root /tmp/vgo-openclaw
bash ./check.sh --host openclaw --profile full --target-root /tmp/vgo-openclaw
bash ./install.sh --host opencode --profile full --target-root /tmp/vgo-opencode
bash ./check.sh --host opencode --profile full --target-root /tmp/vgo-opencode
```

Run governed-runtime and memory probes for representative tasks:

```bash
pwsh -NoLogo -NoProfile -Command "& { & './scripts/runtime/invoke-vibe-runtime.ps1' -Task 'Plan a governed architecture refactor with acceptance criteria.' -Mode interactive_governed -ArtifactRoot '/tmp/vgo-probes/planning' }"
pwsh -NoLogo -NoProfile -Command "& { & './scripts/runtime/invoke-vibe-runtime.ps1' -Task 'I have a failing test and a stack trace. Help me debug systematically before proposing fixes.' -Mode interactive_governed -ArtifactRoot '/tmp/vgo-probes/debug' }"
pwsh -NoLogo -NoProfile -Command "& { & './scripts/runtime/invoke-vibe-runtime.ps1' -Task 'XL approved decision: keep api worker runtime continuity and graph relationship between api worker and planner.' -Mode interactive_governed -ArtifactRoot '/tmp/vgo-probes/memory' }"
```

## Deep Validation Matrix

### Host Matrix

- `codex`
  - install/check/uninstall
  - duplicate-surface hygiene
  - `vibe` discovery
  - routed debug/planning task
- `claude-code`
  - bounded managed settings closure
  - preview/install check
  - `vibe` discoverability and managed JSON preservation
- `openclaw`
  - runtime-core preview lane
  - no unwanted host-local config mutation
  - routed/specialist runtime probe
- `opencode`
  - preview-guidance install/check
  - installed agent/config example surfaces
  - preview smoke and `vibe` detection

### Task Matrix

- planning task: requirement and execution-plan generation through governed runtime
- debug task: router selects or recommends debugging specialist support while `vibe` retains runtime authority
- runtime continuity task: memory activation and context fold behavior
- host-specialist task: live wrapper execution or honest degradation on non-Codex hosts

### Layer Matrix

- routing layer
  - primary skill selection
  - `vibe` explicit invocation
  - specialist recommendation/dispatch boundaries
- governance layer
  - six stages
  - root/child lane authority
  - phase cleanup and delivery acceptance
- memory layer
  - L1/L2/L3/L4 activation behavior
  - explicit write policy
  - fold artifact emission
- install/runtime layer
  - host closures
  - installed runtime freshness/coherence
  - uninstall owned-only cleanup

## Rollback Rule

If any supported host still requires broad peer top-level skill visibility, keep that host on an explicit compatibility projection path rather than reverting the global topology.

Operational rollback criteria:

- `vibe` is not discoverable on a supported host
- OpenCode or equivalent host smoke fails
- upgrade leaves stranded legacy public skill directories
- uninstall leaves managed residue or mis-rolls JSON/config mutations

Operational rollback action:

- re-enable legacy compatibility projection via contract-level toggle
- keep internal corpus and descriptor-driven runtime support in place
- do not revert the entire architecture unless the descriptor-driven runtime itself proves invalid

## Task Breakdown

### Step 1: Freeze Contracts

- define new packaging fields
- define internal corpus descriptor
- define ledger v2 schema
- add compatibility toggle

### Step 2: Implement Runtime Reader

- refactor descriptor resolution
- add internal corpus loader
- keep legacy fallback
- add fallback-observation tests

### Step 3: Implement Installer Writer

- write full corpus into `skills/vibe/...`
- classify owned roots and sidecars
- record legacy cleanup candidates
- refresh payload summary semantics

### Step 4: Implement Uninstall Reader

- prefer ledger v2
- delete owned roots by class
- replay config rollbacks
- make JSON handling BOM-safe

### Step 5: Migrate Tests and Docs

- rewrite profile differentiation expectations
- update smoke/support docs
- add upgrade/uninstall residue coverage
- document rollback/toggle behavior

## Completion Rule

This plan is complete only when:

- the default broad profile installs a narrow public surface
- the full specialist corpus remains available internally
- uninstall removes the new topology cleanly
- docs and tests describe the new truth rather than the legacy broad projection model

## Related Detailed Task Breakdown

Execution should follow the companion task document:

- `docs/plans/2026-04-06-public-skill-surface-decoupling-task-breakdown.md`
