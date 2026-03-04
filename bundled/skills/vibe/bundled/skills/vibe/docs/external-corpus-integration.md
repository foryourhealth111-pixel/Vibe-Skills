# External Corpus Integration

This guide explains how to use an external prompt corpus (for example, `system-prompts-and-models-of-ai-tools`) to improve VCO routing quality without polluting core orchestration instructions.

## Goals

1. Extract reusable routing and execution signals from external prompt/tool artifacts.
2. Generate conservative candidate updates for `config/skill-keyword-index.json`.
3. Validate candidate changes against baseline routing metrics before any manual merge.

## Guardrails

- Treat external repositories as **read-only research inputs**.
- Do not paste raw third-party system prompts into `SKILL.md` or protocols.
- Prefer derived signals and candidate keywords over verbatim content.
- Always run the external-corpus gate before applying changes.
- Keep conflict rules (`references/conflict-rules.md`) unchanged unless explicitly reviewed.

## Workflow

### 1) Mirror external corpus into `third_party`

Example:

```powershell
git clone --depth 1 https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools.git `
  "..\third_party\system-prompts-mirror"
```

### 2) Extract structured signals

```powershell
& ".\scripts\research\extract-prompt-signals.ps1" `
  -SourceRoot ".\third_party\system-prompts-mirror" `
  -OutputPath ".\outputs\external-corpus\prompt-signals.json"
```

### 3) Generate candidate suggestions

```powershell
& ".\scripts\research\generate-vco-suggestions.ps1" `
  -SignalPath ".\outputs\external-corpus\prompt-signals.json" `
  -SourceRoot ".\third_party\system-prompts-mirror" `
  -OutputDirectory ".\outputs\external-corpus"
```

### 4) Run gate and compare baseline vs candidate

```powershell
& ".\scripts\verify\vibe-external-corpus-gate.ps1" `
  -CandidateSkillIndexPath ".\outputs\external-corpus\skill-keyword-index.candidate.json" `
  -RunExistingSmoke
```

## Decision Rule

Candidate is eligible for manual merge only when:

- `accuracy` does not drop,
- `fallback_rate` does not increase,
- `avg_route_gap` does not materially regress,
- optional smoke scripts all pass.

If any gate check fails, discard the candidate and keep current config unchanged.

## Artifacts

- `outputs/external-corpus/prompt-signals.json`
- `outputs/external-corpus/vco-suggestions.json`
- `outputs/external-corpus/vco-suggestions.md`
- `outputs/external-corpus/skill-keyword-index.candidate.json`
- `outputs/external-corpus/external-corpus-gate.json`
- `outputs/external-corpus/external-corpus-gate.md`
