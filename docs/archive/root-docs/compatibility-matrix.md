# Compatibility Matrix

| Component | Windows | macOS | Linux | Governance Mode | Notes |
|---|---|---|---|---|---|
| Core bundled skills | Yes | Yes | Yes | canonical | 仓库主产物，始终为真源 |
| install/check scripts | Yes | Yes | Yes | canonical | PowerShell + Bash 双轨 |
| MCP templates | Yes | Yes | Yes | optional | 需按环境接入 |
| Memory Runtime v2 contracts | Yes | Yes | Yes | shadow-first | 只扩展边界，不替换真源 |
| `mem0` opt-in backend | Yes | Yes | Yes | off/shadow/soft | 仅限 external preference backend |
| `Letta` policy contracts | Yes | Yes | Yes | off/shadow/soft | 仅限 contract / policy source |
| Prompt intelligence assets | Yes | Yes | Yes | shadow-first | 仅作为 pattern / risk / checklist 资产 |
| BrowserOps provider governance | Yes | Yes | Yes | shadow-first | `browser-use` 仅为 provider candidate |
| DesktopOps shadow governance | Yes | Yes | Yes | shadow-first | `Agent-S` 仅为 shadow / advisory / contract source |
| Cross-plane conflict gates | Yes | Yes | Yes | strict governance | 防止 memory/prompt/browser/desktop 角色冲突 |
| Promotion board + pilot eval | Yes | Yes | Yes | evidence-gated | 只有证据充分才可进入更高 rollout stage |
| Bundled sync + packaging | Yes | Yes | Yes | canonical mirror | `docs/config/references/scripts` 全量镜像到 bundled |
