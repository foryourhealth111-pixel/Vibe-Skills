# VCO Docs

该目录用于存放 VCO 运行治理、overlay 集成与可观测性文档。

- `agency-agents-overlay.md`：将 agency-agents 的“部门专家”以 advice-only prompt overlay 方式接入 VCO（自动建议 → 人工确认 → 注入）。
- `gitnexus-overlay.md`：将 GitNexus 作为“代码理解/变更感知”的底层能力，以 advice-only overlay 方式接入（支持与部门 overlay 组合）。
- `gitnexus-mcp-integration-draft.md`：GitNexus MCP（工具层）接入草案：配置方式、治理边界、fallback、rollout 分阶段方案。
- `gitnexus-execution-checklist.md`：按步骤接入 GitNexus MCP 到 Codex CLI，并跑通索引/验证/VCO overlay 注入的执行清单。
