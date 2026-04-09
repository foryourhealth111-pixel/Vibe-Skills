# Vibe Multi-Host Wrapper Skill Projection Design

## Summary
Define a multi-host discoverable entry architecture that exposes `vibe`, `vibe-want`, `vibe-how`, and `vibe-do` as host-visible wrapper skills while preserving one canonical governed runtime authority: `vibe`.

The core runtime, routing, stage machine, requirement freeze, plan freeze, execution, and cleanup contracts remain singular and canonical. The new work is the projection layer: shared entry metadata must drive packaging, installer materialization, host adapter projection, install/check reporting, and regression tests so that discoverable menu entries are actually materialized on supported hosts instead of existing only in docs and contract files.

This design assumes the target hosts support skill-menu or command-menu discoverability. The problem being solved is not whether hosts can render menus. The problem is making the repo ship those discoverable entries consistently across hosts without forking runtime truth.

## Problem
The repository already has a shared discoverable-entry contract in `config/vibe-entry-surfaces.json`, and runtime packet handling already understands `entry_intent_id`, `requested_stage_stop`, and grade-floor metadata. But the install surface still exposes only canonical `vibe` because the packaging layer remains locked to `canonical_vibe_only`.

That creates four concrete failures:

1. docs claim that users may see `Vibe`, `Vibe: What Do I Want?`, `Vibe: How Do We Do It?`, and `Vibe: Do It`
2. host adapters declare discoverable entries as a presentational concept
3. runtime tests validate the shortcut contract
4. installed hosts still materialize only the canonical `vibe` launch surface

The result is a cross-layer contract drift: runtime truth exists, docs promise it, but packaging and installation do not project it into host-visible menu entries.

## Goals
- Materialize four host-visible wrapper entries from one shared contract.
- Preserve one runtime authority, one stage machine, and one requirement/plan/cleanup truth surface.
- Keep grade-floor flags orthogonal to stage intent and prohibit stage-grade alias explosion.
- Make the solution host-generic so `codex`, `claude-code`, `cursor`, `windsurf`, `openclaw`, and `opencode` consume the same discoverable-entry truth.
- Keep packaging, installer behavior, install reports, and docs aligned with what hosts actually receive.
- Add explicit verification for Linux and Windows materialization paths.

## Non-Goals
- No new runtime authority besides `vibe`.
- No `vibe-want-xl`, `vibe-how-l`, `vibe-do-xl`, or other matrix aliases.
- No host-specific semantic forks where an adapter decides what a wrapper means.
- No duplication of requirement generation, planning, execution, or cleanup logic.
- No assumption that `$vibe xxx` textual subcommands are the primary UX.
- No attempt to solve host plugin provisioning, provider credentials, or MCP readiness inside this design.

## Existing Constraints

### Canonical Discoverable Contract
`config/vibe-entry-surfaces.json` is already the correct shared truth for:

- `id`
- `display_name`
- `requested_stage_stop`
- `allow_grade_flags`
- public grade flags `--l` and `--xl`

The approved ids are fixed:

- `vibe`
- `vibe-want`
- `vibe-how`
- `vibe-do`

### Current Root Cause
`config/runtime-core-packaging.full.json` and `config/runtime-core-packaging.minimal.json` still define:

- `public_skill_surface.mode = canonical_vibe_only`
- `public_skill_surface.projected_skill_names = ["vibe"]`

That keeps the public install surface narrower than the discoverable-entry contract.

### Runtime Boundary That Must Not Change
The canonical runtime remains:

- runtime skill id: `vibe`
- requirement authority: single governed requirement doc
- planning authority: single governed plan doc
- execution authority: canonical plan execution
- cleanup authority: canonical phase cleanup

Wrappers may only influence entry metadata:

- `entry_intent_id`
- `requested_stage_stop`
- `requested_grade_floor`

## Architecture Decision
Choose a **multiple thin wrapper skills, single canonical runtime** architecture.

Each discoverable entry is a host-visible wrapper surface generated from shared metadata. Each wrapper points back to canonical `vibe` and contributes only bounded launch metadata. Runtime semantics remain centralized in the existing governed runtime.

This gives the user the multi-entry discoverability they want, but keeps architecture quality defensible:

- high cohesion: runtime behavior lives in runtime-core, not in adapters
- low coupling: hosts project the same contract without owning semantics
- low regression risk: wrappers do not fork execution logic

## Design Units

### 1. Shared Entry Contract Unit
**Responsibility:** define the only approved public discoverable entries and their launch semantics.

**Primary file:** `config/vibe-entry-surfaces.json`

**Interface:**
- input to packaging projection
- input to host adapter projection
- input to runtime validation
- input to install/check reporting

