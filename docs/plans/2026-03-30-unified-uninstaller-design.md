# 统一卸载器设计

**日期**: 2026-03-30
**需求文档**: [../requirements/2026-03-30-unified-uninstaller.md](../requirements/2026-03-30-unified-uninstaller.md)
**Internal Grade**: `L`

## Context

当前仓库已有统一安装入口 `install.ps1` / `install.sh`，并通过 `scripts/install/install_vgo_adapter.py` 对不同 host adapter 做统一路由和写面 materialization。

但仓库还没有对称的统一卸载入口。现状是：

- 官方安装面和 host adapter 安装都可能写入 `skills/**`、`skills/vibe/**`、`.vibeskills/**`、`commands/**`、`global_workflows/**`、`mcp_config.json`、`settings.json` / `opencode.json` 中的 `vibeskills` 片段。
- 这些写面分散在安装脚本、closure contract 和文档里。
- 用户如果想卸载，只能手工删目录或参考零散文档，风险是误删用户自己维护的 host 状态。

因此需要统一卸载器，但它不能越界成为“宿主配置回滚器”。它必须是一个 owned-only uninstaller。

## Approaches

### 方案 A：纯路径硬删

按 host 固定删除路径，例如：

- `skills/**`
- `commands/**`
- `.vibeskills/**`
- `mcp_config.json`
- `settings.json`

优点：

- 实现最快

缺点：

- 对共享文件和旧安装极不安全
- 非常容易误删用户后来改过的内容
- 与当前 honest host-boundary contract 冲突

### 方案 B：统一卸载器，ledger 优先，旧安装兼容回退

统一入口负责 host 路由，但删除决策按 ownership 证据分层：

1. `install-ledger` 为最高优先级
2. `.vibeskills/host-closure.json` 为已安装面辅助证据
3. 对旧安装走保守兼容回退，仅清理安全可证明的受管表面

优点：

- 与现有统一安装器架构对称
- 可以安全支持共享配置文件的局部删除
- 能兼容当前已存在安装面，不要求用户先重装
- 后续可以持续收紧 ownership proof，而不是一次性冒险

缺点：

- 需要先补 install ledger 规范
- 卸载器实现比纯路径硬删更复杂

### 方案 C：每个 host 各自实现独立卸载器

优点：

- 单 host 看起来简单

缺点：

- 与统一安装器方向相反
- 会复制 host 路由、target root 解析、shared ownership 逻辑
- 长期最容易再次漂移

## Recommendation

推荐方案 B。

原因：

- 当前仓库已经有统一安装内核和明确的 host closure contract，最自然的收敛方向是做“统一卸载器”，而不是再复制出六套卸载实现。
- 用户要求“默认直接卸载”，这意味着安全边界必须由 ownership proof 提供，而不能依赖人工确认。
- 只有 ledger-first 设计才能同时满足“默认直接执行”和“只删除 Vibe 自己写入的内容”。

## Final Design

### 1. User-Facing Surface

新增两个对称入口：

- `uninstall.ps1`
- `uninstall.sh`

共同参数：

- `--host codex|claude-code|cursor|windsurf|openclaw|opencode`
- `--target-root <path>`
- `--profile minimal|full`
- `--preview`
- `--purge-empty-dirs`
- `--strict-owned-only`

行为约束：

- 默认直接卸载
- `--preview` 为可选模式，只输出将删除什么
- `--strict-owned-only` 默认开启，除非未来明示设计变更，否则不提供“粗暴强删模式”

### 2. Internal Execution Model

新增统一内核：

- `scripts/uninstall/Uninstall-VgoAdapter.ps1`
- `scripts/uninstall/uninstall_vgo_adapter.py`

职责分层：

- shell/PowerShell 入口负责参数解析、host 规范化、target root 解析
- Python/PowerShell 卸载内核负责：
  - 读取 adapter registry
  - 解析 uninstall surface
  - 读取 install ledger / host closure
  - 生成 delete plan
  - 执行删除
  - 输出 receipt

### 3. Ownership Proof Model

删除决策顺序固定为：

1. `install-ledger`
2. `.vibeskills/host-closure.json`
3. 旧安装兼容规则

#### 3.1 Install Ledger

后续安装器新增：

- `<target-root>/.vibeskills/install-ledger.json`

最小字段：

- `schema_version`
- `host_id`
- `target_root`
- `install_mode`
- `profile`
- `created_paths`
- `merged_files`
- `managed_json_paths`
- `generated_from_template_if_absent`
- `specialist_wrapper_paths`
- `runtime_root`
- `canonical_vibe_root`

卸载器优先用它决定：

