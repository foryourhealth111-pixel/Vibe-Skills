---
name: autonomous-builder
version: "1.0.0"
description: "Full-stack software development agent for design, implementation, testing, and deployment. Use when the user explicitly asks for end-to-end project creation, feature development, bug fixing, or code refactoring."
user-invocable: true
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - WebFetch
  - WebSearch
  - Skill
  - Task
  - ToolSearch
  - mcp__ide__executeCode
  - mcp__ide__getDiagnostics
---

# Autonomous Builder

A fully autonomous software development agent that handles the complete software lifecycle: requirements analysis, architecture design, implementation, testing, debugging, and deployment.

## Architecture Pattern: Two-Agent Model

**Based on Anthropic's official claude-quickstarts architecture**

```
┌─────────────────────────────────────────────────────────────────┐
│                 TWO-AGENT ARCHITECTURE                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  SESSION 1: INITIALIZER AGENT                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ • Read requirements / spec                               │    │
│  │ • Create project structure                               │    │
│  │ • Generate feature_list.json (200+ tests)                │    │
│  │ • Initialize Git repository                              │    │
│  │ • ✨ Prompt for GitHub URL (optional)                    │    │
│  │ • ✨ Create README.md & PLANNING.md                      │    │
│  │ • Commit initial state                                   │    │
│  │ • ✨ Push to GitHub & create issues                      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│                    feature_list.json                             │
│                    (Single Source of Truth)                      │
│                              │                                   │
│  SESSIONS 2+: BUILDER AGENT (fresh context each session)        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Step 1: Get Context (pwd, ls, git log, progress)         │    │
│  │ Step 2: Start/verify server                              │    │
│  │ Step 3: Verify previous tests (regression check)         │    │
│  │ Step 4: Select next "passes": false feature              │    │
│  │ Step 5: Implement feature                                │    │
│  │ Step 6: Browser automation test                          │    │
│  │ Step 7: Update feature_list.json                         │    │
│  │ Step 8: Generate workflow report                         │    │
│  │ Step 9: Git commit + GitHub push                        │    │
│  │ Step 10: Update progress notes                           │    │
│  │ Step 11: Clean exit (auto-continue in 3s)                │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Key Design Principles (Official Pattern):**
1. **Fresh Context Per Session** - Each session uses brand new context window
2. **File-Based State Persistence** - Progress via feature_list.json, not context
3. **Git Commit as State Anchor** - Atomic progress units with easy rollback
4. **Browser Automation Testing** - Act like human user, verify via UI
5. **Auto-Continue with Delay** - 3 second delay between sessions

## Core Philosophy

**The Autonomous Development Loop:**

```
PLAN -> BUILD -> TEST -> DEBUG -> DEPLOY -> (REPEAT)
  |                                    |
  +------------------------------------+
```

**Key Principles:**
1. **Self-Sufficient**: No user intervention required during execution
2. **State-Persistent**: Recovers from interruptions via `.builder/` state files
3. **Multi-Language**: Auto-detects and adapts to project technology stack
4. **Incremental**: Completes one feature at a time, commits progress
5. **Error-Resilient**: 3-strike protocol with automatic recovery strategies

## When to Use This Skill

Use this skill when the user explicitly wants this agent to own an end-to-end build or major refactor, such as:
- Starting a new project from a full specification
- Continuing a previously initialized `.builder/` project
- Driving a broad feature build across multiple implementation steps
- Performing an explicit refactor or modernization effort across the codebase

Use stage assistants or other routed specialists for narrow bug fixes, one-off debugging, or scoped edits that do not need full lifecycle ownership.

## Not For / Boundaries

- **Security-critical systems** without human review
- **Production deployments** without user confirmation
- **Legal/compliance-sensitive code** without audit
- **Data migration** without backup verification
- **Infrastructure changes** without explicit approval
- **System-level operations** outside workspace (see SAFETY CRITICAL below)

**Required inputs (ask if missing):**
1. Project requirements or specification
2. Target platform/environment (web, CLI, mobile, etc.)
3. Preferred language/framework (or auto-detect)

**Safety First:** All operations that could affect system stability, data integrity, or files outside the workspace require explicit user approval. See **SAFETY CRITICAL** section below for details.

## Quick Reference

### Session Continuity (Auto-Resume)

**⚠️ Critical for Unattended Long-Running Operation**

```
AUTO-RESUME PROTOCOL:
┌─────────────────────────────────────────────────────────────────┐
│  Session Start                                                  │
│       │                                                         │
│       ▼                                                         │
│  Check .builder/state.json exists?                              │
│       │                                                         │
│       ├─ NO → Initialize new project                            │
│       │                                                         │
│       └─ YES → Resume from saved state:                         │
│              1. Read current_phase                               │
│              2. Read current_feature                             │
│              3. Read pending_features[]                          │
│              4. Continue from last checkpoint                    │
│                                                                 │
│  After each feature completion:                                 │
│       │                                                         │
│       ▼                                                         │
│  More pending features?                                         │
│       │                                                         │
│       ├─ YES → Auto-start next feature (NO user input needed)   │
│       │                                                         │
│       └─ NO → All complete! Generate report                     │
└─────────────────────────────────────────────────────────────────┘
```

**Auto-Continue Rules:**

| Condition | Action | User Input Required |
|-----------|--------|---------------------|
| Feature completed, more pending | Auto-start next | **NO** |
| Error recovered successfully | Continue current | **NO** |
| 3-strike error failed | Skip and continue | **NO** (unless critical) |
| Loop detected & resolved | Resume from checkpoint | **NO** |
| All features complete | Generate final report | **NO** |

**State Persistence After Each Operation:**

```json
{
  "auto_continue": true,
  "resume_token": "feat-003-phase-implement",
  "next_action": "Continue implementing feat-003",
  "features_remaining": 3,
  "estimated_completion": "2026-02-14T18:00:00Z"
}
```

### Automatic Task Queue

```python
# After completing a feature, automatically proceed:

