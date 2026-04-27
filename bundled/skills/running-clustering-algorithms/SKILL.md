---
name: running-clustering-algorithms
description: |
  Segment data with clustering algorithms such as K-means, DBSCAN, or hierarchical clustering.
  Use for unsupervised grouping and cluster diagnostics, not supervised classification or publication-figure ownership.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(cmd:*)
version: 1.0.0
author: Jeremy Longshore <jeremy@intentsolutions.io>
license: MIT
---
# Clustering Algorithm Runner

Use this skill when the main question is how to group unlabeled data points.

## Overview

This skill covers algorithm choice, preprocessing implications, cluster validation, and interpretation for unsupervised segmentation problems.

## When to Use This Skill

- Customer segmentation, cohort discovery, or grouping unlabeled records
- Choosing between centroid, density, or hierarchical clustering
- Reviewing silhouette score, Davies-Bouldin, or cluster stability

## Not For / Boundaries

- Supervised prediction with labels: use `training-machine-learning-models`
- Pure anomaly review without clustering as the central method: use `scikit-learn`
- Final narrative report packaging: use `scientific-reporting`

## Typical Outputs

- Algorithm recommendation with parameter guidance
- Cluster-assignment workflow
- Validation and interpretation notes for cluster quality

## Related Skills

- `creating-data-visualizations` for exploratory plots of cluster structure
- `scikit-learn` when outliers become the next question
