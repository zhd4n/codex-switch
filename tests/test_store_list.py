from codex_switch.store import SessionStore


def test_list_records_marks_session_as_active(
    app_paths, saved_session, live_auth_matches_saved
):
    store = SessionStore(app_paths)

    records = store.list_records()

    assert len(records) == 1
    assert records[0].is_active is True
