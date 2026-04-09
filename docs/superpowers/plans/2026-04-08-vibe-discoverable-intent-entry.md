# Vibe Discoverable Intent Entry Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add host-discoverable `vibe` intent shortcuts and `--l` / `--xl` public grade overrides while preserving one governed runtime authority, one six-stage state machine, and one canonical runtime entrypoint.

**Architecture:** Treat this as a contract-first change. First add failing tests for the shared shortcut metadata, runtime packet fields, and conflict rules. Then introduce a shared discoverable-entry config plus runtime contract refinements, extend the Python and PowerShell runtime packet layers to carry `entry_intent_id`, `requested_stage_stop`, and `requested_grade_floor`, and finally wire host-facing adapter metadata and docs to the same shared source of truth. No task should introduce a second runtime, duplicate requirement surface, or `stage x grade` public alias matrix.

**Tech Stack:** JSON contract/config files, Python dataclass-based runtime-core and CLI bridge code, PowerShell governed runtime scripts, Markdown docs, pytest/unittest, ripgrep verification

---

## Chunk 1: Contract And Metadata Freeze

### Task 1: Add failing contract tests for discoverable entries and runtime packet fields

**Files:**
- Create: `tests/contract/test_vibe_discoverable_entry_contract.py`
- Modify: `tests/contract/test_runtime_packet_contract.py`
- Modify: `tests/integration/test_runtime_packet_execution.py`
- Modify: `tests/unit/test_runtime_surface_contract.py`
- Spec reference: `docs/superpowers/specs/2026-04-08-vibe-discoverable-intent-entry-design.md`

- [ ] **Step 1: Add a dedicated contract test for the shared discoverable entry surface**

Create `tests/contract/test_vibe_discoverable_entry_contract.py` with assertions equivalent to:

```python
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_vibe_discoverable_entries_are_shared_and_non_explosive() -> None:
    payload = json.loads((REPO_ROOT / "config" / "vibe-entry-surfaces.json").read_text(encoding="utf-8"))
    entries = {entry["id"]: entry for entry in payload["entries"]}

    assert set(entries) == {"vibe", "vibe-want", "vibe-how", "vibe-do"}
    assert entries["vibe"]["display_name"] == "Vibe"
    assert entries["vibe-want"]["display_name"] == "Vibe: What Do I Want?"
    assert entries["vibe-how"]["display_name"] == "Vibe: How Do We Do It?"
    assert entries["vibe-do"]["display_name"] == "Vibe: Do It"
    assert entries["vibe-want"]["requested_stage_stop"] == "deep_interview"
    assert entries["vibe-how"]["requested_stage_stop"] == "xl_plan"
    assert entries["vibe-do"]["requested_stage_stop"] == "phase_cleanup"
    assert payload["grade_flags"] == ["--l", "--xl"]
    assert payload["forbid_stage_grade_matrix"] is True
```

- [ ] **Step 2: Extend the runtime packet contract test to cover the new optional fields**

Update `tests/contract/test_runtime_packet_contract.py` so the roundtrip covers:

```python
packet = RuntimePacket(
    goal="x",
    stage="deep_interview",
    entry_intent_id="vibe-how",
    requested_stage_stop="xl_plan",
    requested_grade_floor="XL",
)
restored = RuntimePacket.model_validate(packet.model_dump())
assert restored.entry_intent_id == "vibe-how"
assert restored.requested_stage_stop == "xl_plan"
assert restored.requested_grade_floor == "XL"
```

- [ ] **Step 3: Add failing execution assertions for stop-stage and grade-floor behavior**

Extend `tests/integration/test_runtime_packet_execution.py` with at least:

```python
def test_runtime_packet_execution_stops_after_requested_stage_stop() -> None:
    result = execute_runtime_packet(
        RuntimePacket(
            goal="plan only",
            stage="skeleton_check",
            entry_intent_id="vibe-how",
            requested_stage_stop="xl_plan",
        ),
        mode="interactive_governed",
        requested_skill="vibe-how",
    )

    assert [receipt["stage"] for receipt in result.stage_receipts] == [
        "skeleton_check",
        "deep_interview",
        "requirement_doc",
        "xl_plan",
    ]
    assert result.final_packet.stage == "xl_plan"
    assert result.route["runtime_selected_skill"] == "vibe"
```

