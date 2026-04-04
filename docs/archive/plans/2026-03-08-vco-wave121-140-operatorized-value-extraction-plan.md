# VCO Wave121-140 Operatorized Value Extraction Plan

- Up: [../README.md](../README.md)
- Index: [README.md](README.md)

**Date:** 2026-03-08
**Mode:** XL / unattended / vibe-first
**Planning Goal:** 在 Wave101-120 已经完成“source cluster 识别、剩余价值切片、禁止事项固定”之后，把后续优质项目榨取推进到 **可运行、可评测、可观测、可回退、可 promotion** 的 operator-grade 阶段；先补齐 executable eval / cockpit / preview / fixture migration / source mapping，再决定哪些资产值得继续上升。

## 1. Why Wave121-140

Wave101-120 解决的是“还剩哪些价值值得榨取”；Wave121-140 要解决的是“这些价值怎样真正落到运行面，而不是继续停留在 contract / note / scorecard 层”。

当前 post-Wave120 的核心缺口已经很清楚：

1. **eval 仍偏合同化**：很多 gate 已能证明 policy / asset 存在，但还不足以给出可比较、可回归、可复跑的 executable eval 结果。
2. **cockpit 仍偏摘要化**：当前 dashboard 以计数为主，还不能直接告诉 operator 哪个 plane 缺 replay、哪个 promotion 被哪条 gate 阻塞、哪个 release 仍 stop-ship。
3. **高风险 operator 缺 preview 一致性**：`sync` / `release` / `publish` 这类写入动作，还没有完全统一的 `Precheck -> Preview -> Apply -> Postcheck` 语义。
4. **outputs boundary Stage 2 尚未完成**：历史 tracked outputs 仍有 fixture / runtime 语义混叠，不利于后续把 evidence bundle 做干净。
5. **仍有未入账来源**：`mem0`、`Letta`、`browser-use`、`Agent-S` 已进入 value-ops board，但还没有完整进入 ledger / re-audit matrix 的制度化映射；在 `forbid_unmapped_absorption = true` 的前提下，这是必须先补的入口缺口。
6. **多个来源已被吸收，但尚未 operatorized**：`Prompt-Engineering-Guide`、connector ecosystem、role-pack / skill corpus、discovery corpora 仍有高价值切片停留在 `shadow`、`partial_absorption`、`tracked_corpus`。

因此，Wave121-140 的关键词不是“新增更多来源”，而是：

- **先映射、再运行化**：先补齐 ledger / matrix / slug 对齐，再把剩余价值变成 executable eval、可回退 SOP、可读 dashboard；
- **再 bounded promotion**：只有具备 eval + replay + rollback + board evidence 的切片，才有资格进入更高 stage；
- **最后 closure**：明确哪些项目价值已榨到 ceiling、哪些继续保留 shadow/reference、哪些应 retirement/parking。

## 2. Wave121-140 Guardrails

1. **Single control plane**：VCO 仍是唯一 orchestrator、唯一默认 execution owner、唯一 canonical truth-source。
2. **Canonical-first only**：所有改动都必须发生在 canonical root，再走 `sync-bundled-vibe.ps1` 与 parity/freshness gates；禁止 bundled-first / nested-first。
3. **Unmapped absorption is forbidden**：任何新吸收都必须先进入 ledger / matrix / board 的制度化映射；不允许“先做实现、后补登记”。
4. **Preview before write**：任何高风险写入 operator 在进入 wider rollout 前，都必须具备统一 preview / dry-run / machine-readable advice 语义。
5. **Executable eval before promotion**：仅有 contract / note / gate 存在不算“已榨干价值”；进入 promotion 前必须有可复跑的 eval 或 stress pack。
6. **Replay + rollback before widening**：browser / desktop / connector / memory 这类高风险面，没有 replay_handle、rollback_command、kill switch 证据，不得 widen。
7. **No raw catalog import**：`awesome-*`、`claude-skills`、`antigravity-awesome-skills`、`awesome-mcp-servers` 等一律只做 selective harvest，不得整库导入。
8. **No second runtime**：`browser-use`、`Agent-S`、`agent-squad`、`awesome-claude-code-subagents`、`activepieces`、`composio` 都不能成为第二运行时或第二默认 owner。
9. **No new tracked outputs**：Wave123 之后不允许再把新的 runtime outputs 留在版本控制里；需要保留的比较样本必须迁移为 `references/fixtures/**`。
10. **Dashboard must point back to evidence**：cockpit 只能聚合已有 board / gate / release artifacts，不得发明平行状态。
11. **Workstream-first planning**：后续 wave 一律优先按 source cluster / workstream 切，而不是继续按单仓库逐个堆叠，避免重复资产与重复治理。

