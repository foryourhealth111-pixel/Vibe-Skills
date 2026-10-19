# Current Runtime Field Contract

Date: 2026-10-19

## Purpose

This document defines the current runtime truth vocabulary for Vibe-Skills.
The packet freezes approved plan inputs; later work-loop artifacts prove what
actually happened.

## Run Artifact Contract

`config/live-document-contract.json` is the executable authority for run
artifacts. Python and PowerShell resolve the same relative fields from the
governed workspace and fail closed when the file is missing, malformed, or
type-invalid. The stable diagnostic prefix is
`live governance artifact contract is required: <contract-path>:`.

The primary release-artifact sink is:

```text
.vibeskills/runs/<run_id>/
```

The sink contains the required `requirement`, `plan`, `status`, and `proof`
artifacts, their declared primary Markdown documents, `manifest.json`, and
`legacy-compatibility.json`. The primary document paths are resolved under the
run sink. Historical documentation roots such as `docs/requirements` and
`docs/plans` are compatibility destinations only and are rejected as the
primary sink.

Runtime session receipts have a separate declared boundary:

```text
.vibeskills/outputs/runtime/vibe-sessions/<run_id>/
```

`artifact_sink.session_receipts` is owned by `runtime`, has
`retention = workspace_local`, and requires `copy_to_artifact_sink = true`.
The runtime may write receipts in this workspace-local directory; completion
copies them into the primary run sink so the release artifact remains
self-contained. Each copied receipt is staged in the destination directory and
atomically replaces its destination entry. Copy failures preserve the previous
file, and replacing a destination hardlink preserves its other linked files.
Synchronization accepts only the exact contract-declared session root for the run. `legacy_projection_root` is a compatibility
projection under the declared compatibility window and does not change
primary ownership.

Child-governed stages may read the root requirement and plan. Those inherited
paths must resolve to the root run's contract-derived primary documents;
historical documentation paths are rejected. A child receipt records the
inherited inputs and does not claim a child-owned primary document destination.

Every compatibility destination is observable in the run manifest under
`legacy_compatibility.write_records`. Each record contains the normalized
workspace-relative POSIX `destination`, the contract `mode`, and the declared
`removal_release`. An empty list means that no compatibility write occurred;
the manifest still records `observable = true`.

## Canonical Truth Chain

```text
requirement guidance: skill_search_guide
plan truth: agent_skill_organization -> module-work-plan.json
handoff truth: module-work-plan.json -> agent-execution-handoff.json
execution truth: agent-execution-handoff.json -> module-execution.json
acceptance truth: module-execution.json -> delivery-acceptance-report.json
```

Meaning:

- `skill_search_guide` tells the Agent how to search declared local skill roots.
- `agent_skill_organization` freezes modules, candidates, selected skills,
  responsibilities, reasons, workflow level, and uncovered modules.
- `module-work-plan.json` freezes module dependencies, work units, write scopes,
  skill roles, and acceptance criteria.
- `agent-execution-handoff.json` tells the current Agent which approved modules
  to complete and which `SKILL.md` applies to each work unit.
- `module-execution.json` returns the Agent's work-unit results, failures,
  blocking reasons, and module states against that exact approved plan.

## Delivery Evidence and Result Publication

A completed file-producing unit supplies readable file evidence for each concrete
path or glob in its approved `expected_outputs`. Directory entries and missing
files cannot serve as file evidence. Descriptive reply outcomes remain supported;
an explicit `write_scope = "no task-file writes"` carries no file-delivery
requirement. Declared evidence paths are checked even for read-only work.
Use `./` or `session:` to identify extensionless file outputs explicitly. Output
paths or globs containing whitespace require an absolute path or one of these
prefixes; unprefixed phrases remain descriptive outcomes.

Relative evidence and output paths use the frozen packet's
`storage.workspace_root`, which must be absolute when present. An absolute path
identifies its file directly;
`session:<relative-path>` explicitly identifies a file inside the source session.
Legacy packets without a workspace root resolve relative paths inside that
session. Resolution never depends on the process working directory or a search
for whichever matching file happens to exist. Required TDD red/green evidence
must identify readable files; their presence does not establish test semantics.
Canonical results use `tdd_evidence.state`. Acceptance also reads legacy `status`;
when both fields are present, their nonempty values must agree after whitespace,
case, and existing legacy alias normalization (for example, `passed` resolves to
`passing`). Conflicting or non-text state fields fail acceptance even when the
requirement document freezes no TDD items. A submitted `not_applicable` state
cannot cancel frozen TDD evidence requirements or exceptions.

