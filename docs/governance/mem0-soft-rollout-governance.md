# mem0 Soft Rollout Governance (VCO / Wave65)

## 1. 文档目的

Wave65 的目标不是让 `mem0` 成为新的默认 memory plane，而是把它从 `opt-in backend` 推进成 **可审计、可回退、可 gate 的 soft rollout pilot**。

soft rollout 的含义只有两个：

- 允许在严格 admission 下写入 preference payload
- 仍然保持 `VCO` 与 canonical owners 不变

## 2. 定位结论（必须保持不变）

- `mem0` 仍然只是 `optional_external_preference_backend`
- soft rollout 仍然是 `opt-in`
- `mem0` 不得记录 route assignment、primary session state、canonical project decision
- `mem0` 写入失败时必须降级为 advisory-only，而不是扩大写权限

## 3. Admission pipeline

### 3.1 classify

先判断 payload 是否属于允许的 preference lane：

- `preference`
- `style_hint`
- `recurring_constraint`
- `output_preference`

### 3.2 reject early

若 payload 命中以下任一类型，必须立即 deny write：

- `route_assignment`
- `canonical_project_decision`
- `primary_session_state`
- `security_secret`
- `build_truth`

### 3.3 admit with evidence

soft rollout 允许写入时，必须同时具备：

- `stability_window`
- `user_confirmation` 或等价 opt-in evidence
- `policy_version`
- `evaluation_id`
- `fallback_owner`

若候选 payload 来自 code fence 中的 JSON 或其他结构化块，admission pipeline 必须保留原始 `candidate_value` 供审计，不得先做“提取失败即丢弃”的静默降损。

### 3.4 audit and rollback

每次 soft write 都必须留下 audit 痕迹，并且能通过 kill switch 立即停写。

## 4. Write classes

| Payload Type | 允许场景 | Soft rollout 要求 |
|---|---|---|
| `preference` | 长期偏好 | stability window + audit |
| `style_hint` | 重复输出风格偏好 | opt-in + audit |
| `recurring_constraint` | 稳定个人约束 | explicit confirmation |
| `output_preference` | 结构化输出格式偏好 | fallback owner 明确 |

## 4.1 Backend portability notes

- OpenAI-compatible embedder 的 `baseURL` 可以作为 `mem0` 的可选 backend compatibility 字段存在，但只属于 backend portability，不改变 Memory Runtime owner boundary。
- SQLite 落盘路径必须是 operator-controlled durable path；禁止把当前工作目录是否可写当作默认前提。
- 结构化 payload 的 fidelity 优先于便利性；code fence 内的内容如被分类为 preference candidate，必须在 admission 审核中原样可见。

## 5. Kill switch / rollback

### 5.1 Kill switch

以 `config/mem0-backend-policy.json` 为唯一 kill switch：

- `mode = shadow`：只分类、不写入
- `enabled = false`：直接停用 backend

### 5.2 Rollback-first

若出现以下情况，必须立即回退到 `shadow`：

- payload 语义不清
- 同时包含 preference 与 project truth
- 出现 secret / build / route 相关字段
- gate 或审计链失败

## 6. 必需资产

- `config/mem0-backend-policy.json`
- `config/memory-runtime-v3-policy.json`
- `references/mem0-write-admission-contract.md`
- `scripts/verify/vibe-mem0-softrollout-gate.ps1`

## 7. 验证方式

```powershell
pwsh -File .\scripts\verify\vibe-mem0-softrollout-gate.ps1
```

## 8. 完成定义（Definition of Done）

满足以下条件，才视为 Wave65 soft rollout pilot 准备完成：

- `mem0` policy 明确限制为 preference lane
- write admission contract 明确列出允许类、拒绝类、审计字段
- soft rollout 文档明确 `shadow -> soft` 是 operator opt-in，而不是自动升级
- kill switch、rollback、audit trail 都已写清楚
- gate 能验证 policy、contract、doc 的关键不变量
