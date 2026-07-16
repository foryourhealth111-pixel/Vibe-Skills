# Local Agent Kernel V2

## Conclusion

The next version should be a small local work kernel, not a router-centered platform.

The public story for this pass is intentionally narrow:

- declared local skill roots are the only specialist reference surface
- a skill must have a readable `SKILL.md` before it can be selected
- `agent_skill_organization` is the Agent-owned skill plan, and `module_assignments` is its validated execution projection into Agent-owned work

This is a practical next step, not a claim that the final architecture is complete.

The binding flow is explicit:

```text
candidate discovery -> Agent reads `SKILL.md` -> `agent_skill_organization` -> `module_assignments` -> execution handoff -> Agent work -> module result return
```

Planner preference is candidate audit only. It cannot bind or execute a skill, and a run without `agent_skill_organization` stays at `awaiting_agent_skill_organization` with an empty `module_assignments`.

At `plan_execute`, Vibe writes `agent-execution-handoff.json` and returns control
to the current Agent. The Agent follows the assigned `SKILL.md` files, completes
the modules, writes `module-execution.json`, and returns it through canonical
`vibe` re-entry. Vibe organizes and validates this path; it never pretends to
run a Skill itself.

## Why This Direction

The old shape asked the router to do too much. It tried to decide intent, choose skills, shape the plan, and act like the control plane. That made normal changes expensive and made extension feel heavier than the work itself.

The new cut is simpler:

- the kernel owns process
- user-owned installed skills own capability
- discovery only finds candidates
- planning defines bounded work modules
- the Agent reads candidate contracts and publishes `agent_skill_organization`
- `module_assignments` records the validated execution projection into Agent-owned work
- verification states what the available evidence proves

The runtime boundary for this pass is also explicit:

- Python owns final truth artifacts, canonical validation, task semantics, `module_assignments`, planning decisions, and structured runtime result data.
- PowerShell still performs stage orchestration, environment setup, script bridging, host bookkeeping, and shell-native checks.
- Scaffolds and drafts are `needs_execution` with `proof_ready = false`; they are not completed work.
- A future full-Python runtime is optional. It is not required for this version.

This keeps problems local. If discovery quality is weak, we improve discovery. If plans are weak, we improve planning. If proof is weak, we improve verification.

## Design Rules

- Install into `<SkillsDir>/vibe` and treat `<SkillsDir>` as the public skills directory.
- Prefer convention over configuration.
- Treat host-declared local skill roots as the only task-Skill source.
- Exclude the controller entry `vibe` from the task-Skill pool.
- Require `agent_skill_organization` before any task skill can enter `module_assignments` or execution.
- Treat `module_assignments` as the validated execution projection into Agent-owned work, not as proof that Vibe ran a Skill.
- Derive Skill use from completed module work; do not create a separate usage ledger, Skill-file hash proof, or artifact-impact receipt.
- Require `runtime-input-packet.json`, `governance-capsule.json`, and `stage-lineage.json` before calling a local-agent-kernel launch canonical verified.
- Use generated catalog and index files only as derived artifacts.
- Do not require a central skill registry for ordinary skills.
- Do not let an arbitrary directory become active just because it exists.
- Do not add new task semantics to PowerShell; existing PowerShell stage scripts are transitional orchestration surfaces.
- Do not describe the repo-owned bundled corpus as an extension or fallback story.

## Terminology

### SkillsDir

The public skills directory selected by install or runtime launch. Vibe lives at `<SkillsDir>/vibe`; ordinary skills live under `<SkillsDir>/*`.

### Host-Declared Local Skill Root

A skill root declared by the current host adapter. It is read-only from the kernel's point of view and can point at the selected SkillsDir or another explicitly configured root.

### User-Owned Skill Folder

A skill folder the user or host manages directly. This can live under a host-declared root or under the installed local root.

### Skill Catalog

A full discovered view of eligible skills. It can show source, precedence, duplicates, and inactive entries. It is for inspection and derived outputs, not for claiming what really ran.

### Active Index

A deduplicated lookup cache projected from the catalog. It is the fast discovery surface, not the runtime truth surface.

### Work Binding

The runtime artifact that projects the Agent-confirmed organization into bounded work units. It is the validated execution projection into Agent-owned work, not a discovery result or a claim that work already happened.

## Runtime Shape

The installed runtime should look like this:

```text
<SkillsDir>/
  vibe/
    kernel/
      task/
      finder/
      planner/
      executor/
      verifier/
      state/
    generated/
      skills-catalog.json
      skills-index.json
    runs/
      <run-id>/
        task-card.json
        plan.json
        module-assignments.json
        agent-execution-handoff.json
        module-execution.json
        run-state.json
        verification.json
```

