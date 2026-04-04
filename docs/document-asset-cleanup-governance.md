# VCO Document Asset Cleanup Governance

## Purpose

Document assets are not ordinary temporary files.
Any cleanup surface that can touch `.docx`, `.xlsx`, `.pptx`, or `.pdf` must treat them as a protected plane.

## Core Rule

For protected document assets, the safe default is:

1. snapshot first
2. preview second
3. quarantine before destroy
4. verify presence after cleanup
5. write receipts

## Protected Extensions

- `.docx`
- `.xlsx`
- `.pptx`
- `.pdf`

## Required Cleanup Modes

- `receipt_only`
- `preview_only`
- `quarantine_only`
- `bounded_cleanup_executed`
- `destructive_cleanup_applied`
- `cleanup_degraded`

## Mandatory Safety Constraints

### 1. No Fuzzy Destructive Cleanup

Protected documents must not be destructively targeted by name fragments, wildcard assumptions, or ambiguous grouping logic.

### 2. Preview Before Stronger Action

If a cleanup action could touch protected documents, the system must be able to emit a preview manifest that shows exactly which assets were considered, and the cleanup policy contract must declare that preview capability explicitly.

### 3. Quarantine Before Destruction

If protected documents appear inside a temporary cleanup root, the cleanup path must prefer quarantine over destruction unless a stronger path is explicitly approved and proven.

### 4. Post-Cleanup Presence Checks

After cleanup, the system must verify:

- protected assets outside the tmp root still exist,
- quarantined protected assets still exist in quarantine,
- cleanup receipts preserve the evidence trail.

## Current Boundaries

This governance surface does not claim that all document workflows across the whole ecosystem are already safe.
It claims only that the canonical phase-end cleanup path now has a protected-plane contract and proof obligations.

## Verification Contract

The document cleanup remediation is not complete until:

- the policy contract exists,
- the cleanup implementation reflects the contract,
- fixtures cover high-similarity file sets including Chinese names,
- the document safety gate passes,
- release wording remains weaker than unproven human-evidence claims.
