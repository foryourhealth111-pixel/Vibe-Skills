---
name: vibe-upgrade
description: Upgrade the local Vibe-Skills installation to the latest official default-branch state.
---

This is an upgrade operation, not a normal staged `vibe` task.

Do not run the router for this entry. Do not relaunch this request as `entry_id = vibe`.
Do not freeze a requirement document or execution plan for this entry.
Do not invoke TDD, specialist dispatch, or delivery-acceptance gates unless the upgrade backend itself reports a verification failure.

Run the shared upgrade backend for the current host installation, then verify and report the before/after install state.
Use the installed runtime root as `--repo-root`; the backend will resolve or prepare the official default-branch source checkout when needed.

Bash execution shape (preferred when the host tool surface is Bash-like):

```bash
# Set this to the host root that contains skills/vibe-upgrade/SKILL.md.
TARGET_ROOT='<host-root>'
REPO_ROOT="$TARGET_ROOT/skills/vibe"
PYTHONPATH="$REPO_ROOT/apps/vgo-cli/src" py -3 -m vgo_cli.main upgrade --repo-root "$REPO_ROOT" --host <host-id> --target-root "$TARGET_ROOT" --frontend powershell --profile full
```

PowerShell execution shape:

```powershell
# Set this to the host root that contains skills\vibe-upgrade\SKILL.md.
$targetRoot = '<host-root>'
$repoRoot = Join-Path $targetRoot 'skills\vibe'
$env:PYTHONPATH = Join-Path $repoRoot 'apps\vgo-cli\src'
py -3 -m vgo_cli.main upgrade --repo-root $repoRoot --host <host-id> --target-root $targetRoot --frontend powershell --profile full
```

If the request is empty, default to upgrading the current host installation through shared `vgo-cli upgrade` and verify the result.
If the backend fails, report the exact backend error and do not fall back to ordinary `vibe` routing.

Request:
$ARGUMENTS
