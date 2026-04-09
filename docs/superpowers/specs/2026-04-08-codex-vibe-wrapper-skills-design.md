# Codex Vibe Wrapper Skills Design

## Summary
Shift the Codex-facing `vibe` surface from `commands`-first to `skills`-first.

The target shape is:

- one canonical runtime skill: `vibe`
- three thin wrapper skills:
  - `vibe-what-do-i-want`
  - `vibe-how-do-we-do`
  - `vibe-do-it`

The wrappers do not become parallel runtimes. They exist only to bias how the canonical `vibe` runtime is entered.

## Problem
The current Codex user-facing surface is being materialized mainly through command files under `commands/`.

That solves discoverability, but it does not match the intended product model:

- the user wants four visible skill-like entries in Codex
- `vibe` should remain the only canonical governed runtime
- the three additional entries should express different entry intents, not different runtime authorities

If we keep building this solely as `commands`, the visible surface stays command-oriented rather than skill-oriented.

If we instead split everything into four independent runtime skills, we break the current `vibe` contract that says there is one governed entry and one runtime authority.

## Goals
- Make Codex discover the `vibe` family primarily through installable skills rather than command files.
- Preserve `vibe` as the only canonical governed runtime skill.
- Add three wrapper skills that encode entry bias only:
  - intent clarification
  - approach and planning
  - approved-plan execution
- Keep install, check, and host reporting truthful.
- Allow a staged compatibility period where old command files can still exist but are no longer the primary surface.

## Non-Goals
- Do not create a second runtime authority.
- Do not create separate requirement, plan, or cleanup contracts for the wrappers.
- Do not redesign the six-stage governed runtime.
- Do not change the public host list.
- Do not treat wrapper discoverability as proof that MCP is complete.

## Design Options Considered

### Option A: Keep `commands` as the primary surface
Use the existing four command files and stop there.

Pros:

- smallest implementation delta
- already proven to work in Codex

Cons:

- does not match the desired `skills` mental model
- keeps user-facing discoverability tied to command files rather than skill entries

### Option B: Four independent skills with equal authority
Create `vibe`, `vibe-what-do-i-want`, `vibe-how-do-we-do`, and `vibe-do-it` as peers.

Pros:

- strongest match to "four visible skills"

Cons:

- conflicts with the canonical `vibe` contract
- creates ambiguity around requirement freeze, plan freeze, and final completion authority
- increases governance and verification complexity for no real gain

### Option C: One canonical skill plus three thin wrapper skills
Keep `vibe` as the only canonical runtime skill and let the three wrappers hand off into it with an explicit entry bias contract.

Pros:

- matches the desired surface shape
- preserves runtime truth
- keeps governance centralized
- allows commands to be reduced to compatibility shims or removed later

Cons:

- requires a new installable skill surface in the repo
- requires installer and check changes beyond the current command materialization

## Decision
Choose **Option C**.

Codex should surface a `vibe` skill family, but only `vibe` itself remains the governed runtime authority. The other three entries are wrappers that bias entry semantics and then defer to the canonical runtime.

## Core Contract

### 1. Canonical Runtime Truth
`vibe` remains the only canonical governed runtime skill.

Only `vibe` owns:

- the six-stage state machine
- requirement freeze authority
- plan freeze authority
- execution authority
- phase cleanup authority
- final completion wording for the governed task

### 2. Wrapper Skills Are Entry Bias Only
Each wrapper skill is a thin skill package whose purpose is to express one user-facing entry intent.

The wrappers must:

- identify their entry bias
- instruct Codex to invoke canonical `vibe`
- pass along a structured bias contract
- avoid creating their own runtime lifecycle

The wrappers must not:

- define a second governed runtime
- freeze a second requirement document
- freeze a second plan
- declare their own completion authority
- override the canonical router

### 3. Wrapper Meanings

#### `vibe-what-do-i-want`
Entry bias:

- intent clarification
- scope shaping
- requirement-first discovery

Expected runtime emphasis inside canonical `vibe`:

- stronger `deep_interview`
- stronger requirement clarification before planning

#### `vibe-how-do-we-do`
Entry bias:

- approach selection
- planning
- sequencing

Expected runtime emphasis inside canonical `vibe`:

