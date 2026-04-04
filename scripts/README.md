# Scripts

`scripts/` 是 operator surface。这里只回答“该进哪个脚本目录”，不承担 proof contract 或长期 reference 导航。

## Start Here

- bootstrap / setup: [`bootstrap/one-shot-setup.ps1`](./bootstrap/one-shot-setup.ps1), [`bootstrap/one-shot-setup.sh`](./bootstrap/one-shot-setup.sh)
- operator actions: [`governance/README.md`](./governance/README.md)
- verify entrypoint: [`verify/README.md`](./verify/README.md)
- verify family map: [`verify/gate-family-index.md`](./verify/gate-family-index.md)
- shared helpers: [`common/README.md`](./common/README.md)
- router modules: [`router/README.md`](./router/README.md)

## Directory Roles

- `scripts/governance/`: rollout, release, audit, policy probes
- `scripts/verify/`: executable gates and proof-producing checks
- `scripts/common/`: shared primitives and execution-context helpers
- `scripts/router/`: routing helpers and probes
- `scripts/bootstrap/`, `scripts/setup/`: install and environment setup
- `scripts/research/`, `scripts/learn/`: auxiliary support surfaces with exact-caller retention only

## Cross-Layer Handoff

- closure proof contract: [`../docs/status/non-regression-proof-bundle.md`](../docs/status/non-regression-proof-bundle.md)
- long-lived contracts and ledgers: [`../references/index.md`](../references/index.md)

## Rules

- topology-aware scripts must run from the canonical repo root.
- packaging / release / compatibility changes后要回到 [`verify/README.md`](./verify/README.md) 复跑 gates。
- shared logic 进 `scripts/common/`，不要在单脚本复制 ad hoc helper。
