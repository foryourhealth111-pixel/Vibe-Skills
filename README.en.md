[中文](./README.md)

# VibeSkills

> 🐙 An integrated AI capability stack that brings upstream projects, hundreds of skills, MCP entry points, plugin surfaces, and governance rules into one runtime.

`VibeSkills` is the public-facing name of the project. `VCO` is the governed runtime behind it. This is not a single-purpose utility repo, and it is not just a bundle of prompts that happens to know how to write code. It is an already-integrated capability system: `340` directly callable skills and capability modules, `19` absorbed upstream projects and practice sources, and `129` config-backed policies, contracts, and rules that keep skills, MCP, plugins, workflows, verification, and cleanup inside one governable execution surface.

<p align="center">
  <sub>🧠 Planning · 🛠️ Engineering · 🤖 AI · 🔬 Research · 🧬 Life Sciences · 🎨 Visualization · 🎬 Media</sub>
</p>

## ✦ What This Repository Can Help You Do From Day One

If you look at these `340` skills through the lens of real work instead of repository folders, `VibeSkills` already covers a full capability chain: requirement discovery, solution design, implementation, testing, documentation, data analysis, research support, life-science workflows, and media generation. The table below is organized from a user-facing perspective rather than an internal file-structure perspective.

| Capability Area | What It Can Cover In Practice | Representative Skills / Systems | Typical Outputs |
| --- | --- | --- | --- |
| Requirement discovery and problem framing | Turn vague ideas, spoken requests, or scattered goals into a defined problem with boundaries, priorities, risks, constraints, and acceptance criteria | `brainstorming`, `create-plan`, `speckit-clarify`, `aios-analyst`, `aios-pm` | Requirement briefs, clarified scope, goal statements, acceptance criteria |
| Product planning and task breakdown | Convert an idea into specs, plans, milestones, dependencies, execution order, and structured task lists | `writing-plans`, `speckit-specify`, `speckit-plan`, `speckit-tasks`, `aios-po`, `aios-sm`, `OpenSpec`-style flows | PRDs, specs, implementation plans, task lists, delivery roadmaps |
| Architecture design and technical choice | Design application structure across frontend, backend, APIs, data, deployment, and system boundaries, then compare trade-offs under real constraints | `aios-architect`, `architecture-patterns`, `context-fundamentals`, `aios-master` | Architecture proposals, module boundaries, API shapes, stack decisions |
| Software engineering and code implementation | Build features, refactor existing systems, scaffold projects, wire integrations, and land multi-file changes end to end | `aios-dev`, `autonomous-builder`, `aios-master`, `speckit-implement` | Working code, refactors, modules, scaffolds, integrated features |
| Debugging, repair, and refactoring | Diagnose failures, isolate root causes, repair broken behavior, clean AI-generated code bloat, and restore maintainability | `error-resolver`, `debugging-strategies`, `systematic-debugging`, `deslop`, `build-error-resolver` | Fixes, root-cause notes, refactoring passes, replayable repair steps |
| Testing strategy and quality assurance | Design test strategy, create regression checks, run quality gates, and verify completion with evidence rather than guesswork | `tdd-guide`, `test-driven-development`, `aios-qa`, `code-review`, `code-reviewer`, `verification-before-completion`, `property-based-testing`, `hypothesis-testing` | Test cases, verification evidence, QA decisions, acceptance checklists |
| Code review and engineering standards | Review code for risk, maintainability, performance, and security, then turn findings into concrete follow-up work | `reviewing-code`, `code-review-excellence`, `security-reviewer`, `receiving-code-review`, `requesting-code-review` | Review findings, risk lists, review notes, change recommendations |
| GitHub operations, release, and DevOps | Manage issues and PRs, repair CI, address review comments, handle releases, and run deployment flows | `aios-devops`, `gh-fix-ci`, `gh-address-comments`, `github_*`, `workflow_*`, `vercel-deploy`, `netlify-deploy`, `yeet` | Issues, PRs, CI fixes, releases, deployment outcomes |
| Governed workflows and multi-agent collaboration | Freeze requirements before execution, orchestrate steps, assign work, retain stage evidence, and enforce cleanup and verification | `vibe`, `swarm_*`, `task_*`, `agent_*`, `hive-mind-advanced`, `local-vco-roles`, `superclaude-framework-compat` | Governed execution logs, task states, coordination records, cleanup receipts |
| Skill activation and capability routing | Solve the “lots of capability, low activation” problem by routing the right skill, MCP surface, plugin, or rule into the right step of work | `vibe`, `deepagent-toolchain-plan`, `hooks_route`, `hooks_worker-detect`, `semantic-router`, `VCO` routing governance | Routing decisions, activation chains, auto-dispatch results, capability hits |
| MCP integration and external systems | Bring browsers, design files, search, scraping, third-party services, plugins, and external context into one runtime | `mcp-integration`, `playwright`, `scrapling`, `browser_*`, `figma`, `figma-implement-design`, `transfer_*` | MCP configs, browser automations, extracted results, integration flows |
| Documentation and knowledge capture | Write READMEs, technical docs, process guides, diagrams, operating notes, knowledge entries, and longer reports | `docs-write`, `docs-review`, `markdown-mermaid-writing`, `knowledge-steward`, `writing-docs`, `scientific-reporting` | READMEs, docs, diagrams, reports, reusable knowledge assets |
| Office documents and file workflows | Work with Word, PDF, Excel, CSV, markdown conversion, comment replies, formatting retention, and document organization | `docx`, `pdf`, `xlsx`, `spreadsheet`, `markitdown`, `excel-analysis`, `file-organizer`, `docx-comment-reply` | Revised docs, spreadsheet analysis, converted files, organized assets |
| Data analysis and statistical modeling | Run EDA, regression, hypothesis tests, visualization, data cleaning, metric analysis, and statistical reporting | `data-exploration-visualization`, `statistical-analysis`, `statsmodels`, `scikit-learn`, `polars`, `dask`, `xan` | Analysis reports, statistical outputs, modeling baselines, data workflows |
| Machine learning and AI engineering | Cover the full AI engineering loop, from data preparation and feature work to training, evaluation, explainability, retrieval, and experiment tracking | `senior-ml-engineer`, `training-machine-learning-models`, `evaluating-machine-learning-models`, `shap`, `embedding-strategies`, `similarity-search-patterns`, `weights-and-biases` | Model plans, metrics, explanations, retrieval systems, experiment logs |
| Visualization and presentation | Generate charts, interactive visualizations, scientific figures, presentations, web-facing showcases, and expressive data communication | `plotly`, `matplotlib`, `seaborn`, `datavis`, `creating-data-visualizations`, `scientific-slides`, `paper-2-web`, `infographics` | Charts, dashboards, slides, visual pages, presentation assets |
| Research search and academic writing | Cover literature search, evidence synthesis, citation management, paper drafting, submission support, and reviewer-response workflows | `research-lookup`, `literature-review`, `citation-management`, `scientific-writing`, `scholarly-publishing`, `peer-review`, `submission-checklist` | Literature reviews, citation libraries, draft papers, submission packages, rebuttals |
| Life sciences and biomedicine | Go beyond generic “research support” into bioinformatics, single-cell workflows, protein work, drug discovery, clinical data, scientific databases, and lab integrations | `biopython`, `scanpy`, `scvi-tools`, `alphafold-database`, `uniprot-database`, `clinicaltrials-database`, `drugbank-database`, `benchling-integration`, `opentargets-database` | Bioinformatics workflows, database outputs, experiment support, scientific analysis |
| Mathematics, optimization, and scientific computing | Perform symbolic derivations, Bayesian modeling, optimization, simulation, quantum workflows, and scientific computation | `math-tools`, `sympy`, `pymc-bayesian-modeling`, `pymoo`, `fluidsim`, `qiskit`, `cirq`, `qutip` | Derivations, scientific code, optimization plans, simulation outputs |
| Images, audio, video, and media production | Generate images, infographics, speech, subtitles, video assets, and multimedia materials for delivery and distribution | `generate-image`, `imagegen`, `speech`, `transcribe`, `video-studio`, `infographics` | Images, audio files, subtitles, finished videos, media packs |

