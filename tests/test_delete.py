from codex_switch.store import SessionStore


def test_delete_removes_saved_snapshot_but_not_live_auth(
    app_paths, saved_session, live_auth_matches_saved
):
    store = SessionStore(app_paths)

    store.delete(saved_session.name)

    assert not saved_session.snapshot_path.exists()
    assert not saved_session.metadata_path.exists()
    assert app_paths.live_auth_file.exists()
