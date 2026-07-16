# Runtime Freshness Install SOP

This playbook covers the installed Vibe payload under `<skills-dir>/vibe`.

## Boundary

- The installer owns only the files listed in `.vibeskills/install-receipt.json`.
- Freshness means every receipt-owned file still exists and has the recorded SHA-256 hash.
- Freshness does not require the installed folder to be a full repository mirror.
- Extra user files are reported by `check`, but they are not treated as installer-owned files.

## Install And Check

PowerShell:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -SkillsDir "<skills-dir>"
pwsh -NoProfile -ExecutionPolicy Bypass -File .\check.ps1 -SkillsDir "<skills-dir>"
```

Bash:

```bash
bash ./install.sh --skills-dir "<skills-dir>"
bash ./check.sh --skills-dir "<skills-dir>"
```

## Freshness Gate

The installed payload contains its own receipt verification gate:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File "<skills-dir>\vibe\scripts\verify\vibe-installed-runtime-freshness-gate.ps1" -TargetRoot "<host-root>"
```

`<skills-dir>` is `<host-root>/skills`. The gate may run from the installed payload because it reads only that payload's install receipt and owned files.

Use `-WriteArtifacts` only when a standalone verification record is needed. It writes `outputs/verify/installed-runtime-freshness.json` inside the installed payload and does not replace the install receipt.

## Receipt Contract

The installer writes `.vibeskills/install-receipt.json` under the installed Vibe root. The required fields are:

- `schema_version`
- `receipt_kind = vibe-skill-install`
- `skill_id = vibe`
- `skills_dir`
- `install_root`
- `package_digest_sha256`
- `files[*].path`
- `files[*].sha256`

The freshness gate fails when the receipt is missing, identifies a different install root, contains an invalid entry, points outside the installed root, or records a missing or changed file.

## Troubleshooting

### Update Refuses To Run

`update` refuses to overwrite a drifted install. Run `check` first. Restore or deliberately remove local changes under the receipt-owned paths, then run `update` again.

### Freshness Fails

1. Read the reported missing or changed path.
2. Run `check` against the same skills directory.
3. Reinstall from the intended source only after confirming no local receipt-owned change needs to be kept.

### Extra Files Are Reported

Extra files are outside installer ownership. Remove them only when their owner and purpose are known.

## Repo Release Audit

`vibe-release-install-runtime-coherence-gate.ps1` remains a repository release audit. It is not an installed-runtime execution unit and must not be used to require a full repository mirror inside `<skills-dir>/vibe`.
