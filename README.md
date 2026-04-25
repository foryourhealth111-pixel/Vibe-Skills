<div align="right">
  <b>🇬🇧 English</b> &nbsp;|&nbsp; <a href="./README.zh.md">🇨🇳 中文</a>
</div>

<br/>

<div align="center">

<a href="https://github.com/foryourhealth111-pixel/Vibe-Skills">
  <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=700&size=45&pause=1000&color=7B61FF&center=true&vCenter=true&width=700&height=100&lines=Vibe+Skills;Super+Skill+Harness;Agent+Orchestration+Layer" alt="VibeSkills Typing Logo" />
</a>

<br/>

<img src="./logo.png" width="260px" alt="VibeSkills Logo"/>

<br/><br/>

### A Super Skill harness for skills-capable AI agents

Install the Skills package, call `vibe`, and let the harness do the heavy lifting. VibeSkills reads the task, breaks it into stages, automatically brings in the right expert Skills, checks the work, and keeps useful context for the next session. It is built to grow: future domain Skills can plug into the same harness instead of forcing every field to reinvent its own workflow.

&nbsp;
*This is not just more tools. It is a new kind of Super Skill: the harness becomes the skill manager, so you do not have to memorize a catalog, babysit every step, or keep reminding the agent how work should move.*

<br/>

<table align="center">
<tr>
<td align="left">
<pre><code>&gt; vibe
  intent.freeze()        -> requirement_doc
  plan.stage()           -> xl_plan
  skills.orchestrate()   -> expert Skills by phase
  evidence.verify()      -> tests, checks, artifacts
  memory.preserve()      -> next-session context</code></pre>
</td>
</tr>
</table>

<br/>

<a href="https://github.com/foryourhealth111-pixel/Vibe-Skills/stargazers">
  <img src="https://img.shields.io/github/stars/foryourhealth111-pixel/Vibe-Skills?style=for-the-badge&logo=github&color=7B61FF&label=STARS" alt="stars">
</a>
<a href="https://github.com/foryourhealth111-pixel/Vibe-Skills/network/members">
  <img src="https://img.shields.io/github/forks/foryourhealth111-pixel/Vibe-Skills?style=for-the-badge&logo=git&color=45a1ff&label=FORKS" alt="forks">
</a>
<a href="https://github.com/foryourhealth111-pixel/Vibe-Skills/pulse">
  <img src="https://img.shields.io/github/last-commit/foryourhealth111-pixel/Vibe-Skills?style=for-the-badge&logo=git-lfs&color=32CD32&label=MOMENTUM" alt="last commit">
</a>
<img src="https://komarev.com/ghpvc/?username=vibe-skills-foryourhealth&label=NODES+ACTIVE&color=0078d7&style=for-the-badge" alt="Visitors">
&nbsp;
<img src="https://img.shields.io/badge/Architecture-VCO_Runtime-orange?style=for-the-badge" alt="Arch">
&nbsp;
<img src="https://img.shields.io/badge/Skills-340%2B-blueviolet?style=for-the-badge" alt="Skills Count">
&nbsp;
<img src="https://img.shields.io/badge/Harness-Automatic_Orchestration-32CD32?style=for-the-badge" alt="Automatic Orchestration">
&nbsp;
<img src="https://img.shields.io/badge/Package-Portable_Skills_Bundle-45a1ff?style=for-the-badge" alt="Portable Skills Bundle">
&nbsp;
<img src="https://img.shields.io/badge/Extensible-Any_Domain_Skills-ff5f87?style=for-the-badge" alt="Any Domain Skills">

<br/><br/>

🧠 Planning · 🛠️ Engineering · 🤖 AI · 🔬 Research · 🎨 Creation

<br/>

<a href="https://github.com/foryourhealth111-pixel/Vibe-Skills/blob/main/docs/install/one-click-install-release-copy.en.md">
  <img src="https://img.shields.io/badge/⚡_Get_Started-7B61FF?style=for-the-badge" alt="Install">
</a>
&nbsp;
<a href="https://github.com/foryourhealth111-pixel/Vibe-Skills/blob/main/docs/quick-start.en.md">
  <img src="https://img.shields.io/badge/📖_Quick_Start-2d3748?style=for-the-badge" alt="Docs">
</a>
&nbsp;
<a href="./README.zh.md">
  <img src="https://img.shields.io/badge/🇨🇳_中文-45a1ff?style=for-the-badge" alt="Chinese">
</a>

<br/><br/>

<kbd>Install</kbd> &nbsp;→&nbsp;
<kbd>vibe | vibe-upgrade</kbd> &nbsp;→&nbsp;
<kbd>Harnessed Workflow</kbd> &nbsp;→&nbsp;
<kbd>Stage Skills</kbd> &nbsp;→&nbsp;
<kbd>TDD / Verification</kbd> &nbsp;→&nbsp;
<kbd>Persistent Context</kbd>

</div>

## 📋 Table of Contents

