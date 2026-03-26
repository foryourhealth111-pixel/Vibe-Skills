# 安装与自定义接入索引

本目录用于对外公开的安装、升级与自定义接入说明。

## 快速导航

### 新安装

- [`prompts/full-version-install.md`](./prompts/full-version-install.md)：全量版本安装提示词
- [`prompts/framework-only-install.md`](./prompts/framework-only-install.md)：框架版本安装提示词

### 更新已安装版本

- [`prompts/full-version-update.md`](./prompts/full-version-update.md)：全量版本更新提示词
- [`prompts/framework-only-update.md`](./prompts/framework-only-update.md)：框架版本更新提示词

### 参考说明

- [`one-click-install-release-copy.md`](./one-click-install-release-copy.md)：默认推荐入口，先看版本和宿主选择，再跳转到对应提示词
- [`recommended-full-path.md`](./recommended-full-path.md)：高级 host / lane / 命令参考
- [`manual-copy-install.md`](./manual-copy-install.md)：离线或无管理员权限时的手动复制路径
- [`installation-rules.md`](./installation-rules.md)：安装助手必须遵守的 truth-first 规则
- [`configuration-guide.md`](./configuration-guide.md)：本地配置说明

## 公开版本

当前对外公开仍是两种用户版本：

- `全量版本 + 可自定义添加治理`
- `仅核心框架 + 可自定义添加治理`

它们在当前脚本里的真实 profile 映射是：

- `全量版本 + 可自定义添加治理` -> `full`
- `仅核心框架 + 可自定义添加治理` -> `minimal`

对外继续使用友好版本名，对内执行时再映射到真实 profile。

## 当前公开支持宿主

- `codex`
- `claude-code`
- `cursor`
- `windsurf`
- `openclaw`

其中：

- `codex`：governed / 当前最完整路径
- `claude-code`：支持的安装与使用路径
- `cursor`：支持的安装与使用路径
- `windsurf`：支持的安装与使用路径，且已接入 runtime adapter
- `openclaw`：preview / runtime-core-preview / runtime-core 路径

其他宿主当前不应被描述成“已支持安装”。

## 推荐阅读顺序

如果你是普通用户：

1. [`one-click-install-release-copy.md`](./one-click-install-release-copy.md)
2. 对应的提示词文档
3. [`custom-workflow-onboarding.md`](./custom-workflow-onboarding.md)
4. [`custom-skill-governance-rules.md`](./custom-skill-governance-rules.md)

如果你是高级用户：

1. [`recommended-full-path.md`](./recommended-full-path.md)
2. [`manual-copy-install.md`](./manual-copy-install.md)
3. [`host-plugin-policy.md`](./host-plugin-policy.md)

## 自定义扩展

- [`custom-workflow-onboarding.md`](./custom-workflow-onboarding.md)：如何把新 workflow 纳入治理与路由
- [`custom-skill-governance-rules.md`](./custom-skill-governance-rules.md)：自定义 skill / workflow 的治理规则
