# README Memory Section Clarity Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the README memory section so it explains what gets remembered, what the boundaries are, and how the memory layers relate without sounding like a marketing page.

**Architecture:** Keep the existing top-level README layout, but change the memory section into a plain-language flow: user-facing outcome first, workspace-memory behavior second, and detailed layering and governance inside the foldout. Preserve the technical links and the guarded sections elsewhere in the README.

**Tech Stack:** Markdown docs, existing README structure, targeted pytest checks for README contracts

---

## Chunk 1: Main Section Rewrite

### Task 1: Reframe the first screen around user outcomes and boundaries

**Files:**
- Modify: `README.md`
- Modify: `README.zh.md`

- [ ] **Step 1: Replace the current memory-section headline and intro copy**

Keep the section in the same place, but rewrite the title and opening so it explains:

- what memory is for
- what it does not do by default
- that memory continuity is workspace-scoped rather than unlimited personal recall

- [ ] **Step 2: Replace the pain-point matrix with a simpler user-facing summary**

Show:

- whether a new session can resume project context
- how long-task handoff works
- whether unrelated project history leaks
- whether all history is dumped back into context
- whether writes happen automatically

## Chunk 2: Foldout Rewrite

### Task 2: Explain layers, skill roles, and boundaries in plain language

**Files:**
- Modify: `README.md`
- Modify: `README.zh.md`

- [ ] **Step 1: Rewrite the foldout structure**

Explain:

- the four memory categories
- why they coexist
- how the memory skills relate to those categories
- which writes require confirmation

- [ ] **Step 2: Keep technical links, but move jargon behind explanations**

Retain:

- workspace memory design doc link
- memory simulation test link

Expected outcome:

- user can understand the section without already knowing `Serena`, `ruflo`, `Cognee`, `mem0`, or `Letta`

## Chunk 3: Verification

### Task 3: Run the README-focused checks and update the PR branch

**Files:**
- Modify: `README.md`
- Modify: `README.zh.md`

- [ ] **Step 1: Run focused README verification**

Run:

```bash
python3 -m pytest tests/integration/test_public_install_uninstall_guidance.py tests/integration/test_native_mcp_first_install_docs.py tests/integration/test_codex_install_prompt_discoverability.py tests/runtime_neutral/test_docs_readme_encoding.py -q
git diff --check origin/main..HEAD
```

Expected: PASS

- [ ] **Step 2: Reconfirm the protected pain-point table stayed unchanged**

Check that diffs against `origin/main` for `README.md` and `README.zh.md` do not touch:

- `Real problem`
- `What VibeSkills does`
- `真实问题`
- `VibeSkills 的做法`