Also add a failing assertion that a grade-floor request is reflected in the plan surface:

```python
assert result.plan["requested_grade_floor"] == "XL"
assert result.plan["internal_grade"] == "XL"
```

- [ ] **Step 4: Add a failing runtime-surface test for packaging the shared config**

Update `tests/unit/test_runtime_surface_contract.py` so the runtime payload projection expects the new shared file:

```python
assert "config/vibe-entry-surfaces.json" in contract["runtime_payload"]["files"]
```

- [ ] **Step 5: Run the targeted contract tests and confirm they fail**

Run:

```bash
pytest tests/contract/test_vibe_discoverable_entry_contract.py tests/contract/test_runtime_packet_contract.py tests/integration/test_runtime_packet_execution.py tests/unit/test_runtime_surface_contract.py -q
```

Expected: FAIL because the config file and optional runtime packet fields do not exist yet.

- [ ] **Step 6: Commit the failing-test checkpoint**

```bash
git add tests/contract/test_vibe_discoverable_entry_contract.py tests/contract/test_runtime_packet_contract.py tests/integration/test_runtime_packet_execution.py tests/unit/test_runtime_surface_contract.py
git commit -m "test: lock discoverable vibe entry contract"
```

### Task 2: Add the shared discoverable-entry metadata and refine runtime invariants

**Files:**
- Create: `config/vibe-entry-surfaces.json`
- Modify: `config/runtime-contract.json`
- Modify: `config/runtime-input-packet-policy.json`
- Modify: `config/runtime-config-manifest.json`
- Modify: `config/version-governance.json`
- Modify: `tests/integration/test_runtime_config_manifest_roles.py`
- Modify: `tests/integration/test_version_governance_runtime_roles.py`

- [ ] **Step 1: Create a shared config file for the four approved entries**

Create `config/vibe-entry-surfaces.json` with content shaped like:

```json
{
  "schema_version": 1,
  "canonical_runtime_skill": "vibe",
  "entries": [
    {
      "id": "vibe",
      "display_name": "Vibe",
      "requested_stage_stop": "phase_cleanup",
      "allow_grade_flags": true
    },
    {
      "id": "vibe-want",
      "display_name": "Vibe: What Do I Want?",
      "requested_stage_stop": "deep_interview",
      "allow_grade_flags": false
    },
    {
      "id": "vibe-how",
      "display_name": "Vibe: How Do We Do It?",
      "requested_stage_stop": "xl_plan",
      "allow_grade_flags": true
    },
    {
      "id": "vibe-do",
      "display_name": "Vibe: Do It",
      "requested_stage_stop": "phase_cleanup",
      "allow_grade_flags": true
    }
  ],
  "grade_flag_map": {
    "--l": "L",
    "--xl": "XL"
  },
  "forbid_stage_grade_matrix": true
}
```

- [ ] **Step 2: Refine the runtime contract to express one authority plus presentational aliases**

Update `config/runtime-contract.json` so it no longer relies on `single_user_facing_path` alone. Add or replace invariants equivalent to:

```json
"single_runtime_authority": true,
"discoverable_intent_entries_allowed": true,
"discoverable_entries_are_presentational": true,
"grade_alias_matrix_forbidden": true
```

Also point the contract at the shared metadata file, for example:

```json
"discoverable_entry_surface": "config/vibe-entry-surfaces.json"
```

- [ ] **Step 3: Extend runtime-input-packet policy with the new optional fields**

Update `config/runtime-input-packet-policy.json` so `required_fields` remains backward-compatible, but policy metadata explicitly recognizes:

```json
"optional_public_entry_fields": [
  "entry_intent_id",
  "requested_stage_stop",
  "requested_grade_floor"
]
```

Add validation hints such as:

```json
"public_grade_floor_allowlist": ["L", "XL"],
"shortcut_rejects_multiple_grade_flags": true,
"shortcut_rejects_multiple_entry_ids": true
```

- [ ] **Step 4: Ship the new config with the installed runtime payload**