def on_feature_complete(feature_id: str, state: ProjectState):
    """Called when a feature is marked complete."""

    # 1. Save checkpoint
    save_checkpoint(state, feature_id)

    # 2. Update feature status
    state.features[feature_id].status = "completed"
    state.features[feature_id].completed_at = datetime.now()

    # 3. Check for pending features
    pending = [f for f in state.features if f.status == "pending"]

    if pending:
        # 4. Auto-select next feature (NO user input)
        next_feature = select_next_feature(pending, state)
        state.current_feature = next_feature.id
        state.current_phase = "implement"

        # 5. Save state immediately
        save_state(state)

        # 6. LOG and CONTINUE (not ask user)
        log_progress(f"Auto-continuing to {next_feature.name}")
        return ContinueAction(feature=next_feature)
    else:
        # All complete!
        return CompleteAction(report=generate_final_report(state))
```

**Resume Message on Session Start:**

```markdown
## 🔄 Session Resume Detected

**Previous Session**: Session #5
**Last Activity**: 2 hours ago
**Current Feature**: feat-003 (User Authentication)
**Phase**: implement (60% complete)

**Pending Features**: 3 remaining
- feat-004: API Rate Limiting
- feat-005: Email Notifications
- feat-006: Final Documentation

**Auto-Continuing**: Resuming feat-003 implementation...

[Proceeding without user input - type "pause" to stop]
```

### Directory Structure

```
.builder/
├── state.json           # Current project state
├── features.json        # Feature list with status
├── architecture.md      # Design decisions
├── progress.md          # Session log
├── errors.json          # Error history and resolutions
├── checkpoints/         # Recovery checkpoints
├── auto-continue.{sh,bat,ps1}  # Auto-restart script (auto-generated)
└── supervisor.json      # Self-supervision config
```

### Skill Recommendations & Router Handoff

**⚠️ Skill discovery is advisory. The host router remains the only main-route authority.**

```markdown
ON PROJECT INITIALIZATION:

1. Check for Claude_Skills_中文指南.md in workspace root
2. If found:
   - Read and parse skill catalog
   - Store available skills in state.json
3. For each feature:
   - Analyze feature requirements
   - Match against skill catalog
   - Add recommended_skills to feature definition as router-handoff suggestions

DURING IMPLEMENTATION:

1. Before each implementation step:
   - Check step's invoke_skill field
   - Or analyze step for skill match

2. Request router-approved handoff:
   - Propose the matched skill to the host router or current route authority
   - Use the Skill tool only after that router-authorized handoff or an explicit user request
   - Continue with the returned guidance once the handoff is granted

3. Log router-approved skill usage to state.json
```

**Task-to-Skill Mapping (Recommended):**

| Task Type | Recommended Skills |
|-----------|--------------------|
| Code review | `code-reviewer`, `code-review-excellence` |
| Data analysis | `exploratory-data-analysis`, `statistical-analysis` |
| Visualization | `data-artist`, `matplotlib`, `plotly` |
| ML training | `senior-ml-engineer`, `pytorch-lightning` |
| ML evaluation | `evaluating-machine-learning-models`, `shap` |
| Scientific writing | `scientific-writing`, `scientific-schematics` |
| Debugging | `debugging-strategies`, `error-resolver` |
| Documentation | `docs-write`, `writing-docs` |
| Architecture | `architecture-patterns` |
| Bioinformatics | `biopython`, `bio-database-evidence` |
| Drug discovery | `torchdrug`, `rdkit`, `uniprot-database` |

**Feature with Skill Planning:**

```json
{
  "id": "feat-001",
  "name": "Data Analysis Module",
  "recommended_skills": [
    {"skill": "exploratory-data-analysis", "phase": "implementation"},
    {"skill": "data-artist", "phase": "implementation"}
  ],
  "skill_dispatch_schedule": [
    {"step": 1, "action": "Explore data", "invoke_skill": "exploratory-data-analysis", "router_handoff_required": true},
    {"step": 2, "action": "Create charts", "invoke_skill": "data-artist", "router_handoff_required": true}
  ]
}
```

**Setup**: Place `Claude_Skills_中文指南.md` in workspace root. Skills will be discovered and stored as recommendations, then handed off through the host router before invocation.

### MCP Auto-Integration & Human-like Computer Control

**⚠️ Enables browser automation, desktop control, and seamless tool invocation**

```markdown
ON SESSION START:

