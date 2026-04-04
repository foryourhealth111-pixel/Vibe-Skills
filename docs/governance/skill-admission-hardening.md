# Skill Admission Hardening

本文件定义 VCO 在 `P2` 阶段对 skill / subagent 生态的硬化原则。目标不是继续批量吸收外部 skills，而是把 **VCO 已经会路由的能力面** 变成一个有元数据边界、可验证、可去重、可维护的受管集合。

## 1. 为什么要做 P2

`P1` 已经把外部工具接入治理化；但 skill 生态仍有另一类风险：

- 同一能力以多个名字、多个 prompt 入口重复存在；
- `pack-manifest`、`capability-catalog`、`alias-map` 中可能引用到并不存在的 skill；
- skill 目录、frontmatter 名称、展示名之间不一致，导致 confirm UI 与路由解释变差；
- subagent 角色 prompt 存在，但没有形成统一 taxonomy 与 permission bundle 语义。

因此，P2 的核心不是“再加多少 skills”，而是：

1. **把 routed surface 明确化**：VCO 真正依赖哪些 skills；
2. **把 metadata 规范化**：frontmatter、别名、显示名、角色 prompt 的最小要求；
3. **把重复能力约束化**：允许少量兼容别名，但不允许无治理重复；
4. **把 subagent 角色治理化**：将角色 archetype、权限束、owner 边界写成 reference + gate。

## 2. Admission Boundary

P2 只治理两类对象：

### A. Routed Skills

P2.5 已把 **capability catalog、pack manifest、skill alias map 明确暴露的 routed surface** 一并纳入治理，并继续保持 overlay 从 `skills[]` 中剥离。

当前已进入 gate 的来源是：

- `config/capability-catalog.json` 中的 `skills[]` / `advice_overlays[]`
- `config/pack-manifest.json` 中的 `skill_candidates[]` / `defaults_by_task`
- `config/skill-alias-map.json` 中的 alias targets
- `references/team-templates.md` 中明确依赖的本地角色 skill

它们必须满足最小 metadata policy，并通过 `skill-metadata-gate.ps1` 与现有 pack/offline verify 链共同验证。

### B. Local Role Prompts / Subagent Bundles

目前重点是 `local-vco-roles` 提供的 dialectic / review 角色 prompt：

- `team-lead`
- `bug-analyst`
- `arch-critic`
- `integration-analyst`
- `usability-analyst`

这些角色不一定都是独立 skill，但它们属于 **VCO 的可调用角色面**，因此必须纳入 taxonomy 与存在性校验。

## 3. 明确不吸收的内容

以下仍然不进入默认运行面：

- 外部 awesome skills 列表的批量导入；
- 第二套 subagent runtime / orchestrator；
- 纯 prompt 资产但没有明确 owner / activation contract / permission boundary 的角色模板；
- overlay / config id 冒充 skill id 进入 `capability-catalog` 或 pack candidates。

换言之：

- **目录可以作为兼容生成目标存在**，不代表 **能力可以默认路由**；
- **高星仓库** 可以成为参考，不代表 **其 skill corpus** 应直接并入 VCO；
- **子代理角色** 可以增加，但必须先有 taxonomy，再谈默认化。

## 4. 当前最小硬化要求

### Routed skill minimum bar

- 有真实 skill 目录与 `SKILL.md`
- frontmatter 存在且可解析
- `name` 非空
- `description` 非空
- 若存在重复显示名，必须是 policy 允许的兼容组
- capability catalog 中不得把 overlay / policy / manifest 这类元标识冒充成 skill id
- advice overlay 必须留在 `advice_overlays[]`，不能混入 `skills[]`

### Role prompt minimum bar

- 角色文件存在
- 与 `references/team-templates.md` 中的角色映射一致
- 能映射到明确的 native agent type 与 permission bundle
- 角色用途清晰：不是“另一个随意命名的 reviewer”

## 5. P2 的治理产物

- `config/skill-metadata-policy.json`
- `scripts/verify/skill-metadata-gate.ps1`
- `references/subagent-role-taxonomy.md`
- `references/skill-spec-delta.md`
- 本文档（`docs/governance/skill-admission-hardening.md`）

其中：

- `policy` 负责把规则变成机器可读配置；
- `gate` 负责把规则变成可执行验证；
- `references` 负责解释“为什么这样收紧，而不是继续扩容”。

## 6. 与 P1 的关系

P1 解决的是“工具如何不失控”；P2.5 则把 capability catalog / pack manifest / alias map / local role surface 一起收进同一条 skill-surface 治理链。

二者共同形成一个更清晰的边界：

- **工具治理**：控制副作用面；
- **skill 治理**：控制语义面与路由面。

如果没有 P2，VCO 仍可能出现“工具可控，但 skill 入口混乱”的问题。

## 7. 验证入口

最小验证命令：

```powershell
& ".\scripts\verify\skill-metadata-gate.ps1" -WriteArtifacts
```

P2.5 建议跑完整验证链：

```powershell
& ".\scripts\verify\skill-metadata-gate.ps1" -WriteArtifacts
& ".\scripts\verify\vibe-pack-routing-smoke.ps1"
& ".\scripts\verify\vibe-offline-skills-gate.ps1"
& ".\scripts\verify\vibe-config-parity-gate.ps1" -WriteArtifacts
& ".\scripts\verify\vibe-version-packaging-gate.ps1" -WriteArtifacts
```

这样既能验证 expanded metadata 规则，也能验证 pack / alias safety 与 canonical-only packaging contract。
