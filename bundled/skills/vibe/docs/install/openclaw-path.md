# OpenClaw 宿主说明

本文档定义 OpenClaw 当前公开安装口径。

## 一句话口径

- `status`：`preview`
- `closure_level`：`runtime-core-preview`
- `install_mode` / `check_mode`：`runtime-core`
- 默认目标根目录：`OPENCLAW_HOME` 或 `~/.openclaw`

对应契约来源：

- `adapters/index.json`
- `adapters/openclaw/host-profile.json`
- `adapters/openclaw/closure.json`
- `adapters/openclaw/settings-map.json`

## 三路径（attach / copy / bundle）

### attach 路径

目标：接入并校验已有 OpenClaw 根目录。

示例：

```bash
bash ./check.sh --host openclaw --target-root "${OPENCLAW_HOME:-$HOME/.openclaw}" --profile full --deep
```

### copy 路径

目标：通过安装入口把 runtime-core payload 复制到 `OPENCLAW_HOME` 或 `~/.openclaw`。

示例：

```bash
bash ./scripts/bootstrap/one-shot-setup.sh --host openclaw --profile full
bash ./check.sh --host openclaw --profile full --deep
```

### bundle 路径

目标：按分发清单消费 OpenClaw runtime-core 预览包。

清单入口：

- `dist/host-openclaw/manifest.json`
- `dist/manifests/vibeskills-openclaw.json`

## 当前重点

- 按 `preview` / `runtime-core-preview` / `runtime-core` 口径描述 OpenClaw
- 目标根目录统一为 `OPENCLAW_HOME` 或 `~/.openclaw`
- 重点覆盖 runtime-core payload 的安装、校验与分发
- 宿主侧本地配置按 OpenClaw 自身方式完成
