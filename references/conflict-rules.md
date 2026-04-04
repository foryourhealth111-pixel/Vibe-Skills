# VCO Conflict Avoidance Rules

VCO 通过指令约束（非代码强制）防止多系统冲突。这些是规则而非建议——Claude 应严格遵守，但用户应知晓违反时不会有技术层面的完全阻断，因此必须依赖 docs/config/gates 共同治理。

All existing hooks remain active. VCO controls which tools/planes/providers are actively invoked.

## Rule 1: Agent Boundary

NEVER use multiple agent systems for the same control responsibility.

| Grade | Agent System | Reason |
|-------|-------------|--------|
| M | Single-agent tools | Lightweight, focused |
| L | Structured planning + bounded subagent workflow | Two-stage review and scoped execution |
| XL | Codex native team (`spawn_agent` family) + optional ruflo collaboration | Primary multi-agent orchestration |
| XL (degraded) | Codex native team only | When optional collaboration stack is unavailable |

Exceptions:
- `build-error-resolver`: may be used at any grade for build failures
- `security-reviewer`: may be used at any grade for security audits

Key rule:
- External projects such as `browser-use`, `Agent-S`, `Letta`, `mem0` **cannot** become a second orchestrator.

## Rule 2: Memory Division

Each memory system has a specific role. Do not cross boundaries.

| Memory System | Scope | Use For |
|--------------|-------|---------|
| `state_store` | Session-level (default) | Task state, intermediate results |
| `Serena` | Project-level | Explicit project decisions, architecture conventions |
| `ruflo` | Session-level | Short-term vector cache, semantic retrieval within current session |
| `Cognee` | Cross-session | Long-term graph memory, entity/relationship retrieval |
| `mem0` | External optional | Preference memory, recurring user constraints, style hints |
| `Letta` | Policy-only | Memory block vocabulary, tool-rule contract, token-pressure policy |
| `episodic-memory` | Disabled in VCO | Do not route/use in normal VCO flow |

Key principles:
- `state_store` is the DEFAULT, not the fallback.
- `mem0` is never a canonical truth-source.
- `Letta` is never runtime memory ownership.
- System runs fully on `state_store + conversation context` even if all optional memory extensions are down.

## Rule 3: Command Priority

Priority order:
1. User explicit command (highest) -- e.g., `/sc:design`, `/ralph-loop` -> bypass VCO
2. VCO protocol instructions
3. Individual plugin default behaviors (lowest)

Exception:
- If user explicitly invokes a specific tool command, bypass VCO routing and use that tool directly.

## Rule 4: Cross-Plane Authority Separation

Prompt / Memory / BrowserOps / DesktopOps 可以协同，但不能相互接管控制权。

| Plane | Allowed Role | Forbidden Role |
|---|---|---|
| Prompt | pattern cards, risk checklists, prompt advice | route takeover, second prompt router |
| Memory | scoped storage & policy boundaries | global execution owner, route override |
| BrowserOps | provider recommendation + task contract | second orchestrator |
| DesktopOps | shadow advisor + open-world contract | default execution owner |

仲裁原则：
1. **Control plane first**：VCO 路由永远优先于任一 plane 建议。
2. **Contract over runtime imitation**：优先吸收 contract/rules/reference，而不是复制上游 runtime。
3. **Shadow before promote**：新增 plane 先进入 `off/shadow/soft`，证据充分后再升级。
4. **Conflict = freeze**：一旦出现 plane 之间的 authority overlap，立即冻结 promotion，退回 `shadow`。

## Adding New Rules

When a new conflict is discovered:
1. Document the conflict scenario
2. Define the resolution strategy
3. Add to the appropriate rule section
4. Update related docs/config/gates so the rule is machine-checkable where possible

## Wave26 Cross-Plane Priority

为防止 Wave19-30 新增平面互相越权，增加以下优先级：

1. **Control plane immutable**：VCO 路由结果高于任何 memory/prompt/browser/desktop 扩展建议。
2. **Canonical memory precedence**：`state_store` / `Serena` / `ruflo` / `Cognee` 的 owner 权高于 `mem0` / `Letta`。
3. **Prompt is advisory only**：prompt intelligence 不能改写 route，只能补充 pattern / risk / checklist。
4. **Browser before desktop for web-native tasks**：纯浏览器任务优先走 BrowserOps；只有 open-world/跨应用桌面任务才考虑 DesktopOps shadow 建议。
5. **No hidden promotion**：任何 plane 未通过 promotion board 前，都不得跳过 `shadow` 直接变成默认面。

规范化锚点：
- `../docs/governance/cross-plane-conflict-governance.md`
- `../config/cross-plane-conflict-policy.json`