Add `config/vibe-entry-surfaces.json` to:

- `config/runtime-config-manifest.json`
- `config/version-governance.json`

Ensure it appears in both:

- runtime config payload files
- required runtime markers / governance marker groups where appropriate

- [ ] **Step 5: Update manifest-role tests for the new shipped config**

Strengthen `tests/integration/test_runtime_config_manifest_roles.py` and `tests/integration/test_version_governance_runtime_roles.py` with assertions such as:

```python
assert "config/vibe-entry-surfaces.json" in manifest["files"]
assert "config/vibe-entry-surfaces.json" in runtime["required_runtime_markers"]
```

- [ ] **Step 6: Run the metadata and governance tests**

Run:

```bash
pytest tests/contract/test_vibe_discoverable_entry_contract.py tests/integration/test_runtime_config_manifest_roles.py tests/integration/test_version_governance_runtime_roles.py tests/unit/test_runtime_surface_contract.py -q
```

Expected: PASS for metadata and packaging once the config and manifest files are updated.

- [ ] **Step 7: Commit the shared metadata and contract refinement**

```bash
git add config/vibe-entry-surfaces.json config/runtime-contract.json config/runtime-input-packet-policy.json config/runtime-config-manifest.json config/version-governance.json tests/contract/test_vibe_discoverable_entry_contract.py tests/integration/test_runtime_config_manifest_roles.py tests/integration/test_version_governance_runtime_roles.py tests/unit/test_runtime_surface_contract.py
git commit -m "feat: add shared discoverable vibe entry metadata"
```

## Chunk 2: Runtime Packet And Stage-Stop Execution

### Task 3: Extend Python runtime-core to carry shortcut intent and stop-stage execution

**Files:**
- Modify: `packages/contracts/src/vgo_contracts/runtime_packet.py`
- Modify: `packages/runtime-core/src/vgo_runtime/stage_machine.py`
- Modify: `packages/runtime-core/src/vgo_runtime/router.py`
- Modify: `packages/runtime-core/src/vgo_runtime/planning.py`
- Modify: `packages/runtime-core/src/vgo_runtime/execution.py`
- Modify: `tests/contract/test_runtime_packet_contract.py`
- Modify: `tests/integration/test_runtime_packet_execution.py`

- [ ] **Step 1: Extend `RuntimePacket` with optional public-entry fields**

Change the dataclass in `packages/contracts/src/vgo_contracts/runtime_packet.py` to something like:

```python
@dataclass(slots=True)
class RuntimePacket:
    goal: str
    stage: str
    entry_intent_id: str | None = None
    requested_stage_stop: str | None = None
    requested_grade_floor: str | None = None

    @classmethod
    def model_validate(cls, payload: dict) -> "RuntimePacket":
        return cls(
            goal=str(payload["goal"]),
            stage=str(payload["stage"]),
            entry_intent_id=payload.get("entry_intent_id"),
            requested_stage_stop=payload.get("requested_stage_stop"),
            requested_grade_floor=payload.get("requested_grade_floor"),
        )
```

- [ ] **Step 2: Teach the stage machine to resolve bounded stage windows**

Add a helper to `packages/runtime-core/src/vgo_runtime/stage_machine.py` similar to:

```python
def iter_between(self, start: str, stop: str | None = None) -> tuple[str, ...]:
    start_index = self.index_of(start)
    stop_index = self.index_of(stop) if stop else len(self.stages) - 1
    if stop_index < start_index:
        raise ValueError("requested stop stage cannot precede start stage")
    return self.stages[start_index : stop_index + 1]
```

- [ ] **Step 3: Keep router-selected shortcuts distinct from runtime authority**

Update `packages/runtime-core/src/vgo_runtime/router.py` so:

- `requested_skill` may be `vibe`, `vibe-want`, `vibe-how`, or `vibe-do`
- `runtime_selected_skill` always resolves to `vibe`
- invalid shortcut ids fail closed

Expected shape:

```python
ALLOWED_VIBE_ENTRY_IDS = {"vibe", "vibe-want", "vibe-how", "vibe-do"}
selected_skill = str(requested_skill or "vibe").strip() or "vibe"
if selected_skill not in ALLOWED_VIBE_ENTRY_IDS:
    raise ValueError(f"unsupported vibe entry id: {selected_skill}")
```

