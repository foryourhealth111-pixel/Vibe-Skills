# Research Scripts

This directory contains corpus-to-config research scripts used to enhance VCO routing safely.

- `extract-prompt-signals.ps1`: parses external prompt/tool files into structured signals and token statistics.
- `generate-vco-suggestions.ps1`: converts extracted signals into conservative VCO keyword suggestions and emits a candidate `skill-keyword-index` file.

Run sequence:

```powershell
& ".\extract-prompt-signals.ps1" `
  -SourceRoot "..\..\third_party\system-prompts-mirror" `
  -OutputPath "..\..\outputs\external-corpus\prompt-signals.json"

& ".\generate-vco-suggestions.ps1" `
  -SignalPath "..\..\outputs\external-corpus\prompt-signals.json" `
  -SourceRoot "..\..\third_party\system-prompts-mirror" `
  -OutputDirectory "..\..\outputs\external-corpus"
```

Then validate with:

```powershell
& "..\verify\vibe-external-corpus-gate.ps1" `
  -CandidateSkillIndexPath "..\..\outputs\external-corpus\skill-keyword-index.candidate.json" `
  -RunExistingSmoke
```
