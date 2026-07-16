# Local Agent Kernel V2 Interfaces

## Conclusion

The next implementation step is not a brand-new platform. It is a clearer contract for who owns what.

For this pass, the public interface story should stay simple:

- host-declared local skill roots are the only specialist source
- a skill must have a readable `SKILL.md` before it can be selected
- `skills-catalog.json` and `skills-index.json` are derived discovery artifacts
- `agent_skill_organization` is the Agent-owned skill plan, and `module_assignments` is its validated execution projection

This document describes the interfaces needed to make that story inspectable without overstating the maturity of the whole architecture.

```text
candidate discovery -> Agent reads `SKILL.md` -> `agent_skill_organization` -> `module_assignments` -> execution
```

Planner preference is candidate audit only. It cannot populate `module_assignments` or authorize execution.

## What We Keep

The current runtime package already has useful building blocks. The goal is not to throw them away. The goal is to move ownership downward into the kernel and make the local-skill-root discovery contract visible in files, commands, and run artifacts.

The practical result should be:

- a small kernel slice under the existing runtime package
- host-aware local discovery inputs
- a catalog artifact for the full discovered surface
- an active index for fast lookup
- an Agent-confirmed `agent_skill_organization`
- a `module_assignments` artifact with validated source details and provenance

## Ownership Shift

### Old Ownership

The old hot path was effectively:

1. entry
2. router
3. plan
4. execute stages

That gave the route result too much authority.

### New Ownership

The new hot path should be:

1. entry
2. task card
3. resolve eligible roots
4. build catalog and active index
5. find candidates
6. let the Agent read retained `SKILL.md` files and publish `agent_skill_organization`
7. project `module_assignments`
8. plan bounded execution
9. execute
10. verify

The route layer becomes discovery support instead of process owner.

## Module Layout

The cleanest near-term layout is still to add a local-kernel slice under the existing runtime package:

```text
packages/runtime-core/src/vgo_runtime/
  kernel/
    __init__.py
    host_skill_roots.py
    task_card.py
    skill_manifest.py
    skill_index.py
    finder.py
    work_plan.py
    planner.py
    executor.py
    verifier.py
    module_assignments.py
    run_state.py
    loop.py
  canonical_entry.py
  planning.py
  stage_machine.py
  runtime_bridge.py
  powershell_bridge.py
```

## Interface Principles

- ordinary skills should remain self-describing through `SKILL.md`
- local skill roots should be declared by the host, not guessed
- the controller entry `vibe` should stay out of the specialist pool
- catalog and index artifacts should describe discovery, not replace runtime truth
- `agent_skill_organization` should be the only source allowed to create task-skill bindings
- `module_assignments` should carry the validated source details and provenance needed for inspection
- the public CLI should stay narrow and match real operator actions

## Root Resolution Interface

### Purpose

The kernel needs a small host-aware interface that says which skill roots are eligible for discovery.

### Suggested Data Shape

```python
@dataclass(frozen=True, slots=True)
class HostSkillRoot:
    host_id: str
    root_key: str
    path: Path
    source: str
```

### Suggested Function

```python
def resolve_host_skill_roots(
    *,
    repo_root: Path,
    host_id: str,
    agent_root: Path,
    workspace_root: Path | None,
) -> tuple[HostSkillRoot, ...]: ...
```

### Meaning

- `host_id` selects the host adapter contract
- `workspace_root` allows hosts with project-scoped skill roots to contribute them explicitly
- the returned roots are read-only discovery inputs from the kernel's point of view

Host-declared local roots are the only specialist reference surface for this pass. The kernel should not describe the repo-owned bundled corpus as an extension or fallback path.

## Skill Manifest Interface

### Purpose

Each ordinary skill should stay self-describing.

### Suggested Data Shape

```python
@dataclass(frozen=True, slots=True)
class SkillManifest:
    id: str
    name: str
    description: str
    when_to_use: tuple[str, ...]
    not_for: tuple[str, ...]
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    plan_hints: tuple[str, ...] = ()
    verify_hints: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    enabled: bool = True
    priority: int = 50
    root_dir: str = ""
    skill_file: str = ""
```

### Suggested Functions

```python
def parse_skill_manifest(skill_file: Path) -> SkillManifest: ...
def validate_skill_manifest(manifest: SkillManifest) -> None: ...
```

## Catalog And Index Interfaces

### Why Two Artifacts

The kernel needs two derived discovery views for different jobs:

- `skills-catalog.json` is the full discovered surface
- `skills-index.json` is the active lookup surface

The catalog can show inactive, shadowed, or duplicate-related entries. The index should expose only the active entries used for fast matching.

### Suggested Catalog Entry Shape

