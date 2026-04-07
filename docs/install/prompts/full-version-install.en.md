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
4. For `codex`, still use `--host codex --profile full`, but default to the real Codex host root so `$vibe` is directly discoverable after install:
   - the real host root here is `~/.codex`
   - Linux / macOS: `CODEX_HOME="$HOME/.codex" bash ./install.sh --host codex --profile full` and `CODEX_HOME="$HOME/.codex" bash ./check.sh --host codex --profile full`
   - Windows: first set `CODEX_HOME` to the real host root `%USERPROFILE%\\.codex`, then run `pwsh -NoProfile -File .\\install.ps1 -HostId codex -Profile full` and `pwsh -NoProfile -File .\\check.ps1 -HostId codex -Profile full`
   - only use `~/.vibeskills/targets/codex` when I explicitly ask for an isolated target root, or when Codex is already pointed there on purpose
   - describe it as the strongest governed path, while making clear that hooks remain frozen
5. For `claude-code`, run `--host claude-code --profile full` and describe it as a supported install-and-use path that defaults to the real host root `~/.claude`:
   - Linux / macOS: `CLAUDE_HOME="$HOME/.claude" bash ./install.sh --host claude-code --profile full` and `CLAUDE_HOME="$HOME/.claude" bash ./check.sh --host claude-code --profile full`
   - Windows: first set `CLAUDE_HOME` to `%USERPROFILE%\\.claude`, then run `pwsh -NoProfile -File .\\install.ps1 -HostId claude-code -Profile full` and `pwsh -NoProfile -File .\\check.ps1 -HostId claude-code -Profile full`
   - also state that it preserves the real `~/.claude/settings.json` while merging a bounded managed `vibeskills` settings surface
6. For `cursor`, run `--host cursor --profile full` and describe it as a preview-guidance path that defaults to the real host root `~/.cursor`:
   - Linux / macOS: `CURSOR_HOME="$HOME/.cursor" bash ./install.sh --host cursor --profile full` and `CURSOR_HOME="$HOME/.cursor" bash ./check.sh --host cursor --profile full`
   - Windows: first set `CURSOR_HOME` to `%USERPROFILE%\\.cursor`, then run `pwsh -NoProfile -File .\\install.ps1 -HostId cursor -Profile full` and `pwsh -NoProfile -File .\\check.ps1 -HostId cursor -Profile full`
   - do not describe this as taking over the full real `~/.cursor/settings.json`
7. For `windsurf`, run `--host windsurf --profile full` and describe it as a runtime-core path; mention the default target root `WINDSURF_HOME`, otherwise the real host root `~/.codeium/windsurf`, and that the repo only owns shared runtime payload plus `.vibeskills/*` sidecar state.
8. For `openclaw`, run `--host openclaw --profile full` and describe it as a preview runtime-core adapter path; mention the default target root `OPENCLAW_HOME` or the real host root `~/.openclaw`, plus the attach / copy / bundle paths.
9. For `opencode`, prefer the thinner direct install/check path by default:
   - Windows: `pwsh -NoProfile -File .\install.ps1 -HostId opencode -Profile full` and `pwsh -NoProfile -File .\check.ps1 -HostId opencode -Profile full`
   - Linux / macOS: `bash ./install.sh --host opencode --profile full` and `bash ./check.sh --host opencode --profile full`
   - describe it as a preview-guidance adapter path with default target root `OPENCODE_HOME`, otherwise the real host root `~/.config/opencode`
   - state clearly that direct install/check writes runtime payload, `.vibeskills/*` sidecars, and `opencode.json.example`, but does not take ownership of the real `~/.config/opencode/opencode.json`, provider credentials, plugin installation, or MCP trust
   - if I explicitly ask to keep the same wrapper across hosts, `scripts/bootstrap/one-shot-setup.* --host opencode --profile full` is also acceptable; do not describe one-shot as unsupported for `opencode`
10. Never ask me to paste secrets, URLs, or model names into chat.
11. If I later want AI-governance online capability, you must recommend the real key names first:
   - `VCO_INTENT_ADVICE_API_KEY`, optional `VCO_INTENT_ADVICE_BASE_URL`, and `VCO_INTENT_ADVICE_MODEL` for the built-in advice path
   - `VCO_VECTOR_DIFF_API_KEY` / `VCO_VECTOR_DIFF_BASE_URL` / `VCO_VECTOR_DIFF_MODEL` separately when vector diff embeddings are desired (not required, vector diff degrades gracefully)
   - note that legacy `OPENAI_*` names are no longer used as automatic fallbacks for the built-in runtime
12. Distinguish “installed locally” from “online-ready”.
13. After installation, proactively give me one quick check command for “is AI governance configured?”:
   - Windows: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-router-ai-connectivity-gate.ps1 -TargetRoot "<resolved host root>" -WriteArtifacts`
   - Linux / macOS: `python3 ./scripts/verify/runtime_neutral/router_ai_connectivity_probe.py --target-root "<resolved host root>" --write-artifacts`
   - if the user already has PowerShell 7, an equivalent `pwsh` command is acceptable, but `pwsh` must not be treated as the default prerequisite.
   - also add one short sentence: `ok` means AI governance advice is online; `missing_credentials`, `missing_model`, or `provider_rejected_request` mean local or online readiness is still incomplete.
14. End with a concise report covering host, public version, real profile, commands executed, completed parts, and manual follow-up.

Supplemental MCP auto-provision rules:
- During installation, you must attempt these five MCP surfaces: `github`, `context7`, `serena`, `scrapling`, and `claude-flow`
- The completion target for these MCPs must be the host's real **native MCP surface**, not a repo template, manifest, sidecar, example config, or `$vibe` discoverability
- `$vibe` or `/vibe` proves governed runtime entry only and is **not MCP completion**
- `mcp/servers.template.json`, plugin manifests, `*.json.example`, `.vibeskills/*` sidecars, and a command merely existing on PATH do not by themselves prove MCP is ready
- Prefer host-native registration first for `github`, `context7`, and `serena`; prefer scripted CLI / stdio installation first for `scrapling` and `claude-flow`
- If native auto-registration fails, or the current host does not expose a stable officially supportable auto-registration interface, you must report that the MCP is still `not host-visible` rather than soft-claiming success through `$vibe`, templates, or sidecars
- If any MCP attempt fails, do not interrupt me repeatedly mid-flow; continue the install path and summarize failures only in the final install report
- The final install report must explicitly separate `installed locally`, `vibe host-ready`, `mcp native auto-provision attempted`, per-MCP `host-visible readiness`, and `online-ready`
```
