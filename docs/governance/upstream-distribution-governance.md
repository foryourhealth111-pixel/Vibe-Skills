# Upstream Distribution Governance

## Purpose

This document defines how upstream sources are classified and made traceable across:

- canonical runtime/distribution metadata
- corpus/value-extraction metadata
- public third-party disclosure

## Current Canonical Model

The upstream governance model is intentionally split:

- `config/upstream-lock.json`
  Tracks runtime-adjacent upstreams and distribution metadata.
- `config/upstream-corpus-manifest.json`
  Tracks corpus, shadow-source, browser/document/memory/prompt governance sources.
- `config/upstream-source-aliases.json`
  Normalizes canonical slugs across the two registries.

This split is valid only if the public disclosure surface stays traceable to those registries.

## Canonicalization Rule

For every upstream source, exactly one of the following must be true:

1. It exists in `config/upstream-lock.json`.
2. It exists in `config/upstream-corpus-manifest.json`.
3. It exists in both, with a shared canonical slug and a non-conflicting explanation of its dual role.

If it appears in `THIRD_PARTY_LICENSES.md` but in neither canonical registry, governance is incomplete.

## Dual-Role Sources

Some upstreams are both:

- runtime/distribution references, and
- corpus/policy/value sources.

These must share the same canonical slug and compatible disclosure language.

Typical examples include:

- `agent-s`
- `browser-use`
- `letta`
- `mem0`
- `prompt-engineering-guide`

## Disclosure Contract

`THIRD_PARTY_LICENSES.md` is a disclosure document, not an independent registry.

It must answer:

- which upstream is involved
- under which license
- how VCO uses it
- what the distribution boundary is
- which canonical source-of-truth record governs it

## Branch Pins vs Commit Pins

The lock may contain both moving branch pins and immutable commit pins.

That is acceptable for Phase 0 governance as long as:

- the choice is visible
- the repo does not pretend moving branches are immutable release locks
- freshness is audited separately

Commit pinning is stronger evidence. Branch pinning is weaker but still traceable.

## Required Future Closure

Before any large-scale repo-local upstream retention is promoted, the following must be true:

- no placeholder freshness fields remain unresolved
- all disclosed upstreams are canonicalized
- all retained upstream assets can carry `ORIGIN.md`
- all retained upstreams have an explicit tier and redistribution posture
