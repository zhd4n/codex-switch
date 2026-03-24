import json
import subprocess
import sys

import pytest

from codex_switch.cli import classify_error
from codex_switch.cli import handle_status
from codex_switch.cli import main
from codex_switch.store import SessionAlreadyExistsError
from codex_switch.store import SessionStore
from conftest import load_only_report
from conftest import run_and_load_report


def test_main_writes_diagnostic_report_on_failure(app_paths, capsys):
    exit_code = main(["status"], home=app_paths.home)

    assert exit_code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Diagnostic report:" in captured.err
    reports = sorted(app_paths.app_dir.joinpath("diagnostics").glob("*.json"))
    assert len(reports) == 1
    payload = json.loads(reports[0].read_text())
    assert payload["command"] == "status"


def test_main_uses_sys_argv_for_diagnostics_when_argv_is_omitted(
    monkeypatch, app_paths
):
    monkeypatch.setattr(sys, "argv", ["codex-switch", "status"])

    exit_code = main(home=app_paths.home)

    assert exit_code == 1
    payload = load_only_report(app_paths)
    assert payload["args"] == ["status"]


def test_main_handles_missing_report_path_gracefully(app_paths, monkeypatch, capsys):
    monkeypatch.setattr(
        "codex_switch.cli.DiagnosticRun.write_failure_report",
        lambda *args, **kwargs: None,
    )

    exit_code = main(["status"], home=app_paths.home)

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "Diagnostic report:" not in captured.err
    assert captured.out == ""


def test_main_does_not_write_report_on_success(app_paths, auth_file):
    app_paths.live_auth_file.parent.mkdir(parents=True, exist_ok=True)
    app_paths.live_auth_file.write_text(auth_file.read_text())

    assert main(["status"], home=app_paths.home) == 0
    assert not list(app_paths.app_dir.joinpath("diagnostics").glob("*.json"))


def test_usage_errors_do_not_create_diagnostics(app_paths):
    with pytest.raises(SystemExit):
        main([], home=app_paths.home)

    assert not list(app_paths.app_dir.joinpath("diagnostics").glob("*.json"))


def test_status_failure_report_includes_auth_events_and_summary(app_paths):
    payload = run_and_load_report(app_paths, ["status"])
    names = [event["name"] for event in payload["events"]]

    assert "auth_snapshot_load_started" in names
    assert payload["context"]["auth_summary"] == {}


def test_malformed_auth_payload_is_classified_as_data_error(app_paths):
    app_paths.live_auth_file.parent.mkdir(parents=True, exist_ok=True)
    app_paths.live_auth_file.write_text(
        json.dumps(
            {
                "auth_mode": "chatgpt",
                "last_refresh": "2026-03-18T12:55:53.815614Z",
                "tokens": [],
            }
        )
    )

    payload = run_and_load_report(app_paths, ["status"])

    assert payload["error_category"] == "data_error"


def test_debug_mode_writes_report_on_success(monkeypatch, app_paths, auth_file):
    monkeypatch.setenv("CODEX_SWITCH_DEBUG", "1")
    app_paths.live_auth_file.parent.mkdir(parents=True, exist_ok=True)
    app_paths.live_auth_file.write_text(auth_file.read_text())

    assert main(["status"], home=app_paths.home) == 0
    assert len(list(app_paths.app_dir.joinpath("diagnostics").glob("*.json"))) == 1


def test_debug_mode_activate_success_report_includes_autosave_event(
    monkeypatch, app_paths, auth_file, other_saved_session
):
    monkeypatch.setenv("CODEX_SWITCH_DEBUG", "1")
    app_paths.live_auth_file.parent.mkdir(parents=True, exist_ok=True)
    app_paths.live_auth_file.write_text(auth_file.read_text())

    assert main(["activate", other_saved_session.name], home=app_paths.home) == 0

    payload = load_only_report(app_paths)
    names = [event["name"] for event in payload["events"]]
    assert "autosave_created" in names


def test_handle_status_without_diagnostics_still_prints_snapshot(
    capsys, app_paths, auth_file
):
    app_paths.live_auth_file.parent.mkdir(parents=True, exist_ok=True)
    app_paths.live_auth_file.write_text(auth_file.read_text())

    exit_code = handle_status(SessionStore(app_paths))

    assert exit_code == 0
    assert "auth_mode: chatgpt" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("error", "category"),
    [
        (SessionAlreadyExistsError("duplicate"), "user_error"),
        (KeyError("missing"), "user_error"),
        (json.JSONDecodeError("bad", "{}", 0), "data_error"),
        (
            subprocess.CalledProcessError(1, ["git"]),
            "dependency_error",
        ),
        (FileNotFoundError(2, "missing", "git"), "dependency_error"),
        (FileNotFoundError("missing"), "user_error"),
        (PermissionError("denied"), "system_error"),
        (OSError("io"), "system_error"),
        (RuntimeError("boom"), "system_error"),
    ],
)
def test_classify_error_maps_expected_categories(error, category):
    assert classify_error(error) == category
