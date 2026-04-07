# Install Prompt MCP Auto-Provision Design

## Summary
Define a new installation-assistant contract where the AI must attempt to provision five MCP surfaces during installation guidance across all six publicly supported hosts. The design does not turn those MCPs into hard install blockers. Instead, it standardizes a best-effort but mandatory attempt flow, reuses repository-owned install/bootstrap/check paths first, prefers host-native registration for host-native MCP/plugin surfaces, and reports failures only in the final install report.

The five MCP surfaces in scope are:

- `github`
- `context7`
- `serena`
- `scrapling`
- `claude-flow`

The six public hosts in scope are:

- `codex`
- `claude-code`
- `cursor`
- `windsurf`
- `openclaw`
- `opencode`

## Problem
The current installation story separates three things, but not consistently:

- repository-owned payload installation
- host-specific MCP or plugin provisioning
- final readiness reporting

That creates two user-facing problems:

1. install assistants may stop after payload installation and never attempt to provision high-value MCP surfaces
2. when MCP provisioning does happen, the result vocabulary is inconsistent across prompt docs, one-shot/bootstrap flows, doctor gates, and final reports

The user wants a stronger and more honest experience:

- every install assistant should try to provision the same five MCP surfaces
- the attempt should happen during installation guidance, not as an unrelated later suggestion
- failure should not block users from beginning to use VibeSkills
- failure should still be explicit and auditable in the final report

## Goals
- Make MCP auto-provision attempts part of the install-assistant contract.
- Cover the same five MCP surfaces across all six public hosts.
- Reuse repository-owned install/bootstrap/check flows before improvising host-specific actions.
- Prefer host-native registration for `github`, `context7`, and `serena`.
- Prefer CLI / stdio provisioning for `scrapling` and `claude-flow`.
- Standardize verification and reporting so all install surfaces use the same state vocabulary.
- Keep base install success separate from MCP readiness and from online governance readiness.

## Non-Goals
- Do not make any of the five MCP surfaces a hard prerequisite for base installation success.
- Do not redefine host support to mean “full parity across all hosts”.
- Do not require users to paste secrets or provider credentials into chat.
- Do not silently claim that a host-native MCP is ready without host-visible verification.
- Do not redesign unrelated router, runtime, or memory policies.

## Scope Boundary
This design applies to:

- install prompt documents
- install / one-shot / check orchestration
- host-specific MCP provision attempts
- doctor / verification artifacts
- final install reporting

This design does not apply to:

- unrelated runtime task execution after install
- online governance credential configuration beyond reporting readiness gaps
- non-public hosts

## Design Options Considered

### Option A: Prompt-only soft reminder
Add a single instruction to install prompts telling the assistant to try the five MCPs.

Pros:

- lowest implementation cost
- minimal document churn

Cons:

- weak execution consistency
- no shared verification contract
- likely drift between prompts and scripts

### Option B: Prompt + unified provision state machine
Define a standard `detect -> attempt_provision -> verify -> final_report` lifecycle shared by install prompts, bootstrap flows, and doctor/reporting layers.

Pros:

- consistent behavior across all hosts
- evidence-backed reporting
- clean separation between base install success and MCP readiness

Cons:

- requires touching prompts, scripts, and doctor outputs together

### Option C: Hard fail provisioning contract
Require all five MCPs to be provisioned successfully or mark installation as failed.

Pros:

- simple user story
- strongest pressure toward full automation

Cons:

- conflicts with the requirement to not block users from starting VibeSkills
- too brittle for hosts that still expose host-managed registration boundaries

## Decision
Choose **Option B** with host-specific executors.

The install assistant contract should become:

- mandatory attempt
- repository-owned path first
- host-native path preferred where relevant
- standardized verification
- final-report-only failure summary
- no install blockage from MCP attempt failure

## Core Contract

### 1. Install Prompt Rule
Every supported install prompt must require the assistant to attempt provisioning:

- `github`
- `context7`
- `serena`
- `scrapling`
- `claude-flow`

The assistant must:

1. detect the host and target root
2. invoke repository-owned install/bootstrap/check flows first
3. attempt MCP provisioning using the host’s preferred path
4. verify discoverability or host visibility
5. summarize the outcome only in the final install report

### 2. No Mid-Flow Failure Spam
The assistant should not interrupt the user each time an MCP attempt fails.

Instead:

- continue the base install path
- record the failure in receipts
- include the failure in the final report

### 3. Truth Separation
The final install truth must separate:

- `installed_locally`
- `mcp_auto_provision_attempted`
- per-MCP readiness
- online governance readiness

This prevents the current ambiguity where successful payload installation can be confused with fully ready integrations.

## Cross-Host Provision Flow

### Shared Lifecycle
All hosts use the same lifecycle:

1. `detect`
2. `attempt_provision`
3. `verify`
4. `final_report`

### MCP Categories

#### Host-native preferred

- `github`
- `context7`
- `serena`

Primary path:

- host-native MCP / plugin registration if a stable, supported interface exists

Fallback behavior:

- record `host_native_unavailable` or `attempt_failed`
- continue installation

#### CLI / stdio preferred

