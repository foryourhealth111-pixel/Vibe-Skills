# OpenClaw Host Notes

This document defines the current public installation wording for OpenClaw.

## One-Line Wording

- `status`: `preview`
- `closure_level`: `runtime-core-preview`
- `install_mode` / `check_mode`: `runtime-core`
- default target root: `OPENCLAW_HOME` or `~/.openclaw`

Contract sources:

- `adapters/index.json`
- `adapters/openclaw/host-profile.json`
- `adapters/openclaw/closure.json`
- `adapters/openclaw/settings-map.json`

## Three Paths (attach / copy / bundle)

### Attach Path

Goal: connect and validate an existing OpenClaw root.

Example:

```bash
bash ./check.sh --host openclaw --target-root "${OPENCLAW_HOME:-$HOME/.openclaw}" --profile full --deep
```

### Copy Path

Goal: copy the runtime-core payload into `OPENCLAW_HOME` or `~/.openclaw` through the install entrypoint.

Example:

```bash
bash ./scripts/bootstrap/one-shot-setup.sh --host openclaw --profile full
bash ./check.sh --host openclaw --profile full --deep
```

### Bundle Path

Goal: consume the OpenClaw runtime-core preview package through distribution manifests.

Manifest entrypoints:

- `dist/host-openclaw/manifest.json`
- `dist/manifests/vibeskills-openclaw.json`

## Current Focus

- describe OpenClaw with the `preview` / `runtime-core-preview` / `runtime-core` wording
- keep the target root consistent as `OPENCLAW_HOME` or `~/.openclaw`
- focus on runtime-core payload install, validation, and distribution
- keep host-local configuration on the OpenClaw side
