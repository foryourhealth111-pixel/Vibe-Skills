# Terminology Governance

Date: 2026-04-30

## Active Model

Current routing and usage language is:

```text
skill_candidates -> selected skill -> used / unused
```

This vocabulary is the active product and implementation language for new routing work.

## Active Terms

| Term | Meaning |
| --- | --- |
| `skill` | A bounded capability with a `SKILL.md` entrypoint. |
| `skill_candidates` | The active pack field listing skills that may be selected for that pack. |
| `selected skill` | A skill selected for the current task, stage, or bounded work unit. |
| `skill_routing.selected` | Runtime evidence that a skill was selected into the governed workflow. |
| `skill_usage.used` | Runtime evidence that a selected skill was loaded and materially shaped artifacts. |
| `skill_usage.unused` | Runtime evidence that a selected skill was not materially used, with a reason. |
| `legacy_skill_routing` | Legacy compatibility container used only to read older runtime artifacts. |

## Deprecated Terms

Do not introduce these names as active concepts in new docs, config, tests, or runtime output:

| Deprecated name | Replacement |
| --- | --- |
| `route_authority` / `route owner` / `direct owner` | `skill_candidates` or `selected skill` |
| `primary route` / `primary skill` / `secondary skill` | `selected skill` or `candidate skill` |
| `stage_assistant` | Legacy compatibility only |
| `specialist Skills` as an active routing class | `selected Skills` |
| `approved dispatch` as evidence of use | `skill_usage.used` / `skill_usage.unused` |
| `主路由` / `主路线` / `主技能` / `次技能` | `候选 skill` or `选中 skill` |
| `阶段助手` / `辅助专家` / `咨询专家` / `专家助手` | Do not use as an active concept |

## Legacy Compatibility

Old runtime artifacts may still contain `specialist_dispatch`, `specialist_recommendations`, `stage_assistant_hints`, `route_authority_candidates`, or `stage_assistant_candidates`.

Readers may keep compatibility paths while old fixtures exist. New active configuration must not write those pack fields, and new public docs must not present those names as current routing concepts.

## Evidence Rule

Selection and usage are separate:

- `skill_routing.selected` means a skill was selected.
- `skill_usage.used` means a selected skill was loaded and materially shaped artifacts.
- `skill_usage.unused` means a selected skill did not materially shape artifacts.

Do not claim a skill was used from candidate, selected, or dispatch data alone.