1. DISCOVER MCP servers
   - Run /mcp to list configured servers
   - Parse available tools from each server
   - Build capability map

2. CHECK critical capabilities:
   - browser_automation (puppeteer)
   - code_execution (ide)
   - desktop_control (desktop) - optional

3. AUTO-INSTALL missing servers if needed:
   - For web projects: puppeteer
   - For desktop apps: desktop
   - For database work: sqlite/postgres

4. UPDATE state.json → mcp_integration
```

**MCP Capability Matrix:**

| Capability | MCP Server | What It Enables |
|------------|------------|-----------------|
| Browser automation | puppeteer | Navigate, click, type, screenshot |
| Desktop control | desktop | Mouse, keyboard, screen capture |
| Code execution | ide | Run Python, get diagnostics |
| Database | sqlite/postgres | Query, insert, manage data |
| Web search | brave-search | Research, documentation lookup |
| HTTP requests | fetch | API testing, web fetching |

**Auto-Tool Selection:**

```
Task Pattern                    → MCP Tool
─────────────────────────────────────────────
"open website/url"              → mcp__puppeteer_navigate
"click button/element"          → mcp__puppeteer_click
"fill form/type text"           → mcp__puppeteer_type
"take screenshot"               → mcp__puppeteer_screenshot
"run JavaScript"                → mcp__puppeteer_evaluate
"control mouse"                 → mcp__desktop_mouse_move
"press key/hotkey"              → mcp__desktop_hotkey
"execute Python"                → mcp__ide__executeCode
```

**Example: Automated Web Testing**

```markdown
## E2E Test Flow (Automatic)

1. mcp__puppeteer_navigate → "https://myapp.com"
2. mcp__puppeteer_screenshot → capture initial state
3. mcp__puppeteer_fill → "#username", "testuser"
4. mcp__puppeteer_click → "#submit"
5. mcp__puppeteer_wait → ".dashboard"
6. mcp__puppeteer_evaluate → verify page state
7. mcp__puppeteer_screenshot → capture result
```

**Custom MCP Server Creation:**

When no existing MCP server fits the task, autonomous-builder can:
1. Identify requirement
2. Design custom MCP server
3. Write server code to `.builder/mcp-servers/`
4. Register with `claude mcp add`
5. Use immediately

### Auto-Restart & Self-Supervision

**⚠️ Enables true unattended long-running operation**

```markdown
ON PROJECT INITIALIZATION:
1. Create .builder/ directory
2. Generate auto-continue script for current platform:
   - Windows: auto-continue.ps1
   - Linux/macOS: auto-continue.sh
3. Create supervisor.json with monitoring config
4. Script runs in background, monitors session health
```

**Auto-Generated Supervisor Script:**

```bash
#!/bin/bash
# .builder/auto-continue.sh - Auto-generated by autonomous-builder

PROJECT_DIR="/path/to/project"
BUILDER_DIR="$PROJECT_DIR/.builder"
STATE_FILE="$BUILDER_DIR/state.json"
SUPERVISOR_CONFIG="$BUILDER_DIR/supervisor.json"

# Self-supervision loop
while true; do
    # Check if project is complete
    if [ -f "$STATE_FILE" ]; then
        STATUS=$(grep -o '"status"[[:space:]]*:[[:space:]]*"[^"]*"' "$STATE_FILE" | head -1 | cut -d'"' -f4)
        if [ "$STATUS" = "completed" ]; then
            echo "[$(date)] Project completed. Exiting supervisor."
            exit 0
        fi
    fi

    # Check last activity (if no activity for 5 min, restart)
    LAST_ACTIVITY=$(grep -o '"last_activity"[[:space:]]*:[[:space:]]*"[^"]*"' "$STATE_FILE" | cut -d'"' -f4)
    if [ -n "$LAST_ACTIVITY" ]; then
        # Parse and check timeout...
        # If timeout exceeded, trigger new session
    fi

    # Start/resume Claude session with permission bypass for unattended operation
    # WARNING: --dangerously-skip-permissions bypasses all user confirmations
    echo "[$(date)] Starting Claude session..."
    claude --skill autonomous-builder --project "$PROJECT_DIR" --dangerously-skip-permissions

    # Log session end
    echo "[$(date)] Session ended. Checking state..."

    # Wait before restart (configurable)
    sleep 5
