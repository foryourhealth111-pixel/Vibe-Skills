# Change Proof Matrix

This matrix translates change classes into the minimum planning and proof
burden. It is intentionally conservative.

| Change class | Typical paths | Plan required before edit | Minimum proof floor | Notes |
| --- | --- | --- | --- | --- |
| Docs-only contributor guidance | `docs/**`, `references/**` except fixtures, `README.md`, `docs/README.md`, `CONTRIBUTING.md` | No, unless the docs rewrite runtime or governance guarantees | `git diff --check` and link/navigation sanity | Safe default zone, but still keep links and claims coherent |
| Governance docs or operator guidance | `docs/**`, `scripts/governance/**`, `scripts/verify/**`, policy-facing `references/**` | Usually no for additive docs, yes if runtime obligations or stop-rules change | Relevant gate docs updated, `git diff --check`, and any touched governance gate rerun if behavior changed | Do not change policy language without matching evidence surfaces |
| Public promises or disclosure | root `README.md`, `NOTICE`, `THIRD_PARTY_LICENSES.md`, provenance docs | Yes if public promises change runtime, provenance, or disclosure scope | Disclosure/provenance validation plus `Command -> Output -> Claim` evidence | Public text is part of the contract |
| Mirror or fixture change | `bundled/**`, `references/fixtures/**`, tracked `outputs/**` | Yes | Canonical-first sync plus parity/boundary proof | Never mirror-first |
| Provenance or retained upstream change | `third_party/**`, `vendor/**`, provenance manifests | Yes | Provenance, disclosure, and cleanliness proof | Every retained upstream needs a clear source and record |
| Runtime-affecting change | `install.*`, `check.*`, `SKILL.md`, `protocols/**`, `scripts/router/**`, routing locks and manifests | Yes | Full runtime non-regression bundle | Treat as high-risk even if diff is small |

## Runtime Non-Regression Bundle

When the change is runtime-affecting or crosses into `Z0` or `Z2`, expect to
justify the result with the relevant subset of:

- `scripts/verify/vibe-pack-routing-smoke.ps1`
- `scripts/verify/vibe-current-routing-debt-gate.ps1`
- `scripts/verify/vibe-version-packaging-gate.ps1`
- `scripts/verify/vibe-output-artifact-boundary-gate.ps1`
- `scripts/verify/vibe-repo-cleanliness-gate.ps1`
- `scripts/verify/vibe-installed-runtime-freshness-gate.ps1`
- `scripts/verify/vibe-release-install-runtime-coherence-gate.ps1`

## Evidence Format

Whenever you claim a guarded or runtime-sensitive change is safe, record:

1. `Command`
2. `Output`
3. `Claim`

If you cannot produce that evidence, the change is not ready to be called
non-regressive.
