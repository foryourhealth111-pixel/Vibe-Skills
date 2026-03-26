# Configuration Guide

This document details VibeSkills configuration options, especially the configuration methods for the governance AI online layer.

---

## 🎯 Configuration Overview

VibeSkills configuration is divided into two levels:

1. **Basic Online Capability**: The host's (Codex/Claude Code) basic AI capability
2. **Governance AI Online Layer**: VibeSkills-specific governance enhancement capability

---

## 📋 VCO Governance AI Configuration Fields

### VCO_AI_PROVIDER_URL

**Purpose**: The provider address or compatible API Base URL that the governance AI connects to.

**Explanation**:
- This is the entry address for the governance AI to call online models
- Can be an OpenAI-compatible API address
- Example: `https://api.openai.com/v1` or other compatible services

**Configuration Location**:
- Codex: `env` field in `~/.codex/settings.json`
- Claude Code: `env` field in `~/.claude/settings.json`
- Or use local environment variables

---

### VCO_AI_PROVIDER_API_KEY

**Purpose**: The local authentication key used by the governance AI when accessing that provider.

**Explanation**:
- This is the API key for accessing online model services
- **Security Note**: Never paste API keys in chat
- Only set in local configuration files or environment variables

**Configuration Location**:
- Codex: `env` field in `~/.codex/settings.json`
- Claude Code: `env` field in `~/.claude/settings.json`
- Or use local environment variables

---

### VCO_AI_PROVIDER_MODEL

**Purpose**: The model name to be called when the governance AI needs online analysis, governance enhancement, or related overlay capabilities.

**Explanation**:
- Specifies the specific model used by the governance AI
- Example: `gpt-4`, `claude-3-opus`, `gpt-3.5-turbo`, etc.
- Set according to the models supported by your provider

**Configuration Location**:
- Codex: `env` field in `~/.codex/settings.json`
- Claude Code: `env` field in `~/.claude/settings.json`
- Or use local environment variables

---

## 🔧 Codex Configuration Method

### Basic Online Capability Configuration

Codex's basic online capability requires configuration:

```json
{
  "env": {
    "OPENAI_API_KEY": "your-openai-api-key",
    "OPENAI_BASE_URL": "https://api.openai.com/v1"
  }
}
```

**Explanation**:
- `OPENAI_API_KEY`: Key for Codex basic online provider
- `OPENAI_BASE_URL`: Address for Codex basic online provider
- **Note**: This only represents Codex basic online capability, not that the governance AI online layer is configured

### Governance AI Online Layer Configuration

If you need to enable the governance AI online layer under Codex, additional configuration is required:

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

**Configuration Steps**:
1. Open `~/.codex/settings.json`
2. Add the above configuration under the `env` field
3. Save the file
4. Restart Codex

**Why Configuration is Needed**:
- Only with these three fields configured can the governance AI online layer under Codex be enabled
- Without configuration, can only say "Codex basic online capability is configured"
- Cannot say "governance AI online layer is ready"

---

## 🔧 Claude Code Configuration Method

### Basic Online Capability

Claude Code's basic online capability is provided by Anthropic and usually does not require additional configuration.

### Governance AI Online Layer Configuration

If you need to enable the AI governance layer's online capability, configuration is required:

```json
{
  "env": {
    "VCO_AI_PROVIDER_URL": "https://api.openai.com/v1",
    "VCO_AI_PROVIDER_API_KEY": "your-api-key",
    "VCO_AI_PROVIDER_MODEL": "gpt-4"
  }
}
```

**Configuration Steps**:
1. Open `~/.claude/settings.json`
2. Add the above configuration under the `env` field (preserve existing settings)
3. Save the file
4. Restart Claude Code

**Why Configuration is Needed**:
- If you want to enable the AI governance layer's online capability, rather than just running local runtime / prompt / check flows, these three items are needed
- Without configuration, can only say "local installation complete, but governance AI online capability not ready"
- Cannot pretend to be full closure or online readiness

