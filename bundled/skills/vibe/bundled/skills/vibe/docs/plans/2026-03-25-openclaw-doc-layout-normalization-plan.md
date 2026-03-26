# OpenClaw 文档版式收口执行计划

**日期**: 2026-03-25
**需求文档**: [2026-03-25-openclaw-doc-layout-normalization.md](../requirements/2026-03-25-openclaw-doc-layout-normalization.md)
**执行级别**: M
**执行模式**: 文案微调与验证

---

## 执行步骤

1. 找出 README 与安装文档中被单独强调 OpenClaw 的入口文案
2. 把这类文案改成普通、并列、自然的标题和链接文字
3. 保留说明入口，但去掉特殊视觉强调
4. 用全文检索确认旧表述已清理

## 验证命令

```bash
rg -n "🐾|runtime-core preview path|runtime-core 路径|安装路径说明" README.md README.zh.md docs/install/openclaw-path.md
```

## 清理要求

- 不产生临时文件
- 不新增 node 进程

---

**计划状态**: 执行中