## 3. Workstream-First Planning Rule

Wave121-140 继续以 `config/upstream-value-ops-board.json` 的 6 个 workstream 为主轴，而不是继续用“按项目逐个榨取”的方式扩张：

| Workstream | Source projects | Target plane | Main waves | Planning rule |
| --- | --- | --- | --- | --- |
| `memory-and-policy` | `mem0`, `Letta` | `memory/policy` | `121`, `126`, `136`, `138` | 先完成 ledger/matrix 准入，再做 memory eval / policy contract，不允许绕过 mapping |
| `browser-and-desktop` | `browser-use`, `Agent-S` | `browser/desktop` | `121`, `128`, `129`, `136` | 优先做 openworld / replay executable eval，不提升为第二运行时 |
| `connector-catalog` | `awesome-mcp-servers`, `activepieces`, `composio` | `connector admission` | `130`, `136`, `138` | 共享一套 sandbox simulation / rollback / replay 资产，避免每个仓库单独造轮子 |
| `skill-role-ecosystem` | `claude-skills`, `awesome-agent-skills`, `awesome-claude-code-subagents`, `antigravity-awesome-skills`, `agent-squad`, `awesome-claude-skills-composio` | `role/skill governance` | `132`, `133`, `138` | 先 dedup 再 harvest，所有价值都落入 role grammar / handoff / quality heuristics |
| `prompt-and-vibe-assets` | `Prompt-Engineering-Guide`, `awesome-vibe-coding`, `vibe-coding-cn` | `prompt intelligence / discovery corpus` | `121`, `127`, `134`, `138` | PEG 做 pattern/eval，vibe corpora 只做 discovery/eval notes，不进入控制面 |
| `document-and-eval-productization` | `docling`, `awesome-ai-agents-e2b` | `document plane / eval corpus` | `131`, `134`, `138` | 继续做 contract_slice / benchmark_slice / eval reference，不重复造 plane |

## 4. Upstream Coverage Matrix (19 projects)

| Project | Current posture | Remaining high-value slice | Planned waves | Hard ceiling / no-go |
| --- | --- | --- | --- | --- |
| `docling` | `canonical_contract` | document benchmark v2、failure taxonomy tightening、contract regression | `131`, `138` | 不建立第二 document plane |
| `awesome-mcp-servers` | `catalog_governed` | connector admission scorecards、sandbox simulation coverage、catalog risk slices | `130`, `138` | 不自动安装 catalog，不把列表变 runtime marketplace |
| `awesome-vibe-coding` | `tracked_corpus` | prompt/discovery pattern cards、eval prompts、workflow heuristics | `127`, `134`, `138` | 不建立第二 vibe methodology control plane |
| `awesome-ai-tools` | `tracked_corpus` | scouting scorecards、candidate triage cards、tool intake heuristics | `134`, `138` | 不把 discovery list 直接变产品面 |
| `claude-skills` | `partial_absorption` | skill distillation rules、schema heuristics、quality bar enrichment | `133`, `138` | 不镜像整个 skill corpus |
| `agent-squad` | `tracked_corpus` | role grammar、team composition、handoff stress patterns | `132`, `138` | 不引入第二 orchestrator |
| `vibe-coding-cn` | `tracked_corpus` | multilingual workflow glossary、中文 discovery/eval prompts | `127`, `134`, `138` | 不绕过 canonical vocabulary governance |
| `awesome-agent-skills` | `tracked_corpus` | selective skill harvest、dedup-aware quality scoring | `133`, `138` | 不 raw-import catalog |
| `awesome-claude-code-subagents` | `tracked_corpus` | reviewer / implementer archetypes、subagent handoff scorecards | `132`, `133`, `138` | 不形成第二 subagent runtime |
| `antigravity-awesome-skills` | `partial_absorption` | anti-pattern heuristics、quality gate patterns、skill review rules | `133`, `138` | 不 wholesale import |
| `activepieces` | `shadow_governed` | connector rollback templates、piece-class risk mapping、action replay boundaries | `130`, `136`, `138` | 不成为默认 automation control plane |
| `composio` | `shadow_governed` | action ledger enrichments、confirm-gated write taxonomy、rollback semantics | `130`, `136`, `138` | 不吸收 execution ownership |
| `awesome-claude-skills-composio` | `partial_absorption` | hybrid skill risk review、connector-skill separation heuristics | `133`, `134`, `138` | 不默认产品化 Composio-style skills |
| `Prompt-Engineering-Guide` | `partial_absorption` | prompt pattern benchmark、audited cards、scenario eval matrix | `127`, `134`, `138` | 不替代 VCO prompt/router rules |
| `awesome-ai-agents-e2b` | `tracked_corpus` | discovery/eval scenario seeds、document/eval reference corpus | `131`, `134`, `138` | 不吸收其 runtime assumptions |
| `mem0` | `board_only_until_mapped` | memory write admission quality、compaction / retention evidence、memory quality eval | `121`, `126`, `136`, `138` | 不形成第二 memory truth-source |
| `browser-use` | `board_only_until_mapped` | browser openworld scenario corpus、provider ranking、fallback traces | `121`, `128`, `136`, `138` | 不形成第二 browser orchestrator |
| `Agent-S` | `board_only_until_mapped` | desktop replay taxonomy、failure bucket enrichment、shadow evidence pack | `121`, `129`, `136`, `138` | 不成为默认 desktop owner |
| `Letta` | `board_only_until_mapped` | policy conformance、memory block lifecycle、persona-state separation contracts | `121`, `126`, `136`, `138` | 不形成自治 memory plane |

