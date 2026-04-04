# VCO Tool Registry

Complete reference of VCO execution tools, their capabilities, APIs, state paths, and verification status.

## Tool Overview

| # | Tool | Type | Hook Types | State Location | Verified |
|---|------|------|------------|----------------|----------|
| 1 | Superpowers | Plugin (hooks + skills) | SessionStart | Stateless (conversation context) | ✅ |
| 2 | SuperClaude | Commands (markdown) | None | Serena MCP memory | ⚠️ Partial |
| 3 | Ralph-loop | Plugin (hooks + skills) | Stop | .claude/ralph-loop.local.md | ✅ |
| 4 | Claude-code-settings | Plugin (skills + agents) | None | .specify/, .kiro/, .autonomous/ | ✅ |
| 5 | Everything-claude-code | Plugin (hooks + skills + agents) | SessionStart, PreToolUse, PostToolUse, Stop | ~/.claude/sessions/, ~/.claude/homunculus/ | ✅ |
| 6 | Claude-flow/ruflo (collaboration backend) | MCP Server | PreToolUse, PostToolUse, PreCompact, Stop | .claude-flow/ | ⚠️ MCP依赖 |
| 7 | Codex native team runtime | Native runtime APIs | None | Session runtime | ✅ |
| 8 | Open Ralph Wiggum CLI (optional) | External CLI | None | .ralph/ | ⚠️ Optional |
| 9 | Cognee (optional long-term memory) | External graph memory backend | None | External/adapter-managed | ⚠️ Optional |
| 10 | xan (optional large-CSV backend) | External CLI | None | Dataset files / shell pipelines | ⚠️ Optional |
| 11 | fuck-u-code (optional quality debt analyzer) | External CLI | None | Analyzer workspace / report output | ⚠️ Optional |
| 12 | ivy (optional framework interop backend) | Python library / optional CLI | None | Python runtime / interop artifacts | ⚠️ Optional |
| 13 | Made-With-ML lifecycle patterns (optional governance source) | Methodology overlay | None | Config-driven advisory metadata | ⚠️ Optional |
| 14 | clean-code-python patterns (optional Python quality source) | Methodology overlay | None | Config-driven advisory metadata | ⚠️ Optional |
| 15 | system-design-primer patterns (optional architecture source) | Methodology overlay | None | Config-driven advisory metadata | ⚠️ Optional |
| 16 | LeetCUDA patterns (optional CUDA optimization source) | Methodology overlay | None | Config-driven advisory metadata | ⚠️ Optional |
| 17 | Scrapling (optional) | External CLI + MCP server | None | None (writes user-specified output files) | ⚠️ Optional |
| 18 | Docling MCP / provider contract | Provider contract / document-plane governance | None | Canonical config + references + verify gates | ✅ |
| 19 | Connector admission layer | Governance layer (catalog + provider admission) | None | Canonical config + matrix + verify gates | ✅ |
| 20 | Role-pack distillation layer | Governance layer (role cards + skill distillation rules) | None | Canonical docs + references + verify gates | ✅ |
| 21 | Capability catalog corpus | Governance layer (capability discovery / eval inputs) | None | Canonical config + references + verify gates | ✅ |

## Verification Status Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Capabilities verified, works as documented |
| ⚠️ Partial | Some capabilities verified, some claimed but unverified |
| ⚠️ MCP依赖 | Requires MCP server running; capabilities verified when available |
| ❌ | Claimed capability does not work as documented |

---

## 1. Superpowers (obra/superpowers)

**Version**: 4.3.1
**Location**: ~/.claude/plugins/cache/superpowers-marketplace/superpowers/4.3.1/

