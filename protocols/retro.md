# vibe-retro Protocol

Protocol for structured retrospective -- collaborative analysis of recent projects,
workflow optimization, error pattern detection, and future improvement planning.

## Scope
Activated when the user wants to:
- Review and reflect on recent project work
- Identify workflow optimization opportunities
- Detect recurring error patterns and design preventive hooks
- Discover reusable patterns for future projects
- Decide whether to create new skills, agents, MCPs, or hooks
- Conduct a collaborative improvement discussion

## 5-Phase Architecture

Phase 1: GATHER -> Phase 2: ANALYZE -> Phase 3: DISCUSS -> Phase 4: DECIDE -> Phase 5: ACT

Each phase uses existing tools from the 6 integrated plugins.

---

## Phase 1: GATHER (Data Collection)

### 1.1 Conversation History Retrieval
Tool: episodic-memory:search
- Search recent conversations related to target project/topic
- Mode: semantic (topic-based) or text (specific errors/files)

### 1.2 Session Activity Review
Tool: Read ~/.claude/sessions/ files
- Read recent session files
- Extract: tasks performed, files modified, tools used

### 1.3 Instinct Status Check
Tool: everything-claude-code:instinct-status
- Show learned instincts grouped by domain
- Check confidence scores and recent updates
- Fallback: Skip if instinct system not active

### 1.4 Project Memory Retrieval
Tool: Serena MCP list_memories + read_memory
- List project-related memories
- Read key decisions, architecture notes
- Fallback: Skip if Serena not available

### 1.5 Error Log Collection
Tool: git log + episodic-memory search
- git log --oneline -20 (recent commits, especially fix/revert)
- Search episodic-memory for error, fix, bug, revert

Present structured data collection report before proceeding.

---

## Phase 2: ANALYZE (Structured Analysis)

### 2.1 Session Reflection
Tool: claude-code-settings:reflection-harder (or everything-claude-code:deep-reflector agent)
Fallback: claude-code-settings:think-harder
- Analyze recent sessions for problems solved, patterns established

### 2.2 Problem Pattern Detection
Tool: hookify:conversation-analyzer agent
Fallback: Manual scan of episodic-memory search results
- Scan for user frustration signals, repeated errors, tool misuse
- Severity categorization (high/medium/low)

### 2.3 Workflow Frequency Analysis
Tool: Analyze session files + episodic-memory search
- Most frequently used tool combinations
- Repeated multi-step workflows (automation candidates)

### 2.4 Cross-Session Trend Analysis
Tool: claude-code-settings:think-ultra (7-phase analysis), or think-harder (4-phase) for M grade
Fallback: Direct Claude reasoning synthesis
- Synthesize data from 2.1-2.3
- Error trends, activity domains, time sinks

---

## Phase 3: DISCUSS (Interactive Discussion)

### Interaction Style: Pedagogical Advisory

**Proactive Engagement:**
- Actively identify improvement opportunities
- Use guiding questions to surface insights
- For each finding, provide concrete improvement path

**Data-Grounded Suggestions:**
- Every suggestion references specific evidence from Phase 2
- When uncertain, acknowledge it explicitly

**Discussion Topics:**
- Workflow review: automation candidates, efficiency improvements
- Error prevention: hooks, pre-commit checks
- Tool effectiveness: routing accuracy, fallback frequency
- Future planning: templates, skills, new tools

**Respectful Autonomy:**
- User makes all final decisions
- Explicitly ask for confirmation before Phase 4

---

## Phase 4: DECIDE (Decisions)

### Decision Categories

| Category | Action Type | Tool |
|----------|------------|------|
| Recurring workflow | Create skill | superpowers:writing-skills |
| Recurring workflow | Create command | claude-code-settings:command-creator |
| Error prevention | Create hook | hookify:hookify |
| Behavioral pattern | Create/update instinct | continuous-learning-v2 |
| Routing improvement | Update VCO config | Edit SKILL.md |
| Knowledge capture | Persist memory | Serena write_memory / episodic-memory |
| Complex automation | Create agent | Manual design + writing-skills |

### User Confirmation Gate
Present all decisions as prioritized list. User approves, modifies, or rejects each before Phase 5.

---

## Phase 5: ACT (Execute Improvements)

### 5.1 Create Hooks
Tool: hookify:hookify
- Define trigger, matcher, action
- Create .local.md rule file

### 5.2 Create Skills/Commands
Tool: superpowers:writing-skills or claude-code-settings:command-creator
- Define skill name, description, trigger
- Write SKILL.md with proper frontmatter

### 5.3 Create/Update Instincts
Tool: everything-claude-code:continuous-learning-v2
- Create .md in ~/.claude/homunculus/instincts/personal/
- Set confidence score (start at 0.5)

### 5.4 Update VCO Configuration
Tool: Direct file edits to SKILL.md, conflict-rules.md, fallback-chains.md

### 5.5 Persist Knowledge
Tool: Serena write_memory + CLAUDE.md updates if globally applicable

### 5.6 Generate Retro Report
Store via Serena write_memory(retro/YYYY-MM-DD, report).

---

## Tool Composition Map

| Phase | Primary Tool | Source Plugin | Fallback |
|-------|-------------|--------------|----------|
| 1.1 History | episodic-memory:search | Superpowers | Read session files |
| 1.2 Activity | Read ~/.claude/sessions/ | Everything-CC | git log |
| 1.3 Instincts | instinct-status | Everything-CC | Skip |
| 1.4 Memory | Serena list/read_memory | Serena MCP | Skip |
| 1.5 Errors | git log + episodic search | Git + Superpowers | Manual review |
| 2.1 Reflection | reflection-harder | Claude-code-settings | deep-reflector agent / think-harder |
| 2.2 Problems | conversation-analyzer | Hookify | Manual scan |
| 2.3 Workflows | Session file analysis | Everything-CC | episodic search |
| 2.4 Trends | think-ultra / think-harder | Claude-code-settings | Direct reasoning |
| 3.x Discussion | brainstorming methodology | Superpowers | Direct dialogue |
| 4.x Decisions | AskUserQuestion | Claude Code native | Direct dialogue |
| 5.1 Hooks | hookify | Hookify | Manual creation |
| 5.2 Skills | writing-skills | Superpowers | Manual creation |
| 5.3 Instincts | continuous-learning-v2 | Everything-CC | Manual creation |
| 5.4 Config | Direct edit | VCO | Manual edit |
| 5.5 Knowledge | Serena write_memory | Serena MCP | episodic-memory |

---

## Grade Adaptation

| Grade | Scope | Phases Used | Depth |
|-------|-------|-------------|-------|
| M | Single project retro | 1 + 2 + 3 + 4 | Full analysis, selective action |
| L | Multi-project retro | All 5 phases | Full analysis + implementation |
| XL | System-wide retro | All 5 + parallel agents | Deep analysis + major changes |

## Conflict Avoidance
- Phase 2 analysis agents run sequentially to avoid mutual exclusion
- Exception: XL grade uses TeamCreate team for parallel analysis
- hookify conversation-analyzer is an analysis tool -- safe at any grade
- deep-reflector is a diagnostic agent -- exempt from Rule 1
- Phase 5 actions are sequential: hooks first, then skills, then config
