# Anti-Proxy-Goal-Drift Tier A Pilot Decision

Date: 2026-03-17
Mode: report-only pilot

## Decision

Recommendation: `continue_report_only`

Tier A is **not** yet eligible for hard enforcement.

## Evidence Summary

- Red-team fixture count: `4`
- Red-team caught: `4`
- Red-team recall: `1.0`
- Legitimate specialization fixture count: `2`
- Specialization false positives: `0`
- Specialization false-positive rate: `0.0`
- Tier gold fixture count: `5`
- Tier agreement: `5`
- Tier agreement rate: `1.0`
- Human usability evidence present: `false`

## Interpretation

The current anti-drift implementation is strong enough to support report-only governance:

- it deterministically catches the red-team corpus,
- it does not falsely escalate the legitimate specialization corpus,
- it classifies the tier-gold corpus consistently.

However, hard enforcement would still be dishonest at this point because the rollout does not yet include real operator burden data or human reviewer usability evidence.

## Resulting Policy Stance

- Keep anti-proxy-goal-drift checker mode as `report_only`.
- Keep Tier A as the only future candidate for first hard enforcement.
- Do not expand hard enforcement to Tier B or Tier C.
- Collect human usability evidence before revisiting enforcement.

## Required Next Evidence

Before Tier A hard enforcement is reconsidered, collect:

- packet author preparation time,
- reviewer clarification count,
- reclassification rate,
- evidence that the new fields reduce false completion in live use rather than only in fixtures.
