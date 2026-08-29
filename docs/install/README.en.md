# Simple Install

The public install path starts from a published release zip, not a repository checkout. Download the current [vibe-skills-4.1.0-public.zip](https://github.com/foryourhealth111-pixel/Vibe-Skills/releases/download/v4.1.0/vibe-skills-4.1.0-public.zip), extract it outside the managed Skills directory, and run the wrappers from the extracted folder.

Verify the downloaded ZIP against the SHA-256 digest shown for the asset on the GitHub Release page.

## One Installation Model

VibeSkills uses the same package and directory layout in every AI application:

1. Choose a `SkillsDir` that the application scans.
2. Run `install` against that directory.
3. Invoke `vibe` through the application's Skills entry.

The installer always writes the same runtime to `<SkillsDir>/vibe`. The
application changes only the `SkillsDir` path and the invocation syntax; it
does not select a different VibeSkills package or runtime.

The default directory is `~/.agents/skills`. If a host or your own workflow needs a different skills directory, pass it explicitly, for example `~/.codex/skills` or `~/.claude/skills`.

## Install

```powershell
pwsh -NoProfile -File .\install.ps1 -SkillsDir "$HOME\.agents\skills"
pwsh -NoProfile -File .\check.ps1 -SkillsDir "$HOME\.agents\skills"
```

```bash
bash ./install.sh --skills-dir "$HOME/.agents/skills"
bash ./check.sh --skills-dir "$HOME/.agents/skills"
```

To use another Skills directory, replace only the `SkillsDir` value. The
installed files and runtime remain identical.

After installation, the managed directory is `<SkillsDir>/vibe`. The install receipt lives at `<SkillsDir>/vibe/.vibeskills/install-receipt.json`.

`check` verifies the files recorded in the receipt.
`check` proves `installed locally`. It does not prove `runtime coherent` or `delivery accepted`.

## Update An Existing Install

Download the newer published release ZIP first, extract it, and run these commands from that newer release copy against the same `SkillsDir`:

```powershell
pwsh -NoProfile -File .\update.ps1 -SkillsDir "$HOME\.agents\skills"
pwsh -NoProfile -File .\check.ps1 -SkillsDir "$HOME\.agents\skills"
```

```bash
bash ./update.sh --skills-dir "$HOME/.agents/skills"
bash ./check.sh --skills-dir "$HOME/.agents/skills"
```

Do not extract the new release inside the managed `<SkillsDir>/vibe` directory. `update` refuses to overwrite receipt-owned files when drift is detected.

## Remove

To remove VibeSkills, delete `<SkillsDir>/vibe` from the installation location.

## Replace An Older Version

Delete the old `<SkillsDir>/vibe` folder, then install the current release with the commands above.

v4 does not automatically install or recommend the `chrome`, `chrome-devtools`, `playwright`, `context7`, or `claude-flow` MCPs. The installer also does not modify their host configuration.

The installer does not edit Codex, Claude, or Agents settings. It also does not write system prompts or command wrappers. Extra skill scan directories are managed by runtime config:

- User level: `~/.vibeskills/skill-roots.json`
- Workspace level: `<workspace>/.vibeskills/skill-roots.json`

Repository checkout installation is for development only.
