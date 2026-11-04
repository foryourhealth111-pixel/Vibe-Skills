# Troubleshooting

If VibeSkills is not working, inspect the install transaction first.
If the journal at `<SkillsDir>/.vibeskills/vibe-install-state.json` exists,
preserve the installed directory, journal and backups. Follow the
[install recovery guidance](install/README.en.md#install) before removing the installation.

After confirming there is no pending install transaction, delete `<SkillsDir>/vibe`
and install the current release again.

If `vibe` does not appear after installation, make sure the AI application scans that `SkillsDir`.
