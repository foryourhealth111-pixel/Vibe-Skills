# Quick Start

If this is your first time in the repository, you do not need to read everything.

Pick the entry that matches what you want right now.

## I just want to understand what this is

Start with:

- [`../README.en.md`](../README.en.md)

That page explains what the project is, what problem it is trying to solve, and why it is not just another skill repository.

## I want to start using it right away

Go straight to:

- [`install/one-click-install-release-copy.en.md`](./install/one-click-install-release-copy.en.md)

The main entry there is not a wall of commands. It is a prompt you can copy into your AI assistant.

The current public host-visible wrapper set is fixed to these four entries:

- `vibe`
- `vibe-want`
- `vibe-how`
- `vibe-do`

If your host supports menu-style rendering, it will usually display them as:

- `Vibe`
- `Vibe: What Do I Want?`
- `Vibe: How Do We Do It?`
- `Vibe: Do It`

They still resolve to the same governed `vibe` runtime. The difference is the default stop target:

- `vibe` / `Vibe`: run the full governed flow
- `vibe-want` / `Vibe: What Do I Want?`: clarify goals, boundaries, and acceptance criteria, then stop after freezing the requirement
- `vibe-how` / `Vibe: How Do We Do It?`: freeze the requirement and plan, then stop
- `vibe-do` / `Vibe: Do It`: execute the full governed flow without skipping requirement or plan

If you want a heavier execution lane, use only:

- `--l`
- `--xl`

Do not rely on aliases like `vibe-l` or `vibe-xl`. Those combinations are intentionally unsupported.

If your target host is OpenCode, you can also go straight to:

- [`install/opencode-path.en.md`](./install/opencode-path.en.md)

## I want to understand why this project exists

Read:

- [`manifesto.en.md`](./manifesto.en.md)

That page is no longer a giant declaration. It is a shorter explanation of how the project grew out of real friction and what principles it tries to protect.

## I am already a heavy user and want the fuller install story

Read these:

- [`install/recommended-full-path.en.md`](./install/recommended-full-path.en.md)
- [`cold-start-install-paths.en.md`](./cold-start-install-paths.en.md)
- [`install/opencode-path.en.md`](./install/opencode-path.en.md)

They are more complete and more operator-oriented than the public entry pages.

## How should I think about `VibeSkills` and `VCO`

The simplest explanation is:

- `VibeSkills` is the public project name
- `VCO` is the core governed runtime behind it

The first is the system you are using.
The second is the execution skeleton that helps the system stay disciplined.

## Recommended Reading Order

If you want the shortest sensible path, go in this order:

1. [`../README.en.md`](../README.en.md)
2. [`install/one-click-install-release-copy.en.md`](./install/one-click-install-release-copy.en.md)
3. [`manifesto.en.md`](./manifesto.en.md)

That is usually enough to understand what it is, how to start, and why it was built this way.
