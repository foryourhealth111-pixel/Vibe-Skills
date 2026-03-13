# Skill Spec Delta

本文件说明：在不批量导入外部 skills 的前提下，VCO 从高价值 skill 仓库中真正吸收了哪些“元规范增量”。

## 1. Current Baseline

当前 VCO skill 生态已经具备的最小事实：

- 多数 skill 有 `SKILL.md`
- 大多数 skill 已带 `name` / `description` frontmatter
- `pack-manifest.json` / `capability-catalog.json` / `skill-alias-map.json` 已形成整体路由面，P2.5 已把它们共同纳入 skill-surface 硬化范围
- `skills-lock.json` 已对 bundled skills 做离线闭包校验

但这些还不足以解决：

- routed surface 引用的 skill 是否真实存在；
- skill frontmatter 是否对 confirm UI / explainability 足够稳定；
- 哪些重复显示名是“兼容别名”，哪些是无治理重复；
- subagent role prompt 是否有明确 taxonomy 与存在性校验。

## 2. Delta from External Best Practices

P2 / P2.5 从外部高价值 skill / subagent 仓库中吸收的不是具体能力，而是以下规范：

| Delta | Why It Matters | P2 落点 |
|---|---|---|
| `routed surface` 明确化 | 只治理真正会被 VCO 路由到的 skill，而不是治理整个互联网 skill 宇宙 | `config/skill-metadata-policy.json` |
| `frontmatter minimum bar` | confirm UI、解释性输出、人工选择菜单依赖稳定 `name/description` | `skill-metadata-gate.ps1` |
| `duplicate display-name allowlist` | 区分“兼容别名”与“无治理重复” | `config/skill-metadata-policy.json` |
| `role taxonomy + permission bundle` | 防止 subagent prompt 无限膨胀且职责重叠 | `references/subagent-role-taxonomy.md` |
| `overlay id 不能冒充 skill id` | 避免 config / overlay 标识污染 skill 路由面 | `skill-metadata-gate.ps1` + catalog 修正 |

## 3. New Minimum Requirements

### Hard-required now

以下要求已进入 P2 gate 关注范围：

- capability catalog 中的 `skills[]` 必须全部是真实 skill id
- capability catalog 中的 `advice_overlays[]` 必须与 `skills[]` 分层，overlay 不得冒充 skill
- capability catalog 中的 `skills[]` 必须全部是真实 skill id
- pack manifest 中的 `skill_candidates[]` / `defaults_by_task` 必须解析到真实 skill，并满足最小 frontmatter 门槛
- alias map 的 terminal target 必须解析到 canonical skill，而不是另一个 alias
- routed capability skill 必须有 frontmatter
- frontmatter 至少包含：
  - `name`
  - `description`
- `metadata_hardening` anchor 必须把 catalog ↔ policy ↔ gate 串起来
- local dialectic role prompt 文件必须存在，且 team template / taxonomy 双边一致

### Allowed but governed

以下情况允许存在，但必须被 policy 显式说明：

- 两个目录共享同一个显示名（如兼容别名 / 历史镜像）
- 目录名与 frontmatter `name` 不完全相同（例如 display label 与 canonical id 分离）

### Not yet hard-required

这些字段/规则被记录为 future hardening，但本轮不强制：

- `tags`
- `task_allow`
- `grade_allow`
- `permission_bundle` 直接写进每个 `SKILL.md`
- `managed_by_pack`
- `evidence_style`
- `confirm_behavior`

原因：当前仓内历史 skill 数量大，直接一刀切会把 P2 变成全量重写，而不是最小治理闭环。

## 4. Anti-Patterns Captured by P2

P2 明确把以下情况视为 metadata anti-pattern：

### A. Missing skill target

例：`capability-catalog.json` 中引用了并不存在的 skill id。

危害：

- confirm UI 生成的 skill 说明会失真；
- 用户看见的选项与真实可执行能力不一致；
- 路由解释链条断裂。

### B. Duplicate display name without policy

例：两个 skill 目录都把 frontmatter `name` 设为同一个值，但没有被标记为兼容组。

危害：

- 菜单里出现两个同名项；
- review / telemetry / 统计时混淆；
- 人工选择与 pack explainability 变差。

### C. Overlay identifier masquerading as skill

例：把 `system-design-overlay` 这种 overlay/config id 当作 `skills[]` 成员。

危害：

- skill surface 与 overlay surface 混在一起；
- 让“能力目录”变得不再可信。

## 5. Future Extension Path

如果 P2 通过并稳定，可继续向下扩：

- 把 `permission_bundle` 提升为 skill frontmatter 推荐字段；
- 把 routed skill 的 `supported_tasks` / `supported_grades` 明确化；
- 为 capability-catalog 建立更细粒度的 `skills[]` vs `advice_overlays[]` 区分；
- 把 duplicate allowlist 从静态 policy 逐步收敛为 alias-only。

## 6. Bottom Line

P2 吸收的是 **规范**，不是 **数量**。

真正有价值的增量是：

- skill id 可验证
- metadata 可解释
- role archetype 可治理
- 重复能力可量化

而不是再导入一批看起来很强、但对 VCO 路由面没有治理价值的新 skills。

