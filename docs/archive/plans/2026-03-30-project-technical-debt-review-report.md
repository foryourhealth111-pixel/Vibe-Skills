# 2026-03-30 项目问题与技术债审查报告

- Up: [README.md](README.md)
- Repo docs root: [../README.md](../README.md)
- Requirement: [../requirements/2026-03-30-project-technical-debt-review.md](../requirements/2026-03-30-project-technical-debt-review.md)
- Plan: [2026-03-30-project-technical-debt-review-plan.md](2026-03-30-project-technical-debt-review-plan.md)

## Scope

本报告基于 `main` 上的 `v2.3.53` 代码面做静态审查，目标是识别仓库当前仍存在的问题与技术债。这里的“问题”既包括可能直接影响后续修改稳定性的结构性风险，也包括已经被治理文档显式承认、但尚未偿还的迁移债。

本轮没有执行全量 gate 或完整测试矩阵；结论主要来自仓库源码、治理配置、历史 release notes 与测试面分布的直接证据。

## Findings

### 1. High: 全量镜像 + 嵌套镜像拓扑把维护成本放大成系统性同步债

`config/version-governance.json` 仍把 `bundled/skills/vibe` 设为强制镜像目标，并把 `bundled/skills/vibe/bundled/skills/vibe` 作为可选但必须匹配的嵌套镜像目标，这意味着一次 canonical 变更默认要承担两层镜像一致性成本。[config/version-governance.json](/home/lqf/table/table5/workspace/release-v2.3.53-candidate/config/version-governance.json#L9) [config/version-governance.json](/home/lqf/table/table5/workspace/release-v2.3.53-candidate/config/version-governance.json#L14) [config/version-governance.json](/home/lqf/table/table5/workspace/release-v2.3.53-candidate/config/version-governance.json#L62)

同步脚本不是最小化复制，而是对 `config`、`protocols`、`references`、`docs`、`templates`、`scripts`、`mcp` 等整目录做复制，再按需裁剪额外文件。这个策略让镜像更新成本与仓库规模正相关，而不是与实际变更范围正相关。[scripts/governance/sync-bundled-vibe.ps1](/home/lqf/table/table5/workspace/release-v2.3.53-candidate/scripts/governance/sync-bundled-vibe.ps1#L63) [scripts/governance/sync-bundled-vibe.ps1](/home/lqf/table/table5/workspace/release-v2.3.53-candidate/scripts/governance/sync-bundled-vibe.ps1#L116) [scripts/governance/sync-bundled-vibe.ps1](/home/lqf/table/table5/workspace/release-v2.3.53-candidate/scripts/governance/sync-bundled-vibe.ps1#L138)

仓库当前文件量也说明这不是抽象风险：`bundled/skills/vibe` 下有 2158 个文件，嵌套镜像下还有 1061 个文件。任何 release / cleanup / docs 变更都会被镜像拓扑放大为一次高 churn 操作。

### 2. High: `release-cut` 不是完整的 release operator，却承担了 release operator 的角色

`release-cut.ps1` 的 preview 和 apply 动作只覆盖 `config/version-governance.json`、maintenance markers、changelog header、release ledger，以及“如果不存在就生成 release note stub”。它没有把 `docs/releases/README.md`、`dist/*/manifest.json` 或其他当前 release surface 作为更新对象纳入计划。[scripts/governance/release-cut.ps1](/home/lqf/table/table5/workspace/release-v2.3.53-candidate/scripts/governance/release-cut.ps1#L189) [scripts/governance/release-cut.ps1](/home/lqf/table/table5/workspace/release-v2.3.53-candidate/scripts/governance/release-cut.ps1#L236) [scripts/governance/release-cut.ps1](/home/lqf/table/table5/workspace/release-v2.3.53-candidate/scripts/governance/release-cut.ps1#L261)

更严重的是，它会在缺少 release note 时自动生成含 `- TODO` 的模板内容。这使“执行了 release-cut”与“发布面真实完成”之间存在明确落差。[scripts/governance/release-cut.ps1](/home/lqf/table/table5/workspace/release-v2.3.53-candidate/scripts/governance/release-cut.ps1#L263)

仓库里已经能看到这种债务留下的痕迹：`docs/releases/v2.3.35.md` 仍是纯 TODO，`docs/releases/v2.3.43.md` 有重复的 `Migration Notes` 段落并遗留 TODO。[docs/releases/v2.3.35.md](/home/lqf/table/table5/workspace/release-v2.3.53-candidate/docs/releases/v2.3.35.md#L1) [docs/releases/v2.3.43.md](/home/lqf/table/table5/workspace/release-v2.3.53-candidate/docs/releases/v2.3.43.md#L25)

仓库已经单独存在 `vibe-dist-manifest-gate.ps1` 去校验 `dist/*/manifest.json` 的 `source_release` 对齐，但 `release-cut.ps1` 的 gate 列表中并没有这个 gate，而且我也没有在测试目录里找到对 `release-cut.ps1` 的端到端覆盖。这意味着当前发布过程仍依赖人工补面，而不是由 operator 自己闭环。[scripts/verify/vibe-dist-manifest-gate.ps1](/home/lqf/table/table5/workspace/release-v2.3.53-candidate/scripts/verify/vibe-dist-manifest-gate.ps1#L183) [scripts/verify/vibe-dist-manifest-gate.ps1](/home/lqf/table/table5/workspace/release-v2.3.53-candidate/scripts/verify/vibe-dist-manifest-gate.ps1#L237) [scripts/governance/release-cut.ps1](/home/lqf/table/table5/workspace/release-v2.3.53-candidate/scripts/governance/release-cut.ps1#L70)

### 3. Medium-High: runtime 契约仍依赖多处手工重组，字段漂移风险高

`Freeze-RuntimeInputPacket.ps1` 手工构造了一个体积很大的 packet object，其中 `host_adapter`、`route_snapshot`、`authority_flags` 等字段都靠显式复制拼装出来；这不是共享 schema 驱动，而是写死在脚本内部的结构复制。[scripts/runtime/Freeze-RuntimeInputPacket.ps1](/home/lqf/table/table5/workspace/release-v2.3.53-candidate/scripts/runtime/Freeze-RuntimeInputPacket.ps1#L525) [scripts/runtime/Freeze-RuntimeInputPacket.ps1](/home/lqf/table/table5/workspace/release-v2.3.53-candidate/scripts/runtime/Freeze-RuntimeInputPacket.ps1#L550)

随后 `Invoke-PlanExecute.ps1` 又把同一批字段重新映射进 execution manifest，尤其是 `requested_host_adapter_id` / `effective_host_adapter_id` 这类关键信息，再次以手工读取 runtime packet 的方式转抄。[scripts/runtime/Invoke-PlanExecute.ps1](/home/lqf/table/table5/workspace/release-v2.3.53-candidate/scripts/runtime/Invoke-PlanExecute.ps1#L1095) [scripts/runtime/Invoke-PlanExecute.ps1](/home/lqf/table/table5/workspace/release-v2.3.53-candidate/scripts/runtime/Invoke-PlanExecute.ps1#L1131)

`VibeExecution.Common.ps1` 还要再单独输出一次 specialist execution 侧的 host adapter 信息，说明同一契约在多个阶段被重复编码。[scripts/runtime/VibeExecution.Common.ps1](/home/lqf/table/table5/workspace/release-v2.3.53-candidate/scripts/runtime/VibeExecution.Common.ps1#L474)

我没有把这归类为“当前 bug”，因为仓库确实已经有 `test_multi_host_specialist_execution.py` 等测试在兜这些字段；但这仍是明显技术债。当前稳定性依赖“多点同步修改 + 测试兜底”，而不是“单一 schema + 自动派生”。

### 4. Medium: `outputs/` 边界已被承认是过渡态，但仍保留一组真实 tracked generated artifacts

`.gitignore` 的规则很明确：`outputs/**` 原则上都应视为生成产物并保持 untracked，只允许 `config/outputs-boundary-policy.json` 里声明的 legacy allowlist 例外。[.gitignore](/home/lqf/table/table5/workspace/release-v2.3.53-candidate/.gitignore#L1)

但 policy 本身又明确写着 `expected_tracked_output_count = 21`，并把这些文件定义为 “legacy candidate artifact / legacy compare fixture / legacy verify snapshot”，迁移阶段也仍是 `stage2_mirrored`。[config/outputs-boundary-policy.json](/home/lqf/table/table5/workspace/release-v2.3.53-candidate/config/outputs-boundary-policy.json#L1) [config/outputs-boundary-policy.json](/home/lqf/table/table5/workspace/release-v2.3.53-candidate/config/outputs-boundary-policy.json#L79) [config/outputs-boundary-policy.json](/home/lqf/table/table5/workspace/release-v2.3.53-candidate/config/outputs-boundary-policy.json#L85)

仓库当前确实跟踪了这 21 个 `outputs/*` 文件。它们并非违规，但它们意味着仓库还没有彻底建立“生成物只在 outputs、长期基线只在 references/fixtures”这一清晰边界。这会持续增加审查噪音，也让后续贡献者更难判断哪些 `outputs` 是临时文件，哪些是长期受控基线。[config/outputs-boundary-policy.json](/home/lqf/table/table5/workspace/release-v2.3.53-candidate/config/outputs-boundary-policy.json#L5)

### 5. Medium: 历史 release surface 质量不稳定，削弱了 release notes 作为真相面的可信度

`docs/releases/README.md` 把 release notes 描述为“governed VCO release notes and the minimum runtime-facing navigation needed to cut or verify a release”，说明这里应当是正式发布面导航，而不是草稿堆积区。[docs/releases/README.md](/home/lqf/table/table5/workspace/release-v2.3.53-candidate/docs/releases/README.md#L5)

但历史版本里仍然存在未完成 note 和结构重复的问题：`v2.3.35` 纯 TODO，`v2.3.43` 重复 `Migration Notes` 且尾部仍有 TODO。这类遗留不会破坏当前运行时，但它会破坏“版本文档可回溯、可审计”的治理可信度，特别是在需要追溯某一版真实变更范围时。[docs/releases/v2.3.35.md](/home/lqf/table/table5/workspace/release-v2.3.53-candidate/docs/releases/v2.3.35.md#L6) [docs/releases/v2.3.43.md](/home/lqf/table/table5/workspace/release-v2.3.53-candidate/docs/releases/v2.3.43.md#L31)

### 6. Medium: Router / runtime 入口脚本体量过大，遗留基线仍是活跃依赖

几个关键入口脚本的体量已经明显超出轻量治理脚本的维护舒适区：`scripts/router/resolve-pack-route.ps1` 1382 行，`scripts/router/legacy/resolve-pack-route.legacy.ps1` 5481 行，`scripts/runtime/Invoke-PlanExecute.ps1` 1363 行，`scripts/runtime/Freeze-RuntimeInputPacket.ps1` 636 行。这些文件仍是高频治理面，审查和安全修改成本都偏高。

更重要的是，legacy router 不是单纯的历史备份，而是当前 contract gate 和 main-chain policy 仍明确要求保留与比对的活跃基线。也就是说，模块化工作虽然已经开始，但仓库仍要同时维护“现代主入口 + 超大 legacy baseline”两套路由真相面。[scripts/verify/vibe-router-contract-gate.ps1](/home/lqf/table/table5/workspace/release-v2.3.53-candidate/scripts/verify/vibe-router-contract-gate.ps1#L175) [config/official-runtime-main-chain-policy.json](/home/lqf/table/table5/workspace/release-v2.3.53-candidate/config/official-runtime-main-chain-policy.json#L38) [docs/governance/router-modularization-governance.md](/home/lqf/table/table5/workspace/release-v2.3.53-candidate/docs/governance/router-modularization-governance.md#L5)

这不是说模块化没有价值，而是说当前模块化仍未把维护负担真正降下来。仓库现在承担的是“新增模块层”与“保留大型 legacy 比对基线”的双重成本。

## Open Questions / Assumptions

- 本报告没有执行全量 PowerShell gate；因此我把结论限定为仓库源码与治理面的结构性审查，而不是一次运行态健康证明。
- 对 `outputs/` 的判断是“已治理承认但仍未清偿的迁移债”，不是说当前 allowlist 本身违背仓库规则。
- 对 runtime host adapter 字段传播的判断是“设计上脆弱”，不是宣称 `v2.3.53` 当前已经存在字段错误；最近版本事实上已经针对这条链路做过修复。

## Debt Themes

这次审查看到的核心不是单点 bug，而是三类系统性债务：

1. 发布与镜像面过宽，导致一次正确变更需要人工维护过多派生表面。
2. runtime / router 契约依然带有较强的手工拼装和历史兼容负担。
3. 历史产物和迁移基线没有完全退出正式 truth surfaces，长期削弱了仓库的可审计性。
