---
name: creating-data-visualizations
description: |
  Create analytical charts and plots from existing data.
  Use for exploratory or reporting visuals such as bars, lines, scatters, and dashboards; not for publication-grade scientific figures or AI-generated schematics.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(cmd:*)
version: 1.0.0
author: Jeremy Longshore <jeremy@intentsolutions.io>
license: MIT
---
# Data Visualization Creator

Use this skill when the user needs a chart from data that already exists.

## Overview

This skill focuses on everyday analytical visualization choices: bars, lines, scatters, distributions, comparisons, and simple dashboards.

## When to Use This Skill

- Plotting trends, distributions, comparisons, or correlations from structured data
- Turning query output or CSV tables into charts for analysis or slides
- Choosing a sensible chart type and axis treatment for a non-specialist audience

## Not For / Boundaries

- Journal-ready figures, multi-panel publication layouts, TIFF/600dpi exports: use `scientific-visualization`
- Structural diagrams, flowcharts, and mechanism illustrations: use `scientific-schematics` or `markdown-mermaid-writing`
- Full research-report ownership: use `scientific-reporting`

## Integration

- Pair with `exploratory-data-analysis` before plotting questionable data
- Hand off to `scientific-visualization` if the chart must meet publication standards

## Example Requests

- "Plot monthly conversion rate with a confidence band"
- "Make a scatter plot of latency vs throughput"
- "Turn this CSV summary into a small dashboard"
