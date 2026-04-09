# Codex Vibe Wrapper Skills Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Codex full-profile installs expose `vibe`, `vibe-what-do-i-want`, `vibe-how-do-we-do`, and `vibe-do-it` as host-visible skills while preserving `vibe` as the only canonical governed runtime.

**Architecture:** Add three thin wrapper skill sources to the bundled skill corpus, project them onto Codex's public skill surface through the existing compatibility projection mechanism, and update installer/check/uninstall tests so skill visibility becomes the primary Codex truth. Keep `commands` only as a temporary compatibility layer during migration.

**Tech Stack:** Python installer core, runtime packaging manifests, shell/PowerShell check scripts, Markdown skill descriptors, pytest/unittest-based repository tests.

---

## Chunk 1: Lock Skill-First Packaging Contract

### Task 1: Convert Codex full-profile packaging truth from canonical-only to wrapper-skill projection

**Files:**
- Modify: `config/runtime-core-packaging.full.json`
- Modify: `tests/integration/test_runtime_core_packaging_roles.py`
- Modify: `tests/unit/test_runtime_packaging_resolver.py`
- Modify: `tests/runtime_neutral/test_install_profile_differentiation.py`

- [ ] **Step 1: Write the failing packaging assertions**

Add assertions that Codex full-profile packaging now declares:

- public canonical root still points at `skills/vibe`
- compatibility projections include:
  - `vibe-what-do-i-want`
  - `vibe-how-do-we-do`
  - `vibe-do-it`
- full-profile public skill story remains `vibe`-canonical rather than peer-runtime

- [ ] **Step 2: Run the targeted packaging tests and confirm they fail**

Run:

```bash
python3 -m pytest \
  tests/integration/test_runtime_core_packaging_roles.py \
  tests/unit/test_runtime_packaging_resolver.py \
  tests/runtime_neutral/test_install_profile_differentiation.py -q
```

Expected: FAIL because full packaging still projects only canonical `vibe`.

- [ ] **Step 3: Update the full-profile packaging manifest**

Edit `config/runtime-core-packaging.full.json` so that:

- `public_skill_surface.projected_skill_names` stays truthful about the canonical story
- `compatibility_skill_projections.projected_skill_names` becomes:

```json
[
  "vibe-what-do-i-want",
  "vibe-how-do-we-do",
  "vibe-do-it"
]
```

- `resolver_roots` remain `skills`
- `minimal` packaging remains unchanged in this implementation

- [ ] **Step 4: Re-run the packaging tests**

Run:

```bash
python3 -m pytest \
  tests/integration/test_runtime_core_packaging_roles.py \
  tests/unit/test_runtime_packaging_resolver.py \
  tests/runtime_neutral/test_install_profile_differentiation.py -q
```

Expected: PASS.

## Chunk 2: Add Wrapper Skill Sources

### Task 2: Create the three thin wrapper skills inside the bundled skill corpus

**Files:**
- Create: `bundled/skills/vibe-what-do-i-want/SKILL.md`
- Create: `bundled/skills/vibe-how-do-we-do/SKILL.md`
- Create: `bundled/skills/vibe-do-it/SKILL.md`
- Modify: `tests/contract/test_repo_layout_contract.py`
- Modify: `tests/runtime_neutral/test_offline_skills_gate.py`

- [ ] **Step 1: Write the failing source-surface assertions**

Add assertions that the repo now contains three bundled wrapper skill directories, each with a readable `SKILL.md`.

- [ ] **Step 2: Run the targeted source-layout tests and confirm they fail**

Run:

```bash
python3 -m pytest \
  tests/contract/test_repo_layout_contract.py \
  tests/runtime_neutral/test_offline_skills_gate.py -q
```

Expected: FAIL because the wrapper skill directories do not exist yet.

- [ ] **Step 3: Author thin wrapper skill descriptors**

Create the three `SKILL.md` files with these constraints:

- frontmatter `name` matches the portable physical skill name
- description explains the entry bias
- body explicitly delegates to canonical `vibe`
- body states that no second requirement, plan, or runtime authority may be created

Use wording shaped like:

```md
Use canonical `vibe` as the runtime authority.
Bias entry toward <intent>.
Do not create a second requirement surface, second plan surface, or parallel runtime.
```

- [ ] **Step 4: Keep wrappers short and non-canonical**

Do not copy the full canonical `vibe` contract into wrapper files.
Limit each wrapper to entry guidance and guardrails only.

- [ ] **Step 5: Re-run the source-layout tests**

Run:

```bash
python3 -m pytest \
  tests/contract/test_repo_layout_contract.py \
  tests/runtime_neutral/test_offline_skills_gate.py -q
```

Expected: PASS.

## Chunk 3: Materialize Wrapper Skills Into Codex Host Surface

### Task 3: Make Codex installs project wrapper skills into `~/.codex/skills`

**Files:**
- Modify: `packages/installer-core/src/vgo_installer/install_runtime.py`
- Modify: `packages/installer-core/src/vgo_installer/materializer.py`
- Modify: `packages/installer-core/src/vgo_installer/uninstall_service.py`
- Modify: `tests/runtime_neutral/test_installed_runtime_scripts.py`
- Modify: `tests/runtime_neutral/test_uninstall_vgo_adapter.py`

- [ ] **Step 1: Write the failing install/uninstall tests**

Add Codex full-profile assertions that a fresh install materializes:

- `skills/vibe/SKILL.md`
- `skills/vibe-what-do-i-want/SKILL.md`
- `skills/vibe-how-do-we-do/SKILL.md`
- `skills/vibe-do-it/SKILL.md`

