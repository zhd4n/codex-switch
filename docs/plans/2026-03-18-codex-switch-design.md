# Codex Switch Design

**Date:** 2026-03-18

## Goal

Build a portable CLI utility that lets users save, inspect, activate, and delete Codex auth sessions, plus install and self-update the tool from a managed copy under `~/.codex-switch/`.

## Constraints

- The tool must be installable by other users, not just the author.
- The repository should remain compatible with future Homebrew packaging.
- User data must live outside the managed clone so install and update do not destroy saved sessions.
- Test coverage must be enforced at `100%`.

## Installation Model

- Keep `install.sh` as the primary user-facing install entrypoint:
  - `git clone`
  - `cd codex-switch`
  - `./install.sh`
- `install.sh` is responsible for:
  - creating `~/.codex-switch/{bin,sessions,snapshots,tmp}`
  - refreshing the managed copy at `~/.codex-switch/tmp/codex-switch`
  - installing an executable shim or symlink in a directory already on `PATH` when possible
  - making the installation idempotent
- A `Makefile` may be added later for developer convenience, but it is not the primary installation interface.

## Architecture

Use a hybrid approach:

- Shell for install and self-update orchestration
- Python 3 for the main CLI and session management logic

This keeps installation simple for end users while making JSON parsing, metadata extraction, atomic writes, and test coverage enforcement reliable and maintainable.

## CLI Commands

### `codex-switch save [name]`

- Save the current `~/.codex/auth.json`.
- Default name is the email extracted from the current auth payload.
- If the name already exists, fail unless `--force` is passed.
- Persist the full raw `auth.json` snapshot plus extracted metadata.

### `codex-switch list`

- Show a compact table of saved sessions.
- Include:
  - session name
  - email
  - plan type
  - account ID
  - default organization title
  - last refresh
  - active marker
- Surface useful auth-derived metadata where available.

### `codex-switch activate <name>`

- If the current live `~/.codex/auth.json` does not match any saved snapshot, create an automatic snapshot before switching.
- Replace `~/.codex/auth.json` with the selected saved snapshot using an atomic write.
- Preserve restrictive file permissions on the restored auth file.

### `codex-switch status`

- Show the current active session and expanded metadata derived from the live `auth.json`.
- Include the matched saved session name when applicable.
- Show fields such as:
  - auth mode
  - email
  - name
  - plan type
  - account ID
  - session ID
  - email verification flag
  - subscription active until
  - subscription last checked
  - organizations
  - compute residency
  - last refresh

### `codex-switch delete <name>`

- Delete only the saved snapshot and metadata for the named session.
- Never delete or mutate the currently live `~/.codex/auth.json`.

### `codex-switch update`

- Refresh the managed repository at `~/.codex-switch/tmp/codex-switch`.
- Pull or reclone from the configured upstream repository.
- Run the managed copy's `install.sh` automatically.
- Ensure the user-facing `codex-switch` command points at the refreshed managed copy after update completes.

## Data Storage

Store all mutable user data under `~/.codex-switch/`.

### `~/.codex-switch/sessions/<slug>.json`

Session metadata record containing:

- display name
- slug
- snapshot path
- extracted auth metadata
- created and updated timestamps
- `auto_snapshot` flag

### `~/.codex-switch/snapshots/<slug>.auth.json`

Raw saved copy of `~/.codex/auth.json`.

### `~/.codex-switch/state.json`

Service state containing:

- storage schema version
- last activated session name
- managed clone path
- install target path for the executable shim or symlink

## Metadata Extraction

Extract metadata from `auth.json` and decoded JWT payloads where available.

Preferred fields:

- `auth_mode`
- `last_refresh`
- `tokens.account_id`
- ID token `email`
- ID token `name`
- ID token `email_verified`
- access token `session_id`
- plan type
- subscription active window
- subscription last checked
- organizations and default organization title
- compute residency
- user IDs when available

If JWT payload decoding fails but the JSON file itself is valid, saving still succeeds and stores only the metadata that can be extracted safely.

## Session Matching

Determine whether a saved session is active by comparing the current live `~/.codex/auth.json` byte-for-byte against saved snapshots.

This avoids weak heuristics based on partial metadata and keeps matching deterministic.

## Error Handling and Safety

- Treat missing or invalid `~/.codex/auth.json` as a hard error for commands that require it.
- Use temporary files plus atomic rename for writes to `~/.codex/auth.json`.
- Restore auth file permissions to `0600`.
- Generate automatic snapshot names with timestamped stable slugs.
- Never remove the live auth file during `delete`.
- Keep session data outside the managed clone so `install` and `update` remain safe.

## Testing Strategy

- Use `pytest` for the Python CLI.
- Use coverage enforcement with a hard `100%` requirement.
- Test with isolated temporary `HOME` directories.
- Use fixture auth files with deterministic JWT payloads.
- Cover:
  - metadata extraction
  - session save semantics
  - duplicate handling
  - active session detection
  - autosnapshot on activate
  - atomic restore behavior
  - status and list rendering
  - deletion semantics
  - update/install orchestration boundaries
- Add shell smoke coverage for `install.sh`.

## Recommendation

Proceed with:

- Python CLI as the primary implementation
- shell-based `install.sh`
- user state under `~/.codex-switch/`
- autosnapshot before activation
- `100%` enforced test coverage from the first implementation commit
