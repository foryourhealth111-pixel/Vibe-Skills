# OpenClaw 安装与使用说明

本文档汇总把 VibeSkills 安装到 OpenClaw 时最常用的命令、默认目标根目录和补充说明。

## 为什么有这份专页

- 通用安装提示词同样可以安装 `openclaw`
- 这份专页不是替代通用安装提示词，而是补充 OpenClaw 宿主特有说明
- 单独拆出本页，是因为 OpenClaw 还需要展开默认目标根目录、attach / copy / bundle 三种路径，以及宿主侧本地边界；这些内容如果全部塞进公共安装文档，会让其他宿主说明变得混乱

## 默认安装信息

- 默认目标根目录：`OPENCLAW_HOME` 或 `~/.vibeskills/targets/openclaw`
- 默认安装方式：one-shot setup + check
- 宿主侧本地配置仍按 OpenClaw 自身方式完成

## 常见安装路径

### attach 路径

目标：接入并校验已有 OpenClaw 根目录。

示例：

```bash
bash ./check.sh --host openclaw --target-root "${OPENCLAW_HOME:-$HOME/.vibeskills/targets/openclaw}" --profile full --deep
```

### copy 路径

目标：通过安装入口把仓库分发内容复制到 `OPENCLAW_HOME` 或 `~/.vibeskills/targets/openclaw`。

示例：

```bash
bash ./scripts/bootstrap/one-shot-setup.sh --host openclaw --profile full
bash ./check.sh --host openclaw --profile full --deep
```

### bundle 路径

目标：按分发清单消费 OpenClaw 分发包。

清单入口：

- `dist/host-openclaw/manifest.json`
- `dist/manifests/vibeskills-openclaw.json`

## 当前重点

- 目标根目录统一为 `OPENCLAW_HOME` 或 `~/.vibeskills/targets/openclaw`
- 重点覆盖仓库分发内容的安装、校验与分发
- 宿主侧本地配置按 OpenClaw 自身方式完成

## 契约来源

如果你需要查看更细的适配契约与分发信息，可继续看：

- `adapters/index.json`
- `adapters/openclaw/host-profile.json`
- `adapters/openclaw/closure.json`
- `adapters/openclaw/settings-map.json`
