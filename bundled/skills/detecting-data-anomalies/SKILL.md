---
name: detecting-data-anomalies
description: |
  Investigate outliers, rare events, spikes, and suspicious records in datasets.
  Use as an explicit anomaly-analysis helper when you want concrete anomaly-detection workflow guidance, not generic data validation or end-to-end ML ownership.
allowed-tools: Read, Bash(python:*), Grep, Glob
version: 1.0.0
author: Jeremy Longshore <jeremy@intentsolutions.io>
license: MIT
---

# Detecting Data Anomalies

## Positioning

Treat this skill as an explicit/manual helper.
In governed ML routing, anomaly-detection ownership normally belongs to `scikit-learn`.

## When to Use

Use this skill when:
- Reviewing outlier transactions, fraud candidates, sensor spikes, or rare failures
- Comparing isolation forest, one-class SVM, LOF, or threshold-based anomaly workflows
- Turning suspicious records into a shortlist for human inspection

## Not For / Boundaries

- Null/duplicate/schema/range validation: use `exploratory-data-analysis`
- Full model training or end-to-end pipeline ownership: use `training-machine-learning-models`
- Publication-grade figure production: use `scientific-visualization`

## Typical Outputs

- Candidate anomaly-detection methods and thresholds
- A review checklist for false positives and false negatives
- Suggested tables or plots for the suspicious subset

## Related Skills

- `scikit-learn` as the governed routed owner for classical anomaly-detection workflows
- `creating-data-visualizations` after anomalies are identified
