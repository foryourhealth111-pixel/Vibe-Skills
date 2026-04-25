# Custom Skill / Workflow Governance Rules

Goal: allow extension without losing control. You may add custom capabilities, but they must not break the canonical runtime or the canonical router.

The default recommended lane remains `workflow`, because it keeps the governed workflow core intact while still allowing custom extensions to be admitted gradually.

## Hard Rules That Must Not Be Broken

1. There is only one runtime: `vibe`
2. There is only one route authority: canonical router
3. Custom content can join routing only after a manifest declaration
4. A directory must not become active just because it exists
5. An external repository must not become a live route source directly

## Governed Directory Conventions

- content directory: `<TARGET_ROOT>/skills/custom/<name>/`
- workflow manifest: `<TARGET_ROOT>/config/custom-workflows.json`
- custom-skill manifest, if enabled: `<TARGET_ROOT>/config/custom-skills.json`

## Update Governance Rules

### Custom Surfaces Users May Keep Long Term

The following paths should be treated as user-owned custom-governance surfaces and should be preserved first during updates:

- `skills/custom/`
- `config/custom-workflows.json`
- `config/custom-skills.json` (if enabled)

### Official Managed Surfaces That Should Not Be Edited Directly

The following paths are official managed surfaces and may be rewritten during overwrite-style updates:

- `skills/vibe/`
- official skill directories such as `skills/<official-skill>/`
- official `mcp/`
- official `rules/`
- official `agents/templates/`

Rules:

- extend through user custom paths
- do not expect direct edits to official managed directories to survive overwrite updates automatically

### Profile-Change Governance

When the installed version changes together with the profile, you must re-check the custom workflow `requires` fields.

Especially:

- downgrading from `full` to framework-only (`minimal`)
- downgrading from `workflow` to framework-only (`minimal`)

These changes most often cause:

- `custom_dependencies_missing`
- what looks like routing failure but is actually a dependency break

### Required Validation After Updates

1. rerun `check --deep`
2. verify that the manifest is still valid
3. verify that the custom workflow path and `SKILL.md` still exist
4. verify that `requires` is still satisfied

If validation fails, inspect in this order:

1. whether `config/custom-workflows.json` still exists
2. whether `skills/custom/<id>/SKILL.md` still exists
3. whether the required skills still exist in the current install profile
4. whether custom changes were mistakenly written into official managed directories

## Routing And Trigger Governance

- default `trigger_mode`: `advisory`
- use `explicit_only` for high-risk or low-frequency flows
- use `auto` only when evidence is strong enough

Every admitted custom workflow must provide:

- `keywords`
- `intent_tags`
- `non_goals`
- `requires`

If those fields are missing, the workflow must not enter a callable state.

## Dependency Governance

Custom workflows must not assume that baseline capabilities are always present.
Declare dependencies explicitly through `requires`, for example:

- `vibe`
- `writing-plans`
- `systematic-debugging`

If dependencies are missing, doctor/check should report `custom_dependencies_missing` instead of silently degrading.

## Readiness Wording Governance

Keep these states clearly separated:

- `lane_complete`
- `lane_complete_with_optional_gaps`
- `core_install_incomplete`
- `custom_manifest_invalid`
- `custom_dependencies_missing`

If provider, MCP, or host-side manual items are still missing, do not claim online readiness.

## Codex And Claude Code Boundaries

- Codex: official governed host; hooks are not installed right now
- Claude Code: supported install-and-use path; the installer preserves existing Claude settings while writing a bounded managed `vibeskills` stanza

For both hosts, never ask users to paste key/url/model values into chat. Only guide them to local `settings.json` `env` fields or local environment variables.

## Governance AI Online Layer Boundary

Baseline online provider access does not automatically mean the governance AI online layer is ready.

The public install flow does not currently expose built-in online enhancement configuration. Custom Skill governance docs should not list provider, credential, URL, or model configuration for users, and missing values for that path must not be described as a custom Skill onboarding failure.

If related online capabilities are not configured through the public path, describe them only as "base install complete" or "related online capability not ready/not verified", not as online enhancement ready.

## Minimal Acceptance Checklist

- manifest schema validation passes
- undeclared directories do not become routable
- explicit user choice can override automatic suggestions
- canonical `vibe` and workflow-core priority remain stable
- doctor status matches the real configuration without overstating readiness