**Rules:**
- only one canonical runtime skill id: `vibe`
- only four public entry ids
- only `--l` and `--xl` as public grade-floor flags
- `vibe-want` rejects public grade flags

### 2. Public Surface Packaging Unit
**Responsibility:** describe which discoverable wrappers must be materialized as host-visible public surfaces.

**Primary files:**
- `config/runtime-core-packaging.json`
- `config/runtime-core-packaging.full.json`
- `config/runtime-core-packaging.minimal.json`

**Interface:**
- consumed by packaging resolvers in installer-core and runtime-core
- exported into install plan and manifest descriptors

**Required change:**
- replace `canonical_vibe_only` with a wrapper-aware public surface mode
- declare wrapper projections from shared contract rather than hardcoded per profile

**Boundary rule:**
- public surface describes host-visible entry surfaces
- compatibility projections remain for legacy or host-specific path preservation only
- internal skill corpus remains private under canonical `vibe`

### 3. Wrapper Projection Resolver Unit
**Responsibility:** resolve which wrapper skills/commands should exist in a target installation for a given profile and host.

**Primary files:**
- `packages/installer-core/src/vgo_installer/runtime_packaging.py`
- `packages/runtime-core/src/vgo_runtime/router_contract_support.py`
- `packages/installer-core/src/vgo_installer/install_plan.py`

**Interface:**
- takes packaging config plus discoverable-entry contract
- returns canonical root, public wrapper names, resolver roots, and projection metadata

**Rules:**
- wrapper names are derived from shared entry ids, not duplicated in code and config separately
- canonical `vibe` stays the runtime-selected skill even when wrapper entry is used
- resolver output must be stable across repo mode and installed-host mode

### 4. Host Materialization Unit
**Responsibility:** physically materialize host-visible wrapper skill or command descriptors in the installed target root.

**Primary files:**
- `packages/installer-core/src/vgo_installer/materializer.py`
- `packages/installer-core/src/vgo_installer/install_runtime.py`

**Interface:**
- receives resolved public wrapper projection data
- writes host-visible wrapper files into the host’s command or skill discovery surface

**Rules:**
- wrappers are generated artifacts, not hand-maintained semantic copies
- wrappers may vary in shell syntax or frontmatter shape per host, but not in entry semantics
- generated wrappers must be recorded in the install ledger as host-visible surfaces

### 5. Host Adapter Projection Unit
**Responsibility:** define how each host renders the same discoverable wrappers into its native menu/discovery surface.

**Primary files:**
- `config/adapter-registry.json`
- `adapters/*/host-profile.json`
- host-specific templates or command descriptors under adapter/config trees

**Host-specific behavior allowed:**
- path conventions
- frontmatter/schema differences
- display formatting differences required by host limitations

**Host-specific behavior forbidden:**
- inventing extra public entry ids
- changing stop targets
- changing grade-flag policy
- creating separate runtime authorities

### 5A. Per-Host Projection Contract
The projection mechanism is shared, but the host-visible target differs by adapter.

**Codex**
- target shape: command-style discoverable entries in the host command surface
- installed expectation: canonical `vibe` plus wrapper command files for `vibe-want`, `vibe-how`, and `vibe-do`
- verification focus: files are present in the real Codex host root and visible to the command menu, not only present in repo `commands/`

**Claude Code**
- target shape: host-visible commands or skill launchers within the managed Claude settings surface
- installed expectation: wrapper entries are added without replacing the broader host-managed settings space
- verification focus: wrapper entries are merged into the real Claude host surface and survive bounded settings merging

**Cursor**
- target shape: preview-guidance discoverable command or skill entries
- installed expectation: wrappers are exposed as menu-visible launch surfaces without claiming full takeover of Cursor settings
- verification focus: wrapper projection exists in the real Cursor host root and is reported separately from generic runtime payload

**Windsurf**
- target shape: runtime-core wrapper descriptors in the Windsurf host-visible launch surface
- installed expectation: runtime payload and `.vibeskills/*` sidecar remain separate from wrapper discoverability
- verification focus: wrapper readiness is reported independently from runtime-core sidecar installation

**OpenClaw**
- target shape: preview runtime-core wrapper descriptors compatible with attach, copy, or bundle style installation
- installed expectation: wrapper discoverability is visible in the chosen OpenClaw host path, not just in sidecar artifacts
- verification focus: install/check distinguishes runtime payload presence from wrapper menu visibility

**OpenCode**
- target shape: command or agent discoverable entries alongside the existing preview-guidance payload
- installed expectation: wrapper entries live in the host-visible OpenCode discovery surface while real `opencode.json` remains host-managed
- verification focus: wrapper entries are visible independently of `opencode.json.example`, provider credentials, or plugin state

