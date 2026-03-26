# OpenClaw Adapter Normalization 需求文档

**日期**: 2026-03-26
**任务类型**: 适配器一致性修复与运行时规范化
**优先级**: 高
**执行模式**: governed, latest-main-only

---

## 目标（Goal）

修复 OpenClaw 在最新主线中的适配器分叉问题，把 canonical runtime truth、runtime-core 安装链路、bundled mirror、副本脚本与验证面重新拉齐。

## 交付物（Deliverable）

1. 统一后的 OpenClaw / Windsurf runtime-core 适配行为
2. 修复后的 runtime-core 安装器自举复制逻辑
3. 与 canonical 一致的 `bundled/skills/vibe` 与 nested bundled mirror
4. 覆盖 bundled-host drift 与 installed-runtime bootstrap 的回归测试
5. 通过本地复现实验的验证结果

## 约束（Constraints）

1. 不降级 `codex`、`claude-code`、`cursor`、`windsurf`、`openclaw` 的现有支持面
2. 不把 OpenClaw 夸大成 host-native closure
3. 不依赖用户手工同步 bundled mirror 才能获得正确 host 支持
4. 不回退仓库中与本任务无关的现有内容
5. 阶段结束后清理本轮临时目录与测试残留

## 验收标准（Acceptance Criteria）

1. 顶层 `check.sh` / `scripts/bootstrap/one-shot-setup.sh` 与 bundled 对应脚本对 `openclaw` 的 host 解析口径一致
2. 从已安装的 `skills/vibe` 目录再次运行 runtime-core 安装/bootstrap，不再因为复制重叠而失败
3. `openclaw` 与 `windsurf` 的 adapter metadata、默认 target root、runtime-core mode 保持一致设计
4. 新增回归测试能覆盖：
   - bundled mirror 不得落后 canonical host 支持
   - installed runtime 自举不会自删源目录
5. 相关测试全部通过

## 非目标（Non-Goals）

1. 不在本轮扩展新的 host
2. 不在本轮重写整个安装框架
3. 不改变 OpenClaw 当前 `preview` / `runtime-core-preview` / `runtime-core` 的产品口径
