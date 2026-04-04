# Pilot Scenarios and Evaluation

## 目标

Wave28 为四个吸收平面定义统一的 `pilot-*.json` 试点场景，确保治理资产不是“只写文档”，而是可以被 gate 读取、被 rollout 引用、被 promotion board 追踪。

## 命名约定

本轮试点 fixture 采用唯一命名规范：

- `pilot-memory.json`
- `pilot-prompt.json`
- `pilot-browserops.json`
- `pilot-desktopops.json`

不再把 `*-shadow.json` 作为 Wave28 的 canonical pilot 命名。

## Legacy / Non-canonical Fixtures

- `*-shadow.json` 旧命名不再被 `vibe-pilot-scenarios.ps1` 或 promotion board 使用，应视为已退役样例，而不是可执行试点资产。
- `prompt-asset-boost.mock.json` 与 `llm-acceleration.mock.json` 仍保留，但它们仅服务各自 gate 的 mock provider，不属于 Wave28 pilot fixture。

## 场景矩阵

| 平面 | Fixture | 评估目标 |
|---|---|---|
| Memory | `scripts/verify/fixtures/pilot-memory.json` | 验证 `state_store` 仍是 canonical session owner，`mem0` / `Letta` 不越权 |
| Prompt | `scripts/verify/fixtures/pilot-prompt.json` | 验证 prompt intelligence 只增强资产层，不形成第二 router |
| BrowserOps | `scripts/verify/fixtures/pilot-browserops.json` | 验证 debug 场景下的 provider expectation 与 advice-only 边界 |
| DesktopOps | `scripts/verify/fixtures/pilot-desktopops.json` | 验证 Agent-S 语义仅作为 shadow contract 来源，不获得默认执行 owner |

## Wave39 扩展：Deep Extraction Closure

Wave39 在四个执行平面 fixture 之外，新增：

- `scripts/verify/fixtures/pilot-deep-extraction.json`

该 fixture 不代表新的 execution owner，而是把以下 release-closure 指标统一纳入可执行验证：

- `governed_mirror_coverage`
- `runtime_only_artifact_count`
- `upstream_manifest_coverage`
- `productization_ratio`

对应门禁：

```powershell
powershell.exe -File .\scripts\verify\vibe-deep-extraction-pilot-gate.ps1 -WriteArtifacts
```

promotion board 中的 Wave31-38 治理条目，应统一引用该 fixture 作为 Wave39 的 release-evidence 入口。

## Fixture 最小字段

每个 fixture 至少包含：

- `scenario_id`
- `plane_id`
- `task`
- `objective`
- `expected`
- `must_not`

## Gate

```powershell
powershell.exe -File .\scripts\verify\vibe-pilot-scenarios.ps1
```

## 通过标准

- 四个 pilot fixture 都存在并可解析
- 每个 fixture 都包含最小字段
- BrowserOps fixture 至少能表达 provider expectation 与 advice-only 边界
- 若 BrowserOps provider suggestion 脚本可用，gate 会执行一次联动 dry-run；若脚本暂不可用，Wave28 gate 不因外部脚本失效而误判失败
- 所有 fixture 的 `must_not` 都没有暗示第二控制面、第二默认执行 owner、第二 truth-source

## 与 Promotion Board 的衔接

- promotion board 用 `pilot_fixture` 记录试点入口
- `pilot_status = fixture_defined` 表示已具备最小试点资产
- 后续若要进入 `strict / promote`，需要补充重复 eval 和人工 signoff 证据
