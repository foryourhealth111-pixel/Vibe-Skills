# Route Replay Fixtures

This directory now keeps only route-facing fixtures that still have live consumers.

Retained fixtures:

- `recovery-wave-curated-prompts.json`: curated prompt pack consumed by router-bridge runtime tests.
- `openclaw-runtime-core-preview.json`: preview-lane route replay retained by proof bundles and preview governance.

The former `official-runtime-golden.json` replay baseline is no longer tracked because the current
no-regression gate validates host/platform contract truth from `tests/replay/fixtures/host-capability-matrix.json`
instead of replaying full official router outputs.