This table does not mechanically dump all `340` skills. It reorganizes the capability surface into the kinds of work people actually want AI to help with. In other words, this repository is not only about coding. It already covers the workflow from requirement definition to delivery, from engineering to research, from automation to documentation, and from data work to life-science operations.

## 🧭 If You Break These 20 Domains Down Further

The top-level matrix is useful for a fast scan. But if you keep going one level deeper, you start to see that the repository does not just cover a handful of broad labels. It covers a more detailed set of working surfaces. The grouped tables below expand the 20 domains into finer-grained subdomains.

### 🧩 Planning, Architecture, And Delivery

| Capability Area | Finer-Grained Subdomains | What That Means In Practice |
| --- | --- | --- |
| Requirement discovery and problem framing | Requirement interviews, problem definition, boundary detection, constraint intake, success criteria, risk anticipation | Turn “I think I want to build something like this” into an executable problem statement with goals, non-goals, boundaries, and evaluation criteria |
| Product planning and task breakdown | Specs, plans, tasks, milestones, dependencies, prioritization, delivery order | Break a large idea into something that can be scheduled, tracked, validated, and shipped incrementally instead of pushed into a black box |
| Architecture design and technical choice | Frontend structure, backend boundaries, API design, data layer, deployment layer, pattern choice, technical comparison | Decide what should be modular, what should be coupled, what should be constrained, and what should be left simple before implementation debt compounds |
| Software engineering and code implementation | Feature delivery, scaffolding, multi-file edits, module integration, engineering hardening, automation | Carry work from the planning layer into actual runnable implementation instead of leaving it as design prose |
| Debugging, repair, and refactoring | Error diagnosis, root-cause isolation, behavior repair, slop cleanup, structural refactoring, maintainability recovery | Fix what is broken while also addressing why the system became brittle, hard to reason about, or easy for AI to damage further |
| Testing strategy and quality assurance | Unit tests, property-based tests, regression checks, acceptance validation, quality gates, completion verification | Move from “it seems okay now” to “there is evidence that it works and did not silently break something else” |
| Code review and engineering standards | Review, risk checks, maintainability assessment, security review, performance review, change recommendations | Push code from merely usable toward something a team can realistically keep evolving |