- [ ] **Step 4: Carry requested grade floor into the planning model**

Extend `packages/runtime-core/src/vgo_runtime/planning.py` so `RuntimeExecutionPlan` includes:

```python
requested_grade_floor: str | None
requested_stage_stop: str | None
```

Then clamp automatic grade selection upward when a floor is requested:

```python
AUTO_ORDER = {"M": 0, "L": 1, "XL": 2}
selected = choose_internal_grade(task_type)
if requested_grade_floor and AUTO_ORDER[selected] < AUTO_ORDER[requested_grade_floor]:
    selected = requested_grade_floor
```

- [ ] **Step 5: Update execution to honor `requested_stage_stop`**

Modify `packages/runtime-core/src/vgo_runtime/execution.py` so stage iteration uses `iter_between(packet.stage, packet.requested_stage_stop)`.

Also ensure the result packet preserves:

- `entry_intent_id`
- `requested_stage_stop`
- `requested_grade_floor`

inside `final_packet`, `route`, or `plan` where appropriate for later assertions.

- [ ] **Step 6: Run the targeted runtime-core tests**

Run:

```bash
pytest tests/contract/test_runtime_packet_contract.py tests/integration/test_runtime_packet_execution.py -q
```

Expected: PASS with new coverage for stage-stop and grade-floor behavior.

- [ ] **Step 7: Commit the Python runtime-core implementation**

```bash
git add packages/contracts/src/vgo_contracts/runtime_packet.py packages/runtime-core/src/vgo_runtime/stage_machine.py packages/runtime-core/src/vgo_runtime/router.py packages/runtime-core/src/vgo_runtime/planning.py packages/runtime-core/src/vgo_runtime/execution.py tests/contract/test_runtime_packet_contract.py tests/integration/test_runtime_packet_execution.py
git commit -m "feat: support discoverable vibe stage-stop packets"
```

### Task 4: Extend PowerShell governed runtime input freezing and validation

**Files:**
- Modify: `scripts/runtime/Freeze-RuntimeInputPacket.ps1`
- Modify: `scripts/runtime/invoke-vibe-runtime.ps1`
- Modify: `scripts/runtime/VibeRuntime.Common.ps1`
- Modify: `scripts/runtime/Write-RequirementDoc.ps1`
- Modify: `scripts/runtime/Write-XlPlan.ps1`
- Modify: `tests/runtime_neutral/test_governed_runtime_bridge.py`
- Modify: `tests/runtime_neutral/test_l_xl_native_execution_topology.py`

- [ ] **Step 1: Add explicit parameters for shortcut id and grade-floor override**

Extend the PowerShell entry surfaces with parameters such as:

```powershell
[AllowEmptyString()] [string]$EntryIntentId = '',
[AllowEmptyString()] [string]$RequestedStageStop = '',
[AllowEmptyString()] [string]$RequestedGradeFloor = ''
```

Do this in both:

- `scripts/runtime/invoke-vibe-runtime.ps1`
- `scripts/runtime/Freeze-RuntimeInputPacket.ps1`

- [ ] **Step 2: Centralize shortcut validation in `VibeRuntime.Common.ps1`**

Add helpers shaped like:

```powershell
function Get-VibeEntrySurfacePolicy { ... }
function Resolve-VibeEntryIntent { ... }
function Assert-VibeGradeFloor { ... }
```

These helpers should:

- load `config/vibe-entry-surfaces.json`
- verify one approved entry id only
- reject invalid grade floors
- reject grade flags for `vibe-want`
- default plain invocations to canonical `vibe`

- [ ] **Step 3: Freeze the resolved metadata into the runtime input packet**

Ensure the runtime packet JSON emitted by `Freeze-RuntimeInputPacket.ps1` contains:

```json
{
  "entry_intent_id": "vibe-how",
  "requested_stage_stop": "xl_plan",
  "requested_grade_floor": "XL"
}
```

when applicable, and preserves current output when the user invokes plain `vibe`.

