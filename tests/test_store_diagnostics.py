from conftest import run_and_load_report


def test_activate_failure_report_includes_store_lookup_events(app_paths):
    payload = run_and_load_report(app_paths, ["activate", "missing"])
    names = [event["name"] for event in payload["events"]]

    assert "record_lookup_started" in names
    assert "record_lookup_failed" in names


def test_write_atomic_failure_records_path_context(
    monkeypatch, app_paths, other_saved_session
):
    app_paths.live_auth_file.parent.mkdir(parents=True, exist_ok=True)

    def explode(*args, **kwargs):
        raise PermissionError("chmod denied")

    monkeypatch.setattr("codex_switch.store.os.chmod", explode)

    payload = run_and_load_report(app_paths, ["activate", other_saved_session.name])
    names = [event["name"] for event in payload["events"]]
    assert "atomic_write_started" in names
    assert payload["error_category"] == "system_error"
    assert payload["context"]["paths"]["live_auth_file"]["exists"] is False
    assert payload["context"]["paths"]["temp_write_path"]["exists"] is True
