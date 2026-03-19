# Repo Rename To Vibe-Skills Execution Plan

**Goal:** Plan a safe GitHub repository rename from `vco-skills-codex` to `Vibe-Skills` without breaking active runtime behavior or losing external discoverability.

**Internal Grade:** M

**Wave Structure:**

1. Confirm external-platform behavior and local dependency shape.
2. Freeze the rename requirement and plan.
3. Categorize risks by severity and runtime impact.
4. Produce a phased operator checklist for pre-rename, rename, and post-rename cleanup.

**Risk Summary:**

- **Low runtime risk:** GitHub repository rename itself; old web and git URLs are redirected by GitHub.
- **Medium maintenance risk:** hardcoded GitHub URLs in issue templates, docs, notices, and release/proof artifacts will become stale.
- **High integration risk:** if any external repository uses `uses: owner/repo@ref` to consume this repository as a GitHub Action, GitHub does not guarantee redirect support for those action references.
- **Operational risk:** local contributors will keep working through redirect for a while, but remotes should still be normalized to the new URL after rename.

**Planned Phases:**

### Phase 1: Pre-rename checklist

- Freeze or at least inventory current dirty local changes.
- Announce a short maintenance window if there are contributors or automation consumers.
- Search for hardcoded repository URLs and repo-name strings.
- Check whether any external workflows, docs, package metadata, install scripts, or badges depend on the old repo slug.

### Phase 2: GitHub rename action

- In GitHub repository settings, rename `vco-skills-codex` to `Vibe-Skills`.
- Do not simultaneously change owner, default branch, package namespace, or release process.
- Do not rename the local filesystem folder in the same maintenance window; treat local path normalization as a separate follow-up task.
- Immediately verify that the old repository URL redirects to the new repository page.

### Phase 3: Post-rename normalization

- Update local remotes with `git remote set-url origin <new-url>`.
- Keep the existing local checkout folder name temporarily if you have scripts, notes, or proof artifacts that still reference the old absolute path.
- Update hardcoded GitHub links in `.github/ISSUE_TEMPLATE/config.yml` first.
- Update public-facing docs, `NOTICE`, and any operational copy that still says `vco-skills-codex`.
- Decide whether to keep internal product naming like `VCO` / `VibeSkills` unchanged for now.

### Phase 4: Deep cleanup

- Sweep docs, proof bundles, release ledgers, and historical artifacts for stale repo name references.
- Only rewrite historical proof paths if you explicitly want a clean public narrative; they are not the first blocker for runtime safety.
- Re-run key GitHub workflow(s) after rename to prove no regression.

**Concrete Repository Follow-up Targets:**

- `.github/ISSUE_TEMPLATE/config.yml`
- `NOTICE`
- docs and bundled docs that still mention `vco-skills-codex`
- proof/reference artifacts containing absolute historical paths
- any release metadata or user-agent strings that should align with the new slug

**Verification Commands After Actual Rename:**

- `git remote -v`
- `git remote set-url origin https://github.com/foryourhealth111-pixel/Vibe-Skills.git`
- `git fetch origin`
- `git remote show origin`
- inspect GitHub issue-template links
- run at least one GitHub Actions workflow on the renamed repository

**Rollback Rules:**

- If a critical external integration depends on the old slug without redirect tolerance, postpone rename until the consumer is updated.
- If package managers, marketplace listings, or action consumers are discovered later, migrate them before broad announcement.
- Do not mass-edit historical proof bundles during the rename action itself.

**Operator Decision:**

Proceed with rename only after checking whether the repository is consumed externally as a GitHub Action or by hardcoded raw/blob links in third-party places.
