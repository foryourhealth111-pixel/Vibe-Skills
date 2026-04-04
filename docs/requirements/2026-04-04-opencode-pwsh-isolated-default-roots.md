# 需求冻结: OpenCode PowerShell 深检一致性与隔离默认安装根

- 日期: 2026-04-04
- 任务入口: 用户要求先修 `OpenCode` 的 PowerShell 深检不一致，再把默认安装改成隔离根

## 目标

修复 `check.ps1` 在 `opencode` preview-guidance 模式下对 `commands/` 与 `agents/` 载荷的深检误报，并把各 host adapter 的默认安装目标根从真实宿主目录切换到隔离目录。

## 交付物

- `OpenCode` PowerShell 深检在已安装 preview wrapper 时通过
- 适配器注册表与各语言 resolver 默认返回隔离根
- shell / PowerShell / bootstrap 的目标根意图校验同时识别旧原生根和新隔离根
- 定向测试覆盖 `opencode`、`windsurf`、`openclaw`

## 约束

- 不能扩大对真实宿主配置文件的接管范围
- 显式环境变量覆盖仍然有效
- 保持 `settings_surface.path` 继续描述真实宿主配置面，而不是安装根
- 不回退用户已有未关联变更

## 验收标准

- `python3 -m unittest tests.runtime_neutral.test_opencode_preview_parity tests.runtime_neutral.test_windsurf_runtime_core tests.runtime_neutral.test_openclaw_runtime_core` 通过
- `opencode` PowerShell 深检不再出现 `opencode command/*` 或 `opencode agent/*` 失败
- `default_target_root.rel` 默认值变为 `.vibeskills/targets/<host>`
- `default_target_root.kind` 变为 `isolated-home`

## 非目标

- 不做历史文档全量改写
- 不修改真实 `opencode.json`、`settings.json` 或其他原生宿主配置文件