### 🔗 Governance, Routing, And External Surfaces

| Capability Area | Finer-Grained Subdomains | What That Means In Practice |
| --- | --- | --- |
| GitHub operations, release, and DevOps | Issue and PR workflows, CI repair, review-comment handling, release branches, deployment records, go-live steps | Cover the whole collaboration and release path instead of stopping at local code changes |
| Governed workflows and multi-agent collaboration | Requirement freeze, staged execution, task assignment, proof artifacts, cleanup, multi-agent coordination | Keep complex work inside a traceable and verifiable operating frame rather than letting the model improvise unchecked |
| Skill activation and capability routing | Rule-based routing, semantic routing, staged triggers, capability orchestration, dormant-skill wake-up, execution-surface matching | Address the core usability problem of large skill repositories: the capability exists, but it does not reliably enter the actual workflow |
| MCP integration and external systems | Browser automation, web extraction, design-to-code, third-party service hooks, plugin entry points, external context intake | Pull websites, services, designs, automation tools, and remote context into one runtime instead of forcing manual tool switching |
| Documentation and knowledge capture | READMEs, technical guides, operating manuals, standards docs, Mermaid diagrams, knowledge entries, reports | Make outcomes durable and team-usable instead of leaving them trapped in chat history |
| Office documents and file workflows | Word, PDF, Excel, CSV, markdown conversion, threaded comment replies, formatting retention, document organization | Cover the many operational document tasks that consume real time but are often ignored in “AI engineering” repos |

### 🔬 Data, AI, Research, And Professional Domains

