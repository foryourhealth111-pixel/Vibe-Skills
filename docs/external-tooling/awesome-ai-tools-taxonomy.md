# Awesome AI Tools Taxonomy (Reference-Only)

本文件将 `awesome-ai-tools` 作为 **外部工具景观的分类法（taxonomy）与风险信号源** 使用。

目标：
- 帮助 VCO 更稳定地识别“用户在要哪类能力”（意图层），而不是“推荐某个具体产品”（工具层）。
- 为 `MCP vs skill vs manual` 的接入决策提供风险分层与治理提示。

非目标（明确不做）：
- 不把条目转成 VCO skills
- 不把条目写进 `references/tool-registry.md`（该文件只记录 VCO 已集成且可验证的工具面）
- 不输出“推荐列表”（awesome 清单经常包含商业/跟踪链接，不能当作默认推荐层）

证据来源（只读镜像）：
- `third_party/vco-ecosystem-mirror/awesome-ai-tools/README.md`
- `third_party/vco-ecosystem-mirror/awesome-ai-tools/marketing.md`
- `third_party/vco-ecosystem-mirror/awesome-ai-tools/IMAGE.md`

---

## Taxonomy Schema（意图层）

顶层按“交付物/媒介”划分（与用户意图天然同构）：

- **Text**：模型/聊天/搜索/写作/效率/扩展/总结/翻译等
- **Code**：IDE 辅助/代码生成/评审/测试/DevOps 等
- **Image**：生成/编辑/修复/风格化/素材等
- **Video**：生成/剪辑/字幕/增强等
- **Audio**：转写/配音/降噪/语音合成等
- **Other**：Agent 平台、自动化、数据处理、文档处理等
- **Learning**：学习资源与教程（不是工具能力）

> 关键点：taxonomy 只回答“是什么类型的需求”，不回答“用哪个工具”。具体工具只能在 `manual reference` 或经过 MCP/skill 准入后进入 VCO 工具面。

---

## VCO 如何使用这份 taxonomy

### 1) 作为 intent 词表的“上游信号”

将顶层/子类名作为路由增强信号（高层关键词即可），例如：
- meeting assistant / note-taking
- voice cloning / voiceover
- image editing / background removal
- local search / private search

> 注意：只引入**类别级关键词**，不要引入具体产品名（否则引入噪声与时效性风险）。

### 2) 作为风险信号（risk tiers）

taxonomy 中某些类别天然高风险，应该触发 VCO 的 `confirm_required` 或“manual-only”：

- **Meeting assistants / Phone calls**：涉及录音、外呼、客户对话、第三方系统动作，必须显式确认 + 留痕
- **Account automation / Social posting**：外部副作用强，且可能不可逆
- **Anything with credentials**：必须走 MCP/平台鉴权治理，不允许把 token 写入 prompt

---

## Risk Tiers（用于治理，而非推荐）

建议用 4 轴定义风险等级（可用于文档与路由 advisory）：

1) **数据敏感度**
- Low：公开/非个人数据
- Medium：内部文档/业务数据
- High：PII、账号、医疗、财务、受监管数据

2) **动作可逆性**
- Read-only：只读
- Transform：本地变换、可回滚
- Destructive：修改/删除/发布/发信等外部副作用

3) **部署形态**
- Local/Self-host：可控、可审计
- Cloud/SaaS：依赖供应商策略与变更

4) **分发偏置（链接治理）**
- 带 `utm_*/ref/affiliate` 的链接：默认降权为“参考”，不进入任何默认推荐层

---

## Mapping：taxonomy → 接入路径（不含具体工具）

| 情况 | 推荐接入路径 | 说明 |
|---|---|---|
| 有稳定 API + 可用 schema + 可测试 | MCP | 走 `docs/external-tooling/mcp-vs-skill-vs-manual.md` 的 MCP 准入门槛 |
| 无稳定 API / 主要靠 UI / 需要人工登录 | Manual | 只写 “如何做/注意事项/风险” 的 reference，不宣称 VCO 可自动化 |
| 重复出现的本地流程（可复现） | Skill | 以脚本 + 协议封装（有验证命令），不绑定具体 SaaS |

---

## 维护方式（防止冗余）

- taxonomy 只做“类别级”更新，优先保持稳定
- 任何想把具体工具接入 VCO 的变更，必须先走：
  - `docs/governance/ecosystem-absorption-dedup-governance.md`（去重流程）
  - `docs/external-tooling/mcp-vs-skill-vs-manual.md`（准入门槛）
