from codex_switch.cli import main


def test_status_prints_expanded_metadata(capsys, app_paths, auth_file):
    app_paths.live_auth_file.parent.mkdir(parents=True, exist_ok=True)
    app_paths.live_auth_file.write_text(auth_file.read_text())

    exit_code = main(["status"], home=app_paths.home)

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "author@example.com" in output
    assert "plan: plus" in output
    assert "account_id: acct-123" in output
    assert "session_id: authsess_123" in output
