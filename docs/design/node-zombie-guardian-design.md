# Node Zombie Guardian Design

## Purpose

Node Zombie Guardian adds a safe, VCO-native process-health capability for Node workloads that overstay, lose ownership, or continue consuming memory after their intended task has ended.

The design follows the agreed `B + C` strategy:

1. `B`: a VCO-owned process ledger with heartbeat-based liveness tracking.
2. `C`: a unified Node launch wrapper so VCO-managed Node processes are explicitly registered at launch.

This capability is designed to solve the practical problem the user described:

- long-running Node processes accumulate
- memory usage grows until the machine becomes unstable
- operators need a bounded way to distinguish VCO-owned stale processes from legitimate application runtimes

## Non-goal

This capability does **not** attempt to kill arbitrary system Node processes.

On Windows, most so-called "zombie node" cases are not OS-level zombie processes. They are usually one of:

- orphaned Node runtimes after the launcher exited
- stale dev servers with no active owner
- detached background processes that no longer belong to the current workflow
- repeated duplicate launches of the same service

The system therefore uses the term **zombie candidate**, not POSIX zombie.

## Safety Model

The core invariant is:

**Only VCO-managed Node processes can become cleanup-safe targets.**

Every observed Node process is classified into one of these ownership buckets:

| Ownership | Meaning | Cleanup |
| --- | --- | --- |
| `vco-managed` | launched through the VCO wrapper and recorded in the ledger | may be cleanup-safe if stale/orphaned |
| `external` | running Node process with no VCO ledger ownership | audit only |
| `unknown` | malformed or insufficient evidence | audit only |

Every `external` or `unknown` process is protected from automatic termination.

## Lifecycle

### 1. Launch

`NodeLaunchWrapper.ps1` launches the requested command, discovers the actual Node runtime PID, and registers a ledger entry with:

- stable `entry_id`
- target PID
- launcher PID
- label
- working directory
- command line
- ownership = `vco-managed`
- heartbeat path
- cleanup-safe eligibility flag

### 2. Heartbeat

The wrapper spawns a lightweight PowerShell monitor that:

- updates `last_heartbeat_at`
- records phase / note
- refreshes `last_seen_alive_at`
- marks the entry completed when the process exits

### 3. Audit

`Invoke-NodeProcessAudit.ps1` compares live Node processes against the ledger and produces a deterministic classification:

- `managed_live`
- `managed_missing_heartbeat`
- `managed_stale`
- `managed_completed_process_alive`
- `external_audit_only`
- `unknown_audit_only`

### 4. Cleanup

`Invoke-NodeZombieCleanup.ps1` consumes audit results and only targets rows that are simultaneously:

- `ownership = vco-managed`
- `cleanup_safe = true`
- in a policy-approved stale/orphan state

Cleanup defaults to report-only and must be explicitly switched to apply mode.

## Detection Rules

The system uses bounded, explainable rules instead of opaque heuristics.

### Managed stale

A managed process is stale when:

- the target PID still exists
- the ledger says it should still be running
- heartbeat age exceeds `stale_heartbeat_sec`
- the process is outside startup grace

### Managed completed but alive

A managed process is orphaned after completion when:

- the ledger status is completed / terminated
- but the PID still exists

### External audit only

A live Node process is external when:

- it matches the Node process-name policy
- but no active ledger entry claims that PID

This state is intentionally non-destructive.

## Why This Avoids False Positives

The design reduces false positives by requiring all of the following before cleanup:

1. explicit launch registration through the wrapper
2. positive ledger ownership
3. heartbeat-based stale evidence
4. policy-approved cleanup state
5. cleanup-safe flag on the entry

Any Node process that fails one of those checks becomes audit-only.

## Data Contracts

### Process ledger

Canonical store:

- `outputs/runtime/process-health/process-ledger.json`
- `outputs/runtime/process-health/process-ledger.events.jsonl`

Each entry records:

- identity: `entry_id`, `label`, `owner_id`
- runtime: `pid`, `launcher_pid`, `working_directory`, `command_line`
- lifecycle: `status`, `started_at`, `closed_at`
- liveness: `last_heartbeat_at`, `last_seen_alive_at`, `heartbeat_path`
- safety: `ownership`, `cleanup_safe`, `stale_after_sec`

### Audit artifact

Canonical store:

- `outputs/runtime/process-health/audits/*.json`
- optional markdown summary alongside JSON

Audit artifacts provide:

- classified process list
- reasons for each decision
- memory footprint summary
- cleanup-safe candidate list

### Cleanup artifact

Canonical store:

- `outputs/runtime/process-health/cleanups/*.json`

Cleanup artifacts provide:

- dry-run vs apply mode
- targeted PIDs
- skipped PIDs and why
- termination result

## Governance Boundaries

Node Zombie Guardian is a governance-side helper, not a second orchestrator.

It may:

- launch and register VCO-owned Node runtimes
- audit process health
- terminate VCO-owned stale processes when explicitly allowed

It may not:

- override VCO routing
- claim ownership of external processes
- become a background runtime manager for all Node software on the machine
- silently kill unknown or non-VCO Node processes

## Routing Integration

The capability is integrated through the existing pack router, not through a new control plane.

Required route signals include:

- `zombie node`
- `orphan node`
- `node memory leak`
- `stale node process`
- `cleanup stale node`
- Chinese equivalents such as `node僵尸进程`, `孤儿node进程`, `node内存拉爆`

The expected selected skill is `node-zombie-guardian`, primarily under debug-oriented routing.

## Verification Strategy

The implementation must prove three things:

1. **Stability**: classification is deterministic on fixtures and does not mutate unrelated state.
2. **Usability**: report-only audit produces immediately actionable output.
3. **Safety**: cleanup never targets `external` or `unknown` processes.

Verification artifacts include:

- config parity
- mirror parity
- routing metadata
- skill metadata
- a dedicated `vibe-node-zombie-gate.ps1`

## Rollout Posture

The capability ships in conservative mode:

- wrapper available immediately
- audit enabled immediately
- cleanup defaults to dry-run / report-only
- external process handling remains advisory-only

This keeps the operational value high while preserving a hard safety boundary.
