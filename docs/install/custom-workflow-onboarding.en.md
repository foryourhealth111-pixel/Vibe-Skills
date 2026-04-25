# Custom Workflow Onboarding Guide (Governed Onboarding)

This document describes one governed onboarding path only: make your workflow callable by the canonical router without weakening route authority.

## Prerequisites

Recommended install lanes:

- `workflow` (default recommendation)
- or `full`

The framework-only profile (`minimal`) can also admit custom workflows, but then you are responsible for filling in the missing workflow-core dependencies yourself. Otherwise you may get a successful declaration with limited callable value.

## Supported Onboarding Path

1. Create the workflow content under the target host root:

- `<TARGET_ROOT>/skills/custom/<name>/SKILL.md`

2. Declare the manifest under the target host root:

- `<TARGET_ROOT>/config/custom-workflows.json`

3. Let the router read manifest entries only. Do not rely on automatic directory scanning.

## Minimal Manifest Example

```json
{
  "version": 1,
  "workflows": [
    {
      "id": "my-domain-flow",
      "path": "skills/custom/my-domain-flow",
      "enabled": true,
      "trigger_mode": "advisory",
      "keywords": ["experiment retrospective", "error analysis", "model evaluation"],
      "intent_tags": ["ml", "research", "evaluation"],
      "preferred_stages": ["deep_interview", "xl_plan", "plan_execute"],
      "requires": ["vibe", "writing-plans"],
      "priority": 60,
      "non_goals": ["general chat", "tiny edit"]
    }
  ]
}
```

## `trigger_mode` Recommendation

Allowed values:

- `explicit_only`
- `advisory` (default recommendation)
- `auto`

`advisory` is the safest default because it allows recommendation without competing for route authority.

## How To Make It Callable At The Right Time

- define `keywords`, `intent_tags`, and `non_goals` clearly
- declare official dependencies through `requires` instead of assuming them implicitly
- keep `priority` below the canonical core path
- let explicit user choice win every time

Frozen priority order:

1. explicit user choice
2. canonical `vibe`
3. official workflow core
4. admitted custom workflows
5. domain packs / overlays

## Common Misunderstandings

- misunderstanding: copying a directory means onboarding is complete
- correct: the workflow becomes routable only after a manifest declaration

- misunderstanding: a custom workflow can replace the canonical router
- correct: a custom workflow can participate, but it cannot take route authority

- misunderstanding: declaration means online readiness
- correct: online readiness still depends on local provider, MCP, and host-side manual work

## Update / Overwrite-Install Notes

If you update VibeSkills later, split your content into two categories first:

### 1. Content That Usually Survives Updates

If you onboard through the governed path, the following custom content usually survives standard overwrite updates:

- `<TARGET_ROOT>/skills/custom/<workflow-id>/`
- `<TARGET_ROOT>/config/custom-workflows.json`

That is because the router reads custom workflows through manifest declarations rather than hard-coded scanning inside the official runtime.

### 2. Content That Is Easy To Overwrite

The following are official managed surfaces and should not be edited directly:

- `<TARGET_ROOT>/skills/vibe/...`
- official skill directories such as `<TARGET_ROOT>/skills/<official-skill>/`
- official governance mirrors such as runtime `config/`, `scripts/`, and `docs/`
- official `mcp/`, `rules/`, and `agents/templates/`

If you patch custom governance directly into those official paths, overwrite updates may rewrite it.

### 3. Most Stable Practice

Keep user-owned content in these two layers:

- custom workflow content: `skills/custom/<id>/`
- custom workflow manifest: `config/custom-workflows.json`

Do not patch custom governance directly into official runtime internals.

### 4. What To Check Before And After Updates

Before updating:

- back up `config/custom-workflows.json`
- back up `skills/custom/`
- record the current version and profile

During the update:

- keep the profile unchanged when possible
- if you are downgrading from `full/workflow` to `minimal`, inspect the custom workflow `requires` fields first

After the update, you must:

- rerun `check --deep`
- confirm that there is no `custom_manifest_invalid`
- confirm that there is no `custom_dependencies_missing`

### 5. Most "Deleted" Cases Are Actually Dependency Breaks

Users often assume an update deleted their custom governance, but the more common reality is:

- the custom workflow directory is still there
- the manifest is still there
- the profile changed, so the `requires` dependencies are no longer satisfied

For example, if you depended on `writing-plans` or `systematic-debugging` and later downgraded to framework-only, doctor/check may correctly report missing dependencies rather than silently absorbing the route.

### 6. One-Line Upgrade Principle

To keep custom governance stable across updates:

- keep custom content in `skills/custom`
- keep custom declarations in `config/custom-workflows.json`
- do not edit official runtime or official skill directories directly
- rerun `check --deep` immediately after the update

## User Prompt Template For Onboarding

Use the following prompt if you want an assistant to onboard a workflow in the governed way:

```text
Please onboard my workflow into VibeSkills using the governed path. Do not create a second routing system.
Target host: codex, claude-code, cursor, windsurf, openclaw, or opencode.
Please:
1) check whether the lane is workflow/full, and if not, recommend the migration path;
2) generate a SKILL.md draft under <TARGET_ROOT>/skills/custom/<workflow-id>/;
3) add a manifest entry to <TARGET_ROOT>/config/custom-workflows.json (default trigger_mode: advisory);
4) validate requires/keywords/non_goals completeness;
5) run check/doctor and report results in a truth-first way.
Do not ask me to paste any API key, URL, or model into chat.
```

## User Prompt Templates For Upgrades

### Upgrade Prompt For Full Install + Custom Governance

```text
Please update my current VibeSkills install.
Target host: codex, claude-code, cursor, windsurf, openclaw, or opencode.
Current public version: Full Version + Customizable Governance.
Please:
1) check whether `skills/custom/` and `config/custom-workflows.json` exist;
2) explain which content usually survives and which official managed paths may be overwritten;
3) keep this update on `full` and do not accidentally downgrade it to `minimal`;
4) run `check --deep` after the update;
5) report in a truth-first way:
   - whether the custom workflow is still present
   - whether the manifest is still valid
   - whether the default workflow core is still complete
   - whether the problem is content loss or dependency break
   - recommended next repair steps
Do not ask me to paste any API key, URL, or model into chat.
```

### Upgrade Prompt For Framework-Only + Custom Governance

```text
Please update my current VibeSkills install.
Target host: codex, claude-code, cursor, windsurf, openclaw, or opencode.
Current public version: Framework Only + Customizable Governance.
Please:
1) check whether `skills/custom/` and `config/custom-workflows.json` exist;
2) explain which content usually survives and which official managed paths may be overwritten;
3) treat this update as the framework profile `minimal`;
4) run `check --deep` after the update;
5) report in a truth-first way:
   - whether the custom workflow is still present
   - whether the manifest is still valid
   - whether the environment is still in governance-foundation mode
   - whether the problem is content loss or dependency break
   - recommended next repair steps
Do not ask me to paste any API key, URL, or model into chat.
```

## Online Configuration Reminder

The public install flow does not currently expose built-in online enhancement configuration. During custom workflow onboarding, do not ask users for providers, credentials, URLs, or model names, and do not make that path a prerequisite for completing workflow onboarding.

If those capabilities are not configured through the public path, describe them only as not ready or not verified. Do not provide concrete configuration keys.