- `scrapling`
- `claude-flow`

Primary path:

- repository-owned scripted CLI install
- verify command availability and host discoverability

Fallback behavior:

- record `attempt_failed` or `verification_failed`
- continue installation

### Host-Specific Attempt Order

#### `codex`

- repository bootstrap / check first
- host-native registration next for `github/context7/serena`
- scripted CLI install for `scrapling/claude-flow`

#### `claude-code`

- managed settings / scaffold first
- host-native plugin or MCP enablement next
- scripted CLI install where appropriate

#### `cursor`

- preview-guidance scaffold first
- host-native registration if documented and stable
- scripted CLI install where applicable

#### `windsurf`

- runtime-core + sidecar preparation first
- host-native registration if documented
- scripted CLI install where applicable

#### `openclaw`

- attach / copy / bundle flow first
- host-native registration if documented
- scripted CLI install where applicable

#### `opencode`

- direct install/check first
- host-native MCP/config registration next
- scripted CLI install where applicable without overstating ownership of host-managed config

## Unified State Model
Every MCP result should emit the same fields:

- `name`
- `category`
- `attempt_required`
- `attempted`
- `provision_path`
- `verify_path`
- `status`
- `failure_reason`
- `next_step`

### Allowed Status Values

- `ready`
- `attempt_failed`
- `host_native_unavailable`
- `missing_credentials`
- `verification_failed`
- `not_attempted_due_to_host_contract`

Rules:

- default expectation is `attempt_required=true`
- use `not_attempted_due_to_host_contract` only when a documented host contract forbids the action
- use `verification_failed` when a provision command succeeded but host discovery or readiness proof failed

## Final Report Format
The final install report should add a fixed section like:

```text
MCP Provision Summary
- github: status=attempt_failed; attempted=true; path=host_native_registration; reason=host plugin registration command unavailable; next_step=use the host-native registration path locally
- context7: status=host_native_unavailable; attempted=true; path=host_native_registration; reason=no stable host-native registration interface detected; next_step=provision via host-side documented path
- serena: status=ready; attempted=true; path=host_native_registration; verify=passed
- scrapling: status=ready; attempted=true; path=cli_stdio_install; verify=passed
- claude-flow: status=attempt_failed; attempted=true; path=cli_stdio_install; reason=npm install failed; next_step=retry local npm provisioning
```

And the top-level report should summarize:

- `installed_locally`
- `mcp_auto_provision_attempted`
- `mcp_ready_count`
- `mcp_failed_count`

## Surfaces To Change

### Prompt Documents
Update install prompt documents to require the five MCP attempts and final-report-only failure disclosure.

Likely surface:

- `docs/install/prompts/*`

### Execution Surfaces
Add or extend a unified MCP provision orchestrator that install, one-shot, and check flows can call.

Likely surfaces:

- `scripts/bootstrap/one-shot-setup.*`
- `install.*`
- `check.*`

### Verification / Doctor
Doctor and verification outputs should consume the same result model instead of using ad hoc wording.

Likely surfaces:

- `scripts/verify/vibe-bootstrap-doctor-gate.ps1`
- runtime-neutral verification helpers or a new MCP provision receipt writer

### Reporting
The final install report template should be updated to print the new MCP summary block in a deterministic format.

## Rollout Plan

### Phase 1: Contract First
Change prompts, reporting expectations, and status vocabulary.

Success criteria:

- the user-visible contract is stable
- all supported hosts enter the same MCP attempt flow on paper

### Phase 2: Unified Provision Orchestrator
Implement a runtime-neutral orchestrator for `detect -> attempt -> verify -> report`.

Success criteria:

- one shared receipt format
- reusable by install, bootstrap, and check

### Phase 3: Host Executors
Implement per-host attempt logic.

Success criteria:

- host-native preferred MCPs use host-native registration where possible
- CLI/stdio preferred MCPs use scripted install paths

### Phase 4: Deep Verification
Connect doctor/check/probe surfaces to the shared receipts.

Success criteria:

- prompts, execution, doctor, and final report agree on the same truth

## Risks And Controls

### Risk: Host capabilities differ too much
Control:

- keep the lifecycle uniform
- vary only executor behavior and final status

### Risk: The assistant claims it attempted provisioning without evidence
Control:

- final report must be generated from receipts, not free-form narration

### Risk: MCP failures get misreported as install failures
Control:

- separate `installed_locally` from MCP readiness in all report surfaces

### Risk: CLI installs are slow or flaky
Control:

- use timeouts and bounded retries
- record deterministic failure reasons

### Risk: Prompt docs drift away from script behavior
Control:

- update prompt docs, bootstrap flows, verification, and final report in the same change set

## Open Questions For Implementation Planning
- Should the shared MCP provision receipt be runtime-neutral JSON only, or JSON plus markdown summary?
- Which hosts already expose sufficiently stable native registration commands for `github/context7/serena`?
- Should `check --deep` be required to print the MCP summary block, or only write it to receipts?

## Recommended Next Step
Convert this design into an implementation plan that:

- enumerates prompt files to update
- defines the shared receipt schema
- maps per-host provision executors
- wires final reporting and verification to the shared state model
