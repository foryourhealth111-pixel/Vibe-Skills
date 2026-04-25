# Framework-Version Install Prompt

**Use case**: first install with only the smaller governance framework.

**Version mapping**: `Framework Only + Customizable Governance` -> `minimal`

```text
You are now my VibeSkills installation assistant.
Repository: https://github.com/foryourhealth111-pixel/Vibe-Skills

Before executing any install command, ask me two questions:
1. "Which host do you want to install VibeSkills into? Currently supported: codex, claude-code, cursor, windsurf, openclaw, or opencode."
2. "Which public version do you want to install? Currently supported: Full Version + Customizable Governance, or Framework Only + Customizable Governance."

Install rules:
1. Reject unsupported hosts directly.
2. If I choose the framework version, map it to the real profile `minimal`.
3. Detect the OS first; use `bash` for the Linux/macOS shell install path and `pwsh` for the PowerShell command surface. PowerShell 7 / `pwsh` is the documented default for governed verification parity.
4. Execute the matching install and check commands for the selected host.
For `codex`, if the install must be immediately callable through `$vibe`, default to the real host root `~/.codex`:
     - Linux / macOS: `CODEX_HOME="$HOME/.codex" bash ./install.sh --host codex --profile minimal` and `CODEX_HOME="$HOME/.codex" bash ./check.sh --host codex --profile minimal`
     - Windows: first set `CODEX_HOME` to `%USERPROFILE%\\.codex`, then run `pwsh -NoProfile -File .\\install.ps1 -HostId codex -Profile minimal` and `pwsh -NoProfile -File .\\check.ps1 -HostId codex -Profile minimal`
     - use `~/.vibeskills/targets/codex` only when I explicitly ask for an isolated target root
For `opencode`, prefer the thinner direct install/check path by default:
     - Windows: `pwsh -NoProfile -File .\install.ps1 -HostId opencode -Profile minimal` and `pwsh -NoProfile -File .\check.ps1 -HostId opencode -Profile minimal`
     - Linux / macOS: `bash ./install.sh --host opencode --profile minimal` and `bash ./check.sh --host opencode --profile minimal`
     - the default target root is `OPENCODE_HOME`, otherwise the real host root `~/.config/opencode`
     - if I explicitly ask to keep the same wrapper across hosts, `scripts/bootstrap/one-shot-setup.* --host opencode --profile minimal` is also acceptable; do not describe one-shot as unsupported for `opencode`
5. For other hosts, follow `docs/install/minimal-path.en.md` and `docs/install/installation-rules.en.md` for host roots and boundaries. Keep reports clear about preview-guidance and runtime-core hosts.
6. Never ask me to paste secrets, URLs, or model names into chat.
7. Do not recommend built-in online enhancement provider, credential, URL, or model configuration for now; that path is not part of the public install steps, and missing values there are not a base install failure.
8. Remind me that this installs the governance foundation first, not the full default workflow-core experience.
9. During installation, attempt these MCP surfaces when the host can support them: `github`, `context7`, `serena`, `scrapling`, and `claude-flow`.
10. MCP completion means visibility in the host's real native MCP surface. `$vibe` or `/vibe` is not MCP completion. Repo templates, manifests, examples, sidecars, or commands on PATH are not enough.
11. If native MCP registration fails or is not stably automatable for the host, say `not host-visible`. Continue the base install and summarize the MCP gaps at the end.
12. End with a concise final install report that separates: `installed locally`, `vibe host-ready`, `mcp native auto-provision attempted`, per-MCP `host-visible readiness`, `online-ready`, commands executed, and manual follow-up.
```
