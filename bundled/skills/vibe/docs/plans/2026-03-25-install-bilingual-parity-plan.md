# 安装文档双语完整性执行计划

**日期**: 2026-03-25
**需求文档**: [2026-03-25-install-bilingual-parity.md](../requirements/2026-03-25-install-bilingual-parity.md)
**执行级别**: L
**执行模式**: 文档补齐与链接修正

---

## 执行步骤

1. 审计 `docs/install` 下缺失 `.en.md` 的文档
2. 为缺失文件补写英文版本，保持与中文原文一致
3. 修正英文 README / install 索引 / install 入口中的链接目标
4. 运行脚本再次检查双语完整性

## 目标文件

- `custom-skill-governance-rules.en.md`
- `custom-workflow-onboarding.en.md`
- `enterprise-governed-path.en.md`
- `minimal-path.en.md`
- `openclaw-path.en.md`

## 验证命令

```bash
python3 - <<'PY'
from pathlib import Path
base = Path('docs/install')
files = sorted(p.name for p in base.iterdir() if p.is_file() and p.suffix == '.md')
base_names = {}
for f in files:
    if f.endswith('.en.md'):
        key = f[:-6]
        base_names.setdefault(key, {})['en'] = f
    else:
        key = f[:-3]
        base_names.setdefault(key, {})['zh'] = f
for key, langs in sorted(base_names.items()):
    if 'zh' not in langs or 'en' not in langs:
        print(key, langs)
PY
```

## 清理要求

- 不产生临时文件
- 不新建 node 进程

---

**计划状态**: 执行中
