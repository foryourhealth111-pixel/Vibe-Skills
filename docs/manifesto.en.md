[中文](./manifesto.md)

# VibeSkills Manifesto

> We are not collecting more skills.
> We are building a real capability infrastructure layer for general-purpose intelligence.

## Why We Built VibeSkills

Models are already powerful enough to code, research, automate, operate tools, and coordinate workflows.

What still prevents them from becoming stable, long-lived systems is not raw model capability. It is the way capability itself is organized.

The problem is not that skills do not exist.
The problem is that skills still live in a fragmented, fragile, and poorly governed state:

- users do not know which skill to use
- teams do not know which skills are trustworthy
- multiple skills do not compose reliably in complex tasks
- custom skills are often inconsistent and hard to maintain
- many agent systems look impressive, but their boundaries, verification surfaces, and rollback paths remain unclear

We do not believe the future of general-purpose AI can be built on prompt glue code, wild plugins, and hidden magic.

We believe models need a skills substrate that can evolve over time, be verified, be rolled back, be composed, and be governed.

That is what VibeSkills is trying to build.

## What We Reject

We reject the idea that “able to call tools” means “able to complete work reliably”.

We reject turning stacks of prompts, one-off tricks, and opaque integrations into something that merely looks like a system.

We reject using more features to hide deeper instability, and using more skills to hide weaker governance.

We reject ecosystems that push the burden of choosing, stitching, validating, and recovering onto the user.

We also reject another common illusion: the idea that stronger base models alone will make these problems disappear.

They will not.

As models become stronger and external capabilities become more numerous, governance becomes more important, not less.

## What We Are Building

VibeSkills aims to become a universal skills substrate for general-purpose AI.

That means it is not just a list of skills, and not just a router.
It is a system layer built around governed capability execution:

- it helps models understand what level a task belongs to and which execution flow should be entered
- it helps models choose better among multiple candidate skills instead of guessing blindly
- it helps multiple skills compose under explicit governance
- it helps complex tasks evolve from single-agent execution into coordinated teams
- it helps the whole process gain boundaries, protocols, gates, evidence, and fallback paths

If the model is the brain, VibeSkills aims to be the execution exoskeleton.

Not a replacement for intelligence.
But a way to make intelligence land more reliably in real work.

## Why This Is Not Just Another Skill Repository

A skill repository answers: what is available?

VibeSkills tries to answer harder questions:

- what should be called for this task
- what should not be called
- in what order capabilities should be activated
- how multiple capabilities should work together
- how execution quality should be verified
- how risk should be exposed
- how failure should be rolled back
- how long-term evolution can avoid turning the system into chaos

In other words, VibeSkills is not a capability directory.
It is a capability governance system.

We are not trying to end skills.
We are trying to end the chaotic state of skills.

## Our Technical Commitments

We do not promise to be “the strongest forever”.
We promise to keep doing the hard things that make systems trustworthy.

### 1. One control plane first

We keep `VCO` as the primary control plane instead of casually stacking multiple orchestration owners on top of each other.

New capabilities, overlays, and upstream projects can be integrated, but they must respect shared governance boundaries, role separation, and conflict rules instead of smuggling in a second execution authority.

### 2. Governance before feature inflation

We prioritize:

- routing correctness
- quality gates
- memory boundaries
- conflict governance
- observability
- rollback paths
- disciplined upgrades and releases

We do not believe “integrate now, govern later” can sustain a serious ecosystem.

### 3. Composition must be explainable, verifiable, and reversible

We encourage multi-skill composition and multi-agent teams.

But composition cannot be a black box pile.
It should be possible to understand:

- why the system routed this way
- why a capability was activated
- why a given execution flow was selected
- how results can be checked
- how the system can degrade or roll back when things fail

### 4. We do not confuse prompt magic with system reliability

Prompts are part of capability, but they are not governance.

We will keep using prompts, overlays, semantic enhancements, and LLM reranking where they help.
But we will not pretend these mechanisms alone constitute infrastructure reliability.

Reliability comes from protocols, gates, validation, evidence, and boundaries, not just from more sophisticated prompting.

### 5. Real user need comes before framework self-indulgence

VibeSkills exists to make AI less stressful, less fragile, and more reliable in real work.

If a design does not reduce user choice cost, composition cost, risk cost, or maintenance cost, it should not become core to this system.

## Our Open-Source Commitments

We want this to be an open substrate, not a closed empire.

### 1. Users come first

The first people we want to attract are not framework hobbyists.
They are people already trying to use AI in real work.

We welcome:

- heavy users doing development, research, analysis, and automation
- team leads trying to make AI operational
- users frustrated with the current fragmented skill ecosystem

Because only real users can keep pulling the system back toward what actually matters.

### 2. Developer contribution should grow from real demand

We welcome skill builders, agent framework authors, governance tool builders, verification maintainers, and integration contributors.

But we want contribution to grow from real use cases, not from the urge to keep attaching new toys.

### 3. Open does not mean boundaryless

VibeSkills should remain open to new capabilities.

But open does not mean giving up standards.
It means being more explicit about admission rules, role boundaries, evidence requirements, and sustainable evolution.

## How To Join

### If you are a user

You can:

- try the system directly
- submit real tasks and scenarios
- tell us where it is still unstable, still confusing, or still not trustworthy enough
- help define what a reliable AI execution system should look like

### If you are a developer

You can:

- contribute skills, routing strategies, governance rules, verification scripts, and integrations
- help reduce duplication and hidden conflict in the ecosystem
- help move skills from “usable” to “reliable, governed, stable, and composable”

## What Kind of Project This Is

This is not a one-shot release of a magical framework.

It is a long-term construction effort:

- organizing scattered capabilities into a system
- placing that system under governance
- turning governance itself into durable open infrastructure

We do not think this will be solved overnight.
But we do think general-purpose intelligence cannot move into its next stage without this layer being built, and built in the open.

## Finally

The ambition of VibeSkills is not modest.

We want to build a universal skills substrate for general-purpose AI.
One that is open enough, strict enough, reliable enough, and broad enough to matter.

We want a future where users no longer have to ask:

- which skill should I use right now
- is this skill actually safe
- can these skills work together
- will this agent lose control
- is this system just another demo

We want a future where models do not merely “do many things”.
We want them to operate inside a governed capability system that can help them get things done reliably over time.

If you believe this is where AI infrastructure should go, use it, star it, and help build it.
