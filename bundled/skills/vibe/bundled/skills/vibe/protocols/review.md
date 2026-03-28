# vibe-review Protocol

Protocol for code review, security audit, and quality assurance tasks.

## Scope
Activated when the task requires evaluating existing code:
- Code review (style, correctness, maintainability)
- Security audit (OWASP Top 10, secrets, injection)
- Quality assurance (test coverage, performance)
- Pre-merge validation (comprehensive check before merge)

## Tool Orchestration by Grade

### M Grade (Quick Review)
Tool: Everything-CC code-reviewer agent
1. Invoke Everything-CC `code-reviewer` directly as a single-agent review tool
2. Lightweight review: bugs, style, correctness
3. Auto-triggered after code changes via PostToolUse hooks

### L Grade (Thorough Review)
Tool: Superpowers two-stage review
1. Stage 1 -- Spec reviewer: Does code match the approved design?
2. Stage 2 -- Quality reviewer: Is code clean, tested, secure?
3. Invoke via `superpowers:requesting-code-review`

### XL Grade (Multi-Agent Review)
Tool: Codex native multi-agent review team
1. Spawn reviewer agents via `spawn_agent` (role prompt per perspective)
2. Coordinate review rounds via `send_input`
3. Parallel perspectives: security, performance, architecture, style
4. Aggregate findings via `wait` + lead synthesis
5. Optional: use ruflo `hive-mind_consensus` for formal aggregation
6. Cleanup: `close_agent` for all spawned reviewers

## Security Review (Any Grade)
Always available as an independent check:
1. Invoke Everything-CC security-reviewer agent
2. Checks: OWASP Top 10, hardcoded secrets, injection, XSS, CSRF
3. Can run alongside any grade-specific review without conflict

## Anti-Proxy-Goal-Drift Review Lens

When the canonical anti-proxy-goal-drift policy is active, every governed review should also answer:

1. What is the primary objective the change claims to serve?
2. Which proxy signals could be mistaken for true success?
3. Was validation material kept in a validation role, or did it leak into product logic?
4. Is the claimed completion state supported by evidence, or is the wording ahead of the proof?
5. Was the fix applied at the correct abstraction layer, rather than only removing the local symptom?
6. Is a bounded specialization being described honestly, or is it being relabeled as generalized capability?

Report-only boundary:
- Anti-drift findings are review evidence and completion-language corrections.
- They do not by themselves create a new hard gate, new owner, or automatic merge block.
- If another approved policy or gate is violated, cite that surface explicitly instead of treating anti-drift as hidden enforcement.

## Review Checklist
Before approving code:
1. Code is readable and well-named
2. Functions are small (<50 lines)
3. Proper error handling at system boundaries
4. No hardcoded values (use constants or config)
5. Tests exist and pass (80%+ coverage)
6. No security vulnerabilities
7. No console.log / debug statements in production code
8. Immutable patterns used (no mutation)
9. No new fallback or degraded-path logic unless the active requirement explicitly approves it
10. Any fallback path is labeled as a hazard, not presented as equivalent success
11. The reviewed change states its primary objective, not only its local success signal
12. Validation material is not absorbed into product logic or route truth
13. The claimed completion state matches the evidence bundle and scope
14. Bounded specialization is either preserved as specialization or explicitly marked as not-yet-generalized
15. Any anti-drift warning is recorded as report-only review evidence, not hidden hard enforcement
16. Product acceptance criteria are frozen in the requirement doc rather than improvised at closeout
17. Manual spot checks are either explicitly not needed or honestly left as pending manual review
18. Delivery-truth wording does not collapse workflow/process success into downstream project acceptance

## Output Format
Review findings categorized by severity:
- CRITICAL: Must fix before merge (security vulnerabilities, data loss risks)
- HIGH: Should fix before merge (bugs, logic errors)
- MEDIUM: Fix when possible (code smells, minor style issues)
- LOW: Optional improvement (naming suggestions, minor refactors)

Fallback-specific review rule:
- Treat silent fallback, silent degradation, or self-introduced fallback logic as HIGH at minimum and CRITICAL when it can hide capability loss from users.

Objective-protection disposition:
- `aligned`: objective, scope, and completion wording match the evidence.
- `report_only_warning`: drift risk exists and must be recorded in review / closure language, but does not by itself block merge.
- `specialization_confirmed`: the change is valid as a bounded specialization and must not be relabeled as generalized capability.
- `completion_language_corrected`: code may stand, but the claimed completion wording must be reduced to match proof.
- `escalate_via_existing_policy`: another already-approved policy or hard gate is independently violated and should be cited directly.

## Conflict Avoidance
- M review: Everything-CC code-reviewer ONLY
- L review: Superpowers two-stage review ONLY
- XL review: Codex native multi-agent team ONLY
- Security review: Everything-CC security-reviewer at ANY grade (exempt from mutual exclusion)

## Transition After Review
- CRITICAL/HIGH issues found: Route to vibe-do protocol for fixes
- `report_only_warning` or `completion_language_corrected`: update requirement / plan / CER / closure wording or route to vibe-do for scope-corrective fixes
- `specialization_confirmed`: preserve specialization wording and avoid generalized overclaim
- `escalate_via_existing_policy`: cite the specific approved policy or gate that blocks progress
- All clean: Proceed to commit/merge
- Architectural issues found: Route to vibe-think protocol for redesign