### Key Skills
| Skill | Purpose | Invocation | Verified |
|-------|---------|------------|----------|
| brainstorming | Design-first requirements discovery | `superpowers:brainstorming` | ✅ |
| writing-plans | Generate implementation plans | `superpowers:writing-plans` | ✅ |
| subagent-driven-development | Execute plans with fresh subagent per task | `superpowers:subagent-driven-development` | ✅ |
| dispatching-parallel-agents | Run independent tasks concurrently | `superpowers:dispatching-parallel-agents` | ✅ |
| systematic-debugging | Structured debugging workflow | `superpowers:systematic-debugging` | ✅ |
| verification-before-completion | Final verification checklist | `superpowers:verification-before-completion` | ✅ |

### Characteristics
- Soft-gate enforcement via persuasive language (not technical blocks)
- HARD-GATE on brainstorming: no implementation before design approval
- Stateless: no global state, all context in conversation
- Skill shadowing: personal skills override superpowers skills
- Wave B upstream review (2026-03-17): observed head `363923f74aa9cd7b470c0aaa73dee629a8bfdc90` / v5.0.2 emphasizes subagent context isolation and owner-aware cleanup; VCO admits the policy signal but keeps repo-governed mirrors authoritative.

### Sub-plugin: episodic-memory (disabled in VCO governance)
- Component availability: MCP server with `search` and `read` tools
- Backend: SQLite + sqlite-vec (384-dim vectors)
- Storage: ~/.claude/episodic-memory/
- Tool names: `episodic-memory:search`, `episodic-memory:read`
- VCO policy: disabled by `config/memory-governance.json`; do not route/use in normal flow

---

## 2. SuperClaude Framework

**Location**: ~/.claude/commands/sc/

### Key Commands
| Command | Purpose | Category | Verified |
|---------|---------|----------|----------|
| sc:brainstorm | Requirements discovery | Planning | ✅ |
| sc:design | Architecture design | Planning | ✅ |
| sc:implement | Feature implementation | Coding | ✅ |
| sc:spawn | Task orchestration | Orchestration | ✅ |
| sc:research | Deep web research | Research | ✅ |
| sc:workflow | Implementation workflow | Planning | ✅ |
| sc:test | Test execution | Quality | ✅ |
| sc:analyze | Code analysis | Quality | ✅ |
| sc:pm | Project manager agent | Management | ⚠️ Claims "always active" but has no hook implementation |

### Characteristics
- Pure command files (markdown), NOT a plugin
- No hooks registered (despite documentation claims) ⚠️
- sc:pm claims "always active" but has no hook implementation ⚠️
- Relies on Serena MCP for state persistence
- Uses cognitive personas (architect, frontend, backend, security, etc.)

---

## 3. Ralph-loop (compat wrapper + optional open backend)

**Compatibility wrapper location**: ~/.codex/skills/ralph-loop/
**Optional external backend**: `ralph` CLI from `@th0rgal/ralph-wiggum`

### Skills
| Skill | Purpose | Verified |
|-------|---------|----------|
| ralph-loop | Start continuous iteration loop | ✅ |
| cancel-ralph | Cancel active loop | ✅ |
| help | Explain plugin usage | ✅ |

### Characteristics
- Keeps stable command surface (`ralph-loop`, `cancel-ralph`) for VCO routing compatibility
- `compat` engine: local state file `.claude/ralph-loop.local.md`, manual `--next`, low dependency
- `open` engine: delegates to external open-ralph-wiggum CLI for auto-iteration (`--engine open`)
- `cancel-ralph` only manages `compat` local state
- Ralph-loop remains mutually exclusive with active XL team orchestration
- Wave B upstream review (2026-03-17): observed head `f1298b8af985a401ed67249365c8f18a8b74ef12` improves stale-exit and quota-exhaustion handling in the optional upstream backend; VCO records this as optional backend guidance only.

---

## 4. Claude-code-settings (feiskyer/claude-code-settings)

**Version**: 2.1.5
**Location**: ~/.claude/plugins/cache/claude-code-settings/claude-code-settings/2.1.5/