| Capability Area | Finer-Grained Subdomains | What That Means In Practice |
| --- | --- | --- |
| Data analysis and statistical modeling | EDA, regression, hypothesis testing, metric systems, cleaning, transformation, distribution analysis, reporting | Turn raw data into interpretable analysis rather than just producing a few charts |
| Machine learning and AI engineering | Model training, evaluation, feature work, explainability, embeddings, RAG, experiment tracking, governed ML workflows | This is not just “the repo can train models.” It covers the real engineering loop around training, evaluation, interpretation, retrieval, and experiment discipline |
| Research search and academic writing | Literature search, review writing, citation management, paper drafting, submission prep, rebuttal writing, academic standards | The strength here is the workflow chain, not a single tool. It can support work from search through review, manuscript drafting, and submission support |
| Life sciences and biomedicine | Bioinformatics, single-cell analysis, protein structure, drug discovery, clinical-trial data, research databases, lab-platform integration | This is one of the clearest differentiators in the repository because it goes into domain-specific scientific work rather than stopping at generic AI support |
| Mathematics, optimization, and scientific computing | Symbolic derivation, Bayesian modeling, multi-objective optimization, simulation, quantum computing, scientific modeling | Useful for exact reasoning, formal derivation, and advanced scientific workflows that go beyond ordinary software tasks |

### 🎨 Visualization, Presentation, And Media Output

| Capability Area | Finer-Grained Subdomains | What That Means In Practice |
| --- | --- | --- |
| Visualization and presentation | Chart generation, interactive visualization, scientific figures, slide decks, web presentation, information design | Turn analysis or project outputs into clear, presentable, and shareable visual artifacts |
| Images, audio, video, and media production | Image generation, infographics, speech synthesis, subtitle generation, video production, media packaging | Support the full path from static visual assets to audio and video deliverables for demos, education, and distribution |

If you connect these subdomains back into a single flow, the repository is really covering a complete working path: understand the request, create the plan, shape the architecture, implement, verify, collaborate, publish, then extend into documentation, data work, AI engineering, research workflows, life sciences, visualization, and media. That breadth is exactly why routing, governance, and standardization matter here. Skill count alone is not enough.

The three areas that stand out most sharply are AI engineering, research writing, and life sciences. Many repositories say they “support machine learning” or “support research,” but often only in scattered tool fragments. The difference here is that these areas are already organized into workflow chains. The system does not just call a few models, search a few papers, or connect to a few databases. It can place training, evaluation, retrieval, academic writing, biomedical analysis, and lab-platform integration inside one governed runtime. That is a real differentiator.

## 📦 What Is Already Integrated

This repository did not attempt to invent everything from scratch. It continuously absorbs mature methods, structures, and workflows that have already proven useful elsewhere, then governs them inside one system.

| Resource Layer | Current Depth | Why It Matters |
| --- | --- | --- |
| Skills and capability modules | `340` directly callable skills and capability modules | Cover the full work chain from requirement discovery, planning, and coding to verification, documentation, research, and media generation |
| MCP, plugins, and browser entry points | Multiple external-tool and context surfaces | Bring web services, designs, documents, search, and automation flows into the same runtime |
| Upstream projects and practice sources | `19` high-value projects and working traditions | Absorb proven strengths into one system instead of forcing people to manually assemble an ecosystem |
| Governance rules and contracts | `129` config-backed policies, contracts, and rules | Constrain clarification, planning, execution, verification, traceability, cleanup, and rollback so the system remains maintainable over time |

The project continuously integrates and governs strengths from `superpower`, `claude-scientific-skills`, `get-shit-done`, `aios-core`, `OpenSpec`, `ralph-claude-code`, and `SuperClaude_Framework`, pulling their advantages in prompt organization, skill accumulation, plan-driven execution, governed workflows, scientific support, and engineering discipline into one operating surface.

That is one of the clearest differences between `VibeSkills` and an ordinary prompt collection or skills index. What you are looking at is not a static directory. It is an integrated capability network that can be routed, governed, verified, and maintained.

<p align="center">
  <img src="./docs/assets/Gemini_Generated_Image_75f8n575f8n575f8.svg" alt="Original Gemini SVG provided by the author" width="100%" />
