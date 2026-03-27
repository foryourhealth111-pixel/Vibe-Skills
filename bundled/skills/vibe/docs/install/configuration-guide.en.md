# Configuration Guide

This guide clarifies one thing only: how to finish the AI-governance advice online configuration after install.

## First, separate these two states

- `installed locally`: VibeSkills files have been installed into the target host root
- `AI governance online-ready`: the advice path has usable local credentials, model selection, and a reachable provider endpoint

The first state does not imply the second.

## What the quick check actually reads

The current quick check reads from:

1. `<target-root>/settings.json` -> `env`
2. the current shell / process environment

So:

- if the host uses a local `settings.json`, put the variables under `env`
- if the host does not use that file surface, or if you just want to validate connectivity first, use local environment variables

Do not paste secrets into chat.

## Recommended path 1: OpenAI-compatible

This is the common and recommended path for AI-governance online advice.

### Recommended keys

```json
{
  "env": {
    "OPENAI_API_KEY": "<local-api-key>",
    "OPENAI_BASE_URL": "https://api.openai.com/v1",
    "VCO_RUCNLPIR_MODEL": "gpt-5.4-high"
  }
}
```

Notes:

- `OPENAI_API_KEY`: required
- `OPENAI_BASE_URL` or `OPENAI_API_BASE`: optional; if omitted, the runtime falls back to provider defaults or policy config
- `VCO_RUCNLPIR_MODEL`: recommended model key

## Current public path

For local follow-up and quick-check readiness, the public install path now standardizes on:

- `OPENAI_API_KEY`
- optional `OPENAI_BASE_URL` / `OPENAI_API_BASE`
- `VCO_RUCNLPIR_MODEL`

## Built-in governance provider boundary

The built-in AI governance layer now supports OpenAI-compatible integration only.

That means:

- advice calls follow OpenAI-compatible Responses / Chat Completions / Embeddings semantics
- install docs, bootstrap, and quick-check guidance no longer present Ark-compatible as a parallel built-in lane
- other provider shapes are outside the standard built-in governance support surface

## Advanced path: provider config in policy

If you already maintain provider config in the repo policy, you can keep using:

- `config/llm-acceleration-policy.json` -> `provider.base_url`
- `config/llm-acceleration-policy.json` -> `provider.model`

In that setup:

- base URL and model can come from policy
- local credentials should still use `OPENAI_API_KEY`

## Where this usually goes per host

### Codex

- target root: `~/.codex`
- common location: `~/.codex/settings.json` -> `env`

### Claude Code

- target root: `~/.claude`
- common location: `~/.claude/settings.json` -> `env`

### Cursor

- target root: `~/.cursor`
- common location: `~/.cursor/settings.json` -> `env`

### Windsurf

- target root: `~/.codeium/windsurf`
- if the host does not use `<target-root>/settings.json`, set local environment variables before running the check

### OpenClaw

- target root: `OPENCLAW_HOME` or `~/.openclaw`
- if the host does not use `<target-root>/settings.json`, set local environment variables before running the check

### OpenCode

- target root: `OPENCODE_HOME` or `~/.config/opencode`
- if the host does not use `<target-root>/settings.json`, set local environment variables before running the check

## Quick-check commands

Run from the repo root.

### Windows

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-router-ai-connectivity-gate.ps1 -TargetRoot "<target host root>" -WriteArtifacts
```

If PowerShell 7 is already installed on your machine, you can use `pwsh` instead.

### Linux / macOS

```bash
python3 ./scripts/verify/runtime_neutral/router_ai_connectivity_probe.py --target-root "<target host root>" --write-artifacts
```

Common default roots:

- `codex` -> `~/.codex`
- `claude-code` -> `~/.claude`
- `cursor` -> `~/.cursor`
- `windsurf` -> `~/.codeium/windsurf`
- `openclaw` -> `~/.openclaw`
- `opencode` -> `~/.config/opencode`

## How to read the result

- `ok`: AI-governance advice is online
- `missing_credentials`: local credentials are missing; usually add `OPENAI_API_KEY`
- `missing_model`: the model is missing; usually add `VCO_RUCNLPIR_MODEL`
- `missing_base_url`: add the provider base URL locally, or define `provider.base_url` in policy
- `provider_rejected_request`: key, model id, or endpoint compatibility is wrong
- `provider_unreachable`: network, DNS, base-url reachability, or timeout is failing
- `prefix_required`: the current policy only evaluates advice in explicit `/vibe` scope

## Short practical conclusion

If you want the fastest path for a common OpenAI-compatible setup:

1. configure `OPENAI_API_KEY` locally
2. add `OPENAI_BASE_URL` or `OPENAI_API_BASE` only when you use a custom gateway
3. configure `VCO_RUCNLPIR_MODEL`
4. run the quick check

That is enough for the normal install-time path.
