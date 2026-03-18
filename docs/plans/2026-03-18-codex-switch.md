# Codex Switch Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a portable `codex-switch` CLI that saves, lists, activates, inspects, deletes, installs, and self-updates Codex auth sessions without losing user data.

**Architecture:** The project uses a Python 3 CLI for session management and metadata extraction, with a shell-based `install.sh` for installation and self-update orchestration. All mutable user state lives under `~/.codex-switch/`, while the executable shim points to a managed clone under `~/.codex-switch/tmp/codex-switch`.

**Tech Stack:** Python 3, `argparse`, `json`, `pathlib`, `tempfile`, `subprocess`, shell script, `pytest`, `pytest-cov`

---

### Task 1: Scaffold Project Layout and Test Harness

**Files:**
- Create: `src/codex_switch/__init__.py`
- Create: `src/codex_switch/cli.py`
- Create: `tests/conftest.py`
- Create: `tests/test_cli_smoke.py`
- Create: `pytest.ini`
- Create: `requirements-dev.txt`
- Modify: `README.md`

**Step 1: Write the failing test**

```python
from codex_switch.cli import build_parser


def test_build_parser_exposes_expected_commands():
    parser = build_parser()
    subparsers = next(
        action for action in parser._actions if action.dest == "command"
    )

    assert {"save", "list", "activate", "status", "delete", "update"} <= set(
        subparsers.choices
    )
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli_smoke.py -q`
Expected: FAIL because `codex_switch.cli` does not exist yet.

**Step 3: Write minimal implementation**

```python
import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codex-switch")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("save", "list", "activate", "status", "delete", "update"):
        subparsers.add_parser(name)
    return parser
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli_smoke.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/codex_switch/__init__.py src/codex_switch/cli.py tests/conftest.py tests/test_cli_smoke.py pytest.ini requirements-dev.txt README.md
git commit -m "feat: scaffold codex-switch cli"
```

### Task 2: Add Configurable Path Layer for `HOME`, `.codex`, and Storage Directories

**Files:**
- Create: `src/codex_switch/paths.py`
- Create: `tests/test_paths.py`
- Modify: `src/codex_switch/cli.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from codex_switch.paths import AppPaths


def test_app_paths_resolve_under_home(tmp_path: Path):
    paths = AppPaths.from_home(tmp_path)

    assert paths.codex_dir == tmp_path / ".codex"
    assert paths.app_dir == tmp_path / ".codex-switch"
    assert paths.sessions_dir == tmp_path / ".codex-switch" / "sessions"
    assert paths.snapshots_dir == tmp_path / ".codex-switch" / "snapshots"
    assert paths.managed_repo_dir == tmp_path / ".codex-switch" / "tmp" / "codex-switch"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_paths.py -q`
Expected: FAIL because `AppPaths` is undefined.

**Step 3: Write minimal implementation**

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    home: Path
    codex_dir: Path
    app_dir: Path
    sessions_dir: Path
    snapshots_dir: Path
    tmp_dir: Path
    managed_repo_dir: Path
    state_file: Path
    live_auth_file: Path

    @classmethod
    def from_home(cls, home: Path) -> "AppPaths":
        codex_dir = home / ".codex"
        app_dir = home / ".codex-switch"
        tmp_dir = app_dir / "tmp"
        return cls(
            home=home,
            codex_dir=codex_dir,
            app_dir=app_dir,
            sessions_dir=app_dir / "sessions",
            snapshots_dir=app_dir / "snapshots",
            tmp_dir=tmp_dir,
            managed_repo_dir=tmp_dir / "codex-switch",
            state_file=app_dir / "state.json",
            live_auth_file=codex_dir / "auth.json",
        )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_paths.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/codex_switch/paths.py src/codex_switch/cli.py tests/test_paths.py
git commit -m "feat: add codex-switch path model"
```

### Task 3: Implement Auth File Loading and JWT Metadata Extraction

**Files:**
- Create: `src/codex_switch/auth.py`
- Create: `tests/test_auth.py`
- Modify: `tests/conftest.py`

**Step 1: Write the failing test**

```python
from codex_switch.auth import load_auth_snapshot


