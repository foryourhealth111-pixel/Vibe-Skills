# 2026-04-03 Frontmatter Gate Runtime Contract Delegation Plan

## Goal

Remove the remaining installed-runtime closure path duplication from the BOM/frontmatter gate so verification consumes one effective runtime-config surface.

## Internal Grade

XL wave, executed serially for this microphase because the change touches a verification gate and must preserve cross-platform behavior.

## Frozen Scope

- Refactor the frontmatter gate to resolve installed-runtime closure paths from `context.runtimeConfig`.
- Keep current scope activation and file-content checks unchanged.
- Add focused tests for the ownership boundary and runtime behavior.
- Run focused verification and a wave-level full regression before closing the phase.