- stronger transition from `deep_interview` to `xl_plan`
- explicit design and execution-structure framing

#### `vibe-do-it`
Entry bias:

- execution from an already approved or nearly-approved direction

Expected runtime emphasis inside canonical `vibe`:

- proceed toward `plan_execute`
- still respect requirement and plan gates
- do not skip cleanup or verification

`vibe-do-it` does not mean "skip governance". It means "enter governance with an execution-forward bias".

### 4. Canonical Handoff Shape
Each wrapper should hand off to `vibe` using a small stable contract.

Minimum fields:

- `entry_skill`
- `entry_bias`
- `requested_emphasis`
- `authority = canonical_vibe`

This contract can be implemented as frontmatter, embedded guidance, or an internal runtime packet, but the semantics must remain stable.

### 5. Naming Rule
Use portable physical names for installable skills:

- `vibe`
- `vibe-what-do-i-want`
- `vibe-how-do-we-do`
- `vibe-do-it`

Do not require colon characters in physical skill directory names.

If a host later supports prettier display aliases, that can be a presentation concern rather than a filesystem contract.

## Repository Shape

### New Source Surface
Add a repo-owned installable skill source surface for Codex-visible skills.

Expected source family:

- canonical skill source for `vibe`
- wrapper skill source for `vibe-what-do-i-want`
- wrapper skill source for `vibe-how-do-we-do`
- wrapper skill source for `vibe-do-it`

Each skill source should be independently installable and verifiable.

### Content Strategy
The canonical `vibe` skill keeps the long-form runtime contract.

The three wrappers should stay short:

- frontmatter
- concise statement of wrapper purpose
- explicit delegation to canonical `vibe`
- guardrails forbidding second-runtime behavior

Avoid copying the full `vibe` contract into wrapper skill files.

## Installer Contract

### Codex Install
For Codex full install into the real host root `~/.codex`, the installer should materialize the skill family into the host-visible skill surface first.

Primary success condition for this design:

- Codex can discover all four skill entries from the native skill surface

Secondary compatibility condition:

- existing `commands` may remain temporarily available while the skill surface is stabilized

### Command Compatibility
`commands` should move from `primary surface` to `compatibility layer`.

Compatibility policy:

- keep only if they are needed for migration or older workflows
- do not describe them as the preferred Codex experience
- do not let command presence substitute for skill-surface verification

This means future checks should treat skill discoverability as the primary truth and command files as optional compatibility truth.

## Check Contract

### Required Host-Visible Checks
Codex check flow should eventually validate:

- canonical `vibe` skill exists in the installed skill surface
- wrapper `vibe-what-do-i-want` exists
- wrapper `vibe-how-do-we-do` exists
- wrapper `vibe-do-it` exists
- canonical `vibe` remains the only runtime authority surface

### Optional Compatibility Checks
If command shims are retained, they should be checked as optional compatibility artifacts rather than the primary health signal.

## Migration Strategy

### Phase 1
Add wrapper skill sources and install them alongside the current command surface.

### Phase 2
Switch Codex install/check truth to skill-first.

### Phase 3
Downgrade command checks to optional compatibility checks.

### Phase 4
Decide whether command shims remain permanently for backward compatibility or are removed.

## Verification Plan
Implementation should be considered correct only when all of the following are true:

- a real Codex install into `~/.codex` materializes the four skill entries
- Codex host-visible verification checks the skill family directly
- wrappers do not duplicate or fork the canonical runtime contract
- command compatibility, if retained, does not become the primary proof surface
- uninstall inventory accounts for the new wrapper skill files

## Risks
- The current repo does not yet expose a dedicated source skill directory, so install plumbing will need to grow a new source surface rather than only reshuffling existing commands.
- If wrapper content becomes too large, it will drift toward parallel runtime contracts.
- If checks continue to privilege commands, the user-visible product model will remain inconsistent.

## Recommendation
Implement the skill-first surface in a staged way:

1. add the installable wrapper skill sources
2. install them into Codex's real host-visible skill surface
3. change checks to validate skills first
4. keep commands only as temporary compatibility shims

This preserves the runtime truth that `vibe` is canonical while giving Codex the four visible entry points the user wants.
