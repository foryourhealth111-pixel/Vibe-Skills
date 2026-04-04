# Cross-Plane Conflict Governance

## 目标

Wave26 为 `memory / prompt / browser / desktop` 四个吸收平面建立统一冲突治理规则，确保：

- `VCO` 仍是唯一控制面
- 不出现第二默认执行 owner
- 不出现第二 canonical memory truth-source
- advice、contract、provider、shadow 之间发生冲突时有稳定仲裁顺序

## 适用平面

| 平面 | plane_id | 角色定位 | 允许输出 | 明确禁止 |
|---|---|---|---|---|
| Memory | `memory-runtime-v2` | memory contract / preference backend boundary | memory contract、偏好后端建议、policy contract | 接管 route、接管 execution owner、成为第二 truth-source |
| Prompt | `prompt-intelligence` | prompt asset / risk advice | pattern cards、risk checklist、quality metadata | 改写 `selected.pack_id`、改写 `selected.skill`、形成第二 router |
| Browser | `browserops-provider` | browser provider suggestion | provider recommendation、`confirm_required` 建议、fallback hint | 成为第二 orchestrator、接管 route、默认替换 Playwright 基线 |
| Desktop | `desktopops-shadow` | desktop shadow contract | ACI contract、OpenWorld checklist、fallback plan | 成为默认执行 owner、隐式 promote、成为第二 orchestrator |

## 冲突仲裁总顺序

跨平面仲裁不是四平面彼此“平级投票”，而是固定优先级：

1. `user_explicit`
2. `vco_route`
3. `verification_gate`
4. `memory-runtime-v2`
5. `prompt-intelligence`
6. `browserops-provider`
7. `desktopops-shadow`

其中第 4-7 项是 Wave26 的平面优先级；在这四者内部采用：

- `memory` 高于 `prompt`
- `prompt` 高于 `browser`
- `browser` 高于 `desktop`

## 冲突类型与处理

### 1. authority overlap

多个平面同时试图影响 route、执行 owner 或 truth-source。

处理规则：
- 仅取更高优先级平面的建议
- 同时冻结低优先级平面的升级动作
- 回退到 `shadow` 解释模式，等待人工复核

### 2. contract contradiction

多个平面对同一任务输出互相矛盾的 contract。

处理规则：
- 优先采用更高优先级平面的 contract
- 保留冲突记录
- 不允许因此绕过 `VCO` 主路由

### 3. confirmation mismatch

一个平面要求 `confirm_required`，另一个平面希望自动推进。

处理规则：
- `confirm_required` 永远优先
- 不允许静默升级 side effect 风险

### 4. promotion mismatch

某平面已尝试进入更高 rollout 阶段，但相邻或上游平面仍存在 unresolved conflict。

处理规则：
- 升级冻结
- 回退为 `shadow` / `soft` 候选说明
- 要求走 promotion board 复核

## 执行边界

所有平面都必须满足以下硬约束：

- 不能改写 `VCO` 的 `grade / route / selected skill`
- 不能变成第二默认执行 owner
- 不能变成第二 memory canonical owner
- 不能在存在 unresolved conflict 时自动 promote

## 落地资产

- `config/cross-plane-conflict-policy.json`
- `scripts/verify/vibe-cross-plane-conflict-gate.ps1`
- `docs/promotion-board-governance.md`
- `scripts/verify/vibe-promotion-board-gate.ps1`

## 最小闭环判定

当以下条件同时成立时，可视为 Wave26 最小闭环完成：

- policy 明确表达四平面的内部优先级
- gate 能验证优先级、禁止项、冲突动作
- promotion board 明确引用 cross-plane policy
- pilot / rollout 不会绕过冲突治理直接升级