External module results are read and validated before publication. The direct
PowerShell entry validates stage, source run, plan digest, work-unit bindings,
and criterion results against the submitted snapshot. The root must be a JSON
object; `units`, `modules`, and each module's `criterion_results` must be arrays
of objects. It then atomically replaces
`module-execution.json`. A rejected submission preserves accepted results and
execution artifacts, including results from a completed run.

## Stage Rules

At `requirement_doc`:

- `skill_search_guide` is required.
- `agent_skill_organization` may be null.
- route candidates must not enter `module_assignments`.

Before `xl_plan`, `plan_execute`, or `phase_cleanup`:

- `agent_skill_organization` is required.
- every selected skill must exist in a declared local root.
- each module must declare exactly one execution mode: covered by a selected
  local Skill (`skill_assigned`), assigned directly to the current Agent without
  a local Skill (`agent_direct`), or blocked by an explicit Skill gap
  (`blocked_gap`).
- `module_assignments` selected ids must exactly match the organization.

After plan approval, bounded re-entry reuses the frozen organization. It must
not rerun procedural skill selection or silently add candidates.

## Runtime Input Fields

Canonical packet fields:

```text
skill_search_guide
agent_skill_organization
```

No separate decision object may choose task skills, bind work, or claim that
work ran outside this canonical chain.

## Shared Local Skill Authority

Python discovery, canonical admission, candidate audit, and the search guide use
one host-root resolver and read-only source scanner. Source precedence is:
workspace configuration, user configuration, the explicit host skills directory,
then existing host defaults and plugin caches. Root paths are deduplicated in
that order. The `route --workspace-root` input carries the same workspace into
the candidate audit as the canonical runtime packet.

Admission requires a safe leaf Skill ID, valid metadata, an enabled active
source, and a resolved descriptor contained in its declared root. Controller
entries and aliases are excluded. A disabled higher-priority duplicate remains
the winner and blocks admission; a lower-priority enabled source cannot replace
it. Host roots scan direct Skill directories and their supported `custom`
subdirectory. A nested vendor layout must declare its containing Skill root in
configuration; arbitrary recursive host-directory lookup is outside admission.
Codex plugin caches support recursive discovery. When the host inventory is
available, `codex plugin list --json` selects the exact installed, enabled
marketplace/plugin/version roots before Skill-ID deduplication. Historical and
disabled cache copies remain ineligible. Conflicting enabled Skill IDs remain
ambiguous. An invalid or unavailable inventory command produces an explicit
admission diagnostic; without a configured host inventory, unresolved cache
collisions continue to fail closed. Supplied entrypoints must
match the admitted descriptor. Frozen task Skill bindings retain the descriptor
entrypoint and SHA-256 of its bytes; plan replay and dispatch reject a changed
source or changed descriptor content. Candidate audit preserves the same
source eligibility and disabled-winner rejection as admission. An explicitly
requested missing or ineligible Skill retains its rejection; composite candidate
fallback cannot select a substitute. Authority lookup
writes no generated cards or catalog caches. The Agent owns task Skill selection; source authority reports
facts and eligibility only.

Planning and execution dispatch resolve configured roots against the frozen
packet's `storage.workspace_root`, including installed-copy execution and direct
plan replay. The packaged runtime includes the authority driver and its Python
implementation.

## Local Kernel Input Identity

Callers of the Python `run_local_kernel` interface may declare required input
files through `context.input_artifacts`, a list of non-empty path strings.
Relative paths resolve from `workspace_root`, or `agent_root` when a workspace
is omitted. The runtime persists absolute paths and their content SHA-256
snapshots in the TaskCard; callers do not supply hashes. These task-level
inputs apply to every work unit in that TaskCard. Free-form prompt and context
text remain descriptive and are not interpreted as file declarations.

Resume inherits the declared paths. The existing `extend` revision mode adds
paths, and `replace` replaces them when `input_artifacts` is explicitly present.
Input path merging and revision differences use exact path identity so
case-distinct files remain independently tracked on case-sensitive filesystems.
A content change invalidates prior task execution identity. Missing or unreadable
inputs block execution, and a mutation during execution prevents final verified
completion. Unchanged content remains reusable even when filesystem timestamps
change. Inspection reports current verification separately from the recorded
verification snapshot.

Completed-result reuse and final verification share readiness checks for final
artifacts, current output hashes, required execution receipts, Skill bindings,
proof references, and declared verification targets. Missing evidence makes a
result ineligible for reuse and sends the work through normal recovery.

