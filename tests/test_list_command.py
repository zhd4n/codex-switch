from codex_switch.cli import main


def test_list_prints_saved_sessions_table(
    capsys, app_paths, saved_session, live_auth_matches_saved
):
    exit_code = main(["list"], home=app_paths.home)

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "author@example.com" in output
    assert "plus" in output
    assert "acct-123" in output
    assert "Personal" in output
    assert "2026-03-18T12:55:53.815614Z" in output
    assert "*" in output