def test_load_auth_snapshot_extracts_email_plan_and_org(auth_file):
    snapshot = load_auth_snapshot(auth_file)

    assert snapshot.email == "author@example.com"
    assert snapshot.plan == "plus"
    assert snapshot.account_id == "acct-123"
    assert snapshot.default_org_title == "Personal"
    assert snapshot.email_verified is True
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_auth.py -q`
Expected: FAIL because `load_auth_snapshot` is undefined.

**Step 3: Write minimal implementation**

```python
def load_auth_snapshot(path: Path) -> AuthSnapshot:
    raw = json.loads(path.read_text())
    id_payload = decode_jwt_payload(raw["tokens"]["id_token"])
    access_payload = decode_jwt_payload(raw["tokens"]["access_token"])
    return AuthSnapshot(
        raw=raw,
        email=id_payload.get("email")
        or access_payload.get("https://api.openai.com/profile", {}).get("email"),
        plan=id_payload.get("https://api.openai.com/auth", {}).get("chatgpt_plan_type"),
        account_id=raw.get("tokens", {}).get("account_id"),
        default_org_title=extract_default_org_title(id_payload),
        email_verified=bool(id_payload.get("email_verified")),
    )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_auth.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/codex_switch/auth.py tests/test_auth.py tests/conftest.py
git commit -m "feat: extract codex auth metadata"
```

### Task 4: Persist Session Metadata and Raw Snapshots

**Files:**
- Create: `src/codex_switch/store.py`
- Create: `tests/test_store_save.py`
- Modify: `src/codex_switch/auth.py`
- Modify: `src/codex_switch/paths.py`

**Step 1: Write the failing test**

```python
from codex_switch.store import SessionStore


def test_save_session_uses_email_as_default_name(app_paths, auth_file):
    store = SessionStore(app_paths)

    record = store.save(auth_file)

    assert record.name == "author@example.com"
    assert record.snapshot_path.exists()
    assert record.metadata_path.exists()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_store_save.py -q`
Expected: FAIL because `SessionStore` is undefined.

**Step 3: Write minimal implementation**

```python
class SessionStore:
    def __init__(self, paths: AppPaths) -> None:
        self.paths = paths

    def save(self, auth_path: Path, name: str | None = None, force: bool = False) -> SessionRecord:
        snapshot = load_auth_snapshot(auth_path)
        session_name = name or snapshot.email
        slug = slugify(session_name)
        self.paths.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.paths.snapshots_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = self.paths.snapshots_dir / f"{slug}.auth.json"
        metadata_path = self.paths.sessions_dir / f"{slug}.json"
        if metadata_path.exists() and not force:
            raise SessionAlreadyExistsError(session_name)
        shutil.copy2(auth_path, snapshot_path)
        metadata_path.write_text(json.dumps(build_record_dict(...), indent=2))
        return load_record(metadata_path)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_store_save.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/codex_switch/store.py src/codex_switch/auth.py src/codex_switch/paths.py tests/test_store_save.py
git commit -m "feat: persist saved codex sessions"
```

### Task 5: Implement Listing and Active Session Detection

**Files:**
- Create: `tests/test_store_list.py`
- Modify: `src/codex_switch/store.py`
- Modify: `src/codex_switch/auth.py`

**Step 1: Write the failing test**

```python
def test_list_records_marks_session_as_active(app_paths, saved_session, live_auth_matches_saved):
    store = SessionStore(app_paths)

    records = store.list_records()

    assert len(records) == 1
    assert records[0].is_active is True
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_store_list.py -q`
Expected: FAIL because `list_records` does not mark active state.

**Step 3: Write minimal implementation**

```python
def list_records(self) -> list[SessionRecord]:
    current_bytes = self.paths.live_auth_file.read_bytes() if self.paths.live_auth_file.exists() else None
    records = [load_record(path) for path in sorted(self.paths.sessions_dir.glob("*.json"))]
    for record in records:
        record.is_active = current_bytes is not None and record.snapshot_path.read_bytes() == current_bytes
    return records
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_store_list.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/codex_switch/store.py src/codex_switch/auth.py tests/test_store_list.py
git commit -m "feat: detect active codex sessions"
```

### Task 6: Implement Autosnapshot and Atomic Activate Behavior

**Files:**
- Create: `tests/test_activate.py`
- Modify: `src/codex_switch/store.py`
- Modify: `src/codex_switch/auth.py`

**Step 1: Write the failing test**

```python
def test_activate_autosaves_live_auth_when_unsaved(app_paths, auth_file, other_saved_session):
    store = SessionStore(app_paths)

    activated = store.activate("target-session")

    assert activated.name == "target-session"
    autosaves = [record for record in store.list_records() if record.auto_snapshot]
    assert len(autosaves) == 1
    assert app_paths.live_auth_file.read_text() == other_saved_session.snapshot_path.read_text()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_activate.py -q`
Expected: FAIL because `activate` is undefined or does not autosave.

**Step 3: Write minimal implementation**

```python
def activate(self, name: str) -> SessionRecord:
    target = self.get_record(name)
    live_bytes = self.paths.live_auth_file.read_bytes()
    if not any(record.snapshot_path.read_bytes() == live_bytes for record in self.list_records()):
        self.save(self.paths.live_auth_file, name=build_autosave_name(...), force=False, auto_snapshot=True)
    write_atomic(self.paths.live_auth_file, target.snapshot_path.read_bytes(), mode=0o600)
    self._write_state(last_activated=name)
    return self.get_record(name)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_activate.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/codex_switch/store.py src/codex_switch/auth.py tests/test_activate.py