### Key Skills
| Skill | Purpose | Verified |
|-------|---------|----------|
| deep-research | Multi-agent parallel research workflow | ✅ |
| spec-kit-skill | 7-phase constitution-based spec-driven development | ✅ |
| kiro-skill | Interactive feature development (EARS format) | ✅ |
| autonomous-skill | Long-running multi-session task automation | ✅ |
| codex-skill | OpenAI Codex/GPT integration | ⚠️ Requires external API |

### Key Commands
| Command | Purpose | Verified |
|---------|---------|----------|
| think-harder | 4-phase structured analysis | ✅ |
| think-ultra | 7-phase ultra-comprehensive analysis | ✅ |
| eureka | Technical breakthrough documentation | ✅ |

### Agents
| Agent | Purpose | Verified |
|-------|---------|----------|
| pr-reviewer | GitHub PR code review | ✅ |
| ui-engineer | Frontend/UI development | ✅ |
| github-issue-fixer | Issue resolution workflow | ✅ |

### MCP Server
- Chrome DevTools MCP (chrome-devtools-mcp) ⚠️ Requires Chrome running

### Characteristics
- No hooks registered
- Provides LiteLLM proxy configuration (localhost:4000)
- Model mapping: Haiku -> gpt-5-mini
- Additive only, no behavior modification
- Wave B upstream review (2026-03-17): observed head `d0c0d2759f8aadfba1b3361b5860024e4a7e68d4` refines config and skills, but does not justify restoring settings-layer authority over VCO's current compatibility surfaces.

---

## 5. Everything-claude-code

**Version**: 1.7.0
**Location**: ~/.claude/plugins/cache/everything-claude-code/everything-claude-code/1.7.0/

### Key Agents
| Agent | Model | Purpose | Verified |
|-------|-------|---------|----------|
| planner | Opus | Feature planning | ✅ |
| architect | Opus | System design | ✅ |
| code-reviewer | Sonnet | Quality/security review | ✅ |
| tdd-guide | Sonnet | Test-driven development | ✅ |
| security-reviewer | Sonnet | Vulnerability detection | ✅ |
| build-error-resolver | Sonnet | Build fix specialist | ✅ |

### Key Skills
| Skill | Purpose | Verified |
|-------|---------|----------|
| tdd-workflow | TDD enforcement (80%+ coverage) | ✅ |
| verification-loop | Comprehensive verification | ✅ |
| continuous-learning | Pattern extraction from sessions | ✅ |
| continuous-learning-v2 | Instinct-based learning system | ✅ |

### Instinct System (v2)
- Observations: ~/.claude/homunculus/observations.jsonl
- Instincts: ~/.claude/homunculus/instincts/personal/
- Evolved: ~/.claude/homunculus/evolved/
- Confidence scoring: 0.3 (tentative) to 0.9 (near-certain)
- Auto-approve threshold: 0.7

### Hooks
- PreToolUse: dev server blocker, tmux reminder, git push reminder, doc blocker, compaction suggester
- PostToolUse: PR logger, build completion, auto-format, TypeScript check, console.log warning
- SessionStart: context loader
- Stop: console.log checker

---

## 6. Claude-flow/ruflo (Collaboration Backend)

**Version**: 3.1.0-alpha.41
**MCP Server**: ruflo ⚠️ MCP 依赖
- 150+ 工具已注册为 deferred tools，需通过 ToolSearch 加载后使用
- 首次调用任何 ruflo 工具前，必须先 ToolSearch 加载对应工具
- MCP server 未运行时所有工具不可用，走 fallback chain
**Location**: ~/.npm-global/node_modules/claude-flow/

