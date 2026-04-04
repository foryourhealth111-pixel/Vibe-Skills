# Upstream Eval Pilot Scenarios

## 1. 目的

这些 pilot scenario 用来证明 Wave37-38 新增的 role-pack / discovery-eval material layer 不是“只写文档”，而是可以被 gate、审阅和后续 promotion 证据读取的制度化资产。

当前阶段它们只承担 **shadow / advisory evidence** 作用，不直接改变 runtime surface。

## 2. Scenario matrix

| Scenario ID | Source | 焦点 | 预期产物 | 通过条件 |
|---|---|---|---|---|
| `pilot-discovery-vibe-workflows` | `awesome-vibe-coding` | 抽取 vibe workflow / anti-pattern | capability hit + material-only说明 | 不出现新的 runtime / pack / skill surface |
| `pilot-tool-landscape-watch` | `awesome-ai-tools` | 工具生态 watchlist、能力空缺登记 | catalog slice + evidence note | 输出指向现有 canonical owner，而不是新 tool runner |
| `pilot-cn-query-localization` | `vibe-coding-cn` | 中文术语 / 提示表达覆盖 | localized discovery slice | 不出现独立中文 router |
| `pilot-e2b-sandbox-eval` | `awesome-ai-agents-e2b` | sandbox / remote execution 评测模式 | eval corpus slice + pilot说明 | 不出现新的 sandbox execution owner |
| `pilot-corpus-to-catalog-dedup` | cross-source | 同类 retained value 去冗余 | dedup decision record | 每个条目都能解释 `dedup_with` |
| `pilot-material-layer-boundary` | cross-source | 证明 material layer 不越界 | governance statement + gate evidence | 所有 discovery/eval 条目均为 `runtime_surface = none` |
| `pilot-role-pack-supervisor-seed` | `agent-squad` / `awesome-claude-code-subagents` | supervisor scatter/gather 模式保留 | role-pack policy evidence | 只映射到现有 template，不新增 team owner |
| `pilot-skill-distillation-quality` | `claude-skills` / `antigravity-awesome-skills` | skill schema / taxonomy 规则化 | distillation rule evidence | 只生成规则与质量门禁，不生成第二 skill runtime |

## 3. 每个 pilot 至少回答的问题

1. retained value 是什么？
2. canonical owner 是谁？
3. 它进入的是 runtime 邻接面，还是 material layer？
4. 与现有能力重复在哪里？
5. 失败时如何回退到“只保留参考”？

## 4. 读取路径

这些 scenario 目前由以下资产共同证明：

- `config/role-pack-policy.json`
- `config/capability-catalog.json`
- `docs/role-pack-distillation-governance.md`
- `docs/governance/discovery-eval-corpus-governance.md`
- `references/skill-distillation-rules.md`
- `references/capability-catalog.md`
- `scripts/verify/vibe-role-pack-governance-gate.ps1`
- `scripts/verify/vibe-capability-catalog-gate.ps1`

## 5. 推荐验证命令

```powershell
pwsh -File .\scripts\verify\vibe-role-pack-governance-gate.ps1 -WriteArtifacts
pwsh -File .\scripts\verify\vibe-capability-catalog-gate.ps1 -WriteArtifacts
```

可选补充：

```powershell
pwsh -File .\scripts\verify\vibe-pack-routing-smoke.ps1
pwsh -File .\scripts\verify\vibe-keyword-precision-audit.ps1
```

## 6. 当前边界声明

在 promotion board 尚未接线本 wave 新平面之前，以上 pilots 只证明：

- 这些 retained value 已被 canonical repo 记录；
- 有统一 schema；
- 有 gate 能验证；
- 但尚未自动升级为 soft/strict/promote runtime authority。

## 7. 2026-03-17 Source Health Notes

- `pilot-discovery-vibe-workflows`: upstream remains active; keep refreshing terminology and workflow anti-pattern evidence.
- `pilot-cn-query-localization`: upstream remains active; keep refreshing Chinese-language prompts and Codex-oriented phrasing.
- `pilot-tool-landscape-watch`: upstream remains broad and noisy; use it only for watchlist deltas and capability-gap accounting.
- `pilot-e2b-sandbox-eval`: upstream is relatively stale; keep the scenario alive only as eval/reference evidence until a fresher canonical sandbox challenger appears.
