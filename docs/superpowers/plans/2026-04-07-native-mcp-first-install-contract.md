# Native MCP-First Install Contract Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update the install prompt and documentation contract so all six public hosts describe MCP as `native MCP first`, keep `$vibe` as governed runtime entry only, and stop treating templates, manifests, sidecars, or CLI presence as proof of host-visible MCP completion.

**Architecture:** Treat this as a docs-and-contract change with tests first. Update the prompt surfaces that directly instruct install assistants, then align the supporting install/reference docs and README wording, and finally strengthen the prompt-contract tests so the new truth model is enforced automatically. Keep runtime-install success, `vibe host-ready`, per-MCP host-visible readiness, and `online-ready` explicitly separated throughout.

**Tech Stack:** Markdown documentation, pytest/unittest doc-contract tests, ripgrep-based verification

---

## Chunk 1: Install Prompt Contract

### Task 1: Add failing prompt-contract assertions for native-MCP-first wording

**Files:**
- Modify: `tests/runtime_neutral/test_install_prompt_mcp_contract.py`
- Create: `tests/integration/test_native_mcp_first_install_docs.py`
- Spec reference: `docs/superpowers/specs/2026-04-07-native-mcp-first-install-contract-design.md`

- [ ] **Step 1: Extend the prompt-contract test with the new wording requirements**

Add assertions that all eight install/update prompt files require wording equivalent to:

```python
for path in PROMPT_FILES:
    text = path.read_text(encoding="utf-8-sig")
    lowered = text.lower()
    assert "native mcp surface" in lowered or "宿主原生 mcp" in text
    assert "$vibe" in text or "/vibe" in text
    assert "not" in lowered and "proof" in lowered
```

Make the assertions precise enough to reject prompt text that still conflates:

- governed runtime entry
- repo-owned templates or manifests
- command presence on PATH
- host-visible MCP readiness

- [ ] **Step 2: Add a focused integration test for the shared cross-host contract**

Create `tests/integration/test_native_mcp_first_install_docs.py` with checks similar to:

```python
def test_install_docs_define_native_mcp_first_as_the_completion_target() -> None:
    zh_prompt = (REPO_ROOT / "docs/install/prompts/full-version-install.md").read_text(encoding="utf-8")
    en_prompt = (REPO_ROOT / "docs/install/prompts/full-version-install.en.md").read_text(encoding="utf-8")

    assert "宿主原生 MCP" in zh_prompt
    assert "native MCP surface" in en_prompt
    assert "$vibe" in zh_prompt and "不等于 MCP" in zh_prompt
    assert "$vibe" in en_prompt and "not MCP completion" in en_prompt
```

Include at least one assertion covering:

- native MCP first
- `$vibe` is not MCP proof
- templates / sidecars / manifests are not completion proof
- six-host unified wording

- [ ] **Step 3: Run the doc-contract tests and confirm they fail before docs are edited**

Run:

```bash
pytest tests/runtime_neutral/test_install_prompt_mcp_contract.py tests/integration/test_native_mcp_first_install_docs.py -q
```

Expected: FAIL because the current docs do not yet require `native MCP first` wording explicitly.

- [ ] **Step 4: Commit the failing-test checkpoint**

```bash
git add tests/runtime_neutral/test_install_prompt_mcp_contract.py tests/integration/test_native_mcp_first_install_docs.py
git commit -m "test: require native mcp first install wording"
```

## Chunk 2: Prompt And Install Docs

### Task 2: Rewrite the eight install/update prompts to use the new truth model

**Files:**
- Modify: `docs/install/prompts/full-version-install.md`
- Modify: `docs/install/prompts/full-version-install.en.md`
- Modify: `docs/install/prompts/framework-only-install.md`
- Modify: `docs/install/prompts/framework-only-install.en.md`
- Modify: `docs/install/prompts/full-version-update.md`
- Modify: `docs/install/prompts/full-version-update.en.md`
- Modify: `docs/install/prompts/framework-only-update.md`
- Modify: `docs/install/prompts/framework-only-update.en.md`
- Spec reference: `docs/superpowers/specs/2026-04-07-native-mcp-first-install-contract-design.md`

- [ ] **Step 1: Replace the generic MCP attempt wording with native-MCP-first wording**

In every prompt, make the MCP section explicitly say that:

- MCP must be automatically installed into the host's real native MCP surface first
- `$vibe` or `/vibe` proves governed runtime entry only
- templates, manifests, example configs, sidecars, and PATH-visible commands do not by themselves prove MCP completion
- if native MCP auto-registration is unavailable or fails, the assistant must report `not host-visible` / pending rather than soft-success language

- [ ] **Step 2: Keep host-specific command guidance but separate it from MCP completion**

Preserve the current host-specific install/check commands and root-path rules, but add wording such as:

```text
`$vibe` direct discoverability is a governed-runtime outcome only.
MCP is counted as ready only when it is visible through the host's real native MCP surface.
```

Make sure this appears in both Chinese and English prompt sets.

- [ ] **Step 3: Tighten the final report requirements in every prompt**

Ensure all eight prompts require final reporting with these distinct sections:

- `installed locally`
- `vibe host-ready`
- `mcp native auto-provision attempted`
- per-MCP `host-visible readiness`
- `online-ready`

Do not allow older wording that collapses these into one install-success statement.

- [ ] **Step 4: Run the prompt-contract tests again**

Run:

```bash
pytest tests/runtime_neutral/test_install_prompt_mcp_contract.py tests/integration/test_native_mcp_first_install_docs.py -q
```

Expected: PASS for the prompt-only contract assertions.