**Generic adapter**
- out of scope for discoverable-wrapper completeness
- rule: generic may remain canonical-`vibe` only unless it grows a stable host-visible menu contract

### 6. Install And Check Reporting Unit
**Responsibility:** report truthfully whether wrapper entries are installed locally and host-visible.

**Primary files:**
- `install.sh`
- `install.ps1`
- `check.sh`
- `check.ps1`
- installer-core reporting paths

**Required reporting split:**
- `installed locally`
- `vibe host-ready`
- `host-visible discoverable entries`
- `mcp native auto-provision attempted`
- per-MCP `host-visible readiness`
- `online-ready`

**Truth rule:**
- runtime payload existing is not enough
- wrapper metadata in config is not enough
- docs mentioning wrappers is not enough
- host-visible installed wrapper files must exist before the install/check path reports discoverable entries ready

## Wrapper Semantics

### Canonical `vibe`
- entry id: `vibe`
- stop target: `phase_cleanup`
- grade flags allowed: yes
- semantic meaning: full governed flow

### `vibe-want`
- entry id: `vibe-want`
- stop target: `deep_interview`
- grade flags allowed: no
- semantic meaning: clarify goal, boundaries, and acceptance criteria

### `vibe-how`
- entry id: `vibe-how`
- stop target: `xl_plan`
- grade flags allowed: yes
- semantic meaning: freeze requirement and plan without executing later stages

### `vibe-do`
- entry id: `vibe-do`
- stop target: `phase_cleanup`
- grade flags allowed: yes
- semantic meaning: execute the governed flow, while still preserving requirement and plan stages

## Data Flow

### Launch Flow
1. User selects a host-visible wrapper entry from a skill or command menu.
2. The wrapper injects `entry_intent_id`.
3. The wrapper injects the approved `requested_stage_stop`.
4. If allowed, the wrapper forwards `--l` or `--xl` as `requested_grade_floor`.
5. Canonical router/runtime authority still resolves to `vibe`.
6. Governed runtime executes the same six-stage state machine and stops at the requested stop target.

### Packaging And Installation Flow
1. Packaging loads shared entry contract.
2. Packaging resolves public wrapper projection names.
3. Installer materializes canonical `vibe` plus wrapper descriptors into host-visible surfaces.
4. Install ledger records wrapper surfaces as generated managed artifacts.
5. Check flow validates both runtime payload and host-visible wrapper presence.

### Validation Flow
1. Contract tests validate shared entry truth.
2. Packaging tests validate wrapper projection resolution.
3. Installer tests validate wrapper materialization.
4. Runtime tests validate packet metadata and stop behavior.
5. Cross-platform tests validate Linux and Windows install/check parity.

## Practical Implementation Strategy

### Phase 1: Contract And Packaging Alignment
Update packaging manifests so public surfaces are derived from discoverable-entry truth rather than fixed to `["vibe"]`.

Implementation targets:
- `config/runtime-core-packaging.json`
- `config/runtime-core-packaging.full.json`
- `config/runtime-core-packaging.minimal.json`
- `packages/installer-core/src/vgo_installer/runtime_packaging.py`
- `packages/runtime-core/src/vgo_runtime/router_contract_support.py`

Deliverable:
- packaging resolver can enumerate all four approved wrappers from shared contract

### Phase 2: Generated Wrapper Projection
Introduce a generated-wrapper projection path so each host receives discoverable wrapper descriptors without semantic duplication.

Implementation targets:
- `packages/installer-core/src/vgo_installer/materializer.py`
- `packages/installer-core/src/vgo_installer/install_runtime.py`
- host template locations referenced by adapters

Deliverable:
- installer writes host-visible wrapper files for `vibe-want`, `vibe-how`, and `vibe-do` in addition to canonical `vibe`

### Phase 3: Adapter-Specific Projection Rules
Make each supported adapter consume the same discoverable-entry truth and project wrapper files into the host-native discovery surface.

Implementation targets:
- `config/adapter-registry.json`
- `adapters/codex/host-profile.json`
- `adapters/claude-code/host-profile.json`
- `adapters/cursor/host-profile.json`
- `adapters/windsurf/host-profile.json`
- `adapters/openclaw/host-profile.json`
- `adapters/opencode/host-profile.json`

Deliverable:
- every adapter reports that discoverable entries are projected from shared wrapper truth, not presentational-only placeholders with no materialization path

### Phase 4: Install, Check, And Report Truthfulness
Make install/check output explicitly report host-visible discoverable entry readiness and fail or degrade honestly when wrapper materialization is absent.

Implementation targets:
- `install.sh`
- `install.ps1`
- `check.sh`
- `check.ps1`
- installer-core reporting functions

