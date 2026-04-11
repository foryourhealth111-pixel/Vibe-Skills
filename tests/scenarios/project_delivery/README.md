# Project Delivery Scenarios

This directory contains downstream project-delivery scenarios for work completed under `vibe`.

These fixtures do not ask only whether runtime governance behaved correctly.
They ask whether the delivered project state is strong enough to justify completion language.

## Scenario Contract

Each scenario should define:

- `scenario_id`
- `task_class`
- `runtime`
- `truths`
- `manual_spot_checks`
- `residual_risks`

## Truth Layers

Each scenario must provide five truth-layer states:

- `governance_truth`
- `engineering_verification_truth`
- `workflow_completion_truth`
- `artifact_review_truth`
- `product_acceptance_truth`

## Purpose

Use these scenarios to prove:

- a governed run can still fail downstream delivery
- partial execution cannot be over-reported as full project success
- manual review requirements remain explicit
- product acceptance is a first-class proof surface
