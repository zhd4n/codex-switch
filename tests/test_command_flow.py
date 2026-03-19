from codex_switch.cli import main


def test_command_flow_save_activate_delete(
    app_paths, auth_file, other_saved_session
):
    app_paths.live_auth_file.parent.mkdir(parents=True, exist_ok=True)
    app_paths.live_auth_file.write_text(auth_file.read_text())

    assert main(["save", "primary"], home=app_paths.home) == 0
    assert main(["activate", other_saved_session.name], home=app_paths.home) == 0
    assert main(["delete", "primary"], home=app_paths.home) == 0
