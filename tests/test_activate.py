from codex_switch.store import SessionStore


def test_activate_autosaves_live_auth_when_unsaved(
    app_paths, auth_file, other_saved_session
):
    app_paths.live_auth_file.parent.mkdir(parents=True, exist_ok=True)
    app_paths.live_auth_file.write_text(auth_file.read_text())
    store = SessionStore(app_paths)

    activated = store.activate("target-session")

    assert activated.name == "target-session"
    autosaves = [record for record in store.list_records() if record.auto_snapshot]
    assert len(autosaves) == 1
    assert app_paths.live_auth_file.read_text() == other_saved_session.snapshot_path.read_text()
