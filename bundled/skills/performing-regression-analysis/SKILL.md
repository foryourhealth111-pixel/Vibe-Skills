---
name: performing-regression-analysis
description: |
  Build and diagnose regression models when the main question is regression itself.
  Use for model specification, coefficient interpretation, residual checks, and fit diagnostics; not for causal identification, generic feature screening, or report packaging.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(cmd:*)
version: 1.0.0
author: Jeremy Longshore <jeremy@intentsolutions.io>
license: MIT
---
# Regression Analysis Tool

## Purpose

Use this skill when regression is the task owner, not just one small step inside a bigger workflow.

## When to Use

Use this skill when:
- Fitting and diagnosing a regression model on a given dataset
- Predicting future values from existing data with regression models
- Interpreting relationships between independent and dependent variables through model coefficients
- Evaluating regression-model residuals, assumptions, and fit quality

## Not For / Boundaries

- Causal identification or policy-effect claims: use `performing-causal-analysis`
- Pairwise screening before modeling: use `exploratory-data-analysis`
- Inline regression help inside a broader ML workflow: use `scikit-learn`
- Final deliverable writing and packaging: use `scientific-reporting`

## Typical Outputs

- Model specification options and assumptions checklist
- Coefficient, residual, and fit interpretation notes
- Next-step recommendations for validation or reporting

## Related Skills

- `exploratory-data-analysis` for pre-model screening
- `scikit-learn` for lightweight inline support inside a larger ML workflow
- `scientific-reporting` when the regression needs to become a deliverable report
