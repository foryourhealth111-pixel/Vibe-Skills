# Prompt Intelligence Governance

## Purpose

This document governs how Prompt-Engineering-Guide material is absorbed into VCO.
The design principle is simple: prompt intelligence should increase quality and safety, not widen the prompt surface or create a second router.

## Plane Boundary

- `prompts.chat` and `prompt-asset-boost` = asset retrieval / candidate suggestion
- Prompt-Engineering-Guide assets = pattern cards + risk checklist + quality checks
- VCO router = single control plane

## Non-Redundancy Rules

1. Do not mirror Prompt-Engineering-Guide as a second searchable prompt library.
2. Do not create a second prompt workflow surface.
3. Do not expand `prompt_overlay` trigger keywords aggressively.
4. Keep PEG-derived assets in `references/` and governance docs.

## Quality Check Surface

Prompt candidates may optionally expose advisory-only metadata:
- `pattern_cards_used[]`
- `risk_flags[]`
- `checklist_pass_rate`

These fields are for human-readable quality signaling only.
They must not replace `selected.pack_id` or `selected.skill`.

## Rollout

- `shadow`: assets exist and quality checks may be emitted
- `soft`: higher-risk candidates can be converted into confirmation prompts
- `strict`: can require the presence of quality metadata, but still cannot become a router

## Current upstream re-audit note

Prompt-Engineering-Guide upstream may change site chrome, CTA copy, examples, or repository hygiene without changing the stable guidance already distilled into VCO cards and checklists.
Those updates refresh source metadata, but do not automatically justify new canonical prompt assets.
