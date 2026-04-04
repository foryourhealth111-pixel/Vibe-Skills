# Mem0 Opt-in Backend Integration

## Role

`mem0` enters VCO as an optional external preference-memory backend.
It is not a primary session store, not a routing hint authority, and not a replacement for Serena/ruflo/Cognee.

## Allowed Payload Types

- user preference
- recurring style hint
- stable personal constraint
- reusable output preference

## Forbidden Payload Types

- route selection
- canonical project decision
- primary session state
- explicit build/test result truth
- security-sensitive raw secrets

## Operating Modes

- `off`: disabled
- `shadow`: classify payloads and emit recommendations only
- `soft`: allow opt-in writes after policy validation

## Support Notes

- OpenAI-compatible embedder endpoints may be configured through a backend `baseURL`, but this remains an optional portability detail inside the `mem0` lane only.
- SQLite-backed persistence must target an operator-controlled durable path rather than assuming the active `cwd` is writable or stable.
- Structured payloads captured from fenced blocks must be preserved verbatim for admission review before any downgrade to advisory-only.

## Rollback

Rollback is simple: set `config/mem0-backend-policy.json` to `off` and keep Memory Runtime v2 canonical owners unchanged.
