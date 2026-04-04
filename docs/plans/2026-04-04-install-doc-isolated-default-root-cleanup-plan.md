# 执行计划: 安装文档默认根目录清理

## 内部等级

L

## 步骤

1. 盘点 `docs/install` 与 `docs/install/prompts` 中涉及默认安装根的文档。
2. 只修改“默认安装根 / 默认目标根”相关表述，不动真实宿主 settings/config 文件说明。
3. 将根文档同步到 `bundled/skills/vibe/docs/install` 和嵌套 bundle 镜像。
4. 用 grep 验证安装文档面不再把旧原生宿主目录写成默认安装根。
5. 做阶段清理审计，不误清理其他工作目录的 node 进程。

## 验证方式

```bash
rg -n "~/.codeium/windsurf|~/.openclaw|~/.config/opencode|~/.codex|~/.claude|~/.cursor" docs/install docs/install/prompts
```

说明：

- 上面的 grep 结果里，真实宿主 settings/config 文件引用可以保留。
- 默认安装根相关旧值不应继续出现于本轮改过的安装文档中。

## 回滚规则

- 如果文档把“真实宿主配置面”误写成“默认安装根”，优先回退该措辞并保留宿主管理边界。
- 如果根文档与 bundle 镜像漂移，以根文档为准重新同步。
