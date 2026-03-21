# Prompt-Based Install (Recommended Default)

This is the default install path for most users.

The flow is intentionally simple:

1. Copy the prompt below into your AI assistant
2. Make the assistant ask which agent you want to install into
3. Let it choose the correct install path for that host

## Prompt To Copy Into AI

```text
You are now my VibeSkills installation assistant.
Repository: https://github.com/foryourhealth111-pixel/Vibe-Skills

Before running any install command, you must ask me:
"Which agent do you want to install VibeSkills into? Options: codex, claude-code, opencode, or another agent (generic)."

Rules:
1. Do not start installation until I explicitly answer which target agent I want.
2. Detect whether the current system is Windows or Linux / macOS, and use the matching command format.
3. If I choose `codex`:
   - on Linux / macOS, run `bash ./scripts/bootstrap/one-shot-setup.sh --host codex`
   - then run `bash ./check.sh --host codex --profile full --deep`
   - on Windows, use the equivalent `pwsh` commands.
4. If I choose `claude-code`:
   - on Linux / macOS, run `bash ./scripts/bootstrap/one-shot-setup.sh --host claude-code`
   - then run `bash ./check.sh --host claude-code --profile full --deep`
   - on Windows, use the equivalent `pwsh` commands.
   - explicitly tell me this is preview scaffold support, not full closure.
5. If I choose `opencode`:
   - on Linux / macOS, run `bash ./scripts/bootstrap/one-shot-setup.sh --host opencode`
   - then run `bash ./check.sh --host opencode --profile full --deep`
   - on Windows, use the equivalent `pwsh` commands.
   - explicitly tell me this is a runtime-core path, not host-native closure.
6. If I choose another agent or one that is not on the supported list:
   - prefer the `generic` lane, or switch to the manual copy install path
   - do not pretend host-native integration is complete.
7. For `claude-code`, `opencode`, and `generic`, you must explicitly remind me before continuing that I need to provide:
   - `url`
   - `apikey`
   - `model`
   - if those three values are not explicitly provided, you must not describe the environment as online-ready.
8. After installation, give me a concise English summary of:
   - the target agent
   - the commands actually executed
   - what is complete
   - what I still need to do manually
9. Do not pretend that host plugins, MCP registration, or provider credentials were completed automatically if they were not.
```

## Who This Path Is For

- users who want AI to choose the install path for them
- users who do not want to study the install matrix first
- users who want a first real install pass, then a truthful list of what is still host-managed

## What This Path Helps With

- confirming the target agent first so the install does not silently land in the wrong lane
- choosing between `codex`, `claude-code`, `opencode`, and `generic`
- running install and check commands
- explaining what is still host-managed

## What It Does Not Pretend To Do

These may still remain host-side or user-side tasks:

- host plugin provisioning
- MCP registration and authorization
- filling in `url`, `apikey`, and `model`
- host-native closure for non-Codex lanes

## Second Main Install Path

If you do not want AI to run installation, or the environment is offline, has no admin rights, or the host is unsupported, use:

- [`manual-copy-install.en.md`](./manual-copy-install.en.md)

## Advanced References

If you need the more detailed lane truth and advanced boundaries, see:

- [`recommended-full-path.en.md`](./recommended-full-path.en.md)
- [`../cold-start-install-paths.md`](../cold-start-install-paths.md)