Dependency readiness binds predecessor evidence to the approved WorkUnit: unit
identity, expected artifacts, Skill, verification targets, proofs, output bytes,
and required receipt. A dependent cannot run from an unrelated result or a
self-consistent result whose declared outputs differ from the approved plan.

Organization and plan preflight complete before accepted task, run-state, or
catalog-snapshot files are committed. Rejected candidates, dependencies, or
schemas preserve the accepted run, including partial legacy checkpoints.
Discovery may refresh its advisory card cache independently of that state.

Effective `known_context` and `unknowns` changes are recorded in TaskRevision as
`added_known_context`, `removed_known_context`, `added_unknowns`, and
`removed_unknowns`, and appear in the Markdown dossier. Older revision records
without these fields load with empty lists. Both `extend` and `replace` modes
record their actual changes.

## Native Bridge Lifetime

Native bridge commands run inside a bounded process tree: a Windows Job Object
or a dedicated POSIX process group. On Windows, a waiting start gate joins the
job before launching the target command. A timeout cancels the tree and drains
the captured streams before the bridge reports failure. POSIX cleanup reaps the
direct child and confirms process-group disappearance within a bounded cleanup
deadline; an unconfirmed exit fails closed. Normal completion also reclaims
remaining descendants. The existing JSON output-file contract,
environment, working directory, exit diagnostics, and partial-output diagnostics
remain available.

## Module Execution Truth

Preferred stable work-run surfaces:

```text
module-work-plan.json
agent-execution-handoff.json
module-execution.json
delivery-acceptance-report.json
```

- `module-work-plan.json`: the only dispatch authority after plan approval.
- `agent-execution-handoff.json`: the work instructions handed to the current Agent at `plan_execute`.
- `module-execution.json`: the Agent's returned work-unit results and module states bound to the approved plan.
- `delivery-acceptance-report.json`: module acceptance first, then task acceptance.

## Compatibility Audit Fields

These fields may remain readable for older hosts and proof readers:

```text
skill_routing.candidates
route_snapshot
canonical_router
divergence_shadow
```

They are audit mirrors only. Scores, order, route selection, and
`confirm_required` must not populate `agent_skill_organization`, bind work, or
stop the governed stage machine.

## Agent Execution Handoff

At `plan_execute`, Vibe organizes the approved work and writes
`agent-execution-handoff.json`. It then stops before cleanup with
`status = agent_action_required` and `control_owner = agent`.

The current Agent reads the listed `SKILL.md` files and completes the modules.
Vibe does not run those skills itself and does not manufacture successful
results on the Agent's behalf.

When the Agent finishes, it writes one complete `module-execution.json` and
returns it through canonical `vibe` re-entry. The runtime checks that the run,
modules, work units, and approved plan match before it can enter cleanup. This
return is not another requirement or plan approval step, and it does not search
for skills again.

Skill use is derived from completed work units in the approved module plan and
the returned module results. There is no separate Skill-use ledger, Skill-file
hash proof, or artifact-impact receipt.

## Retired Selection Fields

Current canonical code must not use these as task-skill truth:

```text
skill_selection
legacy_skill_routing
specialist_recommendations
specialist_dispatch
stage_assistant_hints
discussion_specialist_consultation
planning_specialist_consultation
```

Historical artifacts may still contain them. Current runtime behavior must use
`agent_skill_organization`, `module-work-plan.json`,
`agent-execution-handoff.json`, and `module-execution.json` instead. Retired
fields are not compatibility inputs for current execution.

## Delivery Evidence And Execution Freshness

Python canonical re-entry and direct PowerShell re-entry use the shared
`vgo_contracts.module_execution_contract` admission validator. The staged JSON
snapshot is validated before it is published to the session. Module `required` bindings
must be JSON booleans matching the approved plan; delivery acceptance checks
this type and binding independently.

A passing artifact-review declaration requires its own current readable evidence
files. The declaration source is recorded for traceability and does not satisfy
the evidence requirement. Missing files, directories, malformed path lists and
escaping `session:` paths prevent acceptance.

Skill provenance records `content_sha256` for the descriptor and
`resource_sha256` for the Skill directory's file paths and contents. Changes,
additions and deletions of scripts, templates, rules and references invalidate
completed-work reuse. Interpreter bytecode and generated tool cache directories
are excluded. Legacy checkpoints without a resource fingerprint are recomputed
before reuse. Contained resource links are fingerprinted with their resolved
targets. External and cyclic resources produce explicit scanner diagnostics.
