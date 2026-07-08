# OpenCode Preview Install Path

This note is a preview host-adapter guide, not the main public install story.
The main public path is still the published release zip plus the generic `install`, `check`, `update`, and `uninstall` wrappers.

## What This Preview Lane Covers

- The repository can install the `vibe` runtime payload into OpenCode roots.
- The repository can materialize OpenCode command and agent wrapper scaffolds.
- The repository can ship an `opencode.json.example` reference file.

This lane does **not** claim full host closure.

## What Stays Host-Managed

- the real `opencode.json`
- provider credentials
- plugin provisioning
- MCP trust and native host policy

## Entry Points

Use the host-preview entrypoints when you intentionally want the OpenCode adapter lane:

```powershell
pwsh -NoProfile -File .\install.ps1 -HostId opencode
pwsh -NoProfile -File .\check.ps1 -HostId opencode
```

```bash
bash ./install.sh --host opencode
bash ./check.sh --host opencode
```

## Default Root

The default target root is `OPENCODE_HOME` when that variable is set.
Otherwise the host root is `~/.config/opencode`.

## Repo-Owned Output

The preview lane may write:

- the `vibe` runtime payload
- command wrappers under the OpenCode command roots
- agent wrappers under the OpenCode agent roots
- `.vibeskills` sidecars and receipts
- `opencode.json.example`

It does not take ownership of the real `opencode.json`.

## Detailed Historical Walkthrough

The longer host-specific walkthrough remains available as a historical operator guide:

- [`../archive/install-legacy/2026-07-02/opencode-path.en.md`](../archive/install-legacy/2026-07-02/opencode-path.en.md)