## 5. Program Metrics

| Metric | Target by Wave140 | Meaning |
| --- | ---: | --- |
| `explicit_project_coverage` | `19 / 19` | 所有上游项目都被映射到具体 wave，而不是继续停留在抽象 backlog |
| `unmapped_upstream_sources` | `0` | `mem0` / `Letta` / `browser-use` / `Agent-S` 等 board-only 来源完成 ledger/matrix/slug 对齐 |
| `slug_alias_conflicts` | `0` | ops board、ledger、matrix 对同一来源不再出现多套 slug / 命名 |
| `previewable_high_risk_operators` | `100%` | `sync / release / publish / rollout` 等高风险 operator 都具备统一 preview 语义 |
| `actionable_cockpit_panel_coverage` | `100%` | `freshness / promotion / replay / rollback / release` 五个面板都能输出结论 + 证据指针 + gap list |
| `executable_eval_clusters` | `>= 6` | memory、prompt、browser、desktop、connector、document/eval 至少六个 cluster 有可复跑 eval |
| `fixture_migration_stage2_complete` | `1.0` | allowlisted legacy outputs 已迁移为 `references/fixtures/**` 或明确退役 |
| `promotion_candidates_with_eval_replay_rollback` | `>= 5` | 至少五个候选切片具备 promotion 所需完整证据链 |
| `duplicate_runtime_owner_introductions` | `0` | 全程未引入第二默认 router / orchestrator / execution owner |
| `board_linked_evidence_surfaces` | `100%` | board / cockpit / release 三层都能回链到具体 docs / gates / artifacts |

## 6. Stage Structure

### Stage A — Source Mapping + Operator Runway (Wave121-125)
先把 unmapped source、slug alias、preview、fixture、cockpit、execution lock 这条跑道补齐；如果这一段不做，后面的“继续榨取”仍然会落在不可审计的资产层。

### Stage B — Memory / Prompt / Browser / Desktop Executable Eval (Wave126-129)
把四个最容易被误判为“已经吸收完成”的高价值 cluster 全部推进到可复跑 eval / stress pack。

### Stage C — Connector / Document / Role / Skill Operatorization (Wave130-133)
把 connector、document、role、skill 这四类剩余价值从 note / contract 推到 benchmark / handoff / dedup / rollback 的 operator-grade。

### Stage D — Discovery / Lifecycle / Promotion / Freshness (Wave134-137)
把 discovery intake、capability retirement、bounded promotion、install/runtime freshness 绑成一条完整的收口链，确保只有真正值得 widen 的资产继续上升。

### Stage E — Re-Audit / Board / Release / Closure (Wave138-140)
刷新 re-audit matrix、candidate quality board、release evidence bundle，并形成 Wave141+ 的进入条件。

## 7. Wave121-140 Backlog

