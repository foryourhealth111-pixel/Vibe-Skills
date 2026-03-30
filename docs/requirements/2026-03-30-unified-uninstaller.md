# 统一卸载器需求

**日期**: 2026-03-30
**目标**: 为 Vibe 增加一个覆盖官方安装面与全部当前 host adapter（`codex`、`claude-code`、`cursor`、`windsurf`、`openclaw`、`opencode`）的统一卸载器，默认直接执行卸载，但只删除 Vibe 自己安装或写入的内容，不回滚宿主自己管理的状态。

## Intent Contract

- Goal: 设计并后续实现一个对称于 `install.ps1` / `install.sh` 的统一卸载器，而不是继续依赖文档级手工删除说明。
- Deliverable:
  - 统一卸载入口：`uninstall.ps1` / `uninstall.sh`
  - 统一适配器卸载内核：`scripts/uninstall/Uninstall-VgoAdapter.ps1` / `scripts/uninstall/uninstall_vgo_adapter.py`
  - 安装账本与卸载 receipt 设计
  - 覆盖六个 host lane 的 owned-only 删除边界
  - 对应 tests / verify gate / docs 设计
- Constraints:
  - 默认行为是直接卸载，不以 `--apply` 为前提。
  - 仍允许 `--preview` 作为可选安全模式，但不是默认。
  - 只删除 Vibe 自己安装/写入的内容，不删除宿主登录态、provider 凭证、插件状态或用户手工维护内容。
  - 对共享配置文件（如 `settings.json`、`opencode.json`），只能删除 `vibeskills` 受管片段，不能整文件删除，除非有明确 ownership proof 且可证明整文件由 Vibe 创建。
  - 必须兼容“旧安装无 install ledger”的已安装面。
  - 不允许通过卸载器引入新的 host-native 权限声明或超出现有 install contract 的写面。
- Acceptance Criteria:
  - 统一卸载器支持 `--host`、`--target-root`、`--profile`，行为与安装器路由方式对称。
  - 对每个 host，卸载器有明确定义的“删除什么 / 跳过什么 / 何时整文件删除 / 何时只删受管 stanza”规则。
  - 安装器后续补写 `install-ledger` 后，卸载器优先按 ledger 删除。
  - 在没有 ledger 的旧安装面上，卸载器只能执行保守兼容删除，不得误删用户状态。
  - 卸载后生成统一 receipt，列出 deleted / skipped / foreign / warnings。
  - 新增 tests 与 gate 能证明 owned-only 语义、host 对称性和 non-regression。
- Product Acceptance Criteria:
  - 用户从安装路径能得到对称的“安装 / 检查 / 卸载”闭环。
  - 卸载器应成为权威路径，而不是让用户继续手动删除 `skills/`、`commands/`、`settings.json` 片段。
  - 宿主真实边界仍保持 honest：repo 不宣称能回滚宿主管理状态。
- Manual Spot Checks:
  - 对照 `scripts/install/install_vgo_adapter.py` 的当前写面，确认每个被写入路径都在卸载设计中得到对应处理。
  - 对照各 `adapters/*/closure.json`，确认 `repo_managed_payload` 与 `host_state_written` 都被映射到删除策略。
  - 对照 `docs/universalization/install-matrix.md` 与 `docs/universalization/host-capability-matrix.md`，确认卸载设计没有超出当前 install mode 边界。
- Completion Language Policy:
  - 在 requirement、design、implementation plan 都落地前，只能说“卸载器方案在设计中”。
  - 在脚本、测试和 gate 没有实现并验证前，不能说“统一卸载器已支持”。
- Delivery Truth Contract:
  - 本轮文档只固定卸载器方案和后续实现路线。
  - 对于尚不存在的 install ledger、卸载脚本、gate、tests，只能写为“应新增”或“后续实现”，不能伪装成已存在。
- Non-goals:
  - 不回滚用户手工安装的插件、host 登录态、provider 配置或宿主自己维护的 MCP 注册。
  - 不把统一卸载器扩展成“系统恢复器”或“全环境清洗器”。
  - 不在本轮直接实现卸载逻辑。
- Autonomy Mode: `interactive_governed`
- Inferred Assumptions:
  - 用户希望的是一个可直接运行的统一卸载器，但其安全语义必须是 owned-only。
  - 最合理的策略是“ledger 优先、closure 兜底、旧安装兼容回退”，而不是纯路径硬删。
