# Host Adapters

This directory holds host-specific compatibility contracts for the universalization program.

Rules:

- Adapters do not replace the official runtime.
- Adapters do not own routing truth.
- Adapters describe host capabilities, host-managed surfaces, settings mapping, and honest degradation states.
- A host adapter can be `supported`, `preview`, or `not-yet-proven`, but it must never overclaim closure that has not been verified.

Current adapter intent:

- `codex/`: strongest current adapter because the repository already ships Codex-specific install, settings, and plugin guidance.
- `claude-code/`: preview adapter derived from existing template and governance expectations.
- `cursor/`: preview adapter with truthful host-managed boundaries; no full closure claim yet.
- `opencode/`: contract placeholder only; no runtime closure claim yet.
- `generic/`: lowest-common-denominator contract consumer, not an official runtime.

The official runtime remains the canonical execution owner until replay, install isolation, and platform truth gates are passed.