git commit -m "feat: autosave before auth activation"
```

### Task 7: Implement Delete Semantics

**Files:**
- Create: `tests/test_delete.py`
- Modify: `src/codex_switch/store.py`

**Step 1: Write the failing test**

```python
def test_delete_removes_saved_snapshot_but_not_live_auth(app_paths, saved_session, live_auth_matches_saved):
    store = SessionStore(app_paths)

    store.delete(saved_session.name)

    assert not saved_session.snapshot_path.exists()
    assert not saved_session.metadata_path.exists()
    assert app_paths.live_auth_file.exists()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_delete.py -q`
Expected: FAIL because `delete` is undefined.

**Step 3: Write minimal implementation**

```python
def delete(self, name: str) -> None:
    record = self.get_record(name)
    record.metadata_path.unlink()
    if record.snapshot_path.exists():
        record.snapshot_path.unlink()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_delete.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/codex_switch/store.py tests/test_delete.py
git commit -m "feat: delete saved codex sessions"
```

### Task 8: Implement `status` Rendering With Expanded Auth Metadata

**Files:**
- Create: `tests/test_status.py`
- Modify: `src/codex_switch/cli.py`
- Modify: `src/codex_switch/store.py`
- Modify: `src/codex_switch/auth.py`

**Step 1: Write the failing test**

```python
def test_status_prints_expanded_metadata(capsys, app_paths, auth_file):
    exit_code = main(["status"], home=app_paths.home)

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "author@example.com" in output
    assert "plan: plus" in output
    assert "account_id: acct-123" in output
    assert "session_id: authsess_123" in output
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_status.py -q`
Expected: FAIL because `main` or `status` output is missing.

**Step 3: Write minimal implementation**

```python
def handle_status(store: SessionStore) -> int:
    snapshot = load_auth_snapshot(store.paths.live_auth_file)
    active = store.find_active_record()
    for line in format_status_lines(snapshot, active):
        print(line)
    return 0
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_status.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/codex_switch/cli.py src/codex_switch/store.py src/codex_switch/auth.py tests/test_status.py
git commit -m "feat: show active codex auth status"
```

### Task 9: Implement `list` Rendering With Compact Auth Columns

**Files:**
- Create: `tests/test_list_command.py`
- Modify: `src/codex_switch/cli.py`
- Modify: `src/codex_switch/store.py`

**Step 1: Write the failing test**

```python
def test_list_prints_saved_sessions_table(capsys, app_paths, saved_session, live_auth_matches_saved):
    exit_code = main(["list"], home=app_paths.home)

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "author@example.com" in output
    assert "plus" in output
    assert "acct-123" in output
    assert "*" in output
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_list_command.py -q`
Expected: FAIL because `list` output is missing.

**Step 3: Write minimal implementation**

```python
def handle_list(store: SessionStore) -> int:
    for row in format_record_table(store.list_records()):
        print(row)
    return 0
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_list_command.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/codex_switch/cli.py src/codex_switch/store.py tests/test_list_command.py
git commit -m "feat: list saved codex sessions"
```

### Task 10: Wire `save`, `activate`, and `delete` Commands Through the CLI

**Files:**
- Create: `tests/test_command_flow.py`
- Modify: `src/codex_switch/cli.py`
- Modify: `src/codex_switch/store.py`

**Step 1: Write the failing test**

```python
def test_command_flow_save_activate_delete(capsys, app_paths, auth_file, other_saved_session):
    assert main(["save", "primary"], home=app_paths.home) == 0
    assert main(["activate", other_saved_session.name], home=app_paths.home) == 0
    assert main(["delete", "primary"], home=app_paths.home) == 0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_command_flow.py -q`
Expected: FAIL because the commands are not wired through `main`.

**Step 3: Write minimal implementation**

```python
def main(argv: list[str] | None = None, home: Path | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = SessionStore(AppPaths.from_home(home or Path.home()))
    return dispatch(args, store)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_command_flow.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/codex_switch/cli.py src/codex_switch/store.py tests/test_command_flow.py
git commit -m "feat: wire codex-switch session commands"
```

### Task 11: Implement `install.sh` and Managed-Clone Shim Installation

**Files:**
- Create: `install.sh`
- Create: `tests/test_install_script.py`
- Create: `README.md`
- Modify: `src/codex_switch/paths.py`

**Step 1: Write the failing test**

```python
def test_install_script_creates_managed_clone_and_shim(fake_repo, isolated_home):
    result = subprocess.run(
        ["bash", "install.sh"],
        cwd=fake_repo,
        env=build_install_env(isolated_home),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert (isolated_home / ".codex-switch" / "tmp" / "codex-switch").exists()
    assert (isolated_home / ".local" / "bin" / "codex-switch").exists()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_install_script.py -q`
Expected: FAIL because `install.sh` does not exist yet.

**Step 3: Write minimal implementation**

```bash
#!/usr/bin/env bash
set -euo pipefail

APP_HOME="${HOME}/.codex-switch"
MANAGED_REPO="${APP_HOME}/tmp/codex-switch"
BIN_DIR="${HOME}/.local/bin"

mkdir -p "${APP_HOME}/sessions" "${APP_HOME}/snapshots" "${APP_HOME}/tmp" "${BIN_DIR}"
rsync -a --delete --exclude '.git' ./ "${MANAGED_REPO}/"
ln -sfn "${MANAGED_REPO}/bin/codex-switch" "${BIN_DIR}/codex-switch"
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_install_script.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add install.sh README.md src/codex_switch/paths.py tests/test_install_script.py
git commit -m "feat: add codex-switch installer"
```

### Task 12: Implement `update` to Refresh the Managed Clone and Re-run Installer

**Files:**
- Create: `tests/test_update.py`
- Modify: `src/codex_switch/cli.py`
- Modify: `install.sh`
- Modify: `src/codex_switch/paths.py`

**Step 1: Write the failing test**

```python
def test_update_refreshes_managed_clone_and_reinstalls(fake_origin_repo, isolated_home):
    result = subprocess.run(
        ["python3", "-m", "codex_switch.cli", "update"],
        env=build_cli_env(isolated_home, fake_origin_repo),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "updated" in result.stdout.lower()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_update.py -q`
Expected: FAIL because `update` is not implemented.

**Step 3: Write minimal implementation**

```python
def handle_update(paths: AppPaths) -> int:
    refresh_managed_repo(paths.managed_repo_dir, repo_url=resolve_repo_url())
    subprocess.run(["bash", "install.sh"], cwd=paths.managed_repo_dir, check=True)
    print("Updated managed codex-switch installation.")
    return 0
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_update.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/codex_switch/cli.py install.sh src/codex_switch/paths.py tests/test_update.py
git commit -m "feat: add codex-switch self-update"
```

### Task 13: Enforce `100%` Coverage and Run the Full Suite

**Files:**
- Modify: `pytest.ini`
- Modify: `requirements-dev.txt`
- Modify: `README.md`

**Step 1: Write the failing test**

```ini
[pytest]
addopts = --cov=src/codex_switch --cov-branch --cov-report=term-missing --cov-fail-under=100
```

**Step 2: Run test to verify it fails**

Run: `pytest -q`
Expected: FAIL if any line or branch is untested.

**Step 3: Write minimal implementation**

```ini
[pytest]
pythonpath = src
addopts = --cov=codex_switch --cov-branch --cov-report=term-missing --cov-fail-under=100
```

**Step 4: Run test to verify it passes**

Run: `pytest -q`
Expected: PASS with `100%` total coverage.

**Step 5: Commit**

```bash
git add pytest.ini requirements-dev.txt README.md
git commit -m "test: enforce full codex-switch coverage"
```

### Task 14: Final Verification and Remote Push

**Files:**
- Modify: `README.md`

**Step 1: Write the failing test**

```text
Run the documented install and command smoke flow in a clean temporary HOME.
```

**Step 2: Run test to verify it fails**

Run: `HOME="$(mktemp -d)" bash install.sh`
Expected: FAIL if docs or installation assumptions are wrong.

**Step 3: Write minimal implementation**

```markdown
Document install, save, list, activate, status, delete, and update usage, plus Homebrew-readiness notes.
```

**Step 4: Run test to verify it passes**

Run: `HOME="$(mktemp -d)" bash install.sh && PATH="$HOME/.local/bin:$PATH" codex-switch --help && pytest -q`
Expected: PASS

**Step 5: Commit**

```bash
git add README.md
git commit -m "docs: document codex-switch usage"
git push
```
