import pytest

from codex_switch.store import SessionAlreadyExistsError, SessionStore


def test_save_raises_when_name_exists_without_force(app_paths, auth_file):
    store = SessionStore(app_paths)
    store.save(auth_file, name="primary")

    with pytest.raises(SessionAlreadyExistsError):
        store.save(auth_file, name="primary")


def test_get_record_raises_for_unknown_session(app_paths):
    store = SessionStore(app_paths)

    with pytest.raises(KeyError):
        store.get_record("missing")


def test_activate_restores_target_when_no_live_auth_exists(app_paths, other_saved_session):
    store = SessionStore(app_paths)

    activated = store.activate(other_saved_session.name)

    assert activated.name == other_saved_session.name
    assert app_paths.live_auth_file.read_text() == other_saved_session.snapshot_path.read_text()
    assert all(not record.auto_snapshot for record in store.list_records())


def test_delete_tolerates_missing_snapshot_file(app_paths, saved_session):
    saved_session.snapshot_path.unlink()
    store = SessionStore(app_paths)

    store.delete(saved_session.name)

    assert not saved_session.metadata_path.exists()