```python
@dataclass(frozen=True, slots=True)
class SkillCatalogEntry:
    id: str
    name: str
    description: str
    enabled: bool
    priority: int
    source_kind: str
    source_root: str
    resolved_source_root: str
    resolved_root_dir: str
    resolved_skill_file: str
    source_priority: int
    source_order: int
    path_contract: str
    path_base: str
    active: bool
```

### Suggested Functions

```python
def build_skill_catalog(
    *,
    agent_root: Path,
    host_roots: tuple[Path, ...] = (),
) -> dict[str, object]: ...

def build_skill_index(
    agent_root: Path,
    *,
    host_roots: tuple[Path, ...] = (),
) -> dict[str, object]: ...

def write_skill_catalog(agent_root: Path, payload: dict[str, object]) -> Path: ...
def write_skill_index(agent_root: Path, payload: dict[str, object]) -> Path: ...
def load_skill_index(agent_root: Path) -> dict[str, object]: ...
```

### Required Output Files

```text
<agent_root>/vibe/generated/skills-catalog.json
<agent_root>/vibe/generated/skills-index.json
```

### Required Discovery Story

1. resolve host-declared global roots in priority order
2. resolve host-declared project roots only when the host contract declares them
3. scan `<root>/<skill-id>/SKILL.md` and `<root>/custom/<skill-id>/SKILL.md`
4. build `skills-catalog.json`
5. project active entries into `skills-index.json` with schema `local_skill_index_v2`

### Required Wording Boundary

This design should not be described as automatic orchestration of all installed skills. It is a local-skill-only discovery contract with a bounded runtime truth surface.

## Finder Interface

### Purpose

The finder should rank candidate skills using both relevance and source precedence.

### Suggested Data Shape

```python
@dataclass(frozen=True, slots=True)
class SkillCandidate:
    skill_id: str
    score: float
    matched_tokens: tuple[str, ...]
    search_tokens: tuple[str, ...]
    owner_tokens: tuple[str, ...]
    support_tokens: tuple[str, ...]
    blocked_tokens: tuple[str, ...]
    reasons: tuple[str, ...]
    warnings: tuple[str, ...] = ()
    source_kind: str = ""
    source_root: str = ""
    resolved_source_root: str = ""
    resolved_root_dir: str = ""
    resolved_skill_file: str = ""
    source_priority: int = 0
    source_order: int = 0
    path_contract: str = ""
    path_base: str = ""
```

### Suggested Function

```python
def find_skill_candidates(
    task_card: TaskCard,
    index_payload: dict[str, object],
    *,
    limit: int = 8,
) -> tuple[SkillCandidate, ...]: ...
```

### Required Precedence Rule

The current intended precedence is:

1. Codex `~/.agents/skills`
2. Codex `~/.codex/skills`
3. Claude Code `~/.claude/skills`

This rule should stay visible in the interface contract so operators can understand which duplicate skill entry stays active.

## Work Plan Interface

### Purpose

The planner should turn a task card and ranked candidates into bounded work.

### Suggested Data Shapes

```python
@dataclass(frozen=True, slots=True)
class WorkUnit:
    id: str
    goal: str
    depends_on: tuple[str, ...]
    preferred_skill: str | None
    fallback_skills: tuple[str, ...]
    expected_artifacts: tuple[str, ...]
    verification: tuple[str, ...]
    selected_skill_provenance: SkillProvenance | None = None
    status: str = "pending"


@dataclass(frozen=True, slots=True)
class WorkPlan:
    task_id: str
    work_units: tuple[WorkUnit, ...]
```

### Suggested Function

```python
def build_work_plan(
    task_card: TaskCard,
    candidates: tuple[SkillCandidate, ...],
) -> WorkPlan: ...
```

The internal data can keep `preferred_skill` and `fallback_skills` as candidate-audit hints. They must not populate exported `bound_skill`; only the validated `agent_skill_organization` can do that.

## Work Binding Interface

### Purpose

`module_assignments` is the validated execution projection of `agent_skill_organization`.

### Suggested Provenance Shape

```python
@dataclass(frozen=True, slots=True)
class SkillProvenance:
    source_kind: str
    source_root: str
    resolved_source_root: str
    resolved_root_dir: str
    resolved_skill_file: str
    source_priority: int
    source_order: int
    path_contract: str
    path_base: str
```

### Suggested Binding Unit Shape

```python
@dataclass(frozen=True, slots=True)
class ModuleAssignmentsUnit:
    work_unit_id: str
    bound_skill: str | None
    binding_profile: str
    binding_reason: str | None
    alternative_skills: tuple[str, ...]
    expected_artifacts: tuple[str, ...]
    verification: tuple[str, ...]
    provenance: SkillProvenance | None
```