done
```

**⚠️ Security Warning:** `--dangerously-skip-permissions` bypasses ALL user confirmations. Use only in trusted, isolated environments. Ensure workspace isolation and safety protocols are properly configured.

**Supervisor Configuration:**

```json
{
  "supervisor_version": "1.0",
  "project_path": "/path/to/project",
  "enabled": true,

  "monitoring": {
    "check_interval_seconds": 60,
    "session_timeout_seconds": 300,
    "max_restart_attempts": 10,
    "restart_cooldown_seconds": 5
  },

  "health_checks": {
    "progress_stall_threshold": 600,
    "error_rate_threshold": 0.5,
    "context_usage_warning": 0.8
  },

  "notifications": {
    "on_completion": true,
    "on_error_spike": true,
    "on_stall": true,
    "log_file": ".builder/supervisor.log"
  },

  "statistics": {
    "total_sessions": 0,
    "total_restarts": 0,
    "total_runtime_seconds": 0,
    "last_restart_time": null
  }
}
```

### Core Workflow Phases

| Phase | Actions | Output |
|-------|---------|--------|
| INITIALIZE | Check state, parse requirements | state.json, features.json |
| DESIGN | Detect tech stack, choose architecture | architecture.md |
| IMPLEMENT | Write code per feature | Source files |
| TEST | Run unit/integration/E2E | Test results |
| DEBUG | Apply 3-strike protocol | Fixes or escalation |
| DEPLOY | Build, document, archive | Final deliverables |

### State File Schema

```json
{
  "project_name": "string",
  "current_phase": "init|design|implement|test|deploy",
  "current_feature": "feature-id",
  "tech_stack": {
    "language": "string",
    "framework": "string",
    "runtime": "string"
  },
  "completed_features": ["feat-001"],
  "pending_features": ["feat-002"],
  "session_count": 0,
  "last_activity": "ISO-8601-timestamp"
}
```

### 3-Strike Error Recovery

```
STRIKE 1: Direct Fix
  - Analyze error type and root cause
  - Apply known solution pattern
  - Run tests to verify

STRIKE 2: Alternative Approach
  - Try different library/algorithm
  - Simplify implementation
  - Use different design pattern

STRIKE 3: Architecture Rethink
  - Question design assumptions
  - Research alternatives
  - Consider partial implementation

AFTER 3 STRIKES: Save checkpoint, request user guidance
```

### Loop Prevention (Anti-Infinite-Loop)

**⚠️ Critical: Prevents token waste in unattended operation**

```
DETECTION RULES:
┌─────────────────────────────────────────────────────────────────┐
│  Condition                    │ Threshold │ Action              │
├─────────────────────────────────────────────────────────────────┤
│  Same error repeated          │ 3 times   │ ESCALATE immediately│
│  Same file modified           │ 5 times   │ STOP, review approach│
│  Same command executed        │ 3 times   │ Try alternative     │
│  No progress in N operations  │ 10 ops    │ PAUSE, reassess     │
│  Single session too long      │ 50 turns  │ Checkpoint & pause  │
└─────────────────────────────────────────────────────────────────┘
```

**Loop Detection Algorithm:**

```python
class LoopDetector:
    MAX_SAME_ERROR = 3        # Same error appears 3 times
    MAX_SAME_FILE_EDIT = 5    # Same file edited 5 times
    MAX_SAME_COMMAND = 3      # Same command run 3 times
    MAX_NO_PROGRESS = 10      # No feature completed in 10 ops
    MAX_SESSION_TURNS = 50    # Maximum turns per session

    def check_loop(self, state):
        # Check 1: Same error repeating
        if self.count_same_error(state.errors) >= self.MAX_SAME_ERROR:
            return LoopAlert("SAME_ERROR_LOOP", "Escalate to user")

        # Check 2: Same file being edited repeatedly
        if self.count_same_file_edits(state.recent_edits) >= self.MAX_SAME_FILE_EDIT:
            return LoopAlert("FILE_EDIT_LOOP", "Review approach")

        # Check 3: Same command executing repeatedly
        if self.count_same_commands(state.recent_commands) >= self.MAX_SAME_COMMAND:
            return LoopAlert("COMMAND_LOOP", "Try alternative")

        # Check 4: No progress indicator
        if self.count_operations_without_progress(state) >= self.MAX_NO_PROGRESS:
            return LoopAlert("NO_PROGRESS", "Reassess strategy")

        # Check 5: Session too long
        if state.session_turns >= self.MAX_SESSION_TURNS:
            return LoopAlert("SESSION_LIMIT", "Create checkpoint and pause")

        return None  # No loop detected
```

**When Loop Detected - Escalation Protocol:**

```markdown
## LOOP ALERT: [Type]

**Detected Pattern**: [What repeated]
**Occurrences**: [Count] times
**Time Spent**: [Duration]
**Token Estimate**: [Approximate tokens used]

**Actions Taken**:
1. Stopped current operation
2. Saved checkpoint to .builder/checkpoints/
3. Logged loop pattern to .builder/loop-log.json

**Status**: PAUSED - Awaiting user input

**Options**:
A) Skip this feature and continue with next
B) Accept partial implementation
C) Provide additional context/guidance
D) Abort and generate report
```

**Loop State Tracking:**

```json
{
  "loop_detection": {
    "error_history": [
      {"error_hash": "abc123", "count": 2, "first_seen": "...", "last_seen": "..."}
    ],
    "file_edit_history": [
      {"file": "src/app.py", "edit_count": 3, "last_edit": "..."}
    ],
    "command_history": [
      {"command": "npm test", "run_count": 2, "last_run": "..."}
    ],
    "progress_check": {
      "operations_since_last_feature": 5,
      "last_completed_feature": "feat-002",
      "last_completion_time": "..."
    },
    "session_metrics": {
      "start_time": "...",
      "turn_count": 25,
      "tokens_estimated": 50000
    }
  }
}
```

**Mandatory Break Points:**

```
After every 20 operations:
  └─ Check progress: Did any feature advance?
      ├─ YES: Continue
      └─ NO: Pause and reassess

