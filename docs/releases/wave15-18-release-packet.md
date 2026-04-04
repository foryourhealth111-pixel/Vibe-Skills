# Wave15–18 Release Packet

## Packet Metadata

- candidate id / surface / cluster: `wave15-18-portfolio / portfolio / cross-cluster`
- linked promotion review: `references/promotion-memos/wave15-18-promotion-prep.md`
- owner and review date: `governance-board-chair / 2026-03-07`
- requested action: `review-ready packaging only`

## change-summary

Wave15–18 将前期 15 个高价值项目的剩余价值收缩为四类正式资产：

1. watch lane decision register；
2. eval slicing policy and catalog；
3. XL operator priority + checkpoints；
4. consistency / packet / rollback handoff assets。

本 release packet 的目标不是批准 promotion，而是确认这些资产已经足够完整，能够支撑下一轮 board review，同时继续保持 `advisory only`, `shadow first`, `rollback first` 的边界。

明确 scope boundary：

- allowed: `advisory only`, `review-ready`, `pilot-only`, `rollback-ready`
- not allowed: `default surface expansion`, `live router mutation`, `connector auto-enable`

## evidence

- latest scoreboard linked: `outputs/governance/scoreboard/governance-scoreboard.json`
- latest candidate leaderboard linked: `outputs/governance/candidate-curation/candidate-curation-leaderboard.json`
- watch portfolio review: `outputs/governance/watch-portfolio/watch-portfolio-review.json`
- eval slicing catalog: `outputs/governance/eval-slicing/eval-slicing-catalog.json`
- XL operator checklist: `outputs/governance/xl-operator/xl-operator-checklist.json`
- overlap / risk evidence attached:
  - `docs/archive/root-docs/watch-lane-remaining-value-cases.md`
  - `references/candidate-case-files/remaining-value-case-matrix.md`

## gate-results

- prompt regression gate result included: existing governance baseline
- prompt intelligence gate result included: existing governance baseline with warning-aware posture
- tool governance gate result included: existing governance baseline
- skill metadata gate result included: existing governance baseline
- team contract gate result included: existing governance baseline
- candidate curation gate result included: existing governance baseline
- watch portfolio gate result included: `outputs/verify/watch-portfolio-gate.json`
- wave15-18 consistency gate result included: `outputs/verify/wave15-18-consistency-gate.json`
- warning-only gates explicitly acknowledged: `prompt-intelligence`

## owner-and-landing-zone

- named owner: `governance-board-chair`
- named rollback owner: `rollback-owner`
- landing zones documented:
  - `watch portfolio` → governance board / quarterly review
  - `eval slicing` → shadow evaluation / operator explanation
  - `XL operator checkpoints` → execution playbook / intake policy
  - `pilot candidates` → project-scoped control plane trials only
- next checkpoint / next review date assigned: `next quarterly portfolio review`

## degraded-mode

如果 Wave15–18 的任一新增资产在后续 board review 中被判定过度外推，则 degraded path 为：

- 保留文档和 case matrix；
- 撤销任何 `review-ready` 或 `pilot` 口径，降回 `watch / hold`；
- 继续允许 operator 参考这些材料，但不得据此执行 runtime widening。

Blast radius 限制：

- 只允许影响 documentation、reporting、board preparation；
- 不允许影响 live router、default packs、approved connectors。

## rollback-plan

- rollback trigger:
  - consistency gate fail
  - packet sections incomplete
  - board 发现 default-surface ambiguity
  - pilot proposal 缺少 degraded mode / rollback evidence
- concrete rollback steps:
  1. 将相关表述降回 `watch` 或 `hold`
  2. 更新 packet 和 promotion prep
  3. 重新运行 `watch-portfolio-gate` 与 `wave15-18-consistency-gate`
- evidence needed to reopen promotion:
  - fresh gates
  - explicit landing zone
  - no-default-surface ambiguity removed
- rollback communications / audit path:
  - governance board notes
  - updated memo and packet artifacts

## retro-trigger

- retro owner assigned: `release-steward`
- retro timing defined: `within 7 days of rollback or board rejection`
- retro artifact destination defined: `docs/releases/` follow-up note or governance retro
- auto-trigger conditions:
  - rollback executed
  - pilot rejected due to missing controls
  - drift between packet and policy detected
  - user/runtime harm caused by over-claiming readiness

## Final Gate

本 packet 只支持以下结论：

- `hold`
- `watch`
- `review-ready`
- `pilot-only`
- `rollback-ready`

在缺少正式 promotion review 与 board approval 之前，本 packet **不支持** `default-surface expansion`。