</p>

## ✨ Why It Feels Different Right Away

Most skill repositories mainly answer one question: what is available here?

`VibeSkills` is more concerned with a different set of questions:

- what should be called now, instead of forcing you to manually search the ecosystem
- what should happen first, instead of letting the model sprint straight into execution
- which capabilities can be safely combined, and where boundaries need to stay explicit
- how outcomes get verified, retained, and kept out of long-term black-box drift

It is not about stacking more capability.
It is about integrating activation, governance, verification, and review into a system that can hold up under real use.

## ⚠️ The Pain Points It Is Trying To Solve

If you already use AI heavily, you have probably seen some version of these failures:

- there are too many skills, but no clear answer for which one fits the current moment
- skill activation rates are low, so capability exists in the repo but rarely gets triggered, remembered, or connected to the actual workflow
- projects, plugins, and workflows overlap with one another and then conflict with one another
- models start executing before the task is actually clear
- work ends without verification, evidence, or rollback surfaces
- the workflow gets more powerful over time, but also harder to understand

`VibeSkills` does not pretend these problems disappear on their own.
Its value is that it treats them as real design problems.

The `VCO` ecosystem is also trying to solve a very practical issue: not that there are too few skills, but that too many capabilities stay dormant and their real activation rate stays low. Through routing decisions, MCP and plugin entry points, workflow orchestration, and governance rules, the system tries to pull the right capability into the right stage of work instead of leaving it asleep in the repository.

## ⚙️ How It Works

You can think about it as three layers.

### 1. 🧠 Smart routing

In the right situations, you should not need to remember the exact skill name first.

`VibeSkills` combines rule-based routing and AI-assisted routing so the right capability is more likely to be activated in the right context. Part of what the `VCO` ecosystem is trying to solve is low skill activation rate, so more capabilities can enter the execution surface at the right moment instead of remaining technically present but practically unused.

### 2. 🧭 Governed workflows

This is not only about calling tools.
It is also about how work gets done in a stable way.

That is why the system tries to keep requirement clarification, confirmation, execution, verification, review, and traceability inside one working flow instead of letting the model sprint into a black box.

### 3. 🧩 Integrated capabilities

This is not just a pile of skills.

It also includes plugins, project integrations, workflow design, AI norms, safety boundaries, maintenance lessons, and the mistakes I have already made and do not want to repeat. `VCO` is the runtime layer that keeps those capabilities organized instead of leaving them scattered in unrelated places.

## 👥 Who It Is For

`VibeSkills` is mainly for:

- ordinary people who want AI to help more reliably
- heavy AI, agent, and automation users
- individuals or small teams who want more disciplined AI workflows
- anyone tired of a skill ecosystem that is rich in options but poor in usability

If you only want a single-purpose utility, this repo may be heavier than you need.
If you want AI to become steadier, easier to manage, and more useful over time, it is a much better fit.

## 🚀 Start Here

If you want the shortest path to understanding the system before you install it:

- [`docs/quick-start.en.md`](./docs/quick-start.en.md)
- [`docs/manifesto.en.md`](./docs/manifesto.en.md)

If you are ready to install after that, use the one-step AI-assisted path:

- [`docs/install/one-click-install-release-copy.en.md`](./docs/install/one-click-install-release-copy.en.md)

If you are already a heavier user and want fuller installation detail:

- [`docs/install/recommended-full-path.en.md`](./docs/install/recommended-full-path.en.md)
- [`docs/cold-start-install-paths.en.md`](./docs/cold-start-install-paths.en.md)

## 📐 Project Philosophy

The core idea of `VibeSkills` is standardization. Only when requirement clarification, planning, execution, verification, traceability, and rollback are turned into reusable order does human intent become clearer, model execution become steadier, and long-term maintenance keep technical debt lower.

The project is not trying to make AI look more magical. It is trying to let people focus on describing goals while the remaining work can be carried, verified, and maintained inside a standardized workflow that is more callable, more governable, and more sustainable over time.