After every 10 minutes:
  └─ Review: Are we making meaningful progress?
      ├─ YES: Continue
      └─ NO: Checkpoint and evaluate

On same error 2nd occurrence:
  └─ Warning: Same error detected, trying different approach
  └─ Log: Record pattern for analysis

On same error 3rd occurrence:
  └─ STOP: Loop detected, escalate to user
  └─ Save: Create checkpoint before pause
```

### File Writing Strategy

For files > 500 lines, write in segments:
```python
SEGMENT_SIZE = 200  # lines per segment

# First segment: create file
write_file(path, first_segment)

# Subsequent segments: append
edit_file(path, append=next_segment)
```

### Technology Stack Detection

```python
def detect_tech_stack(project_path):
    indicators = {
        'python': ['requirements.txt', 'pyproject.toml', '*.py'],
        'nodejs': ['package.json', '*.ts', '*.js'],
        'rust': ['Cargo.toml', '*.rs'],
        'go': ['go.mod', '*.go'],
    }
    # Auto-detect and return primary stack
```

## Rules & Constraints

### MUST (Non-negotiable)

- Create `.builder/` directory before any work
- Update `state.json` after EVERY tool operation
- Log ALL errors to `errors.json` with resolution attempts
- Commit checkpoint after each feature completion
- Use segmented writes for files > 500 lines
- Run tests before marking feature complete

### SHOULD (Strong recommendations)

- Follow existing project conventions
- Use conventional commit messages
- Create meaningful tests (not just coverage)
- Document non-obvious decisions in `architecture.md`
- Prefer simpler solutions over clever ones

### NEVER (Explicit prohibitions)

- Delete user files without explicit permission
- Overwrite existing code without backup
- Commit secrets or credentials
- Skip error handling
- Make network calls without timeout
- Create infinite loops without escape conditions

### SAFETY CRITICAL (System Protection - HIGHEST PRIORITY)

**⚠️ These rules take precedence over ALL other operations. When in doubt, STOP and ASK.**

**Operations requiring explicit user confirmation:**

| Operation Type | Examples | Required Action |
|---------------|----------|-----------------|
| Files outside workspace | `C:\Windows\`, `/etc/`, `/usr/bin/` | STOP, warn user, get explicit approval |
| System configuration | Registry edits, `/etc/hosts`, environment variables | STOP, explain risk, get approval |
| Destructive operations | `rm -rf`, `format`, `DROP DATABASE` | STOP, show impact, get approval |
| Network/firewall changes | Port binding, firewall rules | STOP, explain scope, get approval |
| Package installation | `npm install -g`, `pip install --system` | Warn about system-wide changes |

**Pre-execution safety checks:**

```markdown
Before ANY operation, verify:

1. IS TARGET INSIDE WORKSPACE?
   ✅ Path starts with project root -> Proceed
   ⚠️ Path outside workspace -> STOP and confirm

2. IS OPERATION DESTRUCTIVE?
   ✅ Read/Write/Create in workspace -> Proceed
   ⚠️ Delete/Format/Truncate -> STOP and confirm

3. IS OPERATION SYSTEM-WIDE?
   ✅ Project-local operation -> Proceed
   ⚠️ Global install/System config -> STOP and confirm

4. COULD DATA BE LOST?
   ✅ New file creation -> Proceed
   ⚠️ Overwrite/Delete existing -> STOP and backup first
```

**Protected paths (NEVER modify without explicit approval):**

```
System directories:
- Windows: C:\Windows\, C:\Program Files\, C:\Program Files (x86)\
- Linux: /etc/, /usr/, /var/, /root/, /home/ (other users)
- macOS: /System/, /Library/, /Applications/

User data outside workspace:
- Desktop, Documents, Downloads (outside project)
- Any path containing "backup", "archive", "important"
- Database files not in project directory
- Configuration files: .bashrc, .zshrc, .gitconfig (global)
```

**Safe operation protocol:**

```
IF operation touches files outside workspace:
  1. STOP execution immediately
  2. Display warning to user:
     "⚠️ SAFETY ALERT: This operation affects files outside the workspace"
     - Target path: [full path]
     - Operation type: [read/write/delete]
     - Potential impact: [description]
  3. Ask for explicit confirmation:
     "Do you want to proceed? This action cannot be undone."
  4. If user declines -> Abort and suggest alternatives
  5. If user approves -> Log the approval and proceed cautiously

IF operation could cause data loss:
  1. Create backup before proceeding
  2. Log the operation to .builder/safety-log.json
  3. Provide rollback instructions