### MCP Tool Categories (100+ tools)
| Category | Key Tools | Purpose | Verified |
|----------|-----------|---------|----------|
| agent | agent_spawn, agent_list, agent_pool | Agent lifecycle management | ⚠️ MCP依赖 |
| swarm | swarm_init, swarm_status | Basic coordination | ⚠️ MCP依赖 |
| hive-mind | hive-mind_spawn, hive-mind_consensus | Advanced collective intelligence | ⚠️ MCP依赖 |
| memory | memory_store, memory_search | HNSW vector memory | ⚠️ MCP依赖 |
| workflow | workflow_create, workflow_execute | Workflow engine (5 step types) | ⚠️ MCP依赖 |
| task | task_create, task_list | Task queue management | ⚠️ MCP依赖 |
| session | session_save, session_restore | Session management | ⚠️ MCP依赖 |

### State Directory
```
.claude-flow/
  agents/store.json
  memory/ (sql.js + HNSW)
  hive-mind/state.json
  workflows/store.json
  tasks/store.json
  sessions/
```

### Characteristics
- 60+ agent type templates with model routing（基于 prompt 模板的角色分化）
- 3 aggregation modes (Majority voting, Weighted voting, Multi-perspective validation)
- HNSW vector search (150x-12,500x faster than JSON)
- File-based state in .claude-flow/ (per-project)
- No API keys required (local embeddings)

---

## 7. Codex Native Team Runtime (Primary XL Executor)

Runtime-native APIs for multi-agent orchestration:

| API | Purpose | Verified |
|-----|---------|----------|
| `spawn_agent` | Create specialized agents | ✅ |
| `send_input` | Assign/follow-up work to specific agent | ✅ |
| `wait` | Synchronize and collect results | ✅ |
| `close_agent` | Explicit lifecycle cleanup | ✅ |

Characteristics:
- No MCP dependency
- Primary XL path in VCO
- Works with role-specialized prompts and ownership boundaries

---

## 8. Open Ralph Wiggum CLI (Optional Auto-Loop Backend)

**Package**: `@th0rgal/ralph-wiggum`
**Binary**: `ralph`

### Key Capabilities
- Auto-iteration loop for repeated prompts (`--max-iterations`, completion promises)
- Tasks mode (`--tasks`, `--add-task`, `--remove-task`, `--list-tasks`)
- Mid-loop context injection (`--add-context`, `--clear-context`)
- Runtime status dashboard (`--status`)

### VCO Integration Boundary
- Invoked only through local `ralph-loop` wrapper with `--engine open`
- Must not run concurrently with active XL team orchestration
- Recommended to use no-commit mode during loop and complete VCO quality gates before manual commit

---

## 9. Cognee (Optional Long-Term Graph Memory)

**Purpose**: long-term graph memory and relationship retrieval
**Status in VCO**: optional backend, activated only under memory governance policy

### VCO Memory Governance Boundary
- `state_store`: session state only
- `Serena`: explicit project decisions only
- `ruflo`: short-term session vector cache only
- `Cognee`: long-term graph memory + relationship retrieval only
- `episodic-memory`: disabled in VCO governance path

### Integration Notes
- VCO route selection remains unchanged; memory governance is post-route advice only.
- If Cognee is unavailable, fall back to Serena summaries for long-term retrieval.
- Never use Cognee to replace state_store session state tracking.

---

## 10. xan (Optional Large-CSV Backend)

**Package**: `xan`
**Binary**: `xan`

### Key Capabilities
- High-performance CSV/TSV processing (Rust, low-memory, streaming-friendly)
- Fast tabular operations (`filter`, `sort`, `dedup`, `join`, `groupby`, `frequency`)
- Works well for large flat files where workbook semantics are not required

### VCO Integration Boundary
- Routed as a skill candidate under `docs-media` for tabular tasks.
- Activated through data-scale overlay (`data_scale_advice`) using real file signals.
- Does not replace workbook-focused skills (`xlsx`, `excel-analysis`).
- Does not replace ML workflow routing (`data-ml` pack remains authoritative for model tasks).

---

## 11. fuck-u-code (Optional Quality Debt Analyzer)

**Package/Repo**: `Done-0/fuck-u-code`
**Binary**: `fuck-u-code` (optional, environment-specific)