Deliverable:
- install/check can tell the operator whether discoverable wrapper entries are merely configured or actually visible in the host

### Phase 5: Docs And Regression Closure
Update docs to describe discoverable wrappers as actual shipped surfaces and lock behavior with cross-layer tests.

Implementation targets:
- `docs/quick-start.md`
- `docs/quick-start.en.md`
- install-path docs for affected hosts
- release notes / PR description

Deliverable:
- docs, install behavior, and test evidence tell the same story

## Error Handling And Edge Cases
- If a host adapter cannot materialize a stable host-visible wrapper surface, install/check must report `not host-visible` rather than silently succeeding.
- If a host has formatting constraints on entry labels, cosmetic display changes are allowed, but ids must remain stable.
- If a wrapper file is missing after installation, check must mark discoverable-entry readiness as incomplete even if canonical `vibe` exists.
- If more than one public grade flag is requested, runtime input validation must continue rejecting the invocation.
- If a wrapper that forbids grade flags receives one, the runtime or launcher must reject it explicitly rather than silently ignoring it.
- If the canonical `vibe` root exists but wrapper descriptors are stale, installer refresh must replace them atomically enough to avoid partial host-visible drift.

## Testing Strategy

### Contract Tests
- extend `tests/contract/test_vibe_discoverable_entry_contract.py`
- extend `tests/contract/test_adapter_descriptor_contract.py`

Assertions:
- four fixed ids only
- fixed display names only
- correct stop targets
- grade-flag allowance policy
- adapters consume shared wrapper truth

### Packaging Resolver Tests
- extend `tests/unit/test_runtime_packaging_resolver.py`
- extend `tests/integration/test_runtime_core_packaging_roles.py`
- extend `tests/unit/test_router_contract_support_descriptor_sources.py`

Assertions:
- public surface projection resolves all four wrapper ids
- canonical runtime relpath stays `skills/vibe`
- compatibility projections stay narrow and do not become semantic truth

### Installer Materialization Tests
- add or extend installer-core tests around generated wrapper files
- extend `tests/runtime_neutral/test_install_profile_differentiation.py`

Assertions:
- target root contains host-visible wrapper descriptors
- wrappers are recorded in ledger state
- full and minimal profiles behave according to policy

### Runtime Integration Tests
- preserve and extend:
  - `tests/integration/test_runtime_packet_execution.py`
  - `tests/unit/test_vgo_cli_commands.py`
  - `tests/runtime_neutral/test_l_xl_native_execution_topology.py`

Assertions:
- wrapper entries still resolve runtime-selected skill to `vibe`
- stop-stage behavior is truthful
- `vibe-want` rejects grade flags
- `vibe-how` and `vibe-do` preserve grade-floor behavior

### Cross-Platform Verification
Required verification lanes:
- Linux install/check path
- Windows install/check path

Evidence target:
- wrapper entries are not only contract-valid but physically materialized in host-visible surfaces on both platforms

## Cohesion And Coupling Standard
This design must be implemented so that:

- runtime-core owns runtime behavior
- installer-core owns materialization
- adapter metadata owns host-specific projection format
- docs describe public behavior but never define semantics

Bad implementation patterns to reject:

- host adapters hardcoding stop targets independently
- duplicated wrapper semantics in multiple command files with no generator or shared source
- install scripts directly inventing wrapper names not present in shared contract
- runtime behavior branching by host when the entry semantics are host-neutral

## Rollout Strategy
Use a staged rollout:

1. land contract and packaging alignment first
2. land generated wrapper materialization second
3. land install/check truthfulness third
4. land docs and release evidence last

This sequencing keeps regression diagnosis easier because each phase narrows the fault domain.

## Acceptance Criteria
- A fresh install on a supported host materializes host-visible entries for `vibe`, `vibe-want`, `vibe-how`, and `vibe-do`.
- Selecting any wrapper still routes into canonical `vibe` governed runtime.
- `vibe-want` stops at `deep_interview` and cannot take `--l` or `--xl`.
- `vibe-how` stops at `xl_plan` and can carry a grade floor into planning.
- `vibe-do` executes the full governed path without skipping requirement or plan.
- Packaging, installer, adapter metadata, docs, and tests all derive from the same shared discoverable-entry contract.
- Linux and Windows verification prove host-visible wrapper materialization, not just runtime payload presence.

## Open Questions Resolved By This Design
- Multiple wrapper skills are the correct compatibility shape because they map cleanly into host skill menus.
- They are still wrappers, not new runtimes.
- Cross-host support should be implemented once in shared projection logic, not re-invented host by host.
- `$vibe xxx` textual composition is not the primary public UX and does not need to be the center of this design.
