from codex_switch.cli import build_parser


def test_build_parser_exposes_expected_commands():
    parser = build_parser()
    subparsers = next(action for action in parser._actions if action.dest == "command")

    assert {"save", "list", "activate", "status", "delete", "update"} <= set(
        subparsers.choices
    )
