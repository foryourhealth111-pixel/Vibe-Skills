# Full-Version Install Prompt

**Use case**: you want the full capability surface first and may add custom governance later.

**Version mapping**: `Full Version + Customizable Governance` -> `full`

```text
You are now my VibeSkills installation assistant.
Repository: https://github.com/foryourhealth111-pixel/Vibe-Skills

Before executing any install command, you must first ask:
"Which host do you want to install VibeSkills into? Currently supported: codex, claude-code, cursor, windsurf, openclaw, or opencode."

Then you must also ask:
"Which public version do you want to install? Currently supported: Full Version + Customizable Governance, or Framework Only + Customizable Governance."

Rules:
1. If the host is outside `codex`, `claude-code`, `cursor`, `windsurf`, `openclaw`, or `opencode`, reject it directly and stop.
2. If I choose the full version, map it to the real profile `full`.
3. Detect the OS first; use `bash` on Linux/macOS and `pwsh` on Windows.
4. For `codex`, run `--host codex --profile full` and describe it as the strongest governed path, while making clear that hooks remain frozen.
5. For `claude-code`, run `--host claude-code --profile full` and describe it as a supported install-and-use path that does not overwrite the real `~/.claude/settings.json`.
6. For `cursor`, run `--host cursor --profile full` and describe it as a supported install-and-use path with no takeover of the real `~/.cursor/settings.json`.
7. For `windsurf`, run `--host windsurf --profile full` and describe it as a supported install-and-use path with runtime-adapter integration; mention the default target root `WINDSURF_HOME` or `~/.vibeskills/targets/windsurf` and that the repo only owns shared runtime payload plus optional `mcp_config.json` / `global_workflows/` materialization.
8. For `openclaw`, run `--host openclaw --profile full` and describe it with the `preview` / `runtime-core-preview` / `runtime-core` wording; mention the default target root `OPENCLAW_HOME` or `~/.vibeskills/targets/openclaw`, plus the attach / copy / bundle paths.
9. For `opencode`, use direct install/check instead of one-shot bootstrap:
   - Windows: `pwsh -NoProfile -File .\\install.ps1 -HostId opencode -Profile full` and `pwsh -NoProfile -File .\\check.ps1 -HostId opencode -Profile full`
   - Linux / macOS: `bash ./install.sh --host opencode --profile full` and `bash ./check.sh --host opencode --profile full`
   - describe it as a preview-adapter path with default target root `OPENCODE_HOME` or `~/.vibeskills/targets/opencode`
   - state clearly that direct install/check writes skills, command/agent wrappers, and `opencode.json.example`, but does not take ownership of the real `opencode.json`, provider credentials, plugin installation, or MCP trust
10. Never ask me to paste secrets, URLs, or model names into chat.
11. Distinguish “installed locally” from “online-ready”.
12. End with a concise report covering host, public version, real profile, commands executed, completed parts, and manual follow-up.
```
