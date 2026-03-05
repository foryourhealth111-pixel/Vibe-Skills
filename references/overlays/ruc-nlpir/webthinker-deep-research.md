## WebThinker 深度调研（advice-only）

适用：需要“多跳网页探索 + 可复核来源 + 结构化报告”的任务（例如技术调研/竞品调研/方案对比/最新信息核验）。

### 输出契约（必须有）

产物目录中至少包含：

- `report.md`（结论、证据、权衡、下一步）
- `sources.json`（所有 URL + 标题 + 访问时间 + 摘要片段）
- `trace.jsonl`（每一步 search/open/extract/decision 的可审计日志）

### 最小动作（Lite，无重依赖）

1) 初始化调研 run 目录：

- `python C:\Users\羽裳\.codex\skills\webthinker-deep-research\scripts\init_webthinker_run.py --topic "<问题>" --out outputs/webthinker`

2) 通过 `web.run` / `mcp__tavily` 搜索并打开页面，持续更新：

- `sources.json`：新增来源条目（不要丢 URL）
- `trace.jsonl`：每个动作一行（search/open/extract/decision）
- `notes.md`：按来源记录要点（可直接粘贴片段）
- `report.md`：边搜边写（think-search-and-draft）

3) 关键结论尽量做到 ≥2 来源交叉验证；不确定则显式标注。

### 失败回退

- 页面需要动态渲染/交互：用 `playwright`（或 `turix-cua` overlay）
- 信息过新/变化快：在 `sources.json` 记录访问日期并给出“再次核验”下一步

### 非目标（避免冗余）

- 只要 3 条引用：用 `research-lookup`
- 代码结构证据：用 GitNexus

