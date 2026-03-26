# Framework-Only Path 兼容入口修复计划

**日期**: 2026-03-26
**需求文档**: [2026-03-26-framework-only-path-compat-fix.md](../requirements/2026-03-26-framework-only-path-compat-fix.md)

## 执行步骤

1. 确认 `main` 上目标文件缺失且 README 仍在引用
2. 新增中英文兼容落点页
3. 修正英文 README 和安装索引入口
4. 用全文检索验证引用闭环

## 验证命令

```bash
rg -n "framework-only-path" README.md README.zh.md docs/install
test -f docs/install/framework-only-path.md
test -f docs/install/framework-only-path.en.md
```
