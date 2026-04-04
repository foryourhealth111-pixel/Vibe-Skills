# review-ready: wave15-18-portfolio

## decision_context
- Wave15–18 的目的不是继续扩大默认吸收面，而是把 watch lane、eval slicing、XL operator、release handoff 变成 board-readable 资产。
- 本 memo 作为 promotion prep 使用，回答“哪些项目值得继续推进到 review-ready / pilot-ready 的讨论层”，而不是直接批准 promotion。
- reviewed upstream artifacts:
  - `docs/archive/root-docs/watch-portfolio-rationalization.md`
  - `docs/eval-slicing-operationalization.md`
  - `docs/design/xl-operator-playbook.md`
  - `docs/archive/root-docs/wave15-18-execution-backlog.md`

## candidate_snapshot
- surface: `portfolio`
- scope: `watch lane closure + remaining value operationalization`
- current approved state: `advisory / watch-first`
- proposed board posture: `review-ready for discussion, rollback-ready for any pilot, no default surface expansion`
- watch candidates in scope:
  - `awesome-ai-tools`
  - `awesome-mcp-servers`
  - `activepieces`
  - `composio`
  - `awesome-vibe-coding`
  - `awesome-agent-skills`
  - `awesome-claude-skills-composio`
  - `awesome-ai-agents-e2b`

## dedup_review
- `awesome-ai-tools` 的剩余价值已被收缩到 eval slicing 与 governance taxonomy，不与 live routing 重复。
- `awesome-mcp-servers` 仅保留 registry / intake 价值，不与 approved MCP allowlist 混淆。
- `activepieces` 与 `composio` 仅保留 project-scoped pilot 价值，避免形成第二默认 control plane。
- `awesome-agent-skills`、`awesome-claude-skills-composio`、`awesome-ai-agents-e2b` 继续保持 hold-first，直到真实 gap 出现。
- `awesome-vibe-coding` 被压缩为 operator playbook 价值，不作为新的默认 command family。

## rubric_summary
- active-like remaining value exists in: `awesome-ai-tools`, `awesome-mcp-servers`, `awesome-vibe-coding`
- gated pilot value exists in: `activepieces`, `composio`
- hold bias remains strongest for: `awesome-agent-skills`, `awesome-claude-skills-composio`, `awesome-ai-agents-e2b`
- suggested board framing:
  - `review-ready`: governance-facing operationalization only
  - `pilot`: rollback-first and project-scoped only
  - `hold`: no new absorption until a verified gap appears

## routing_impact
- affected packs: none directly
- affected router defaults: none
- confirm_required expectations: unchanged
- default-surface change: explicitly disallowed in this memo
- live router mutation: not authorized by this memo

## verification
- required artifacts:
  - `outputs/governance/watch-portfolio/watch-portfolio-review.json`
  - `outputs/verify/watch-portfolio-gate.json`
  - `outputs/governance/eval-slicing/eval-slicing-catalog.json`
  - `outputs/governance/xl-operator/xl-operator-checklist.json`
  - `outputs/verify/wave15-18-consistency-gate.json`
- required gates:
  - existing governance scoreboard remains `review-required`, not auto-promoted
  - no new artifact claims `default surface` widening
- open board questions:
  - whether `activepieces` / `composio` deserve a pilot lane in the next quarter
  - whether `awesome-mcp-servers` should stay review-ready or drop back to hold after allowlist snapshotting

## rollback
- if any downstream reader interprets this memo as promotion approval, rollback posture is immediate:
  - revert the claim to `watch/advisory`
  - require a full promotion review using `references/promotion-review-template.md`
  - require a release packet with explicit degraded mode and retro trigger
- rollback owner: governance board chair
- maximum acceptable blast radius: documentation and reporting artifacts only