### Key Capabilities
- Offline-oriented quality debt signal extraction (maintainability/test/security debt perspectives)
- Works as a focused analyzer to complement normal review flows
- Useful for difficult cleanup/refactor tasks where plain lint/test signals are insufficient

### VCO Integration Boundary
- Integrated through `quality-debt-overlay` as post-route advice only.
- Does not replace `code-reviewer`, `security-reviewer`, or `tdd-guide`.
- Missing binary never blocks routing; status is reported as `tool_unavailable`.
- Current default is `manual_only` invocation hint mode to keep routing deterministic.

---

## 12. ivy (Optional Framework Interop Backend)

**Package/Repo**: `ivy-llc/ivy`
**Import/Binary**: `import ivy` (optional CLI entrypoint if installed by environment)

### Key Capabilities
- Cross-framework model/function migration (`transpile`)
- Optional graph-level execution optimization (`trace_graph`)
- Backend interoperability for migration scenarios (for example PyTorch <-> TensorFlow/JAX pathways)

### VCO Integration Boundary
- Integrated through `framework-interop-overlay` as post-route advice only.
- Does not replace training/evaluation flows in `data-ml`.
- Missing runtime never blocks routing; status is reported as `tool_unavailable`.
- Current default is `manual_only` invocation hint mode to keep routing deterministic.

---

## 13. Made-With-ML Lifecycle Patterns (Optional Governance Source)

**Package/Repo**: `GokuMohandas/Made-With-ML`
**Integration Type**: methodology and lifecycle policy source (non-executable dependency)

### Key Capabilities Imported into VCO
- Lifecycle stage framing: `develop -> evaluate -> deploy -> iterate`
- Evidence expectations: run/evaluation/baseline/test/monitoring artifacts
- Production-readiness mindset: promote explicit evidence before release decisions

### VCO Integration Boundary
- Integrated through `ml-lifecycle-overlay` as post-route advice only.
- Does not replace `data-ml` pack routing or ML tool execution.
- Does not mutate route selection; only emits lifecycle advice metadata.
- Compatible with `data-scale`, `quality-debt`, and `framework-interop` overlays.

---

## 14. clean-code-python Patterns (Optional Python Quality Source)

**Package/Repo**: `zedr/clean-code-python`
**Integration Type**: methodology and Python clean-code policy source (non-executable dependency)

### Key Capabilities Imported into VCO
- Python-specific clean-code principles (naming, function/class responsibilities, side effects, duplication discipline)
- Practical anti-pattern framing for refactor readiness (long functions, flag args, magic numbers, god objects)
- Review-time guidance for maintainability-focused Python change sets

### VCO Integration Boundary
- Integrated through `python-clean-code-overlay` as post-route advice only.
- Does not replace `code-reviewer`, `tdd-guide`, or `quality-debt-overlay`.
- Does not mutate route selection; only emits Python clean-code advice metadata.
- Designed for automatic `.py/.pyi` signal detection with mode-gated confirm advice.

---

## 15. system-design-primer Patterns (Optional Architecture Source)

**Package/Repo**: `donnemartin/system-design-primer`
**Integration Type**: architecture methodology source (non-executable dependency)

### Key Capabilities Imported into VCO
- Architecture-first decomposition for distributed system planning (requirements, trade-offs, bottlenecks)
- Coverage-driven design checklist (capacity, consistency/availability, caching, partitioning, failure recovery, observability, cost)
- Design-review prompts that reduce under-specified architecture plans before implementation

### VCO Integration Boundary
- Integrated through `system-design-overlay` as post-route advice only.
- Does not replace OpenSpec governance or pack routing decisions.
- Does not mutate route selection; only emits architecture-coverage advice metadata.
- Suppresses interview-only prompts via negative keywords to avoid noisy production routing.

---

## 16. LeetCUDA Patterns (Optional CUDA Optimization Source)

