# Repo Slimming Refresh Path Role Matrix

## Purpose

This matrix refreshes the earlier 2026-04-04 slimming inventory after the first archive-focused waves.

The main point of the refresh is simple: the repository is no longer primarily blocked by `docs/plans/**` or `docs/releases/**`. The current bottlenecks are live-root sprawl, proof and fixture retention, verify-family complexity, and bundled payload size.

## Source Requirement / Plan

- [`../requirements/2026-04-04-comprehensive-repo-slimming-refresh.md`](../requirements/2026-04-04-comprehensive-repo-slimming-refresh.md)
- [`../plans/2026-04-04-comprehensive-repo-slimming-refresh-plan.md`](../plans/2026-04-04-comprehensive-repo-slimming-refresh-plan.md)

## Matrix

| Path Family | Primary Role | Current Issue | Recommended Next Step |
| --- | --- | --- | --- |
| `docs/README.md`, `docs/status/**`, `docs/install/**` | live navigation | current spine is valid | keep live and concise |
| root `docs/*.md` live set | live navigation but over-expanded | about `150` root docs still compete for authority | regroup into family directories, merge, or archive |
| `docs/archive/**` | archive | already carries historical load | keep archive-first |
| `references/index.md` | live navigation | correct stable landing surface | keep live and concise |
| root `references/*` live set | mixed contract surface | about `65` root files remain flat and crowded | regroup by contracts, matrices, ledgers, scenarios, and checklists |
| `references/proof-bundles/**` | fixture / proof | manifests are valuable, raw detail is noisy | keep manifests and summaries live; archive low-signal raw logs |
| `references/fixtures/**` | fixture | some families have weak consumer clarity | add consumer ledger, then archive historical-only families |
| `scripts/verify/**` | contract-first executable surface | `205` files, high family sprawl | extract shared logic first, keep path stability |
| `scripts/setup/**`, `scripts/research/**`, `scripts/learn/**` | auxiliary operator surface | likely contains low-frequency or dead helpers | exact-path consumer audit before retirement |
| `bundled/skills/**` | packaged payload | about `30M` and `2120` files, largest hotspot | define payload tiers first via `config/bundled-skill-tier-policy.json`, then cut |
| `packages/**`, `core/**`, `config/**` | canonical source | behavior-bearing | protect |
| `adapters/**`, `dist/**`, `distributions/**` | compatibility and release projections | active release-facing contracts | protect |
| `tests/integration/**`, `tests/runtime_neutral/**` | verification source | needed to prove slimming is safe | protect |
| `benchmarks/**`, `vendor/**`, `third_party/**` | low-mass edge surfaces | not first-order slimming payoff | monitor only for now |

## Decision Rules

- Strong slimming should reduce the widest live roots before it spends review budget on tiny directories.
- Any path with live config, test, release, or installer callers is a contract problem before it is a cleanup problem.
- Archive-first is the default downgrade when consumer proof is incomplete.
- Bundled payload reduction must follow tiering, not precede it.
