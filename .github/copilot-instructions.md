# Repository Instructions

- This repository is a Python CLI project. The main application code lives in `src/codex_switch/`.
- Public installation entrypoint is `install.sh`. The installed launcher is `bin/codex-switch`.
- Mutable user state must live under `~/.codex-switch/`, not inside the repository.
- Treat `~/.codex/auth.json` as sensitive live state. `activate` must preserve an unsaved current session via autosnapshot before replacing it.
- `delete` must never modify or remove the live `~/.codex/auth.json`; it only deletes saved metadata and snapshot files.
- `update` must refresh the managed copy in `~/.codex-switch/tmp/codex-switch` and rerun installation so the launcher keeps pointing at the managed copy.
- Favor atomic file replacement and restrictive file permissions when writing auth-related files.
- Keep `README.md` aligned with the actual CLI behavior and install flow.
- Python changes should keep the `pytest` suite passing and preserve `100%` coverage.