**Package/Repo**: `xlite-dev/LeetCUDA`
**Integration Type**: CUDA optimization methodology source (non-executable dependency)

### Key Capabilities Imported into VCO
- CUDA kernel optimization checklist framing (memory hierarchy, tensor core path, occupancy, launch parameters)
- Profiling-first workflow emphasis (baseline vs optimized, Nsight evidence, reproducible hardware context)
- Correctness/guardrail expectations (numerical parity checks, fallback/degrade strategy)

### VCO Integration Boundary
- Integrated through `cuda-kernel-overlay` as post-route advice only.
- Does not replace `data-ml` pack routing or generic code-quality routing.
- Does not mutate route selection; only emits CUDA optimization advice metadata.
- License-safe boundary: methodology-level advisory only, no upstream code vendoring (`LeetCUDA` upstream is GPL-3.0).

---

## 17. Scrapling (optional web scraping CLI + MCP server)

**Type**: External CLI + optional MCP server
**Primary Use**: Web scraping / targeted extraction (CSS selector / XPath), pre-extract page content before handing to the LLM to reduce tokens and speed up workflows.
**Invocation**:
- CLI: `scrapling ...`
- MCP server (optional): `scrapling mcp` (stdio)

**State Location**: None (stateless). Outputs are written to user-specified files/paths only.

**Verified**: ⚠️ Optional
Notes:
- Requires user environment install (e.g. `pip install "scrapling[ai]"` for MCP features).
- If unavailable or blocked by anti-bot / interactive flows, fall back to `playwright` (real browser automation).
## 18. Docling MCP / provider contract

**Type**: Provider contract / document-plane governance
**Primary Use**: Treat `docling` as the canonical document-plane contract source for structured extraction, not as a second document orchestrator.
**Invocation**: Governance only; use the VCO document-plane rules and provider policy.
**State Location**:
- `config/docling-provider-policy.json`
- `references/docling-output-spec.md`
- `docs/design/docling-document-plane-integration.md`

**VCO Integration Boundary**:
- productized as a provider contract only
- may inform routing and extraction expectations
- must not replace the canonical VCO route owner

## 19. Connector admission layer

**Type**: Governance layer (catalog + provider admission)
**Primary Use**: Admit or reject connector candidates from `awesome-mcp-servers`, `composio`, and `activepieces` with explicit risk classes and rollback notes.
**State Location**:
- `config/connector-admission-policy.json`
- `references/connector-capability-matrix.md`
- `docs/connector-admission-governance.md`

**VCO Integration Boundary**:
- connector catalogs are discovery inputs only
- providers remain `advice-first` / `confirm-gated`
- no connector source may become a second route owner or automation runtime by default

## 20. Role-pack distillation layer

**Type**: Governance layer (role cards + skill distillation rules)
**Primary Use**: Distill value from `agent-squad`, `claude-skills`, `awesome-agent-skills`, `awesome-claude-code-subagents`, and `antigravity-awesome-skills` into VCO-native role packs and quality rules.
**State Location**:
- `config/role-pack-policy.json`
- `references/role-pack-catalog.md`
- `references/skill-distillation-rules.md`
- `docs/role-pack-distillation-governance.md`

**VCO Integration Boundary**:
- role packs may inform team templates and review quality
- they must not become a second orchestrator or second team execution owner

## 21. Capability catalog corpus

**Type**: Governance layer (capability discovery / eval inputs)
**Primary Use**: Quantify the value slices absorbed from the 15-project upstream corpus and provide a canonical discovery/eval index.
**State Location**:
- `config/capability-catalog.json`
- `references/capability-catalog.md`
- `docs/governance/discovery-eval-corpus-governance.md`
- `docs/external-tooling/upstream-eval-pilot-scenarios.md`

**VCO Integration Boundary**:
- capability cards are discovery and evaluation aids only
- they cannot supersede the primary router or create a new runtime surface
