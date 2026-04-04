# 执行计划: OpenCode PowerShell 深检一致性与隔离默认安装根

## 内部等级

L

## 步骤

1. 定位 `OpenCode` PowerShell 深检误报点，确认是路径拼接而非安装载荷缺失。
2. 更新 canonical adapter registry 以及 Python / PowerShell embedded registry，使默认目标根统一指向 `.vibeskills/targets/<host>`。
3. 更新 shell、PowerShell helper、bootstrap 的默认根解析与 host-intent 识别逻辑，兼容旧原生根和新隔离根。
4. 修复 `check.ps1` 中 `opencode` commands / agents 路径拼接，避免 Linux `pwsh` 深检误报。
5. 更新定向测试，并同步 bundle 镜像，避免 release/install/runtime coherence 漂移。
6. 运行定向验证并做阶段清理审计。

## 验证命令

```bash
python3 -m unittest \
  tests.runtime_neutral.test_opencode_preview_parity \
  tests.runtime_neutral.test_windsurf_runtime_core \
  tests.runtime_neutral.test_openclaw_runtime_core
```

## 回滚规则

- 若定向测试失败，优先回查 registry 与 host-intent 判断是否存在主/副本漂移。
- 若 only bundle 漂移，则以 canonical root 为准重新同步 bundle 副本。

## 清理要求

- 审计本阶段产生的 node 进程；仅清理确认由本任务启动且已失活的进程
- 确认测试临时目录由测试框架自动回收
