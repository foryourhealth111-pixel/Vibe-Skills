# VCO Bootstrap Doctor Gate

- Gate Result: **PASS**
- Readiness State: **manual_actions_pending**
- Blocking Issues: `0`
- Manual Actions Pending: `6`
- Warnings: `1`
- Target Root: `<proof-target-root>`
- MCP Profile: `full`
- MCP Active File Exists: `False`

## Settings

- `VCO_INTENT_ADVICE_API_KEY`: `missing` via `missing`
- `VCO_INTENT_ADVICE_MODEL`: `missing` via `missing`
- `VCO_VECTOR_DIFF_API_KEY`: `missing` via `missing`
- `VCO_VECTOR_DIFF_MODEL`: `missing` via `missing`

## Plugin Readiness

- `serena`: status=`platform_plugin_required` install_mode=`manual-host` next_step=`Provision via host-native MCP tooling if your Claude host exposes official MCP registration.`
- `context7`: status=`platform_plugin_required` install_mode=`manual-host` next_step=`Provision via host-native MCP tooling if your Claude host exposes official MCP registration.`
- `github`: status=`platform_plugin_required` install_mode=`manual-host` next_step=`Provision via host-native MCP tooling if your Claude host exposes official MCP registration.`
- `prompts-chat`: status=`platform_plugin_required` install_mode=`manual-host` next_step=`Provision prompts.chat MCP/API integration in the Claude host runtime; optional, used by prompt-lookup/prompt-overlay.`
- `claude-flow`: status=`ready` install_mode=`scripted` next_step=`none`
- `xan`: status=`platform_plugin_required` install_mode=`manual-host` next_step=`Install xan CLI manually (recommended on Windows: scoop install xan) for large CSV acceleration.`
- `fuck-u-code`: status=`platform_plugin_required` install_mode=`manual-host` next_step=`Optional quality-debt analyzer for quality-debt-overlay; install manually only if you want external analyzer hints beyond built-in risk scoring.`
- `ivy`: status=`platform_plugin_required` install_mode=`manual-host` next_step=`Optional framework-interop backend for framework-interop-overlay; install manually in Python environment (for example: pip install ivy).`
- `leetcuda`: status=`platform_plugin_required` install_mode=`manual-host` next_step=`Optional methodology source for cuda-kernel-overlay; no runtime dependency required. Keep GPL-3.0 boundary: do not vendor upstream code.`

## External Tools

- `git`: present=`True` required_for=`bootstrap`
- `npm`: present=`True` required_for=`claude-flow, ralph-wiggum`
- `python`: present=`True` required_for=`default-mcp:scrapling, ivy`
- `claude-flow`: present=`True` required_for=`mcp:claude-flow`
- `scrapling`: present=`True` required_for=`default-full-profile-mcp:scrapling`
- `xan`: present=`False` required_for=`csv-acceleration`

## Enhancement Surfaces

- `cognee`: role=`default_long_term_graph_memory_owner` status=`declared_default_owner` next_step=`Optional enhancement lane. Enable Cognee only when you want governed cross-session graph memory; keep state_store as the session truth-source.`

## MCP Servers

- `github`: mode=`plugin` status=`platform_plugin_required` next_step=`Provision the corresponding host plugin in the Claude runtime.`
- `context7`: mode=`plugin` status=`platform_plugin_required` next_step=`Provision the corresponding host plugin in the Claude runtime.`
- `serena`: mode=`plugin` status=`platform_plugin_required` next_step=`Provision the corresponding host plugin in the Claude runtime.`
- `scrapling`: mode=`stdio` status=`ready` next_step=`none`
- `claude-flow`: mode=`stdio` status=`ready` next_step=`none`

## External Integration Surfaces

- `Activepieces MCP Server`: status=`prewired_setup_required` risk=`tier3_open_world_or_high_impact` confirm_required=`True` next_step=`Set ACTIVEPIECES_MCP_TOKEN, replace the placeholder project endpoint, and enable the MCP surface only when you need governed external automation.`
- `Composio Tool Router`: status=`prewired_setup_required` risk=`tier3_open_world_or_high_impact` confirm_required=`True` next_step=`Set COMPOSIO_API_KEY, create a session-scoped COMPOSIO_SESSION_MCP_URL, and keep Composio actions confirm-gated.`

## Secret Surfaces

- `ACTIVEPIECES_MCP_TOKEN`: status=`not_configured` storage=`environment, vault`
- `COMPOSIO_API_KEY`: status=`not_configured` storage=`environment, vault`
- `COMPOSIO_SESSION_MCP_URL`: status=`runtime_not_set` storage=`runtime`

