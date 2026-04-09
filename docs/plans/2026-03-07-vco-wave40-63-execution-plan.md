# VCO Wave40-63 Formal Execution Plan

- Up: [../README.md](../README.md)
- Index: [README.md](README.md)

> **Execution Mode:** XL / unattended / `vibe`-first. Every delegated subtask must end with `$vibe` and remain inside the existing VCO single-control-plane, single-default-execution-owner, single-canonical-truth-source constraints.

**Goal:** 在 Wave31-39 完成“先收口，再扩张”的基础上，把 Wave40-63 落成一个正式、可审计、可执行、可验证的治理执行面：先把 UTF-8 BOM / frontmatter / runtime freshness / execution-context 这类会直接破坏运行态解析与副本新鲜度的风险彻底制度化，再把去重图谱、评测自适应路由、持续价值榨取与 release 运营闭环固化为 VCO 原生资产。

**Core Principle:** 任何“吸收完成”的声明都必须至少对应 `docs + config + reference + verify gate (+ install/runtime linkage if applicable)`；没有产物层与门禁层，就只能算候选吸收，不能算已完成吸收。

## Guardrails

1. `VCO` remains the single control plane.
2. New planes must not become a second default execution owner.
3. Canonical repo root remains the single truth source.
4. Runtime hardening must precede new intake.
5. Byte-0 frontmatter integrity is stop-ship.
6. Advice-first / shadow-first / rollback-first still applies.
7. No duplicate role ownership.
8. Every wave needs gate-backed evidence before promotion.

## Execution Summary

The canonical wave inventory for 40-63 is maintained in [config/wave40-63-execution-board.json](../../config/wave40-63-execution-board.json). This compatibility plan preserves the formal execution entrypoint expected by historical governance gates while the living governance corpus now sits across:

- [docs/governance/frontmatter-bom-governance.md](../governance/frontmatter-bom-governance.md)
- [docs/governance/capability-dedup-graph-governance.md](../governance/capability-dedup-graph-governance.md)
- [docs/governance/adaptive-routing-eval-governance.md](../governance/adaptive-routing-eval-governance.md)
- [docs/continuous-value-extraction-operations.md](../continuous-value-extraction-operations.md)
- [config/upstream-value-ops-board.json](../../config/upstream-value-ops-board.json)

## Verification Stack

```powershell
pwsh -NoProfile -File .\scripts\verify\vibe-bom-frontmatter-gate.ps1 -WriteArtifacts
pwsh -NoProfile -File .\scripts\verify\vibe-wave40-63-board-gate.ps1 -WriteArtifacts
pwsh -NoProfile -File .\scripts\verify\vibe-capability-dedup-gate.ps1 -WriteArtifacts
pwsh -NoProfile -File .\scripts\verify\vibe-adaptive-routing-readiness-gate.ps1 -WriteArtifacts
pwsh -NoProfile -File .\scripts\verify\vibe-upstream-value-ops-gate.ps1 -WriteArtifacts
pwsh -NoProfile -File .\scripts\verify\vibe-release-install-runtime-coherence-gate.ps1 -TargetRoot "$env:USERPROFILE\.codex"
```