### Required Export Meaning

The exported `module_assignments.json` should make it easy to inspect:

- which Agent-confirmed skill was bound
- what alternatives existed
- what source kind won
- what source root and resolved paths produced that choice

These validated binding details are more authoritative than catalog, planner preference, route, or benchmark summaries when you need to know what was authorized for execution.

## Loop Interface

### Purpose

The loop should own the runtime process and write the run artifacts.

### Suggested Function

```python
def run_local_kernel(
    *,
    agent_root: Path,
    prompt: str,
    context: dict[str, object] | None = None,
    run_id: str | None = None,
    host_id: str = "codex",
    workspace_root: Path | None = None,
    agent_skill_organization: dict[str, object] | None = None,
    execute: bool = True,
) -> dict[str, object]: ...
```

### Required Behavior

- resolve eligible roots from `host_id` and `workspace_root`
- build `skills-catalog.json`
- project `skills-index.json` from the same catalog view
- expose candidate modules without binding when `agent_skill_organization` is absent
- validate `agent_skill_organization` against the discovered candidates
- write `module_assignments.json` only as that organization's execution projection
- execute bounded work only when the organization is present and `execute` is true

The loop should not discover one set of roots for the catalog and a different set for the active index.

## CLI Surface

### Purpose

The command surface should stay narrow and map to real operator actions.

### Required Commands

```text
vgo index --agent-root <path> --host-id <host>
vgo index --agent-root <path> --host-id <host> --workspace-root <path>

vgo run --agent-root <path> --prompt "..." --host-id <host>
vgo run --agent-root <path> --prompt-file <path> --host-id <host> --workspace-root <path>

vgo inspect-run --agent-root <path> --run-id <id> --host-id <host>
vgo inspect-run --agent-root <path> --run-id <id> --host-id <host> --workspace-root <path>
```

### Required Input Meaning

- `--host-id` chooses which host contract declares eligible local roots
- `--workspace-root` lets project-scoped host roots participate explicitly

These inputs matter because host-declared local roots are the only specialist source in this pass. They are not optional narrative details.

## Agent Root Contract

The install root should still look like this:

```text
<agent_root>/
    vibe/
    generated/
    runs/
```

Host-declared local roots may live outside this tree, but the generated artifacts inside `<agent_root>/vibe/generated/` should still describe them clearly.

## Run Artifact Surface

### Required Files

```text
<agent_root>/vibe/generated/skills-catalog.json
<agent_root>/vibe/generated/skills-index.json
<agent_root>/vibe/runs/<run-id>/task-card.json
<agent_root>/vibe/runs/<run-id>/plan.json
<agent_root>/vibe/runs/<run-id>/module-assignments.json
<agent_root>/vibe/runs/<run-id>/run-state.json
<agent_root>/vibe/runs/<run-id>/verification.json
```

### Artifact Roles

- `skills-catalog.json`: full discovered surface with source metadata
- `skills-index.json`: active deduplicated lookup surface
- `plan.json`: bounded work units and preferred choices
- `module-assignments.json`: runtime truth for final selected source details

## Mapping To Current Files

### `canonical_entry.py`

Keep it as the public entry wrapper for now, but make it delegate into the kernel loop.

### `router.py`

Reduce it to discovery support or compatibility shims. It should stop returning the object that decides the whole runtime.

### `planning.py`

Keep it temporarily, but move the durable contract toward bounded work and `module_assignments`.

### `execution.py`

Keep it, but narrow its job to executing bounded work and recording outcomes.

### `stage_machine.py`

Keep it as a thin state helper if useful, but do not let it pull discovery authority back into the old route model.

## Migration Slices

### Slice 1

- add host root resolution
- add `skills-catalog.json`
- keep `skills-index.json`
- expose `--host-id` and `--workspace-root`

### Slice 2

- add source-aware candidate ranking
- add selected source details to `module_assignments`
- keep unusable or duplicate skills in diagnostics, not in selected work

### Slice 3

- tighten inspect-run so it validates requested host context
- make resume behavior provenance-aware
- keep `module_assignments` as the first truth surface

## Tests

The first tests should protect contracts and operator-facing evidence.

Suggested order:

1. host root resolution
2. catalog build and duplicate handling
3. active index projection
4. source-aware candidate ranking
5. CLI pass-through for `--host-id` and `--workspace-root`
6. `module_assignments` provenance export
7. inspect-run host-context validation

## Non-Negotiable Outcome

After this migration wave, an operator should be able to inspect one install root and answer three practical questions:

1. which local roots were eligible
2. which entries were active in discovery
3. which skill and source actually won at runtime

If the files and CLI cannot answer those questions, the interface contract is still too vague.