Host-declared local skill roots may live outside the selected `<SkillsDir>`. They are referenced by discovery and catalog artifacts, not copied into a repo-owned central corpus first.

### Meaning Of Each Area

- `kernel/` is the semantic core. It owns process and bounded work.
- `generated/` contains derived catalog and index artifacts.
- `runs/` contains the work plan, Agent handoff, returned module results, and verification records.
- host-declared local roots are the task-Skill reference surface.

## Discovery Rules

The system should discover skills by fixed declared roots, not by a layered routing control plane.

### Required Rules

1. Resolve the selected `<SkillsDir>` or host-declared skill roots in priority order.
2. Resolve host-declared project skill roots only when the host contract declares them.
3. Scan `<root>/<skill-id>/SKILL.md` and `<root>/custom/<skill-id>/SKILL.md`.
4. Read frontmatter from each discovered `SKILL.md`.
5. Validate that each usable entry has at least a name and description.
6. Record invalid entries and inactive duplicates as diagnostics.
7. Build `generated/skills-catalog.json` as the full discovered view.
8. Project the active entries into `generated/skills-index.json` with schema `local_skill_index_v2`.
9. Keep discovered candidates out of `module_assignments` until the Agent publishes `agent_skill_organization`.

### Precedence

The public contract is SkillsDir-centered. When a host supplies defaults, the intended duplicate-resolution order for this pass is:

1. Codex: `~/.agents/skills`
2. Codex: `~/.codex/skills`
3. Claude Code: `~/.claude/skills`

This ordering is about duplicate resolution. It does not make any missing or unreadable skill selectable.

### Forbidden Rules

- no repo-owned bundled corpus as the main extension surface
- no arbitrary repository path becomes a live route source because it exists
- no central pack manifest for ordinary skill registration
- no alias map as a second source of truth
- no hidden directory scanning outside declared roots
- no separate routing file that re-describes what a skill already says about itself

## Skill Contract

Each skill should stay self-describing. The minimum contract should live in the frontmatter of `SKILL.md`.

Example:

```md
---
id: code-review
name: Code Review
description: Review an implementation for behavior risk, design drift, and missing tests.
when_to_use:
  - The user asks for a review.
  - The result looks correct but may hide regressions.
not_for:
  - Building a feature from scratch.
inputs:
  - task goal
  - changed files
outputs:
  - findings
  - test gaps
  - next recommendation
plan_hints:
  - inspect change surface first
  - test the highest-risk path before summarizing
verify_hints:
  - confirm each finding against code or tests
tags:
  - review
  - testing
  - architecture
enabled: true
priority: 50
---
```

### Required Fields

- `id`
- `name`
- `description`
- `when_to_use`
- `not_for`
- `inputs`
- `outputs`
- `enabled`

### Optional Fields

- `plan_hints`
- `verify_hints`
- `tags`
- `examples`
- `priority`

The source root, source kind, and provenance fields are derived by the kernel from where the skill was discovered. They should not be duplicated as a second manual registration layer.

## Kernel Modules

The kernel should stay small. It only needs six core modules plus a binding artifact.

### Task Module

Turns a user request into a task card.

### Finder Module

Retrieves candidate skills from the active index. The active index contains only usable local skills from declared roots.

### Planner Module

Builds bounded work units from the task card and candidates.

### Agent Handoff Module

Turns the approved module plan into `agent-execution-handoff.json`, then waits
for the current Agent to return `module-execution.json`. It does not run Skills.

### Verifier Module

Checks whether the available evidence satisfies the completion criteria or still needs execution.

### State Module

Owns the runtime loop and current status.

### Module Assignments Artifact

Records which skill was bound to each work unit and where that skill came from.

## Runtime Contracts

The new system should keep the runtime contracts small and inspectable.

### Catalog

`generated/skills-catalog.json`

This file shows the full discovered view, including source information and inactive or shadowed entries.

### Active Index

`generated/skills-index.json`

This file is the fast lookup view projected from the catalog.

### Task Card

`runs/<run-id>/task-card.json`

This records goal, deliverables, constraints, missing information, completion criteria, and mode.

### Plan

`runs/<run-id>/plan.json`

This records bounded work units and the preferred skill choice for each unit.

### Module Assignments

`runs/<run-id>/module-assignments.json`

This records approved Skill assignments, expected outputs, verification needs,
and selected-source details. It does not claim that the assigned work ran.

### Agent Execution Handoff

`runs/<run-id>/agent-execution-handoff.json`

