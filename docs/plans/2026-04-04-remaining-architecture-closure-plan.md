# 2026-04-04 Remaining Architecture Closure Plan

## Goal

Execute the remaining architecture closure work in governed XL waves until the repository reaches a provable low-coupling, high-cohesion state with preserved behavior.

## Internal Grade

XL wave-sequential execution. Analysis may run in bounded parallel for independent audit lanes, but implementation and verification remain wave-ordered.

## Wave Structure

### Wave 1: Remaining Owner Audit

- inventory remaining script-text truth checks and duplicated semantic owners
- inventory compatibility shim boundaries and fallback surfaces
- inventory cross-layer contract inconsistencies
- rank remaining cuts by architectural value and blast radius

### Wave 2: High-Value Contract Cutovers

- execute the next highest-value microphase with narrow ownership boundaries
- prefer contract-backed consumption over local script-owned inventories
- add focused tests that freeze the new owner boundary

### Wave 3: Compatibility Boundary Closure

- demote shims to pure compatibility delegates where safe
- reduce fallback surfaces that still duplicate semantics
- keep live compatibility callers intact unless explicitly proven removable

### Wave 4: Architectural Consistency Audit

- verify owner -> consumer relationships across contracts, runtime-core, verification-core, CLI, governance, and packaging
- confirm residual fallbacks are bounded, documented, and intentional

### Wave 5: Final Proof and Cleanup

- run focused verification for the final cut
- run full regression suites
- run `git diff --check`
- clear temporary audit files and inspect zombie Node processes
- update architectural audit documents and residual-risk notes

## Execution Rules

- freeze a requirement doc and plan before each substantial microphase
- use bounded parallel analysis only for independent audit tasks
- preserve one canonical requirement / plan truth surface under root governance
- require focused verification before full regression on each cut
- do not claim completion without fresh evidence

## Phase Cleanup Rules

- remove temporary audit files created during the phase
- inspect and clean stale Node processes if they were spawned by the work
- leave behind only intentional docs, tests, and contract changes
