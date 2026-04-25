<div align="right">
  <a href="./README.md">🇬🇧 English</a> &nbsp;|&nbsp; <b>🇨🇳 中文</b>
</div>

<br/>

<div align="center">

<a href="https://github.com/foryourhealth111-pixel/Vibe-Skills">
  <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=700&size=45&pause=1000&color=7B61FF&center=true&vCenter=true&width=600&height=100&lines=Vibe+Skills;Agent+Harness" alt="VibeSkills Typing Logo" />
</a>

<br/>

<img src="./logo.png" width="260px" alt="VibeSkills Logo"/>

<br/><br/>

### 面向 Skills AI Agent 的简单易用工作 harness

#### 安装这个 Skills 包，调用 `vibe`，剩下的重活交给 harness：理解任务、拆分阶段、自动拉起合适的专家 Skills、检查结果，并把关键上下文留给下一次会话。

&nbsp;
*你不需要背技能表，也不需要一步步盯着 AI 该做什么。VibeSkills 想做的事很直接：让用户少操心，让 Agent 更有章法地完成工作。*


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
<a href="https://gitcgr.com/foryourhealth111-pixel/Vibe-Skills">
  <img src="https://gitcgr.com/badge/foryourhealth111-pixel/Vibe-Skills.svg" alt="gitcgr" />
</a>

<br/><br/>

<img src="https://komarev.com/ghpvc/?username=vibe-skills-foryourhealth&label=NODES+ACTIVE&color=0078d7&style=for-the-badge" alt="Visitors">
&nbsp;
<img src="https://img.shields.io/badge/Architecture-VCO_Runtime-orange?style=for-the-badge" alt="Arch">
&nbsp;
<img src="https://img.shields.io/badge/Skills-340%2B-blueviolet?style=for-the-badge" alt="Skills Count">

<br/><br/>

🧠 规划 · 🛠️ 工程 · 🤖 AI · 🔬 科研 · 🎨 创作

<br/>

<a href="https://github.com/foryourhealth111-pixel/Vibe-Skills/blob/main/docs/install/one-click-install-release-copy.md">
  <img src="https://img.shields.io/badge/⚡_立即安装-7B61FF?style=for-the-badge" alt="安装">
</a>
&nbsp;
<a href="https://github.com/foryourhealth111-pixel/Vibe-Skills/blob/main/docs/quick-start.md">
  <img src="https://img.shields.io/badge/📖_快速上手-2d3748?style=for-the-badge" alt="文档">
</a>
&nbsp;
<a href="./README.md">
  <img src="https://img.shields.io/badge/🇬🇧_English-45a1ff?style=for-the-badge" alt="English">
</a>

<br/><br/>

<kbd>安装</kbd> &nbsp;→&nbsp;
<kbd>vibe | vibe-upgrade</kbd> &nbsp;→&nbsp;
<kbd>受管流程</kbd> &nbsp;→&nbsp;
<kbd>阶段 Skills</kbd> &nbsp;→&nbsp;
<kbd>TDD / 验证</kbd> &nbsp;→&nbsp;
<kbd>持续上下文</kbd>

</div>

## 📋 目录

