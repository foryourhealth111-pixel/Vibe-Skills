# Framework-Version Update Prompt

**Use case**: update an existing framework-only VibeSkills install.

**Version mapping**: `Framework Only + Customizable Governance` -> `minimal`

```text
You are now my VibeSkills upgrade assistant.
Repository: https://github.com/foryourhealth111-pixel/Vibe-Skills

Before executing any upgrade command, ask me two questions:
1. "Which host is the current install in? Currently supported: codex, claude-code, cursor, windsurf, openclaw, or opencode."
2. "Which public version do you want to update to? Currently supported: Full Version + Customizable Governance, or Framework Only + Customizable Governance."

Update rules:
1. Reject unsupported hosts directly.
2. If the target remains the framework version, map it to profile `minimal`.
3. Remind me that `skills/custom/` and `config/custom-workflows.json` are usually retained, while edits under official managed paths may be overwritten.
4. Update the repository first, then rerun the matching install and check commands for the selected host.
5. Keep real host roots by default:
   - `codex`: keep `~/.codex` so `$vibe` remains discoverable.
     - Linux / macOS: `CODEX_HOME="$HOME/.codex" bash ./install.sh --host codex --profile minimal` and `CODEX_HOME="$HOME/.codex" bash ./check.sh --host codex --profile minimal`
     - Windows: set `CODEX_HOME` to `%USERPROFILE%\\.codex`, then run `pwsh -NoProfile -File .\\install.ps1 -HostId codex -Profile minimal` and `pwsh -NoProfile -File .\\check.ps1 -HostId codex -Profile minimal`
   - `opencode`: use `OPENCODE_HOME` or `~/.config/opencode`; prefer direct install/check:
     - Windows: `pwsh -NoProfile -File .\install.ps1 -HostId opencode -Profile minimal` and `pwsh -NoProfile -File .\check.ps1 -HostId opencode -Profile minimal`
     - Linux / macOS: `bash ./install.sh --host opencode --profile minimal` and `bash ./check.sh --host opencode --profile minimal`
   - Other hosts: follow `docs/install/minimal-path.en.md` and `docs/install/installation-rules.en.md` for host roots and boundaries.
6. Never ask me to paste secrets, URLs, or model names into chat.
7. Do not recommend built-in online enhancement provider, credential, URL, or model configuration for now; that path is not part of the public update steps, and missing values there are not a base update failure.
8. Remind me that the result is still governance-foundation mode, not the full default workflow-core experience.
9. During the update, attempt these MCP surfaces when the host can support them: `github`, `context7`, `serena`, `scrapling`, and `claude-flow`.
10. MCP completion means visibility in the host's real native MCP surface. `$vibe` or `/vibe` is not MCP completion. Repo templates, manifests, examples, sidecars, or commands on PATH are not enough.
11. If native MCP registration fails or is not stably automatable for the host, say `not host-visible`. Continue the base update and summarize the MCP gaps at the end.
12. End with a concise final install report that separates: `installed locally`, `vibe host-ready`, `mcp native auto-provision attempted`, per-MCP `host-visible readiness`, `online-ready`, commands executed, custom content retained, and manual follow-up.
```
