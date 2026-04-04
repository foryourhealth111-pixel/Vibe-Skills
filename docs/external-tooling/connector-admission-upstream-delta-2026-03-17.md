# Connector Admission Upstream Delta 2026-03-17

Date: 2026-03-17
Reviewed sources: `activepieces`, `composio`, `awesome-mcp-servers`
Verified remote HEAD:

- `activepieces`: `e1bd2772affc271f69b502b07cfa22e57eb2b757`
- `composio`: `3d284eef2e48b4c3e8ce84ad1f866bdb4d204056`
- `awesome-mcp-servers`: `ed1aa4fbeb0006e9c2be7594b494910a948d83ae`

## Packet Purpose

This packet completes Wave A of the follow-on arrangement.
Its job is to refresh connector-governance truth and tighten connector admission language where upstream drift adds governance value, without widening connector execution authority.

## Reviewed Delta Classes

### `activepieces`

Observed drift is materially large and heavily documentation/template shaped.
The reviewed surface shows stronger upstream structure around:

- piece-builder patterns
- action / trigger taxonomy
- auth and props pattern guidance
- builder-side quality expectations

Admissible intake:

- tighten capability-tag language,
- tighten piece-category and trigger references,
- keep all write-capable paths confirm-gated,
- keep `activepieces` in `shadow_governed` posture.

Decision class: `admit`
Admission scope: `governance-tightening only`

### `composio`

Observed drift is materially large and dominated by docs / connect-client / workflow sync surfaces.
The reviewed surface strengthens VCO governance around:

- provider/client sync vocabulary
- auth boundary posture
- tool-binding / app-catalog framing
- documentation-first contract clarity

Admissible intake:

- tighten provider-contract wording,
- clarify secret-profile / auth-boundary notes,
- keep `composio` as `provider_candidate`,
- keep all write-capable actions in `confirm_required` mode.

Decision class: `admit`
Admission scope: `governance-tightening only`

### `awesome-mcp-servers`

Observed drift confirms continued catalog churn and scouting value.
That is useful for VCO only as:

- catalog snapshot input,
- capability scouting feed,
- metadata ranking evidence.

It is not admissible as an install or execution control plane.

Decision class: `metadata-only`
Admission scope: `catalog-governance refresh only`

## Not Admitted

This packet does not admit:

- connector auto-install
- connector-driven route ownership
- connector-driven browser or memory ownership
- provider takeover
- background execution owner widening
- any write-capable path without confirmation

## Canonical Effect

After this packet:

- `activepieces` remains `shadow_governed`
- `composio` remains `shadow_governed`
- `awesome-mcp-servers` remains `catalog_governed`
- connector docs now explicitly record decision class and reviewed-head evidence
- operator-facing and gate-facing connector assets remain aligned without creating a second connector control plane
