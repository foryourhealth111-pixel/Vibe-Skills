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
1. Invoke via Task tool with subagent_type `everything-claude-code:code-reviewer`
2. Lightweight review: bugs, style, correctness
3. Auto-triggered after code changes via PostToolUse hooks

### L Grade (Thorough Review)
Tool: Superpowers two-stage review
1. Stage 1 -- Spec reviewer: Does code match the approved design?
2. Stage 2 -- Quality reviewer: Is code clean, tested, secure?
3. Invoke via `superpowers:requesting-code-review`

### XL Grade (Multi-Agent Review)
Tool: TeamCreate multi-agent review team
1. Create team via `TeamCreate` with reviewer roles
2. Spawn reviewer agents via `Task` tool (subagent_type per perspective)
3. Parallel perspectives: security, performance, architecture, style
4. Aggregate findings via `SendMessage` + `TaskList`
5. With ruflo: use `hive-mind_consensus` for aggregation
6. Without ruflo: team lead collects and synthesizes via SendMessage

## Security Review (Any Grade)
Always available as an independent check:
1. Invoke Everything-CC security-reviewer agent
2. Checks: OWASP Top 10, hardcoded secrets, injection, XSS, CSRF
3. Can run alongside any grade-specific review without conflict

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

## Output Format
Review findings categorized by severity:
- CRITICAL: Must fix before merge (security vulnerabilities, data loss risks)
- HIGH: Should fix before merge (bugs, logic errors)
- MEDIUM: Fix when possible (code smells, minor style issues)
- LOW: Optional improvement (naming suggestions, minor refactors)

## Conflict Avoidance
- M review: Everything-CC code-reviewer ONLY
- L review: Superpowers two-stage review ONLY
- XL review: TeamCreate multi-agent team ONLY (with optional ruflo consensus)
- Security review: Everything-CC security-reviewer at ANY grade (exempt from mutual exclusion)

## Transition After Review
- CRITICAL/HIGH issues found: Route to vibe-do protocol for fixes
- All clean: Proceed to commit/merge
- Architectural issues found: Route to vibe-think protocol for redesign
