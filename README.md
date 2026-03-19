# codex-switch

CLI for saving and switching Codex auth sessions across multiple accounts.

## What It Does

`codex-switch` manages saved copies of `~/.codex/auth.json` so you can switch Codex CLI accounts without manually copying tokens around.

It can:

- save the current auth session under a name
- list saved sessions with auth metadata
- activate a saved session
- show the current live auth status
- delete a saved session
- self-update from the managed installed copy

## Install

```bash
git clone https://github.com/zhd4n/codex-switch.git
cd codex-switch
./install.sh
```

The installer:

- creates `~/.codex-switch/`
- syncs a managed copy into `~/.codex-switch/tmp/codex-switch`
- installs `codex-switch` into `~/.local/bin/codex-switch`

## Commands

### Save the current session

```bash
codex-switch save
codex-switch save work-account
```

If no name is passed, the email from the current auth payload is used.

### List saved sessions

```bash
codex-switch list
```

Shows saved session name, email, plan, account ID, default org, last refresh, and an active marker for the currently loaded auth snapshot.

### Activate a saved session

```bash
codex-switch activate work-account
```

If the current live auth file is not already saved, `codex-switch` creates an autosnapshot before switching.

### Show current status

```bash
codex-switch status
```

Shows live auth metadata including auth mode, email, name, plan, account ID, session ID, default org, email verification, and last refresh time.

### Delete a saved session

```bash
codex-switch delete work-account
```

Deletes only the saved snapshot and metadata. It does not touch the currently live `~/.codex/auth.json`.

### Update the installed tool

```bash
codex-switch update
```

Refreshes the managed copy in `~/.codex-switch/tmp/codex-switch` and re-runs `install.sh` so the user-facing executable keeps pointing at the refreshed copy.

## Development

Run the full test suite with enforced `100%` coverage:

```bash
uv run --with pytest --with pytest-cov pytest -q
```

## Storage Layout

Mutable data lives outside the repo under `~/.codex-switch/`:

- `sessions/` stores metadata records
- `snapshots/` stores raw saved `auth.json` files
- `tmp/codex-switch/` stores the managed installed copy