| Wave | Lane | Title | Goal | Primary sources | Canonical outputs | Evidence / gate |
| --- | --- | --- | --- | --- | --- | --- |
| 121 | governance | upstream mapping / slug alignment | 把 `mem0`、`Letta`、`browser-use`、`Agent-S` 正式纳入 ledger / matrix，并解决 board vs ledger vs matrix 的命名漂移 | `mem0`, `Letta`, `browser-use`, `Agent-S`, `Prompt-Engineering-Guide`, `awesome-ai-agents-e2b` | ledger refresh、matrix delta、slug alias policy、mapping notes | `vibe-upstream-corpus-manifest-gate`, `vibe-upstream-reaudit-matrix-gate` |
| 122 | governance | operator preview contract v1 | 把高风险 operator 统一到 `Precheck -> Preview -> Apply -> Postcheck` 语义，并输出 machine-readable preview summary | cross-cutting | `docs/governance/operator-preview-contract-governance.md`、preview receipts、operator contract notes | operator preview contract gate |
| 123 | governance | outputs fixture migration stage2 | 将 allowlisted tracked outputs 迁移到 `references/fixtures/**`，清晰分离 runtime evidence 与 compare baselines | cross-cutting | fixture migration map、updated boundary policy、fixture index | `vibe-output-artifact-boundary-gate` + stage2 migration report |
| 124 | ops | ops cockpit v2 actionable panels | 把 cockpit 从“摘要计数”升级为“结论 + blocker + evidence pointer”面板集 | all promoted planes | dashboard v2、panel contract schema、gap matrix | `vibe-ops-cockpit-gate`, `vibe-ops-dashboard-gate` |
| 125 | verify | gate family convergence / execution-lock hardening | 收敛 verify family、显式 execution-context 状态，让 operator 不再在错误树上生成“看似正常”的 evidence | cross-cutting | gate family index v2、execution-context status asset、runner notes | `vibe-gate-reliability-gate` + family convergence audit |
| 126 | memory | mem0 + Letta executable memory eval | 把 memory 相关 gate 升级为可复跑质量评测：write admission、compaction、persona-state separation | `mem0`, `Letta` | memory eval fixtures、quality scoreboard、contract delta notes | `vibe-memory-quality-eval-gate` + memory executable eval pack |
| 127 | prompt | prompt pattern benchmark pack | 将 Prompt-Engineering-Guide 与中英 vibe corpus 的剩余价值沉淀为 audited prompt cards + benchmark matrix | `Prompt-Engineering-Guide`, `awesome-vibe-coding`, `vibe-coding-cn` | prompt benchmark matrix、bilingual prompt cards、glossary addenda | `vibe-prompt-intelligence-eval-gate` + prompt benchmark report |
| 128 | browser | browser openworld executable eval | 把 `browser-use` 的场景价值变成 provider ranking、fallback traces、可回归 openworld browser eval | `browser-use` | browser fixtures、provider ranking note v2、fallback trace pack | `vibe-openworld-runtime-eval-gate` + browser openworld eval |
| 129 | desktop | desktop replay executable eval | 把 `Agent-S` 价值落成 desktop shadow replay stress pack 与 failure bucket taxonomy v2 | `Agent-S` | desktop replay scenarios v2、failure taxonomy enrichments、shadow evidence bundle | `vibe-desktopops-replay-gate` + desktop replay eval |
| 130 | connector | connector rollback simulation v2 | 强化 connector sandbox simulation、rollback drill、replay_handle / rollback_command 质量 | `awesome-mcp-servers`, `activepieces`, `composio` | connector simulation v2、rollback drill pack、risk-tier map v2 | `vibe-connector-sandbox-simulation-gate`, `vibe-connector-action-ledger-gate` |
| 131 | document/eval | document benchmark v2 | 继续榨取 `docling` 的 benchmark / taxonomy 价值，并引入 discovery/eval corpus 做对比基线 | `docling`, `awesome-ai-agents-e2b` | document benchmark v2、failure taxonomy v2、eval reference pack | `vibe-document-plane-benchmark-gate`, `vibe-docling-contract-v2-gate` |
| 132 | role-pack | role handoff stress pack | 把 `agent-squad` / `awesome-claude-code-subagents` 的剩余价值沉淀为 role grammar v2 与 handoff stress patterns | `agent-squad`, `awesome-claude-code-subagents` | role grammar v2、handoff scorecard、team composition stress notes | `vibe-role-pack-v2-gate` + role handoff stress report |
| 133 | skill-corpus | selective skill harvest / dedup v3 | 在 dedup 前提下继续榨取 skill corpus，但只沉淀 schema、heuristics、anti-pattern、quality rules | `claude-skills`, `antigravity-awesome-skills`, `awesome-agent-skills`, `awesome-claude-skills-composio` | harvest matrix v3、dedup notes v3、skill quality heuristics pack | `vibe-capability-dedup-gate` + skill harvest review |
| 134 | discovery | discovery intake / scouting v2 | 把各类 `awesome-*` 发现面压成 candidate scoring queue，而不是继续堆运行面想象 | `awesome-ai-tools`, `awesome-ai-agents-e2b`, `awesome-vibe-coding`, `vibe-coding-cn`, `Prompt-Engineering-Guide` | intake scorecard v2、scouting backlog、multilingual discovery notes | `vibe-discovery-intake-scorecard-gate` |
| 135 | lifecycle | capability retirement / ceiling enforcement | 明确哪些上游价值已榨到 ceiling、哪些保留 shadow/reference、哪些应 retirement/parking | all upstream-derived surfaces | lifecycle updates、retirement register、ceiling enforcement notes | `vibe-capability-lifecycle-gate` + retirement audit |
| 136 | promotion | bounded soft-rollout package v2 | 只为已经具备 eval + replay + rollback + kill switch 的切片生成 bounded promotion proposal | `mem0`, `Letta`, `browser-use`, `Agent-S`, connector slices | rollout proposals v2、operator SOPs、kill switch receipts | `vibe-rollout-proposal-boundedness-gate` |
| 137 | runtime | install/runtime/operator freshness v2 | 把 promotion 后的 canonical / bundled / installed runtime / cockpit freshness 重新绑紧 | cross-cutting | install SOP v2、freshness receipt schema v2、runtime drift summary | `vibe-installed-runtime-freshness-gate`, `vibe-release-install-runtime-coherence-gate` |
| 138 | audit | upstream re-audit matrix v4 | 基于 Wave121-137 的真实落地结果刷新 19 项项目的 absorbed / remaining / ceiling 状态 | all upstream sources | re-audit matrix v4、value ledger refresh、remaining-value memo | `vibe-upstream-reaudit-matrix-gate` |
| 139 | board | candidate quality board v3 | 对齐 promotion board、candidate quality board、cockpit panels 的 stage / blocker / next stage 语义 | all promoted surfaces | board v3、blocker summary、stage mapping notes | `vibe-candidate-quality-board-gate`, `vibe-promotion-scorecard-gate` |
| 140 | closure | Wave121-140 release / closure bundle | 把 operator / eval / promotion 证据打包成可审计 closure，并生成 Wave141+ 入口 memo | all stage outputs | release bundle v4、closure report、Wave141+ memo | release evidence bundle gate + Wave121-140 closure gate |

