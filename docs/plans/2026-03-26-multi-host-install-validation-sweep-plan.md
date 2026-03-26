# Multi-Host Install Validation Sweep 执行计划

**日期**: 2026-03-26
**需求文档**: [2026-03-26-multi-host-install-validation-sweep.md](../requirements/2026-03-26-multi-host-install-validation-sweep.md)
**执行级别**: XL
**执行模式**: automated + command-level + cleanup

---

## 内部级别决策

- 选择 `XL`
- 原因：本轮不是单点 smoke test，而是多宿主、多入口、自动化与命令级交叉验证，需要并行执行并统一分析

## Wave 设计

1. Wave 1: 审计现有安装相关自动化测试覆盖
2. Wave 2: 跑自动化测试，验证 canonical、bundled、installed-runtime 关键路径
3. Wave 3: 跑真实命令级安装矩阵，覆盖五个宿主
4. Wave 4: 分析失败与边界，必要时修复并复测
5. Wave 5: 清理临时目录、审计 node、形成结论

## 验证命令

```bash
python3 -m pytest -q tests/runtime_neutral

bash ./install.sh --host codex --target-root <temp> --profile full
bash ./check.sh --host codex --target-root <temp> --profile full --deep

bash ./install.sh --host claude-code --target-root <temp> --profile full
bash ./check.sh --host claude-code --target-root <temp> --profile full

bash ./install.sh --host cursor --target-root <temp> --profile full
bash ./check.sh --host cursor --target-root <temp> --profile full

bash ./install.sh --host windsurf --target-root <temp> --profile full
bash ./check.sh --host windsurf --target-root <temp> --profile full --deep
bash <temp>/skills/vibe/check.sh --host windsurf --target-root <temp> --profile full --deep

bash ./install.sh --host openclaw --target-root <temp> --profile full
bash ./check.sh --host openclaw --target-root <temp> --profile full --deep
bash <temp>/skills/vibe/check.sh --host openclaw --target-root <temp> --profile full --deep
bash <temp>/skills/vibe/scripts/bootstrap/one-shot-setup.sh --host openclaw --target-root <temp> --profile full
```

## 风险判定规则

1. `preview-guidance` 下要求用户手工填 provider 配置，属于预期边界，不记为失败
2. `runtime-core` 下不写宿主原生设置，属于设计边界，不记为失败
3. mirror drift、host 解析分叉、自举复制失败，记为真实缺陷
4. 任何无法稳定复现的“偶现失败”都不能直接忽略，必须给出条件

## Cleanup

1. 删除本轮所有临时 target root 与日志
2. 不保留无意义的实验中间文件
3. 审计并报告 node 进程状态
