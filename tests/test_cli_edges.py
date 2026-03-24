import subprocess
from pathlib import Path

from conftest import run_and_load_report
from codex_switch.cli import (
    DEFAULT_REPO_URL,
    main,
    refresh_managed_repo,
    resolve_repo_url,
)
from codex_switch.cli import run_subprocess
from codex_switch.cli import tail_lines


def test_resolve_repo_url_uses_default_when_env_missing(monkeypatch):
    monkeypatch.delenv("CODEX_SWITCH_REPO_URL", raising=False)

    assert resolve_repo_url() == DEFAULT_REPO_URL


def test_refresh_managed_repo_clones_when_directory_is_stale(tmp_path, monkeypatch):
    managed_repo_dir = tmp_path / "managed"
    managed_repo_dir.mkdir()
    (managed_repo_dir / "stale.txt").write_text("stale")
    seen = {}

    def fake_run(cmd, **kwargs):
        seen["cmd"] = cmd
        managed_repo_dir.mkdir(exist_ok=True)
        (managed_repo_dir / ".git").mkdir(exist_ok=True)
        return None

    monkeypatch.setattr("codex_switch.cli.subprocess.run", fake_run)

    refresh_managed_repo(managed_repo_dir, "repo-url")

    assert seen["cmd"] == ["git", "clone", "repo-url", str(managed_repo_dir)]
    assert (managed_repo_dir / ".git").exists()


def test_refresh_managed_repo_clones_when_directory_is_missing(tmp_path, monkeypatch):
    managed_repo_dir = tmp_path / "managed"
    seen = {}

    def fake_run(cmd, **kwargs):
        seen["cmd"] = cmd
        managed_repo_dir.mkdir(exist_ok=True)
        (managed_repo_dir / ".git").mkdir(exist_ok=True)
        return None

    monkeypatch.setattr("codex_switch.cli.subprocess.run", fake_run)

    refresh_managed_repo(managed_repo_dir, "repo-url")

    assert seen["cmd"] == ["git", "clone", "repo-url", str(managed_repo_dir)]


def test_refresh_managed_repo_pulls_when_git_directory_exists(tmp_path, monkeypatch):
    managed_repo_dir = tmp_path / "managed"
    (managed_repo_dir / ".git").mkdir(parents=True)
    seen = {}

    def fake_run(cmd, **kwargs):
        seen["cmd"] = cmd
        return None

    monkeypatch.setattr("codex_switch.cli.subprocess.run", fake_run)

    refresh_managed_repo(managed_repo_dir, "repo-url")

    assert seen["cmd"] == ["git", "-C", str(managed_repo_dir), "pull", "--ff-only"]


def test_main_dispatches_update_branch(monkeypatch, tmp_path):
    calls = {}

    def fake_refresh(path: Path, repo_url: str, *, diagnostics=None) -> None:
        calls["refresh"] = (path, repo_url, diagnostics is not None)
        path.mkdir(parents=True, exist_ok=True)

    def fake_run(cmd, **kwargs):
        calls["run"] = (cmd, kwargs["cwd"])
        return None

    monkeypatch.setattr("codex_switch.cli.refresh_managed_repo", fake_refresh)
    monkeypatch.setattr("codex_switch.cli.resolve_repo_url", lambda: "repo-url")
    monkeypatch.setattr("codex_switch.cli.subprocess.run", fake_run)

    assert main(["update"], home=tmp_path) == 0
    assert calls["refresh"][1] == "repo-url"
    assert calls["refresh"][2] is True
    assert calls["run"][0] == ["bash", "install.sh"]


def test_update_failure_report_includes_structured_subprocess_details(
    monkeypatch, app_paths
):
    def fake_run(*args, **kwargs):
        raise subprocess.CalledProcessError(
            1,
            ["git", "clone", "repo", "dest"],
            output="line1\nline2",
            stderr="fatal: boom",
        )

    monkeypatch.setattr("codex_switch.cli.subprocess.run", fake_run)

    payload = run_and_load_report(app_paths, ["update"])
    assert payload["exception"]["details"]["subprocess"]["command"] == [
        "git",
        "clone",
        "repo",
        "dest",
    ]
    assert payload["exception"]["details"]["subprocess"]["exit_code"] == 1
    assert payload["exception"]["details"]["subprocess"]["stderr_tail"] == [
        "fatal: boom"
    ]


def test_run_subprocess_reraises_called_process_error_without_diagnostics(monkeypatch):
    def fake_run(*args, **kwargs):
        raise subprocess.CalledProcessError(1, ["git"], output="", stderr="")

    monkeypatch.setattr("codex_switch.cli.subprocess.run", fake_run)

    try:
        run_subprocess(["git"], check=True)
    except subprocess.CalledProcessError as error:
        assert error.returncode == 1
    else:  # pragma: no cover
        raise AssertionError("CalledProcessError was not raised")


def test_tail_lines_returns_empty_for_missing_output():
    assert tail_lines(None) == []
    assert tail_lines("") == []
