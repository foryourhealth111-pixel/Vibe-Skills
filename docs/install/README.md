# 安装与自定义接入索引

本目录用于对外公开的安装、升级与自定义接入说明。

## 快速导航

### 公开安装入口

- [`one-click-install-release-copy.md`](./one-click-install-release-copy.md)：唯一公开安装入口；先选宿主、动作和版本，再复制对应提示词

### 公开卸载入口

- [`../../uninstall.ps1`](../../uninstall.ps1) / [`../../uninstall.sh`](../../uninstall.sh)：安装完成后的对称卸载入口；参数与 `install.*` 对齐，默认直接执行，但只会按 install ledger、host closure 和保守 legacy surface 删除 Vibe 自己管理的内容
- [`../uninstall-governance.md`](../uninstall-governance.md)：卸载契约说明；明确 shared JSON 只删 `vibeskills` 受管节点，不回滚宿主登录态、provider 凭证或插件状态

### 参考说明

- [`recommended-full-path.md`](./recommended-full-path.md)：多宿主安装命令参考
- [`openclaw-path.md`](./openclaw-path.md)：OpenClaw 专用安装与使用说明
- [`opencode-path.md`](./opencode-path.md)：OpenCode 专用安装与使用说明
- [`manual-copy-install.md`](./manual-copy-install.md)：离线或无管理员权限时的手动复制路径
- [`../one-shot-setup.md`](../one-shot-setup.md)：`install/check/one-shot-setup` 三条宿主模式如何对齐的说明页
- [`../troubleshooting.md`](../troubleshooting.md)：集中式排障入口，避免把故障说明拆成平行安装入口
- [`framework-only-path.md`](./framework-only-path.md)：旧入口名兼容说明
- [`full-featured-install-prompts.md`](./full-featured-install-prompts.md)：Codex 深度路径兼容说明
- [`installation-rules.md`](./installation-rules.md)：安装助手必须遵守的 truth-first 规则
- [`configuration-guide.md`](./configuration-guide.md)：本地配置说明

## 文档角色收敛

| 文档类 | 当前 canonical surface | 说明 |
| --- | --- | --- |
| 公开安装入口 | `one-click-install-release-copy.md` | 唯一对外公开的安装入口 |
| 宿主补充页 | `openclaw-path.md`, `opencode-path.md` | 只补充宿主差异，不是平行公开入口 |
| prompt library | `prompts/*.md`, `full-featured-install-prompts.md` | 作为提示词资产库保留，不额外升格为公开 landing page |
| 兼容/运维参考 | `recommended-full-path.md`, `manual-copy-install.md`, `framework-only-path.md` | 面向高级用户和兼容场景，保留但不抢占公开入口 |

## 当前安装口径怎么读

当前安装说明已经改成 registry-driven：

- `HostId` / `--host` 决定宿主语义
- `install.*`、`check.*` 与 `one-shot-setup.*` 的宿主模式都应以 [`../../config/adapter-registry.json`](../../config/adapter-registry.json) 为准
- 当前公开宿主会落到三类模式：`governed`、`preview-guidance`、`runtime-core`
- `opencode` 仍保留更薄的 direct install/check 路径，但这不代表 registry-driven 的 one-shot wrapper 不可用

说明：

- 面向普通用户时，公开安装入口只保留 [`one-click-install-release-copy.md`](./one-click-install-release-copy.md)
- 真正保留的安装提示词文档仍是 4 份：全量安装、框架安装、全量更新、框架更新
- 其他安装相关页面只作为兼容说明、宿主补充说明或命令参考，不再作为平行公开入口
- 通用安装提示词同样支持 `openclaw` 和 `opencode`
- 单独拆出 [`openclaw-path.md`](./openclaw-path.md) 与 [`opencode-path.md`](./opencode-path.md)，只是为了补充宿主特有细节，不是因为通用安装路径不能安装
- provider / MCP / 宿主 settings 等补充配置，默认都按“增强建议”处理；基础安装完成后即可直接使用，需要更强集成时再按需补充
- `framework-only-path.md`、`full-featured-install-prompts.md`、`minimal-path.md`、`enterprise-governed-path.md` 属于兼容/附录层，不应再被当作并列公开入口

## 公开版本

当前对外公开仍是两种用户版本：

- `全量版本 + 可自定义添加治理`
- `仅核心框架 + 可自定义添加治理`

它们在当前脚本里的真实 profile 映射是：

- `全量版本 + 可自定义添加治理` -> `full`
- `仅核心框架 + 可自定义添加治理` -> `minimal`

对外继续使用友好版本名，对内执行时再映射到真实 profile。

## 当前公开支持宿主

当前公开支持六个宿主，但模式并不相同：

- `codex`：最强 governed lane，也是默认推荐路径
- `claude-code`：支持的安装与使用路径，带 bounded managed closure
- `cursor`：preview-guidance 路径
- `windsurf`：runtime-core 路径，repo 只负责 shared runtime payload 与 `.vibeskills/*` sidecar 状态
- `openclaw`：preview runtime-core adapter 路径，宿主专页展开 attach / copy / bundle 细节
- `opencode`：preview-guidance adapter 路径；public surface 仍保留更薄的 direct install/check 作为默认命令参考

其他宿主当前不应被描述成“已支持安装”。

## 推荐阅读顺序

如果你是普通用户：

1. [`one-click-install-release-copy.md`](./one-click-install-release-copy.md)
2. [`cold-start-install-paths.md`](../cold-start-install-paths.md)
3. 只在这些入口里选择对应提示词或命令路径
4. [`custom-workflow-onboarding.md`](./custom-workflow-onboarding.md)
5. [`custom-skill-governance-rules.md`](./custom-skill-governance-rules.md)

如果你是高级用户：

1. [`recommended-full-path.md`](./recommended-full-path.md)
2. [`manual-copy-install.md`](./manual-copy-install.md)
3. [`host-plugin-policy.md`](./host-plugin-policy.md)
4. [`configuration-guide.md`](./configuration-guide.md)

## 自定义扩展

- [`custom-workflow-onboarding.md`](./custom-workflow-onboarding.md)：如何把新 workflow 纳入治理与路由
- [`custom-skill-governance-rules.md`](./custom-skill-governance-rules.md)：自定义 skill / workflow 的治理规则