## 8. Priority Order

### P0 — 必须先推进

- **Wave121-125**：不先补齐 mapping / preview / fixture / cockpit / execution-lock，后面任何“继续榨取”都只会再制造一层不可操作资产。
- **Wave126-129**：memory / prompt / browser / desktop 是当前最有价值、也最容易被误判为“已经吸收完成”的四个 cluster，必须先把 executable eval 做实。

### P1 — 跑道稳定后推进

- **Wave130-133**：connector / document / role / skill 是继续榨取的第二批主战场，但必须建立在 P0 的 operator + eval 跑道之上。

### P2 — 最后收口

- **Wave134-140**：discovery intake、retirement、bounded promotion、freshness、re-audit、board、closure 是收官层；如果前面没有足够证据，这一层只会变成“看起来完整”的板子工程。

## 9. Explicit Non-Goals

- 不新增新的顶层 plane。
- 不把任何 discovery / catalog 项目变成默认 runtime surface。
- 不把 `browser-use`、`Agent-S`、`agent-squad`、`activepieces`、`composio` 升级成第二控制面。
- 不在没有 executable eval 的前提下宣称“某来源价值已经榨干”。
- 不通过 bundled-first / nested-first 修改去“加速”规划落地。
- 不继续把历史 compare baseline 混放在 `outputs/**` 里。
- 不让 cockpit 生成脱离 gate / board / release evidence 的平行状态。
- 不绕过 ledger / matrix / board 做“未入账吸收”。

## 10. Definition of Ready

任一 Wave121-140 子 wave 在开始前，至少必须满足：

- 已明确它覆盖哪些上游项目与哪些 remaining value slice；
- 已明确 canonical 输出路径（`docs / config / references / scripts / outputs` 哪些会变化）；
- 已明确依赖的 gate / board / release artifact；
- 已明确失败时回退到哪个 stage、哪个 shadow posture、哪个 operator command；
- 已明确它不会引入第二 runtime / 第二 owner / 第二 router；
- 若涉及上游来源，已确认 slug / lane / status 已经进入 ledger / matrix / board 的统一通道。

## 11. Definition of Done

Wave121-140 规划层面的完成，要求：

- 19 个上游项目都有明确的后续榨取路径与 ceiling；
- `mapping -> runway -> executable eval -> operatorization -> bounded promotion -> closure` 的顺序被固定；
- 当前最关键的 post-W120 缺口（unmapped sources、preview、cockpit、fixture migration、executable eval）都被映射到早期 wave；
- 每个 wave 都有 `goal + sources + canonical outputs + evidence` 四元组；
- 规划本身不会重新引入 catalog raw-import、bundled-first、second-runtime、unmapped absorption 等旧漂移风险。
