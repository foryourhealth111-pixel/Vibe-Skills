---
name: engineering-features-for-machine-learning
description: |
  Create, encode, transform, and select features before model fitting.
  Use when the user needs feature engineering decisions or implementation, not final training ownership or leakage auditing.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(cmd:*)
version: 1.0.0
author: Jeremy Longshore <jeremy@intentsolutions.io>
license: MIT
---
# Feature Engineering Toolkit

Use this skill when the main question is how to improve or restructure the input features.

## Overview

This skill covers feature creation, encoding, scaling coordination, and feature selection before the model is finalized.

## When to Use This Skill

- Creating derived variables, interaction terms, bins, encodings, or date-based features
- Selecting or pruning features before training
- Reworking feature representations to fit model assumptions or data geometry

## Not For / Boundaries

- Full training runs and benchmark ownership: use `training-machine-learning-models`
- Post-hoc interpretation of a trained model: use `shap`
- Leak checking across the preprocessing order: use `ml-data-leakage-guard`

## Typical Outputs

- Candidate feature set changes
- Implementation notes for encoders, scalers, and selectors
- Rationale for what to keep, drop, or combine

## Related Skills

- `preprocessing-data-with-automated-pipelines` for scaling-only questions
- `ml-data-leakage-guard` before accepting the engineered pipeline
