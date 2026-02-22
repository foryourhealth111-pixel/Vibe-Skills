# Extending VCO

Guide for adding new tools or adapting to tool updates.

## Adding a New Tool

### Step 1: Analyze the Tool
Before integration, answer:
1. What hook types does it register?
2. What state does it manage? (file paths, databases)
3. What agent/skill capabilities does it provide?
4. Does it assume exclusive control of any resource?

### Step 2: Register in Tool Registry
Add entry to references/tool-registry.md with:
- Tool name, version, location
- Hook types registered
- State location
- Key skills/agents/commands

### Step 3: Identify Conflicts
Check against existing tools for:
- Hook type overlaps (same event types)
- State path collisions (same directories)
- Agent name collisions
- Behavioral conflicts (competing mandates)

### Step 4: Add Conflict Rules
Add resolution rules to references/conflict-rules.md:
- Which grade should use the new tool (M/L/XL)
- How it coexists with existing tools
- Any mutual exclusion requirements
- Add to contextual notes if it's a deconfliction detail

### Step 5: Update SKILL.md
Update the main vibe/SKILL.md:
- Add to the tool selection matrix (Section 2)
- Update conflict summary (Section 6) if needed

### Step 6: Update Protocols
If the new tool provides unique capabilities, update the relevant protocol:
- protocols/think.md for planning/research tools
- protocols/do.md for coding/debugging tools
- protocols/review.md for review/quality tools
- protocols/team.md for orchestration tools
- protocols/retro.md for retrospective tools

### Step 7: Update Fallback Chains
Add fallback entries to references/fallback-chains.md

## Adapting to Tool Updates

### Minor Updates (patch/minor version)
1. Check release notes for new features or changed behavior
2. Verify existing conflict rules still apply
3. Update version numbers in tool-registry.md

### Major Updates (breaking changes)
1. Re-analyze the tool (Step 1 above)
2. Check if hook registrations changed
3. Check if state paths changed
4. Update all affected reference documents

### Tool Removal
1. Remove from tool-registry.md
2. Remove conflict rules that reference it
3. Update protocols that used it
4. Update SKILL.md tool selection matrix
5. Update fallback-chains.md

## Design Principles

1. No source modification: VCO never modifies existing tools
2. Additive only: New tools are added alongside existing ones
3. Conflict-first thinking: Always identify conflicts before adding
4. Grade-based routing: New tools should fit into M/L/XL grades
5. Protocol alignment: New tools should map to think/do/review/team/retro

## Iteration Governance

### Occam's Razor Principle
Every modification must pass:
1. Necessity proof: Can the goal be achieved WITHOUT this change?
2. Minimal scope: Change the fewest files possible
3. Evidence-based: Every addition must cite a concrete problem it solves
4. Removal bias: When in doubt, remove rather than add

### User Confirmation Gate
Any structural change requires explicit user approval:
1. Propose: Describe what will change, which files, and why
2. Discuss: Answer user questions, adjust based on feedback
3. Confirm: User explicitly approves before modification
4. Report: After implementation, summarize what was done

Structural changes: adding/removing protocols, modifying routing rules, changing grade criteria.
Non-structural changes (no gate): typo fixes, version updates, fallback additions.

### Change Rationale Recording
Every VCO iteration should be recorded with:
- Version number (semver)
- Date
- List of changes with file paths
- Rationale: WHY this change was made
