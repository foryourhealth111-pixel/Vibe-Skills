# VCO Release / Install / Runtime Coherence Gate

- Gate Result: **PASS**
- Repo Root: `<repo-root>`
- Target Root: `<proof-target-root>`
- Assertion Failures: 0
- Warnings: 0

## Assertions

- [PASS] [runtime] target_relpath is declared
- [PASS] [runtime] receipt_relpath is declared
- [PASS] [runtime] receipt_relpath stays under target_relpath
- [PASS] [runtime] post-install freshness gate script exists
- [PASS] [runtime] coherence gate script exists
- [PASS] [runtime] BOM/frontmatter gate script exists
- [PASS] [runtime] sync-bundled-vibe script exists for mirror closure
- [PASS] [runtime] required_runtime_markers includes post-install freshness gate
- [PASS] [runtime] required_runtime_markers includes coherence gate
- [PASS] [runtime] receipt_contract_version is declared and >= 1
- [PASS] [runtime] shell_degraded_behavior declares warn-and-skip semantics
- [PASS] [docs] version-packaging-governance.md exists
- [PASS] [docs] runtime-freshness-install-sop.md exists
- [PASS] [docs] version governance doc defines release boundary
- [PASS] [docs] version governance doc documents execution-context lock
- [PASS] [docs] runtime SOP documents receipt contract
- [PASS] [docs] runtime SOP documents shell degraded behavior
- [PASS] [install.ps1] install flow invokes runtime freshness gate
- [PASS] [install.sh] shell install flow invokes runtime freshness gate
- [PASS] [check.ps1] check flow invokes runtime freshness gate
- [PASS] [check.ps1] check flow invokes coherence gate
- [PASS] [check.sh] shell check flow invokes runtime freshness gate
- [PASS] [check.sh] shell check flow invokes coherence gate
- [PASS] [check.sh] shell check documents a degraded or runtime-neutral gate path
- [PASS] [receipt] installed runtime freshness gate emits receipt_version
- [PASS] [receipt] gate receipt_version matches configured receipt_contract_version
- [PASS] [receipt] installed runtime freshness gate writes gate_result
- [PASS] [receipt] installed runtime receipt gate_result is PASS
- [PASS] [receipt] installed runtime receipt version satisfies contract