```

**Data safety principles:**

1. **Preserve user data** - Never delete/overwrite without explicit consent
2. **Backup before destructive ops** - Create .backup/ if needed
3. **Workspace isolation** - All operations confined to project directory
4. **Fail-safe defaults** - When uncertain, choose the safer option
5. **Audit trail** - Log all potentially dangerous operations

## MCP Integration

### Puppeteer (Web Testing)

```markdown
## E2E Test Pattern
1. Launch browser: mcp__puppeteer_navigate
2. Interact: mcp__puppeteer_click, mcp__puppeteer_type
3. Verify: mcp__puppeteer_evaluate, mcp__puppeteer_screenshot
4. Cleanup: mcp__puppeteer_close
```

### IDE Tools (Code Execution)

```markdown
## Code Execution Pattern
1. Write code to file
2. Execute: mcp__ide__executeCode
3. Check diagnostics: mcp__ide__getDiagnostics
4. Fix errors and retry
```

## Workflow Reporting

### Overview

Autonomous-builder now generates comprehensive workflow reports that document the entire development process, including user prompts, decisions, errors, and solutions.

**Features**:
- Automatic workflow logging during feature implementation
- Unified report template compatible with commit-with-reflection
- Detailed recording of user prompts and AI decisions
- Integration with knowledge-steward for experience extraction
- Pure Chinese reports for better readability

### Configuration

**Project-level configuration** (`.claude-workflows.yaml`):
```yaml
version: "1.0"
enabled: true

reporting:
  language: "zh-CN"
  detail_level: "detailed"
  output_dir: "docs/workflows"

skills:
  autonomous-builder:
    workflow_reporting: true
```

**Builder-level configuration** (`.builder/config.yaml`):
```yaml
workflow_reporting:
  enabled: true
  use_unified_template: true
  language: "zh-CN"
  detail_level: "detailed"
  record_all_tools: true
  record_decisions: true
```

### Workflow Log Structure

During feature implementation, autonomous-builder maintains a detailed log in `.builder/workflow-log.json`:

```json
{
  "session_id": "session-2026-02-15-001",
  "feature_id": "feat-003",
  "start_time": "2026-02-15T14:00:00Z",
  "end_time": "2026-02-15T14:45:00Z",
  "user_prompts": [
    {
      "timestamp": "2026-02-15T14:00:00Z",
      "prompt": "实现用户认证功能",
      "context": "用户希望添加JWT token验证"
    }
  ],
  "workflow_steps": [
    {
      "step": 1,
      "action": "分析需求",
      "tool": "Read",
      "files": ["server/auth.ts"],
      "duration_seconds": 120
    }
  ],
  "decisions": [
    {
      "point": "选择认证方案",
      "options": ["JWT", "Session", "OAuth"],
      "chosen": "JWT",
      "reason": "无状态，适合API"
    }
  ],
  "errors": [
    {
      "type": "TypeError",
      "message": "Cannot read property 'userId'",
      "solution": "更新User接口定义",
      "attempts": 2
    }
  ]
}
```

### Report Generation (Step 8)

After completing feature implementation and testing, autonomous-builder generates a workflow report:

1. **Read workflow log**: Load `.builder/workflow-log.json`
2. **Load template**: Use unified template from `docs/workflows/templates/unified-template.md`
3. **Fill template**: Populate all 12 sections with session data
4. **Save report**: Write to `docs/workflows/YYYY-MM/DD_workflow_[category]_[desc].md`
5. **Update index**: Regenerate `docs/workflows/INDEX.md`

### Report Structure

The generated report includes 12 sections:

1. **概述** - Summary of the work
2. **用户需求与提示词** - User requirements and key prompts
3. **工作流记录** - Detailed workflow steps, decisions, and tools used
4. **修改内容** - Files modified and main changes
5. **遇到的错误** - Errors encountered with details
6. **根本原因分析** - Root cause analysis
7. **调试过程** - Debugging steps and iterations
8. **经验总结** - Key insights and prevention strategies
9. **知识提炼** - Reusable patterns and anti-patterns
10. **测试与验证** - Test cases and verification steps
11. **参考资料** - Related documentation and resources
12. **指标** - Metrics (errors, iterations, success rate, etc.)

### Updated Commit Message Format

Commits now reference the workflow report:

```
feat: 实现用户认证功能

添加了JWT token验证和用户登录API端点。

工作流步骤: 8
决策点: 3
遇到错误: 2
调试迭代: 4

详见工作流报告: docs/workflows/2026-02/15_workflow_feature_user-auth.md

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

### Integration with knowledge-steward

Workflow reports can be analyzed by knowledge-steward to:
- Extract effective prompts and interaction patterns
- Identify reusable architectural patterns
- Build a knowledge base of common errors and solutions
- Generate experience summaries and best practices

See `references/workflow-recording.md` for detailed implementation guide.

## GitHub Integration

### Overview

Autonomous-builder integrates with GitHub for remote repository management, issue tracking, and release automation.

**Features**:
- Automatic push after each feature completion
- GitHub Issues tracking for features
- Release tags at milestones (25%, 50%, 75%, 100%)
- Version rollback support via GitHub history

### Prerequisites

**GitHub CLI (gh)**:
```bash
# Windows
winget install GitHub.cli

# macOS
brew install gh

# Linux
sudo apt install gh
```

**Authentication**:
```bash
gh auth login
gh auth status  # Verify
```

### Workflow Integration