- [ ] **Step 5: Commit the prompt contract changes**

```bash
git add docs/install/prompts/full-version-install.md docs/install/prompts/full-version-install.en.md docs/install/prompts/framework-only-install.md docs/install/prompts/framework-only-install.en.md docs/install/prompts/full-version-update.md docs/install/prompts/full-version-update.en.md docs/install/prompts/framework-only-update.md docs/install/prompts/framework-only-update.en.md tests/runtime_neutral/test_install_prompt_mcp_contract.py tests/integration/test_native_mcp_first_install_docs.py
git commit -m "docs: enforce native mcp first prompt contract"
```

### Task 3: Align the supporting install docs and README with the same contract

**Files:**
- Modify: `docs/install/recommended-full-path.md`
- Modify: `docs/install/recommended-full-path.en.md`
- Modify: `docs/install/installation-rules.md`
- Modify: `docs/install/installation-rules.en.md`
- Modify: `docs/install/minimal-path.md`
- Modify: `docs/install/minimal-path.en.md`
- Modify: `docs/one-shot-setup.md`
- Modify: `README.md`
- Modify: `README.zh.md`

- [ ] **Step 1: Update the shared MCP contract sections in install-path docs**

Make `recommended-full-path.*`, `installation-rules.*`, `minimal-path.*`, and `one-shot-setup.md` describe:

- native MCP surface as the preferred completion target
- non-blocking MCP attempt behavior
- `$vibe` as governed runtime only
- runtime payload/template/sidecar/CLI as non-proof of MCP completion

- [ ] **Step 2: Update README installation language without weakening the runtime entry story**

Keep the current invocation guidance for `/vibe` and `$vibe`, but add clarifying wording that:

- those invocations are runtime-entry syntax
- they do not by themselves imply MCP is installed into the host
- host-native MCP readiness is a separate install outcome

- [ ] **Step 3: Preserve host support wording while removing fake MCP success implications**

Audit the host-summary and install-guide paragraphs for wording that could still imply:

- `skills/vibe` presence equals MCP completion
- preview-guidance or runtime-core payload equals native MCP completion

Replace such wording with explicit separation.

- [ ] **Step 4: Run the existing doc tests that cover host-root and prompt discoverability**

Run:

```bash
pytest tests/integration/test_codex_install_prompt_discoverability.py tests/integration/test_multi_host_real_host_root_docs.py tests/runtime_neutral/test_install_prompt_mcp_contract.py tests/integration/test_native_mcp_first_install_docs.py -q
```

Expected: PASS after supporting docs are aligned.

- [ ] **Step 5: Commit the supporting-doc and README changes**

```bash
git add docs/install/recommended-full-path.md docs/install/recommended-full-path.en.md docs/install/installation-rules.md docs/install/installation-rules.en.md docs/install/minimal-path.md docs/install/minimal-path.en.md docs/one-shot-setup.md README.md README.zh.md tests/integration/test_codex_install_prompt_discoverability.py tests/integration/test_multi_host_real_host_root_docs.py tests/runtime_neutral/test_install_prompt_mcp_contract.py tests/integration/test_native_mcp_first_install_docs.py
git commit -m "docs: align install guides with native mcp first contract"
```

## Chunk 3: Final Verification And Handoff

### Task 4: Verify the whole contract surface and prepare execution handoff

**Files:**
- Review: `docs/superpowers/specs/2026-04-07-native-mcp-first-install-contract-design.md`
- Review: `docs/superpowers/plans/2026-04-07-native-mcp-first-install-contract.md`
- Review: all files changed in Tasks 2 and 3

- [ ] **Step 1: Run the complete targeted verification suite**

Run:

```bash
pytest tests/runtime_neutral/test_install_prompt_mcp_contract.py tests/integration/test_native_mcp_first_install_docs.py tests/integration/test_codex_install_prompt_discoverability.py tests/integration/test_multi_host_real_host_root_docs.py -q
```

Expected: all targeted doc-contract tests PASS.

- [ ] **Step 2: Run ripgrep sanity checks against accidental regression wording**

Run:

```bash
rg -n "MCP ready.*\\$vibe|\\$vibe.*MCP ready|template.*MCP.*ready|sidecar.*MCP.*ready|manifest.*MCP.*ready" docs README* tests
```

Expected: no misleading completion shortcuts remain, or only negative/forbidden examples remain inside the spec.

- [ ] **Step 3: Review the diff for wording drift and unsupported claims**

Run:

```bash
git diff --stat
git diff -- docs/install/prompts docs/install README.md README.zh.md tests/runtime_neutral/test_install_prompt_mcp_contract.py tests/integration/test_native_mcp_first_install_docs.py tests/integration/test_codex_install_prompt_discoverability.py tests/integration/test_multi_host_real_host_root_docs.py
```

Confirm that the diff:

- does not change installer implementation
- does not claim native MCP automation exists where it does not
- does not weaken the real-host-root guidance for `codex`

- [ ] **Step 4: Commit the final verified plan execution result**

```bash
git add docs/install/prompts docs/install README.md README.zh.md tests/runtime_neutral/test_install_prompt_mcp_contract.py tests/integration/test_native_mcp_first_install_docs.py tests/integration/test_codex_install_prompt_discoverability.py tests/integration/test_multi_host_real_host_root_docs.py
git commit -m "test: lock native mcp first install contract"
```

- [ ] **Step 5: Prepare the close-out summary**

The final execution summary should state:

- which prompt/docs surfaces changed
- which tests were added or updated
- which verification commands passed
- that this is a docs-and-contract change only, not an installer-core behavior change
