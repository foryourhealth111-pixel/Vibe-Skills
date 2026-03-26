# OpenClaw Runtime-Core 补齐执行计划

**日期**: 2026-03-26
**需求文档**: [2026-03-26-openclaw-runtime-core-completion.md](../requirements/2026-03-26-openclaw-runtime-core-completion.md)
**执行级别**: L
**执行模式**: 本地补齐 + 本地验证

---

## 阶段

1. 校验现有 OpenClaw 安装/检查链条是否真实可用
2. 补齐 closure、dist manifest、public manifest、matrix docs
3. 补齐 `vibe-dist-manifest-gate.ps1` 的覆盖范围
4. 运行本地测试与临时目录安装校验
5. 清理临时目录和僵尸 node

## 验证命令

```bash
pytest -q tests/runtime_neutral/test_openclaw_runtime_core.py tests/runtime_neutral/test_windsurf_runtime_core.py
pwsh -NoProfile -File scripts/verify/vibe-host-adapter-contract-gate.ps1
pwsh -NoProfile -File scripts/verify/vibe-dist-manifest-gate.ps1
bash ./install.sh --host openclaw --profile full --target-root <temp>
bash ./check.sh --host openclaw --profile full --target-root <temp> --deep
```

## 清理要求

- 删除本轮临时 target root
- 清理本轮产生的临时文件
- 审计并清理僵尸 node 进程