**Initializer Agent (Session 1)**:
1. Prompt for GitHub repository URL (optional)
2. Verify `gh auth status`
3. Set up remote: `git remote add origin <url>`
4. Create README.md and PLANNING.md
5. Initial commit and push to GitHub
6. Create GitHub issues for all features

**Builder Agent (Sessions 2+)**:
1. Implement feature
2. Commit with issue reference: `Closes #N`
3. Push to GitHub: `git push origin main`
4. Update GitHub issue (auto-closed via commit)
5. Check milestone and create release tag if needed

### Commit Message Format

```
feat: 实现用户认证功能

添加了JWT token验证和用户登录API端点。

工作流步骤: 8
决策点: 3
遇到错误: 2
调试迭代: 4

详见工作流报告: docs/workflows/2026-02/15_workflow_feature_user-auth.md

Closes #123

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

### Release Tags

Automatic tags created at milestones:
- **25% completion**: v0.1.0 (Foundation)
- **50% completion**: v0.2.0 (Core Features)
- **75% completion**: v0.3.0 (Advanced Features)
- **100% completion**: v1.0.0 (Release)

### Error Handling

- **Network failures**: 3 retries with 5s delay, then queue for next session
- **Auth failures**: Disable GitHub integration, continue with local commits
- **Push conflicts**: Auto-pull with rebase and retry

### Disabling GitHub

Leave repository URL empty during initialization, or set `state.json → github.enabled = false`.

### Rollback

```bash
# Rollback to previous feature
git log --oneline
git reset --hard <commit_hash>
git push --force origin main
gh issue reopen <issue_number>

# Rollback to release tag
git checkout v0.1.0
git checkout -b rollback-to-v0.1.0
```

**See**: `references/github-integration.md` for comprehensive documentation.

## Examples

### Example 1: New Project Creation

**Input**: "Build a REST API for task management with Python FastAPI"

**Steps**:
1. Initialize `.builder/` with state.json
2. Analyze requirements -> Generate features.json:
   ```json
   {
     "features": [
       {"id": "feat-001", "name": "Project Setup", "status": "pending"},
       {"id": "feat-002", "name": "Database Models", "status": "pending"},
       {"id": "feat-003", "name": "CRUD Endpoints", "status": "pending"},
       {"id": "feat-004", "name": "Authentication", "status": "pending"},
       {"id": "feat-005", "name": "API Tests", "status": "pending"}
     ]
   }
   ```
3. Create architecture.md with FastAPI patterns
4. Implement feature by feature
5. Test each feature before moving to next
6. Generate final documentation

### Example 2: Resume Interrupted Project

**Input**: User starts new session, `.builder/state.json` exists

**Steps**:
1. Read state.json -> Get current phase and feature
2. Read features.json -> Get feature status
3. Resume from last checkpoint
4. Continue implementation

### Example 3: Bug Fix Request

**Input**: "Fix the authentication bug in my FastAPI app"

**Steps**:
1. Detect existing project structure
2. Read relevant code files
3. Identify bug using error-resolver patterns
4. Apply fix with 3-strike protocol
5. Run tests to verify fix
6. Update state and commit

## References

### Official Architecture Patterns (Anthropic claude-quickstarts)

- `references/two-agent-architecture.md`: **CRITICAL** - Two-Agent pattern for long-running tasks, fresh context per session
- `references/think-tool.md`: **CRITICAL** - Think Tool for complex reasoning before action
- `references/multi-layer-security.md`: **CRITICAL** - Defense in depth security architecture

### Core Capabilities

- `references/safety-protocols.md`: **CRITICAL** - System protection and safe operation protocols
- `references/loop-prevention.md`: **CRITICAL** - Anti-infinite-loop detection and token management
- `references/session-continuity.md`: **CRITICAL** - Auto-resume and continuous operation across sessions
- `references/skill-scheduling.md`: **CRITICAL** - Automatic skill discovery, planning, and dispatch
- `references/mcp-auto-integration.md`: **CRITICAL** - MCP auto-discovery, installation, and human-like computer control
- `references/github-integration.md`: **NEW** - GitHub integration for remote push, issue tracking, and release automation

### Implementation Guides

- `references/index.md`: Navigation for all reference docs
- `references/architecture-patterns.md`: Clean Architecture, Hexagonal, DDD
- `references/multi-language.md`: Language-specific patterns (Python, Node.js, Go, Rust)
- `references/error-recovery.md`: Detailed error handling strategies
- `references/mcp-integration.md`: MCP tool usage guide
- `references/testing-patterns.md`: Unit, integration, E2E testing

## Plugin 智能发现与自动使用 (ToolSearch Auto-Discovery)

### 核心原则

autonomous-builder 在执行任务时，**必须主动使用 ToolSearch** 动态发现并调用可用的 MCP 插件工具。这是对现有 MCP Auto-Integration 的升级，从静态配置变为运行时动态发现。

### 会话启动时自动发现

```
ON SESSION START (Step 0 - 在 Step 1 之前执行):