- [Runtime at a Glance](#-runtime-at-a-glance)
- [A New Kind of Super Skill](#-a-new-kind-of-super-skill)
- [What makes it different](#-what-makes-it-different)
- [Who is it for](#-who-is-it-for)
- [Intelligent Routing](#-intelligent-routing-how-340-skills-collaborate-without-conflict)
- [Memory System](#-memory-system-resume-context-across-the-same-workspace)
- [Full Capability Map](#-full-capability-map-your-all-in-one-workbench)
- [Installation & Management](#️-installation--skills-management)
- [Getting Started](#-getting-started)


<details>
<summary><b>🔑 New here? Quick glossary of key terms (click to expand)</b></summary>

<br/>

| Term | Plain-English Meaning |
|:---|:---|
| **Harness** | The workflow layer around your AI agent. It figures out the next stage, calls the right Skills, checks the work, and saves useful context. |
| **Skill** | A focused expert capability, such as `tdd-guide`, `code-review`, data analysis, writing, or research support. |
| **Vibe / VCO** | The canonical runtime that runs the harness. Public entrypoints are `vibe` and `vibe-upgrade`. |
| **Automatic orchestration** | Different Skills are selected and used at different moments: requirements, planning, implementation, review, verification, and cleanup. |
| **Open Skill plane** | New domain Skills can plug into the same harness, so the workflow can grow from software work into research, design, education, finance, law, and more. |
| **TDD / proof-first delivery** | Work should be backed by tests, checks, artifacts, or explicit manual-review notes before completion is claimed. |
| **Workspace memory** | Structured project information, decisions, and evidence are stored so later sessions can continue without starting over. |

</details>

> [!IMPORTANT]
> ### 🎯 Core Vision
>
> VibeSkills starts from a simple idea: Skills become much more useful when an intelligent harness knows how to orchestrate them.
>
> It packages a governed harness, expert Skills, TDD-oriented execution, verification rules, and workspace memory into one plug-in Skills bundle. You should not have to remember every tool, choose every Skill by hand, prompt every phase, police every test, or rebuild context in every new session.
>
> It is also not limited to the Skills it ships with today. VibeSkills is an extensible harness: as new domain Skills appear, the same `vibe` entry can route them, stage them, verify their work, and preserve context across sessions.
>
> **Plug it in, invoke `vibe`, and the agent gets a clearer way to work.**
> Because VibeSkills is delivered as a Skills package, it is easy to install, easy to move across hosts, and useful for many kinds of work out of the box.

<br/>

<img width="1376" height="768" alt="Generated Image April 21, 2026 - 8_49PM" src="https://github.com/user-attachments/assets/82c6e1f2-23fb-46de-b4c6-2f73b5350d4c" />



---

## 🛰️ Runtime at a Glance

VibeSkills feels different because the harness owns the sequence. The user brings intent; `vibe` turns that intent into staged work, routes expert Skills where they belong, and keeps the proof trail alive for the next session.

```mermaid
flowchart LR
    accTitle: VibeSkills Harness Flow
    accDescr: User intent enters the vibe harness. The harness freezes intent, plans stages, routes expert Skills, verifies evidence, and preserves workspace context.

    user["User Intent"]
    vibe["vibe<br/>Super Skill Harness"]
    freeze["Freeze<br/>Requirement"]
    plan["Plan<br/>Stages"]
    route["Route<br/>Expert Skills"]
    skills["340+ Skills<br/>bounded by phase"]
    future["Future Domain Skills<br/>research / finance / law / education / more"]
    verify["Verify<br/>Tests + Evidence"]
    memory["Remember<br/>Workspace Context"]

    user --> vibe --> freeze --> plan --> route --> verify --> memory
    route --> skills --> verify
    route --> future --> verify

    classDef core fill:#ede9fe,stroke:#7B61FF,stroke-width:2px,color:#1f1147
    classDef stage fill:#e0f2fe,stroke:#0284c7,stroke-width:1.5px,color:#0c4a6e
    classDef proof fill:#dcfce7,stroke:#16a34a,stroke-width:1.5px,color:#14532d
    classDef user fill:#fff7ed,stroke:#f97316,stroke-width:1.5px,color:#7c2d12

    class vibe core
    class freeze,plan,route,skills,future stage
    class verify,memory proof
    class user user
```

<div align="center">

| Signal | What it means |
|:---|:---|
| `one entry` | Start with `vibe`; keep `vibe-upgrade` for updates. |
| `stage router` | Different moments get different Skills. |
| `open skill plane` | New domain Skills can plug into the same harness instead of creating a new workflow every time. |
| `proof trail` | Tests, checks, artifacts, or manual-review state back delivery claims. |
| `memory plane` | Requirements, plans, decisions, and evidence survive the chat window. |

</div>

---

## 🧬 A New Kind of Super Skill

The agent-skills world is moving past "give the model a bigger toolbox."

Projects like **[Superpowers](https://github.com/obra/superpowers)** show that Skills can become a serious software-development methodology: clarify before coding, design before implementation, test before claiming success. **[GSD / Get Shit Done](https://github.com/gsd-build/get-shit-done)** shows another important truth: agents need context engineering, specs, milestones, and a way to keep projects moving instead of drifting in chat history.

VibeSkills builds on that same direction, but pushes the package shape further:

> **A normal Skill says:** "Here is one thing I can do."
>
> **A Super Skill says:** "Here is how the work should run."

VibeSkills is the second kind. It wraps the harness, the expert Skills, the stage orchestration, the verification discipline, and the workspace memory into one portable Skills package. More importantly, it gives future Skills a place to plug in: the harness can keep the same entry, stages, proof trail, and memory model as the skill plane expands.

<div align="center">

| Project style | What it is great at | Where VibeSkills goes further |
|:---|:---|:---|
| **Traditional skill collections** | Give the agent more capabilities | Turns those capabilities into a staged, verified, context-aware working system |
| **Superpowers-style methodology** | Gives coding agents stronger development discipline | Generalizes the idea into a broader Super Skill harness with automatic expert-Skill orchestration |
| **GSD-style project flow** | Keeps projects moving through specs, context, milestones, and execution | Makes stage-aware Skill dispatch and cross-session memory first-class runtime behavior |
| **VibeSkills** | One portable Super Skill package for Skills-capable agents | Simple entry, intelligent orchestration, lower user cognitive load, TDD/verification, multi-host adaptation, and an extensible plane for future domain Skills |

</div>

The innovation is not simply "more Skills." The innovation is turning Skills from a fixed library into an open, working system that can absorb new expert capabilities over time.

---


## ✨ What makes it different?

> Most skill repos answer: _"What tools can my AI use?"_
> **VibeSkills answers the more practical question: _"How can my AI use those Skills automatically, at the right time, without making me manage the whole process?"_**

The operating model is intentionally simple:

<div align="center">

| Layer | What it does for the user |
|:---|:---|
| **Easy start** | Start with `vibe`; use `vibe-upgrade` to keep the package current. No long command menu to learn first. |
| **Intelligent harness** | The agent follows a structured path: clarify → plan → execute → test → verify → preserve context. |
| **Automatic Skill orchestration** | The harness picks expert Skills by task, phase, and constraints, then keeps them in bounded roles. |
| **Extensible Skill plane** | New Skills for any domain can join the same orchestration model instead of forcing users to learn a separate workflow for each field. |
| **TDD and verification discipline** | Work is pushed toward tests, checks, evidence, and explicit acceptance instead of unsupported completion claims. |
| **Structured context storage** | Requirements, plans, decisions, handoff notes, and evidence are stored in predictable places for future sessions. |
| **Portable Skills package** | The core is a plug-in bundle, so any Skills-capable AI agent can get the same workflow upgrade across supported hosts. |

</div>

<br/>

<div align="center">

| Without a harness | With VibeSkills |
|:---|:---|
| You keep deciding the next prompt, tool, and quality check. | The harness guides the workflow and asks for confirmation where it matters. |
| Skills are a long list the agent may forget. | Skills become expert workers dispatched automatically by phase and task type. |
| Each new domain tends to create another workflow for the user to learn. | New domain Skills can plug into the same `vibe` harness and inherit the same staged rhythm. |
| "Done" can mean the model stopped talking. | Delivery is tied to tests, checks, artifacts, or explicit manual-review state. |
| Long projects lose context across sessions. | Requirements, plans, decisions, and evidence are stored for continuation. |
| Every host needs a different workflow story. | The core stays a general Skills package, with host adapters around it. |

</div>

<br/>

---


## 👥 Who is it for?

VibeSkills is for people who want AI agents to be easy to start, useful across many kinds of work, and less exhausting to manage.

<details>
<summary>Is this for you? Click to expand</summary>

<br/>

<div align="center">

| Audience | Description |
|:---:|:---|
| 🎯 **Users who need reliable delivery** | Want the agent to clarify, plan, test, and verify instead of rushing to an answer. |
| ⚡ **Power users of AI agents** | Need one harness to coordinate many expert Skills without micromanaging every step. |
| 🏢 **Teams standardizing AI workflows** | Want repeatable requirements, plans, verification, and handoff artifacts. |
| 🧩 **Skill builders and integrators** | Want a plug-in package model that is easy to install and portable across hosts. |
| 😩 **Users tired of tool micromanagement** | Want the system to decide which Skill belongs in which stage. |

</div>

> _If you only need one isolated script, VibeSkills may be more structure than you need. If you want an AI agent that can handle real work across phases and sessions, this is the friendly layer that makes Skills usable at scale._

</details>

<br/>

---


## 🔀 Intelligent Routing: How 340+ Skills Collaborate Without Conflict

The core point is simple: the Skills are not the product by themselves. The harness is what turns them into a usable working system.

`vibe` owns the workflow. It decides when the agent should clarify, when it should plan, which specialist Skills should help, when tests or checks should run, and when delivery can be claimed. The user gets one simple entry instead of a pile of decisions.

<div align="center">

| Common worry | What actually happens |
|:---|:---|
| "There are too many Skills." | You do not manually choose from the whole list. The harness routes intelligently by task, phase, and constraints. |
| "Similar Skills might conflict." | The router picks bounded roles, and specialist Skills stay scoped to the current phase or work unit. |
| "Multi-agent work will get chaotic." | Larger work is split into bounded units, with explicit ownership, verification, and coordinator approval. |

</div>

### How the harness works in practice

- **Start with one governed entry**: Most work enters through `vibe`, so the user does not have to choose a workflow tree manually.
- **Freeze intent before execution**: Requirements and plans become stable artifacts instead of disappearing into chat history.
- **Dispatch experts automatically by stage**: Requirement, planning, implementation, testing, review, and cleanup can each use different Skills.
- **Drive toward evidence**: TDD, targeted checks, artifact review, and delivery acceptance keep completion claims grounded.
- **Preserve context**: The runtime stores enough structure for another session or agent to continue.

---

### Why many expert Skills can coexist

- They are not all active at once.
- Some serve different stages: one clarifies, one plans, one implements, one reviews, one verifies.
- Some serve different domains: code, research, data, writing, design, documents, operations.
- Governance rules keep the harness, not the individual Skill, in charge of the final workflow.

---

### M / L / XL Execution Levels

After selecting the primary route, the runtime also chooses the execution grade based on task complexity:

<div align="center">

| Level | Use Case | Characteristics |
|:---:|:---|:---|
| **M** | Narrow-scope work with clear boundaries | Single-agent, token-efficient, fast response |
| **L** | Medium complexity requiring design, planning, and review | Governed multi-step execution, usually in planned serial order |
| **XL** | Large tasks with independent parts worth splitting | The coordinator breaks work into bounded units and can run independent units in parallel waves |

</div>

> Even in XL, this is not a free-for-all. The system decides the main route first, then assigns skills to each bounded unit under the same governed coordinator.

---

<details>
<summary><b>🔍 Expand: wrapper entrypoints, grade overrides, and routing notes</b></summary>

<br/>

- Public discoverable entries are `vibe` and `vibe-upgrade`.
- `vibe` is progressive: it stops after `requirement_doc`, then after `xl_plan`, and only reaches `phase_cleanup` after explicit bounded re-entry approval at each boundary.
- `vibe-upgrade` runs the governed upgrade path.
- Compatibility stage IDs such as `vibe-what-do-i-want`, `vibe-how-do-we-do`, and `vibe-do-it` are disabled as public host entries. They may remain in runtime metadata for continuity, but installers must not materialize them as host-visible command or skill wrappers.
- The only lightweight public grade overrides are `--l` and `--xl`. Aliases like `vibe-l`, `vibe-xl`, or stage-plus-grade combinations are intentionally unsupported.
- When specialist skills such as `tdd-guide` or `code-review` are called, they assist a phase or a bounded unit. They do not take over global coordination.
- In XL multi-agent work, worker lanes can suggest specialist help, but the coordinator approves the final assignment.

</details>

<br/>

---


## 🧠 Memory System: Resume Context Across the Same Workspace

_Routing decides which skill should lead. Memory decides whether the next session has to start from zero._

VibeSkills memory is built to solve three practical problems:

- resume confirmed project context inside the same workspace
- keep long tasks resumable after interruption or handoff
- preserve decisions, handoff notes, and related evidence without dumping full history back into every prompt

It does not mean "save everything forever."
By default, memory is scoped and layered: session state, project conventions, task-relevant retrieval, and controlled long-term knowledge all have different boundaries.

<br/>

<div align="center">

| What users usually ask | Default behavior |
|:---|:---|
| Do I need to re-explain project context in every new session? | No. Confirmed project context can be resumed inside the same workspace. |
| What if a long task gets interrupted? | Key progress can be folded into resumable working, tool, and evidence memory. |
| Will unrelated history flood the prompt? | No. Retrieval stays bounded and task-relevant. |
| Will one project leak into another? | No. Different workspaces stay isolated by default. |
| Does it write everything automatically? | No. Durable writes stay governed, and some writes require explicit confirmation. |

</div>

<br/>

### What the workspace-shared memory upgrade changes in practice

You can read the current behavior like this:

- **Same workspace can resume**: `codex`, `claude-code`, and other supported hosts can reconnect to the same project memory inside one workspace.
- **Different workspaces stay isolated**: even if two workspaces point at the same backend root, memory does not bleed across repos.
- **Only related memory comes back**: generic scaffold terms such as `$vibe`, `plan`, or `continuity` are filtered out so recall depends on task-relevant content instead of noisy keywords.
- **Long tasks are easier to continue**: the runtime keeps key decisions, handoff cards, and evidence anchors so a later turn or a new agent can continue from the useful parts.
- **Failure is explicit**: if the workspace broker is unavailable, the runtime fails openly instead of pretending that memory continuity still exists.

### What this system actually remembers

You can think of it as four memory categories rather than one giant "long-term memory":

- **Session memory**
  - Keeps current progress, intermediate results, and temporary state
  - Useful for finishing the work happening right now

- **Project memory**
  - Keeps confirmed project conventions, architecture decisions, and durable working agreements
  - Useful when you come back later and do not want to restate the same background

- **Task-semantic memory**
  - Keeps the relevant fragments of long-running tasks easy to retrieve
  - Useful when the context gets large and earlier details would otherwise disappear

- **Long-term knowledge memory**
  - Keeps durable relations, knowledge links, and information worth retaining across sessions
  - Useful when something should be preserved beyond a single task

<details>
<summary><b>📐 Expand: memory layers, write boundaries, and how the memory skills fit together</b></summary>

<br/>

This part explains three things:

1. which memory category is responsible for which job
2. why several memory-related components exist at the same time
3. which writes are automatic, which require confirmation, and which are optional extensions

### Four memory categories and their primary owners

| Memory Category | Primary Owner | Default Scope | What It Keeps |
|:---|:---:|:---:|:---|
| **Session memory** | `state_store` | Current session | execution progress, temporary state, intermediate results |
| **Project memory** | `Serena` | Current workspace / project | confirmed architecture decisions, conventions, durable project rules |
| **Task-semantic memory** | `ruflo` | Intra-session / long task retrieval | relevant context fragments for long-running tasks |
| **Long-term knowledge memory** | `Cognee` | Controlled cross-session knowledge | entities, relations, and durable knowledge links |

> **Optional extensions**: `mem0` can be used as a personal preference backend, and `Letta` can provide memory-block mapping vocabulary. Neither replaces the canonical memory roles above.

### Why several memory layers coexist

They are not duplicate systems. They cover different responsibilities:

- session memory helps finish the current task
- project memory helps a later session reconnect to the same project
- task-semantic memory helps long tasks recover the right context without replaying everything
- long-term knowledge memory keeps the things worth retaining beyond a single task

If you removed any one of these layers, a different part of the workflow would get worse. Session memory alone cannot survive a later return, and long-term memory alone is too coarse to replace current-task state.

### How the memory skills fit into that model

These skills are not a second, competing memory system. They are common entrypoints or helpers around the layers above:

- `knowledge-steward`
  - Best when a prompt, bug lesson, or insight is worth preserving on purpose
  - Think of it as "store this in the right long-term place"

- `digital-brain`
  - Best when you want a more structured personal knowledge base
  - Think of it as a long-term knowledge organization entrypoint

- `deepagent-memory-fold`
  - Best when a long task is getting too large and needs a clean handoff
  - Think of it as a continuity tool for long-running work

### Write boundaries and governance

The important part is the boundary model, not just the feature names:

- not everything becomes durable memory
- project-level decision writes stay governed, and `Serena` requires confirmation before writing durable project truth
- retrieval returns only bounded, relevant capsules instead of replaying the whole store
- `episodic-memory` stays disabled
- `mem0` is limited to personal preferences rather than project truth or routing authority
- every external backend can be disabled with a kill switch

### If you remember one thing

The goal is not to make AI remember everything about you.
The goal is to resume the right project context, preserve the right task state, and keep durable knowledge in controlled places.

</details>

See [workspace memory plane design](./docs/design/workspace-memory-plane.md) for the technical contract and [quantitative Codex memory simulation](./tests/runtime_neutral/test_codex_memory_user_simulation.py) for the benchmark coverage.


---


## ✦ Full Capability Map: Your All-in-One Workbench

_This section is not a full inventory of skill IDs. It is a practical map of the kinds of work VibeSkills can cover._

_If you only want to judge whether VibeSkills fits your task, the table below is the fastest way to read it._

<br/>

<div align="center">

| Work Area | What It Helps With | Representative Engines |
|:---|:---|:---|
| **💡 Requirements, Planning & Product Work** | Clarify vague ideas, write specs, and break work into executable plans and tasks | `brainstorming`, `writing-plans`, `speckit-specify` |
| **🏗️ Engineering, Architecture & Governed Execution** | Design systems, implement changes, and coordinate multi-step governed workflows | `aios-architect`, `autonomous-builder`, `vibe` |
| **🔧 Debugging, Testing & Quality Control** | Investigate failures, add tests, review code, and verify changes before completion | `systematic-debugging`, `verification-before-completion`, `code-review` |
| **📊 Data Analysis & Statistical Modeling** | Clean data, run statistical analysis, explore patterns, and explain results | `statistical-analysis`, `performing-regression-analysis`, `data-exploration-visualization` |
| **🤖 Machine Learning & AI Engineering** | Train, evaluate, explain, and iterate on model-driven workflows | `senior-ml-engineer`, `training-machine-learning-models`, `evaluating-machine-learning-models` |
| **🔬 Research, Literature & Life Sciences** | Review papers, support scientific workflows, and handle bioinformatics-heavy tasks | `literature-review`, `research-lookup`, `scanpy` |
| **📐 Scientific Computing & Mathematical Modeling** | Handle symbolic math, probabilistic modeling, simulation, and optimization | `sympy`, `pymc-bayesian-modeling`, `pymoo` |
| **🎨 Documentation, Visualization & Output** | Turn work into readable docs, charts, figures, slides, and other deliverables | `docs-write`, `plotly`, `scientific-visualization` |
| **🔌 External Integrations, Automation & Delivery** | Work with browsers, web content, external services, CI/CD, and deployment surfaces | `playwright`, `scrapling`, `aios-devops` |

</div>

<br/>

<details>
<summary><b>👉 Expand if needed: detailed categories, usage scenarios, and why similar skills coexist</b></summary>

<br/>

This section explains the full coverage in plain language.
It is meant to answer three practical questions:

1. When would this category be used?
2. Why do several similar skills exist at the same time?
3. Which entries are the representative starting points?

The names below are representative, not a full inventory dump. The point of this section is to explain roles and boundaries, not to turn the README into a warehouse list.

---

### 🧠 Requirements, Planning & Product Management

**When this gets used**: when the task is still fuzzy and the first job is to decide what problem is actually being solved before anyone starts coding.

**Why similar skills coexist**: they handle different stages of the same path. One clarifies the ask, another writes the spec, another turns that spec into a plan, and another breaks the plan into tasks.

**How you usually meet them**: early in a project, before a large change, or whenever a request is too vague to execute safely.

**Representative entries**: `brainstorming`, `speckit-clarify`, `writing-plans`, `speckit-specify`

---

### 🛠️ Software Engineering & Architecture

**When this gets used**: when the problem is clear enough to design system boundaries, make code changes, or coordinate a multi-step implementation.

**Why similar skills coexist**: some focus on architecture, some on implementation, and some on governed execution across several steps or agents. They are adjacent, but they are not doing the same job.

**How you usually meet them**: after planning is done, when a change touches several files, several layers, or several execution phases.

**Representative entries**: `aios-architect`, `architecture-patterns`, `autonomous-builder`, `vibe`

---

### 🔧 Debugging, Testing & Quality Assurance

**When this gets used**: when something is broken, risky, hard to trust, or ready for review.

**Why similar skills coexist**: debugging, testing, review, and final verification are separate actions. A quick bug-fix entrypoint is not the same thing as a disciplined debugging workflow, and neither replaces review or regression checks.

**How you usually meet them**: after a failure, before a PR, or whenever a change needs evidence instead of guesswork.

**Representative entries**: `systematic-debugging`, `error-resolver`, `verification-before-completion`, `code-review`

---

### 📊 Data Analysis & Statistical Modeling

**When this gets used**: when the main task is to understand data, clean it, test assumptions, or explain findings.

**Why similar skills coexist**: some are for cleaning and exploration, some for statistical testing, some for visualization, and some for specific data types or pipelines. They support one another, rather than duplicating one another.

**How you usually meet them**: before modeling, during experiment analysis, or anytime the question is "what does this data actually say?"

**Representative entries**: `statistical-analysis`, `performing-regression-analysis`, `detecting-data-anomalies`, `data-exploration-visualization`

---

### 🤖 Machine Learning & AI Engineering

**When this gets used**: when the task is no longer just data understanding, but model building, evaluation, iteration, and explanation.

**Why similar skills coexist**: training, evaluation, explainability, and experiment tracking are different parts of a model workflow. A model-training skill should not be expected to cover data analysis, and an explainability skill should not be expected to replace training infrastructure.

**How you usually meet them**: after data prep is done, when you need to train something, compare results, or understand why a model behaves a certain way.

**Representative entries**: `senior-ml-engineer`, `training-machine-learning-models`, `evaluating-machine-learning-models`, `explaining-machine-learning-models`

---

### 🧬 Research, Literature & Life Sciences

**When this gets used**: when the work itself is research-heavy, especially in literature review, scientific support, life sciences, or bioinformatics.

**Why similar skills coexist**: research workflows are naturally multi-step. One skill helps find papers, another structures evidence, another handles scientific analysis, and another focuses on life-science-specific toolchains.

**How you usually meet them**: when the request is about papers, experiments, scientific evidence, single-cell workflows, genomics, or drug-related analysis.

**Representative entries**: `literature-review`, `research-lookup`, `biopython`, `scanpy`

---

### 🔬 Scientific Computing & Mathematical Logic

**When this gets used**: when the hard part of the task is mathematical reasoning, symbolic work, formal modeling, simulation, or optimization.

**Why similar skills coexist**: some focus on symbolic derivation, some on probabilistic models, some on simulation, and some on optimization or formal logic. They may sit near each other, but they solve different kinds of mathematical work.

**How you usually meet them**: in research-heavy tasks, quantitative modeling, or workflows where natural-language reasoning is not precise enough.

**Representative entries**: `sympy`, `pymc-bayesian-modeling`, `pymoo`, `qiskit`

---

### 🎨 Multimedia, Visualization & Documentation

**When this gets used**: when the job is to turn work into something another person can read, present, review, or publish.

**Why similar skills coexist**: a chart generator, a documentation writer, a slide tool, and an image tool are all output layers, but they serve different formats and audiences. They belong in the same family because they are delivery surfaces, not because they are interchangeable.

**How you usually meet them**: near the end of a workflow, once results need to become reports, figures, slides, diagrams, or polished documentation.

**Representative entries**: `docs-write`, `plotly`, `scientific-visualization`, `generate-image`

---

### 🔌 External Integrations, Automation & Deployment

**When this gets used**: when the task depends on browsers, web content, design surfaces, external services, CI, or deployment.

**Why similar skills coexist**: browser interaction, content extraction, external service adapters, and deployment automation are related, but they solve different surface-level problems. `playwright` and `scrapling`, for example, both touch the web, but one is better for browser behavior and the other for fetching or extracting content efficiently.

**How you usually meet them**: when the work cannot stay inside the model alone and needs to touch the outside world.

**Representative entries**: `playwright`, `scrapling`, `mcp-integration`, `aios-devops`

---

Taken together, these categories are meant to cover different task types, different workflow stages, and different output surfaces. Similar skills usually coexist for predictable reasons: stage differences, domain specialization, host adaptation, or format-specific delivery.

</details>

<br/>

---


## 📊 Why is it powerful?

_Now for the numbers. This isn't a demo project — it's a running system._

The runtime core behind **VibeSkills** is **VCO**. This is not a single-point tool or a "code completion" script — it is a **super-capability network** that has been deeply integrated and governed:

<br/>

<div align="center">

|                              🧩 Skill Modules                               |                            🌍 Ecosystem                            |                               ⚖️ Governance Rules                                |
| :---------------------------------------------------------------------: | :---------------------------------------------------------------: | :----------------------------------------------------------------------: |
| <h2>340+</h2>Directly callable Skills<br/>covering the full chain from requirements to delivery | <h2>19+</h2>Absorbed high-value upstream<br/>open-source projects and best practices | <h2>129</h2>Policy rules and contracts<br/>ensuring stable, traceable, divergence-free execution |

</div>

<br/>

---


## ⚙️ Installation & Skills Management

You do not need to learn the whole architecture before you install VibeSkills.

### Default install path

1. Decide which app you are installing into: `codex`, `claude-code`, `cursor`, `windsurf`, `openclaw`, or `opencode`
2. If this is your first install and you have no special constraint, choose `install + full`
3. Open the main install guide:
   [Prompt-based install (recommended)](https://github.com/foryourhealth111-pixel/Vibe-Skills/blob/main/docs/install/one-click-install-release-copy.en.md)
4. Copy the prompt that matches your app and version, then paste it into that AI app
5. Finish the install, then continue with [Getting Started](#-getting-started)

### `full` or `minimal`?

- Choose `full` if you want the recommended setup and the simplest default path
- Choose `minimal` only if you deliberately want the smaller framework-only install

### When should you open the other install docs?

- If you are not sure which host path matches your app, start with the [cold-start host matrix](https://github.com/foryourhealth111-pixel/Vibe-Skills/blob/main/docs/cold-start-install-paths.en.md)
- If you want the longer step-by-step command path, use the [multi-host command reference](https://github.com/foryourhealth111-pixel/Vibe-Skills/blob/main/docs/install/recommended-full-path.en.md)
- If you need host-specific notes for OpenClaw or OpenCode, open the [OpenClaw host guide](https://github.com/foryourhealth111-pixel/Vibe-Skills/blob/main/docs/install/openclaw-path.en.md) or the [OpenCode host guide](https://github.com/foryourhealth111-pixel/Vibe-Skills/blob/main/docs/install/opencode-path.en.md)
- If you need an offline or manual copy path, open the [manual install guide](https://github.com/foryourhealth111-pixel/Vibe-Skills/blob/main/docs/install/manual-copy-install.en.md)

<details>
<summary><b>🔧 Advanced install details</b></summary>

Only read this part if you need manual configuration, troubleshooting, or advanced customization.

**If a guide asks you to edit something manually, these are the real file paths**

- Codex: `~/.codex/settings.json`
- Claude Code: `~/.claude/settings.json`
- Cursor: `~/.cursor/settings.json`
- OpenCode: `~/.config/opencode/opencode.json`
- Windsurf / OpenClaw sidecar state: `<target-root>/.vibeskills/host-settings.json`

**What stays visible after install**

- public runtime entry: `<target-root>/skills/vibe`
- internal bundled corpus: `<target-root>/skills/vibe/bundled/skills/*`
- compatibility helper files: only when a host explicitly needs them

The `.vibeskills` folders are split on purpose:

- host-sidecar: `<target-root>/.vibeskills/host-settings.json`, `host-closure.json`, `install-ledger.json`, `bin/*`
- workspace-sidecar: `<workspace-root>/.vibeskills/project.json`, `.vibeskills/docs/requirements/*`, `.vibeskills/docs/plans/*`, `.vibeskills/outputs/runtime/vibe-sessions/*`

**What has been verified after install**

| Host | Verified areas after install |
|:---|:---|
| `codex` | planning, debug, governed execution, memory continuity |
| `claude-code` | planning, debug, governed execution, memory continuity |
| `openclaw` | planning, debug, governed execution, memory continuity |
| `opencode` | planning, debug, governed execution, memory continuity |

These checks confirm that the installed runtime still controls routing, still writes its governance and cleanup records, and still preserves memory continuity. They do not mean that every host-specific invocation surface was exercised in the exact same way.

**Uninstall and custom skills**

- uninstall paths: `uninstall.ps1 -HostId <host>` and `uninstall.sh --host <host>`
- uninstall governance notes: [`docs/uninstall-governance.md`](https://github.com/foryourhealth111-pixel/Vibe-Skills/blob/main/docs/uninstall-governance.md)
- custom skill onboarding: [custom workflow & skill onboarding guide](https://github.com/foryourhealth111-pixel/Vibe-Skills/blob/main/docs/install/custom-workflow-onboarding.en.md)

</details>

## 📦 Standing on the Shoulders of Giants

_These capabilities were not built in isolation. VibeSkills draws on existing open-source projects, patterns, and tools, then adapts them into one governed runtime._

VibeSkills does not claim to replace or fully reproduce every upstream project listed below. The practical goal is narrower: reuse proven ideas where they fit, connect them through one runtime and governance layer, and make them easier to activate together in day-to-day work.

> 🙏 **Acknowledgements**
>
> This project references, adapts, or integrates ideas, workflows, or tooling from projects such as:
>
> `superpower` · `claude-scientific-skills` · `get-shit-done` · `aios-core` · `OpenSpec` · `ralph-claude-code` · `SuperClaude_Framework` · `spec-kit` · `Agent-S` · `mem0` · `scrapling` · `claude-flow` · `serena` · `everything-claude-code` · `DeepAgent` and more
>
> _We try to attribute upstream work carefully. If we missed a source or described a dependency inaccurately, please open an Issue and we will correct it._

<br/>

---


## 🚀 Getting Started

_If VibeSkills is already installed, start with one invocation._

> ⚠️ **Invocation note**: VibeSkills uses a **Skills-format runtime**. Invoke it through your host's Skills entrypoint, not as a standalone CLI program.

<br/>

<div align="center">

| Host Environment | Invocation | Example |
|:---:|:---:|:---|
| **Claude Code** | `/vibe` | `Plan this task /vibe` |
| **Codex** | `$vibe` | `Plan this task $vibe` |
| **OpenCode** | `/vibe` | `Plan this task with vibe.` |
| **OpenClaw** | Skills entry | Refer to the host docs |
| **Cursor / Windsurf** | Skills entry | Refer to each platform's Skills docs |

</div>

<br/>

- First try a small request such as planning, clarifying, or breaking down a task.
- If you want later turns to stay inside the governed workflow, append `$vibe` or `/vibe` to each message.
- If VibeSkills is not installed yet, start with [Prompt-based install (recommended)](https://github.com/foryourhealth111-pixel/Vibe-Skills/blob/main/docs/install/one-click-install-release-copy.en.md).

> MCP note: `$vibe` or `/vibe` only enters the governed runtime. It is **not MCP completion**, and it does not by itself prove that MCP is installed in the host's native MCP surface.

**Public host status**: `codex` and `claude-code` are the clearest install-and-use paths today. `cursor`, `windsurf`, `openclaw`, and `opencode` are available too, but some of those paths are still preview-oriented or host-specific.

<br/>

---

<details>
<summary><b>📚 Documentation & Installation Guides (click to expand)</b></summary>

<br/>

**Start here**

- ⚡️ [Prompt-based install (recommended)](https://github.com/foryourhealth111-pixel/Vibe-Skills/blob/main/docs/install/one-click-install-release-copy.en.md)
- 📖 [System architecture & philosophy](https://github.com/foryourhealth111-pixel/Vibe-Skills/blob/main/docs/quick-start.en.md)

**Open only if needed**

- 🧩 [Custom workflow onboarding](https://github.com/foryourhealth111-pixel/Vibe-Skills/blob/main/docs/install/custom-workflow-onboarding.en.md)
- 📄 [OpenClaw host notes](https://github.com/foryourhealth111-pixel/Vibe-Skills/blob/main/docs/install/openclaw-path.en.md)
- 📄 [OpenCode host notes](https://github.com/foryourhealth111-pixel/Vibe-Skills/blob/main/docs/install/opencode-path.en.md)
- 📁 [Manual copy install (offline)](https://github.com/foryourhealth111-pixel/Vibe-Skills/blob/main/docs/install/manual-copy-install.en.md)
- 🛠 [Advanced install command reference](https://github.com/foryourhealth111-pixel/Vibe-Skills/blob/main/docs/install/recommended-full-path.en.md)
- 🧊 [Cold start & other environments](https://github.com/foryourhealth111-pixel/Vibe-Skills/blob/main/docs/cold-start-install-paths.en.md)

</details>

<br/>

<div align="center">

### 🤝 Join the Community · Build Together

Give it a try! If you have questions, ideas, or suggestions, feel free to open an issue — I'll take every piece of feedback seriously and make improvements.

<br/>

**This project is fully open source. All contributions are welcome!**

Whether it's fixing bugs, improving performance, adding features, or improving documentation — every PR is deeply appreciated.

```
Fork → Modify → Pull Request → Merge ✅
```

<br/>

> ⭐ If this project helps you, a **Star** is the greatest support you can give!
> Its underlying philosophy has been well-received; however, the current codebase carries some technical debt, and certain features still require refinement. We welcome you to point out any such issues in the Issues section.
> Your support is the enriched uranium that fuels this nuclear-powered donkey 🫏

<br/>

Thank you to the **LinuxDo** community for your support!

[![LinuxDo](https://img.shields.io/badge/Community-LinuxDo-blue?style=for-the-badge)](https://linux.do/)

Tech discussions, AI frontiers, AI experience sharing — all at Linuxdo!

</div>

<br/>

---

## Star History
<div align="center">
<a href="https://www.star-history.com/?repos=foryourhealth111-pixel%2FVibe-Skills&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/image?repos=foryourhealth111-pixel/Vibe-Skills&type=date&theme=dark&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/image?repos=foryourhealth111-pixel/Vibe-Skills&type=date&legend=top-left" />
   <img alt="Star History Chart" src="https://api.star-history.com/image?repos=foryourhealth111-pixel/Vibe-Skills&type=date&legend=top-left" />
 </picture>
</a>

---

<div align="center">
  <p><i>Transform the parts of real work most prone to going off the rails into a system that is more callable, more governable, and more maintainable over time.</i></p>
  <br/>
  <sub>Made with ❤️ &nbsp;·&nbsp; <a href="https://github.com/foryourhealth111-pixel/Vibe-Skills">GitHub</a> &nbsp;·&nbsp; <a href="./README.zh.md">中文</a></sub>
</div>
