# 配置指南

本文档详细说明 VibeSkills 的配置选项，特别是治理 AI 在线层的配置方法。

---

## 🎯 配置概览

VibeSkills 的配置分为两个层次：

1. **基础在线能力**：宿主（Codex/Claude Code）的基本 AI 能力
2. **治理 AI 在线层**：VibeSkills 特有的治理增强能力

---

## 📋 VCO 治理 AI 配置字段

### VCO_AI_PROVIDER_URL

**作用**: 治理 AI 要连接的 provider 地址或兼容 API Base URL。

**说明**:
- 这是治理 AI 调用在线模型的入口地址
- 可以是 OpenAI 兼容的 API 地址
- 例如：`https://api.openai.com/v1` 或其他兼容服务

**配置位置**:
- Codex: `~/.codex/settings.json` 的 `env` 字段
- Claude Code: `~/.claude/settings.json` 的 `env` 字段
- 或使用本地环境变量

---

### VCO_AI_PROVIDER_API_KEY

**作用**: 治理 AI 访问该 provider 时使用的本地认证密钥。

**说明**:
- 这是访问在线模型服务的 API 密钥
- **安全提示**: 永远不要在聊天中粘贴 API 密钥
- 只在本地配置文件或环境变量中设置

**配置位置**:
- Codex: `~/.codex/settings.json` 的 `env` 字段
- Claude Code: `~/.claude/settings.json` 的 `env` 字段
- 或使用本地环境变量

---

### VCO_AI_PROVIDER_MODEL

**作用**: 治理 AI 在线分析、治理增强或相关 overlay 要调用的模型名。

**说明**:
- 指定治理 AI 使用的具体模型
- 例如：`gpt-4`, `claude-3-opus`, `gpt-3.5-turbo` 等
- 根据你的 provider 支持的模型来设置

**配置位置**:
- Codex: `~/.codex/settings.json` 的 `env` 字段
- Claude Code: `~/.claude/settings.json` 的 `env` 字段
- 或使用本地环境变量

---

## 🔧 Codex 配置方法

### 基础在线能力配置

Codex 的基础在线能力需要配置：

```json
{
  "env": {
    "OPENAI_API_KEY": "your-openai-api-key",
    "OPENAI_BASE_URL": "https://api.openai.com/v1"
  }
}
```

**说明**:
- `OPENAI_API_KEY`: Codex 基础在线 provider 的密钥
- `OPENAI_BASE_URL`: Codex 基础在线 provider 的地址
- **注意**: 这只代表 Codex 基础在线能力，不等于治理 AI 在线层已配置

### 治理 AI 在线层配置

如果需要启用 Codex 下的治理 AI 在线层，还需要额外配置：

```json
{
  "env": {
    "OPENAI_API_KEY": "your-openai-api-key",
    "OPENAI_BASE_URL": "https://api.openai.com/v1",
    "VCO_AI_PROVIDER_URL": "https://api.openai.com/v1",
    "VCO_AI_PROVIDER_API_KEY": "your-vco-api-key",
    "VCO_AI_PROVIDER_MODEL": "gpt-4"
  }
}
```

**配置步骤**:
1. 打开 `~/.codex/settings.json`
2. 在 `env` 字段下添加上述配置
3. 保存文件
4. 重启 Codex

**为什么需要配置**:
- 只有配置了这三个字段，才能启用 Codex 下的治理 AI 在线层
- 如果没配，只能说"Codex 基础在线能力已配置"
- 不能说"治理 AI 在线层已就绪"

---

## 🔧 Claude Code 配置方法

### 基础在线能力

Claude Code 的基础在线能力由 Anthropic 提供，通常不需要额外配置。

### 治理 AI 在线层配置

如果需要启用 AI 治理层的在线能力，需要配置：

```json
{
  "env": {
    "VCO_AI_PROVIDER_URL": "https://api.openai.com/v1",
    "VCO_AI_PROVIDER_API_KEY": "your-api-key",
    "VCO_AI_PROVIDER_MODEL": "gpt-4"
  }
}
```

**配置步骤**:
1. 打开 `~/.claude/settings.json`
2. 在 `env` 字段下添加上述配置（保留原有设置）
3. 保存文件
4. 重启 Claude Code

**为什么需要配置**:
- 如果希望启用 AI 治理层的在线能力，而不是只跑本地 runtime / prompt / check 流程，就需要这三项
- 没配时只能说"本地安装完成，但治理 AI 在线能力未就绪"
- 不能伪装成 full closure 或 online readiness

---

## 🔐 安全最佳实践

### 1. 永远不要在聊天中粘贴密钥

❌ **错误做法**:
```
用户: 我的 API key 是 sk-xxxxx，帮我配置
```

✅ **正确做法**:
```
用户: 我需要配置 API key
助手: 请打开 ~/.codex/settings.json，在 env 字段下添加 VCO_AI_PROVIDER_API_KEY
```

### 2. 使用本地配置文件

优先使用本地配置文件，而不是环境变量：
- 配置文件更容易管理
- 可以版本控制（但要排除敏感信息）
- 更容易备份和恢复

### 3. 区分不同的密钥

- `OPENAI_API_KEY`: Codex 基础能力的密钥
- `VCO_AI_PROVIDER_API_KEY`: 治理 AI 的密钥
- 可以使用相同的密钥，也可以使用不同的密钥

---

## 📊 配置状态检查

### 如何检查配置是否正确

安装完成后，运行 check 命令：

```bash
# Codex
bash ./check.sh --host codex --profile full --deep

# Claude Code
bash ./check.sh --host claude-code --profile full --deep
```

### 配置状态说明

| 状态 | 说明 |
|------|------|
| ✅ 本地安装完成 | 安装脚本执行成功，文件已复制 |
| ✅ 基础在线能力已配置 | OPENAI_API_KEY 等基础字段已配置 |
| ✅ 治理 AI 在线层已就绪 | VCO_AI_PROVIDER 三个字段都已配置 |
| ⚠️ 治理 AI 在线能力未就绪 | VCO_AI_PROVIDER 字段未配置或不完整 |

---

## 🎯 常见配置场景

### 场景 1: 只使用本地能力

如果你只想使用本地 runtime / prompt / check 流程，不需要在线能力：

**不需要配置任何字段**

### 场景 2: 使用基础在线能力

如果你想使用 Codex 的基础在线能力：

**只需要配置**:
- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`

### 场景 3: 使用完整的治理 AI 在线层

如果你想使用完整的治理 AI 在线增强能力：

**需要配置**:
- `OPENAI_API_KEY` (Codex)
- `OPENAI_BASE_URL` (Codex)
- `VCO_AI_PROVIDER_URL`
- `VCO_AI_PROVIDER_API_KEY`
- `VCO_AI_PROVIDER_MODEL`

---

## 📖 使用方法

在安装提示词中，可以这样引用配置说明：

```text
## 配置说明
详细配置请参考：[配置指南](../configuration-guide.md)

核心配置项：
- VCO_AI_PROVIDER_URL: 治理 AI 的 provider 地址
- VCO_AI_PROVIDER_API_KEY: 治理 AI 的认证密钥
- VCO_AI_PROVIDER_MODEL: 治理 AI 使用的模型名

配置位置：
- Codex: ~/.codex/settings.json 的 env 字段
- Claude Code: ~/.claude/settings.json 的 env 字段
```

---

**文档版本**: 1.0
**最后更新**: 2026-03-23
