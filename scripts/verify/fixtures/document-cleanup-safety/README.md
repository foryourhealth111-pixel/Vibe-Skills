# Document Cleanup Safety Fixtures

These fixtures simulate protected document cleanup scenarios without touching real runtime state.

Each scenario contains:

- `metadata.json`: expected protected/quarantine counts
- `source/`: a minimal directory tree copied into a disposable sandbox during gate execution

The goal is to prove:

- protected document assets are detected,
- protected assets outside tmp are retained,
- tmp-root protected assets are quarantined,
- non-protected tmp files are not misclassified as protected.
