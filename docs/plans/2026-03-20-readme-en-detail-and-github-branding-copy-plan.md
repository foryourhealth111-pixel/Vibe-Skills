# README EN Detail And GitHub Branding Copy Plan

**Goal:** Bring `README.en.md` up to the same public-facing detail level as the Chinese README and add a reusable GitHub branding copy document for repository settings.

**Internal Grade:** M

**Wave Structure:**

1. Freeze this turn in governed requirement and plan docs.
2. Rewrite `README.en.md` so it mirrors the Chinese README's information depth and section rhythm.
3. Add a compact branding doc covering `About`, `Topics`, and social preview copy.
4. Update requirements / plans indexes.
5. Verify markdown integrity and final diff scope.

**Execution Rules:**

- Keep the capability-first opening.
- Keep the English readable and idiomatic rather than mechanically literal.
- Make the branding copy short, reusable, and settings-ready.
- Do not widen scope into new assets, homepage redesign, or README CN rewrites.

**Planned Output Shape:**

- `README.en.md`
  - detailed capability matrix
  - deeper subdomain expansion
  - integrated resources section
  - pain points and operating philosophy
- `docs/brand/github-branding-copy.md`
  - `About` candidates
  - recommended `Topics`
  - social preview title / subtitle / copy candidates

**Verification Commands:**

- `sed -n '1,320p' README.en.md`
- `sed -n '1,260p' docs/brand/github-branding-copy.md`
- `git diff -- README.en.md docs/brand/github-branding-copy.md docs/requirements/2026-03-20-readme-en-detail-and-github-branding-copy.md docs/plans/2026-03-20-readme-en-detail-and-github-branding-copy-plan.md docs/requirements/README.md docs/plans/README.md`
- `git diff --check -- README.en.md docs/brand/github-branding-copy.md docs/requirements/2026-03-20-readme-en-detail-and-github-branding-copy.md docs/plans/2026-03-20-readme-en-detail-and-github-branding-copy-plan.md docs/requirements/README.md docs/plans/README.md`

**Rollback Rules:**

- If the English becomes stiff, compress literal translation and prioritize clarity.
- If the branding doc becomes too long, keep only the strongest recommended options and move alternates below.
- Do not attempt GitHub settings automation in this pass.

**Phase Cleanup Expectations:**

- Leave a clean README EN diff and a settings-ready branding copy doc.
- Verify markdown formatting before completion.