- [为什么与众不同](#-为什么它与众不同)
- [适合你吗](#-适用人群)
- [智能路由](#-智能路由机制340-技能如何协同而不冲突)
- [记忆系统](#-记忆系统让-ai-在同一工作区里持续接上上下文)
- [全景能力地图](#-全景能力地图你的全能工作台)
- [安装与管理](#️-安装与-skills-管理)
- [开始使用](#-开启你的-vibe-体验)


<details>
<summary><b>🔑 初次使用？点击展开关键概念说明</b></summary>

<br/>

| 术语 | 通俗解释 |
|:---|:---|
| **Harness** | 包在 AI Agent 外层的工作流层。它判断下一阶段、调用合适的 Skills、检查结果，并保存有用上下文。 |
| **Skill** | 一个聚焦的专家能力，例如 `tdd-guide`、`code-review`、数据分析、文档处理、科研写作等。 |
| **Vibe / VCO** | 运行这套 harness 的 canonical runtime。公开入口是 `vibe` 和 `vibe-upgrade`。 |
| **自动编排** | 不同阶段自动选择并调用不同 Skills：需求、规划、实现、评审、验证、清理，各司其职。 |
| **TDD / 证据优先交付** | 完成不能只靠模型一句“做好了”，而要有测试、检查、产物证据，或明确的人工复核状态。 |
| **工作区记忆** | 结构化保存需求、计划、决策和证据，让后续会话不用从零开始。 |

</details>

> [!IMPORTANT]
> ### 🎯 核心愿景
>
> VibeSkills 的出发点很简单：Skills 只有被智能 harness 自动编排起来，才真正好用。
>
> 它把受管 harness、专家 Skills、TDD 导向执行、验证规则和工作区记忆封装进一个即插即用的 Skills 包。用户不应该手动记住每个工具、手动选择每个 Skill、手动催促每个阶段、手动盯住每个测试，也不应该在每次新会话里重新搭一遍上下文。
>
> **安装后调用 `vibe`，AI Agent 就获得一套更清晰的工作方式。**
> 因为 VibeSkills 本质上是 Skills 包，所以它易安装、易迁移、能适配多种宿主，也适合很多不同类型的任务。

<br/>

<img width="1376" height="768" alt="Generated Image April 21, 2026 - 8_51PM" src="https://github.com/user-attachments/assets/de9f1d20-3976-40b9-bc7c-37bb308a3591" />


---


## ✨ 为什么它与众不同？

> 大多数 Skills 仓库回答的是：_"我的 AI 能用哪些工具？"_
> **VibeSkills 更关心一个实际问题：_"AI 能不能在合适的时间自动用上这些 Skills，而不是让用户全程指挥？"_**

<sub>适用于 **Claude Code** · **Codex** · **Windsurf** · **OpenClaw** · **OpenCode** · **Cursor** 及所有支持 Skills 协议的 AI 环境，原生兼容 **MCP**。</sub>

<br/>

<div align="center">

| 层次 | 它替用户解决什么 |
|:---|:---|
| **简单入口** | 从 `vibe` 开始，用 `vibe-upgrade` 更新，先不用学一长串 workflow 命令。 |
| **智能 harness** | AI 按「澄清 → 规划 → 执行 → 测试 → 验证 → 保存上下文」推进，而不是直接乱跑。 |
| **自动 Skill 编排** | harness 按任务、阶段和约束选择专家 Skills，并让它们在有边界的职责里工作。 |
| **TDD 与验证纪律** | 任务结果落到测试、检查、证据或明确人工复核状态上，而不是一句“完成了”。 |
| **结构化上下文存储** | 需求、计划、决策、交接信息和证据存到可预期的位置，方便后续会话接上。 |
| **通用 Skills 包** | 核心是即插即用的 Skills bundle，能给支持 Skills 的 AI Agent 带来同一套工作流升级。 |

</div>

<br/>

<div align="center">

| 没有 harness 时 | 使用 VibeSkills 后 |
|:---|:---|
| 用户自己决定下一句提示词、下一个工具、下一步质量检查。 | harness 引导流程，并在关键位置要求确认。 |
| Skills 只是一长串能力列表，AI 可能根本想不起来用。 | Skills 变成按阶段自动调度的专家工人。 |
| “完成”可能只是模型停止输出。 | 交付要绑定测试、检查、产物证据，或明确人工复核状态。 |
| 长任务跨会话后上下文丢失。 | 需求、计划、决策和证据被保存，方便继续。 |
| 每个宿主都要重新设计一套使用方式。 | 核心保持为通用 Skills 包，宿主适配围绕它展开。 |

</div>

<br/>

---


## 👥 适用人群

VibeSkills 适合希望 AI Agent 更容易上手、更泛用、更少手动控制的人。

<details>
<summary>适合你吗？点击展开</summary>

<br/>

<div align="center">

| 人群 | 描述 |
|:---:|:---|
| 🎯 **追求稳定交付的用户** | 希望 AI 先澄清、再规划、再测试验证，而不是直接给一个答案。 |
| ⚡ **重度使用 AI Agent 的人** | 需要一个 harness 来协调大量专家 Skills，不想每一步都自己调度。 |
| 🏢 **想规范 AI 工作流的团队** | 需要可复用的需求、计划、验证和交接产物。 |
| 🧩 **Skill 构建者与集成者** | 希望用易安装、可迁移的 Skills 包作为核心封装，适配多种宿主环境。 |
| 😩 **厌倦手动调工具的人** | 希望系统自动判断哪个阶段该用哪个 Skill。 |

</div>

> _如果你只想要一个孤立小脚本，VibeSkills 可能偏重。但如果你希望 AI Agent 能跨阶段、跨会话承接真实工作，它就是让 Skills 规模化可用、又不难上手的那层基础。_

</details>

<br/>

---


## 🔀 智能路由机制：340+ 技能如何协同而不冲突

核心点其实很简单：Skills 本身不是完整产品。harness 才是把它们组织成工作系统的关键。

`vibe` 负责整个流程：什么时候澄清，什么时候规划，什么时候让专家 Skills 介入，什么时候跑测试或检查，以及什么时候允许声明交付完成。用户只需要一个简单入口，不需要面对一堆选择题。

<div align="center">

| 用户常见担心 | 实际怎么处理 |
|:---|:---|
| “Skills 太多了，我怎么选？” | 不需要你从完整列表里手动挑。harness 会按任务、阶段和约束智能路由。 |
| “相似 Skills 会不会冲突？” | 路由会给它们分配有边界的职责，专项 Skills 只在当前阶段或任务单元里工作。 |
| “多代理会不会乱跑？” | 大任务会先拆成有边界的单元，再明确所有权、验证方式和协调者批准。 |

</div>

### harness 在实际里怎么协同

- **一个受管入口开始**：多数任务从 `vibe` 进入，用户不用手动选择一棵 workflow 树。
- **执行前先冻结意图**：需求和计划会变成稳定产物，而不是散落在聊天记录里。
- **按阶段自动调度专家**：需求、规划、实现、测试、评审、清理，可以各自调用不同 Skills。
- **结果必须落到证据**：TDD、定向检查、产物审阅和交付验收共同约束完成声明。
- **上下文要能延续**：运行时保存足够结构，方便下一个会话或下一个代理继续工作。

---

### 为什么大量专家 Skills 可以共存

- 它们不会一次性全部启动。
- 有些服务不同阶段：澄清、规划、实现、评审、验证。
- 有些服务不同领域：代码、科研、数据、写作、设计、文档、运维。
- 最终掌控工作流的是 harness，而不是某个单独 Skill。

---

### M / L / XL 执行级别

选定主路线之后，运行时还会根据任务复杂度决定执行级别：

<div align="center">

| 级别 | 适用场景 | 特点 |
|:---:|:---|:---|
| **M** | 窄范围执行，边界清楚的小范围工作 | 单代理，省 token，响应快 |
| **L** | 中等复杂任务，需要设计、计划与评审 | 受管的多步骤执行，通常按计划串行推进 |
| **XL** | 适合拆分的大任务，存在彼此独立的工作单元 | 先拆单元，再由协调者按波次调度，可对独立单元并行推进 |

</div>

> 即使到了 XL，也不是“大家各自找技能乱跑”。系统会先定主路线，再把技能分配给有边界的任务单元，整个过程仍由同一个受管协调者控制。

---

<details>
<summary><b>🔍 展开：入口 wrapper、级别覆盖与路由补充说明</b></summary>

<br/>

- 公开可发现入口固定是 `vibe` 和 `vibe-upgrade`。
- `vibe` 是渐进式入口：先在 `requirement_doc` 停止，再在 `xl_plan` 停止，只有在每个边界都得到明确 re-entry 批准后才进入 `phase_cleanup`。
- `vibe-upgrade` 负责受管升级路径。
- `vibe-what-do-i-want`、`vibe-how-do-we-do`、`vibe-do-it` 这类阶段 ID 已禁用为公开宿主入口。它们可以作为运行时连续性元数据保留，但安装器不应把它们物化成宿主可见的 command 或 skill wrapper。
- 公开允许的轻量级别覆盖只有 `--l` 和 `--xl`。像 `vibe-l`、`vibe-xl` 或阶段入口叠加级别的组合别名是故意不支持的。
- 当内部调用 `tdd-guide`、`code-review` 这类专项技能时，它们只负责当前阶段或当前任务单元，不会接管全局协调。
- 在 XL 多代理流程里，子代理可以提出专项技能建议，但最终由协调者确认分配。

</details>

<br/>

---


## 🧠 记忆系统：让 AI 在同一工作区里持续接上上下文

_路由解决的是“该用哪个技能”。记忆解决的是“下次还要不要从头再讲一遍”。_

VibeSkills 的记忆机制，默认解决的是三类实际问题：

- 在同一个工作区里，重新开会话时还能接上已经确认过的项目背景
- 长任务中断后，还能把关键过程和交接信息续上
- 需要保留的决策、handoff 信息和相关证据，不会随着上下文窗口一起丢掉

它不是“什么都自动永久保存”。
默认重点是分层和边界：会话状态、项目约定、任务相关检索，以及受控的长期知识，分别由不同的层负责。

<br/>

<div align="center">

| 用户最关心的问题 | VibeSkills 默认怎么处理 |
|:---|:---|
| 新会话还要不要重新解释项目背景？ | 不用。同一工作区内，会优先接上已经确认过的项目记忆。 |
| 长任务做到一半中断怎么办？ | 关键进度会被折叠成可继续使用的工作记忆、工具记忆和证据记忆。 |
| 会不会把不相关历史全塞回当前上下文？ | 不会。检索只会返回有边界、和当前任务相关的内容。 |
| 不同项目会不会串味？ | 不会。不同工作区默认隔离。 |
| 会不会把所有东西都自动写入长期记忆？ | 不会。持久写入有治理边界，部分写入需要明确确认。 |

</div>

<br/>

### 工作区共享记忆，实际会发生什么

你可以把当前行为直接理解成下面这几条：

- **同一工作区可以续上**：`codex`、`claude-code` 等宿主，只要落在同一个工作区里，就能接上同一套项目记忆。
- **不同工作区默认隔离**：即使两个工作区共用同一个 backend root，记忆也不会跨仓库串过去。
- **只取相关内容**：像 `$vibe`、`plan`、`continuity` 这样的通用脚手架词会先被过滤，真正决定命中的，是和当前任务相关的内容。
- **长任务更容易继续**：运行时会保留关键决策、交接卡片和证据锚点，方便后续会话或新代理继续往下做。
- **不可用时会直接暴露问题**：如果 workspace broker 不可用，运行时会明确报错，而不是假装自己还记得。

### 这套系统实际记什么

可以把它理解成四类记忆，而不是一整团“长期记忆”：

- **会话记忆**
  - 记录当前任务的进度、中间结果和临时状态
  - 作用是把眼前这一轮工作做完

- **项目记忆**
  - 记录已经确认过的项目约定、架构决策和长期规则
  - 作用是下次回来时不用重新讲一遍背景

- **任务语义记忆**
  - 记录长任务里容易丢失、但和当前问题相关的上下文片段
  - 作用是任务做长以后还能快速找回关键内容

- **长期知识记忆**
  - 记录值得跨会话保留的关系、知识点和长期线索
  - 作用是把真正值得沉淀的东西留下来

<details>
<summary><b>📐 展开：记忆分层、写入边界与记忆相关 skill 的分工</b></summary>

<br/>

这一部分主要讲三件事：

1. 不同类型的记忆分别由谁负责
2. 为什么会同时存在几类看起来相近的记忆能力
3. 哪些写入是自动的，哪些需要确认，哪些属于可选扩展

### 四类记忆和它们各自的主要负责面

| 记忆类型 | 主要负责组件 | 默认作用域 | 主要保存什么 |
|:---|:---:|:---:|:---|
| **会话记忆** | `state_store` | 当前会话 | 执行进度、临时状态、中间结果 |
| **项目记忆** | `Serena` | 当前工作区 / 当前项目 | 已确认的架构决策、约定、长期项目规则 |
| **任务语义记忆** | `ruflo` | 会话内 / 长任务检索 | 长任务里和当前问题相关的上下文片段 |
| **长期知识记忆** | `Cognee` | 受控的跨会话知识 | 实体、关系和长期知识线索 |

> **可选外部扩展**：`mem0` 可以作为个人偏好后端使用，`Letta` 可以提供记忆块映射相关能力。但它们都不替代上面这四类记忆的权威分工。

### 为什么要同时保留几类记忆

它们不是重复设计，而是各自解决不同问题：

- 会话记忆负责“这一轮怎么做完”
- 项目记忆负责“下次回来还认得这个项目”
- 任务语义记忆负责“长任务里别把前面的关键内容弄丢”
- 长期知识记忆负责“真正值得沉淀的东西以后还能用”

如果只保留其中一种，实际体验都会变差。只有会话记忆，换一次会话就断；只有长期记忆，又很难替代当前任务里的细粒度状态。

### 三个记忆相关 skill，各自做什么

它们不是另一套平行记忆系统，而是围绕上面这些记忆层的常见入口或辅助能力：

- `knowledge-steward`
  - 适合把值得保留的提示词、踩坑经验、知识点主动存下来
  - 更像“把该记的东西送到合适的位置”

- `digital-brain`
  - 适合主动维护更结构化的个人知识和长期资料
  - 更像“长期知识整理入口”

- `deepagent-memory-fold`
  - 适合长任务上下文太大时，把内容压缩成可继续交接的记忆
  - 更像“长任务不中断的续航工具”

### 写入边界和治理规则

这里最重要的是边界，不是功能名本身：

- 不是所有内容都会自动变成长期记忆
- 项目级决策写入是受管的，`Serena` 写入持久项目真相前需要确认
- 检索只会返回有边界、和当前任务相关的 capsule，而不是整库回灌
- `episodic-memory` 保持禁用
- `mem0` 只负责个人偏好，不负责项目真相或路由权威
- 所有外部后端都可以通过 kill switch 关闭

### 如果只记一件事

这套系统的重点不是“让 AI 永远记住你的一切”。
重点是把该续上的项目上下文续上，把该保留的任务状态保留下来，把真正值得沉淀的东西放到受控的位置。

</details>

技术契约见 [工作区记忆平面设计](./docs/design/workspace-memory-plane.md)，量化验证见 [Codex 记忆仿真测试](./tests/runtime_neutral/test_codex_memory_user_simulation.py)。


---


## ✦ 全景能力地图：你的全能工作台

_这一节不是完整的 skill 名字清单，而是帮助你快速判断：VibeSkills 大致能覆盖哪些工作。_

_如果你只是想先判断它适不适合你的任务，看下面这张表就够了。_

<br/>

<div align="center">

| 工作方向 | 它主要能帮你做什么 | 代表能力 |
|:---|:---|:---|
| **💡 需求、规划与产品工作** | 把模糊想法讲清楚，写成 spec、计划和可执行任务 | `brainstorming`, `writing-plans`, `speckit-specify` |
| **🏗️ 工程开发、架构与受管执行** | 设计系统边界、落地代码改动，并协调多步骤工作流 | `aios-architect`, `autonomous-builder`, `vibe` |
| **🔧 调试、测试与质量控制** | 排查问题、补测试、做 review，并在完成前做核验 | `systematic-debugging`, `verification-before-completion`, `code-review` |
| **📊 数据分析与统计建模** | 清洗数据、做统计分析、探索模式并解释结果 | `statistical-analysis`, `performing-regression-analysis`, `data-exploration-visualization` |
| **🤖 机器学习与 AI 工程** | 训练、评估、解释并迭代模型相关工作流 | `senior-ml-engineer`, `training-machine-learning-models`, `evaluating-machine-learning-models` |
| **🔬 科研、文献与生命科学** | 做文献检索、科研支持，以及偏生信和生命科学的任务 | `literature-review`, `research-lookup`, `scanpy` |
| **📐 科学计算与数学建模** | 处理符号推导、概率建模、仿真和优化问题 | `sympy`, `pymc-bayesian-modeling`, `pymoo` |
| **🎨 文档、可视化与交付输出** | 把结果整理成文档、图表、图像、幻灯片等可交付内容 | `docs-write`, `plotly`, `scientific-visualization` |
| **🔌 外部集成、自动化与交付** | 连接浏览器、网页、外部服务、CI/CD 和部署流程 | `playwright`, `scrapling`, `aios-devops` |

</div>

<br/>

<details>
<summary><b>👉 按需展开：查看更细的能力分类、适用场景与分工</b></summary>

<br/>

这一部分讲的是完整覆盖面，但会尽量说人话。
它主要回答三个实际问题：

1. 你在什么场景下会用到这一类能力？
2. 为什么会同时保留几个看起来相近的 skill？
3. 这一类里，哪些是比较典型的代表项？

下面列的是代表项，不是把所有 skill 名字一股脑堆出来。重点是把角色和分工讲清楚，而不是把 README 写成库存表。

---

### 🧠 需求、规划与产品管理

**什么时候会用到**：当任务还很模糊，第一步不是写代码，而是先搞清楚“到底要解决什么问题”。

**为什么会共存**：它们解决的是同一条链路上的不同环节。一个负责澄清需求，一个负责写 spec，一个负责把 spec 拆成计划，还有的继续往下拆成任务。

**通常怎么遇到**：项目刚开始时、需求还没冻结时，或者要做高风险改动前。

**代表项**：`brainstorming`, `speckit-clarify`, `writing-plans`, `speckit-specify`

---

### 🛠️ 软件工程与架构设计

**什么时候会用到**：当问题已经比较清楚，开始进入“怎么设计、怎么实现、怎么协调落地”这一步。

**为什么会共存**：有的偏架构和边界设计，有的偏具体开发落地，有的偏多步骤、多代理的受管执行。它们很近，但不是一回事。

**通常怎么遇到**：规划完成后，任务开始涉及多文件修改、多层结构或多阶段执行时。

**代表项**：`aios-architect`, `architecture-patterns`, `autonomous-builder`, `vibe`

---

### 🔧 调试、测试与质量保证

**什么时候会用到**：当东西坏了、风险高、需要补测试，或者准备提交 review 的时候。

**为什么会共存**：排错、写测试、做 review、做完成前核验，本来就是不同动作。一个偏快速修复入口，另一个偏严格排障流程，谁都不能完全替代谁。

**通常怎么遇到**：报错之后、PR 之前，或者改动完成后需要拿证据说话的时候。

**代表项**：`systematic-debugging`, `error-resolver`, `verification-before-completion`, `code-review`

---

### 📊 数据分析与统计建模

**什么时候会用到**：当重点是“看数据、清数据、解释数据”，而不是先上模型。

**为什么会共存**：有的负责清洗和探索，有的负责统计检验，有的负责可视化，有的适合特定数据类型或处理链路。它们是配合关系，不是重复关系。

**通常怎么遇到**：建模前、实验分析时，或者当你真正想问“这些数据到底说明了什么”。

**代表项**：`statistical-analysis`, `performing-regression-analysis`, `detecting-data-anomalies`, `data-exploration-visualization`

---

### 🤖 机器学习与 AI 工程

**什么时候会用到**：当任务目标已经从“理解数据”变成“训练、评估、解释和迭代模型”。

**为什么会共存**：训练、评估、可解释性、实验记录本来就不是同一个动作。模型训练 skill 不等于数据分析 skill，可解释性 skill 也不该替代训练链路。

**通常怎么遇到**：数据准备完成后，需要真正跑模型、比较结果，或者理解模型为什么这样输出时。

**代表项**：`senior-ml-engineer`, `training-machine-learning-models`, `evaluating-machine-learning-models`, `explaining-machine-learning-models`

---

### 🧬 科研、文献与生命科学

**什么时候会用到**：当任务本身是科研工作，尤其是文献整理、研究支持、生命科学或生信分析。

**为什么会共存**：科研流程天然就是多步的。有人负责找论文，有人负责整理证据，有人负责分析实验数据，也有人负责生命科学专用工具链。

**通常怎么遇到**：做文献综述、单细胞分析、基因组学任务，或药物和实验支持类工作时。

**代表项**：`literature-review`, `research-lookup`, `biopython`, `scanpy`

---

### 🔬 科学计算与数学逻辑

**什么时候会用到**：当问题真正难的地方在数学推导、形式化建模、仿真或优化上。

**为什么会共存**：有的偏符号推导，有的偏概率模型，有的偏仿真，有的偏优化或形式逻辑。它们都跟“算”有关，但处理的不是同一种问题。

**通常怎么遇到**：科研任务、量化建模，或者自然语言解释已经不够精确的场景里。

**代表项**：`sympy`, `pymc-bayesian-modeling`, `pymoo`, `qiskit`

---

### 🔌 外部集成、自动化与部署

**什么时候会用到**：当任务离不开浏览器、网页内容、设计平台、外部服务、CI 或部署环境。

**为什么会共存**：浏览器交互、页面抓取、外部服务适配、部署自动化虽然都属于“连接外部世界”，但解决的是不同层面的工作。比如 `playwright` 和 `scrapling` 都碰网页，但一个更适合浏览器行为，一个更适合抓取和提取内容。

**通常怎么遇到**：当任务已经不能只靠模型本身完成，而是必须去碰外部系统的时候。

**代表项**：`playwright`, `scrapling`, `mcp-integration`, `aios-devops`

---

### 🎨 文档、可视化与交付输出

**什么时候会用到**：当任务结果需要被别人阅读、展示、评审或交付出去的时候。

**为什么会共存**：图表、文档、幻灯片、图片虽然都属于输出层，但服务的格式和对象不同。它们被放在一类，是因为都承担“把结果变成可交付物”的职责，而不是因为可以互相替代。

**通常怎么遇到**：工作流后段，当分析结果、研究结论或工程产出需要变成报告、图示、幻灯片或更完整的文档时。

**代表项**：`docs-write`, `plotly`, `scientific-visualization`, `generate-image`

---

合起来看，这些类别覆盖的是不同任务类型、不同工作阶段和不同交付形式。相似 skill 同时存在，通常不是为了重复堆料，而是因为它们分别承担了阶段差异、领域差异、宿主适配，或输出格式差异带来的不同职责。

</details>

<br/>

---


## 📊 为什么说它强大？

_看完完整版图，来看实际数字。这不是演示项目，而是已经跑起来的系统：_

**VibeSkills** 背后的运行时核心是 **VCO**。它绝不仅仅是一个单点工具或只会"补代码"的脚本，而是一个已完成高度整合与治理的**超级能力网络**：

<br/>

<div align="center">

|                              🧩 技能模块                               |                            🌍 生态融合                            |                               ⚖️ 治理规则                                |
| :---------------------------------------------------------------------: | :---------------------------------------------------------------: | :----------------------------------------------------------------------: |
| <h2>340+</h2>可直接调用的 Skills<br/>覆盖从需求规划到执行的完整链路 | <h2>19+</h2>吸收高价值上游开源项目<br/>与最佳实践来源 | <h2>129 条</h2>基于配置的策略与契约<br/>确保执行稳定、可溯源、防发散 |

</div>

<br/>

---


## ⚙️ 安装与 Skills 管理

你不需要先把整套架构弄懂，才能把 VibeSkills 装起来。

### 默认怎么装

1. 先确认你准备在哪个客户端里用它：`codex`、`claude-code`、`cursor`、`windsurf`、`openclaw`、`opencode`
2. 第一次安装、又没有特别要求时，直接选 `安装 + full`
3. 打开主安装页：
   [提示词安装（推荐）](https://github.com/foryourhealth111-pixel/Vibe-Skills/blob/main/docs/install/one-click-install-release-copy.md)
4. 找到对应客户端和版本，复制提示词，并粘贴到对应 AI 里执行
5. 安装完成后，按下面的 [开启你的 Vibe 体验](#-开启你的-vibe-体验) 调用方式开始使用

### `full` 还是 `minimal`？

- 想按推荐方式直接装好并开始用，就选 `full`
- 只有你明确只想要更小、更轻的框架安装时，再选 `minimal`

### 什么时候再看其他安装文档？

- 不知道自己该选哪种宿主路径：看 [冷启动宿主矩阵](https://github.com/foryourhealth111-pixel/Vibe-Skills/blob/main/docs/cold-start-install-paths.md)
- 想看更完整的分步命令：看 [多宿主命令参考](https://github.com/foryourhealth111-pixel/Vibe-Skills/blob/main/docs/install/recommended-full-path.md)
- 需要 OpenClaw / OpenCode 的宿主补充说明：看 [OpenClaw 宿主说明](https://github.com/foryourhealth111-pixel/Vibe-Skills/blob/main/docs/install/openclaw-path.md) 或 [OpenCode 宿主说明](https://github.com/foryourhealth111-pixel/Vibe-Skills/blob/main/docs/install/opencode-path.md)
- 需要离线或手动复制安装：看 [手动复制安装](https://github.com/foryourhealth111-pixel/Vibe-Skills/blob/main/docs/install/manual-copy-install.md)

<details>
<summary><b>🔧 高级安装细节</b></summary>

下面这些内容只在你需要手动补配置、排查问题或做高级定制时再看。

**如果文档要求你手动补一步，这些是真实文件路径**

- Codex：`~/.codex/settings.json`
- Claude Code：`~/.claude/settings.json`
- Cursor：`~/.cursor/settings.json`
- OpenCode：`~/.config/opencode/opencode.json`
- Windsurf / OpenClaw sidecar：`<target-root>/.vibeskills/host-settings.json`

**安装后对外保留什么**

- 对外运行时入口：`<target-root>/skills/vibe`
- 内部 bundled 语料：`<target-root>/skills/vibe/bundled/skills/*`
- 兼容性辅助文件：只有宿主明确需要时才生成

`.vibeskills` 被拆成两层：

- host-sidecar：`<target-root>/.vibeskills/host-settings.json`、`host-closure.json`、`install-ledger.json`、`bin/*`
- workspace-sidecar：`<workspace-root>/.vibeskills/project.json`、`.vibeskills/docs/requirements/*`、`.vibeskills/docs/plans/*`、`.vibeskills/outputs/runtime/vibe-sessions/*`

**哪些宿主已经做过安装后验证**

| 宿主 | 已验证的范围 |
|:---|:---|
| `codex` | planning、debug、governed execution、memory continuity |
| `claude-code` | planning、debug、governed execution、memory continuity |
| `openclaw` | planning、debug、governed execution、memory continuity |
| `opencode` | planning、debug、governed execution、memory continuity |

这些检查说明：安装后的 `vibe` 仍然能负责路由、写出治理和清理记录，并保持记忆连续性；但这不等于“每一种宿主调用语法都被同一次验证直接跑过”。

**卸载和自定义**

- 卸载入口：`uninstall.ps1 -HostId <host>`、`uninstall.sh --host <host>`
- 卸载治理说明：[`docs/uninstall-governance.md`](https://github.com/foryourhealth111-pixel/Vibe-Skills/blob/main/docs/uninstall-governance.md)
- 自定义 Skill 接入：[自定义工作流与 Skill 接入指南](https://github.com/foryourhealth111-pixel/Vibe-Skills/blob/main/docs/install/custom-workflow-onboarding.md)

</details>

## 📦 集众家之所长：资源整合

_这些能力不是闭门造车做出来的。VibeSkills 会参考现有开源项目、方法和工具，再把适合的部分接入同一套受管运行时。_

VibeSkills 并不声称要替代、也不会完整复刻下面列出的每一个上游项目。更实际的目标是：在合适的地方复用已经被验证的方法和能力，再通过同一套运行时与治理层把它们串起来，减少日常使用时的切换和拼装成本。

> 🙏 **鸣谢**
>
> 本项目参考、适配或接入了以下项目中的部分思路、工作流或工具能力：
>
> `superpower` · `claude-scientific-skills` · `get-shit-done` · `aios-core` · `OpenSpec` · `ralph-claude-code` · `SuperClaude_Framework` · `spec-kit` · `Agent-S` · `mem0` · `scrapling` · `claude-flow` · `serena` · `everything-claude-code` · `DeepAgent` 等等
>
> _我们会尽量认真处理上游来源的署名与说明。如果有遗漏，或某处表述不准确，欢迎在 Issue 中指出，我们会及时修正。_

<br/>

---


## 🚀 开启你的 Vibe 体验

_如果你已经装好了 VibeSkills，接下来只需要一次调用。_

> ⚠️ **调用说明**：VibeSkills 采用 **Skills 格式运行时**，请从宿主环境的 Skills 入口调用，**不要**把它当成独立 CLI 程序直接运行。

<br/>

<div align="center">

| 宿主环境 | 调用方式 | 示例 |
|:---:|:---:|:---|
| **Claude Code** | `/vibe` | `请帮我规划这个任务 /vibe` |
| **Codex** | `$vibe` | `请帮我规划这个任务 $vibe` |
| **OpenCode** | `/vibe` | `请用 vibe 帮我规划这次改动。` |
| **OpenClaw** | Skills 入口 | 参考宿主说明 |
| **Cursor / Windsurf** | Skills 入口 | 参考各平台 Skills 调用文档 |

</div>

<br/>

- 第一次可以先从一个很小的请求开始，比如让它先帮你澄清、规划或拆分任务。
- 如果你希望后续每一轮都留在受管工作流里，就在每条消息后面继续附上 `$vibe` 或 `/vibe`。
- 如果你还没安装，先回到 [提示词安装（默认推荐）](https://github.com/foryourhealth111-pixel/Vibe-Skills/blob/main/docs/install/one-click-install-release-copy.md)。

> MCP 说明：`$vibe` 或 `/vibe` 只表示进入 governed runtime，**不等于 MCP 完成**，也不能单独证明某个 MCP 已安装到宿主原生 MCP 配置面。

**当前宿主状态**：`codex` 和 `claude-code` 是目前最清晰、最完整的安装与使用路径。`cursor`、`windsurf`、`openclaw`、`opencode` 也可用，但其中一部分仍偏 preview 或带宿主特定约束。

<br/>

---

<details>
<summary><b>📚 文档导航与安装指引（点击展开）</b></summary>

<br/>

**先看这两个**

- ⚡️ [提示词安装（默认推荐）](https://github.com/foryourhealth111-pixel/Vibe-Skills/blob/main/docs/install/one-click-install-release-copy.md)
- 📖 [了解系统架构与理念](https://github.com/foryourhealth111-pixel/Vibe-Skills/blob/main/docs/quick-start.md)

**下面这些按需再看**

- 🧩 [自定义工作流接入](https://github.com/foryourhealth111-pixel/Vibe-Skills/blob/main/docs/install/custom-workflow-onboarding.md)
- 📄 [OpenClaw 宿主说明](https://github.com/foryourhealth111-pixel/Vibe-Skills/blob/main/docs/install/openclaw-path.md)
- 📄 [OpenCode 宿主说明](https://github.com/foryourhealth111-pixel/Vibe-Skills/blob/main/docs/install/opencode-path.md)
- 📁 [手动复制安装（离线）](https://github.com/foryourhealth111-pixel/Vibe-Skills/blob/main/docs/install/manual-copy-install.md)
- 🛠 [高级 host / lane 参考](https://github.com/foryourhealth111-pixel/Vibe-Skills/blob/main/docs/install/recommended-full-path.md)
- 🧊 [冷启动与其他环境说明](https://github.com/foryourhealth111-pixel/Vibe-Skills/blob/main/docs/cold-start-install-paths.md)

</details>

<br/>

<div align="center">

### 🤝 加入社区 · 共建生态

欢迎来尝试和体验！有问题、有想法、有建议，欢迎随时提出——鄙人不才，一定认真听取和修改。

<br/>

**本项目完全开源，欢迎一切形式的贡献！**

无论是修复 bug、提升性能、添加新功能还是完善文档，你的每一个 PR 都弥足珍贵。

```
Fork → 修改 → Pull Request → 合并 ✅
```

<br/>

> ⭐ 如果这个项目对你有帮助，点个 **Star** 是对我最大的支持！
> 它的理念受到了大家的欢迎，但目前的底层代码存在一些技术债，功能也有待完善，欢迎大家在issue区指出。
> 您的支持也是我这个核动力驴的浓缩 U-235 :blush:

<br/>

感谢 **LinuxDo** 各位佬的支持！

[![LinuxDo](https://img.shields.io/badge/社区-LinuxDo-blue?style=for-the-badge)](https://linux.do/)

各种技术交流、AI 前沿资讯、AI 经验分享，尽在 Linuxdo！

</div>

<br/>

---


## Star History

<a href="https://www.star-history.com/?repos=foryourhealth111-pixel%2FVibe-Skills&type=date&legend=top-left">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/image?repos=foryourhealth111-pixel/Vibe-Skills&type=date&theme=dark&legend=top-left" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/image?repos=foryourhealth111-pixel/Vibe-Skills&type=date&legend=top-left" />
    <img alt="Star History Chart" src="https://api.star-history.com/image?repos=foryourhealth111-pixel/Vibe-Skills&type=date&legend=top-left" />
  </picture>
</a>

<br/>

---

<div align="center">
  <p><i>把真实工作里最容易失控的部分，变成一个更可调用、更可治理、也更可长期维护的系统。</i></p>
  <br/>
  <sub>Made with ❤️ &nbsp;·&nbsp; <a href="https://github.com/foryourhealth111-pixel/Vibe-Skills">GitHub</a> &nbsp;·&nbsp; <a href="./README.md">English</a></sub>
</div>