---

## 🔐 Security Best Practices

### 1. Never Paste Keys in Chat

❌ **Wrong Approach**:
```
User: My API key is sk-xxxxx, help me configure it
```

✅ **Correct Approach**:
```
User: I need to configure API key
Assistant: Please open ~/.codex/settings.json and add VCO_AI_PROVIDER_API_KEY under the env field
```

### 2. Use Local Configuration Files

Prefer local configuration files over environment variables:
- Configuration files are easier to manage
- Can be version controlled (but exclude sensitive information)
- Easier to backup and restore

### 3. Distinguish Different Keys

- `OPENAI_API_KEY`: Key for Codex basic capability
- `VCO_AI_PROVIDER_API_KEY`: Key for governance AI
- Can use the same key or different keys

---

## 📊 Configuration Status Check

### How to Check if Configuration is Correct

After installation completes, run the check command:

```bash
# Codex
bash ./check.sh --host codex --profile full --deep

# Claude Code
bash ./check.sh --host claude-code --profile full --deep
```

### Configuration Status Explanation

| Status | Explanation |
|--------|-------------|
| ✅ Local installation complete | Installation script executed successfully, files copied |
| ✅ Basic online capability configured | OPENAI_API_KEY and other basic fields configured |
| ✅ Governance AI online layer ready | All three VCO_AI_PROVIDER fields configured |
| ⚠️ Governance AI online capability not ready | VCO_AI_PROVIDER fields not configured or incomplete |

---

## 🔎 Router AI Advice Connectivity Probe (#33)

This probe checks only the router AI advice connectivity path (intent/advice layer). It is not a host-wide health doctor and not a platform-wide availability verdict.

Boundary:
- `advice-only`: diagnostic only, never rewrites canonical route decisions.
- Probe failure does not mean the whole platform is unusable; local install/runtime flows can still work.

Typical states:
- `ok`
- `missing_credentials`
- `prefix_required`
- `provider_unreachable`
- `vector_diff_not_configured` / `vector_diff_missing_credentials` / `vector_diff_provider_unreachable` / `vector_diff_ok`

Run:

```powershell
pwsh -NoProfile -File .\scripts\verify\vibe-router-ai-connectivity-gate.ps1 -WriteArtifacts
```

Read outputs:
- JSON: `outputs/verify/vibe-router-ai-connectivity-gate.json` (machine-readable status + next steps)
- Markdown: `outputs/verify/vibe-router-ai-connectivity-gate.md` (human-readable summary)

---

## 🎯 Common Configuration Scenarios

### Scenario 1: Use Local Capability Only

If you only want to use local runtime / prompt / check flows without online capability:

**No configuration needed**

### Scenario 2: Use Basic Online Capability

If you want to use Codex's basic online capability:

**Only need to configure**:
- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`

### Scenario 3: Use Complete Governance AI Online Layer

If you want to use the complete governance AI online enhancement capability:

**Need to configure**:
- `OPENAI_API_KEY` (Codex)
- `OPENAI_BASE_URL` (Codex)
- `VCO_AI_PROVIDER_URL`
- `VCO_AI_PROVIDER_API_KEY`
- `VCO_AI_PROVIDER_MODEL`

---

## 📖 Usage

In installation prompts, you can reference configuration instructions like this:

```text
## Configuration Instructions
For detailed configuration, see: [Configuration Guide](../configuration-guide.en.md)

Core configuration items:
- VCO_AI_PROVIDER_URL: Governance AI provider address
- VCO_AI_PROVIDER_API_KEY: Governance AI authentication key
- VCO_AI_PROVIDER_MODEL: Model name used by governance AI

Configuration location:
- Codex: env field in ~/.codex/settings.json
- Claude Code: env field in ~/.claude/settings.json
```

---

**Document Version**: 1.1
**Last Updated**: 2026-03-26