- 哪些路径可以整删
- 哪些共享 JSON 只能删受管 stanza
- 哪些模板文件只有在“当时由 Vibe 创建”时才能整删

#### 3.2 Host Closure

当前已存在：

- `.vibeskills/host-closure.json`

它可作为旧安装与部分 host surface 的辅助证据，用于识别：

- `settings_materialized`
- `specialist_wrapper.launcher_path`
- `specialist_wrapper.script_path`
- `commands_root`
- `global_workflows_root`
- `mcp_config_path`

#### 3.3 Legacy Compatibility

对于没有 install ledger 的旧安装，仅允许删除以下安全表面：

- `.vibeskills/**`
- `settings.json` / `opencode.json` 中 `vibeskills.managed=true` 且 `host_id` 匹配的节点
- 与模板完全一致的 `mcp_config.json`
- 明确由当前 packaging 拥有的 `skills/vibe/**` 与 runtime-core 载荷

任何无法证明 ownership 的路径：

- 不删除
- 写入 receipt 的 `skipped_foreign_paths`

### 4. Host-Specific Rules

#### 4.1 Codex

删除：

- runtime-core 载荷
- `skills/vibe/**`
- `rules/**`
- `agents/templates/**`
- `mcp/**`
- `config/plugins-manifest.codex.json`

特殊规则：

- `settings.json` 只有在 install ledger 证明整文件由模板创建且未被用户修改时，才允许整删
- 否则仅移除 `vibeskills` 受管片段或直接跳过

#### 4.2 Claude Code / Cursor

删除：

- runtime-core 载荷
- `.vibeskills/host-closure.json`
- `.vibeskills/bin/*-specialist-wrapper.*`

共享文件：

- `settings.json` 只删 `vibeskills` 节点

#### 4.3 Windsurf / OpenClaw

删除：

- runtime-core 载荷
- `.vibeskills/**`
- `global_workflows/**` 中 ledger 登记的内容

条件删除：

- `mcp_config.json` 仅在 install ledger 标记为 Vibe 创建，或当前内容仍与模板一致时整删

#### 4.4 OpenCode

删除：

- runtime-core 载荷
- `commands/**`
- `command/**`
- `agents/**`
- `agent/**`
- `opencode.json.example`
- `.vibeskills/**`

共享文件：

- `opencode.json` 只删 `vibeskills` 受管节点

### 5. Shared JSON Mutation Rules

对 `settings.json` / `opencode.json` 一律不使用整文件覆盖删除。

行为固定为：

- 仅删除 `vibeskills` 顶级节点
- 如果删完后文件为空对象 `{}`，且 ledger 证明该文件由 Vibe 初建，才允许整文件删除
- 任何 JSON 解析失败都不做 destructive delete，只写 warning

### 6. Receipt Contract

卸载输出：

- `outputs/runtime/uninstall/<run-id>/uninstall-receipt.json`

最小字段：

- `host_id`
- `target_root`
- `mode`
- `deleted_paths`
- `mutated_json_paths`
- `skipped_foreign_paths`
- `warnings`
- `empty_dirs_removed`
- `ownership_source`
- `completion_language_allowed`

### 7. Verification Strategy

新增测试：

- `tests/runtime_neutral/test_uninstall_vgo_adapter.py`
- `tests/runtime_neutral/test_installed_runtime_uninstall.py`

新增 gate：

- `scripts/verify/vibe-uninstall-coherence-gate.ps1`

必须覆盖：

- preview 模式与默认直接卸载模式
- ledger 驱动删除
- 旧安装兼容删除
- `settings.json` / `opencode.json` 局部删除
- foreign file 不误删
- 空目录清理
- host target root guard
- uninstall/install 后的 non-regression

## Risks And Controls

### 风险 1：误删共享配置

控制：

- 共享 JSON 只删 `vibeskills`
- 解析失败不删
- 整文件删除必须要 ownership proof

### 风险 2：旧安装没有 ledger

控制：

- 明确 legacy compatibility mode
- 只删除 `.vibeskills/**`、模板等高置信 owned surface

### 风险 3：host 路径漂移

控制：

- 继续复用现有 adapter registry 和 target-root guard

### 风险 4：卸载器与安装器继续漂移

控制：

- 后续把 install ledger 纳入安装器权威输出
- 新增 uninstall coherence gate，要求 install/uninstall surface 对称

## Approved Direction

本设计冻结的最终方向是：

- 做一个统一卸载器
- 默认直接执行卸载
- 严格采用 owned-only 语义
- 以 install ledger 为未来权威证据
- 以 host closure 和 legacy compatibility 兜底现有安装面
- 不宣称回滚宿主自己管理的状态