- [ ] **Step 4: Surface the shortcut intent inside requirement and plan artifacts**

Update `scripts/runtime/Write-RequirementDoc.ps1` and `scripts/runtime/Write-XlPlan.ps1` so frozen docs include a small metadata section such as:

```markdown
- Entry intent: `vibe-how`
- Requested stop stage: `xl_plan`
- Requested grade floor: `XL`
```

This keeps later execution and review grounded in the same frozen public-entry intent.

- [ ] **Step 5: Add or update runtime-neutral integration assertions**

Extend `tests/runtime_neutral/test_governed_runtime_bridge.py` and `tests/runtime_neutral/test_l_xl_native_execution_topology.py` to verify:

- the PowerShell runtime still produces the same six-stage order when no stop target is supplied
- `vibe-how` writes requirement and plan artifacts but does not execute `plan_execute`
- grade-floor requests are reflected in the execution manifest or plan receipt

- [ ] **Step 6: Run the targeted PowerShell/runtime-neutral tests**

Run:

```bash
pytest tests/runtime_neutral/test_governed_runtime_bridge.py tests/runtime_neutral/test_l_xl_native_execution_topology.py -q
```

Expected: PASS, or `Skip` only where PowerShell is unavailable.

- [ ] **Step 7: Commit the PowerShell runtime packet work**

```bash
git add scripts/runtime/Freeze-RuntimeInputPacket.ps1 scripts/runtime/invoke-vibe-runtime.ps1 scripts/runtime/VibeRuntime.Common.ps1 scripts/runtime/Write-RequirementDoc.ps1 scripts/runtime/Write-XlPlan.ps1 tests/runtime_neutral/test_governed_runtime_bridge.py tests/runtime_neutral/test_l_xl_native_execution_topology.py
git commit -m "feat: freeze vibe shortcut intent into governed runtime"
```

## Chunk 3: Host Discoverability And CLI Surfaces

### Task 5: Add host-facing discoverability metadata without duplicating runtime authority

**Files:**
- Modify: `adapters/index.json`
- Modify: `adapters/codex/host-profile.json`
- Modify: `adapters/claude-code/host-profile.json`
- Modify: `adapters/cursor/host-profile.json`
- Modify: `adapters/windsurf/host-profile.json`
- Modify: `adapters/openclaw/host-profile.json`
- Modify: `adapters/opencode/host-profile.json`
- Modify: `config/distribution-manifest-sources.json`
- Modify: `tests/contract/test_adapter_descriptor_contract.py`
- Modify: `tests/integration/test_dist_manifest_surface_roles.py`
- Modify: `tests/unit/test_adapter_registry_support.py`

- [ ] **Step 1: Point the adapter registry at the shared entry-surface metadata**

Add a registry-level field in `adapters/index.json` such as:

```json
"discoverable_entry_surface": "config/vibe-entry-surfaces.json"
```

so adapters consume one source of truth.

- [ ] **Step 2: Add per-host presentation metadata, not per-host authority**

For each `adapters/*/host-profile.json`, add a bounded section like:

```json
"discoverable_entries": {
  "shared_source": "config/vibe-entry-surfaces.json",
  "host_native_menu_expected": true,
  "authority_owner": "vibe",
  "notes": "These entries are presentational host launch surfaces only."
}
```

If a host cannot yet render all four entries natively, use honest host-specific capability notes rather than silently inventing extra aliases.

- [ ] **Step 3: Update distribution-manifest truth surfaces**

Adjust `config/distribution-manifest-sources.json` so release-facing manifest summaries remain honest:

- repo-provided entrypoints remain canonical
- discoverable shortcut labels are presentation metadata
- no manifest claims that discoverability equals multiple runtime authorities

- [ ] **Step 4: Extend adapter and distribution contract tests**

Add assertions equivalent to:

```python
assert descriptor["discoverable_entries"]["authority_owner"] == "vibe"
assert descriptor["discoverable_entries"]["shared_source"] == "config/vibe-entry-surfaces.json"
```

and:

```python
assert "discoverable intent entries are presentational" in notes.lower()
```

- [ ] **Step 5: Run the adapter/distribution verification set**

Run:

```bash
pytest tests/contract/test_adapter_descriptor_contract.py tests/unit/test_adapter_registry_support.py tests/integration/test_dist_manifest_surface_roles.py -q
```

Expected: PASS with explicit protection against per-host authority drift.

- [ ] **Step 6: Commit the host discoverability metadata**

```bash
git add adapters/index.json adapters/codex/host-profile.json adapters/claude-code/host-profile.json adapters/cursor/host-profile.json adapters/windsurf/host-profile.json adapters/openclaw/host-profile.json adapters/opencode/host-profile.json config/distribution-manifest-sources.json tests/contract/test_adapter_descriptor_contract.py tests/unit/test_adapter_registry_support.py tests/integration/test_dist_manifest_surface_roles.py
git commit -m "feat: expose discoverable vibe entries through adapter metadata"
```

### Task 6: Extend CLI/runtime helper surfaces for shortcut ids and grade flags

**Files:**
- Modify: `apps/vgo-cli/src/vgo_cli/commands.py`
- Modify: `apps/vgo-cli/src/vgo_cli/output.py`
- Modify: `apps/vgo-cli/src/vgo_cli/skill_surface.py`
- Modify: `tests/unit/test_vgo_cli_commands.py`
- Modify: `tests/runtime_neutral/test_runtime_entrypoint_helper.py`
- Modify: `tests/integration/test_cli_runtime_entrypoint_contract_cutover.py`

- [ ] **Step 1: Thread shortcut id and grade-floor options through the CLI bridge**

Extend the CLI argument handling so runtime passthrough can forward options like:

```text
--entry-intent-id vibe-how
--requested-grade-floor XL
```

Do not introduce `vibe-l` or `vibe-xl` as CLI entrypoints.

- [ ] **Step 2: Keep user-facing output honest about authority**

If `apps/vgo-cli/src/vgo_cli/output.py` prints runtime hints, update the wording so it can explain:

- selected discoverable entry label
- canonical runtime owner remains `vibe`
- grade floor is a preference, not a new runtime

- [ ] **Step 3: Keep installed skill surface hygiene intact**

If `apps/vgo-cli/src/vgo_cli/skill_surface.py` needs to recognize the discoverable-entry metadata for host rendering or duplicate-surface warnings, keep that logic metadata-based. Do not allow it to materialize extra `skills/vibe-*` directories as the default implementation.

- [ ] **Step 4: Strengthen CLI tests**

Extend `tests/unit/test_vgo_cli_commands.py` so the recorded argv includes the new passthrough parameters when supplied:

```python
assert recorded["argv"] == [
    "--prompt", "route this",
    "--grade", "XL",
    "--task-type", "debug",
    "--requested-skill", "vibe-how",
    "--requested-grade-floor", "XL",
]
```

Update runtime-entrypoint helper tests only if helper behavior changes because of new runtime config keys.

- [ ] **Step 5: Run the targeted CLI test suite**

Run:

```bash
pytest tests/unit/test_vgo_cli_commands.py tests/runtime_neutral/test_runtime_entrypoint_helper.py tests/integration/test_cli_runtime_entrypoint_contract_cutover.py -q
```

Expected: PASS with no regression to the canonical runtime entrypoint ownership.

- [ ] **Step 6: Commit the CLI bridge updates**

```bash
git add apps/vgo-cli/src/vgo_cli/commands.py apps/vgo-cli/src/vgo_cli/output.py apps/vgo-cli/src/vgo_cli/skill_surface.py tests/unit/test_vgo_cli_commands.py tests/runtime_neutral/test_runtime_entrypoint_helper.py tests/integration/test_cli_runtime_entrypoint_contract_cutover.py
git commit -m "feat: add vibe shortcut and grade-floor cli plumbing"
```

## Chunk 4: Docs, Guardrails, And Final Verification

### Task 7: Update user-facing docs to explain discoverable entries and `--l` / `--xl`

**Files:**
- Modify: `README.md`
- Modify: `README.zh.md`
- Modify: `SKILL.md`
- Modify: `docs/quick-start.md`
- Modify: `docs/quick-start.en.md`
- Modify: `tests/runtime_neutral/test_docs_readme_encoding.py`

