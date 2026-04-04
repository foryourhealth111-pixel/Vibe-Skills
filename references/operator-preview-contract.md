# Operator Preview Contract Reference

- `contract_version`: `1`
- `precheck`: execution-context, mirror-target, and write-scope validation
- `preview`: machine-readable receipt written before apply
- `apply`: canonical write flow after human/operator review
- `apply_gates`: canonical apply-time governed gate list for operators that run bounded post-write verification
- `postcheck`: named verification gates and hygiene checks after apply

## Notes

- Preview receipts are intentionally JSON-first so downstream tooling can diff them.
- The preview contract governs `sync-bundled-vibe` and `release-cut` first, then future operator scripts can opt in.
