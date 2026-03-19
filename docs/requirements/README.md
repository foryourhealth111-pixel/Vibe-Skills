# Governed Requirements

This directory stores the frozen requirement document for each governed `vibe` run.

Rules:

- one requirement document per governed run
- execution plans must trace back to the requirement document, not raw chat history
- benchmark mode must record inferred assumptions explicitly
- execution should not widen scope without updating the frozen requirement

Filename contract:

- `YYYY-MM-DD-<topic>.md`

Primary policy:

- `config/requirement-doc-policy.json`

## Current Entry

- [`2026-03-20-readme-en-detail-and-github-branding-copy.md`](./2026-03-20-readme-en-detail-and-github-branding-copy.md): 冻结英文 README 细化与 GitHub 品牌文案补充；聚焦让 `README.en.md` 与中文版接近同等细节层级，并产出 `About / Topics / social preview` 可复用文案。
- [`2026-03-20-readme-emoji-layout-polish.md`](./2026-03-20-readme-emoji-layout-polish.md): 冻结 README 中文视觉润色；聚焦用少量 emoji 和版式节奏优化，让首页更精致、更有设计感但仍保持克制。
- [`2026-03-20-readme-differentiated-science-ai-strengths.md`](./2026-03-20-readme-differentiated-science-ai-strengths.md): 冻结 README 中文差异化强化；聚焦把生命科学、科研、AI 工程三块写得更有冲击力，更能体现仓库强势能力区。
- [`2026-03-20-readme-capability-subdomain-expansion.md`](./2026-03-20-readme-capability-subdomain-expansion.md): 冻结 README 中文能力矩阵第二轮细化；聚焦把 20 个能力域继续拆成更细的子领域说明，提升公开介绍的完整度与可读性。
- [`2026-03-20-readme-detailed-capability-matrix.md`](./2026-03-20-readme-detailed-capability-matrix.md): 冻结 README 顶部详细能力矩阵重写；聚焦把泛泛能力列表改成更完整、更自然的领域化总览表。
- [`2026-03-19-commit-and-rename-repo-to-vibe-skills.md`](./2026-03-19-commit-and-rename-repo-to-vibe-skills.md): 冻结“先提交当前改动、再把仓库改名为 `Vibe-Skills`”的执行需求；聚焦隔离 worktree 发布、GitHub rename 与 remote 更新验证。
- [`2026-03-19-repo-rename-to-vibe-skills.md`](./2026-03-19-repo-rename-to-vibe-skills.md): 冻结仓库更名为 `Vibe-Skills` 的规划需求；聚焦 GitHub rename 风险、路径影响评估与安全执行顺序。
- [`2026-03-19-public-readme-skill-activation-pain-point.md`](./2026-03-19-public-readme-skill-activation-pain-point.md): 冻结 README 的 skills 激活率低痛点补充；聚焦说明 `VCO` 生态如何通过路由与工作流治理提高能力激活率，并发布当前版本。
- [`2026-03-19-public-readme-capability-first-opening.md`](./2026-03-19-public-readme-capability-first-opening.md): 冻结 README 的 capability-first 开场重排；聚焦先展示整合规模、能力资源与覆盖领域，再在末尾收束到规范化理念。
- [`2026-03-19-public-readme-philosophy-and-source-image.md`](./2026-03-19-public-readme-philosophy-and-source-image.md): 冻结 README 的规范化哲学开场与作者原始 Gemini SVG 首屏展示；聚焦更直接的项目表达与更易懂的能力说明。
- [`2026-03-19-public-readme-anxiety-positioning-refresh.md`](./2026-03-19-public-readme-anxiety-positioning-refresh.md): 冻结 README 首页焦虑定位刷新；聚焦时代焦虑切入、系统回应强化与章鱼识别区移除。
- [`2026-03-19-public-readme-octopus-identity-zone.md`](./2026-03-19-public-readme-octopus-identity-zone.md): 冻结 README 章鱼识别区优化；聚焦无图片素材的可爱章鱼中枢品牌识别层。
- [`2026-03-19-public-readme-capability-snapshot.md`](./2026-03-19-public-readme-capability-snapshot.md): 冻结 README 能力快照展示区优化；聚焦纯 Markdown 的能力战报面板与首屏辨识度增强。
- [`2026-03-19-public-readme-propagation-optimization.md`](./2026-03-19-public-readme-propagation-optimization.md): 冻结 README 首屏传播优化目标；聚焦判断冲击、数字冲击、对比冲击联合叙事，以及安装入口后移。
- [`2026-03-19-public-docs-entrypoint-restructure.md`](./2026-03-19-public-docs-entrypoint-restructure.md): 冻结公开入口文档组重构目标；聚焦 README、manifesto、一步式安装入口与 quick-start 导航收敛。
- [`2026-03-15-linux-router-host-neutrality-and-route-quality-recovery.md`](./2026-03-15-linux-router-host-neutrality-and-route-quality-recovery.md): Frozen requirement baseline for Linux host-neutral router recovery, route quality repair, path-neutral cleanup, and proof-aligned release truth.
