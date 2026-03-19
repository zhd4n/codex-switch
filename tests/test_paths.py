from pathlib import Path

from codex_switch.paths import AppPaths


def test_app_paths_resolve_under_home(tmp_path: Path):
    paths = AppPaths.from_home(tmp_path)

    assert paths.codex_dir == tmp_path / ".codex"
    assert paths.app_dir == tmp_path / ".codex-switch"
    assert paths.sessions_dir == tmp_path / ".codex-switch" / "sessions"
    assert paths.snapshots_dir == tmp_path / ".codex-switch" / "snapshots"
    assert paths.managed_repo_dir == tmp_path / ".codex-switch" / "tmp" / "codex-switch"