This tells the current Agent which `SKILL.md` to read, what module to complete,
what outputs to produce, how to verify them, and how to return the complete
module result.

### Module Execution Return

`runs/<run-id>/module-execution.json`

This is the Agent's complete return for the approved work units. Canonical
re-entry validates it against the frozen plan before cleanup can begin.

### Run State

`runs/<run-id>/run-state.json`

This records current progress through the loop.

### Verification

`runs/<run-id>/verification.json`

This records whether the work is done, needs rework, or needs replanning.

## State Machine

The state machine should stay explicit and small.

```text
capture -> clarify -> find_skills -> organize_skills -> plan -> handoff -> await_agent -> accept_results -> verify -> close
                          ^                                  |                    |
                          |                                  v                    v
                          +----------------------------- replan <------------ rework
```

### State Meanings

- `capture`: create the first task card from the user request
- `clarify`: fill missing information when the task card is incomplete
- `find_skills`: retrieve candidate skills from declared local roots only
- `organize_skills`: the Agent reads retained `SKILL.md` files and publishes `agent_skill_organization`
- `plan`: generate work units
- `handoff`: write `agent-execution-handoff.json` and return control to the Agent
- `await_agent`: the current Agent reads assigned Skills and completes the modules
- `accept_results`: canonical re-entry validates `module-execution.json`
- `verify`: compare outputs against completion criteria
- `close`: summarize and persist results

The router disappears as a top-level state because it is no longer the owner of process.

## Language Split

Python should own the kernel because it is better suited for data contracts, final truth artifacts, canonical validation, planning logic, testing, and structured runtime result modules.

PowerShell still performs stage orchestration where it has real leverage:

- install
- check
- stage coordination
- environment setup
- script bridging
- Windows host wiring
- shell-native checks when a specific step truly needs PowerShell

This keeps the final semantic authority in Python without pretending the current PowerShell runtime is only a thin host adapter.

## Small Hot Path

The hot path should stay short:

1. read task
2. resolve eligible skill roots
3. build or load the skill catalog and active index
4. retrieve candidates
5. let the Agent read retained `SKILL.md` files and publish `agent_skill_organization`
6. project `module_assignments`
7. freeze the approved module work plan
8. write `agent-execution-handoff.json` and return control to the Agent
9. accept `module-execution.json` through canonical re-entry
10. verify

Anything not needed for that path should stay out of it.

The default closure story should stay small too: governed runtime contract, canonical entry truth, runtime execution proof, release truth consistency, and repo cleanliness. Wider packaging or retired-routing audit gates are still useful, but they are not the normal closeout path.

## Large Extension Surface

The extension surface should be wide even while the kernel stays small.

A new ordinary skill should require only:

1. put a skill folder under a declared local skill root
2. write `SKILL.md`
3. optionally add examples or tests
4. let the catalog and index rebuild

No router surgery and no repo-owned corpus promotion should be needed.

## What To Delete Or Retire

The following ideas should lose authority in v2:

- repo-owned bundled skill growth as the public product story
- router-led plan ownership
- central routing config as the normal way to add ordinary skills
- PowerShell as semantic authority
- duplicated descriptions of the same skill across multiple files

This does not mean every old file must disappear on day one. It means those files must stop being the source of truth.

## Migration Plan

### Phase 1: Freeze Growth In The Old Shape

- stop expanding bundled skills as the main product story
- stop adding new routing rules for ordinary skill admission
- keep the old runtime working, but do not deepen it

### Phase 2: Add Local-Only Discovery

- resolve host-declared local skill roots
- allow users to add declared local skill roots through runtime configuration
- add `generated/skills-catalog.json`
- add `generated/skills-index.json`

### Phase 3: Build The Kernel Loop

- implement task card creation
- implement finder against the active index
- implement planner that outputs bounded work units
- require the Agent organization before binding
- implement `module_assignments` as the validated execution projection into Agent-owned work
- emit the Agent execution handoff and strictly accept the returned module result
- implement verifier against completion criteria

### Phase 4: Demote The Router

- convert router authority into discovery support
- keep legacy PowerShell only as a compatibility adapter
- remove plan ownership from the old route layer

### Phase 5: Keep The Public Story Small

- install only the controller and public entries
- move public value toward user-owned installed skill composition
- keep docs focused on how to install, inspect, and extend the kernel without a bigger central catalog

## Non-Negotiable Outcome

The next version succeeds only if a user can install Vibe into `<SkillsDir>/vibe`, make a skill visible under a declared user-owned root, and get honest bounded work status without editing a stack of routing files.

If that is not true, the design is still too heavy.
