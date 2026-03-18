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