1. 使用 ToolSearch 探测所有可用插件:
   - ToolSearch("+playwright") → 浏览器自动化工具
   - ToolSearch("+github") → GitHub 操作工具
   - ToolSearch("+serena") → 代码语义分析工具
   - ToolSearch("context7") → 文档查询工具
   - ToolSearch("getDiagnostics") → IDE 诊断工具
   - ToolSearch("executeCode") → 代码执行工具

2. 构建能力矩阵并存入 .builder/state.json:
   {
     "discovered_plugins": {
       "playwright": true/false,
       "github_mcp": true/false,
       "serena": true/false,
       "context7": true/false,
       "ide_diagnostics": true/false,
       "ide_execute": true/false
     },
     "last_discovery": "ISO-8601-timestamp"
   }

3. 根据发现的插件调整工作流策略
```

### 各步骤插件智能调用

| Builder Step | ToolSearch 查询 | 用途 |
|-------------|----------------|------|
| Step 1: Get Context | `ToolSearch("+serena get_symbols_overview")` | 语义级代码结构分析，比 ls/grep 更精确 |
| Step 2: Start Server | `ToolSearch("+playwright navigate")` | 用 Playwright 代替 Puppeteer 验证服务 |
| Step 3: Regression Check | `ToolSearch("getDiagnostics")` | IDE 诊断检查类型错误和 lint 问题 |
| Step 4: Select Feature | `ToolSearch("context7")` | 查询相关库文档辅助实现决策 |
| Step 5: Implement | `ToolSearch("+serena find_symbol")` | 精确定位需要修改的代码符号 |
| Step 5: Implement | `ToolSearch("+serena replace_symbol_body")` | 语义级代码编辑 |
| Step 6: Browser Test | `ToolSearch("+playwright snapshot")` | 获取页面快照进行 UI 验证 |
| Step 6: Browser Test | `ToolSearch("+playwright click")` | 模拟用户交互 |
| Step 7: Update Status | `ToolSearch("+github update_issue")` | 更新 GitHub Issue 状态 |
| Step 8: Report | `ToolSearch("+github create_or_update_file")` | 直接推送报告到 GitHub |
| Step 9: Git Push | `ToolSearch("+github push_files")` | 通过 MCP 推送代码 |

### 实现阶段的智能插件选择

```
DURING FEATURE IMPLEMENTATION:

1. 代码分析阶段:
   IF serena 可用:
     → ToolSearch("+serena find_symbol") 定位目标符号
     → ToolSearch("+serena find_referencing_symbols") 分析影响范围
     → ToolSearch("+serena get_symbols_overview") 理解文件结构
   ELSE:
     → 回退到 Grep + Read 方式

2. 代码编辑阶段:
   IF serena 可用:
     → ToolSearch("+serena replace_symbol_body") 精确替换符号
     → ToolSearch("+serena insert_after_symbol") 插入新代码
   ELSE:
     → 回退到 Edit 工具

3. 测试阶段:
   IF playwright 可用:
     → ToolSearch("+playwright navigate") 打开应用
     → ToolSearch("+playwright snapshot") 获取页面状态
     → ToolSearch("+playwright click") 模拟交互
     → ToolSearch("+playwright browser_evaluate") 执行 JS 验证
   ELSE IF puppeteer 可用:
     → 使用 puppeteer MCP 工具
   ELSE:
     → 回退到 Bash 执行测试命令

4. 文档查询阶段:
   IF context7 可用:
     → ToolSearch("context7") 查询库文档
     → 获取最新 API 用法和最佳实践
   ELSE:
     → 使用 WebSearch/WebFetch

5. 代码质量检查:
   IF ide_diagnostics 可用:
     → ToolSearch("getDiagnostics") 获取诊断
     → 在提交前修复所有错误和警告
   ELSE:
     → 使用 Bash 运行 linter/type-checker
```

### 与现有 MCP Auto-Integration 的关系

```
旧方式 (静态):
  ON SESSION START → 运行 /mcp → 解析工具列表 → 硬编码工具名

新方式 (动态 ToolSearch):
  ON NEED → ToolSearch(关键词) → 发现工具 → 立即使用

优势:
  - 无需预先知道工具名称
  - 自动适应不同环境的插件配置
  - 按需加载，减少上下文占用
  - 关键词搜索比精确名称更灵活
```

### 注意事项

- ToolSearch 返回的工具**立即可用**，无需再次 select
- 关键词搜索已加载工具后，**不要**重复用 `select:` 加载
- 优先使用 MCP 工具而非 Bash 命令
- 如果 ToolSearch 未找到相关工具，回退到原有方式
- 将插件发现结果缓存到 state.json，避免重复探测
- 每个新会话重新探测一次（插件配置可能变化）

## Maintenance

- Sources: Anthropic agent patterns, claude-skills best practices
- Last updated: 2026-02-16
- Version: 2.0 (添加 ToolSearch 插件智能发现)
- Known limits: Cannot handle hardware-dependent code, GPU computing without setup

## Quality Gate

Before marking project complete:

1. [ ] All features in features.json have status "complete"
2. [ ] All tests pass (check features.json test counts)
3. [ ] No uncommitted changes
4. [ ] Documentation generated
5. [ ] State archived to `.builder/archive/`