and that uninstall inventory owns the three wrapper directories.

- [ ] **Step 2: Run the targeted install/uninstall tests and confirm they fail**

Run:

```bash
python3 -m pytest \
  tests/runtime_neutral/test_installed_runtime_scripts.py \
  tests/runtime_neutral/test_uninstall_vgo_adapter.py -q -k 'vibe_wrapper or codex'
```

Expected: FAIL because Codex currently installs only canonical `vibe` as a visible skill.

- [ ] **Step 3: Wire projections through existing allowlisted-skill materialization**

Use the existing projection path rather than inventing a new installer branch:

- keep `materialize_allowlisted_skills()` as the public skill projector
- let full-profile manifest data drive which wrappers are copied into `target_root/skills`
- ensure canonical `vibe` remains excluded from wrapper projection logic

- [ ] **Step 4: Extend uninstall ownership**

Teach uninstall inventory to remove wrapper skill directories cleanly when they were materialized into the public skill surface.

- [ ] **Step 5: Re-run the targeted install/uninstall tests**

Run:

```bash
python3 -m pytest \
  tests/runtime_neutral/test_installed_runtime_scripts.py \
  tests/runtime_neutral/test_uninstall_vgo_adapter.py -q -k 'vibe_wrapper or codex'
```

Expected: PASS.

## Chunk 4: Switch Codex Check Truth To Skill-First

### Task 4: Make governed Codex checks validate wrapper skills before command compatibility

**Files:**
- Modify: `check.sh`
- Modify: `check.ps1`
- Modify: `tests/runtime_neutral/test_runtime_contract_schema.py`
- Modify: `tests/runtime_neutral/test_installed_runtime_scripts.py`

- [ ] **Step 1: Write the failing Codex health-check assertions**

Add assertions that governed Codex checks require:

- `skill/vibe`
- `skill/vibe-what-do-i-want`
- `skill/vibe-how-do-we-do`
- `skill/vibe-do-it`

and treat any retained command files as optional compatibility evidence rather than primary health proof.

- [ ] **Step 2: Run the targeted check-related tests and confirm they fail**

Run:

```bash
python3 -m pytest \
  tests/runtime_neutral/test_runtime_contract_schema.py \
  tests/runtime_neutral/test_installed_runtime_scripts.py -q -k 'codex and (check or wrapper)'
```

Expected: FAIL because current Codex checks still privilege command-surface verification.

- [ ] **Step 3: Update shell and PowerShell checks**

Implement these rule changes:

- keep `resolve_skill_descriptor_path()` as the source of truth for visible skills
- add Codex-specific checks for the three wrappers
- if command shims are kept, check them as non-blocking compatibility artifacts only

- [ ] **Step 4: Re-run the targeted check-related tests**

Run:

```bash
python3 -m pytest \
  tests/runtime_neutral/test_runtime_contract_schema.py \
  tests/runtime_neutral/test_installed_runtime_scripts.py -q -k 'codex and (check or wrapper)'
```

Expected: PASS.

## Chunk 5: Reduce Command Surface To Compatibility Layer

### Task 5: Keep or trim command files without letting them define product truth

**Files:**
- Modify: `commands/vibe.md`
- Modify: `commands/vibe-what-do-i-want.md`
- Modify: `commands/vibe-how-do-we-do.md`
- Modify: `commands/vibe-do-it.md`
- Modify: `tests/integration/test_dist_manifest_surface_roles.py`

- [ ] **Step 1: Write the failing compatibility assertions**

Add assertions that command files, if retained, are documented as compatibility surfaces and not the preferred Codex discovery path.

- [ ] **Step 2: Run the targeted manifest-surface test and confirm the current contract fails**

Run:

```bash
python3 -m pytest tests/integration/test_dist_manifest_surface_roles.py -q
```

Expected: FAIL if the distribution surface still implies commands are the primary Codex user entry.

- [ ] **Step 3: Rewrite command templates as compatibility shims**

Adjust command descriptions so they clearly route into canonical `vibe` and no longer imply that commands are the preferred primary surface.

- [ ] **Step 4: Re-run the manifest-surface test**

Run:

```bash
python3 -m pytest tests/integration/test_dist_manifest_surface_roles.py -q
```

Expected: PASS.

## Chunk 6: Real-Host Verification

### Task 6: Verify the skill-first surface against the real Codex root

**Files:**
- Modify: none
- Test: real host root `~/.codex`

- [ ] **Step 1: Reinstall into the real Codex host root**

Run:

```bash
CODEX_HOME="$HOME/.codex" bash ./install.sh --host codex --profile full
```

- [ ] **Step 2: Run governed check**

Run:

```bash
CODEX_HOME="$HOME/.codex" bash ./check.sh --host codex --profile full
```

Expected: PASS, with offline AI-governance warnings allowed.

- [ ] **Step 3: Confirm the host-visible skill files**

Run:

```bash
find "$HOME/.codex/skills" -maxdepth 2 -name SKILL.md | sort
```

Expected to include:

- `~/.codex/skills/vibe/SKILL.md`
- `~/.codex/skills/vibe-what-do-i-want/SKILL.md`
- `~/.codex/skills/vibe-how-do-we-do/SKILL.md`
- `~/.codex/skills/vibe-do-it/SKILL.md`

- [ ] **Step 4: Confirm command surface is only compatibility truth**

Run:

```bash
find "$HOME/.codex/commands" -maxdepth 1 -type f | sort
```

Expected: command files may still exist, but successful installation no longer depends on them being the primary discoverability story.
