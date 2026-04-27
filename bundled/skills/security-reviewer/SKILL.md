---
name: security-reviewer
description: Dedicated security-audit route for OWASP-style risks, secret leaks, auth flaws, injection, unsafe input handling, SSRF/XSS, and sensitive-data exposure. Use instead of code-reviewer when the prompt explicitly asks for security, vulnerability, threat, auth, or OWASP review.
---

# security-reviewer (Codex Compatibility)

Use this skill after code changes that touch input handling, auth, APIs, data access, uploads, payments, or external integrations.

## Routing Boundary

Use this skill when security is the main question:
- OWASP/security audit/security review
- secret leak, token exposure, unsafe logging
- auth bypass, authorization gaps, session/token handling
- injection, XSS, SSRF, unsafe file upload or command execution

Do not use this as the default owner for ordinary maintainability review. If security is only one item in a general PR review, `code-reviewer` can flag it, but explicit security-audit wording should route here.

## Security Review Workflow

1. Initial Scan
- Locate auth, API endpoints, DB queries, file handling, and external calls.
- Check for hardcoded secrets and unsafe config defaults.

2. OWASP-Oriented Checks
- Injection: parameterized queries, sanitized inputs.
- AuthZ/AuthN: enforce authorization per route, secure session/token handling.
- Data exposure: secrets/PII protection and safe logging.
- XSS/SSRF: output encoding, URL allowlist, no blind fetch of user URLs.
- Dependency risk: audit vulnerable dependencies.

3. High-Risk Pattern Audit
- Hardcoded secrets/tokens
- Command execution with user input
- SQL string concatenation
- Missing auth check
- Missing rate limiting on sensitive endpoints
- Unsafe crypto/password handling

4. Remediation Output
- Severity (CRITICAL/HIGH/MEDIUM/LOW)
- Evidence (file + line + risk)
- Concrete fix proposal
- Verification steps after fix

## Vibe Integration

- Security gate skill usable at any grade.
- Pair with `security-best-practices` for language/framework-specific guidance.
- Pair with `code-reviewer` for combined correctness + security review.
