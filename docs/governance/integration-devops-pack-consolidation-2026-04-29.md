# Integration DevOps Pack Consolidation

Date: 2026-04-29

## Decision

`integration-devops` is consolidated as a deployment, integration, CI/CD, runtime diagnostics, and local process hygiene pack.

This pass preserves the existing six-stage Vibe runtime. It does not introduce primary/secondary skills, advisory skills, consult mode, or stage-assistant execution semantics.

Skill usage remains binary:

```text
skill_routing.selected -> skill_usage.used / unused
```

## Before / After

| Surface | Before | After |
| --- | ---: | ---: |
| `skill_candidates` | 13 | 6 |
| `route_authority_candidates` | 0 | 6 |
| `stage_assistant_candidates` | 0 | 0 |
| `task_allow` | planning, coding, debug, review | planning, coding, debug |
| physical directory deletion | 0 | 0 |

`route_authority_candidates` is a compatibility/documentation mirror of `skill_candidates`. It is not a second execution model.

## Retained Route Authorities

| Skill id | Route authority boundary |
| --- | --- |
| `gh-fix-ci` | GitHub Actions, CI failures, workflow logs, failing checks, and pipeline repair |
| `mcp-integration` | MCP server/client integration, `.mcp.json`, MCP transport setup, and MCP wiring |
| `sentry` | Sentry issue diagnostics, production error triage, release/environment tagging, and alert investigation |
| `vercel-deploy` | Vercel deployment, preview URLs, environment variables, logs, and production deploy checks |
| `netlify-deploy` | Netlify deployment, preview links, redirects, build settings, and production deploy checks |
| `node-zombie-guardian` | Auditing and cleaning orphan/zombie Node processes owned by VCO or local dev servers |

## Moved Out Of Integration DevOps

| Skill | Action | Rationale |
| --- | --- | --- |
| `gh-address-comments` | Removed from this pack routing surface | PR review/comment response is a code review workflow, not core integration/devops ownership. |
| `performance-testing` | Removed from this pack routing surface | BenchmarkDotNet/performance measurement is a narrow performance/testing workflow, not deployment or integration ownership. |
| `security-best-practices` | Removed from this pack routing surface | Security review belongs to the security/code-quality surface. |
| `security-ownership-map` | Removed from this pack routing surface | Security ownership and bus-factor analysis belongs to security/code-quality or review governance. |
| `security-threat-model` | Removed from this pack routing surface | Threat modeling belongs to security/code-quality or research-design review, not DevOps routing. |
| `smart-file-writer` | Removed from this pack routing surface | File-write/permission recovery is a utility/debug helper, not integration/devops route ownership. |
| `yeet` | Removed from this pack routing surface | Commit/push/PR publishing is an explicit git/PR workflow, not default deployment routing. |

The moved-out skill directories remain on disk. This pass performs no physical deletion and no asset migration.

## Protected Boundaries

Positive examples that must remain inside `integration-devops`:

- `排查GitHub Actions CI失败并修复` -> `integration-devops / gh-fix-ci`
- `需要接入MCP server并配置.mcp.json` -> `integration-devops / mcp-integration`
- `查看Sentry线上报错并汇总根因` -> `integration-devops / sentry`
- `请把应用部署到Vercel并返回访问链接` -> `integration-devops / vercel-deploy`
- `请部署到Netlify并生成预览链接` -> `integration-devops / netlify-deploy`
- `审计并清理VCO托管的僵尸node进程` -> `integration-devops / node-zombie-guardian`

Negative examples that must not route to `integration-devops`:

- PR review comment response.
- Security best-practices review.
- Threat modeling.
- Security ownership / bus-factor analysis.
- Generic permission or file-write failure repair.
- BenchmarkDotNet performance testing.
- One-shot commit/push/open-PR publishing.

## Verification

Required focused and broader checks:

```powershell
python -m pytest tests/runtime_neutral/test_integration_devops_pack_consolidation.py -q
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-skill-index-routing-audit.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-pack-regression-matrix.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-pack-routing-smoke.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-offline-skills-gate.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-config-parity-gate.ps1 -WriteArtifacts
git diff --check
```
