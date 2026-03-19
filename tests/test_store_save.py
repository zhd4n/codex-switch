from codex_switch.store import SessionStore


def test_save_session_uses_email_as_default_name(app_paths, auth_file):
    store = SessionStore(app_paths)

    record = store.save(auth_file)

    assert record.name == "author@example.com"
    assert record.snapshot_path.exists()
    assert record.metadata_path.exists()
