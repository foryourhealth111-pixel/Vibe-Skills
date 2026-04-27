---
name: evaluating-machine-learning-models
description: |
  Evaluate trained machine learning models with the right metrics and comparison logic.
  Use for benchmark review, threshold selection, calibration, validation, and model comparison; not for feature engineering or leakage auditing.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(cmd:*)
version: 1.0.0
author: Jeremy Longshore <jeremy@intentsolutions.io>
license: MIT
---
# Model Evaluation Suite

Use this skill when the model exists and the question is whether it is good enough.

## Overview

This skill focuses on choosing and interpreting the right evaluation metrics for the problem, then comparing candidate models or thresholds.

## When to Use This Skill

- Comparing candidate models with consistent metrics
- Reviewing precision/recall/F1/AUC, regression error, calibration, or ranking quality
- Stress-testing validation strategy before deployment or publication

## Not For / Boundaries

- Building the training pipeline itself: use `training-machine-learning-models`
- Engineering features: use `engineering-features-for-machine-learning`
- Checking train/test contamination: use `ml-data-leakage-guard`

## Typical Outputs

- Metric suite recommendations
- Model comparison tables
- Notes on threshold tradeoffs, calibration, and validation weaknesses

## Related Skills

- `scikit-learn` for class-level error breakdowns and confusion matrices
- `scientific-reporting` when the evaluation must become a deliverable
