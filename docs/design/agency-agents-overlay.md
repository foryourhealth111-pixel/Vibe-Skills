# agency-agents 部门专家 overlay（advice-only）接入 VCO

## 目标

把 `agency-agents` 的部门/岗位经验，作为 **prompt overlay** 注入到 VCO 工作流中：

- VCO 仍负责：Grade 路由、协议（think/do/review/team/retro）、工具链与质量闸门（P5/V2/V3）。
- overlay 只负责：补齐“部门专家视角”与“交付物格式/检查清单”，帮助你稳定产出跨部门可验收的结果。

当前覆盖的部门：

- 工程部（Engineering）
- 设计部（Design）
- 产品部（Product）
- 市场部（Marketing）
- 项目管理部（Project Management）
- 测试部（Testing / QA）— 可在任何阶段推荐
- 空间计算部（Spatial Computing / XR）

## 设计原则（避免冲突）

- **advice-only**：overlay 不改变 VCO 路由/协议/工具选择，只影响“视角与交付物格式”。
- **冲突优先级**：用户显式指令 > VCO 协议/质量闸门 > overlay 建议。
- **组合上限**：默认最多选择 2 个 overlay（典型：1 个部门 + 1 个测试门禁）。
- **不写死脚本**：overlay 不强制要求某个外部脚本存在；执行仍由 VCO 现有技能链完成。

## 上游来源（vendor）

上游仓库（参考）：

- `https://github.com/msitarzewski/agency-agents`

> 本仓库默认不 vendoring 上游仓库内容；我们只保留“精简版部门 overlay 模板”（可注入 prompt），避免把第三方工程结构与许可证边界强行引入核心编排层。

## overlay 定义位置

部门 overlay 的“精简版模板”位于：

- `references/overlays/agency/`

每个文件都是可直接注入到 prompt 的文本片段（包含 overlay contract + 交付物模板 + 检查清单 + 上游角色索引）。

## 自动建议 → 确认 → 注入：如何使用

### 1) 获取候选 overlay（自动建议）

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/overlay/suggest-agency-overlays.ps1 `
  -Task "写你的任务描述" `
  -Stage think
```

`-Stage` 支持：`think` / `do` / `review` / `team` / `retro` / `any`。

脚本会输出 Top-K 候选（默认 3 个）与推荐理由（命中关键词）。

### 2) 选择并渲染“注入文本”

用序号选择（最多 2 个）：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/overlay/suggest-agency-overlays.ps1 `
  -Task "写你的任务描述" `
  -Stage think `
  -Select "1,2"
```

或者用 overlay id 选择：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/overlay/suggest-agency-overlays.ps1 `
  -Task "写你的任务描述" `
  -Stage think `
  -Select "agency-testing,agency-engineering"
```

输出中会包含：

- 菜单（建议候选）
- `--- BEGIN VCO PROMPT OVERLAY ---` 到 `--- END VCO PROMPT OVERLAY ---` 的注入片段

把注入片段复制到你当前的 `/vibe` 任务描述或执行阶段 prompt 中即可。

## 配置（关键词 / Top-K / 组合上限）

配置文件：

- `config/agency-overlays.json`

常见调整点：

- `top_k`：候选数量
- `max_select`：最多可选 overlay 数（建议保持 2）
- `stage_fallbacks`：无关键词命中时的兜底候选（按阶段）
- `overlays[].keywords`：每个部门的关键词集合（中英文均可）

## 与 VCO overlay 开关的关系

`config/prompt-overlay.json` 已启用：

- `enabled: true`
- `mode: advice-only`

当前实现是“脚本生成建议 + 人工确认 + 手动注入”，不需要改动任何插件源码或 hook。
