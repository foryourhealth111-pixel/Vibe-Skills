# OpenClaw Adapter Normalization 执行计划

**日期**: 2026-03-26
**需求文档**: [2026-03-26-openclaw-adapter-normalization.md](../requirements/2026-03-26-openclaw-adapter-normalization.md)
**执行级别**: XL
**执行模式**: latest-main repair + mirror normalization + proof

---

## 内部级别决策

- 选择 `XL`
- 原因：本轮不是单文件修复，而是 canonical、bundled、nested bundled、runtime-core 安装器、回归测试五个面需要一起收口，否则会继续出现表面修复、镜像落后、安装再坏掉的分叉

## Wave 设计

1. Wave 1: 定位 canonical 与 bundled 的 host drift、安装重叠复制缺陷
2. Wave 2: 修复 runtime-core 安装器的重叠复制逻辑
3. Wave 3: 重新同步并规范 bundled / nested bundled mirror
4. Wave 4: 新增并通过回归测试，覆盖 OpenClaw runtime-core 与 mirror drift
5. Wave 5: 运行本地安装 / 检查 / bootstrap 证明，并清理临时产物

## Ownership

- canonical adapter/runtime-core 逻辑：`scripts/install/install_vgo_adapter.py`、顶层 shell / PowerShell 入口
- mirror 一致性：`bundled/skills/vibe/**`
- 测试与证明：`tests/runtime_neutral/**`

## 验证命令

```bash
python -m pytest -q \
  tests/runtime_neutral/test_openclaw_runtime_core.py \
  tests/runtime_neutral/test_windsurf_runtime_core.py \
  tests/runtime_neutral/test_installed_runtime_scripts.py

bash ./check.sh --host openclaw --target-root <temp-root> --profile full --deep
bash ./install.sh --host openclaw --target-root <temp-root> --profile full
bash ./scripts/bootstrap/one-shot-setup.sh --host openclaw --target-root <temp-root> --profile full

bash bundled/skills/vibe/check.sh --host openclaw --target-root <temp-root> --profile full
bash bundled/skills/vibe/scripts/bootstrap/one-shot-setup.sh --host openclaw --target-root <temp-root> --profile full
```

## 回滚规则

1. 如果 runtime-core 安装器修复导致 codex governed lane 受影响，先回退安装器逻辑再单独收窄补丁
2. 如果 bundled mirror 同步引入大量非本轮预期 diff，优先保留与 host/runtime-core 直接相关的必要同步
3. 任何“通过顶层但 bundled 失败”的状态都不视为完成

## 阶段清理要求

1. 删除本轮临时 target root 与 clone/workdir 测试目录
2. 不保留无用中间文件
3. 审计并清理本轮产生的僵尸 node 进程
