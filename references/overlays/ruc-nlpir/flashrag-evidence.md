## FlashRAG 证据平面（advice-only）

适用：当你需要**从本地 VCO/vibe 文档与配置中**快速找到“可引用”的证据（path:line + snippet），用于解释路由/协议/治理规则来源。

### 最小动作（Lite）

1) 运行本地证据检索（BM25，stdlib-only）：

- `python C:\Users\羽裳\.codex\skills\flashrag-evidence\scripts\flashrag_evidence.py --query "<你的问题关键词>" --topk 8`

2) 把输出当作 P5 证据链使用：

- **[Command]**：上面的命令
- **[Output]**：top hits（包含 `path:line`）
- **[Claim]**：仅基于证据得出的结论

### 典型关键词

- “这条规则/阈值/策略在哪里定义？”
- “overlay / routing / confirm_required 的来源？”
- “protocols/think/do/review 的具体要求？”

### 失败回退

- 低覆盖：加大 `--topk` 或手动扩大语料 roots（用 `--roots <dir...>`）
- 精准定位：对目标文件做 `rg -n`（例如 `rg -n \"confirm_required\" C:\\Users\\羽裳\\.codex\\skills\\vibe\\config\\ -S`）

### 非目标（避免冗余）

- 代码依赖/执行流/影响面：用 GitNexus overlays
- 最新事实/新闻：用 web 搜索或深度调研（WebThinker）