- [ ] **Step 1: Update the public runtime description in `README` and `SKILL.md`**

Add wording that:

- canonical governed runtime authority remains `vibe`
- hosts may expose discoverable labels for `What Do I Want?`, `How Do We Do It?`, and `Do It`
- `--l` and `--xl` are the only public execution overrides
- those overrides do not skip requirement or plan stages

- [ ] **Step 2: Update both quick-start docs for discoverability-first usage**

Add a short section that explains the new user-facing choice model:

```markdown
- `Vibe`: default governed entry
- `Vibe: What Do I Want?`: clarify intent first
- `Vibe: How Do We Do It?`: freeze requirement and plan
- `Vibe: Do It`: run the full governed flow
- `--l` / `--xl`: request heavier execution only
```

- [ ] **Step 3: Keep the docs explicit about what is not allowed**

Make the docs say directly that the system does not support:

- `vibe-l`
- `vibe-xl`
- `vibe-how-xl`
- stage skipping through public aliases

- [ ] **Step 4: Run doc sanity tests**

Run:

```bash
pytest tests/runtime_neutral/test_docs_readme_encoding.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit the docs update**

```bash
git add README.md README.zh.md SKILL.md docs/quick-start.md docs/quick-start.en.md tests/runtime_neutral/test_docs_readme_encoding.py
git commit -m "docs: explain discoverable vibe entries and grade flags"
```

### Task 8: Run full targeted verification and review for authority regressions

**Files:**
- Review: `docs/superpowers/specs/2026-04-08-vibe-discoverable-intent-entry-design.md`
- Review: `docs/superpowers/plans/2026-04-08-vibe-discoverable-intent-entry.md`
- Review: all files changed in Tasks 1-7

- [ ] **Step 1: Run the consolidated targeted test suite**

Run:

```bash
pytest tests/contract/test_vibe_discoverable_entry_contract.py tests/contract/test_runtime_packet_contract.py tests/integration/test_runtime_packet_execution.py tests/integration/test_runtime_config_manifest_roles.py tests/integration/test_version_governance_runtime_roles.py tests/integration/test_dist_manifest_surface_roles.py tests/unit/test_runtime_surface_contract.py tests/unit/test_vgo_cli_commands.py tests/runtime_neutral/test_governed_runtime_bridge.py tests/runtime_neutral/test_l_xl_native_execution_topology.py tests/runtime_neutral/test_runtime_entrypoint_helper.py tests/runtime_neutral/test_docs_readme_encoding.py -q
```

Expected: all targeted tests PASS, with PowerShell-backed suites allowed to `Skip` only when the shell is unavailable.

- [ ] **Step 2: Run ripgrep guardrails against forbidden alias growth**

Run:

```bash
rg -n "vibe-(m|l|xl)|vibe-(want|how|do)-(l|xl)|stage x grade|second runtime authority" README* SKILL.md docs config apps tests
```

Expected: no positive implementation surfaces for forbidden aliases; matches should only appear in negative examples, specs, or tests that explicitly forbid them.

- [ ] **Step 3: Review the diff for contract drift**

Run:

```bash
git diff --stat
git diff -- config apps/vgo-cli packages/contracts packages/runtime-core scripts/runtime adapters README.md README.zh.md SKILL.md docs/quick-start.md docs/quick-start.en.md tests
```

Confirm that the diff:

- preserves canonical runtime authority as `vibe`
- does not add new installed skill roots by default
- does not permit `vibe-do` to skip `requirement_doc` or `xl_plan`
- does not treat `--l` or `--xl` as new runtime modes

- [ ] **Step 4: Commit the verified final implementation**

```bash
git add config apps/vgo-cli packages/contracts packages/runtime-core scripts/runtime adapters README.md README.zh.md SKILL.md docs/quick-start.md docs/quick-start.en.md tests
git commit -m "feat: add discoverable vibe intent entries"
```

- [ ] **Step 5: Prepare the execution close-out**

The final execution summary should state:

- which shared config and contract files were introduced or changed
- which runtime packet fields were added
- how stop-stage and grade-floor behavior works
- which host discoverability surfaces were updated
- which verification commands passed

